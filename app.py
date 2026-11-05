import os
import sqlite3
from functools import wraps

from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, static_folder="static", static_url_path="")
# Chave usada para "assinar" o cookie de sessão. Em produção, troque por um valor secreto.
app.secret_key = "troque-esta-chave"

BANCO = "banco.db"


def conectar():
    conexao = sqlite3.connect(BANCO)
    conexao.row_factory = sqlite3.Row  # permite acessar colunas pelo nome: usuario["email"]
    return conexao


def criar_tabela():
    with conectar() as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                perfil TEXT NOT NULL DEFAULT 'usuario'  -- 'usuario' ou 'admin'
            )
        """)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS denuncias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id), -- quem denunciou
                descricao TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'aberta',  -- aberta, em_andamento, resolvida
                resposta TEXT,                          -- preenchida pelo admin
                criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizada_em TEXT
            )
        """)


def login_obrigatorio(rota):
    """Decorator: colocado em cima de uma rota, bloqueia quem não está logado."""
    @wraps(rota)
    def verificar(*args, **kwargs):
        if "usuario_id" not in session:
            return jsonify(erro="Você precisa estar logado."), 401
        return rota(*args, **kwargs)
    return verificar


def eh_admin():
    with conectar() as conexao:
        usuario = conexao.execute(
            "SELECT perfil FROM usuarios WHERE id = ?", (session.get("usuario_id"),)
        ).fetchone()
    return usuario is not None and usuario["perfil"] == "admin"


def admin_obrigatorio(rota):
    """Decorator: só deixa passar quem está logado E tem perfil admin."""
    @wraps(rota)
    def verificar(*args, **kwargs):
        if "usuario_id" not in session:
            return jsonify(erro="Você precisa estar logado."), 401
        if not eh_admin():
            # 401 = não sei quem você é. 403 = sei quem você é, mas você não pode.
            return jsonify(erro="Apenas administradores podem fazer isso."), 403
        return rota(*args, **kwargs)
    return verificar


@app.get("/")
def inicio():
    return app.send_static_file("index.html")


@app.post("/api/cadastro")
def cadastro():
    dados = request.get_json()
    nome = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    # Validação no backend: o front pode ser burlado, o back não.
    if not nome or not email or len(senha) < 6:
        return jsonify(erro="Preencha nome, e-mail e senha (mínimo 6 caracteres)."), 400

    # Nunca salvamos a senha! Salvamos só o "hash" dela.
    senha_hash = generate_password_hash(senha)

    try:
        with conectar() as conexao:
            conexao.execute(
                "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
                (nome, email, senha_hash),
            )
    except sqlite3.IntegrityError:  # o UNIQUE do e-mail barrou
        return jsonify(erro="Este e-mail já está cadastrado."), 409

    return jsonify(mensagem="Cadastro realizado! Agora faça login."), 201


@app.post("/api/login")
def login():
    dados = request.get_json()
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    with conectar() as conexao:
        usuario = conexao.execute(
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()

    # Mesma mensagem para e-mail ou senha errados: não contamos qual dos dois falhou.
    if usuario is None or not check_password_hash(usuario["senha_hash"], senha):
        return jsonify(erro="E-mail ou senha incorretos."), 401

    # Guardamos o id na sessão (um cookie assinado que o navegador manda em toda requisição).
    session["usuario_id"] = usuario["id"]
    return jsonify(mensagem=f"Bem-vindo(a), {usuario['nome']}!")


@app.get("/api/eu")
@login_obrigatorio
def eu():
    with conectar() as conexao:
        usuario = conexao.execute(
            "SELECT id, nome, email, perfil FROM usuarios WHERE id = ?", (session["usuario_id"],)
        ).fetchone()

    return jsonify(dict(usuario))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(mensagem="Você saiu.")


# ------------------------------------------------------------------ DENÚNCIAS
# Fluxo: usuário registra (com localização) -> acompanha o status -> admin responde.

STATUS_DENUNCIA = ("aberta", "em_andamento", "resolvida")

SELECT_DENUNCIA = """SELECT denuncias.*, usuarios.nome AS denunciante
                     FROM denuncias JOIN usuarios ON usuarios.id = denuncias.usuario_id"""


@app.post("/api/denuncias")
@login_obrigatorio
def registrar_denuncia():
    dados = request.get_json()
    descricao = (dados.get("descricao") or "").strip()
    try:
        latitude = float(dados.get("latitude"))
        longitude = float(dados.get("longitude"))
    except (TypeError, ValueError):  # veio vazio ou texto que não é número
        return jsonify(erro="Latitude e longitude precisam ser números."), 400

    if not descricao:
        return jsonify(erro="Descreva o problema."), 400
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return jsonify(erro="Localização inválida."), 400

    with conectar() as conexao:
        cursor = conexao.execute(
            "INSERT INTO denuncias (usuario_id, descricao, latitude, longitude) VALUES (?, ?, ?, ?)",
            (session["usuario_id"], descricao, latitude, longitude),
        )
        denuncia = conexao.execute(SELECT_DENUNCIA + " WHERE denuncias.id = ?", (cursor.lastrowid,)).fetchone()

    return jsonify(dict(denuncia)), 201


@app.get("/api/denuncias")
@login_obrigatorio
def listar_denuncias():
    sql = SELECT_DENUNCIA + " WHERE 1 = 1"
    parametros = []

    # Usuário comum só vê as PRÓPRIAS denúncias. Admin vê todas.
    if not eh_admin():
        sql += " AND denuncias.usuario_id = ?"
        parametros.append(session["usuario_id"])

    status = request.args.get("status")
    if status:
        sql += " AND denuncias.status = ?"
        parametros.append(status)

    with conectar() as conexao:
        denuncias = conexao.execute(sql + " ORDER BY denuncias.id DESC", parametros).fetchall()

    return jsonify([dict(d) for d in denuncias])


@app.get("/api/denuncias/<int:denuncia_id>")
@login_obrigatorio
def detalhar_denuncia(denuncia_id):
    with conectar() as conexao:
        denuncia = conexao.execute(SELECT_DENUNCIA + " WHERE denuncias.id = ?", (denuncia_id,)).fetchone()

    # Denúncia de outra pessoa responde 404 (e não 403) para não revelar que ela existe.
    if denuncia is None or (denuncia["usuario_id"] != session["usuario_id"] and not eh_admin()):
        return jsonify(erro="Denúncia não encontrada."), 404
    return jsonify(dict(denuncia))


@app.patch("/api/denuncias/<int:denuncia_id>")
@admin_obrigatorio
def responder_denuncia(denuncia_id):
    # PATCH = altera só alguns campos (aqui: status e resposta). PUT substituiria tudo.
    dados = request.get_json()
    status = dados.get("status")
    resposta = (dados.get("resposta") or "").strip() or None

    if status not in STATUS_DENUNCIA:
        return jsonify(erro=f"Status deve ser um destes: {', '.join(STATUS_DENUNCIA)}."), 400

    with conectar() as conexao:
        cursor = conexao.execute(
            """UPDATE denuncias SET status = ?, resposta = COALESCE(?, resposta),
               atualizada_em = CURRENT_TIMESTAMP WHERE id = ?""",
            (status, resposta, denuncia_id),
        )
        if cursor.rowcount == 0:
            return jsonify(erro="Denúncia não encontrada."), 404
        denuncia = conexao.execute(SELECT_DENUNCIA + " WHERE denuncias.id = ?", (denuncia_id,)).fetchone()

    return jsonify(dict(denuncia))


@app.get("/api/denuncias/resumo")
def resumo_denuncias():
    # Público: quantas denúncias em cada status. Base para relatórios e o "reciclômetro".
    with conectar() as conexao:
        linhas = conexao.execute(
            "SELECT status, COUNT(*) AS total FROM denuncias GROUP BY status"
        ).fetchall()

    resumo = {status: 0 for status in STATUS_DENUNCIA}
    resumo.update({linha["status"]: linha["total"] for linha in linhas})
    resumo["total"] = sum(resumo.values())
    return jsonify(resumo)


# ------------------------------------------------------------------ USUÁRIOS (admin)


@app.get("/api/usuarios")
@admin_obrigatorio
def listar_usuarios():
    # Nunca devolva a senha_hash! Escolha as colunas em vez de usar SELECT *.
    with conectar() as conexao:
        usuarios = conexao.execute("SELECT id, nome, email, perfil FROM usuarios ORDER BY id").fetchall()
    return jsonify([dict(u) for u in usuarios])


@app.patch("/api/usuarios/<int:usuario_id>")
@admin_obrigatorio
def mudar_perfil(usuario_id):
    perfil = request.get_json().get("perfil")

    if perfil not in ("usuario", "admin"):
        return jsonify(erro="Perfil deve ser 'usuario' ou 'admin'."), 400
    if usuario_id == session["usuario_id"]:
        # Evita o admin tirar o próprio acesso e o sistema ficar sem nenhum admin.
        return jsonify(erro="Você não pode mudar o seu próprio perfil."), 400

    with conectar() as conexao:
        cursor = conexao.execute("UPDATE usuarios SET perfil = ? WHERE id = ?", (perfil, usuario_id))
        if cursor.rowcount == 0:
            return jsonify(erro="Usuário não encontrado."), 404
        usuario = conexao.execute(
            "SELECT id, nome, email, perfil FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()

    return jsonify(dict(usuario))


def criar_admin_inicial():
    """Todo sistema precisa de um primeiro admin. Ele é criado ao iniciar, se ainda não existir.
    Na vida real, e-mail e senha vêm de variáveis de ambiente, nunca escritos no código."""
    email = os.environ.get("ADMIN_EMAIL", "admin@ecodescarte.com")
    senha = os.environ.get("ADMIN_SENHA", "admin123")
    with conectar() as conexao:
        conexao.execute(
            # OR IGNORE: se o e-mail já existe (UNIQUE), não faz nada
            "INSERT OR IGNORE INTO usuarios (nome, email, senha_hash, perfil) VALUES (?, ?, ?, 'admin')",
            ("Administrador", email, generate_password_hash(senha)),
        )


criar_tabela()
criar_admin_inicial()

if __name__ == "__main__":
    app.run(debug=True)

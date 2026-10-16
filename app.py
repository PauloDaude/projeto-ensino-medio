import sqlite3

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
                senha_hash TEXT NOT NULL
            )
        """)


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
def eu():
    usuario_id = session.get("usuario_id")
    if usuario_id is None:
        return jsonify(erro="Você não está logado."), 401

    with conectar() as conexao:
        usuario = conexao.execute(
            "SELECT id, nome, email FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()

    return jsonify(dict(usuario))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(mensagem="Você saiu.")


criar_tabela()

if __name__ == "__main__":
    app.run(debug=True)

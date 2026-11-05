# Teste rápido de todo o fluxo. Rode com: python teste.py
import os
import tempfile

import app as aplicacao

aplicacao.BANCO = os.path.join(tempfile.mkdtemp(), "teste.db")
aplicacao.criar_tabela()
aplicacao.criar_admin_inicial()
cliente = aplicacao.app.test_client()

usuario = {"nome": "Ana", "email": "ana@email.com", "senha": "123456"}

assert cliente.post("/api/cadastro", json=usuario).status_code == 201
assert cliente.post("/api/cadastro", json=usuario).status_code == 409  # e-mail repetido
assert cliente.post("/api/cadastro", json={**usuario, "email": "b@b.com", "senha": "123"}).status_code == 400
assert cliente.get("/api/eu").status_code == 401  # ainda não logou
assert cliente.post("/api/login", json={**usuario, "senha": "errada"}).status_code == 401
assert cliente.post("/api/login", json=usuario).status_code == 200
assert cliente.get("/api/eu").get_json()["nome"] == "Ana"

# ---- Denúncias: Ana (usuária comum) registra
denuncia = {"descricao": "Entulho jogado no terreno", "latitude": -10.17, "longitude": -48.88}
assert cliente.post("/api/denuncias", json={**denuncia, "latitude": "abc"}).status_code == 400
assert cliente.post("/api/denuncias", json={**denuncia, "latitude": 200}).status_code == 400
criada = cliente.post("/api/denuncias", json=denuncia).get_json()
assert criada["status"] == "aberta" and criada["denunciante"] == "Ana"
assert cliente.patch(f"/api/denuncias/{criada['id']}", json={"status": "resolvida"}).status_code == 403  # não é admin

# Admin (outro navegador = outro cliente) responde
admin = aplicacao.app.test_client()
assert admin.post("/api/login", json={"email": "admin@ecodescarte.com", "senha": "admin123"}).status_code == 200
admin.post("/api/denuncias", json={**denuncia, "descricao": "Pneus na beira do rio"})
assert len(admin.get("/api/denuncias").get_json()) == 2  # admin vê todas
assert len(cliente.get("/api/denuncias").get_json()) == 1  # Ana só vê a dela
assert cliente.get("/api/denuncias/2").status_code == 404  # e não acessa a do admin

assert admin.patch(f"/api/denuncias/{criada['id']}", json={"status": "voando"}).status_code == 400
assert admin.patch("/api/denuncias/999", json={"status": "resolvida"}).status_code == 404
respondida = admin.patch(f"/api/denuncias/{criada['id']}",
                         json={"status": "em_andamento", "resposta": "Equipe a caminho"}).get_json()
assert respondida["status"] == "em_andamento" and respondida["atualizada_em"]

# Ana acompanha o status
assert cliente.get(f"/api/denuncias/{criada['id']}").get_json()["resposta"] == "Equipe a caminho"
assert len(cliente.get("/api/denuncias?status=resolvida").get_json()) == 0

# Resumo é público
assert aplicacao.app.test_client().get("/api/denuncias/resumo").get_json() == \
    {"aberta": 1, "em_andamento": 1, "resolvida": 0, "total": 2}

# ---- Usuários: só admin lista e muda perfil
assert cliente.get("/api/usuarios").status_code == 403  # Ana não é admin
usuarios = admin.get("/api/usuarios").get_json()
assert all("senha_hash" not in u for u in usuarios)  # senha nunca sai da API
ana = next(u for u in usuarios if u["email"] == "ana@email.com")
eu_admin = admin.get("/api/eu").get_json()
assert admin.patch(f"/api/usuarios/{ana['id']}", json={"perfil": "chefe"}).status_code == 400
assert admin.patch(f"/api/usuarios/{eu_admin['id']}", json={"perfil": "usuario"}).status_code == 400
assert admin.patch("/api/usuarios/999", json={"perfil": "admin"}).status_code == 404
assert admin.patch(f"/api/usuarios/{ana['id']}", json={"perfil": "admin"}).get_json()["perfil"] == "admin"
assert len(cliente.get("/api/denuncias").get_json()) == 2  # agora Ana vê todas

cliente.post("/api/logout")
assert cliente.get("/api/eu").status_code == 401
assert cliente.post("/api/denuncias", json=denuncia).status_code == 401

print("Tudo funcionando!")

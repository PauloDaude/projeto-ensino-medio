# Teste rápido de todo o fluxo. Rode com: python teste.py
import os
import tempfile

import app as aplicacao

aplicacao.BANCO = os.path.join(tempfile.mkdtemp(), "teste.db")
aplicacao.criar_tabela()
cliente = aplicacao.app.test_client()

usuario = {"nome": "Ana", "email": "ana@email.com", "senha": "123456"}

assert cliente.post("/api/cadastro", json=usuario).status_code == 201
assert cliente.post("/api/cadastro", json=usuario).status_code == 409  # e-mail repetido
assert cliente.post("/api/cadastro", json={**usuario, "email": "b@b.com", "senha": "123"}).status_code == 400
assert cliente.get("/api/eu").status_code == 401  # ainda não logou
assert cliente.post("/api/login", json={**usuario, "senha": "errada"}).status_code == 401
assert cliente.post("/api/login", json=usuario).status_code == 200
assert cliente.get("/api/eu").get_json()["nome"] == "Ana"
cliente.post("/api/logout")
assert cliente.get("/api/eu").status_code == 401

print("Tudo funcionando!")

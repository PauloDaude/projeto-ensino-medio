# EcoDescarte — Cadastro e Login (Python + Flask)

Projeto de exemplo: frontend em HTML/JS conversando com um backend em Python.

## Como rodar

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000 no navegador.

Para testar tudo de uma vez: `python teste.py`

## Arquivos

| Arquivo | O que faz |
|---|---|
| `app.py` | Backend: rotas da API e banco de dados |
| `static/index.html` | Telas de cadastro e login |
| `static/painel.html` | Página que só quem está logado vê |
| `static/estilo.css` | Visual |
| `banco.db` | Banco SQLite (criado sozinho ao rodar) |

## Rotas da API

| Método | Rota | O que faz | Respostas |
|---|---|---|---|
| POST | `/api/cadastro` | Cria usuário | 201 ok, 400 dados inválidos, 409 e-mail repetido |
| POST | `/api/login` | Faz login | 200 ok, 401 e-mail/senha errados |
| GET | `/api/eu` | Diz quem está logado | 200 ok, 401 não logado |
| POST | `/api/logout` | Sai | 200 ok |

## Roteiro da aula 1 (1 hora)

1. **Demonstração (10 min)** — Rodar o projeto, cadastrar, logar, ver o painel, sair.
   Tentar cadastrar o mesmo e-mail duas vezes e errar a senha para mostrar os erros.
2. **O caminho de um cadastro (15 min)** — Abrir o DevTools (F12 → aba Rede/Network),
   cadastrar de novo e mostrar a requisição: o JSON que vai e o que volta.
   Depois seguir o caminho no código: `index.html` (fetch) → `app.py` (`cadastro`) → banco.
3. **Por que não salvamos a senha (10 min)** — Abrir o `banco.db`
   (ex: https://sqliteviewer.app) e mostrar a coluna `senha_hash`.
   Explicar: se o banco vazar, ninguém descobre a senha.
4. **Como o site "lembra" que você está logado (10 min)** — Sessão/cookie:
   F12 → Application → Cookies. Apagar o cookie e recarregar o painel.
5. **Mão na massa (15 min)** — Desafios abaixo.

## Desafios

- Fácil: mudar a mensagem de boas-vindas do painel.
- Médio: adicionar o campo "cidade" no cadastro (HTML + `app.py` + tabela).
  Dica: apague o `banco.db` depois de mudar a tabela.
- Difícil: impedir cadastro de e-mail sem `@` no backend (não só no HTML).

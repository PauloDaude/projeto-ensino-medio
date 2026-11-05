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
| `static/denuncias.html` | Registrar, acompanhar e responder denúncias |
| `static/estilo.css` | Visual |
| `banco.db` | Banco SQLite (criado sozinho ao rodar) |
| `teste.py` | Testa todo o fluxo: `python teste.py` |
| `EcoDescarte.postman_collection.json` | Rotas para importar no Postman |
| `arquitetura.excalidraw` | Diagrama da aula 1: frontend, API, banco e login |
| `denuncias.excalidraw` | Diagrama da aula 2: perfis, tabelas, status e relatório |

Os `.excalidraw` abrem em https://excalidraw.com (menu → Abrir).

## Rotas da API

| Método | Rota | O que faz | Respostas |
|---|---|---|---|
| POST | `/api/cadastro` | Cria usuário | 201 ok, 400 dados inválidos, 409 e-mail repetido |
| POST | `/api/login` | Faz login | 200 ok, 401 e-mail/senha errados |
| GET | `/api/eu` | Diz quem está logado | 200 ok, 401 não logado |
| POST | `/api/logout` | Sai | 200 ok |
| POST | `/api/denuncias` | Registra denúncia com localização (logado) | 201, 400, 401 |
| GET | `/api/denuncias?status=aberta` | Lista: usuário vê as suas, admin vê todas | 200, 401 |
| GET | `/api/denuncias/<id>` | Detalhes / acompanhar status | 200, 401, 404 |
| PATCH | `/api/denuncias/<id>` | Admin muda status e responde | 200, 400, 401, 403, 404 |
| GET | `/api/denuncias/resumo` | Total por status (público) | 200 |
| GET | `/api/usuarios` | Lista usuários (só admin, sem a senha) | 200, 401, 403 |
| PATCH | `/api/usuarios/<id>` | Admin muda o perfil de alguém | 200, 400, 401, 403, 404 |

### Admin

Ao iniciar, o sistema cria um **admin inicial** (se ainda não existir):

- e-mail: `admin@ecodescarte.com`
- senha: `admin123`

Na vida real esses valores vêm de variáveis de ambiente (`ADMIN_EMAIL` e `ADMIN_SENHA`), nunca do código.

Para promover outra pessoa: faça login como admin, descubra o `id` dela em `GET /api/usuarios` e envie
`PATCH /api/usuarios/<id>` com `{"perfil": "admin"}`. A collection do Postman tem a pasta "Usuários (admin)".

> Mudou uma tabela no `app.py`? Apague o `banco.db` e rode de novo: o `CREATE TABLE IF NOT EXISTS`
> não altera tabela que já existe.

## Aula 2: Denúncias (exemplo base)

Exemplo pequeno de propósito. A ideia é entender, copiar o padrão e adaptar para o seu projeto.

### O que tem de novo

| Conceito | Onde ver no `app.py` |
|---|---|
| Perfis de acesso (usuário x admin) | coluna `perfil`, `admin_obrigatorio` |
| 401 x 403 | `admin_obrigatorio` |
| Decorator (`@login_obrigatorio`) para não repetir a checagem de login | `login_obrigatorio` |
| Registro ligado ao usuário logado (chave estrangeira) | `usuario_id REFERENCES usuarios(id)` |
| Geolocalização (latitude/longitude) | `registrar_denuncia` + botão 📍 em `static/denuncias.html` |
| Cada usuário só vê o que é dele | `listar_denuncias`, `detalhar_denuncia` |
| Status que muda com o tempo + PATCH | `responder_denuncia` |
| `JOIN` (trazer o nome de quem denunciou) | `SELECT_DENUNCIA` |
| Filtro pela URL (`?status=aberta`) | `listar_denuncias` |
| `COUNT` + `GROUP BY` (relatório) | `resumo_denuncias` |
| Primeiro admin criado ao iniciar + variáveis de ambiente | `criar_admin_inicial` |
| Nunca devolver a senha na API (escolher colunas no `SELECT`) | `listar_usuarios` |
| Regra de negócio: admin não muda o próprio perfil | `mudar_perfil` |

### Como isso vira o seu projeto

| Exemplo | Green Flames (bombeiros) | EcoDescarte |
|---|---|---|
| Registrar denúncia com localização | Registrar denúncia de foco de incêndio | Cadastrar local de coleta |
| Admin responde / muda status | Responder denúncia | Admin aprova/desativa local de coleta |
| Usuário acompanha o status | Acompanhar status da denúncia | Histórico de descartes |
| Resumo com `COUNT/GROUP BY` | Relatório de denúncias | Reciclômetro (`SUM` da quantidade) |
| Perfil admin | Bombeiro | Administrador (AT1) |

### Desafios

1. **Fácil:** adicionar o campo `endereco` (texto opcional) na denúncia.
2. **Médio:** criar `GET /api/denuncias?busca=entulho` procurando na descrição (dica: `LIKE`).
3. **Médio:** criar `DELETE /api/denuncias/<id>`: o dono pode apagar enquanto estiver `aberta`.
4. **Difícil:** mostrar todas as denúncias num mapa com a biblioteca [Leaflet](https://leafletjs.com).
5. **Seu projeto:** copiar o padrão para a entidade principal do seu sistema
   (foco de incêndio, local de coleta, registro de descarte...).

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

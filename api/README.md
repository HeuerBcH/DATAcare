# API — DATAcare

Separação de responsabilidades entre **backend** (Django) e **frontend** (React).

## Por que `templates/`, `static/` e `media/` ficam no backend?

São convenções do **Django**, não do React:

| Pasta (backend) | Função |
|-----------------|--------|
| `templates/` | HTML renderizado no servidor (views MVT em `apps/*/views.py`) |
| `static/` | CSS/JS do admin Django e páginas MVT; `collectstatic` gera `staticfiles/` |
| `media/` | Uploads persistidos no servidor (ex.: `profile_image` no model `User`) |

O frontend React **não lê** essas pastas. Ele usa `public/`, `src/assets/`, `src/pages/` (componentes `.tsx`) e consome apenas a **API REST** (`/api/v1/`).

Arquitetura atual: **API + SPA** (React) com **páginas MVT legadas** ainda registradas em `config/urls.py` (`users/`, `patients/`, `predictions/`). As pastas do backend permanecem corretas enquanto essas rotas ou o admin existirem.

## Backend (`api/backend/`)

```
api/backend/
├── apps/           # users, patients, predictions, api (DRF)
├── config/         # settings, urls, wsgi
├── templates/      # HTML MVT
├── static/         # arquivos estáticos do Django
├── media/          # uploads
└── requirements.txt
```

## Frontend (`api/frontend/`)

```
api/frontend/
├── public/         # arquivos servidos pelo Vite sem processamento
├── src/
│   ├── assets/     # imagens/fontes importadas no código
│   ├── components/
│   ├── hooks/
│   ├── pages/      # telas React (não são templates Django)
│   ├── services/   # cliente HTTP (axios)
│   ├── styles/
│   ├── types/
│   └── utils/
└── package.json
```

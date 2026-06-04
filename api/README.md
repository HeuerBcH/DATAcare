# API — DATAcare

## Backend (`api/backend/`)

API REST Django + DRF + JWT. **Não serve interface web** (exceto `/admin/`).

| Pasta | Uso |
|-------|-----|
| `apps/api/` | Endpoints REST (`/api/v1/`) |
| `apps/users/` | Autenticação JWT (`/api/v1/auth/`) |
| `static/` / `media/` | Admin Django e uploads (`profile_image`) |
| `templates/` | Removido — UI migrada para React |

## Frontend (`api/frontend/`)

**Interface principal** do sistema (React + Vite + React Router).

| Pasta | Uso |
|-------|-----|
| `public/` | Arquivos estáticos do Vite |
| `src/pages/` | Telas (login, pacientes, predições, etc.) |
| `src/services/` | Cliente HTTP para a API |
| `src/contexts/` | Estado global (autenticação) |

```powershell
cd api\frontend
npm install
npm run dev
```

API em `http://localhost:8000` — configure `VITE_API_URL` no `.env` da raiz do projeto.

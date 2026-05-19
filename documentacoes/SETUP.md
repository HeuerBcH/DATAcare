# Data Care - Setup Guia Rápido

## 📋 Pré-requisitos

- **Python 3.11+** (`python --version`)
- **Node.js 18+** (`node --version`)
- **PostgreSQL 15+** (`psql --version`)
- **Git** (`git --version`)
- **Docker & Docker Compose** (opcional, mas recomendado)

---

## 🚀 Quick Start (Com Docker)

```bash
# 1. Clonar
git clone https://github.com/seu-usuario/data-care.git
cd data-care

# 2. Rodar
docker-compose up

# 3. Acessar
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

---

## 🛠️ Setup Manual (FastAPI + React)

### Backend (FastAPI)

```bash
# Criar venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Configurar .env
cp .env.example .env

# Criar BD
createdb data_care
cd backend && alembic upgrade head && cd ..

# Rodar
uvicorn app.main:app --reload --port 8000
```

**Backend:** http://localhost:8000  
**Swagger:** http://localhost:8000/docs

---

### Frontend (React + Vite)

```bash
# Entrar na pasta
cd frontend

# Instalar dependências
npm install

# Configurar .env
cp .env.example .env

# Rodar
npm run dev
```

**Frontend:** http://localhost:3000

---

## 🧪 Testes

### Backend
```bash
pytest tests/ -v
pytest --cov=app tests/
```

### Frontend
```bash
cd frontend
npm test
npm test -- --coverage
```

---

## 🔧 Comandos Úteis

### Backend
```bash
uvicorn app.main:app --reload              # Desenvolvimento
pytest tests/ -v                           # Testes
alembic revision --autogenerate -m "msg"   # Nova migration
alembic upgrade head                       # Aplicar migrations
black app/ && isort app/                   # Format
flake8 app/                                # Lint
```

### Frontend
```bash
npm run dev              # Desenvolvimento
npm run build            # Build produção
npm run preview          # Preview build
npm test                 # Testes
npm run format           # Format
npm run lint:fix         # Lint fix
```

### Docker
```bash
docker-compose up           # Rodar
docker-compose up -d        # Background
docker-compose logs -f      # Logs
docker-compose down         # Parar
docker-compose down -v      # Parar + remover volumes
```

---

## 📊 Verificar se Funciona

```bash
# Backend
curl http://localhost:8000/docs

# Frontend
curl http://localhost:3000

# BD
psql -U app_user -d data_care
\dt
```

---

## 🗄️ Estrutura

```
data-care/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── routes/
│   │   └── services/
│   ├── tests/
│   ├── alembic/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── services/
│   └── package.json
│
├── ml/
│   ├── training/
│   ├── models/
│   └── requirements-dev-ml.txt
│
├── docker-compose.yml
├── .gitignore
├── .env.example
└── README.md
```

---

## 🐛 Troubleshooting

### Port já em uso
```bash
lsof -i :8000  # Encontrar
uvicorn app.main:app --port 8001  # Outra porta
```

### BD não conecta
```bash
psql -U postgres  # Testar conexão
# Se não tiver: brew install postgresql (macOS)
```

### Frontend não conecta API
```bash
# Verificar backend
curl http://localhost:8000/docs

# Verificar frontend/.env
cat frontend/.env
# VITE_API_URL deve ser http://localhost:8000
```

---

## ✅ Checklist

- [ ] Python 3.11+ instalado
- [ ] Node.js 18+ instalado  
- [ ] PostgreSQL instalado
- [ ] Backend rodando (http://localhost:8000)
- [ ] Frontend rodando (http://localhost:3000)
- [ ] API Docs acessível

---

**Pronto! Comece pelas Histórias de Usuário!** 🚀
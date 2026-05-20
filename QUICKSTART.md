# 🚀 Quick Start - DATAcare Django MVT

## 1️⃣ Setup Inicial (< 5 minutos)

### Windows PowerShell

```powershell
# Clone o repositório
git clone https://github.com/seu-usuario/DATAcare.git
cd DATAcare

# Execute o script de setup
.\scripts\setup.ps1
```

Este script vai:
- ✓ Instalar dependências Node.js
- ✓ Criar ambiente virtual Python
- ✓ Instalar pacotes Django/ML
- ✓ Executar migrations do banco

## 2️⃣ Criar Superuser (Admin)

```powershell
# Ativar ambiente Python
.\.venv\Scripts\Activate.ps1

# Criar usuário admin
cd backend
python manage.py createsuperuser

# Informe: username, email, senha
```

## 3️⃣ Rodar o Projeto

### Terminal 1 - Backend Django

```powershell
# Ativar env
.\.venv\Scripts\Activate.ps1

# Entrar na pasta backend
cd backend

# Rodar servidor
python manage.py runserver 0.0.0.0:8000
```

**URL:** http://localhost:8000

### Terminal 2 - Frontend React

```powershell
# Voltar para a raiz
cd ..

# Rodar frontend
npm run dev
```

**URL:** http://localhost:3000 ou http://localhost:5173

## 4️⃣ Acessar Interfaces

| Interface | URL | Usuário | Senha |
|-----------|-----|---------|-------|
| 🏠 Frontend | http://localhost:3000 | - | - |
| 🔌 API | http://localhost:8000/api/v1/ | Token auth | - |
| 👨‍💼 Admin | http://localhost:8000/admin | admin | [sua senha] |
| 📚 API Swagger | http://localhost:8000/api/schema/ | - | - |

## 5️⃣ Primeiros Passos

### A. Registrar novo usuário

1. Acesse **http://localhost:3000**
2. Clique em "Registrar"
3. Preencha: usuário, email, senha, nome

### B. Criar perfil de paciente

1. Após registrar, acesse **Meu Perfil**
2. Complete informações: CPF, data de nascimento, etc.

### C. Registrar sinais vitais

1. Vá para **Sinais Vitais**
2. Registre: pressão, frequência cardíaca, temperatura, etc.

### D. Gerar predição ML

1. Clique em **Nova Predição**
2. Selecione o modelo
3. Veja o resultado do risco

## 6️⃣ API REST - Primeiras Requisições

### Registrar Usuário

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "usuario1",
    "email": "user@example.com",
    "password": "senha123",
    "password_confirm": "senha123",
    "first_name": "João",
    "last_name": "Silva"
  }'
```

### Listar Predições

```bash
curl http://localhost:8000/api/v1/predictions/ \
  -H "Authorization: Token seu_token"
```

### Registrar Sinais Vitais

```bash
curl -X POST http://localhost:8000/api/v1/patients/1/vitals/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token seu_token" \
  -d '{
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 80,
    "heart_rate": 72,
    "temperature": 36.5,
    "weight": 75,
    "height": 180,
    "blood_glucose": 100
  }'
```

## 7️⃣ Estrutura de Arquivos

```
DATAcare/
├── backend/                 # Django backend
│   ├── config/             # Configurações
│   ├── apps/               # Aplicações
│   │   ├── users/          # Autenticação
│   │   ├── patients/       # Pacientes
│   │   ├── predictions/    # Predições
│   │   └── api/            # REST API
│   ├── templates/          # HTML templates
│   └── manage.py
├── src/                    # Frontend React
├── data_pipeline/          # ML & ETL
├── requirements.txt        # Dependências Python
├── package.json            # Dependências Node.js
└── docker-compose.yaml     # Docker setup
```

## 8️⃣ Comandos Úteis

### Django

```powershell
# Migrations
python manage.py makemigrations   # Criar migrations
python manage.py migrate          # Aplicar migrations

# Admin
python manage.py createsuperuser  # Criar admin
python manage.py changepassword    # Mudar senha

# Desenvolvimento
python manage.py runserver         # Rodar locally
python manage.py shell             # Django shell

# Produção
python manage.py collectstatic --noinput  # Coletar static
python manage.py check --deploy           # Verificar produção
```

### Frontend

```bash
npm run dev        # Desenvolvimento
npm run build      # Build produção
npm run preview    # Preview build
npm test           # Rodar testes
npm run lint       # Lint
npm run format     # Format código
```

### Docker

```bash
docker-compose build        # Build imagens
docker-compose up          # Rodar containers
docker-compose up -d       # Rodar em background
docker-compose logs -f     # Ver logs
docker-compose down        # Parar containers
docker-compose down -v     # Parar e limpar volumes
```

## 9️⃣ Troubleshooting

### ❌ Erro: "ModuleNotFoundError: No module named 'django'"

```powershell
pip install -r requirements.txt
```

### ❌ Erro: "No such table: auth_user"

```powershell
cd backend
python manage.py migrate
```

### ❌ Erro: CORS / "Access-Control-Allow-Origin"

Verifique `.env`:
```
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### ❌ Erro: "psycopg2 not found"

```powershell
pip install psycopg2-binary
```

### ❌ Erro: Porta 8000 já em uso

```powershell
python manage.py runserver 0.0.0.0:8001
```

## 🔟 Próximas Etapas

1. [ ] Ler [SETUP.md](../documentacoes/SETUP.md) - Setup completo
2. [ ] Ler [DJANGO_MVT_MIGRATION.md](../documentacoes/DJANGO_MVT_MIGRATION.md) - Detalhes migração
3. [ ] Ler [backend/README.md](../backend/README.md) - Documentação backend
4. [ ] Explorar API em http://localhost:8000/api/v1/
5. [ ] Entenderos models em `backend/apps/*/models.py`
6. [ ] Adicionar lógica de ML customizada

## 📚 Documentação Completa

- **Setup Detalhado:** [SETUP.md](../documentacoes/SETUP.md)
- **Migração de FastAPI:** [DJANGO_MVT_MIGRATION.md](../documentacoes/DJANGO_MVT_MIGRATION.md)
- **Backend Django:** [backend/README.md](../backend/README.md)
- **API REST:** [backend/API.md](../backend/API.md) (em breve)

## 💬 Suporte

Em caso de dúvidas:
1. Consulte a documentação
2. Verifique os logs: `logs/django.log`
3. Use o Django shell: `python manage.py shell`
4. Veja o admin: http://localhost:8000/admin

## 🎉 Pronto!

Sua aplicação DATAcare está rodando! 

- 🏠 Frontend: http://localhost:3000
- 🔌 Backend: http://localhost:8000
- 👨‍💼 Admin: http://localhost:8000/admin

**Aproveite! 🚀**

---

_DATAcare — CESAR School, Projeto 6, Grupo 13_

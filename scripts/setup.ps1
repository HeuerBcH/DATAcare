# Setup local - Windows PowerShell
# Use: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> DATAcare Setup" -ForegroundColor Cyan
Write-Host "Installing Node.js and Python dependencies..." -ForegroundColor Yellow

# Node.js Frontend Setup
Write-Host ""
Write-Host "==> Node.js (Frontend)" -ForegroundColor Cyan
npm install

# Environment file
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "OK - .env created" -ForegroundColor Green
}

# Python Virtual Environment Setup
Write-Host ""
Write-Host "==> Python 3.12 (Backend + ML)" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
  py -3.12 -m venv .venv
  Write-Host "OK - Virtual environment created" -ForegroundColor Green
}

# Upgrade pip and install dependencies
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt

# Django Setup
Write-Host ""
Write-Host "==> Django Backend Setup" -ForegroundColor Cyan

# Create logs directory
if (-not (Test-Path "logs")) {
  New-Item -ItemType Directory -Path "logs" -Force | Out-Null
  Write-Host "OK - logs directory created" -ForegroundColor Green
}

# Get into backend directory
Set-Location $Root/backend

# Run migrations
Write-Host "Running migrations..." -ForegroundColor Yellow
.\..\venv\Scripts\python.exe manage.py migrate

# Create superuser (manual step)
Write-Host ""
Write-Host "==> Create Superuser" -ForegroundColor Cyan
Write-Host "Run the command to create admin user:" -ForegroundColor Yellow
Write-Host ".\..\venv\Scripts\python.exe manage.py createsuperuser" -ForegroundColor Magenta

# Collect static files
Write-Host ""
Write-Host "Collecting static files..." -ForegroundColor Yellow
.\..\venv\Scripts\python.exe manage.py collectstatic --noinput

Set-Location $Root

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Activate Python environment:"
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Magenta
Write-Host ""
Write-Host "2. Create admin user (in backend folder):"
Write-Host "   cd backend" -ForegroundColor Magenta
Write-Host "   ..\venv\Scripts\python.exe manage.py createsuperuser" -ForegroundColor Magenta
Write-Host ""
Write-Host "3. Start backend (in separate terminal):"
Write-Host "   cd backend" -ForegroundColor Magenta
Write-Host "   ..\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000" -ForegroundColor Magenta
Write-Host ""
Write-Host "4. Start frontend (in new terminal):"
Write-Host "   npm run dev" -ForegroundColor Magenta
Write-Host ""
Write-Host "5. Access:"
Write-Host "   Frontend: http://localhost:3000 or http://localhost:5173" -ForegroundColor Magenta
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor Magenta
Write-Host "   Admin:    http://localhost:8000/admin" -ForegroundColor Magenta
Write-Host ""

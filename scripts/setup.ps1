# Setup local — Windows PowerShell
# Uso: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> Node.js (frontend)" -ForegroundColor Cyan
npm install

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Criado .env a partir de .env.example"
}

Write-Host "==> Python 3.12 (data pipeline / ML)" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
  py -3.12 -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt

Write-Host ""
Write-Host "Setup concluido." -ForegroundColor Green
Write-Host "  Frontend:  npm run dev"
Write-Host "  Jupyter:   .\.venv\Scripts\jupyter.exe lab"
Write-Host "  Ativar venv: .\.venv\Scripts\Activate.ps1"

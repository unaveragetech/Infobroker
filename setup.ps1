# Infobroker setup (Windows PowerShell)
# Creates .venv, installs deps, copies .env.example → .env if missing.
# Usage:  powershell -ExecutionPolicy Bypass -File .\setup.ps1
# Then:   .\.venv\Scripts\Activate.ps1
#         python -m infobroker.web.app

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "==> Infobroker setup" -ForegroundColor Cyan
Write-Host "    Root: $Root"

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
  Write-Error "Python not found on PATH. Install Python 3.11+ from https://www.python.org/downloads/ and re-run."
}
$ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "    Python: $ver ($($py.Source))"

if (-not (Test-Path ".venv")) {
  Write-Host "==> Creating virtualenv (.venv)" -ForegroundColor Cyan
  python -m venv .venv
} else {
  Write-Host "==> Reusing existing .venv" -ForegroundColor DarkCyan
}

$pip = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $pip)) {
  Write-Error "Expected $pip after venv create — check Python install."
}

Write-Host "==> Upgrading pip" -ForegroundColor Cyan
& $pip -m pip install --upgrade pip

Write-Host "==> Installing requirements.txt" -ForegroundColor Cyan
Write-Host "    Note: TA-Lib may need a binary wheel on Windows (pip usually finds one)." -ForegroundColor DarkGray
& $pip -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
  if (Test-Path ".env.example") {
    Copy-Item ".env.example" ".env"
    Write-Host "==> Created .env from .env.example (edit secrets locally — never commit)" -ForegroundColor Cyan
  } else {
    Write-Warning ".env.example missing — create .env manually"
  }
} else {
  Write-Host "==> Keeping existing .env" -ForegroundColor DarkCyan
}

if (-not (Test-Path "data")) {
  New-Item -ItemType Directory -Path "data" | Out-Null
}

Write-Host ""
Write-Host "==> Setup complete" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. .\.venv\Scripts\Activate.ps1"
Write-Host "  2. (optional) ollama pull arriella-grapevine"
Write-Host "  3. python -m infobroker.web.app"
Write-Host "  4. Open http://127.0.0.1:8000/"
Write-Host ""
Write-Host "Docs: docs\README.md  |  License: LICENSE (SDUC v1.1)  |  Donate: DONATE.md"
Write-Host ""

#!/usr/bin/env bash
# Infobroker setup (macOS / Linux / Git Bash)
# Creates .venv, installs deps, copies .env.example → .env if missing.
# Usage:  bash setup.sh
# Then:   source .venv/bin/activate
#         python -m infobroker.web.app

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "==> Infobroker setup"
echo "    Root: $ROOT"

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "ERROR: Python not found. Install Python 3.11+ and re-run." >&2
  exit 1
fi

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
echo "    Python: $($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') ($($PY -c 'import sys; print(sys.executable)'))"

if [[ ! -d .venv ]]; then
  echo "==> Creating virtualenv (.venv)"
  "$PY" -m venv .venv
else
  echo "==> Reusing existing .venv"
fi

PIP="$ROOT/.venv/bin/python"
if [[ ! -x "$PIP" ]]; then
  echo "ERROR: expected $PIP after venv create" >&2
  exit 1
fi

echo "==> Upgrading pip"
"$PIP" -m pip install --upgrade pip

echo "==> Installing requirements.txt"
echo "    Note: TA-Lib may need system libs (e.g. brew install ta-lib) on some platforms."
"$PIP" -m pip install -r requirements.txt

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "==> Created .env from .env.example (edit secrets locally — never commit)"
  else
    echo "WARN: .env.example missing — create .env manually"
  fi
else
  echo "==> Keeping existing .env"
fi

mkdir -p data

echo ""
echo "==> Setup complete"
echo ""
echo "Next steps:"
echo "  1. source .venv/bin/activate"
echo "  2. (optional) ollama pull arriella-grapevine"
echo "  3. python -m infobroker.web.app"
echo "  4. Open http://127.0.0.1:8000/"
echo ""
echo "Docs: docs/README.md  |  License: LICENSE (SDUC v1.1)  |  Donate: DONATE.md"
echo ""

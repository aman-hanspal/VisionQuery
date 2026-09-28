#!/usr/bin/env bash
set -euo pipefail

# macOS, Linux and Windows WSL. Native Windows: use the README commands.
setup_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v uv >/dev/null || { echo "Install uv before running setup."; exit 1; }
command -v node >/dev/null || { echo "Install Node.js 22.12+ (or 20.19+) before running setup."; exit 1; }
node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (!((major === 20 && minor >= 19) || (major === 22 && minor >= 12) || major >= 24)) { console.error("Use Node.js 22.12+ (or 20.19+)"); process.exit(1); }'

cd "$setup_root/backend"
if [[ ! -d .venv ]]; then uv venv --python 3.12; fi
uv pip install -r requirements.txt
if [[ ! -f .env ]]; then cp .env.example .env; fi

cd "$setup_root/frontend"
npm ci
if [[ ! -f .env.local ]]; then cp .env.example .env.local; fi

cat <<'INSTRUCTIONS'
Setup complete. Configure backend/.env for your device.
For NVIDIA, verify a CUDA-enabled PyTorch build is installed before setting DEVICE=cuda.

Backend terminal:
  cd backend
  uv run --no-sync python -m uvicorn app.main:app --reload --port 8000

Frontend terminal:
  cd frontend
  npm run dev

Open http://localhost:3000
INSTRUCTIONS

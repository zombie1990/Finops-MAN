#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${PURPLE}${BOLD}"
echo "  __________________________________________________"
echo " |                                                  |"
echo " |         Φ   F I N O P T I C A   A I  Φ           |"
echo " |      Platforme SaaS IA FinOps Enterprise         |"
echo " |__________________________________________________|"
echo -e "${NC}\n"

PYTHON="${ROOT}/.venv/bin/python"
PIP="${ROOT}/.venv/bin/pip"

echo -e "${BLUE}[1/3] Environnement Python...${NC}"
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}Erreur: Python3 requis.${NC}"
  exit 1
fi
if [ ! -x "$PYTHON" ]; then
  echo "Création du venv dans ${ROOT}/.venv"
  python3 -m venv "${ROOT}/.venv"
fi
echo -e "${GREEN}✓ $("$PYTHON" --version)${NC}\n"

echo -e "${BLUE}[2/3] Dépendances backend...${NC}"
"$PIP" install -r backend/requirements.txt -q
echo -e "${GREEN}✓ Dépendances installées${NC}\n"

echo -e "${BLUE}[3/3] Démarrage Uvicorn...${NC}"
echo -e "API : ${BOLD}http://localhost:8000/api/v1${NC}"
echo -e "Docs : ${BOLD}http://localhost:8000/docs${NC}"
echo -e "UI : ${BOLD}http://localhost:8000/${NC}\n"

exec "$PYTHON" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

#!/bin/bash

# Script de démarrage rapide pour FinOptica AI
# Développé pour Mac OS (zsh/bash)

# Couleurs pour le terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
RED='\033[0;31m'
NC='\033[0;5m' # No Color
BOLD='\033[1m'

echo -e "${PURPLE}${BOLD}"
echo "  __________________________________________________"
echo " |                                                  |"
echo " |         Φ   F I N O P T I C A   A I  Φ           |"
echo " |      Platforme SaaS IA FinOps Enterprise         |"
echo " |__________________________________________________|"
echo -e "${NC}\n"

echo -e "${BLUE}[1/3] Vérification de l'environnement Python...${NC}"
if ! command -v python3 &> /dev/null
then
    echo -e "${RED}Erreur: Python3 n'est pas installé sur votre Mac.${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ Python3 est disponible : ${PYTHON_VERSION}${NC}\n"

echo -e "${BLUE}[2/3] Installation des dépendances du backend (FastAPI, Pandas, etc.)...${NC}"
echo "Exécution de : pip3 install -r backend/requirements.txt"
pip3 install -r backend/requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}Erreur lors de l'installation des dépendances.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dépendances installées avec succès !${NC}\n"

echo -e "${BLUE}[3/3] Démarrage du serveur unifié FinOptica AI...${NC}"
echo -e "L'API sera disponible sur : ${BOLD}http://localhost:8000/api/v1${NC}"
echo -e "La documentation Swagger : ${BOLD}http://localhost:8000/docs${NC}"
echo -e "L'application Web interactive : ${BOLD}http://localhost:8000/${NC}"
echo -e "\n${GREEN}${BOLD}Lancement du serveur Uvicorn...${NC}\n"

# Démarre le serveur Uvicorn
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

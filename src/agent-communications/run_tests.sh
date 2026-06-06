#!/bin/bash
# run_tests.sh - Runs pytest for the agent communications using its local virtualenv

set -e

# Terminal colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

if [ "$1" = "--all" ] || [ "$1" = "-a" ] || [ "$1" = "all" ]; then
    export RUN_FIRESTORE_TESTS="true"
fi

echo -e "${CYAN}[>>>>] Corriendo pruebas de agent-communications...${NC}"
env $(cat .env | xargs) .venv/bin/python -m pytest tests/ --tb=short

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN} ¡Pruebas de agente completadas con éxito!${NC}"
echo -e "${GREEN}========================================${NC}"

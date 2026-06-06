#!/bin/bash
# run_tests.sh - Runs pytest for the ingestion pipeline using its local virtualenv

set -e

# Terminal colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

if [ "$1" = "--all" ] || [ "$1" = "-a" ] || [ "$1" = "all" ]; then
    echo -e "${CYAN}[>>>>] Habilitando pruebas reales de Firestore...${NC}"
    export RUN_FIRESTORE_TESTS="true"
    if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
        read -p "Ingresa el ID del proyecto de GCP (default: devhack-3f0c2): " project_id
        if [ -z "$project_id" ]; then
            project_id="devhack-3f0c2"
        fi
        export GOOGLE_CLOUD_PROJECT="$project_id"
        export GCP_PROJECT_ID="$project_id"
    fi
else
    echo -e "${CYAN}[>>>>] Omitiendo pruebas reales de Firestore (usa --all o -a para incluirlas)...${NC}"
fi

echo -e "${CYAN}[>>>>] Corriendo pruebas de ingestion-pipeline...${NC}"
.venv/bin/python -m pytest tests/ --tb=short

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN} ¡Pruebas de ingesta completadas con éxito!${NC}"
echo -e "${GREEN}========================================${NC}"

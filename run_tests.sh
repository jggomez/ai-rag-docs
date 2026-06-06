#!/bin/bash
# run_tests.sh - Runs all unit and integration tests for the project

set -e

# Terminal colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

ARG=""
if [ "$1" = "--all" ] || [ "$1" = "-a" ] || [ "$1" = "all" ]; then
    ARG="--all"
    read -p "Ingresa el ID del proyecto de GCP (default: devhack-3f0c2): " project_id
    if [ -z "$project_id" ]; then
        project_id="devhack-3f0c2"
    fi
    export GOOGLE_CLOUD_PROJECT="$project_id"
    export GCP_PROJECT_ID="$project_id"
fi

# 1. Ingestion Pipeline
echo -e "${CYAN}[>>>>] Corriendo pruebas de ingestion-pipeline...${NC}"
cd src/ingestion-pipeline
./run_tests.sh $ARG

# 2. Agent Communications
echo -e "\n${CYAN}[>>>>] Corriendo pruebas de agent-communications...${NC}"
cd ../agent-communications
./run_tests.sh $ARG

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN} ¡Todas las pruebas han pasado con éxito!${NC}"
echo -e "${GREEN}========================================${NC}"

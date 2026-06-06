#!/bin/bash
# =============================================================================
# run_all.sh - Start all services for ai-doc-communications
#
# Services:
#   1. MLflow Tracking Server          → http://localhost:5001
#   2. Ingestion Pipeline (Retriever)  → http://localhost:8080
#   3. Agent Communications (ADK)      → http://localhost:8000
#   4. UI Frontend (Vite dev server)   → http://localhost:5173
#
# Usage:
#   ./run_all.sh          Start all services
#   ./run_all.sh stop     Stop all services
# =============================================================================

set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
INGESTION_DIR="${BASE_DIR}/src/ingestion-pipeline"
AGENT_DIR="${BASE_DIR}/src/agent-communications"
UI_DIR="${BASE_DIR}/src/ui-ai-comunicados"

PID_DIR="${BASE_DIR}/.pids"
export MLFLOW_TRACKING_URI="http://localhost:5001"
export ENABLE_MLFLOW="true"

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${CYAN}[>>>>]${NC} $1"; }

# ---------------------------------------------------------------------------
# Stop all services
# ---------------------------------------------------------------------------
stop_services() {
  log_step "Stopping all services..."

  if [ -d "${PID_DIR}" ]; then
    for pid_file in "${PID_DIR}"/*.pid; do
      [ -f "${pid_file}" ] || continue
      pid=$(cat "${pid_file}")
      service_name=$(basename "${pid_file}" .pid)

      if kill -0 "${pid}" 2>/dev/null; then
        # Kill the entire process group so child processes (e.g. uvicorn
        # spawned inside run_mlflow.sh) are also terminated and do not
        # linger as orphans holding their ports open.
        pgid=$(ps -o pgid= -p "${pid}" 2>/dev/null | tr -d ' ')
        if [ -n "${pgid}" ] && [ "${pgid}" != "0" ]; then
          kill -- "-${pgid}" 2>/dev/null || kill "${pid}" 2>/dev/null
        else
          kill "${pid}" 2>/dev/null
        fi
        log_info "Stopped ${service_name} (PID ${pid})"
      else
        log_warn "${service_name} (PID ${pid}) was not running"
      fi
      rm -f "${pid_file}"
    done
    rmdir "${PID_DIR}" 2>/dev/null || true
  else
    log_warn "No PID directory found. Services may not be running."
  fi

  # Fallback: release any leftover processes on the known service ports.
  # This handles orphaned children that survived the group kill above.
  for port in 5001 8080 8000 5173; do
    leftover=$(lsof -ti :"${port}" 2>/dev/null)
    if [ -n "${leftover}" ]; then
      echo "${leftover}" | xargs kill -9 2>/dev/null
      log_warn "Force-killed orphaned process(es) on port ${port}: ${leftover}"
    fi
  done

  log_info "All services stopped."
}

# ---------------------------------------------------------------------------
# Handle stop command
# ---------------------------------------------------------------------------
if [ "${1}" = "stop" ]; then
  stop_services
  exit 0
fi

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
log_step "Running pre-flight checks..."

if [ ! -d "${INGESTION_DIR}" ]; then
  log_error "Ingestion pipeline directory not found: ${INGESTION_DIR}"
  exit 1
fi

if [ ! -d "${AGENT_DIR}" ]; then
  log_error "Agent communications directory not found: ${AGENT_DIR}"
  exit 1
fi

if [ ! -d "${UI_DIR}" ]; then
  log_error "UI directory not found: ${UI_DIR}"
  exit 1
fi

# Check for uv (Python package manager)
if ! command -v uv &>/dev/null; then
  log_error "'uv' is not installed. Install it: https://docs.astral.sh/uv/"
  exit 1
fi

# Check for npm
if ! command -v npm &>/dev/null; then
  log_error "'npm' is not installed."
  exit 1
fi

log_info "All pre-flight checks passed."

# ---------------------------------------------------------------------------
# Create PID directory
# ---------------------------------------------------------------------------
mkdir -p "${PID_DIR}"

# ---------------------------------------------------------------------------
# Cleanup on exit (Ctrl+C or script termination)
# ---------------------------------------------------------------------------
cleanup() {
  echo ""
  log_step "Caught interrupt signal. Shutting down..."
  stop_services
  exit 0
}
trap cleanup INT TERM

# ---------------------------------------------------------------------------
# 1. Start MLflow Tracking Server on port 5001
# ---------------------------------------------------------------------------
log_step "Starting MLflow Tracking Server on http://localhost:5001 ..."
./run_mlflow.sh \
  > "${PID_DIR}/mlflow.log" 2>&1 &
echo $! > "${PID_DIR}/mlflow.pid"
log_info "MLflow Tracking Server started (PID $(cat ${PID_DIR}/mlflow.pid))"

# ---------------------------------------------------------------------------
# 2. Start Ingestion Pipeline (Retriever) on port 8080
# ---------------------------------------------------------------------------
log_step "Starting Ingestion Pipeline (Retriever) on http://localhost:8080 ..."
cd "${INGESTION_DIR}"
uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload \
  > "${PID_DIR}/ingestion.log" 2>&1 &
echo $! > "${PID_DIR}/ingestion.pid"
log_info "Ingestion Pipeline started (PID $(cat ${PID_DIR}/ingestion.pid))"

# ---------------------------------------------------------------------------
# 3. Start Agent Communications (ADK) on port 8000
# ---------------------------------------------------------------------------
log_step "Starting Agent Communications (ADK) on http://localhost:8000 ..."
cd "${AGENT_DIR}"
uv run python app/fast_api_app.py \
  > "${PID_DIR}/agent.log" 2>&1 &
echo $! > "${PID_DIR}/agent.pid"
log_info "Agent Communications started (PID $(cat ${PID_DIR}/agent.pid))"

# ---------------------------------------------------------------------------
# 4. Start UI Frontend (Vite) on port 5173
# ---------------------------------------------------------------------------
log_step "Starting UI Frontend (Vite) on http://localhost:5173 ..."
cd "${UI_DIR}"
npm run dev \
  > "${PID_DIR}/ui.log" 2>&1 &
echo $! > "${PID_DIR}/ui.pid"
log_info "UI Frontend started (PID $(cat ${PID_DIR}/ui.pid))"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} All services are running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  ${CYAN}MLflow Tracking${NC}        → http://localhost:5001"
echo -e "  ${CYAN}Ingestion (Retriever)${NC}  → http://localhost:8080"
echo -e "  ${CYAN}Agent (ADK)${NC}            → http://localhost:8000"
echo -e "  ${CYAN}UI Frontend${NC}            → http://localhost:5173"
echo ""
echo -e "  Logs: ${PID_DIR}/*.log"
echo -e "  Stop: ${GREEN}./run_all.sh stop${NC}  or  ${GREEN}Ctrl+C${NC}"
echo ""

# Keep the script alive to catch Ctrl+C
wait

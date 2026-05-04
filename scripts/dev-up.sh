#!/usr/bin/env bash
# ====================================================================
# Onetouch AI+MES - Start local development environment
# ====================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/infra/docker"

cd "${DOCKER_DIR}"

# Bootstrap .env from example on first run -------------------------
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[dev-up] .env created from .env.example — please review and edit secrets."
    else
        echo "[dev-up] WARNING: .env.example not found; continuing with shell environment only."
    fi
fi

echo "[dev-up] Pulling latest images..."
docker compose pull --ignore-pull-failures || true

echo "[dev-up] Starting services..."
docker compose up -d --remove-orphans

echo
echo "Services started. Endpoints:"
echo "  Frontend     : http://localhost:3000"
echo "  Backend (API): http://localhost:8000/docs"
echo "  PostgreSQL   : localhost:5432  (db=onetouch_mes user=onetouch)"
echo "  Redis        : localhost:6379"
echo "  MinIO Console: http://localhost:9001  (user=minioadmin pass=minioadmin)"
echo "  Qdrant       : http://localhost:6333/dashboard"
echo "  Kafka        : localhost:29092 (host) / kafka:9092 (internal)"
echo "  MQTT         : tcp://localhost:1883  ws://localhost:9002"
echo "  MLflow       : http://localhost:5000"
echo
echo "Tail all logs:    docker compose -f ${DOCKER_DIR}/docker-compose.yml logs -f"
echo "Stop everything:  ${SCRIPT_DIR}/dev-down.sh"

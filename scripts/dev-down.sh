#!/usr/bin/env bash
# ====================================================================
# Onetouch AI+MES - Stop local development environment
# Usage:
#   ./dev-down.sh            # stop containers, keep volumes
#   ./dev-down.sh --volumes  # stop containers AND remove volumes (DESTRUCTIVE)
# ====================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/infra/docker"

cd "${DOCKER_DIR}"

if [ "${1:-}" = "--volumes" ] || [ "${1:-}" = "-v" ]; then
    read -r -p "[dev-down] This will DELETE all data volumes (postgres, kafka, minio, ...). Continue? [y/N] " ans
    if [ "${ans}" = "y" ] || [ "${ans}" = "Y" ]; then
        docker compose down -v --remove-orphans
        echo "[dev-down] All containers and volumes removed."
    else
        echo "[dev-down] Aborted."
        exit 0
    fi
else
    docker compose down --remove-orphans
    echo "[dev-down] Containers stopped. Volumes preserved."
    echo "           Use './dev-down.sh --volumes' to also remove data."
fi

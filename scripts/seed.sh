#!/usr/bin/env bash
# ====================================================================
# Onetouch AI+MES - Seed initial master data
# Loads:
#   - Roles & default admin user
#   - Equipment master
#   - Process master
#   - Material / BOM samples
#   - Qdrant collections (inbound/outbound knowledge)
#   - MinIO buckets (cad-files, reports)
# ====================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/infra/docker"

cd "${DOCKER_DIR}"

# --- 1. Verify backend is running -----------------------------------
if ! docker compose ps backend --status running --quiet | grep -q .; then
    echo "[seed] Backend container is not running. Start it first: ./scripts/dev-up.sh"
    exit 1
fi

# --- 2. Run Alembic migrations --------------------------------------
echo "[seed] Applying database migrations..."
docker compose exec -T backend alembic upgrade head || {
    echo "[seed] WARNING: alembic migration failed or no migrations defined yet."
}

# --- 3. Run master data seed (Python script in backend) -------------
echo "[seed] Seeding master data..."
if docker compose exec -T backend test -f scripts/seed_master_data.py; then
    docker compose exec -T backend python scripts/seed_master_data.py
else
    echo "[seed] backend/scripts/seed_master_data.py not found — skipping app-level seed."
fi

# --- 4. Create MinIO buckets ----------------------------------------
echo "[seed] Ensuring MinIO buckets exist..."
docker compose exec -T minio sh -c '
    mc alias set local http://localhost:9000 "${MINIO_ROOT_USER:-minioadmin}" "${MINIO_ROOT_PASSWORD:-minioadmin}" >/dev/null 2>&1 || true
    for bucket in cad-files reports mlflow-artifacts; do
        if mc ls local/$bucket >/dev/null 2>&1; then
            echo "  - bucket already exists: $bucket"
        else
            mc mb local/$bucket && echo "  - created bucket: $bucket"
        fi
    done
' || echo "[seed] MinIO bucket setup skipped (mc client may not be present in image)."

# --- 5. Create Qdrant collections -----------------------------------
echo "[seed] Ensuring Qdrant collections exist..."
for collection in inbound_knowledge outbound_knowledge; do
    code=$(docker compose exec -T qdrant sh -c \
        "wget -q -O- --header='Content-Type: application/json' \
            --post-data='{\"vectors\":{\"size\":1536,\"distance\":\"Cosine\"}}' \
            http://localhost:6333/collections/${collection} \
            --method=PUT 2>&1 | head -c 200" || true)
    echo "  - ${collection}: ${code:-ok}"
done

echo
echo "[seed] Done."

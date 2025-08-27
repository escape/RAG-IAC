#!/usr/bin/env bash
set -euo pipefail

# Load .env if present (simple parsing)
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
fi


# Ensure Ollama model is available before proceeding
echo "[smoke] Bringing stack up..."
docker compose --env-file .env up -d

echo "[smoke] Ensuring Ollama models are available..."
# Pull embedding model for document indexing
docker compose exec ollama ollama pull "${EMBED_MODEL:-nomic-embed-text}"
# Pull LLM for text generation
docker compose exec ollama ollama pull "${GEN_MODEL:-phi3:mini}"

# Tiny sample doc
mkdir -p data/raw
if [ ! -f data/raw/_smoke.txt ]; then
  cat > data/raw/_smoke.txt <<'TXT'
This is a tiny smoke-test document.
It exists to validate the RAG pipeline (embed → index → retrieve → generate).
TXT
fi

# Wait for Weaviate to be ready from inside the Jupyter container (network context matches ingestion)
# Try up to 180s, print container status every 10s
echo "[smoke] Waiting for Weaviate readiness..."
code="000"
for i in {1..180}; do
  # ensure jupyter exists before probing (it may still be starting on fresh runs)
  docker compose --env-file .env up -d jupyter >/dev/null 2>&1 || true
  code=$(docker compose exec jupyter curl -s -o /dev/null -w "%{http_code}" http://weaviate:8080/v1/.well-known/ready || true)
  if [ "$code" = "200" ]; then
    break
  fi
  if (( i % 10 == 0 )); then
    echo "[smoke] Still waiting... ($i s) http=$code"
    docker compose --env-file .env ps weaviate || true
  fi
  sleep 1
done
if [ "$code" != "200" ]; then
  echo "[smoke] weaviate not ready (still $code). Recent logs:" >&2
  docker compose --env-file .env logs --no-color --since=5m weaviate | tail -n 120 >&2 || true
  exit 1
fi


# Always run Python inside the jupyter container (container-native style)
run_py () {
  # ensure jupyter is up (idempotent)
  docker compose --env-file .env up -d jupyter >/dev/null

  # get container id
  cid="$(docker compose ps -q jupyter)"
  if [ -z "$cid" ]; then
    echo "[smoke] 'jupyter' container not found. Is it defined in compose.yml?"
    exit 1
  fi

  # execute the script inside the container, mapping repo path /scripts -> /home/jovyan/scripts
  docker exec -it "$cid" python "/home/jovyan/scripts/$(basename "$1")" "${@:2}"
}



echo "[smoke] Ingesting sample data..."
run_py scripts/ingest.py

echo "[smoke] Querying..."
run_py scripts/rag_query.py "Summarize the sample in one short line." || true

echo "[smoke] Done. If you saw a one-line summary above, the stack is healthy."

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
for i in {1..60}; do
  code=$(docker compose exec jupyter curl -s -o /dev/null -w "%{http_code}" http://weaviate:8080/v1/.well-known/ready || true)
  [ "$code" = "200" ] && break
  sleep 1
done
[ "$code" = "200" ] || { echo "[smoke] weaviate not ready (still $code)"; exit 1; }


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

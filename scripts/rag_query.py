#!/usr/bin/env python3
import os, sys, time, requests, textwrap, json

IN_DOCKER = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "1"
OLLAMA   = "http://ollama:11434"   if IN_DOCKER else f"http://localhost:{os.getenv('OLLAMA_PORT','11434')}"
WEAVIATE = "http://weaviate:8080"  if IN_DOCKER else f"http://localhost:{os.getenv('WEAVIATE_PORT','8080')}"

EMBED_MODEL = os.getenv("EMBED_MODEL","nomic-embed-text")
GEN_MODEL   = os.getenv("GEN_MODEL","phi3:mini")
CLASS_NAME  = "DocChunk"

def wait_ready(timeout=60):
  last_err = None
  for _ in range(timeout):
    try:
      # Weaviate readiness
      r1 = requests.get(f"{WEAVIATE}/v1/.well-known/ready", timeout=2)
      r1.raise_for_status()
      # Ollama tags for liveness
      r2 = requests.get(f"{OLLAMA}/api/tags", timeout=2)
      r2.raise_for_status()
      return True
    except Exception as e:
      last_err = str(e)
      time.sleep(1)
  if last_err:
    print(json.dumps({"last_ready_error": last_err}))
  return False

def embed(text):
    # Preferred modern endpoint
    r = requests.post(f"{OLLAMA}/api/embed", json={"model": EMBED_MODEL, "input": text})
    if r.status_code == 404:
        # Fallback for older images
        r = requests.post(f"{OLLAMA}/api/embeddings", json={"model": EMBED_MODEL, "prompt": text})
    r.raise_for_status()
    # /api/embed returns {"embeddings":[...]} ; /api/embeddings returns {"embedding":[...]}
    data = r.json()
    vec = (data.get("embedding") or (data.get("embeddings") or [None])[0])
    return vec

def retrieve(q: str, top_k: int = 5):
  vec = embed(q)
  if vec is None:
    raise ValueError("Embedding returned None (empty query or model error)")
  gql = {
    "query": f"""
    {{
      Get {{
        {CLASS_NAME}(nearVector: {{vector: [{",".join(map(str, vec))}]}}, limit: {top_k}) {{
          doc_id
          chunk
        }}
      }}
    }}
    """
  }
  r = requests.post(f"{WEAVIATE}/v1/graphql", json=gql)
  r.raise_for_status()
  data = r.json().get("data", {})
  hits = (data.get("Get", {}) or {}).get(CLASS_NAME, []) or []
  return [h.get("chunk","") for h in hits if "chunk" in h]

def generate(prompt: str):
  r = requests.post(f"{OLLAMA}/api/generate", json={"model": GEN_MODEL, "prompt": prompt, "stream": False, "options": {"num_ctx": 2048}})
  r.raise_for_status()
  data = r.json()
  return (data.get("response") or "").strip()

if __name__ == "__main__":
  # Wait for services
  wait_ready(60)
  # Get question from arg or env Q, fallback to default
  q = sys.argv[1] if len(sys.argv) > 1 else os.getenv("Q", "").strip()
  q = " ".join(q.split())
  if not q:
    print(json.dumps({"error": "Empty question. Pass as: make query q='Your question'"}))
    sys.exit(2)
  try:
    ctx = retrieve(q, top_k=3)
  except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
  context_str = "\n\n".join(ctx)
  indented_context = textwrap.indent(context_str, "  ")
  prompt = (
    f"""Answer using only the context below. If missing, say you don't know.

Context:
{indented_context}

Question: {q}"""
  )
  print(generate(prompt))

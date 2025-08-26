#!/usr/bin/env python3
import os, sys, requests, textwrap

IN_DOCKER = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "1"
OLLAMA   = "http://ollama:11434"   if IN_DOCKER else f"http://localhost:{os.getenv('OLLAMA_PORT','11434')}"
WEAVIATE = "http://weaviate:8080"  if IN_DOCKER else f"http://localhost:{os.getenv('WEAVIATE_PORT','8080')}"

EMBED_MODEL = os.getenv("EMBED_MODEL","nomic-embed-text")
GEN_MODEL   = os.getenv("GEN_MODEL","phi3:mini")
CLASS_NAME  = "DocChunk"

def embed(text):
    # Preferred modern endpoint
    r = requests.post(f"{OLLAMA}/api/embed", json={"model": EMBED_MODEL, "input": text})
    if r.status_code == 404:
        # Fallback for older images
        r = requests.post(f"{OLLAMA}/api/embeddings", json={"model": EMBED_MODEL, "prompt": text})
    r.raise_for_status()
    # /api/embed returns {"embeddings":[...]} ; /api/embeddings returns {"embedding":[...]}
    data = r.json()
    return (data.get("embedding") 
            or (data.get("embeddings") or [None])[0])

def retrieve(q: str, top_k: int = 5):
    vec = embed(q)
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
  r = requests.post(f"{OLLAMA}/api/generate", json={"model": GEN_MODEL, "prompt": prompt})
  r.raise_for_status()
  print("Raw response:", r.text)
  # Ollama streams JSON objects, one per line
  responses = []
  for line in r.text.strip().splitlines():
    try:
      obj = requests.models.complexjson.loads(line)
      resp = obj.get("response")
      if resp:
        responses.append(resp)
    except Exception as e:
      print(f"Error parsing line: {line}\n{e}")
  return "".join(responses).strip()

if __name__ == "__main__":
  q = sys.argv[1] if len(sys.argv) > 1 else "What are the key points?"
  ctx = retrieve(q, top_k=1)
  context_str = "\n\n".join(ctx)
  indented_context = textwrap.indent(context_str, "  ")
  prompt = (
    f"""Answer using only the context below. If missing, say you don't know.

Context:
{indented_context}

Question: {q}"""
  )
  print(generate(prompt))

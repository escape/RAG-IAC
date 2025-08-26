#!/usr/bin/env python3
import os, glob, json, time, requests
from pathlib import Path

IN_DOCKER = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "1"
OLLAMA  = "http://ollama:11434"  if IN_DOCKER else f"http://localhost:{os.getenv('OLLAMA_PORT','11434')}"
WEAVIATE= "http://weaviate:8080" if IN_DOCKER else f"http://localhost:{os.getenv('WEAVIATE_PORT','8080')}"

EMBED_MODEL = os.getenv("EMBED_MODEL","nomic-embed-text")
CLASS_NAME  = "DocChunk"  # literal, keep it simple/camel-case

def embed(text):
    # Only use /api/embed endpoint
    r = requests.post(f"{OLLAMA}/api/embed", json={"model": EMBED_MODEL, "input": text})
    if not r.ok:
        print(f"[embed error] {r.status_code} {r.text}")
        exit(1)
    data = r.json()
    return (data.get("embedding") 
            or (data.get("embeddings") or [None])[0])

def chunker(text, max_len=900, overlap=150):
    text = " ".join(text.split())
    i = 0
    while i < len(text):
        yield text[i:i+max_len]
        i += max_len - overlap

def ingest_dir(path="data/raw"):
    files = [p for p in glob.glob(f"{path}/**/*", recursive=True) if os.path.isfile(p)]
    added = 0
    for fp in files:
        txt = Path(fp).read_text(errors="ignore")
        did = Path(fp).name
        for ch in chunker(txt):
            vec = embed(ch)
            obj = {
                "class": CLASS_NAME,
                "properties": {"doc_id": did, "chunk": ch, "meta": ""},
                "vector": vec,
            }
            # With AUTOSCHEMA, this first insert will auto-create the class
            requests.post(f"{WEAVIATE}/v1/objects", json=obj).raise_for_status()
            added += 1
    print(json.dumps({"ingested_chunks": added, "files": len(files)}))

if __name__ == "__main__":
    # wait for services
    for _ in range(60):
        try:
            requests.get(f"{WEAVIATE}/v1/.well-known/ready").raise_for_status()
            requests.post(f"{OLLAMA}/api/tags").raise_for_status()
            break
        except Exception:
            time.sleep(1)
    ingest_dir()
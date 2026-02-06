#!/usr/bin/env python3
import os, json, time, requests
from pathlib import Path

IN_DOCKER = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "1"
OLLAMA  = "http://ollama:11434"  if IN_DOCKER else f"http://localhost:{os.getenv('OLLAMA_PORT','11434')}"
WEAVIATE= "http://weaviate:8080" if IN_DOCKER else f"http://localhost:{os.getenv('WEAVIATE_PORT','8080')}"

EMBED_MODEL = os.getenv("EMBED_MODEL","nomic-embed-text")
CLASS_NAME  = "DocChunk"

def embed(text):
    r = requests.post(f"{OLLAMA}/api/embed", json={"model": EMBED_MODEL, "input": text})
    r.raise_for_status()
    data = r.json()
    return (data.get("embedding") or (data.get("embeddings") or [None])[0])

def chunker(text, max_len=900, overlap=150):
    text = " ".join(text.split())
    i = 0
    while i < len(text):
        yield text[i:i+max_len]
        i += max_len - overlap

def ingest_file(fp: Path):
    txt = fp.read_text(errors="ignore")
    did = fp.name
    added = 0
    for ch in chunker(txt):
        vec = embed(ch)
        obj = {
            "class": CLASS_NAME,
            "properties": {"doc_id": did, "chunk": ch, "meta": ""},
            "vector": vec,
        }
        requests.post(f"{WEAVIATE}/v1/objects", json=obj).raise_for_status()
        added += 1
    return added

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: ingest_one.py <file_path>")
        sys.exit(2)
    target = Path(sys.argv[1])
    if not target.exists() or not target.is_file():
        print(f"File not found: {target}")
        sys.exit(1)
    # wait for services
    for _ in range(60):
        try:
            requests.get(f"{WEAVIATE}/v1/.well-known/ready").raise_for_status()
            requests.get(f"{OLLAMA}/api/tags").raise_for_status()
            break
        except Exception:
            time.sleep(1)
    n = ingest_file(target)
    print(json.dumps({"file": str(target), "ingested_chunks": n}))

#!/usr/bin/env python3
import os, sys, glob, json, math
from pathlib import Path

MAX_LEN = 900
OVERLAP = 150
STEP = MAX_LEN - OVERLAP

def estimate_for_text(text: str):
    norm = " ".join(text.split())
    L = len(norm)
    if L == 0:
        return 0, 0
    # chunks: 1 if L<=MAX_LEN else 1 + ceil((L - MAX_LEN)/STEP)
    extra = max(0, L - MAX_LEN)
    chunks = 1 + (math.ceil(extra / STEP) if extra > 0 else 0)
    return L, chunks

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Estimate chunk counts for a file or directory")
    ap.add_argument("path", nargs="?", default="data/raw", help="File or directory path")
    ap.add_argument("--summary-only", action="store_true", help="Print only totals, omit per-file details")
    args = ap.parse_args()
    p = Path(args.path)
    files = []
    if p.is_dir():
        files = [Path(fp) for fp in glob.glob(f"{p}/**/*", recursive=True) if os.path.isfile(fp)]
    elif p.is_file():
        files = [p]
    else:
        print(json.dumps({"error": f"Path not found: {args.path}"}))
        sys.exit(1)

    results = []
    total_bytes = 0
    total_chars = 0
    total_chunks = 0

    for fp in files:
        try:
            bsize = fp.stat().st_size
        except Exception:
            bsize = 0
        try:
            txt = fp.read_text(errors="ignore")
        except Exception:
            txt = ""
        chars, chunks = estimate_for_text(txt)
        results.append({
            "file": str(fp),
            "size_bytes": bsize,
            "chars": chars,
            "chunks": chunks,
        })
        total_bytes += bsize
        total_chars += chars
        total_chunks += chunks

    out = {
        "path": str(p),
        "files": len(results),
        "total_bytes": total_bytes,
        "total_chars": total_chars,
        "total_chunks": total_chunks,
        "max_len": MAX_LEN,
        "overlap": OVERLAP,
        "step": STEP,
    }
    if not args.summary_only:
        out["details"] = results
    print(json.dumps(out))

if __name__ == "__main__":
    main()

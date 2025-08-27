#!/usr/bin/env python3
import os, sys, json, time, glob
from pathlib import Path

# Reuse single-file ingest and splitting utilities
import ingest_one as one
from split_file import human_size_to_bytes, split_file

def wait_ready(timeout=60):
    import requests
    IN_DOCKER = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "1"
    OLLAMA  = "http://ollama:11434"  if IN_DOCKER else f"http://localhost:{os.getenv('OLLAMA_PORT','11434')}"
    WEAVIATE= "http://weaviate:8080" if IN_DOCKER else f"http://localhost:{os.getenv('WEAVIATE_PORT','8080')}"
    last_err = None
    for _ in range(timeout):
        try:
            # Weaviate readiness
            r1 = requests.get(f"{WEAVIATE}/v1/.well-known/ready", timeout=2)
            r1.raise_for_status()
            # Ollama tags (GET is sufficient for liveness)
            r2 = requests.get(f"{OLLAMA}/api/tags", timeout=2)
            r2.raise_for_status()
            return True
        except Exception as e:
            last_err = str(e)
            time.sleep(1)
    if last_err:
        print(json.dumps({"last_ready_error": last_err}))
    return False

def ingest_dir(dir_path: Path, pattern: str = "*", recursive: bool = True, quiet: bool = False):
    files = []
    if recursive:
        files = [Path(p) for p in glob.glob(str(dir_path / "**" / pattern), recursive=True) if os.path.isfile(p)]
    else:
        files = [Path(p) for p in glob.glob(str(dir_path / pattern)) if os.path.isfile(p)]
    ingested = 0
    details = []
    if not quiet:
        print(f"\n┌──────────────────────────────┐\n│ Ingesting directory (batch)  │\n└──────────────────────────────┘")
        print(f"Path: {dir_path}  Pattern: {pattern}  Recursive: {recursive}")
        print(f"Found {len(files)} file(s)\n")
    for fp in sorted(files):
        if not quiet:
            print(f"→ Ingesting: {fp}")
        n = one.ingest_file(fp)
        ingested += n
        if not quiet:
            details.append({"file": str(fp), "chunks": n})
            print(f"  ✓ Chunks ingested: {n}\n")
    return ingested, (details if not quiet else None), len(files)

def ingest_split_file(src: Path, size_str: str, out_dir: Path = None, prefix: str = None, quiet: bool = False):
    part_size = human_size_to_bytes(size_str)
    if out_dir is None:
        out_dir = src.parent
    parts = []
    # Split
    if not quiet:
        print(f"\n┌──────────────────────────────┐\n│ Split & Ingest large file    │\n└──────────────────────────────┘")
        print(f"Source: {src}\nPart size: {size_str}\nOutput dir: {out_dir}\nPrefix: {prefix or src.stem + '.part.'}")
    count = split_file(src, out_dir, part_size, prefix)
    if not quiet:
        print(f"Created {count} part file(s).\n")
    # Collect part files matching prefix
    pref = prefix if prefix is not None else (src.stem + ".part.")
    suffix = src.suffix
    for idx in range(count):
        parts.append(out_dir / f"{pref}{idx:03d}{suffix}")
    # Ingest
    ingested = 0
    details = []
    if not quiet:
        print("Ingesting parts...\n")
    for fp in parts:
        if not quiet:
            print(f"→ Ingesting: {fp}")
        n = one.ingest_file(fp)
        ingested += n
        if not quiet:
            details.append({"file": str(fp), "chunks": n})
            print(f"  ✓ Chunks ingested: {n}\n")
    return count, ingested, (details if not quiet else None)

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Batch ingestion helper: split large files or ingest a directory.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="Path to a large text file to split and ingest")
    g.add_argument("--dir", help="Directory to ingest all matching files")
    ap.add_argument("--size", help="Part size for splitting (e.g., 5MB)")
    ap.add_argument("--out", help="Output directory for parts (defaults to file's directory)")
    ap.add_argument("--prefix", help="Prefix for split parts (defaults to <stem>.part.)")
    ap.add_argument("--pattern", default="*", help="Glob pattern for --dir mode (default: *)")
    ap.add_argument("--no-recursive", action="store_true", help="Do not recurse in --dir mode")
    ap.add_argument("--summary-only", action="store_true", help="Suppress per-file logs and omit detailed results from final JSON")
    args = ap.parse_args()

    print("Waiting for services (Weaviate & Ollama)...", flush=True)
    ok = wait_ready(90)
    if not ok:
        print("✗ Services not ready. See error above.")
        print(json.dumps({"error": "Services not ready"}))
        sys.exit(1)
    print("✓ Services ready.\n")

    summary = {}
    if args.file:
        if not args.size:
            print(json.dumps({"error": "--size is required with --file"}))
            sys.exit(2)
        src = Path(args.file)
        out_dir = Path(args.out) if args.out else None
        count, ingested, details = ingest_split_file(src, args.size, out_dir, args.prefix, quiet=args.summary_only)
        summary = {
            "mode": "split-file",
            "file": str(src),
            "parts": count,
            "ingested_chunks": ingested,
            **({} if args.summary_only else {"details": details}),
        }
        if not args.summary_only:
            print(f"Batch completed: parts={count}, total_chunks={ingested}\n")
    else:
        dirp = Path(args.dir)
        ingested, details, file_count = ingest_dir(dirp, args.pattern, recursive=not args.no_recursive, quiet=args.summary_only)
        summary = {
            "mode": "ingest-dir",
            "dir": str(dirp),
            "pattern": args.pattern,
            "recursive": not args.no_recursive,
            "ingested_chunks": ingested,
            "files": (len(details) if details is not None else file_count),
            **({} if args.summary_only else {"details": details}),
        }
        if not args.summary_only and details is not None:
            print(f"Batch completed: files={len(details)}, total_chunks={ingested}\n")

    print(json.dumps(summary))

if __name__ == "__main__":
    main()

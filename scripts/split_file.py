#!/usr/bin/env python3
import os, sys
from pathlib import Path

def human_size_to_bytes(s: str) -> int:
    s = s.strip().lower()
    if s.endswith('kb'):
        return int(float(s[:-2]) * 1024)
    if s.endswith('mb'):
        return int(float(s[:-2]) * 1024 * 1024)
    if s.endswith('gb'):
        return int(float(s[:-2]) * 1024 * 1024 * 1024)
    if s.endswith('b'):
        return int(float(s[:-1]))
    return int(float(s))

def split_file(src: Path, out_dir: Path, part_size: int, prefix: str = None):
    out_dir.mkdir(parents=True, exist_ok=True)
    if prefix is None:
        prefix = src.stem + ".part."
    idx = 0
    with src.open('rb') as f:
        while True:
            chunk = f.read(part_size)
            if not chunk:
                break
            out = out_dir / f"{prefix}{idx:03d}{src.suffix}"
            with out.open('wb') as w:
                w.write(chunk)
            idx += 1
    return idx

def main():
    if len(sys.argv) < 3:
        print("Usage: split_file.py <src_file> <part_size e.g. 5MB> [out_dir] [prefix]")
        sys.exit(2)
    src = Path(sys.argv[1])
    size = human_size_to_bytes(sys.argv[2])
    out_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else src.parent
    prefix = sys.argv[4] if len(sys.argv) > 4 else None
    if not src.exists() or not src.is_file():
        print(f"Source not found: {src}")
        sys.exit(1)
    parts = split_file(src, out_dir, size, prefix)
    print(f"Wrote {parts} parts to {out_dir}")

if __name__ == '__main__':
    main()

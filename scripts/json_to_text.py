#!/usr/bin/env python3
"""
json_to_text.py

Extract Q/A text from JSON exports (ChatGPT-like) into plain .md files for ingestion.
Runs inside the Jupyter container; place inputs under ./data for container access.
"""
import os, sys, json, re
from pathlib import Path
from typing import List, Dict, Any, Tuple

def sanitize_title(title: str, fallback: str) -> str:
    if not title:
        title = fallback
    t = re.sub(r"[^A-Za-z0-9._-]+", "_", title.strip())
    return (t[:80] or fallback)

def parts_to_text(msg: Dict[str, Any]) -> str:
    # ChatGPT-like: message.content.parts is a list of strings
    content = msg.get("content") or {}
    parts = content.get("parts") or []
    txt = "\n".join([p for p in parts if isinstance(p, str) and p.strip()])
    return txt.strip()

def extract_messages_from_mapping(mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    msgs: List[Dict[str, Any]] = []
    for node in mapping.values():
        m = node.get("message")
        if not m:
            continue
        role = ((m.get("author") or {}).get("role") or "").lower()
        if role in {"tool", "system"}:
            continue
        txt = parts_to_text(m)
        if not txt:
            continue
        ct = m.get("create_time")
        msgs.append({
            "role": role, "text": txt, "create_time": ct,
        })
    # sort by create_time if present; stable fallback is original order
    msgs.sort(key=lambda x: (x["create_time"] is None, x["create_time"]))
    return msgs

def pair_qa(messages: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    pending_q = None
    for m in messages:
        role = m["role"]
        txt = m["text"]
        if role == "user":
            if pending_q is not None:
                # previous Q without A; flush with empty A
                pairs.append((pending_q, ""))
            pending_q = txt
        else:
            # treat any non-user (e.g., assistant/model) as answer
            if pending_q is not None:
                pairs.append((pending_q, txt))
                pending_q = None
    if pending_q is not None:
        pairs.append((pending_q, ""))
    return pairs

def process_conversation(conv: Dict[str, Any], out_dir: Path, index: int) -> Path:
    title = conv.get("title") or f"conversation_{index:04d}"
    mapping = conv.get("mapping") or {}
    msgs = extract_messages_from_mapping(mapping)
    qa = pair_qa(msgs)
    if not qa:
        return None
    name = sanitize_title(title, f"conversation_{index:04d}") + ".md"
    out_path = out_dir / name
    with out_path.open("w", encoding="utf-8") as w:
        w.write(f"# {title}\n\n")
        for i, (q, a) in enumerate(qa, 1):
            w.write(f"## Q{i}\n{q}\n\n")
            if a:
                w.write(f"### A{i}\n{a}\n\n")
    return out_path

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8", errors="ignore") as r:
        return json.load(r)

def is_conv_obj(obj: Any) -> bool:
    return isinstance(obj, dict) and ("mapping" in obj or "title" in obj)

def process_file(in_path: Path, out_dir: Path, start_index: int = 1) -> Dict[str, Any]:
    obj = load_json(in_path)
    written: List[str] = []
    idx = start_index
    if isinstance(obj, list):
        for item in obj:
            if is_conv_obj(item):
                p = process_conversation(item, out_dir, idx)
                if p:
                    written.append(str(p))
                idx += 1
    elif is_conv_obj(obj):
        p = process_conversation(obj, out_dir, idx)
        if p:
            written.append(str(p))
    else:
        # Unknown shape; skip
        pass
    return {"input": str(in_path), "written": written, "next_index": idx}

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Convert JSON exports (ChatGPT-like) to Q/A markdown files.")
    ap.add_argument("--input", required=True, help="Input file or directory (must be under ./data for container access)")
    ap.add_argument("--out-dir", default="/home/jovyan/data/raw/json2txt", help="Output directory inside container")
    ap.add_argument("--pattern", default="*.json", help="Glob when input is a directory")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n┌──────────────────────────────┐\n│ JSON → Text (Q/A extractor)  │\n└──────────────────────────────┘")
    print(f"Input: {in_path}\nOutput dir: {out_dir}\n")

    summary = {"processed": [], "total_written": 0}
    idx = 1
    if in_path.is_dir():
        files = sorted(in_path.glob(args.pattern))
        print(f"Found {len(files)} json file(s)\n")
        for fp in files:
            print(f"→ Processing: {fp}")
            res = process_file(fp, out_dir, idx)
            idx = res["next_index"]
            written = res["written"]
            summary["processed"].append({"file": str(fp), "written": written})
            summary["total_written"] += len(written)
            print(f"  ✓ Wrote {len(written)} file(s)\n")
    else:
        print(f"→ Processing: {in_path}")
        res = process_file(in_path, out_dir, idx)
        written = res["written"]
        summary["processed"].append({"file": str(in_path), "written": written})
        summary["total_written"] += len(written)
        print(f"  ✓ Wrote {len(written)} file(s)\n")

    print(f"Batch completed: total_written={summary['total_written']}\n")
    print(json.dumps(summary))

if __name__ == "__main__":
    main()

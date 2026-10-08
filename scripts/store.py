"""合併結果落地：data/ 下的譯文、出處（prov）與紀錄（*.jsonl，成績單的來源）。"""
import json

import common as C


def log_rows(name, rows):
    if not rows:
        return
    p = C.DATA / f"{name}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def merge_into(path, d):
    if not d:
        return
    cur = C.load_json(path) if path.exists() else {}
    cur.update(d)
    C.save_json(path, cur)


def set_prov(ns, updates):
    merge_into(C.DATA / "prov" / f"{ns}.json", updates)


def text_len(v):
    return sum(len(x) for x in v) if isinstance(v, list) else len(v)

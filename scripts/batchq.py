"""機翻批次佇列：queue/<kind>/batch_NNN.json（輸入）與 queue/<kind>/out/batch_NNN.json（輸出）。

queue/ 進版控，本機切批 → push → WSL 跑 workflow 寫 out/ → push → 本機合併後 clear。
"""
import argparse
import json
import sys

import common as C

KINDS = {
    "lang": "rules/mt_rules.md",
    "book": "rules/mt_book_rules.md",
    "quest": "rules/mt_quest_rules.md",
    "review": "rules/review_rules.md",
    "terms": "rules/terms_rules.md",
}


def _dir(kind):
    return C.QUEUE / kind


def write_batches(kind, items, size):
    d = _dir(kind)
    out = d / "out"
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"queue/{kind}/out/ 還有未合併的輸出，先跑合併")
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("batch_*.json"):
        f.unlink()
    n = 0
    for i in range(0, len(items), size):
        batch = {}
        for group, key, value in items[i:i + size]:
            if group is None:
                batch[key] = value
            else:
                batch.setdefault(group, {})[key] = value
        n += 1
        C.save_json(d / f"batch_{n:03d}.json", batch)
    return n


def _batches(kind):
    return sorted(_dir(kind).glob("batch_*.json"))


def pending(kind):
    res = []
    for f in _batches(kind):
        o = _dir(kind) / "out" / f.name
        if not o.exists():
            res.append({"id": f.stem, "in": f"queue/{kind}/{f.name}", "out": f"queue/{kind}/out/{f.name}"})
    return res


def finished(kind):
    res = []
    for f in _batches(kind):
        o = _dir(kind) / "out" / f.name
        if not o.exists():
            continue
        try:
            out = C.load_json(o)
        except Exception:
            out = None
        res.append({"id": f.stem, "in": C.load_json(f), "out": out})
    return res


def clear(kind, batch_id):
    for p in (_dir(kind) / f"{batch_id}.json", _dir(kind) / "out" / f"{batch_id}.json"):
        if p.exists():
            p.unlink()


def drop_output(kind, batch_id):
    """只刪輸出、保留輸入：該批回到 pending，下次 workflow 會重跑。"""
    p = _dir(kind) / "out" / f"{batch_id}.json"
    if p.exists():
        p.unlink()


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("args")
    a.add_argument("kind", choices=KINDS)
    a.add_argument("model", choices=["haiku", "sonnet", "opus"])
    a.add_argument("--limit", type=int)
    ns = ap.parse_args(argv)
    batches = pending(ns.kind)
    if ns.limit:
        batches = batches[:ns.limit]
    json.dump({"repo": str(C.REPO), "kind": ns.kind, "model": ns.model,
               "rules": KINDS[ns.kind], "batches": batches}, sys.stdout, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()

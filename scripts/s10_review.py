"""Opus 審校機翻條目：任務書全部＋lang 英文 ≥80 字的長文（yuki 2026-10-08 拍板縮減 Opus 用量；
短名稱的一致性交給術語統一）。CFPA／jar 譯文與書頁不審。

  prep  → queue/review/batch_NNN.json  {ns: {key: {"en": 英文, "zh": 目前譯文}}}（lang 依 ns 排序，任務書 ns＝_quests）
  merge → 讀 queue/review/out（只含要改的條目）→ to_tw 收斂 → check_value → 套用（目前值須仍等於送審值）
"""
import argparse

import batchq
import common as C
import quests_io
import store
from s07q_quests import to_tw_value
from validate import check_value

BATCH = 250
LANG_MIN_LEN = 80


def _load(p):
    return C.load_json(p) if p.exists() else {}


def prep():
    items = []
    for mt_p in sorted((C.DATA / "mt").glob("*.json")):
        ns = mt_p.stem
        en = _load(C.WORK / "extract/en" / f"{ns}.json")
        for k, zh in sorted(C.load_json(mt_p).items()):
            if k in en and len(en[k]) >= LANG_MIN_LEN:
                items.append((ns, k, {"en": en[k], "zh": zh}))
    q = _load(C.DATA / "quests_mt.json")
    if q:
        en_q = quests_io.load_flat(C.QUESTS_LANG_DIR / "en_us")
        items += [("_quests", k, {"en": en_q[k], "zh": v}) for k, v in q.items() if k in en_q]
    n = batchq.write_batches("review", items, BATCH)
    print(f"送審 {len(items)} 條 → {n} 批")


def _target(ns):
    return C.DATA / "quests_mt.json" if ns == "_quests" else C.DATA / "mt" / f"{ns}.json"


def merge():
    changed_n = rejected = 0
    for b in batchq.finished("review"):
        if not isinstance(b["out"], dict):
            batchq.drop_output("review", b["id"])
            print(f"⚠️ {b['id']}: 輸出不是合法 JSON，已刪輸出、保留批次待重跑")
            continue
        out = b["out"]
        rows = []
        for ns, entries in b["in"].items():
            fixes = out.get(ns) if isinstance(out.get(ns), dict) else {}
            cur = _load(_target(ns))
            prov = _load(C.DATA / "prov" / f"{ns}.json")
            apply = {}
            for k, pair in entries.items():
                row = {"kind": "review", "ns": ns, "key": k, "prev_model": prov.get(k), "changed": False, "why": None}
                if k in fixes:
                    v = fixes[k]
                    if isinstance(v, (str, list)):
                        v = to_tw_value(v)
                    why = check_value(pair["en"], v, amp_codes=(ns == "_quests"))
                    if why is None and cur.get(k) != pair["zh"]:
                        why = "送審後已被改動（略過）"
                    if why:
                        row["why"] = why
                        rejected += 1
                    elif v != pair["zh"]:
                        apply[k] = v
                        row["changed"] = True
                rows.append(row)
            if apply:
                store.merge_into(_target(ns), apply)
                store.set_prov(ns, {k: "opus" for k in apply})
                changed_n += len(apply)
        store.log_rows("review_log", rows)
        batchq.clear("review", b["id"])
    print(f"審校修正 {changed_n} 條，修正被驗證退回 {rejected} 條；仍待審批次 {len(batchq.pending('review'))}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prep", "merge"])
    {"prep": prep, "merge": merge}[ap.parse_args(argv).cmd]()


if __name__ == "__main__":
    main()

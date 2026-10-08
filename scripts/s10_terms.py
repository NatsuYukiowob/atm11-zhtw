"""術語統一：同一英文名稱出現多種譯名（且至少一個是機翻）→ Opus 定標準譯名 → 逐 key 改寫機翻條目。

不寫進子字串術語表（Valhelsia 教訓：子字串規則會靜默污染上千條）。
  prep  → queue/terms/batch_NNN.json  {en_name: {"variants": {zh: ["ns:key@src", ...]}}}
  apply → data/terms_canon.json，改寫 data/mt 名稱型 key，寫 review_log
"""
import argparse
from collections import defaultdict

import batchq
import common as C
import store
from validate import check_text

NAME_PREFIXES = ("item.", "block.", "entity.", "fluid.", "effect.", "enchantment.")
MAX_LEN = 40
BATCH = 150


def _load(p):
    return C.load_json(p) if p.exists() else {}


def collect():
    groups = defaultdict(lambda: defaultdict(list))
    for en_p in sorted((C.WORK / "extract/en").glob("*.json")):
        ns = en_p.stem
        en = C.load_json(en_p)
        conv = _load(C.WORK / "zhtw_lang" / f"{ns}.json")
        mt = _load(C.DATA / "mt" / f"{ns}.json")
        prov = _load(C.DATA / "prov" / f"{ns}.json")
        for k, ev in en.items():
            if not k.startswith(NAME_PREFIXES) or len(ev) > MAX_LEN:
                continue
            if k in mt:
                groups[ev][mt[k]].append(f"{ns}:{k}@{prov.get(k, 'mt')}")
            elif k in conv:
                groups[ev][conv[k]].append(f"{ns}:{k}@conv")
    return {
        ev: {zh: refs for zh, refs in v.items()}
        for ev, v in groups.items()
        if len(v) >= 2 and any(not r.endswith("@conv") for refs in v.values() for r in refs)
    }


def prep():
    items = [(None, ev, {"variants": v}) for ev, v in sorted(collect().items())]
    n = batchq.write_batches("terms", items, BATCH)
    print(f"譯名分歧 {len(items)} 組 → {n} 批")


def apply():
    canon = {}
    for b in batchq.finished("terms"):
        if not isinstance(b["out"], dict):
            batchq.drop_output("terms", b["id"])
            print(f"⚠️ {b['id']}: 輸出不是合法 JSON，已刪輸出、保留批次待重跑")
            continue
        for ev in b["in"]:
            v = b["out"].get(ev)
            if isinstance(v, str) and v.strip():
                v = C.to_tw(v.strip())
                why = check_text(ev, v)
                if why:
                    print(f"✗ 標準譯名 {ev!r} → {v!r}：{why}")
                else:
                    canon[ev] = v
        batchq.clear("terms", b["id"])
    p = C.DATA / "terms_canon.json"
    if not p.exists():
        C.save_json(p, {})
    store.merge_into(p, canon)
    rows, n = [], 0
    for en_p in sorted((C.WORK / "extract/en").glob("*.json")):
        ns = en_p.stem
        mt_p = C.DATA / "mt" / f"{ns}.json"
        if not mt_p.exists():
            continue
        en, mt = C.load_json(en_p), C.load_json(mt_p)
        prov = _load(C.DATA / "prov" / f"{ns}.json")
        changed = {}
        for k, zh in mt.items():
            ev = en.get(k)
            if k.startswith(NAME_PREFIXES) and ev in canon and zh != canon[ev]:
                changed[k] = canon[ev]
                rows.append({"kind": "term", "ns": ns, "key": k, "prev_model": prov.get(k),
                             "changed": True, "why": None})
        if changed:
            store.merge_into(mt_p, changed)
            n += len(changed)
    store.log_rows("review_log", rows)
    print(f"標準譯名 {len(canon)} 組；改寫機翻名稱 {n} 條")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prep", "apply"])
    {"prep": prep, "apply": apply}[ap.parse_args(argv).cmd]()


if __name__ == "__main__":
    main()

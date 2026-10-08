"""驗證並合併 queue/lang/out/ → data/mt/<modid>.json（進版控）。

每條先 to_tw() 收斂（統一術語、殘留簡體轉正），再過 validate.check_text。
不合格或漏掉的 key 不寫入，下次 s06_make_batches 會重出。處理過的批次從 queue 清掉。
"""
import argparse

import batchq
import common as C
import store
from validate import check_text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["haiku", "sonnet", "opus"])
    model = ap.parse_args(argv).model
    ok = bad = 0
    for b in batchq.finished("lang"):
        rows, accepted = [], {}
        out = b["out"] if isinstance(b["out"], dict) else None
        for ns, entries in b["in"].items():
            got = out.get(ns, {}) if out is not None and isinstance(out.get(ns), dict) else {}
            for k, en in entries.items():
                v = got.get(k)
                if isinstance(v, str):
                    v = C.to_tw(v)
                if out is None:
                    why = "輸出不是合法 JSON"
                elif v is None:
                    why = "缺漏"
                else:
                    why = check_text(en, v)
                rows.append({"kind": "lang", "model": model, "ns": ns, "key": k,
                             "len": store.text_len(en), "ok": why is None, "why": why})
                if why:
                    bad += 1
                    print(f"✗ {ns}:{k} — {why}")
                    continue
                accepted.setdefault(ns, {})[k] = v
                ok += 1
        for ns, d in accepted.items():
            store.merge_into(C.DATA / "mt" / f"{ns}.json", d)
            store.set_prov(ns, {k: model for k in d})
        store.log_rows("merge_log", rows)
        batchq.clear("lang", b["id"])
    print(f"\n[{model}] 合併 {ok} 條，退回 {bad} 條；仍待翻批次 {len(batchq.pending('lang'))}")


if __name__ == "__main__":
    main()

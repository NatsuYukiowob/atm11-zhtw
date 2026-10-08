"""驗證並合併 queue/quest/out/ → data/quests_mt.json（進版控）。值先 to_tw 收斂，再 check_value(amp_codes=True)。"""
import argparse

import batchq
import common as C
import store
from s07q_quests import to_tw_value
from validate import check_value


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["haiku", "sonnet", "opus"])
    model = ap.parse_args(argv).model
    ok = bad = 0
    for b in batchq.finished("quest"):
        rows, accepted = [], {}
        out = b["out"] if isinstance(b["out"], dict) else None
        for k, ev in b["in"].items():
            v = out.get(k) if out is not None else None
            if isinstance(v, (str, list)) and all(isinstance(x, str) for x in (v if isinstance(v, list) else [v])):
                v = to_tw_value(v)
            if out is None:
                why = "輸出不是合法 JSON"
            elif v is None:
                why = "缺漏"
            else:
                why = check_value(ev, v, amp_codes=True)
            rows.append({"kind": "quest", "model": model, "ns": "_quests", "key": k,
                         "len": store.text_len(ev), "ok": why is None, "why": why})
            if why:
                bad += 1
                print(f"✗ {k} — {why}")
                continue
            accepted[k] = v
            ok += 1
        store.merge_into(C.DATA / "quests_mt.json", accepted)
        store.set_prov("_quests", {k: model for k in accepted})
        store.log_rows("merge_log", rows)
        batchq.clear("quest", b["id"])
    print(f"\n[{model}] 合併 {ok} 條，退回 {bad} 條；仍待翻批次 {len(batchq.pending('quest'))}")


if __name__ == "__main__":
    main()

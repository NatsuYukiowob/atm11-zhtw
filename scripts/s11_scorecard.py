"""haiku 成績單：從 data/merge_log.jsonl 與 data/review_log.jsonl 算指標 → reports/haiku-scorecard.md。"""
import json
import re
from collections import Counter, defaultdict

import common as C


def _rows(name):
    p = C.DATA / f"{name}.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def _reason(why):
    """退回原因歸類：去掉「第 N 行：」與書頁 JSON 路徑前綴，再去掉細節（: 之後、括號／箭頭之後、尾端數字）。"""
    why = re.sub(r"^第 \d+ 行：", "", why or "")
    why = re.sub(r"^[.\[][^:]*: ", "", why)
    why = re.split(r": | [(\[]| →", why)[0]
    return re.sub(r"[\s\d]+$", "", why)


def _bucket(n):
    return "short" if n < 20 else "sentence" if n < 80 else "long"


def compute():
    per_key = defaultdict(list)
    for r in _rows("merge_log"):
        per_key[(r["kind"], r["ns"], r["key"])].append(r)
    by_kind = defaultdict(lambda: {"haiku_n": 0, "haiku_ok": 0, "sonnet_n": 0, "sonnet_ok": 0, "never_ok": 0})
    by_len = defaultdict(lambda: {"n": 0, "ok": 0})
    ns_rej = Counter()
    ns_n = Counter()
    reasons = Counter()
    for (kind, ns, _), rs in per_key.items():
        k = by_kind[kind]
        first = next((r for r in rs if r["model"] == "haiku"), None)
        if first:
            k["haiku_n"] += 1
            k["haiku_ok"] += first["ok"]
            b = by_len[_bucket(first["len"])]
            b["n"] += 1
            b["ok"] += first["ok"]
            ns_n[ns] += 1
            if not first["ok"]:
                ns_rej[ns] += 1
                reasons[_reason(first["why"])] += 1
        for r in rs:
            if r["model"] == "sonnet":
                k["sonnet_n"] += 1
                k["sonnet_ok"] += r["ok"]
        if not any(r["ok"] for r in rs):
            k["never_ok"] += 1
    review = {"reviewed": 0, "changed": 0, "by_prev": defaultdict(lambda: {"reviewed": 0, "changed": 0}),
              "terms_changed": 0}
    for r in _rows("review_log"):
        if r["kind"] == "term":
            review["terms_changed"] += r["changed"]
            continue
        review["reviewed"] += 1
        review["changed"] += r["changed"]
        bp = review["by_prev"][r["prev_model"] or "?"]
        bp["reviewed"] += 1
        bp["changed"] += r["changed"]
    review["by_prev"] = dict(review["by_prev"])
    top_ns = [(ns, ns_rej[ns], ns_n[ns]) for ns, _ in ns_rej.most_common(20)]
    return {"by_kind": dict(by_kind), "by_len": dict(by_len), "review": review,
            "top_ns": top_ns, "reasons": reasons.most_common(10)}


def _pct(a, b):
    return f"{a / b * 100:.1f}%" if b else "—"


def main():
    s = compute()
    L = ["# haiku 成績單", "", "## 首翻（haiku）與重翻（sonnet）", "",
         "| 類型 | haiku 首翻 | 通過率 | sonnet 重翻 | sonnet 通過率 | 最終保留英文 |", "|---|---|---|---|---|---|"]
    for kind, k in sorted(s["by_kind"].items()):
        L.append(f"| {kind} | {k['haiku_n']} | {_pct(k['haiku_ok'], k['haiku_n'])} | {k['sonnet_n']} | "
                 f"{_pct(k['sonnet_ok'], k['sonnet_n'])} | {k['never_ok']} |")
    L += ["", "## haiku 首翻通過率 × 英文長度", "", "| 長度 | 條數 | 通過率 |", "|---|---|---|"]
    for b in ("short", "sentence", "long"):
        v = s["by_len"].get(b, {"n": 0, "ok": 0})
        L.append(f"| {b} | {v['n']} | {_pct(v['ok'], v['n'])} |")
    r = s["review"]
    L += ["", "## Opus 審校", "", f"- 審校 {r['reviewed']} 條，修正 {r['changed']} 條（{_pct(r['changed'], r['reviewed'])}）",
          f"- 術語統一改寫 {r['terms_changed']} 條", "", "| 原譯者 | 審校 | 修正 | 修正率 |", "|---|---|---|---|"]
    for m, v in sorted(r["by_prev"].items()):
        L.append(f"| {m} | {v['reviewed']} | {v['changed']} | {_pct(v['changed'], v['reviewed'])} |")
    L += ["", "## haiku 退回最多的 namespace（前 20）", "", "| namespace | 退回 | 首翻數 | 退回率 |", "|---|---|---|---|"]
    for ns, rej, n in s["top_ns"]:
        L.append(f"| {ns} | {rej} | {n} | {_pct(rej, n)} |")
    L += ["", "## haiku 退回原因（前 10）", "", "| 原因 | 次數 |", "|---|---|"]
    for why, n in s["reasons"]:
        L.append(f"| {why} | {n} |")
    L += ["", "## 註記", "",
          "- 判定都是合併當下的規則。任務書 & 色碼在 haiku 合併後才放寬為「只少不多」（2026-10-08），"
          "haiku 任務書列仍是舊的嚴格判定 → 通過率偏低；sonnet 列已用新規則重驗。",
          "- 「未翻譯（與英文相同）」多為三字以上的專名（曲目「作者 - 曲名」、地名），保留英文是正確結果，"
          "不全是模型失誤；lang 的 sonnet 低通過率主要來自這類。",
          "- 首翻成本（API 等價，實際走訂閱額度）見 docs/discovery.md。"]
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    (C.REPORTS / "haiku-scorecard.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()

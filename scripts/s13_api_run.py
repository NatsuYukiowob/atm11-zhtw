"""s13_audit 的 API 執行器：取代 workflows/audit.js，直接用 Anthropic API 跑審查／驗證批次。

  set -a; . ~/claude-api/.env; set +a      # CLAUDE_API、ANTHROPIC_WORKSPACE_ID
  python scripts/s13_audit.py args --queue audit_mt1 | python scripts/s13_api_run.py [-j 8] [--limit N]

讀 args JSON（{repo, batches:[{id, need, model, in, out|verify}]}），每批一次 Messages 呼叫，
回覆的 JSON 寫到 out／verify（同 audit.js 的檔案約定）；解析失敗不寫檔，下次 args 會重排。
規則檔與它提到的參考檔整份放進 system（快取）；本批來源層由佇列的 scope.txt 決定。
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import anthropic

MODELS = {"sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}
# 每 MTok 美元：(input, output, cache write 5m, cache read)
PRICE = {"claude-sonnet-5-5": (2, 10, 2.5, 0.2), "claude-opus-5-5": (4, 20, 5, 0.2)}
REFS = ["rules/mt_rules.md", "data/terms_canon.json", "rules/vanilla_names.json"]
LAYER = {
    "conv": "本批譯文來源：簡中／CFPA 經 OpenCC 轉成繁體（轉換層），不是 mod 作者自帶的 zh_tw；規則中「mod 作者自帶」的描述以此為準。",
    "mt": "本批譯文來源：AI（haiku）機翻，不是 mod 作者自帶的 zh_tw；規則中「mod 作者自帶」的描述以此為準。常見問題是誤譯、望文生義、專有名詞與本包標準譯名不一致。",
}
OUTPUT_NOTE = ("你沒有任何工具。規則提到要讀的檔案內容都已附在下方；規則中「用 Write 寫到輸出路徑」改為："
               "直接把結果 JSON 當成整個回覆輸出，不要 code fence、不要其他文字。")


@lru_cache
def system_blocks(repo, rules, kind):
    head = OUTPUT_NOTE + ("\n" + LAYER[kind] if kind in LAYER else "")
    parts = [f"# 規則檔 {rules}\n\n" + (repo / rules).read_text()]
    parts += [f"# 參考檔 {r}\n\n" + (repo / r).read_text() for r in REFS]
    blocks = [{"type": "text", "text": head}, {"type": "text", "text": "\n\n".join(parts)}]
    blocks[-1]["cache_control"] = {"type": "ephemeral"}
    return blocks


def parse(text):
    t = text.strip()
    if t.startswith("```"):
        t = t.partition("\n")[2].rsplit("```", 1)[0]
    d, _ = json.JSONDecoder().raw_decode(t)  # 回覆偶爾在 JSON 後面多一段說明
    if not isinstance(d, dict):
        raise ValueError("not a dict")
    return d


def scope_of(repo, rel):
    """批次所在佇列的 scope.txt（in 可能是 queue/x/batch_*.json 或 queue/x/vin/v_*.json）。"""
    for d in (repo / rel).parents:
        if (d / "scope.txt").exists():
            return (d / "scope.txt").read_text().strip()
        if d == repo:
            break
    raise SystemExit(f"{rel} 的佇列沒有 scope.txt：無法判斷來源層，先重跑 s13_audit prep")


def run_one(client, repo, b, usage):
    review = b["need"] == "sonnet"
    model = MODELS["sonnet" if review else b["model"]]
    rules = "rules/audit_rules.md" if review else "rules/audit_verify_rules.md"
    dst = repo / (b["out"] if review else b["verify"])
    body = (repo / b["in"]).read_text()
    for attempt in range(2):
        with client.beta.messages.stream(
            model=model, max_tokens=64000,
            output_config={"effort": "high"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            system=system_blocks(repo, rules, scope_of(repo, b["in"]).partition(":")[0]),
            messages=[{"role": "user", "content": "輸入 JSON：\n" + body}],
        ) as s:
            msg = s.get_final_message()
        u = msg.usage
        # fallback 時以實際服務的模型計價；不在價目表的照請求模型估
        usage.append((msg.model if msg.model in PRICE else model, u.input_tokens, u.output_tokens,
                       u.cache_creation_input_tokens or 0, u.cache_read_input_tokens or 0))
        if msg.stop_reason == "refusal":
            return f"{b['id']}: refusal"
        text = "".join(c.text for c in msg.content if c.type == "text")
        try:
            d = parse(text)
        except ValueError as e:
            err = f"{b['id']}: 解析失敗（{e}；stop={msg.stop_reason}）"
            if msg.stop_reason == "max_tokens":
                break  # 截斷：重送同一請求只會再截斷一次
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(".tmp")  # args 會刪掉讀不懂的 out，不可留半個檔
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        tmp.replace(dst)
        return None
    return err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=8)
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    args = json.load(sys.stdin)
    repo, batches = Path(args["repo"]), args["batches"][:a.limit]
    client = anthropic.Anthropic(
        api_key=os.environ["CLAUDE_API"], max_retries=8,
        default_headers={"anthropic-workspace-id": os.environ["ANTHROPIC_WORKSPACE_ID"]},
    )
    usage, fails = [], []

    def job(b):
        try:
            return run_one(client, repo, b, usage)
        except anthropic.APIError as e:
            return f"{b['id']}: {type(e).__name__} {getattr(e, 'status_code', '')} {e.message[:200]}"
        except Exception as e:  # 單批出錯不可中斷整輪（否則看不到花費與失敗清單）
            return f"{b['id']}: {type(e).__name__} {e}"

    with ThreadPoolExecutor(a.j) as ex:
        for i, r in enumerate(ex.map(job, batches), 1):
            if r:
                fails.append(r)
                print(r, file=sys.stderr, flush=True)
            if i % 10 == 0:
                print(f"{i}/{len(batches)}", file=sys.stderr, flush=True)
    cost = sum((i * p[0] + o * p[1] + cw * p[2] + cr * p[3]) / 1e6
               for m, i, o, cw, cr in usage for p in [PRICE[m]])
    print(json.dumps({"batches": len(batches), "failed": len(fails), "calls": len(usage),
                      "cache_read": sum(x[4] for x in usage), "usd": round(cost, 2)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

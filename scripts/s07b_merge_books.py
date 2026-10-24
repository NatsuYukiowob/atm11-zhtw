"""驗證並合併 queue/book/out/ → data/book_mt/（進版控）。

每頁先對文字欄位 tw_fix()（夾簡體才轉），再驗：
  1. JSON 結構（key 集合、list 長度）與原文完全一致
  2. 非文字欄位值 byte 級相同
  3. 文字欄位 Patchouli 標記守恆：$( 與 /$ 數量、$(l:...)/$(k:...) 參照集合
  4. 文字欄位過 validate.check_text（佔位符／§／{}／換行／符號／簡體殘留）
不合格者不合併，下次 s07_books 會重出。
"""
import argparse
import re

import batchq
import common as C
import store
from s07_books import TEXT_FIELDS, is_text, walk
from validate import check_text

REF = re.compile(r"\$\((?:l|k):[^)]*\)")


def check(orig, tran, path=""):
    errs = []
    if isinstance(orig, dict):
        if not isinstance(tran, dict) or set(orig) != set(tran):
            return [f"{path}: key 集合不一致"]
        for k, v in orig.items():
            if k in TEXT_FIELDS and isinstance(v, str) and is_text(v):
                t = tran[k]
                if not isinstance(t, str) or not t.strip():
                    errs.append(f"{path}.{k}: 空值/非字串")
                elif v.count("$(") != t.count("$(") or v.count("/$") != t.count("/$"):
                    errs.append(f"{path}.{k}: $() 標記數不符")
                elif sorted(REF.findall(v)) != sorted(REF.findall(t)):
                    errs.append(f"{path}.{k}: 連結/按鍵參照被改動")
                elif why := check_text(v, t):
                    errs.append(f"{path}.{k}: {why}")
            elif isinstance(v, (dict, list)):
                errs += check(v, tran[k], f"{path}.{k}")
            elif tran[k] != v:
                errs.append(f"{path}.{k}: 非文字欄位被改動")
    elif isinstance(orig, list):
        if not isinstance(tran, list) or len(orig) != len(tran):
            return [f"{path}: list 長度不一致"]
        for i, (o, t) in enumerate(zip(orig, tran)):
            if isinstance(o, (dict, list)):
                errs += check(o, t, f"{path}[{i}]")
            elif o != t:
                errs.append(f"{path}[{i}]: 非文字元素被改動")
    return errs


def _text_len(page):
    n = 0

    def count(s):
        nonlocal n
        n += len(s)
        return s
    walk(page, count)
    return n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["haiku", "sonnet", "opus"])
    model = ap.parse_args(argv).model
    ok = bad = 0
    for b in batchq.finished("book"):
        rows, prov = [], {}
        out = b["out"] if isinstance(b["out"], dict) else None
        for rel, orig in b["in"].items():
            tran = out.get(rel) if out is not None else None
            if out is None:
                errs = ["輸出不是合法 JSON"]
            elif tran is None:
                errs = ["缺漏"]
            else:
                if isinstance(tran, (dict, list)):
                    tran, _ = walk(tran, lambda s: C.tw_fix(s) if isinstance(s, str) else s)
                errs = check(orig, tran)
            rows.append({"kind": "book", "model": model, "ns": rel.split("/")[0], "key": rel,
                         "len": _text_len(orig), "ok": not errs, "why": errs[0] if errs else None})
            if errs:
                bad += 1
                print(f"✗ {rel}: {errs[0]}")
                continue
            C.save_json(C.DATA / "book_mt" / rel, tran)
            prov[rel] = model
            ok += 1
        store.set_prov("_books", prov)
        store.log_rows("merge_log", rows)
        batchq.clear("book", b["id"])
    print(f"\n[{model}] 合併 {ok} 頁，退回 {bad} 頁；仍待翻批次 {len(batchq.pending('book'))}")


if __name__ == "__main__":
    main()

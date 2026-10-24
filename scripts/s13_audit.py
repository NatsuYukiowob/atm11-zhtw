"""jar 內建 zh_tw 審查（移植自 sf5-zhtw s13_audit，只留 lang 的 jar 範圍）。

sonnet 逐條審 → 標記條目反方驗證（error→opus、minor→sonnet） → 通過的修正寫進 data/mt 蓋過 jar。

  prep --scope jar_sample  → 每 mod 名稱／其他各抽 SAMPLE_N 條（依 key 雜湊，可重現）
  prep --scope jar:<mod,…> → 指定 mod 的 jar 內建 zh_tw 全審
  prep --scope conv:<min>-<max> → 轉換層（work/zhtw_lang，簡中／CFPA 轉繁）英文長度 min ≤ len < max 且遊戲顯示的條目
  prep --scope mt:<min>-<max>   → 機翻層（data/mt 中 prov＝haiku／sonnet）同上長度條件
       → queue/audit/batch_NNN.json  {"a1": {"ns", "key", "en", "zh"}}
  args  → workflow 參數：待 sonnet 審的批＋驗證組 queue/audit/vin/v_<sev>_*.json（key＝batch/aid）
  merge → approve／amend 才套用；fix 先 tw_fix（同 s08 對 data/mt 的處理）再過 check_text，
          且遊戲現值仍須等於送審值

升級門檻（同 sf5）：抽樣中某 mod 套用的 error ≥3 條或套用率 ≥10% → `--scope jar:<mod>` 全審。
"""
import argparse
import hashlib
import json
import sys

import common as C
import store
from s08_build_pack import reconv
from validate import check_text

SAMPLE_N = 25
NAME_PREFIXES = ("item.", "block.", "entity.", "effect.", "enchantment.", "fluid.")
MAX_ITEMS = 120
MAX_CHARS = 20000
# 驗證組：嚴重度 → (模型, 每組條數)。minor 多半是用語，不值得 opus
VGROUP = {"error": ("opus", 50), "minor": ("sonnet", 80)}
QNAME = "audit"  # queue/ 下的佇列目錄，main 依 --queue 設定


def q():
    """目前佇列目錄；每次從 C.QUEUE 取（測試只 monkeypatch common.QUEUE）。"""
    return C.QUEUE / QNAME


def _load(p):
    return C.load_json(p) if p.exists() else {}


def shown(ns):
    """遊戲實際顯示的 zh_tw：jar 內建 ← 轉換層 ← 機翻層（與 s08 疊在 jar 上的順序一致；
    s08 丟掉佔位符與英文不符的值，那些 key 仍顯示 jar 內建值）。"""
    en = _load(C.WORK / "extract/en" / f"{ns}.json")
    cur = dict(_load(C.WORK / "extract/tw_jar" / f"{ns}.json"))
    pack = dict(_load(C.WORK / "zhtw_lang" / f"{ns}.json"))
    pack.update({k: reconv(v) for k, v in _load(C.DATA / "mt" / f"{ns}.json").items()})
    cur.update({k: v for k, v in pack.items() if k not in en or C.placeholders(v) == C.placeholders(en[k])})
    return cur


def _hkey(k):
    return hashlib.sha1(k.encode()).hexdigest()


def collect_conv(lo, hi):
    """轉換層仍在遊戲顯示（沒被 data/mt 蓋掉、佔位符沒被 s08 丟掉）的條目。"""
    items = []
    for p in sorted((C.WORK / "zhtw_lang").glob("*.json")):
        ns = p.stem
        en, cur = _load(C.WORK / "extract/en" / f"{ns}.json"), shown(ns)
        items += [(ns, k, en[k], v) for k, v in sorted(C.load_json(p).items())
                  if k in en and lo <= len(en[k]) < hi and cur.get(k) == v and v != en[k]]
    return items


def collect_mt(lo, hi):
    """機翻層（data/mt 中 prov＝haiku／sonnet 重翻、還沒被審查或 opus 改過）仍在遊戲顯示的條目；zh＝出貨值。"""
    items = []
    for p in sorted((C.DATA / "mt").glob("*.json")):
        ns = p.stem
        prov = _load(C.DATA / "prov" / f"{ns}.json")
        en, cur = _load(C.WORK / "extract/en" / f"{ns}.json"), shown(ns)
        for k, v in sorted(C.load_json(p).items()):
            if prov.get(k) in ("haiku", "sonnet") and k in en and lo <= len(en[k]) < hi:
                zh = reconv(v)
                if cur.get(k) == zh and zh != en[k]:
                    items.append((ns, k, en[k], zh))
    return items


def collect(scope):
    """送審條目 [(ns, key, en, zh)]：jar 內建 zh_tw、轉換層或機翻層。"""
    if scope.startswith(("conv:", "mt:")):
        kind, _, rng = scope.partition(":")
        lo, hi = map(int, rng.split("-"))
        return (collect_conv if kind == "conv" else collect_mt)(lo, hi)
    if scope == "jar_sample":
        mods = None
    elif scope.startswith("jar:"):
        mods = set(scope[4:].split(","))
        have = {p.stem for p in (C.WORK / "extract/tw_jar").glob("*.json")}
        if mods - have:
            raise SystemExit(f"jar:<mods> 沒有 jar zh_tw（打錯？）：{sorted(mods - have)}")
    else:
        raise SystemExit(f"不支援的 scope：{scope}（jar_sample／jar:<mod,…>／conv:<min>-<max>／mt:<min>-<max>）")
    items = []
    for p in sorted((C.WORK / "extract/tw_jar").glob("*.json")):
        ns = p.stem
        if mods is not None and ns not in mods:
            continue
        en, tw, cur = _load(C.WORK / "extract/en" / f"{ns}.json"), C.load_json(p), shown(ns)
        cand = [k for k, v in tw.items()
                if k in en and isinstance(v, str) and v != en[k] and cur.get(k) == v]
        if mods is None:
            names = sorted((k for k in cand if k.startswith(NAME_PREFIXES)), key=_hkey)[:SAMPLE_N]
            other = sorted((k for k in cand if not k.startswith(NAME_PREFIXES)), key=_hkey)[:SAMPLE_N]
            cand = names + other
        items += [(ns, k, en[k], tw[k]) for k in sorted(cand)]
    return items


def prep(scope, force=False):
    Q = q()
    # 已審未合併的結果（out/、verify/）重排批號後會失效，先 merge 再 prep
    if not force and any(True for d in ("out", "verify") for _ in (Q / d).glob("*.json")):
        raise SystemExit(f"{Q} 還有未合併的審查結果：先跑 merge（或 --force 捨棄）")
    items = collect(scope)
    Q.mkdir(parents=True, exist_ok=True)
    (Q / "scope.txt").write_text(scope)  # merge 記錄來源層用
    for d in (Q, Q / "out", Q / "verify", Q / "vin"):
        for f in [*d.glob("batch_*.json"), *d.glob("v_*.json")]:
            f.unlink()
    batches, cur, chars, last_ns = [], [], 0, None
    for it in items:
        size = len(it[2]) + len(it[3])
        if cur and (len(cur) >= MAX_ITEMS or chars + size > MAX_CHARS or (it[0] != last_ns and len(cur) >= MAX_ITEMS // 2)):
            batches.append(cur)
            cur, chars = [], 0
        cur.append(it)
        chars += size
        last_ns = it[0]
    if cur:
        batches.append(cur)
    for i, b in enumerate(batches, 1):
        C.save_json(Q / f"batch_{i:03d}.json",
                    {f"a{j}": {"ns": ns, "key": k, "en": en, "zh": zh} for j, (ns, k, en, zh) in enumerate(b, 1)})
    print(f"送審 {len(items)} 條（{len({it[0] for it in items})} mod）→ {len(batches)} 批")


def _flags(p):
    """sonnet 標記檔；非 dict 的條目（"OK"、null）當作沒標記。"""
    d = C.load_json(p)
    if not isinstance(d, dict):
        raise ValueError(p)
    return {k: v for k, v in d.items() if isinstance(v, dict)}


def all_verdicts():
    """{batch: {aid: 判決}}，來源 verify/v_*.json（key＝batch/aid）。"""
    Q = q()
    out = {}
    for f in sorted((Q / "verify").glob("*.json")):
        try:
            d = C.load_json(f)
        except ValueError:
            f.unlink()
            continue
        if not isinstance(d, dict):
            f.unlink()
            continue
        for gid, v in d.items():
            if isinstance(v, dict):
                b, _, aid = gid.partition("/")
                out.setdefault(b, {})[aid] = v
    return out


def args(limit=None):
    """待 sonnet 審的批＋驗證組（只含還沒判決的標記條目，依嚴重度分模型，每次重建）。"""
    Q = q()
    verdicts = all_verdicts()
    rel = Q.relative_to(C.QUEUE.parent).as_posix()
    out, pend = [], {sev: [] for sev in VGROUP}
    for f in sorted(Q.glob("batch_*.json")):
        o = Q / "out" / f.name
        flags = None
        if o.exists():
            try:
                flags = _flags(o)
            except ValueError:
                o.unlink()
        if flags is None:
            out.append({"id": f.stem, "need": "sonnet", "in": f"{rel}/{f.name}", "out": f"{rel}/out/{f.name}"})
            continue
        body, have = C.load_json(f), verdicts.get(f.stem, {})
        for aid, flag in flags.items():
            if aid in body and aid not in have:
                sev = "error" if flag.get("sev") == "error" else "minor"
                pend[sev].append((f"{f.stem}/{aid}", {**body[aid], **{k: flag.get(k) for k in ("sev", "fix", "why")}}))
    vin = Q / "vin"
    vin.mkdir(parents=True, exist_ok=True)
    for p in vin.glob("*.json"):
        p.unlink()
    for sev, items in pend.items():
        model, size = VGROUP[sev]
        for i in range(0, len(items), size):
            chunk = items[i:i + size]
            # id 含整組內容雜湊：agent 漏判首條時下一輪的組 id 不同，不會覆寫已寫好的判決檔
            h = hashlib.sha1("\n".join(k for k, _ in chunk).encode()).hexdigest()[:8]
            gid = f"v_{sev}_{chunk[0][0].replace('/', '_')}_{h}"
            C.save_json(vin / f"{gid}.json", dict(chunk))
            out.append({"id": gid, "need": "verify", "model": model,
                        "in": f"{rel}/vin/{gid}.json", "verify": f"{rel}/verify/{gid}.json"})
    if limit:
        out = out[:limit]
    json.dump({"repo": str(C.REPO), "batches": out}, sys.stdout, ensure_ascii=False)
    print()


def final_fix(flag, verdict):
    """判決後要套用的譯文；None＝不改。"""
    if not isinstance(flag, dict) or not isinstance(verdict, dict):
        return None
    v = verdict.get("verdict")
    if v == "approve":
        return flag.get("fix")
    if v == "amend":
        return verdict.get("fix")
    return None


def merge():
    Q = q()
    apply, rows, done = {}, [], []
    stats = {"flagged": 0, "applied": 0, "rejected": 0, "no_fix": 0, "failed_check": 0, "stale": 0}
    sp = Q / "scope.txt"
    kind = sp.read_text().partition(":")[0] if sp.exists() else ""
    layer = kind if kind in ("conv", "mt") else "jar_tw"
    allv = all_verdicts()
    for f in sorted(Q.glob("batch_*.json")):
        o = Q / "out" / f.name
        if not o.exists():
            continue
        try:
            flags = _flags(o)
        except ValueError:
            continue  # 壞掉的標記檔：下次 args 會刪掉並重排這批
        body = C.load_json(f)
        verdicts = allv.get(f.stem, {})
        if any(aid in body and aid not in verdicts for aid in flags):
            continue  # 還有標記沒判決
        done.append(f)
        for aid, flag in flags.items():
            if aid not in body:
                continue  # agent 回報不存在的 id
            it = body[aid]
            stats["flagged"] += 1
            fix = final_fix(flag, verdicts.get(aid))
            # final_fix：判決後採用的原文（amend 的修法只在 verify 檔，merge 後會刪）
            row = {"batch": f.stem, "id": aid, "ns": it["ns"], "key": it["key"], "en": it["en"], "before": it["zh"],
                   "sev": flag.get("sev"), "why": flag.get("why"), "sonnet_fix": flag.get("fix"),
                   "verdict": (verdicts.get(aid) or {}).get("verdict"), "final_fix": fix, "after": None, "result": None,
                   "layer": layer}
            if isinstance(fix, str):
                fix = C.tw_fix(fix)  # 同 s08 對 data/mt 的處理：寫入值＝出貨值
            if fix is None and row["verdict"] in ("approve", "amend"):
                row["result"] = "驗證通過但沒有修法（略過）"
                stats["no_fix"] += 1
            elif fix is None or fix == it["zh"]:
                row["result"] = "驗證否決" if fix is None else "無變更"
                stats["rejected"] += fix is None
            elif not isinstance(fix, str) or (why := check_text(it["en"], fix)):
                row["result"] = f"驗證不過：{why if isinstance(fix, str) else '型別'}"
                stats["failed_check"] += 1
            else:
                row["after"] = fix
                apply[(it["ns"], it["key"], it["zh"])] = fix
            rows.append(row)

    shipped = {}
    for (ns, k, sent), fix in apply.items():
        if ns not in shipped:
            shipped[ns] = shown(ns)
        if shipped[ns].get(k) != sent:
            stats["stale"] += 1
            _mark(rows, ns, k, "送審後已改動（略過）")
            continue
        store.merge_into(C.DATA / "mt" / f"{ns}.json", {k: fix})
        store.set_prov(ns, {k: "audit"})
        stats["applied"] += 1
        _mark(rows, ns, k, "套用")

    store.log_rows("audit_log", rows)
    for f in done:
        for p in (f, Q / "out" / f.name):
            p.unlink(missing_ok=True)
    left = {f.stem for f in Q.glob("batch_*.json")}
    for vf in (Q / "verify").glob("v_*.json"):
        if not {k.partition("/")[0] for k in _load(vf)} & left:
            vf.unlink()
            (Q / "vin" / vf.name).unlink(missing_ok=True)
    stats["batches"] = len(done)
    stats["remaining"] = len(list(Q.glob("batch_*.json")))
    print(json.dumps(stats, ensure_ascii=False))


def _mark(rows, ns, key, result):
    """標記待寫入列的結果；沒寫入的列清掉 after（after＝實際寫入值）。"""
    for r in rows:
        if r["ns"] == ns and r["key"] == key and r["after"] is not None:
            r["result"] = result
            if result != "套用":
                r["after"] = None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prep", "args", "merge"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true", help="prep 時捨棄未合併的審查結果")
    ap.add_argument("--scope", default="jar_sample", help="jar_sample／jar:<mod,mod>／conv:<min>-<max>／mt:<min>-<max>")
    ap.add_argument("--queue", default="audit", help="queue/ 下的佇列目錄（同時跑多個範圍時分開）")
    a = ap.parse_args(argv)
    global QNAME
    QNAME = a.queue
    if a.cmd == "args":
        args(a.limit)
    elif a.cmd == "prep":
        prep(a.scope, a.force)
    else:
        merge()


if __name__ == "__main__":
    main()

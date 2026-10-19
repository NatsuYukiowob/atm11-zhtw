"""從官方 vanilla zh_cn/zh_tw 逐 key 配對，自動萃取「OpenCC 轉完仍不對」的術語對照表。

兩種規則：
  1. 全字串對照：短字串（≤14 字）整串不同 → 直接映射（如 下界合金錠→獄髓錠、刷怪籠→生怪磚）
  2. 子字串對照：用 SequenceMatcher 對齊差異片段，出現 ≥3 次且一致性 ≥80% 才收

再疊上 data/glossary_manual.json（人工覆寫，優先權最高；值為 null 表示封鎖自動規則）。
輸出 work/glossary.json（套用時依 key 長度由長到短取代）。
"""
import difflib
import re
from collections import Counter, defaultdict

from opencc import OpenCC

from common import DATA, WORK, load_json, save_json

CJK = re.compile(r"[一-鿿]")


def main():
    cc = OpenCC("s2twp")
    cn = load_json(WORK / "vanilla/zh_cn.json")
    tw = load_json(WORK / "vanilla/zh_tw.json")

    full_map = defaultdict(Counter)   # conv 全字串 -> tw 候選
    sub_map = defaultdict(Counter)    # conv 片段 -> tw 片段候選

    for k, cn_v in cn.items():
        tw_v = tw.get(k)
        if not tw_v or not isinstance(cn_v, str):
            continue
        # 旗幟圖紋名兩岸翻譯結構完全不同，挖出來全是垃圾對齊，整類排除
        if ".banner." in k or k.startswith("block.minecraft.banner"):
            continue
        conv = cc.convert(cn_v)
        if conv == tw_v:
            continue
        # 全字串規則最少 2 字元：單字元規則（如 Empty＝空/空白）套用時會無差別
        # 取代所有含該字的字串（空氣→空白氣、打開→打開啟），是毀滅性的
        if 2 <= len(conv) <= 14 and CJK.search(conv):
            full_map[conv][tw_v] += 1
        # 子字串規則只從「名稱型」配對挖（雙方都短）；長句的差異多是行文風格，
        # 拆成片段會產生毀滅性的誤取代（如 傳送→提交檢）
        if len(conv) > 14 or len(tw_v) > 14:
            continue
        sm = difflib.SequenceMatcher(None, conv, tw_v, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "replace":
                src, dst = conv[i1:i2], tw_v[j1:j2]
                # src/dst 必須是純 CJK（不含標點、空白、拉丁字），避免對齊碎片
                if 2 <= len(src) <= 8 and all(CJK.match(c) for c in src) and dst and all(CJK.match(c) for c in dst):
                    sub_map[src][dst] += 1

    glossary = {}
    # 子字串規則：頻率 ≥4 且主導性 ≥80%
    for src, cands in sub_map.items():
        dst, n = cands.most_common(1)[0]
        if n >= 4 and n / sum(cands.values()) >= 0.8:
            glossary[src] = dst
    # 全字串規則（蓋過子字串）：一致（唯一候選）即收
    for src, cands in full_map.items():
        if len(cands) == 1:
            glossary[src] = next(iter(cands))

    # 人工覆寫
    manual_path = DATA / "glossary_manual.json"
    manual = load_json(manual_path) if manual_path.exists() else {}
    manual.pop("_comment", None)
    for src, dst in manual.items():
        if dst is None:
            glossary.pop(src, None)
        else:
            glossary[src] = dst

    # 去掉無效規則（src == dst）與自我增長規則（src ⊂ dst）：
    # 後者在子字串取代下非冪等——「最小→最小值」套在已含「最小值」的正確譯文上
    # 會長成「最小值值」，且每套用一次再長一節。這類規則只在整串完全相等時才對，
    # 而本管線是子字串套用，直接剔除。
    # 例外：manual 的 src == dst 是保護詞（見 common.apply_glossary），保留。
    glossary = {s: d for s, d in glossary.items() if (s != d and s not in d) or (s == d and manual.get(s) == d)}

    save_json(WORK / "glossary.json", glossary)
    print(f"規則總數: {len(glossary)}（人工 {len(manual)} 條）")
    subs = [(s, d) for s, d in glossary.items() if len(s) <= 8 and s not in (manual or {})]
    print("\n=== 子字串規則抽樣（高頻差異，供人工檢查）===")
    for s, d in sorted(subs, key=lambda x: -sub_map[x[0]].total())[:40]:
        print(f"  {sub_map[s].total():4d}×  {s} → {d}")


if __name__ == "__main__":
    main()

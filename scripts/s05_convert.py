"""把簡中來源轉成繁中（OpenCC s2twp ＋ 術語表），產出每個 modid 的 zh_tw 檔與 MT 待翻清單。

目標 key ＝ en_us 有，而 jar 內建 zh_tw 缺 key **或值直接等於英文原文**的 key。
後者是「假翻譯」：不少 mod（minecolonies、twilightforest…）的 zh_tw 檔 key 一個不缺，
但未翻的條目就填英文原文，只看 key 有無會誤判成 100% 已翻而整包跳過。
來源優先序：jar 內建 zh_cn（版本最準）→ CFPA；來源值等於英文＝該來源也沒翻，往下一個來源找。
佔位符（%s、%1$s…）轉換前後必須一致，不一致的字串降級進 MT 清單。

輸出：
  work/zhtw_lang/<modid>.json   資源包用的 zh_tw lang
  work/todo/<modid>.json        需要機翻的 {key: en 原文}
  work/report_lang.json         覆蓋率統計
"""
import shutil

from common import WORK, load_json, placeholders, save_json, to_tw


def main():
    index = load_json(WORK / "extract/index.json")
    # 整個重建：modpack 更新後已不需要轉換／機翻的 mod，舊檔不得殘留（會被打包或重切批）
    for d in (WORK / "zhtw_lang", WORK / "todo"):
        if d.exists():
            shutil.rmtree(d)
    stats = {"mods": 0, "target": 0, "fake_tw": 0, "from_jar_cn": 0, "from_cfpa": 0, "todo": 0, "ph_demoted": 0}
    per_mod = {}

    for modid, info in sorted(index.items()):
        if not info["en_keys"]:
            continue
        en = load_json(WORK / f"extract/en/{modid}.json")
        tw_jar_p = WORK / f"extract/tw_jar/{modid}.json"
        tw_jar = load_json(tw_jar_p) if tw_jar_p.exists() else {}
        # 缺 key、或值直接等於英文原文（假翻譯）都算未翻
        targets = {k: v for k, v in en.items() if k not in tw_jar or tw_jar[k] == v}
        if not targets:
            continue
        stats["mods"] += 1
        stats["target"] += len(targets)
        stats["fake_tw"] += sum(1 for k in targets if k in tw_jar)

        sources = []
        p = WORK / f"extract/cn_jar/{modid}.json"
        if p.exists():
            sources.append(("jar_cn", load_json(p)))
        p = WORK / f"cfpa/{modid}.json"
        if p.exists():
            sources.append(("cfpa", load_json(p)))

        out, todo = {}, {}
        for k, en_v in targets.items():
            cn_v = None
            src_tag = None
            for tag, src in sources:
                v = src.get(k, "")
                # 來源值等於英文原文＝該來源自己也沒翻，不能當譯文用，往下一個來源找
                # （ars_elemental 的 309 條 jar 簡中全是英文，但 CFPA 有 307 條真譯文）
                if v.strip() and v != en_v:
                    cn_v, src_tag = v, tag
                    break
            if cn_v is None:
                todo[k] = en_v
                continue
            tw_v = to_tw(cn_v)
            if placeholders(tw_v) != placeholders(en_v):
                # 簡中來源的佔位符跟現在版本的 en 不一致（來源版本漂移），不能用
                todo[k] = en_v
                stats["ph_demoted"] += 1
                continue
            out[k] = tw_v
            stats["from_jar_cn" if src_tag == "jar_cn" else "from_cfpa"] += 1

        if out:
            save_json(WORK / f"zhtw_lang/{modid}.json", out)
        if todo:
            save_json(WORK / f"todo/{modid}.json", todo)
            stats["todo"] += len(todo)
        per_mod[modid] = {"target": len(targets), "converted": len(out), "todo": len(todo)}

    save_json(WORK / "report_lang.json", {"stats": stats, "per_mod": per_mod})
    print(f"目標 key: {stats['target']}（{stats['mods']} mods），其中假翻譯（jar zh_tw 值＝英文）: {stats['fake_tw']}")
    print(f"jar 內建簡中轉換: {stats['from_jar_cn']}；CFPA 轉換: {stats['from_cfpa']}")
    print(f"佔位符不符降級: {stats['ph_demoted']}")
    print(f"→ 待機翻: {stats['todo']}")
    worst = sorted(per_mod.items(), key=lambda kv: -kv[1]["todo"])[:15]
    print("\n待機翻最多的 mod:")
    for m, s in worst:
        if s["todo"]:
            print(f"  {s['todo']:5d}/{s['target']:5d}  {m}")


if __name__ == "__main__":
    main()

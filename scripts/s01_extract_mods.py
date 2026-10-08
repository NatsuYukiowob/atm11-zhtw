"""掃描 instance mods/*.jar 與 kubejs/assets/*/lang，抽出每個 modid 的 en_us / 內建 zh_tw / 內建 zh_cn lang，
以及 Patchouli 指南書頁面（en_us 與 zh_cn）。

輸出：
  work/extract/index.json           每個 modid 的 jar、key 數、內建語言概況
  work/extract/en/<modid>.json      en_us（同 modid 多 jar 時合併）
  work/extract/tw_jar/<modid>.json  jar 內建 zh_tw
  work/extract/cn_jar/<modid>.json  jar 內建 zh_cn
  work/extract/books/<modid>/<book>/<locale>/...  書頁原始 JSON
"""
import glob
import zipfile
from collections import defaultdict
from pathlib import PurePosixPath

from common import KUBEJS_DIR, MODS_DIR, WORK, jar_json, load_json, save_json

LANGS = {"en_us": "en", "zh_tw": "tw_jar", "zh_cn": "cn_jar"}


def main():
    merged = {v: defaultdict(dict) for v in LANGS.values()}
    index = defaultdict(lambda: {"jars": [], "en_keys": 0, "tw_jar_keys": 0, "cn_jar_keys": 0, "book_pages": {}})

    for jar in sorted(glob.glob(str(MODS_DIR / "*.jar"))):
        try:
            z = zipfile.ZipFile(jar)
        except Exception as e:
            print(f"⚠️ 開不了 {jar}: {e}")
            continue
        jarname = PurePosixPath(jar).name
        for n in z.namelist():
            parts = n.split("/")
            # assets/<modid>/lang/<locale>.json
            if len(parts) == 4 and parts[0] == "assets" and parts[2] == "lang" and parts[3].endswith(".json"):
                locale = parts[3][:-5]
                if locale not in LANGS:
                    continue
                d = jar_json(z, n)
                if not isinstance(d, dict):
                    print(f"⚠️ 解析失敗 {jarname}:{n}")
                    continue
                modid = parts[1]
                slot = LANGS[locale]
                merged[slot][modid].update({k: v for k, v in d.items() if isinstance(v, str)})
                if jarname not in index[modid]["jars"]:
                    index[modid]["jars"].append(jarname)
            # assets/<modid>/patchouli_books/<book>/<locale>/... .json
            if "/patchouli_books/" in n and n.endswith(".json") and parts[0] == "assets":
                bi = parts.index("patchouli_books")
                if len(parts) > bi + 3 and parts[bi + 2] in ("en_us", "zh_cn", "zh_tw"):
                    modid, book, locale = parts[1], parts[bi + 1], parts[bi + 2]
                    rel = "/".join(parts[bi + 3:])
                    d = jar_json(z, n)
                    if d is None:
                        continue
                    out = WORK / "extract/books" / modid / book / locale / rel
                    save_json(out, d)
                    key = f"{book}/{locale}"
                    index[modid]["book_pages"][key] = index[modid]["book_pages"].get(key, 0) + 1

    # KubeJS 自訂 lang（kubejs/assets/<ns>/lang/<locale>.json）視同一個名為 kubejs 的 jar
    for f in sorted((KUBEJS_DIR / "assets").glob("*/lang/*.json")):
        locale = f.stem
        if locale not in LANGS:
            continue
        try:
            d = load_json(f)
        except Exception as e:
            print(f"⚠️ 解析失敗 {f}: {e}")
            continue
        modid = f.parent.parent.name
        merged[LANGS[locale]][modid].update({k: v for k, v in d.items() if isinstance(v, str)})
        if "kubejs" not in index[modid]["jars"]:
            index[modid]["jars"].append("kubejs")

    for slot, mods in merged.items():
        for modid, d in mods.items():
            if d:
                save_json(WORK / f"extract/{slot}/{modid}.json", d)
                index[modid][f"{slot}_keys"] = len(d)

    save_json(WORK / "extract/index.json", dict(sorted(index.items())))

    n_mod = len(index)
    full = [m for m, i in index.items() if i["en_keys"] and i["tw_jar_keys"] >= i["en_keys"] * 0.95]
    partial = [m for m, i in index.items() if i["en_keys"] and 0 < i["tw_jar_keys"] < i["en_keys"] * 0.95]
    none = [m for m, i in index.items() if i["en_keys"] and not i["tw_jar_keys"]]
    print(f"modid 總數（有 lang）: {n_mod}")
    print(f"內建 zh_tw ≥95%: {len(full)}；部分翻譯: {len(partial)}；全缺: {len(none)}")
    gap = sum(i["en_keys"] - i["tw_jar_keys"] for i in index.values() if i["en_keys"])
    print(f"待補 key 總數（en - 內建tw，含部分翻譯的缺口）: {gap}")


if __name__ == "__main__":
    main()

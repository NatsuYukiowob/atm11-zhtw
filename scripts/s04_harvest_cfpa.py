"""從 CFPA repo（cfpa/projects/assets/<slug>/<ver>/<modid>/lang/zh_cn.json）
收割我們需要的 modid 的簡中翻譯。版本偏好：1.21 > 1.21-fabric > 1.20* > 1.19*（舊版只補缺 key；佔位符漂移由 s05 擋）。

輸出 work/cfpa/<modid>.json 與覆蓋率報告。
"""
from common import CFPA, WORK, load_json, save_json

PREF = ["1.21", "1.21-fabric", "1.20", "1.20-fabric", "1.19.3", "1.19", "1.19-fabric"]


def main():
    index = load_json(WORK / "extract/index.json")
    assets = CFPA / "projects/assets"

    # modid → {ver: path}
    found = {}
    for slug in assets.iterdir():
        if not slug.is_dir():
            continue
        for ver in slug.iterdir():
            if ver.name not in PREF or not ver.is_dir():
                continue
            for modid_dir in ver.iterdir():
                f = modid_dir / "lang/zh_cn.json"
                if f.is_file():
                    found.setdefault(modid_dir.name, {})[ver.name] = f

    hits, total_covered = 0, 0
    for modid, info in index.items():
        if not info["en_keys"] or modid not in found:
            continue
        en = load_json(WORK / f"extract/en/{modid}.json")
        merged = {}
        for ver in reversed(PREF):  # 低偏好先放，高偏好覆蓋
            p = found[modid].get(ver)
            if not p:
                continue
            try:
                d = load_json(p)
            except Exception as e:
                print(f"⚠️ {modid} {ver}: {e}")
                continue
            merged.update({k: v for k, v in d.items() if k in en and isinstance(v, str)})
        if merged:
            save_json(WORK / f"cfpa/{modid}.json", merged)
            hits += 1
            total_covered += len(merged)

    print(f"CFPA 命中 modid: {hits}，可用簡中 key 總數: {total_covered}")


if __name__ == "__main__":
    main()

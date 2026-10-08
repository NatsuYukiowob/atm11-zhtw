"""下載官方 Minecraft 1.20.1 的 zh_cn / zh_tw lang 檔（Mojang asset index）。
輸出 work/vanilla/{zh_cn,zh_tw}.json
"""
import json
import urllib.request

from common import MC_VERSION, WORK, save_json

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
RESOURCES = "https://resources.download.minecraft.net/{}/{}"


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def main():
    manifest = get(MANIFEST)
    ver = next(v for v in manifest["versions"] if v["id"] == MC_VERSION)
    meta = get(ver["url"])
    assets = get(meta["assetIndex"]["url"])["objects"]
    for locale in ("zh_cn", "zh_tw"):
        h = assets[f"minecraft/lang/{locale}.json"]["hash"]
        d = get(RESOURCES.format(h[:2], h))
        save_json(WORK / f"vanilla/{locale}.json", d)
        print(f"{locale}: {len(d)} keys")


if __name__ == "__main__":
    main()

"""把 work/todo/*.json 切成機翻批次 queue/lang/batch_NNN.json（{modid: {key: en}}，每批 200）。
已在 data/mt/<modid>.json 的 key 不重出 → 上一輪被退回或漏掉的 key 會自然重出（重跑安全）。
"""
import batchq
import common as C

BATCH = 200


def main():
    done = {f.stem: set(C.load_json(f)) for f in (C.DATA / "mt").glob("*.json")}
    items = []
    for f in sorted((C.WORK / "todo").glob("*.json")):
        for k, v in sorted(C.load_json(f).items()):
            if k not in done.get(f.stem, ()):
                items.append((f.stem, k, v))
    n = batchq.write_batches("lang", items, BATCH)
    print(f"待翻 {len(items)} key → {n} 批（每批 ≤{BATCH}）→ queue/lang/")


if __name__ == "__main__":
    main()

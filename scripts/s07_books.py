"""Patchouli 指南書繁中化。

來源優先序（per book）：jar 內建 zh_tw（直接用）→ jar 內建 zh_cn（OpenCC＋術語表轉換）
→ en_us（進 work/book_todo/ 待機翻）。

只轉換/翻譯「人類文字」欄位（TEXT_FIELDS），其他欄位（type、item、recipe、圖片路徑…）
原樣保留。值長得像 translation key（無空白的 a.b.c 型）也原樣保留 —— 這類書（如 Botania）
的文字走 lang 檔，已由 lang 管線處理。

輸出：
  work/books_tw/<modid>/<book>/<relpath>   已完成的 zh_tw 頁面（jar zh_tw 直用／zh_cn 轉換）
  queue/book/batch_NNN.json               待機翻的 en 頁面 {"<modid>/<book>/<rel>": page}；
                                          data/book_mt/ 已有的頁面不重出
"""
import re
import shutil

import batchq
import common as C
from common import load_json, save_json, to_tw

BATCH = 20

TEXT_FIELDS = {"name", "title", "subtitle", "text", "description", "landing_text", "header"}
DOTTED_KEY = re.compile(r"^[A-Za-z0-9_/-]+(\.[A-Za-z0-9_/-]+)+$")   # a.b.c（含駝峰）
NAMESPACED = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")            # modid:path


def is_text(v):
    """真的需要翻譯的人類文字：排除 translation key、資源 ID 與 template 佔位符（#foo）。"""
    v = v.strip()
    return bool(v) and not v.startswith("#") and not DOTTED_KEY.match(v) and not NAMESPACED.match(v)

def walk(obj, fn):
    """遞迴走訪 JSON，對 TEXT_FIELDS 的字串值套 fn；回傳 (新物件, 是否含可翻文字)。"""
    has_text = False
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if k in TEXT_FIELDS and isinstance(v, str) and is_text(v):
                new[k] = fn(v)
                has_text = True
            else:
                new[k], sub = walk(v, fn) if isinstance(v, (dict, list)) else (v, False)
                has_text = has_text or sub
        return new, has_text
    if isinstance(obj, list):
        outs = [walk(x, fn) if isinstance(x, (dict, list)) else (x, False) for x in obj]
        return [o for o, _ in outs], any(h for _, h in outs)
    return obj, False


def main():
    books_root = C.WORK / "extract/books"
    if (C.WORK / "books_tw").exists():
        shutil.rmtree(C.WORK / "books_tw")
    todo = []

    stats = {"tw": 0, "cn2tw": 0, "todo": 0, "keyonly": 0}
    for modid_dir in sorted(books_root.iterdir()):
        for book_dir in sorted(modid_dir.iterdir()):
            locales = {p.name for p in book_dir.iterdir()}
            for locale in ("zh_tw", "zh_cn", "en_us"):
                if locale not in locales:
                    continue
                for f in sorted((book_dir / locale).rglob("*.json")):
                    rel = f.relative_to(book_dir / locale)
                    out = C.WORK / "books_tw" / modid_dir.name / book_dir.name / rel
                    if out.exists():  # 高優先來源已處理過
                        continue
                    page = load_json(f)
                    if locale == "zh_tw":
                        save_json(out, page)
                        stats["tw"] += 1
                    elif locale == "zh_cn":
                        conv, _ = walk(page, to_tw)
                        save_json(out, conv)
                        stats["cn2tw"] += 1
                    else:
                        key = f"{modid_dir.name}/{book_dir.name}/{rel.as_posix()}"
                        _, has_text = walk(page, lambda s: s)
                        if not has_text:
                            # 純 lang-key 書頁：文字由 lang 管線處理，頁面本身不用出
                            stats["keyonly"] += 1
                        elif (C.DATA / "book_mt" / key).exists():
                            stats["done"] = stats.get("done", 0) + 1
                        else:
                            todo.append((None, key, page))
                            stats["todo"] += 1

    n = batchq.write_batches("book", todo, BATCH)
    print(f"jar zh_tw 直用: {stats['tw']}；zh_cn 轉換: {stats['cn2tw']}；"
          f"純 key 頁(略): {stats['keyonly']}；已機翻: {stats.get('done', 0)}；待機翻: {stats['todo']} → {n} 批")


if __name__ == "__main__":
    main()

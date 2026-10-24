"""組裝資源包＋任務書：lang（轉換＋機翻合併）＋ Patchouli 書頁 → dist/atm11-zhtw.zip（含 sha1）、dist/ftbquests/zh_tw/（任務書 lang 同構目錄）。

機翻層（data/mt、data/book_mt、data/quests_mt.json）打包前再過一次 tw_fix（夾簡體才轉、否則只套術語表；
OpenCC 對 LLM 寫的繁體會改壞）：術語表修正後要靠這裡才會套到；再轉後不收斂的保留原值（合併時已驗過）。轉換層（work/）每次由 s05/s07/s07q
重建，已收斂，不再轉（OpenCC 對繁體再轉會出錯，如 演算法→演演算法）。
最終驗證：每條 lang 值再過一次佔位符比對；任務書再過 check_value。
zip 用固定時間戳，內容不變則 sha1 不變（客戶端快取友善）。
"""
import hashlib
import json
import shutil
import zipfile

import common as C
import quests_io
from common import DATA, DIST, PACK_FORMAT, REPO, WORK, load_json, placeholders
from s07_books import walk
from validate import check_value

DESC = "ATM11 繁體中文化包（CFPA轉繁+LLM補翻，haiku/sonnet/opus）"
ZIP_DATE = (2026, 1, 1, 0, 0, 0)


def reconv(s):
    """機翻值套用目前術語表（tw_fix）；不收斂（術語表振盪）就保留原值。"""
    t = C.tw_fix(s)
    return t if C.tw_fix(t) == t else s


def reconv_value(v):
    return [reconv(x) for x in v] if isinstance(v, list) else reconv(v)


def build_quests():
    """回傳 ({en_us 相對路徑: {key: 譯文}}, 驗證剔除數)，檔案切分與 en_us 相同。

    instance 內建 zh_tw（非假翻譯）是人工譯文，原樣採用；簡中轉換與機翻每條再過
    check_value，不過的剔除（遊戲回退英文）。
    """
    en_files = quests_io.load_dir(C.QUESTS_LANG_DIR / "en_us")
    tw = quests_io.load_flat(C.QUESTS_LANG_DIR / "zh_tw")
    # (譯文, 是否人工來源)；機翻蓋過轉換（與 s07q 的優先序一致）
    ours = {}
    for p, human in ((C.WORK / "quests_tw.json", True), (C.DATA / "quests_mt.json", False)):
        if p.exists():
            ours.update({k: (v if human else reconv_value(v), human) for k, v in load_json(p).items()})
    files, dropped = {}, 0
    for rel, en in en_files.items():
        out = {}
        for k, ev in en.items():
            if k in tw and tw[k] != ev:
                out[k] = tw[k]
            elif k in ours:
                v, human = ours[k]
                if check_value(ev, v, amp_codes=True, human=human):
                    dropped += 1
                    continue
                out[k] = v
        if out:
            files[rel] = out
    return files, dropped


def write_quests(out_dir, files):
    """整個目錄重建：上一版的檔不得殘留（s12 會整包交付）。"""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    if files:
        quests_io.dump_dir(out_dir / "zh_tw", files)


def main():
    entries = {}  # zip 內路徑 -> bytes

    # --- lang ---
    stats = {"mods": 0, "keys": 0, "ph_dropped": 0}
    modids = {p.stem for p in (WORK / "zhtw_lang").glob("*.json")}
    modids |= {p.stem for p in (DATA / "mt").glob("*.json")} if (DATA / "mt").exists() else set()
    for modid in sorted(modids):
        merged = {}
        for src in (WORK / f"zhtw_lang/{modid}.json", DATA / f"mt/{modid}.json"):
            if src.exists():
                vals = load_json(src)
                merged.update({k: reconv(v) for k, v in vals.items()} if src.parent.name == "mt" else vals)
        if not merged:
            continue
        en_p = WORK / f"extract/en/{modid}.json"
        en = load_json(en_p) if en_p.exists() else {}
        clean = {}
        for k, v in merged.items():
            if k in en and placeholders(v) != placeholders(en[k]):
                stats["ph_dropped"] += 1
                continue
            clean[k] = v
        if not clean:
            continue
        entries[f"assets/{modid}/lang/zh_tw.json"] = json.dumps(
            clean, ensure_ascii=False, indent=1, sort_keys=True).encode()
        stats["mods"] += 1
        stats["keys"] += len(clean)

    # --- Patchouli 書頁（work/books_tw = jar 簡中轉換；data/book_mt = 已驗證機翻，進版控）---
    n_pages = 0
    for books_root in (WORK / "books_tw", DATA / "book_mt"):
        if not books_root.exists():
            continue
        for f in sorted(books_root.rglob("*.json")):
            modid, book, *rest = f.relative_to(books_root).parts
            name = f"assets/{modid}/patchouli_books/{book}/zh_tw/{'/'.join(rest)}"
            if books_root == DATA / "book_mt":
                page, _ = walk(load_json(f), reconv)
                entries[name] = json.dumps(page, ensure_ascii=False, indent=1).encode()
            else:
                entries[name] = f.read_bytes()
            n_pages += 1

    entries["pack.mcmeta"] = json.dumps(
        {"pack": {"pack_format": PACK_FORMAT, "description": DESC}},
        ensure_ascii=False, indent=2).encode()

    DIST.mkdir(exist_ok=True)
    zip_path = DIST / "atm11-zhtw.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(entries):
            zi = zipfile.ZipInfo(name, date_time=ZIP_DATE)
            zi.external_attr = 0o644 << 16
            z.writestr(zi, entries[name], compress_type=zipfile.ZIP_DEFLATED)

    sha1 = hashlib.sha1(zip_path.read_bytes()).hexdigest()
    (DIST / "atm11-zhtw.zip.sha1").write_text(sha1 + "\n")

    print(f"lang: {stats['mods']} mods / {stats['keys']} keys（佔位符不符剔除 {stats['ph_dropped']}）")
    print(f"書頁: {n_pages}")
    print(f"→ {zip_path}  ({zip_path.stat().st_size/1024:.0f} KB)")
    print(f"sha1: {sha1}")
    quests, q_dropped = build_quests()
    write_quests(DIST / "ftbquests", quests)
    shutil.copy(REPO / "docs/INSTALL.txt", DIST / "INSTALL.txt")
    n_q = sum(len(v) for v in quests.values())
    print(f"任務書: {n_q} 條／{len(quests)} 檔（驗證剔除 {q_dropped}）→ {DIST / 'ftbquests/zh_tw'}")


if __name__ == "__main__":
    main()

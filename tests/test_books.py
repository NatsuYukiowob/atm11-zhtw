import batchq
import common
import s07_books
import s07b_merge_books

PAGE = {"name": "Intro", "icon": "minecraft:book", "pages": [{"type": "text", "text": "Craft a $(item)Gear/$."}]}


def test_s07_skips_done_and_queues_todo(repo):
    base = common.WORK / "extract/books/m/guide/en_us"
    common.save_json(base / "entries/a.json", PAGE)
    common.save_json(base / "entries/b.json", PAGE)
    common.save_json(common.DATA / "book_mt/m/guide/entries/a.json", PAGE)
    s07_books.main()
    assert common.load_json(common.QUEUE / "book/batch_001.json") == {"m/guide/entries/b.json": PAGE}


def test_merge_good_and_bad(repo):
    batchq.write_batches("book", [(None, "m/g/a.json", PAGE), (None, "m/g/b.json", PAGE), (None, "m/g/c.json", PAGE)], 20)
    good = {"name": "簡介", "icon": "minecraft:book", "pages": [{"type": "text", "text": "製作一個$(item)齒輪/$。"}]}
    bad = {"name": "簡介", "icon": "minecraft:stick", "pages": [{"type": "text", "text": "製作一個$(item)齒輪/$。"}]}
    common.save_json(common.QUEUE / "book/out/batch_001.json", {"m/g/a.json": good, "m/g/b.json": bad})
    s07b_merge_books.main(["--model", "haiku"])
    assert common.load_json(common.DATA / "book_mt/m/g/a.json") == good
    assert not (common.DATA / "book_mt/m/g/b.json").exists()
    assert not (common.DATA / "book_mt/m/g/c.json").exists()
    assert common.load_json(common.DATA / "prov/_books.json") == {"m/g/a.json": "haiku"}


def test_check_symbol_in_text_field():
    o = {"text": "✔ Done"}
    assert s07b_merge_books.check(o, {"text": "完成"})

import common
import quests_io
import s08_build_pack


def test_build_quests(tmp_path, monkeypatch, repo):
    ql = tmp_path / "ql"
    quests_io.dump_dir(ql / "en_us", {"chapter.json5": {"a": "Open menu", "b": "B"},
                                      "chapters/x.json5": {"c": "&aC", "d": "D"}})
    # instance 內建繁中是人工譯文：不受 to_tw 冪等檢查（點擊打開 → s2twp 會改寫）
    quests_io.dump_dir(ql / "zh_tw", {"chapter.json5": {"a": "右鍵點擊打開選單"}, "chapters/x.json5": {"d": "D"}})
    monkeypatch.setattr(common, "QUESTS_LANG_DIR", ql)
    common.save_json(common.WORK / "quests_tw.json", {"b": "乙"})
    common.save_json(common.DATA / "quests_mt.json", {"c": "丙"})
    files, dropped = s08_build_pack.build_quests()
    assert files == {"chapter.json5": {"a": "右鍵點擊打開選單", "b": "乙"}} and dropped == 1


def test_write_quests_clears_stale(tmp_path):
    out = tmp_path / "ftbquests"
    s08_build_pack.write_quests(out, {"chapters/old.json5": {"k": "舊"}})
    s08_build_pack.write_quests(out, {})
    assert not out.exists()


def test_build_quests_human_conversion_lenient(tmp_path, monkeypatch, repo):
    ql = tmp_path / "ql"
    quests_io.dump_dir(ql / "en_us", {"chapter.json5": {"q": ["A &aB&r\n\nC"], "m": ["X &aY&r\n\nZ"]}})
    monkeypatch.setattr(common, "QUESTS_LANG_DIR", ql)
    common.save_json(common.WORK / "quests_tw.json", {"q": ["甲 &a乙", "", "丙"]})
    common.save_json(common.DATA / "quests_mt.json", {"m": ["甲 &a乙", "", "丙"]})
    files, dropped = s08_build_pack.build_quests()
    assert files == {"chapter.json5": {"q": ["甲 &a乙", "", "丙"]}} and dropped == 1


def test_build_quests_reconverts_mt_only(tmp_path, monkeypatch, repo):
    # 機翻值在合併時已 to_tw 寫死；改術語表後打包要再轉一次。人工簡中轉換層（s07q 每次重建）不再轉
    monkeypatch.setattr(common, "_glossary_rules", [("代設計器", "程式設計器")])
    ql = tmp_path / "ql"
    quests_io.dump_dir(ql / "en_us", {"chapter.json5": {"a": "Logic Programmer", "b": "Logic Programmer"}})
    monkeypatch.setattr(common, "QUESTS_LANG_DIR", ql)
    common.save_json(common.WORK / "quests_tw.json", {"b": "邏輯程式"})
    common.save_json(common.DATA / "quests_mt.json", {"a": "邏輯代設計器"})
    files, dropped = s08_build_pack.build_quests()
    assert files == {"chapter.json5": {"a": "邏輯程式設計器", "b": "邏輯程式"}} and dropped == 0


def test_main_reconverts_lang_and_books(tmp_path, monkeypatch, repo):
    import json, zipfile
    monkeypatch.setattr(common, "_glossary_rules", [("代設計器", "程式設計器")])
    monkeypatch.setattr(common, "QUESTS_LANG_DIR", tmp_path / "noquests")
    monkeypatch.setattr(s08_build_pack, "WORK", common.WORK)
    monkeypatch.setattr(s08_build_pack, "DATA", common.DATA)
    monkeypatch.setattr(s08_build_pack, "DIST", common.DIST)
    common.save_json(common.WORK / "extract/en/m.json", {"k": "Logic Programmer"})
    common.save_json(common.DATA / "mt/m.json", {"k": "邏輯代設計器", "c": "右鍵點擊背包"})
    common.save_json(common.DATA / "book_mt/m/b/entries/e.json",
                     {"name": "邏輯代設計器", "pages": [{"type": "patchouli:text", "text": "用邏輯代設計器"}]})
    s08_build_pack.main()
    z = zipfile.ZipFile(common.DIST / "atm11-zhtw.zip")
    # 機翻層只套術語表、不跑 OpenCC（點擊→點選、背包→揹包 不可發生）
    assert json.loads(z.read("assets/m/lang/zh_tw.json")) == {"k": "邏輯程式設計器", "c": "右鍵點擊背包"}
    assert json.loads(z.read("assets/m/patchouli_books/b/zh_tw/entries/e.json")) == {
        "name": "邏輯程式設計器", "pages": [{"type": "patchouli:text", "text": "用邏輯程式設計器"}]}


def test_main_reconverts_only_mt_layers(tmp_path, monkeypatch, repo):
    # s05/s07 每次重建的轉換層已收斂；再轉會讓 OpenCC 對繁體再轉（演算法→演演算法）。不收斂的值保留原值
    import json, zipfile
    monkeypatch.setattr(common, "_glossary_rules", [("甲", "乙"), ("乙", "甲")])
    monkeypatch.setattr(common, "QUESTS_LANG_DIR", tmp_path / "noquests")
    for n in ("WORK", "DATA", "DIST"):
        monkeypatch.setattr(s08_build_pack, n, getattr(common, n))
    common.save_json(common.WORK / "extract/en/m.json", {"a": "Algorithm", "b": "A"})
    common.save_json(common.WORK / "zhtw_lang/m.json", {"a": "演算法"})
    common.save_json(common.DATA / "mt/m.json", {"b": "甲"})
    common.save_json(common.WORK / "books_tw/m/b/entries/e.json", {"name": "演算法"})
    s08_build_pack.main()
    z = zipfile.ZipFile(common.DIST / "atm11-zhtw.zip")
    assert json.loads(z.read("assets/m/lang/zh_tw.json")) == {"a": "演算法", "b": "甲"}
    assert json.loads(z.read("assets/m/patchouli_books/b/zh_tw/entries/e.json")) == {"name": "演算法"}

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

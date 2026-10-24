import batchq
import common
import quests_io
import s07q_merge
import s07q_quests


def _setup(tmp_path, monkeypatch, en, cn=None, tw=None):
    ql = tmp_path / "ql"
    quests_io.dump_dir(ql / "en_us", {"chapter.json5": en})
    if cn:
        quests_io.dump_dir(ql / "zh_cn", {"chapter.json5": cn})
    if tw:
        quests_io.dump_dir(ql / "zh_tw", {"chapter.json5": tw})
    monkeypatch.setattr(common, "QUESTS_LANG_DIR", ql)


def test_extract(tmp_path, monkeypatch, repo):
    en = {"a.title": "Video", "b.title": "Iron", "c.desc": ["Hi", ""], "d.title": "Done"}
    _setup(tmp_path, monkeypatch, en, cn={"a.title": "视频"}, tw={"d.title": "完成"})
    common.save_json(common.DATA / "quests_mt.json", {"b.title": "鐵"})
    s07q_quests.main()
    assert common.load_json(common.WORK / "quests_tw.json") == {"a.title": "影片"}
    assert common.load_json(common.QUEUE / "quest/batch_001.json") == {"c.desc": ["Hi", ""]}


def test_merge_list_values(repo):
    batchq.write_batches("quest", [(None, "q.desc", ["&aGo", "", "Now"]), (None, "q.t", "Go")], 60)
    common.save_json(common.QUEUE / "quest/out/batch_001.json",
                     {"q.desc": ["&a出發", "", "現在"], "q.t": ["出發"]})
    s07q_merge.main(["--model", "haiku"])
    assert common.load_json(common.DATA / "quests_mt.json") == {"q.desc": ["&a出發", "", "現在"]}
    assert common.load_json(common.DATA / "prov/_quests.json") == {"q.desc": "haiku"}


def test_extract_human_line_split_accepted(tmp_path, monkeypatch, repo):
    en = {"q.desc": ["Go &aNow&r\n\nMore here"]}
    _setup(tmp_path, monkeypatch, en, cn={"q.desc": ["出发 &a现在", "", "更多"]})
    s07q_quests.main()
    assert common.load_json(common.WORK / "quests_tw.json") == {"q.desc": ["出發 &a現在", "", "更多"]}


def test_to_tw_value_restores_double_escaped_newline():
    # 人工簡中任務書的值裡是「兩個反斜線＋n」，遊戲內顯示成字面；英文原文是真換行
    import s07q_quests
    assert s07q_quests.to_tw_value(["甲\\\\n\\\\n乙"]) == ["甲\n\n乙"]


def test_extract_rejects_unconverged_conversion(tmp_path, monkeypatch, repo):
    # 轉換層（簡中→to_tw）不收斂（術語表振盪）→ 不收，改走機翻
    monkeypatch.setattr(common, "_glossary_rules", [("甲乙", "甲乙乙")])  # 每輪都再變長，5 輪內不收斂
    _setup(tmp_path, monkeypatch, {"a.title": "AB", "b.title": "Video"}, cn={"a.title": "甲乙", "b.title": "视频"})
    s07q_quests.main()
    assert common.load_json(common.WORK / "quests_tw.json") == {"b.title": "影片"}
    assert common.load_json(common.QUEUE / "quest/batch_001.json") == {"a.title": "AB"}

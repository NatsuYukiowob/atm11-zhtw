import common


def test_constants():
    assert common.MC_VERSION == "1.21.1"
    assert common.PACK_FORMAT == 34


def test_placeholders_multiset():
    assert common.placeholders("%s and %1$s %%") == ("%%", "%1$s", "%s")


def test_to_tw_converts_simplified():
    assert common.to_tw("视频") == "影片"


def test_to_tw_reaches_fixed_point(monkeypatch):
    # 長規則優先、單次順序取代：ADE →(DE→BC) ABC，要再一輪才會 →(ABC→X) X
    monkeypatch.setattr(common, "_glossary_rules", [("ABC", "X"), ("DE", "BC")])
    once = common.to_tw("ADE")
    assert once == "X" and common.to_tw(once) == once


def test_load_json_tolerates_bom(tmp_path):
    p = tmp_path / "x.json"
    p.write_bytes("﻿".encode() + b'{"a": "b"}')
    assert common.load_json(p) == {"a": "b"}


def test_manual_glossary_keeps_algorithm_fixed_point(monkeypatch):
    # s2twp 把已是繁體的「演算法」再轉成「演演算法」→ 靠 glossary_manual 的定點規則收斂
    g = common.load_json(common.REPO / "data/glossary_manual.json")
    rules = sorted(((k, v) for k, v in g.items() if isinstance(v, str) and not k.startswith("_")), key=lambda kv: -len(kv[0]))
    monkeypatch.setattr(common, "_glossary_rules", rules)
    assert common.to_tw("演算法") == "演算法"
    assert common.to_tw("计算算法") == "計算演算法"

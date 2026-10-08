import pytest

import quests_io

CHAPTER = '{\n  "chapter.A.title": "Hi",\n  "q.B.desc": [\n    "a",\n    "",\n  ],\n}\n'


def _write(d, rel, text):
    p = d / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_load_dir_trailing_commas(tmp_path):
    d = tmp_path / "en_us"
    _write(d, "chapter.json5", CHAPTER)
    _write(d, "chapters/x.json5", '{"q.C.title": "Forbidden \\\\& Arcanus",}')
    assert quests_io.load_dir(d) == {
        "chapter.json5": {"chapter.A.title": "Hi", "q.B.desc": ["a", ""]},
        "chapters/x.json5": {"q.C.title": "Forbidden \\& Arcanus"},
    }
    assert quests_io.load_flat(d) == {"chapter.A.title": "Hi", "q.B.desc": ["a", ""], "q.C.title": "Forbidden \\& Arcanus"}


def test_comma_inside_string_untouched():
    assert quests_io.loads('{"a": "x, ]", "b": ["y, }",],}') == {"a": "x, ]", "b": ["y, }"]}


def test_missing_dir_is_empty(tmp_path):
    assert quests_io.load_dir(tmp_path / "zh_tw") == {}


def test_nested_value_rejected():
    with pytest.raises(ValueError):
        quests_io.loads('{"a": {"b": "c"}}')


def test_dump_roundtrip(tmp_path):
    files = {"chapters/x.json5": {"k": "繁中 ✔", "l": ["第一行", ""]}}
    quests_io.dump_dir(tmp_path / "zh_tw", files)
    assert quests_io.load_dir(tmp_path / "zh_tw") == files
    assert "繁中" in (tmp_path / "zh_tw/chapters/x.json5").read_text(encoding="utf-8")

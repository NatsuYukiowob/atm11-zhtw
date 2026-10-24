import pytest

import s13_api_run as r


def test_parse():
    assert r.parse('{"a": 1}\n\n說明') == {"a": 1}
    assert r.parse('```json\n{"b": 2}\n```') == {"b": 2}
    for bad in ("[1]", "```json", "沒有 JSON"):
        with pytest.raises(ValueError):
            r.parse(bad)


def test_scope_of(tmp_path):
    (tmp_path / "queue/q/vin").mkdir(parents=True)
    (tmp_path / "queue/q/scope.txt").write_text("mt:1-80\n")
    assert r.scope_of(tmp_path, "queue/q/vin/v_x.json") == "mt:1-80"
    (tmp_path / "queue/old").mkdir()
    with pytest.raises(SystemExit):
        r.scope_of(tmp_path, "queue/old/batch_001.json")

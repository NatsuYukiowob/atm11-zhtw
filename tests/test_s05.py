import common
import s05_convert


def test_stale_outputs_cleared(repo, monkeypatch):
    monkeypatch.setattr(s05_convert, "WORK", common.WORK)
    common.save_json(common.WORK / "extract/index.json", {"x": {"en_keys": 1}})
    common.save_json(common.WORK / "extract/en/x.json", {"k": "A"})
    common.save_json(common.WORK / "extract/tw_jar/x.json", {"k": "甲"})
    common.save_json(common.WORK / "zhtw_lang/x.json", {"k": "舊轉換"})
    common.save_json(common.WORK / "todo/x.json", {"k": "A"})
    s05_convert.main()
    assert not (common.WORK / "zhtw_lang/x.json").exists()
    assert not (common.WORK / "todo/x.json").exists()

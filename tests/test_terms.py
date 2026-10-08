import common
import s10_terms


def _seed():
    common.save_json(common.WORK / "extract/en/a.json", {"item.a.gear": "Iron Gear", "item.a.x": "X"})
    common.save_json(common.WORK / "extract/en/b.json", {"item.b.gear": "Iron Gear", "tooltip.b": "Iron Gear"})
    common.save_json(common.WORK / "zhtw_lang/a.json", {"item.a.gear": "鐵齒輪"})
    common.save_json(common.DATA / "mt/b.json", {"item.b.gear": "鐵製齒輪", "tooltip.b": "鐵製齒輪"})
    common.save_json(common.DATA / "prov/b.json", {"item.b.gear": "haiku", "tooltip.b": "haiku"})


def test_collect(repo):
    _seed()
    got = s10_terms.collect()
    assert got == {"Iron Gear": {"鐵齒輪": ["a:item.a.gear@conv"], "鐵製齒輪": ["b:item.b.gear@haiku"]}}


def test_apply_rewrites_only_name_keys(repo):
    _seed()
    s10_terms.main(["prep"])
    common.save_json(common.QUEUE / "terms/out/batch_001.json", {"Iron Gear": "鐵齒輪"})
    s10_terms.main(["apply"])
    assert common.load_json(common.DATA / "mt/b.json") == {"item.b.gear": "鐵齒輪", "tooltip.b": "鐵製齒輪"}
    assert common.load_json(common.DATA / "terms_canon.json") == {"Iron Gear": "鐵齒輪"}


def test_apply_rejects_canon_failing_validation(repo):
    common.save_json(common.WORK / "extract/en/a.json", {"item.a.g": "§6Gear ★"})
    common.save_json(common.WORK / "extract/en/b.json", {"item.b.g": "§6Gear ★"})
    common.save_json(common.WORK / "zhtw_lang/a.json", {"item.a.g": "§6齒輪 ★"})
    common.save_json(common.DATA / "mt/b.json", {"item.b.g": "§6齒輪組 ★"})
    common.save_json(common.DATA / "prov/b.json", {"item.b.g": "haiku"})
    s10_terms.main(["prep"])
    common.save_json(common.QUEUE / "terms/out/batch_001.json", {"§6Gear ★": "齒輪"})
    s10_terms.main(["apply"])
    assert common.load_json(common.DATA / "mt/b.json") == {"item.b.g": "§6齒輪組 ★"}
    assert common.load_json(common.DATA / "terms_canon.json") == {}


def test_apply_keeps_batch_on_corrupt_output(repo):
    _seed()
    s10_terms.main(["prep"])
    (common.QUEUE / "terms/out").mkdir(parents=True, exist_ok=True)
    (common.QUEUE / "terms/out/batch_001.json").write_text('{"Iron Gear": "鐵', encoding="utf-8")
    s10_terms.main(["apply"])
    assert (common.QUEUE / "terms/batch_001.json").exists()
    assert not (common.QUEUE / "terms/out/batch_001.json").exists()

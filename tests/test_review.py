import json

import common
import s10_review

A = "Iron Ingot is smelted from raw iron in a furnace and used across most early-game crafting recipes."
B = "Holds %s items; shift-right-click to open the configuration screen and adjust filters for each slot."


def test_prep_and_merge(repo):
    common.save_json(common.WORK / "extract/en/m.json", {"a": A, "b": B})
    common.save_json(common.DATA / "mt/m.json", {"a": "鐵棒", "b": "%s 個物品"})
    common.save_json(common.DATA / "prov/m.json", {"a": "haiku", "b": "sonnet"})
    s10_review.main(["prep"])
    b = common.load_json(common.QUEUE / "review/batch_001.json")
    assert b == {"m": {"a": {"en": A, "zh": "鐵棒"}, "b": {"en": B, "zh": "%s 個物品"}}}
    common.save_json(common.QUEUE / "review/out/batch_001.json", {"m": {"a": "鐵錠", "b": "物品"}})
    s10_review.main(["merge"])
    assert common.load_json(common.DATA / "mt/m.json") == {"a": "鐵錠", "b": "%s 個物品"}
    assert common.load_json(common.DATA / "prov/m.json")["a"] == "opus"
    rows = {r["key"]: r for r in map(json.loads, (common.DATA / "review_log.jsonl").read_text().splitlines())}
    assert rows["a"]["changed"] and rows["a"]["prev_model"] == "haiku"
    assert not rows["b"]["changed"] and rows["b"]["why"]


def test_merge_skips_stale(repo):
    common.save_json(common.WORK / "extract/en/m.json", {"a": A})
    common.save_json(common.DATA / "mt/m.json", {"a": "鐵棒"})
    common.save_json(common.DATA / "prov/m.json", {"a": "haiku"})
    s10_review.main(["prep"])
    common.save_json(common.DATA / "mt/m.json", {"a": "鐵條"})
    common.save_json(common.QUEUE / "review/out/batch_001.json", {"m": {"a": "鐵錠"}})
    s10_review.main(["merge"])
    assert common.load_json(common.DATA / "mt/m.json") == {"a": "鐵條"}


def test_merge_keeps_batch_on_corrupt_output(repo):
    common.save_json(common.WORK / "extract/en/m.json", {"a": A})
    common.save_json(common.DATA / "mt/m.json", {"a": "鐵棒"})
    common.save_json(common.DATA / "prov/m.json", {"a": "haiku"})
    s10_review.main(["prep"])
    (common.QUEUE / "review/out").mkdir(parents=True, exist_ok=True)
    (common.QUEUE / "review/out/batch_001.json").write_text('{"m": {"a": "鐵', encoding="utf-8")
    s10_review.main(["merge"])
    assert (common.QUEUE / "review/batch_001.json").exists()
    assert not (common.QUEUE / "review/out/batch_001.json").exists()
    assert not (common.DATA / "review_log.jsonl").exists()


def test_prep_lang_only_long_entries(repo):
    long_en = "This machine converts raw ore into dust with a small chance of a bonus output per operation."
    common.save_json(common.WORK / "extract/en/m.json", {"a": "Iron Ingot", "b": long_en})
    common.save_json(common.DATA / "mt/m.json", {"a": "鐵錠", "b": "長譯文"})
    common.save_json(common.DATA / "prov/m.json", {"a": "haiku", "b": "haiku"})
    s10_review.main(["prep"])
    assert common.load_json(common.QUEUE / "review/batch_001.json") == {"m": {"b": {"en": long_en, "zh": "長譯文"}}}

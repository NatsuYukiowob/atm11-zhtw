import json

import batchq
import common
import s06_merge_mt


def _rows():
    return [json.loads(l) for l in (common.DATA / "merge_log.jsonl").read_text().splitlines()]


def test_merge_good_bad_missing(repo):
    batchq.write_batches("lang", [("m", "a", "Iron Ingot"), ("m", "b", "%s items"), ("m", "c", "Gold")], 10)
    common.save_json(common.QUEUE / "lang/out/batch_001.json", {"m": {"a": "鐵錠", "b": "物品"}})
    s06_merge_mt.main(["--model", "haiku"])
    assert common.load_json(common.DATA / "mt/m.json") == {"a": "鐵錠"}
    assert common.load_json(common.DATA / "prov/m.json") == {"a": "haiku"}
    rows = {r["key"]: r for r in _rows()}
    assert rows["a"]["ok"] and not rows["b"]["ok"] and rows["c"]["why"] == "缺漏"
    assert rows["a"]["model"] == "haiku" and rows["a"]["len"] == len("Iron Ingot")
    assert not list((common.QUEUE / "lang").glob("batch_*.json"))


def test_merge_broken_json_rejects_all(repo):
    batchq.write_batches("lang", [("m", "a", "Iron")], 10)
    (common.QUEUE / "lang/out").mkdir(parents=True)
    (common.QUEUE / "lang/out/batch_001.json").write_text('{"m": {"a": "鐵"')
    s06_merge_mt.main(["--model", "haiku"])
    assert not (common.DATA / "mt/m.json").exists()
    assert _rows()[0]["why"] == "輸出不是合法 JSON"


def test_merge_normalizes_with_to_tw(repo):
    batchq.write_batches("lang", [("m", "a", "Video")], 10)
    common.save_json(common.QUEUE / "lang/out/batch_001.json", {"m": {"a": "视频"}})
    s06_merge_mt.main(["--model", "haiku"])
    assert common.load_json(common.DATA / "mt/m.json") == {"a": "影片"}


def test_make_batches_skips_done(repo):
    import s06_make_batches
    common.save_json(common.WORK / "todo/m.json", {"a": "A", "b": "B"})
    common.save_json(common.DATA / "mt/m.json", {"a": "甲"})
    s06_make_batches.main()
    assert common.load_json(common.QUEUE / "lang/batch_001.json") == {"m": {"b": "B"}}

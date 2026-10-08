import json

import pytest

import batchq
import common


def test_write_grouped_and_split(repo):
    items = [("a", f"k{i}", f"v{i}") for i in range(3)] + [("b", "x", "y")]
    assert batchq.write_batches("lang", items, 2) == 2
    b1 = common.load_json(common.QUEUE / "lang/batch_001.json")
    b2 = common.load_json(common.QUEUE / "lang/batch_002.json")
    assert b1 == {"a": {"k0": "v0", "k1": "v1"}}
    assert b2 == {"a": {"k2": "v2"}, "b": {"x": "y"}}


def test_write_flat(repo):
    batchq.write_batches("quest", [(None, "q.1.title", "Hi")], 10)
    assert common.load_json(common.QUEUE / "quest/batch_001.json") == {"q.1.title": "Hi"}


def test_rewrite_removes_old_batches(repo):
    batchq.write_batches("lang", [("a", str(i), "v") for i in range(5)], 1)
    batchq.write_batches("lang", [("a", "0", "v")], 1)
    assert sorted(p.name for p in (common.QUEUE / "lang").glob("batch_*.json")) == ["batch_001.json"]


def test_refuse_when_unmerged_output(repo):
    batchq.write_batches("lang", [("a", "k", "v")], 10)
    common.save_json(common.QUEUE / "lang/out/batch_001.json", {"a": {"k": "值"}})
    with pytest.raises(RuntimeError):
        batchq.write_batches("lang", [("a", "k", "v")], 10)


def test_pending_finished_clear(repo):
    batchq.write_batches("lang", [("a", "k1", "v"), ("a", "k2", "v")], 1)
    common.save_json(common.QUEUE / "lang/out/batch_001.json", {"a": {"k1": "值"}})
    (common.QUEUE / "lang/out/batch_002.json").write_text("{broken")
    assert batchq.pending("lang") == []
    fin = batchq.finished("lang")
    assert [f["id"] for f in fin] == ["batch_001", "batch_002"]
    assert fin[0]["out"] == {"a": {"k1": "值"}} and fin[1]["out"] is None
    batchq.clear("lang", "batch_001")
    assert not (common.QUEUE / "lang/batch_001.json").exists()
    assert not (common.QUEUE / "lang/out/batch_001.json").exists()


def test_cli_args(repo, monkeypatch, capsys):
    monkeypatch.setattr(common, "REPO", repo)
    batchq.write_batches("lang", [("a", "k1", "v"), ("a", "k2", "v")], 1)
    batchq.main(["args", "lang", "haiku", "--limit", "1"])
    out = json.loads(capsys.readouterr().out)
    assert out["kind"] == "lang" and out["model"] == "haiku"
    assert out["rules"] == "rules/mt_rules.md"
    assert out["batches"] == [{"id": "batch_001", "in": "queue/lang/batch_001.json",
                               "out": "queue/lang/out/batch_001.json"}]

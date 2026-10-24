import json

import pytest

import common
import s13_audit as a


@pytest.fixture
def q(repo):
    # 只 monkeypatch common.QUEUE（repo 慣例）；佇列路徑每次從 common 取
    assert a.q() == common.QUEUE / "audit"
    return a.q()


def test_final_fix():
    flag = {"sev": "error", "fix": "甲"}
    assert a.final_fix(flag, {"verdict": "approve"}) == "甲"
    assert a.final_fix(flag, {"verdict": "amend", "fix": "乙"}) == "乙"
    assert a.final_fix(flag, {"verdict": "reject"}) is None
    assert a.final_fix(flag, None) is None


def test_collect_jar_filters(q, monkeypatch):
    monkeypatch.setattr(a, "SAMPLE_N", 2)
    en = {f"item.m.{i}": f"Thing {i}" for i in range(5)} | {f"gui.m.{i}": f"Text {i}" for i in range(5)}
    en |= {"gui.m.ph": "Count %s", "gui.m.fake": "Same", "gui.m.cn": "Fluid"}
    common.save_json(common.WORK / "extract/en/m.json", en)
    tw = {k: f"譯{k}" for k in en} | {"gui.m.ph": "數量 %s", "gui.m.fake": "Same", "gui.m.cn": "流体"}
    common.save_json(common.WORK / "extract/tw_jar/m.json", tw)
    # 轉換層的佔位符壞掉 → s08 不出貨 → 遊戲顯示 jar 值，仍要送審；被 mt 蓋掉的不送
    common.save_json(common.WORK / "zhtw_lang/m.json", {"gui.m.ph": "數量"})
    common.save_json(common.DATA / "mt/m.json", {"gui.m.0": "機翻"})
    keys = [it[1] for it in a.collect("jar_sample")]
    assert sum(k.startswith("item.") for k in keys) == 2 and sum(k.startswith("gui.") for k in keys) == 2
    full = {it[1] for it in a.collect("jar:m")}
    # 假翻譯（＝英文）、被 mt 蓋掉的不送；夾簡體的 jar 值 atm11 沒有別層會修 → 要送
    assert {"gui.m.ph", "gui.m.cn"} <= full and not {"gui.m.fake", "gui.m.0"} & full and len(full) == 11
    with pytest.raises(SystemExit):
        a.collect("jar:typo")


def test_collect_conv(q):
    common.save_json(common.WORK / "extract/en/m.json", {"a": "x" * 30, "b": "y" * 30, "c": "z" * 60, "d": "w" * 30, "e": "Count %s and more text"})
    common.save_json(common.WORK / "zhtw_lang/m.json", {"a": "甲", "b": "乙", "c": "丙", "d": "w" * 30, "e": "數量"})
    common.save_json(common.DATA / "mt/m.json", {"b": "機翻"})
    # b 被 mt 蓋掉、c 超出長度、d 等於英文、e 佔位符不符（s08 不出貨）→ 只剩 a
    assert [it[1] for it in a.collect("conv:20-50")] == ["a"]


def test_grouped_verify_args_and_merge(q, capsys):
    common.save_json(common.WORK / "extract/en/m.json", {"k": "Iron Pipe", "j": "Gold Pipe", "s": "Save"})
    common.save_json(common.WORK / "extract/tw_jar/m.json", {"k": "鐵管線", "j": "金管", "s": "保存"})
    common.save_json(q / "batch_001.json", {
        "a1": {"ns": "m", "key": "k", "en": "Iron Pipe", "zh": "鐵管線"},
        "a2": {"ns": "m", "key": "j", "en": "Gold Pipe", "zh": "金管"},
        "a3": {"ns": "m", "key": "s", "en": "Save", "zh": "保存"}})
    common.save_json(q / "out/batch_001.json", {
        "a1": {"sev": "minor", "fix": "鐵管道", "why": "x"}, "a2": {"sev": "error", "fix": "金管道", "why": "y"},
        # fix 夾簡體 → tw_fix 只轉簡體所在的詞（設置→設定）
        "a3": {"sev": "error", "fix": "保存设置", "why": "z"}, "a9": {"sev": "error", "fix": "不存在"}})
    a.args()
    groups = {g["id"]: g for g in json.loads(capsys.readouterr().out)["batches"]}
    assert {g["model"] for g in groups.values()} == {"opus", "sonnet"}
    err = next(g for gid, g in groups.items() if gid.startswith("v_error_batch_001_a2_"))
    assert common.load_json(q / "vin" / f"{err['id']}.json")["batch_001/a2"]["fix"] == "金管道"
    common.save_json(q / "verify" / f"{err['id']}.json",
                     {"batch_001/a2": {"verdict": "approve"}, "batch_001/a3": {"verdict": "approve"}})
    # minor 組還沒判 → 批次不能合併
    a.merge()
    assert (q / "batch_001.json").exists()
    capsys.readouterr()
    a.args()
    left = json.loads(capsys.readouterr().out)["batches"]
    assert [g["id"][:20] for g in left] == ["v_minor_batch_001_a1"]
    common.save_json(q / "verify" / f"{left[0]['id']}.json", {"batch_001/a1": {"verdict": "reject"}})
    a.merge()
    assert common.load_json(common.DATA / "mt/m.json") == {"j": "金管道", "s": "保存設定"}
    rows = {r["key"]: r for r in map(json.loads, (common.DATA / "audit_log.jsonl").read_text().splitlines())}
    log = {k: r["result"] for k, r in rows.items()}
    assert log["s"] == "套用" and rows["s"]["final_fix"] == "保存设置" and log["k"] == "驗證否決" and log["j"] == "套用"
    assert rows["j"]["layer"] == "jar_tw"
    assert not (q / "batch_001.json").exists()
    assert not list((q / "verify").glob("*.json")) and not list((q / "vin").glob("*.json"))


def test_merge_keeps_taiwan_wording_and_skips_stale(q):
    common.save_json(common.WORK / "extract/en/m.json", {"k": "Click", "j": "Gold"})
    common.save_json(common.WORK / "extract/tw_jar/m.json", {"k": "單擊", "j": "金"})
    common.save_json(q / "batch_001.json", {
        "a1": {"ns": "m", "key": "k", "en": "Click", "zh": "單擊"},
        "a2": {"ns": "m", "key": "j", "en": "Gold", "zh": "舊值"}})
    # 點擊 → s2twp 會改成 點選；機翻層改走 tw_fix 後原樣寫入、s08 也不再改
    common.save_json(q / "out/batch_001.json", {"a1": {"sev": "error", "fix": "點擊"}, "a2": {"sev": "error", "fix": "黃金"}})
    common.save_json(q / "verify/v_error_x.json", {"batch_001/a1": {"verdict": "approve"}, "batch_001/a2": {"verdict": "approve"}})
    a.merge()
    assert common.load_json(common.DATA / "mt/m.json") == {"k": "點擊"} and a.shown("m")["k"] == "點擊"
    log = {r["key"]: r["result"] for r in map(json.loads, (common.DATA / "audit_log.jsonl").read_text().splitlines())}
    assert log["k"] == "套用" and log["j"] == "送審後已改動（略過）"
    # 沒寫入的列 after 必須是 None（after＝實際寫入值）
    rows = {r["key"]: r for r in map(json.loads, (common.DATA / "audit_log.jsonl").read_text().splitlines())}
    assert rows["j"]["after"] is None


def test_merge_survives_bad_out_and_logs_missing_fix(q, capsys):
    common.save_json(common.WORK / "extract/en/m.json", {"k": "Iron", "j": "Gold"})
    common.save_json(common.WORK / "extract/tw_jar/m.json", {"k": "鐵", "j": "金"})
    common.save_json(q / "batch_001.json", {"a1": {"ns": "m", "key": "k", "en": "Iron", "zh": "鐵"}})
    (q / "out").mkdir(parents=True, exist_ok=True)
    (q / "out/batch_001.json").write_text('"OK"')  # agent 寫壞的標記檔
    common.save_json(q / "batch_002.json", {"a1": {"ns": "m", "key": "j", "en": "Gold", "zh": "金"}})
    common.save_json(q / "out/batch_002.json", {"a1": {"sev": "error", "why": "沒給 fix"}})
    common.save_json(q / "verify/v_error_x.json", {"batch_002/a1": {"verdict": "approve"}})
    a.merge()
    stats = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert stats["batches"] == 1 and stats["rejected"] == 0
    row = json.loads((common.DATA / "audit_log.jsonl").read_text().splitlines()[0])
    assert row["result"] == "驗證通過但沒有修法（略過）"
    # 壞掉的 out 留給 args 重排，不刪批次
    assert (q / "batch_001.json").exists()


def test_conv_queue_layer(repo, monkeypatch, capsys):
    monkeypatch.setattr(a, "QNAME", "audit_conv")
    common.save_json(common.WORK / "extract/en/m.json", {"a": "x" * 30})
    common.save_json(common.WORK / "zhtw_lang/m.json", {"a": "甲"})
    a.prep("conv:20-50")
    q = a.q()
    assert q == common.QUEUE / "audit_conv" and (q / "batch_001.json").exists()
    common.save_json(q / "out/batch_001.json", {"a1": {"sev": "error", "fix": "乙"}})
    common.save_json(q / "verify/v_error_x.json", {"batch_001/a1": {"verdict": "approve"}})
    a.merge()
    row = json.loads((common.DATA / "audit_log.jsonl").read_text().splitlines()[0])
    assert row["result"] == "套用" and row["layer"] == "conv"


def test_prep_refuses_unmerged(q, monkeypatch):
    monkeypatch.setattr(a, "collect", lambda *_: [])
    common.save_json(q / "out/batch_001.json", {})
    with pytest.raises(SystemExit):
        a.prep("jar_sample")
    a.prep("jar_sample", force=True)
    assert not (q / "out/batch_001.json").exists()


def test_collect_mt_and_layer(repo, monkeypatch):
    monkeypatch.setattr(a, "QNAME", "audit_mt")
    common.save_json(common.WORK / "extract/en/m.json", {"a": "x" * 30, "b": "y" * 30, "c": "z" * 90, "d": "w" * 30, "e": "v" * 30})
    common.save_json(common.DATA / "mt/m.json", {"a": "甲", "b": "乙", "c": "丙", "d": "丁", "e": "戊"})
    common.save_json(common.DATA / "prov/m.json", {"a": "haiku", "b": "audit", "c": "haiku", "e": "sonnet"})
    # b 已審過、c 超出長度、d 沒有 prov（不是機翻）→ 剩 a 與 sonnet 重翻的 e
    assert [(it[1], it[3]) for it in a.collect("mt:20-80")] == [("a", "甲"), ("e", "戊")]
    a.prep("mt:20-80")
    q = a.q()
    common.save_json(q / "out/batch_001.json", {"a1": {"sev": "error", "fix": "乙乙"}})
    common.save_json(q / "verify/v_error_x.json", {"batch_001/a1": {"verdict": "approve"}})
    a.merge()
    row = json.loads((common.DATA / "audit_log.jsonl").read_text().splitlines()[0])
    assert row["result"] == "套用" and row["layer"] == "mt"
    assert common.load_json(common.DATA / "prov/m.json")["a"] == "audit"

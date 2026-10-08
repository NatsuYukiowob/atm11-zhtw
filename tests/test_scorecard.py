import json

import common
import s11_scorecard


def _write(name, rows):
    (common.DATA / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def test_compute(repo):
    _write("merge_log", [
        {"kind": "lang", "model": "haiku", "ns": "m", "key": "a", "len": 5, "ok": True, "why": None},
        {"kind": "lang", "model": "haiku", "ns": "m", "key": "b", "len": 50, "ok": False, "why": "佔位符 ('%s',) → ()"},
        {"kind": "lang", "model": "sonnet", "ns": "m", "key": "b", "len": 50, "ok": True, "why": None},
        {"kind": "lang", "model": "haiku", "ns": "m", "key": "c", "len": 100, "ok": False, "why": "缺漏"},
        {"kind": "lang", "model": "sonnet", "ns": "m", "key": "c", "len": 100, "ok": False, "why": "缺漏"},
    ])
    _write("review_log", [
        {"kind": "review", "ns": "m", "key": "a", "prev_model": "haiku", "changed": True, "why": None},
        {"kind": "review", "ns": "m", "key": "b", "prev_model": "sonnet", "changed": False, "why": None},
        {"kind": "term", "ns": "m", "key": "a", "prev_model": "haiku", "changed": True, "why": None},
    ])
    s = s11_scorecard.compute()
    assert s["by_kind"]["lang"] == {"haiku_n": 3, "haiku_ok": 1, "sonnet_n": 2, "sonnet_ok": 1, "never_ok": 1}
    assert s["by_len"]["short"] == {"n": 1, "ok": 1} and s["by_len"]["long"] == {"n": 1, "ok": 0}
    assert s["review"]["reviewed"] == 2 and s["review"]["changed"] == 1 and s["review"]["terms_changed"] == 1
    assert s["review"]["by_prev"]["haiku"] == {"reviewed": 1, "changed": 1}
    assert s["reasons"][0] == ("佔位符", 1) or s["reasons"][0] == ("缺漏", 1)
    s11_scorecard.main()
    assert "haiku" in (common.REPORTS / "haiku-scorecard.md").read_text()
    assert "## 註記" in (common.REPORTS / "haiku-scorecard.md").read_text()


def test_reason_normalized():
    r = s11_scorecard._reason
    assert r("第 3 行：佔位符 ('%s',) → ()") == "佔位符"
    assert r(".pages[0].text: $() 標記數不符") == "$() 標記數不符"
    assert r("疑似簡體/未收斂: '视频' → '影片'") == "疑似簡體/未收斂"
    assert r("行數不符 2 → 1") == "行數不符"
    assert r("缺漏") == "缺漏"

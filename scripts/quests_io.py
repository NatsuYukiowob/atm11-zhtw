"""FTB Quests 任務書 lang 讀寫：config/ftbquests/quests/lang/<locale>/**/*.json5。

每檔是平面 {key: 字串 | 字串 list} 的 json5；ATM11 實測唯一的 JSON 不相容處是尾逗號
（docs/discovery.md）。其他結構直接 ValueError，寧可炸掉也不要靜默吃錯。
"""
import json
import re
from pathlib import Path

# 字串整段吃掉保留原樣，只刪字串外的尾逗號
_TRAILING = re.compile(r'"(?:[^"\\]|\\.)*"|,(\s*[}\]])')


def loads(text):
    d = json.loads(_TRAILING.sub(lambda m: m.group(1) if m.group(1) is not None else m.group(0), text))
    if not isinstance(d, dict):
        raise ValueError("頂層不是物件")
    for k, v in d.items():
        if not (isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v))):
            raise ValueError(f"{k}: 不支援的值型別 {type(v).__name__}")
    return d


def load_dir(d):
    """{相對路徑: {key: value}}；目錄不存在回傳 {}。"""
    d = Path(d)
    if not d.is_dir():
        return {}
    return {p.relative_to(d).as_posix(): loads(p.read_text(encoding="utf-8-sig")) for p in sorted(d.rglob("*.json5"))}


def load_flat(d):
    out = {}
    for content in load_dir(d).values():
        out.update(content)
    return out


def dump_dir(d, files):
    for rel, content in files.items():
        p = Path(d) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

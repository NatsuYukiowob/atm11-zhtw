"""譯文硬驗證：所有合併步驟的唯一入口。回傳 None＝通過，否則回中文原因。

呼叫端合併前：轉換層過 to_tw()、機翻層過 tw_fix()（夾簡體才轉）；這裡只擋殘留簡體字（has_simplified）。

human=True 用於人工簡中來源轉繁（CFPA／instance zh_cn）：譯者常把英文單行內的 \\n\\n
拆成多個 list 元素、省略結尾的 &r——顯示效果相同，不該把人工譯文丟去機翻。
寬鬆的只有換行／行數與重設碼（&r、§r）；佔位符、其他色碼、{} 標記、JSON 元件照樣守恆。
"""
import re
import unicodedata
from collections import Counter

from common import has_simplified, placeholders

SECTION_RE = re.compile(r"§[0-9a-fk-orA-FK-OR]")
# & 色碼只在 FTB Quests 有意義；lang 裡的 R&D、Salt & Pepper 不是格式碼
AMP_RE = re.compile(r"&[0-9a-fk-orA-FK-OR]")
BRACE_RE = re.compile(r"\{[^{}]*\}")
# 三字以上英文句原樣照抄＝沒翻（mod 名、學名這類一兩個字的專有名詞保留英文是合法的）
SENTENCE_RE = re.compile(r"[A-Za-z]{2,}(?:[\s-]+[A-Za-z]{2,}){2,}")


def _symbols(s):
    """非 ASCII 的符號字元（✔ ★ → × ±…）multiset；haiku 會刪掉或換成 ASCII。"""
    return Counter(c for c in s if ord(c) > 127 and unicodedata.category(c) in ("So", "Sm"))


def _codes(rx, s, human):
    codes = rx.findall(s)
    if human:
        codes = [c for c in codes if c[1] not in "rR"]
    return sorted(codes)


def is_raw_json_line(s):
    s = s.strip()
    return s.startswith("{") and s.endswith("}") and '"' in s


def check_text(en, zh, *, amp_codes=False, human=False):
    if not isinstance(zh, str):
        return "非字串"
    if en.strip() and not zh.strip():
        return "空值"
    # {image:… width:200 height:50} 這類標記行原樣保留是對的，不算「沒翻」
    if zh == en and SENTENCE_RE.search(BRACE_RE.sub("", en)):
        return "未翻譯（與英文相同）"
    if placeholders(zh) != placeholders(en):
        return f"佔位符 {placeholders(en)} → {placeholders(zh)}"
    if _codes(SECTION_RE, zh, human) != _codes(SECTION_RE, en, human):
        return "§ 格式碼不守恆"
    # & 色碼（任務書）只能少不能多：中文重組會合併色段，少了只差顏色（yuki 2026-10-08 拍板放寬）；全丟光仍算沒照規則
    if amp_codes:
        ez, zz = _codes(AMP_RE, en, human), _codes(AMP_RE, zh, human)
        if Counter(zz) - Counter(ez) or (ez and not zz):
            return "& 格式碼不守恆"
    if sorted(BRACE_RE.findall(zh)) != sorted(BRACE_RE.findall(en)):
        return "{} 標記被改動"
    if not human and zh.count("\n") != en.count("\n"):
        return "換行數不符"
    # 只擋刪掉／換成 ASCII；譯文多加符號（2000C → 2000°C）沒問題
    lost = _symbols(en) - _symbols(zh)
    if lost:
        return f"符號被改動 {sorted(lost.elements())} → 缺"
    if has_simplified(zh):
        return f"含簡體字: {zh[:30]!r}"
    return None


def check_value(en, zh, *, amp_codes=False, human=False):
    """任務書值可能是字串或多行 list；list 逐行驗，空行與整行 JSON 元件必須原樣。

    human=True：不比行數，整行 JSON 元件須原樣出現，其餘行合併後以寬鬆模式比對。
    """
    if human and isinstance(en, list) and isinstance(zh, list) and all(isinstance(z, str) for z in zh):
        if any(is_raw_json_line(e) and e not in zh for e in en):
            return "JSON 元件被改動"
        join = lambda xs: "\n".join(x for x in xs if not is_raw_json_line(x))  # noqa: E731
        return check_text(join(en), join(zh), amp_codes=amp_codes, human=True)
    if isinstance(en, str):
        return check_text(en, zh, amp_codes=amp_codes, human=human) if isinstance(zh, str) else "型別不符"
    if not isinstance(zh, list) or len(zh) != len(en):
        return f"行數不符 {len(en)} → {len(zh) if isinstance(zh, list) else type(zh).__name__}"
    for i, (e, z) in enumerate(zip(en, zh)):
        if not isinstance(z, str):
            return f"第 {i} 行非字串"
        if not e.strip():
            if z.strip():
                return f"第 {i} 行應為空行"
            continue
        if is_raw_json_line(e):
            if z != e:
                return f"第 {i} 行 JSON 元件被改動"
            continue
        why = check_text(e, z, amp_codes=amp_codes)
        if why:
            return f"第 {i} 行：{why}"
    return None

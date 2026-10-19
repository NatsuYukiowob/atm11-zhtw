"""共用路徑與工具。"""
import json
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INSTANCE_DIR = Path(os.environ.get("ATM11_INSTANCE", REPO / "instance"))  # modpack 客戶端 instance（mods／config／kubejs）
MODS_DIR = INSTANCE_DIR / "mods"
KUBEJS_DIR = INSTANCE_DIR / "kubejs"
QUESTS_LANG_DIR = INSTANCE_DIR / "config/ftbquests/quests/lang"
WORK = REPO / "work"
CFPA = REPO / "cfpa"
DATA = REPO / "data"
DIST = REPO / "dist"
QUEUE = REPO / "queue"
REPORTS = REPO / "reports"

MC_VERSION = "1.21.1"
PACK_FORMAT = 34  # resource pack format for MC 1.21–1.21.1
OPENCC_PROFILE = "s2twp"

# Java format specifier 的一般形（任意轉換字母），別手列 [sdfx] —— 現役資料就有 %b
PLACEHOLDER_RE = re.compile(r"%(?:\d+\$)?[a-zA-Z]|%%")


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:  # mod／CFPA／KubeJS 檔常帶 BOM
        return json.load(f)


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def placeholders(s):
    """回傳字串中的格式化佔位符 multiset（排序 tuple），供翻譯前後比對。"""
    return tuple(sorted(PLACEHOLDER_RE.findall(str(s))))


_opencc = None
_glossary_rules = None


def get_opencc():
    global _opencc
    if _opencc is None:
        from opencc import OpenCC
        _opencc = OpenCC(OPENCC_PROFILE)
    return _opencc


def glossary_rules():
    """work/glossary.json 的 (src, dst) 清單，依 src 長度由長到短；同長度時保護詞排後（先改寫成它再保護）。"""
    global _glossary_rules
    if _glossary_rules is None:
        g = load_json(WORK / "glossary.json")
        _glossary_rules = sorted(g.items(), key=lambda kv: (-len(kv[0]), kv[0] == kv[1]))
    return _glossary_rules


def apply_glossary(s):
    """依術語表逐條取代（長規則優先；順序取代允許鏈式收斂，語意勿改）。

    src == dst 的規則是保護詞（只來自 glossary_manual）：先遮起來，較短規則碰不到，最後還原。
    """
    masks = []
    for src, dst in glossary_rules():
        if src in s:
            if src == dst:
                s = s.replace(src, f"\x00{len(masks)}\x01")
                masks.append(src)
            else:
                s = s.replace(src, dst)
    for i, w in enumerate(masks):
        s = s.replace(f"\x00{i}\x01", w)
    return s


def to_tw(s):
    """簡中 → 台灣繁中：OpenCC s2twp ＋ 術語表，重複到定點（術語表單次取代可能鏈式未收斂）。

    OpenCC 本身也有振盪詞（註冊表→登錄檔→登入檔），所以最多 5 輪；仍不收斂的字串
    會被 validate 的冪等檢查擋下，靠 data/glossary_manual.json 加定點規則解。
    """
    for _ in range(5):
        t = apply_glossary(get_opencc().convert(s))
        if t == s:
            break
        s = t
    return tw_quotes(s)


_SINGLE_Q = re.compile(r"(?<![A-Za-z])‘([^‘’]*)’")


def tw_quotes(s):
    """台灣引號：“”→「」；‘’ 成對且前面不是英文字母時→『』（避開英文撇號 Odus’）。巢狀引號不處理。"""
    return _SINGLE_Q.sub(r"『\1』", s.replace("“", "「").replace("”", "」"))


def jar_json(zf, name):
    """從 jar 讀 JSON；容忍 BOM 與尾逗號等常見髒格式，失敗回傳 None。"""
    try:
        raw = zf.read(name).decode("utf-8-sig", "ignore")
        return json.loads(raw)
    except Exception:
        try:
            # 少數 mod 的 lang 檔帶尾逗號
            cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
            return json.loads(cleaned)
        except Exception:
            return None

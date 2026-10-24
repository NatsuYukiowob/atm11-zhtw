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


def _glossary_fixpoint(s, pre=lambda x: x):
    """pre（OpenCC 或不轉）＋術語表重複到定點，最多 5 輪（OpenCC 本身也有振盪詞：註冊表→登錄檔→登入檔）。"""
    for _ in range(5):
        t = apply_glossary(pre(s))
        if t == s:
            break
        s = t
    return tw_quotes(s)


def to_tw(s):
    """簡中 → 台灣繁中：OpenCC s2twp ＋ 術語表，重複到定點（術語表單次取代可能鏈式未收斂）。

    仍不收斂的字串由轉換層呼叫端以 to_tw(v) == v 擋下（s07q），靠 data/glossary_manual.json 加定點規則解。
    """
    return _glossary_fixpoint(s, get_opencc().convert)


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


def tw_fix(s):
    """LLM 寫的繁體譯文（機翻層、審查修法）：夾簡體字才轉那幾段；否則只套術語表（到定點）＋轉引號，不跑 OpenCC。

    OpenCC s2twp 套在已是繁體的文字上會改壞（點擊→點選、背包→揹包、演算法→演演算法）；
    術語表則要套——LLM 常寫大陸版 MC 譯名（圓石、豬靈）。移植自 sf5-zhtw。
    """
    if has_simplified(s):
        s = _fix_simp_spans(s)
    return _glossary_fixpoint(_t2tw(s))  # t2tw：繁體異體字轉台灣正字（爲→為、着→著），只有字形表、不做詞彙轉換


_t2tw_cc = None


def _t2tw(s):
    global _t2tw_cc
    if _t2tw_cc is None:
        from opencc import OpenCC
        _t2tw_cc = OpenCC("t2tw")
    return _t2tw_cc.convert(s)


def _fix_simp_spans(s):
    """只轉簡體字所在片段，其餘 LLM 寫的繁體原樣保留。

    1. 標記簡體字、大陸用法詞（MAINLAND_RE），以及緊鄰它們的一對多字（游戏 的 游、一只铁 的 只）。
    2. 整句過 s2tw（逐字＋詞組消歧，等長），只採用標記位置。
    3. 台灣詞組（OpenCC TWPhrases，s2twp 的那一層）最長匹配，只換涵蓋標記位置的詞（内存→記憶體、视频→影片）；
       緊鄰的台灣用語不動（查看内存 → 查看記憶體，不是 檢視記憶體）。
    ponytail: 單獨出現、鄰字都不是簡體的一對多字（背包里的东西 的 里）不轉，has_simplified 也看不到。
    """
    simp, multi = _st_sets()
    mark = {i for i, c in enumerate(s) if c in simp}
    mark |= {i for m in MAINLAND_RE.finditer(s) for i in range(m.start(), m.end())}
    mark |= {i for i, c in enumerate(s) if c in multi and (i - 1 in mark or i + 1 in mark)}
    u = _s2tw(s)
    if len(u) != len(s):  # s2tw 理論上等長；不等長時退回逐字轉
        u = "".join(_s2tw(c) for c in s)
    u = "".join(b if i in mark else a for i, (a, b) in enumerate(zip(s, u)))
    phrases, longest = _tw_phrases()
    out, i = [], 0
    while i < len(u):
        for n in range(min(longest, len(u) - i), 0, -1):
            w = u[i:i + n]
            if w in phrases:
                out.append(phrases[w] if mark.intersection(range(i, i + n)) else w)
                i += n
                break
        else:
            out.append(u[i])
            i += 1
    return "".join(out)


_twp = None


def _tw_phrases():
    global _twp
    if _twp is None:
        import opencc
        f = Path(opencc.__file__).parent / "dictionary/TWPhrases.txt"
        d = {}
        for line in f.read_text(encoding="utf-8").splitlines():
            a, b = line.split("\t")
            d[a] = b.split()[0]
        _twp = (d, max(map(len, d)))
    return _twp


_s2tw_cc = None


def _s2tw(s):
    global _s2tw_cc
    if _s2tw_cc is None:
        from opencc import OpenCC
        _s2tw_cc = OpenCC("s2tw")
    return _s2tw_cc.convert(s)


# 一對多字（后／里／干／尸…在 STCharacters 對應到自身，逐字無法判定）寫成大陸用法的詞；
# 后面／后来 前面是 皇王蜂天太影母 時是「皇后面前」這類正常繁體
MAINLAND_RE = re.compile(r"之后|然后|以后|最后|随后|(?<![皇王帝蜂天太影母])后[面来來]|背后|干[净淨]|尸")
# STCharacters 一對多、但台灣幾乎不用的簡體字（种→種 种）。台灣正常用字（岩台游里干栗伙后采征…）不列入：
# 2026-10-20 對 vanilla zh_tw 與出貨包校準，這些字在兩者都 0 次
AMBIGUOUS_SIMP = set("万价种确极广厂愿筑胜适虫叶范据蜡蝎腊腌苹荐柜涂淀熏帘挂杠佣党咨亘膻蚝跖涌杰")
_st = None


def _st_sets():
    """(簡體字集, 一對多字集)，取自 OpenCC STCharacters。

    簡體字＝沒有對應到自身、且 s2tw 會改變的字（秘、霉 台灣通用，排除）＋ AMBIGUOUS_SIMP；
    一對多字＝對應清單含自身且不只一個（只→隻 只、游→遊 游），單看一個字無法判定。
    """
    global _st
    if _st is None:
        import opencc
        f = Path(opencc.__file__).parent / "dictionary/STCharacters.txt"
        simp, multi = set(), set()
        for line in f.read_text(encoding="utf-8").splitlines():
            a, b = line.split("\t")
            bs = b.split()
            if a not in bs:
                simp.add(a)
            elif len(bs) > 1:
                multi.add(a)
        # OpenCC 的繁體用舊字形（床→牀、峰→峯、群→羣）：s2tw 單字轉換不變的字是台灣正字
        simp = {c for c in simp if _s2tw(c) != c} - set("秘霉")
        _st = (simp | AMBIGUOUS_SIMP, multi)
    return _st


def _has_simp_chars(s):
    simp = _st_sets()[0]
    return any(c in simp for c in s)


def has_simplified(s):
    """含簡體字或大陸用法的一對多字詞。

    不用 to_tw(v) != v 判斷：s2twp 會把台灣正確用語也改掉（點擊→點選、查看→檢視）。
    """
    return _has_simp_chars(s) or bool(MAINLAND_RE.search(s))

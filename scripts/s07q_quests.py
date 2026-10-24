"""FTB Quests 任務書：讀 lang/en_us/**/*.json5 → 決定每個 key 的來源 → 產出待翻批次。

目標 key＝instance lang/zh_tw/ 缺、或值等於英文（假翻譯）、且 data/quests_mt.json 還沒有的。
來源：instance lang/zh_cn/（值≠英文）→ to_tw 轉換並過 check_value；不過或沒有 → 機翻。
輸出：
  work/quests_tw.json        簡中轉繁結果
  queue/quest/batch_NNN.json 待機翻 {key: en_value}（每批 60）
"""
import batchq
import common as C
import quests_io
from validate import check_value

BATCH = 60


def _unescape(s):
    # 人工簡中任務書有雙重跳脫的換行（值裡是兩個反斜線＋n，遊戲內顯示成字面），英文原文沒有 → 還原成換行
    return s.replace("\\\\n", "\n")


def _map_value(f, v):
    return [f(_unescape(x)) for x in v] if isinstance(v, list) else f(_unescape(v))


def to_tw_value(v):
    """轉換層（人工簡中）：to_tw。"""
    return _map_value(C.to_tw, v)


def tw_fix_value(v):
    """機翻任務書值（LLM 寫的繁體）：tw_fix，不跑 OpenCC。"""
    return _map_value(C.tw_fix, v)


def main():
    en = quests_io.load_flat(C.QUESTS_LANG_DIR / "en_us")
    tw = quests_io.load_flat(C.QUESTS_LANG_DIR / "zh_tw")
    cn = quests_io.load_flat(C.QUESTS_LANG_DIR / "zh_cn")
    mt_p = C.DATA / "quests_mt.json"
    done = C.load_json(mt_p) if mt_p.exists() else {}
    conv, todo = {}, []
    for k, ev in en.items():
        if k in tw and tw[k] != ev:
            continue
        if k in done:
            continue
        cv = cn.get(k)
        if cv is not None and cv != ev:
            t = to_tw_value(cv)
            # to_tw 不收斂（術語表／OpenCC 振盪）的不收，改走機翻
            if to_tw_value(t) == t and check_value(ev, t, amp_codes=True, human=True) is None:
                conv[k] = t
                continue
        todo.append((None, k, ev))
    C.save_json(C.WORK / "quests_tw.json", conv)
    n = batchq.write_batches("quest", todo, BATCH)
    print(f"任務書 key {len(en)}：instance 繁中 {sum(1 for k in en if k in tw and tw[k] != en[k])}，"
          f"簡中轉換 {len(conv)}，已機翻 {len(done)}，待機翻 {len(todo)} → {n} 批")


if __name__ == "__main__":
    main()

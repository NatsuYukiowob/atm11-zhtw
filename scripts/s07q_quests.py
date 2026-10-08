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


def to_tw_value(v):
    return [C.to_tw(x) for x in v] if isinstance(v, list) else C.to_tw(v)


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
            if check_value(ev, t, amp_codes=True, human=True) is None:
                conv[k] = t
                continue
        todo.append((None, k, ev))
    C.save_json(C.WORK / "quests_tw.json", conv)
    n = batchq.write_batches("quest", todo, BATCH)
    print(f"任務書 key {len(en)}：instance 繁中 {sum(1 for k in en if k in tw and tw[k] != en[k])}，"
          f"簡中轉換 {len(conv)}，已機翻 {len(done)}，待機翻 {len(todo)} → {n} 批")


if __name__ == "__main__":
    main()

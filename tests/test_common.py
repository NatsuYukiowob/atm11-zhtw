import common


def test_constants():
    assert common.MC_VERSION == "1.21.1"
    assert common.PACK_FORMAT == 34


def test_placeholders_multiset():
    assert common.placeholders("%s and %1$s %%") == ("%%", "%1$s", "%s")


def test_to_tw_converts_simplified():
    assert common.to_tw("视频") == "影片"


def test_to_tw_reaches_fixed_point(monkeypatch):
    # 長規則優先、單次順序取代：ADE →(DE→BC) ABC，要再一輪才會 →(ABC→X) X
    monkeypatch.setattr(common, "_glossary_rules", [("ABC", "X"), ("DE", "BC")])
    once = common.to_tw("ADE")
    assert once == "X" and common.to_tw(once) == once


def test_load_json_tolerates_bom(tmp_path):
    p = tmp_path / "x.json"
    p.write_bytes("﻿".encode() + b'{"a": "b"}')
    assert common.load_json(p) == {"a": "b"}


def test_manual_glossary_keeps_algorithm_fixed_point(monkeypatch):
    # s2twp 把已是繁體的「演算法」再轉成「演演算法」→ 靠 glossary_manual 的定點規則收斂
    g = common.load_json(common.REPO / "data/glossary_manual.json")
    rules = sorted(((k, v) for k, v in g.items() if isinstance(v, str) and not k.startswith("_")), key=lambda kv: -len(kv[0]))
    monkeypatch.setattr(common, "_glossary_rules", rules)
    assert common.to_tw("演算法") == "演算法"
    assert common.to_tw("计算算法") == "計算演算法"


def test_apply_glossary_protected_word(monkeypatch):
    # src == dst 的規則是保護詞：較短規則不得改寫它（「同時運作」不能被「時運→幸運」吃掉）
    rules = sorted({"時運作": "時運作", "時運": "幸運", "螢石粉": "螢石粉", "螢石": "螢光石"}.items(),
                   key=lambda kv: -len(kv[0]))
    monkeypatch.setattr(common, "_glossary_rules", rules)
    assert common.apply_glossary("同時運作，時運 III，螢石粉與螢石") == "同時運作，幸運 III，螢石粉與螢光石"


def test_glossary_rules_rewrite_before_protect_at_same_length(tmp_path, monkeypatch):
    # 同長度時先改寫再保護：「狂風使者→旋風使者」之後「旋風使者」受保護，「旋風→狂風」碰不到
    monkeypatch.setattr(common, "WORK", tmp_path)
    monkeypatch.setattr(common, "_glossary_rules", None)
    common.save_json(tmp_path / "glossary.json", {"旋風": "狂風", "旋風使者": "旋風使者", "狂風使者": "旋風使者"})
    assert common.apply_glossary("狂風使者與旋風使者") == "旋風使者與旋風使者"


def test_to_tw_taiwan_quotes():
    assert common.to_tw("硫象徵“概念”或“靈魂”") == "硫象徵「概念」或「靈魂」"
    assert common.to_tw("設為‘NONE’時停用") == "設為『NONE』時停用"
    assert common.to_tw("Odus’ Open Convocation") == "Odus’ Open Convocation"


def test_manual_glossary_regressions(monkeypatch):
    g = common.load_json(common.REPO / "data/glossary_manual.json")
    rules = sorted(((k, v) for k, v in g.items() if isinstance(v, str) and not k.startswith("_")),
                   key=lambda kv: (-len(kv[0]), kv[0] == kv[1]))
    monkeypatch.setattr(common, "_glossary_rules", rules)
    assert common.to_tw("请Select目标") == "請選擇目標"
    assert common.to_tw("Selected Selection Selector") == "Selected Selection Selector"
    assert common.to_tw("该调节器已被禁用") == "該調節器已被停用"
    assert common.to_tw("以幸運作為獎勵") == "以幸運作為獎勵"
    assert common.to_tw("這隻適合高階使用者") == "這只適合高階使用者"


def test_manual_blocks_mined_rules_that_hit_prose(monkeypatch):
    # 從 vanilla 挖出的效果／附魔名規則套到一般句子會誤傷（第二輪審查 2026-10-19）
    mined = {"力量": "強力", "使用預設": "使用此方案", "向上": "上", "紅石控制": "需要紅石",
             "中毒": "劇毒", "緩慢": "緩速", "粒子效果": "粒子密度", "苔石": "青苔鵝卵石",
             "迅捷": "加速", "時運": "幸運"}
    g = common.load_json(common.REPO / "data/glossary_manual.json")
    for k, v in g.items():
        if k.startswith("_"):
            continue
        if v is None:
            mined.pop(k, None)
        else:
            mined[k] = v
    rules = sorted(((k, v) for k, v in mined.items() if (k != v and k not in v) or g.get(k) == v),
                   key=lambda kv: (-len(kv[0]), kv[0] == kv[1]))
    monkeypatch.setattr(common, "_glossary_rules", rules)
    assert common.to_tw("获得力量，使用默认材质，在方向上") == "獲得力量，使用預設材質，在方向上"
    assert common.to_tw("可被红石控制，使目标中毒，缓慢地产出粒子效果") == "可被紅石控制，使目標中毒，緩慢地產出粒子效果"
    assert common.to_tw("苔石砖，迅捷药水，红石信号时运转") == "青苔石磚，迅捷藥水，紅石訊號時運轉"
    assert common.to_tw("擷取畫面畫面場景，任意面，所有组合") == "擷取畫面場景，任意面，所有組合"
    # 機翻層已寫死的值靠反向規則救回
    assert common.to_tw("使用此方案的配方，加速藥水") == "使用預設的配方，迅捷藥水"
    assert common.to_tw("免疫缓慢效果，缓慢抗性，中毒效果") == "免疫緩速效果，緩速抗性，劇毒效果"
    assert common.to_tw("实例目录，森林群系，激光钻") == "實例目錄，森林生態域，雷射鑽"


def test_has_simplified():
    assert common.has_simplified("流体管道") and common.has_simplified("仅在") and common.has_simplified("完成之后")
    assert not common.has_simplified("台灣岩石占卜游標伙伴神秘漏斗床頭櫃山峰社群發霉的麵包")


def test_tw_fix_glossary_without_opencc(monkeypatch):
    # LLM 寫的繁體：只套術語表，不跑 OpenCC（點擊→點選、背包→揹包 是 s2twp 改壞的）
    monkeypatch.setattr(common, "_glossary_rules", [("圓石", "鵝卵石")])
    assert common.tw_fix("右鍵點擊背包裡的圓石") == "右鍵點擊背包裡的鵝卵石"
    assert common.tw_fix("用圆石") == "用鵝卵石"


def test_tw_fix_only_touches_simplified_chars():
    assert common.tw_fix("右鍵點擊查看資訊，流体") == "右鍵點擊查看資訊，流體"
    assert common.tw_fix("完成之后打開介面") == "完成之後打開介面"
    assert common.tw_fix("视频") == "影片"


def test_tw_fix_normalizes_tw_variants():
    # 繁體異體字（OpenCC 舊字形）has_simplified 抓不到，用 t2tw 轉台灣正字；詞彙不動
    assert common.tw_fix("我爲此描述着裏面的點擊") == "我為此描述著裡面的點擊"


def test_has_simplified_ambiguous_chars_and_queen():
    # STCharacters 一對多（种→種 种）的字：台灣幾乎不用的算簡體；岩台游里干栗伙 是台灣正常用字
    assert all(common.has_simplified(s) for s in ("种子", "范围", "你确定", "之后", "后面有"))
    assert not any(common.has_simplified(s) for s in ("皇后面前", "蜂后來了", "岩石台階游泳公里干擾栗木伙伴"))


def test_tw_fix_keeps_taiwan_wording_next_to_simplified(monkeypatch):
    # 夾簡體時只轉簡體所在的詞；緊鄰的台灣用語不可被 OpenCC 一起帶走（查看→檢視、點擊→點選）
    monkeypatch.setattr(common, "_glossary_rules", [("圓石", "鵝卵石")])
    assert common.tw_fix("右鍵點擊背包裡的圆石") == "右鍵點擊背包裡的鵝卵石"
    assert common.tw_fix("右鍵點擊背包，内存不足") == "右鍵點擊背包，記憶體不足"
    assert common.tw_fix("查看内存") == "查看記憶體"
    assert common.tw_fix("點擊内存") == "點擊記憶體"


def test_tw_fix_fully_simplified_equals_to_tw(monkeypatch):
    # 整句簡體：結果應與 to_tw 相同，不可錯位攪亂（召成、游遊、允允）
    monkeypatch.setattr(common, "_glossary_rules", [("傀儡", "魔像")])
    for s in ("用召唤一只铁傀儡来帮忙守卫村庄做", "用多人游戏中不允许使用当前名称做"):
        assert common.tw_fix(s) == common.to_tw(s)


def test_mainland_re_emperor_and_mixed_ganjing():
    assert not common.has_simplified("帝后面前")
    assert common.has_simplified("干淨") and common.tw_fix("干淨") == "乾淨"

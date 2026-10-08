from validate import check_text, check_value


def test_plain_ok():
    assert check_text("Iron Ingot", "鐵錠") is None


def test_placeholder_lost():
    assert "佔位符" in check_text("%s items", "物品")


def test_section_code_lost():
    assert "§" in check_text("§aGreen", "綠色")


def test_ampersand_in_lang_is_not_code():
    assert check_text("R&D Lab", "研發實驗室") is None
    assert check_text("Salt & Pepper", "鹽與胡椒") is None


def test_amp_code_checked_for_quests():
    assert check_text("&aHello", "哈囉", amp_codes=True) is not None
    assert check_text("&aHello", "&a哈囉", amp_codes=True) is None


def test_brace_token_preserved():
    en = "See {image:atm:textures/quests/a.png} here"
    assert check_text(en, "看這裡") is not None
    assert check_text(en, "看這裡 {image:atm:textures/quests/a.png}") is None


def test_newline_count():
    assert check_text("a\nb", "甲乙") is not None


def test_symbol_dropped_or_asciified():
    assert check_text("✔ Done", "完成") is not None
    assert check_text("Speed ×2", "速度 x2") is not None
    assert check_text("✔ Done", "✔ 完成") is None


def test_simplified_residue():
    assert check_text("Video", "视频") is not None


def test_empty():
    assert check_text("Hi", "  ") is not None
    assert check_text("", "") is None


def test_non_string():
    assert check_text("Hi", None) is not None


def test_list_line_count():
    assert "行數" in check_value(["a", "b"], ["甲"])


def test_list_empty_line_preserved():
    assert check_value(["a", "", "b"], ["甲", "x", "乙"]) is not None
    assert check_value(["a", "", "b"], ["甲", "", "乙"]) is None


def test_list_raw_json_line_untouched():
    j = '{"text":"Click","clickEvent":{"action":"open_url","value":"https://x"}}'
    assert check_value([j], ['{"text":"點我"}']) is not None
    assert check_value([j], [j]) is None


def test_type_mismatch():
    assert check_value("a", ["甲"]) is not None


def test_untranslated_sentence_rejected():
    assert "未翻譯" in check_text("Right-click to open", "Right-click to open")


def test_proper_noun_kept_ok():
    assert check_text("Mekanism", "Mekanism") is None
    assert check_text("FE/t", "FE/t") is None


def test_brace_only_line_not_untranslated():
    line = "{image:atm:textures/q.png width:200 height:50 align:center}"
    assert check_text(line, line) is None


def test_symbol_added_ok():
    assert check_text("heats to 2000C", "加熱到 2000°C") is None


def test_human_line_split_ok():
    en = ["Intro &aA&r\n\nMore text here"]
    zh = ["介紹 &aA&r", "", "更多文字"]
    assert check_value(en, zh, amp_codes=True) is not None
    assert check_value(en, zh, amp_codes=True, human=True) is None


def test_human_missing_reset_ok_but_color_required():
    assert check_text("&3Vibranium Template&r", "&3振金模板", amp_codes=True, human=True) is None
    assert check_text("&3Vibranium Template&r", "振金模板", amp_codes=True, human=True) is not None


def test_human_json_line_must_survive():
    j = '{"text":"Click","clickEvent":{"action":"open_url","value":"https://x"}}'
    assert check_value(["Hi there", j], ["嗨"], human=True) is not None
    assert check_value(["Hi there", j], ["嗨", "", j], human=True) is None


def test_two_word_names_kept_ok():
    assert check_text("[Anthophora urbana]", "[Anthophora urbana]") is None
    assert check_text("Productive Farming", "Productive Farming") is None


def test_amp_codes_may_merge_but_not_add_or_vanish():
    # 中文重組常把兩段同色／異色合併成一段 → 少幾個色碼只影響顏色，放行
    assert check_text("&3Wrath of the &eDesert", "&3沙漠之怒", amp_codes=True) is None
    assert check_text("The &bA&r or the &bB&r and &bA&r", "&bA&r還是&bB&r", amp_codes=True) is None
    # 多出來源沒有的色碼、或整串色碼丟光 → 仍退回
    assert check_text("&3Wrath of the Desert", "&3沙漠&e之怒", amp_codes=True) is not None
    assert check_text("&3Wrath of the &eDesert", "沙漠之怒", amp_codes=True) is not None
    # § 色碼維持嚴格守恆
    assert check_text("§3Wrath of the §eDesert", "§3沙漠之怒") is not None

# All the Mods 11 繁體中文化資源包 (zh_TW Resource Pack)

為 [All the Mods 11](https://www.curseforge.com/minecraft/modpacks/all-the-mods-11)（Minecraft 1.21.1 NeoForge，267 mods）產生**繁體中文（台灣）**資源包與 FTB Quests 任務書翻譯的自動化管線。

> [!WARNING]
> **本包大量使用 AI 機器翻譯。** 約 3.1 萬條 lang、443 頁指南書與 1,479 條任務書文字由 Claude 模型翻譯（haiku 首翻 → sonnet 重翻驗證不過者 → Opus 術語統一與審校），未經人工逐條校對。
> 有人工翻譯（mod 內建簡中、CFPA 簡中包）的條目優先採用並轉為繁體；AI 翻譯僅補其餘缺口。譯文品質統計見 [haiku 成績單](https://github.com/NatsuYukiowob/atm11-zhtw/blob/main/reports/haiku-scorecard.md)。

## 覆蓋範圍

- 220 個 mod 的 lang，共約 7.3 萬條；未覆蓋的字串自動 fallback 英文。
- Patchouli 指南書（Modonomicon 書位於 data pack，資源包無法覆蓋，未處理）。
- FTB Quests 任務書（`config/ftbquests/quests/lang/zh_tw/`）。

## 安裝

從 [Releases](https://github.com/NatsuYukiowob/atm11-zhtw/releases) 下載與你 modpack 版本相同的檔案（版本號對齊 CurseForge 上的 ATM11 版本，例：`v0.11.1-beta`）。

1. 把 `atm11-zhtw-<版本>.zip` 放進 instance 的 `resourcepacks/`。
2. 遊戲內：選項 → 資源包 → 啟用它並移到最上層。
3. 選項 → 語言 → 繁體中文（台灣）。
4. 任務書：解壓 `atm11-zhtw-ftbquests-<版本>.zip`，把裡面的 `zh_tw` 資料夾複製到 instance 的 `config/ftbquests/quests/lang/`（與 `en_us` 同一層）。

modpack 更新後譯文可能過期，需以新版 instance 重新產生。

## 管線架構

```
mods/*.jar ──┬─ en_us（翻譯目標）
             ├─ 內建 zh_tw（值≠英文才算已翻）
             └─ 內建 zh_cn ─┐
CFPA 簡中包───────────────┤→ OpenCC s2twp ＋ 術語表 → zh_tw
                            └─ 都沒有 → Claude 機翻 → 硬驗證 → zh_tw
```

- 術語表由官方 Minecraft `zh_cn`／`zh_tw` lang 逐 key 配對自動挖掘，疊加 `data/glossary_manual.json` 人工覆寫。
- 機翻每條都過硬驗證（`scripts/validate.py`）：佔位符、`§`／`&` 格式碼、`{}` 標記、換行數、非 ASCII 符號守恆，簡繁轉換冪等。不過者改派較強模型重翻一次，仍不過則保留英文。
- 機翻派工走 Claude Code Workflow（`workflows/translate.js`），批次放 `queue/<kind>/`。

## 使用

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
ln -s /path/to/ATM11/instance instance        # 或 export ATM11_INSTANCE=...
git clone --depth 1 --filter=blob:none --sparse https://github.com/CFPAOrg/Minecraft-Mod-Language-Package.git cfpa
(cd cfpa && git sparse-checkout set projects/assets)

.venv/bin/python scripts/s01_extract_mods.py    # 掃 mods/，抽 lang 與書頁
.venv/bin/python scripts/s02_fetch_vanilla.py   # 官方 vanilla zh_cn/zh_tw
.venv/bin/python scripts/s03_build_glossary.py  # 挖術語表
.venv/bin/python scripts/s04_harvest_cfpa.py    # 收割 CFPA 簡中
.venv/bin/python scripts/s05_convert.py         # 簡→繁，產出待機翻清單
# s06／s07／s07q 切批 → workflow 機翻 → 合併驗證（data/mt、data/book_mt、data/quests_mt.json）
# s10 術語統一＋審校；s11 成績單
.venv/bin/python scripts/s08_build_pack.py      # 驗證＋打包 dist/
.venv/bin/python -m pytest -q
```

## 授權與致謝

- 管線程式碼（`scripts/`、`workflows/`、`tests/`、`rules/`）：[MIT](https://github.com/NatsuYukiowob/atm11-zhtw/blob/main/LICENSE)。
- 譯文：簡中來源為 [CFPA 簡體中文翻譯包](https://github.com/CFPAOrg/Minecraft-Mod-Language-Package)（CC BY-NC-SA 4.0）及各 mod 內建翻譯，產出的資源包與任務書譯文為其衍生作品，依 **CC BY-NC-SA 4.0** 散布，禁止商用。原文著作權屬各 mod 作者與 All the Mods 團隊。
- 簡繁轉換：[OpenCC](https://github.com/BYVoid/OpenCC)。
- 機器翻譯：[Claude](https://www.anthropic.com/claude)（Anthropic）。

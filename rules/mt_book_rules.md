# Patchouli 指南書頁機翻規則（en → zh_TW 台灣繁體）

輸入是一個 JSON：`{"<modid>/<book>/<路徑>.json": 書頁物件}`。輸出結構完全相同的 JSON（同樣的外層 key、同樣的書頁結構）。

對每個書頁物件，**只翻譯**下列欄位的值（任何深度）：
`name`、`title`、`subtitle`、`text`、`description`、`landing_text`、`header`
其他欄位（`type`、`icon`、`item`、`recipe`、`advancement`、`category`、`entity`、座標數字…）**一個字元都不能動**。
值長得像 translation key（`a.b.c`）、資源 ID（`modid:path`）或以 `#` 開頭的，原樣保留。

## Patchouli 標記（必須原樣保留結構）
- `$(l:path/to/entry)顯示文字/$` — 連結：`l:` 後的路徑不動，只翻「顯示文字」
- `$(item)`、`$(thing)`、`$(o)`、`$(bold)`、`$(br)`、`$(br2)`、`$(li)`、`$(0)`…`$(f)`、`$()`、`/$` — 全部原樣保留，數量不可增減
- `$(k:use)`、`$(k:sneak)` — 按鍵參照，不動
- 範例：`Craft a $(item)Pressure Gauge/$ to measure $(l:base_concepts/pressure)pressure/$.`
  → `製作一個$(item)壓力計/$來測量$(l:base_concepts/pressure)壓力/$。`

## 其他
- 保留所有非 ASCII 字元與格式符號原樣（✔ ★ → × § 等），不得轉成 ASCII 等價字元。
- `\n` 數量不變；`%s` 等佔位符原樣。
- 譯名與語氣遵守 `rules/mt_rules.md`（同一個 repo）。

## 輸出
用 Write 工具把 JSON 寫到指定輸出路徑（UTF-8、中文直出）。

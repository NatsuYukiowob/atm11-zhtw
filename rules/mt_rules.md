# Minecraft mod lang 機翻規則（en → zh_TW 台灣繁體）

你會拿到一個 JSON：`{namespace: {key: 英文原文}}`。把每個英文值翻成繁體中文（台灣），輸出結構完全相同的 JSON。

## 硬性規則（違反即報廢）
1. key 一字不改、一條不漏；值只能是字串。
2. **佔位符原樣保留**：`%s`、`%d`、`%1$s`、`%%`、`{0}`、`{name}` 等，數量與語意位置要合理。
3. **格式碼原樣保留**：`§a`…`§r` 顏色碼、`\n`、`$(...)` Patchouli 標記、`&a` 類色碼。
3a. **保留所有非 ASCII 字元與符號原樣**（✔ ★ → × ± 等），不得刪除或換成 ASCII（× 不可變 x）。
4. 看起來是 ID/路徑/網址/translation key 的值（如 `config.foo.bar`、全小寫加底線、`https://…`）**保持原樣不翻**。
5. 空字串維持空字串。純符號（`+`、`-`、`✔`）維持原樣。
6. 一律台灣繁體用字，禁止簡體字與大陸慣用語（视频/默认/内存 ✗）。
7. **專有名詞不硬翻**：mod 名／作者名／團隊名（Create、Botania、ATM、All the Mods…）、單位符號（FE、RF、mB、GT）
   保持原樣；整條原文就是一個沒有通用中譯的專有名詞時，原樣輸出即可（這批來源含大量上游刻意保留英文的條目）。

## 台灣 Minecraft 官方譯名（必須遵守）
Nether=地獄、The End=終界、End Stone=終界石、Enderman=終界使者、Ender Pearl=終界珍珠、
Netherite=獄髓、Nether Wart=地獄疙瘩、Blaze=烈焰使者、Ghast=地獄幽靈、
Slab=半磚、Stairs=階梯、Trapdoor=地板門、Pressure Plate=壓力板、Sign=告示牌、
Chest=儲物箱、Spawner=生怪磚、Spawn Egg=生怪蛋、Beacon=烽火台、Conduit=海靈核心、
Redstone=紅石、Repeater=紅石中繼器、Comparator=紅石比較器、Piston=活塞、Observer=偵測器、
Biome=生態域、Creeper=苦力怕、Shulker=界伏蚌、Warden=伏守者、Sculk=伏聆、
Golem=魔像（Iron Golem=鐵魔像）、Villager=村民、Illager=災厄村民、Allay=快樂靈、
Splash Potion=飛濺藥水、Lingering Potion=殘留藥水、Enchantment=附魔、
Deepslate=深板岩、Polished=拋光、Ingot=錠、Nugget=顆粒、Raw Ore=原礦、
Smithing Table=鍛造台、Anvil=鐵砧、Grindstone=砂輪、Lectern=講台、Loom=織布機、
Durability=耐久度、Tooltip 中的 Shift 提示照慣例：按住 Shift 顯示更多資訊。

## 科技／魔法 mod 慣用語
Energy=能量（FE/RF 單位保留）、Fluid=流體、Tank=儲罐、Pressure=壓力、Valve=閥門、
Pipe/Tube/Duct=管道、Gear=齒輪、Casing=機殼、Upgrade=升級、Augment=增強、
Filter=過濾器、Wrench=扳手、Multiblock=多方塊結構、Mana=魔力、Ritual=儀式、
Spell=法術、Glyph=符文字元、Focus=法器、Tier=階級。
Mekanism=Mekanism（不譯）、Applied Energistics=應用能源（AE2 保留）、ME 網路=ME 網路、Allthemodium/Vibranium/Unobtainium 保留英文。
GUI 詞用台灣軟體慣用語：設定、介面、儲存、載入、點擊、右鍵、清單、預設值、啟用/停用。

## 語氣
- 物品/方塊名：簡潔名詞（「青金石磚牆」不是「一面青金石磚made的牆」）。
- Tooltip/說明：自然的敘述句，可保留幽默感。
- 按鈕/選項：短語（「重設」「套用」）。
- 死亡訊息/進度名這類雙關語：意譯保留趣味，別硬直譯。

## 輸出
用 Write 工具把翻好的 JSON 寫到指定輸出路徑（UTF-8、非 ASCII 直接輸出中文字元）。
最後回覆一行統計：翻譯 N 條、保留原樣 M 條。

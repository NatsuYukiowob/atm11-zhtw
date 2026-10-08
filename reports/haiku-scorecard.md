# haiku 成績單

## 首翻（haiku）與重翻（sonnet）

| 類型 | haiku 首翻 | 通過率 | sonnet 重翻 | sonnet 通過率 | 最終保留英文 |
|---|---|---|---|---|---|
| book | 443 | 96.2% | 17 | 94.1% | 1 |
| lang | 31387 | 99.5% | 156 | 42.3% | 90 |
| quest | 1479 | 90.9% | 135 | 92.6% | 10 |

## haiku 首翻通過率 × 英文長度

| 長度 | 條數 | 通過率 |
|---|---|---|
| short | 20667 | 99.7% |
| sentence | 10359 | 98.9% |
| long | 2283 | 94.3% |

## Opus 審校

- 審校 2829 條，修正 373 條（13.2%）
- 術語統一改寫 1961 條

| 原譯者 | 審校 | 修正 | 修正率 |
|---|---|---|---|
| haiku | 2680 | 349 | 13.0% |
| sonnet | 149 | 24 | 16.1% |

## haiku 退回最多的 namespace（前 20）

| namespace | 退回 | 首翻數 | 退回率 |
|---|---|---|---|
| _quests | 135 | 1479 | 9.1% |
| productivefarming | 36 | 181 | 19.9% |
| productivetrees | 33 | 4158 | 0.8% |
| aether_ii | 22 | 1688 | 1.3% |
| occultism | 19 | 564 | 3.4% |
| productivebees | 13 | 105 | 12.4% |
| integrateddynamics | 10 | 904 | 1.1% |
| deepnullreforged | 8 | 252 | 3.2% |
| apotheosis | 4 | 23 | 17.4% |
| crashutilities | 4 | 4 | 100.0% |
| mffs | 2 | 65 | 3.1% |
| modularrouters | 2 | 79 | 2.5% |
| arsmagicalegacy | 2 | 1645 | 0.1% |
| enchdesc | 2 | 12 | 16.7% |
| justdirethings | 2 | 7 | 28.6% |
| modonomicon | 2 | 318 | 0.6% |
| aquaculture | 1 | 15 | 6.7% |
| cloth-config2 | 1 | 1 | 100.0% |
| evilcraftcompat | 1 | 29 | 3.4% |
| ftbchunks | 1 | 306 | 0.3% |

## haiku 退回原因（前 10）

| 原因 | 次數 |
|---|---|
| 未翻譯（與英文相同） | 145 |
| & 格式碼不守恆 | 113 |
| 換行數不符 | 26 |
| 佔位符 | 9 |
| 缺漏 | 7 |
| $() 標記數不符 | 4 |
| 疑似簡體/未收斂 | 3 |
| § 格式碼不守恆 | 1 |

## 註記

- 判定都是合併當下的規則。任務書 & 色碼在 haiku 合併後才放寬為「只少不多」（2026-10-08），haiku 任務書列仍是舊的嚴格判定 → 通過率偏低；sonnet 列已用新規則重驗。
- 「未翻譯（與英文相同）」多為三字以上的專名（曲目「作者 - 曲名」、地名），保留英文是正確結果，不全是模型失誤；lang 的 sonnet 低通過率主要來自這類。
- 首翻成本（API 等價，實際走訂閱額度）見 docs/discovery.md。

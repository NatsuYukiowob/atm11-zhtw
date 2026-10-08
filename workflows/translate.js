export const meta = {
  name: 'atm11-translate',
  description: 'ATM11 繁中化：每個 queue 批次派一個 agent 依規則檔翻譯並寫出輸出檔',
  whenToUse: '在 WSL 的 atm11-zhtw repo；args 由 python3 scripts/batchq.py args <kind> <model> 產生',
  phases: [{ title: 'Translate', detail: '一批一個 agent，寫 queue/<kind>/out/' }],
}

const RESULT = {
  type: 'object',
  properties: {
    written: { type: 'boolean' },
    translated: { type: 'integer' },
    kept: { type: 'integer' },
    note: { type: 'string' },
  },
  required: ['written', 'translated', 'kept'],
}

const { repo, kind, model, rules, batches } = args
const TASK = {
  lang: '把每個英文值翻成台灣繁體中文',
  book: '翻譯每個書頁物件的文字欄位',
  quest: '把每個英文值（字串或逐行陣列）翻成台灣繁體中文',
  review: '審校機翻：只輸出你要修改的條目',
  terms: '為每個英文名稱選定標準譯名',
}

phase('Translate')
log(`${kind} × ${batches.length} 批，model=${model}`)
const results = await parallel(batches.map(b => () => {
  const opts = { label: `${kind}:${b.id}`, phase: 'Translate', model, schema: RESULT }
  if (model === 'haiku') opts.effort = 'low'
  return agent(
    `任務：${TASK[kind]}。\n` +
    `1. 用 Read 讀規則檔 ${repo}/${rules}，嚴格遵守（規則檔提到的其他檔案也用 ${repo}/ 開頭的路徑讀）。\n` +
    `2. 用 Read 讀輸入 ${repo}/${b.in}。\n` +
    `3. 用 Write 把結果 JSON 寫到 ${repo}/${b.out}（UTF-8、中文直出、合法 JSON）。\n` +
    `保留所有非 ASCII 字元與格式符號原樣，不得轉成 ASCII 等價字元。不要改動任何其他檔案。\n` +
    `完成後回報：written（是否已寫出檔案）、translated（翻譯/修改條數）、kept（保留原文條數）、note（異常說明，可空）。`,
    opts,
  ).then(r => ({ id: b.id, ...(r || { written: false, translated: 0, kept: 0, note: 'agent 無回傳' }) }))
}))
const ok = results.filter(r => r && r.written)
const failed = batches.map(b => b.id).filter(id => !ok.some(r => r.id === id))
log(`寫出 ${ok.length}/${batches.length}；未寫出：${failed.join(', ') || '無'}`)
return { results, failed }

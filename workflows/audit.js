export const meta = {
  name: 'atm11-audit',
  description: 'ATM11 jar 內建 zh_tw 審查：sonnet 標記問題；驗證組反方驗證（error→opus、minor→sonnet）',
  whenToUse: '在 WSL ~/work/atm11-audit（workflows/wsl_audit_run.sh）；args 由 scripts/s13_audit.py args 產生',
  phases: [{ title: 'Review', detail: 'sonnet 審查' }, { title: 'Verify', detail: '反方驗證（error→opus、minor→sonnet）' }],
}

const RESULT = {
  type: 'object',
  properties: { written: { type: 'boolean' }, flagged: { type: 'integer' }, note: { type: 'string' } },
  required: ['written', 'flagged'],
}

const { repo, batches } = args

function review(b) {
  return agent(
    `任務：審查繁中譯文。\n` +
    `1. 用 Read 讀規則檔 ${repo}/rules/audit_rules.md，嚴格遵守（規則檔提到的其他檔案用 ${repo}/ 開頭的路徑讀）。\n` +
    `2. 用 Read 讀輸入 ${repo}/${b.in}。\n` +
    `3. 用 Write 把結果 JSON 寫到 ${repo}/${b.out}（UTF-8、中文直出、合法 JSON；沒問題也要寫 {}）。\n` +
    `不要改動任何其他檔案。完成後回報 written、flagged（標記條數）、note。`,
    { label: `review:${b.id}`, phase: 'Review', model: 'sonnet', schema: RESULT },
  )
}

function verify(b) {
  return agent(
    `任務：反方驗證審查者的標記。\n` +
    `1. 用 Read 讀規則檔 ${repo}/rules/audit_verify_rules.md，嚴格遵守。\n` +
    `2. 用 Read 讀輸入 ${repo}/${b.in}（每條含原文、譯文與審查者標記）。\n` +
    `3. 用 Write 把判決 JSON 寫到 ${repo}/${b.verify}（UTF-8、中文直出、合法 JSON）。\n` +
    `不要改動任何其他檔案。完成後回報 written、flagged（判決條數）、note。`,
    { label: `verify:${b.id}`, phase: 'Verify', model: b.model, schema: RESULT },
  )
}

log(`audit × ${batches.length} 批`)
// 審查與驗證互相獨立：剛審完的批，其標記由下一次 s13_audit args 分組後再驗（流程見 CLAUDE.md「s13 審查」）
const results = await pipeline(batches, b =>
  (b.need === 'sonnet' ? review(b) : verify(b)).then(r => ({ id: b.id, r })),
)
const failed = results.filter(x => !x || !x.r || !x.r.written).map(x => x && x.id)
log(`完成 ${results.length - failed.length}/${batches.length}；失敗：${failed.join(', ') || '無'}`)
return { failed }

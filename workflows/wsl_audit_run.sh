#!/usr/bin/env bash
# 用法（在 WSL ~/work/atm11-audit）：bash wsl_audit_run.sh <args.json>；目錄內容與流程見 CLAUDE.md「s13 審查」
cd "$(dirname "$0")"
ARGS=$(cat "$1")
echo "start $1 $(date -Is)"
CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 ~/.local/bin/claude -p "使用者明確要求執行 workflow（不需再確認）。呼叫 Workflow 工具：scriptPath=$PWD/audit.js，args 為以下 JSON（以物件傳入，不要轉成字串）：$ARGS 。等 workflow 完成後，只回覆它回傳值中的 failed 陣列。" --permission-mode acceptEdits --allowedTools Workflow Read Write --output-format text
echo "exit=$? $(date -Is)"

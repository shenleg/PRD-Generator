#!/bin/sh
# 本次试跑的生产脚本命令；所有输出保存在 artifacts。
ROOT=/home/collin/orca/PRD-Generator/workspace-sandbox/prd-generator/stage-5-model/iteration-1/current-skill-snapshot
TRIAL=/home/collin/orca/PRD-Generator/.claude/worktrees/agent-ab17c6bd5a2d7e52a/stage-5-trial
for scenario in content-request ambiguous-request layout-request manual-layout; do
  uv run --offline --no-project --python /usr/bin/python3 --with-requirements "$ROOT/requirement-analyst/scripts/requirements.txt" python -I -B "$ROOT/prd-generator/scripts/check_sync.py" "$TRIAL/workspace/$scenario" > "$TRIAL/artifacts/$scenario-check-sync.json" 2> "$TRIAL/artifacts/$scenario-check-sync.stderr"
  printf '%s check_sync exit=%s\n' "$scenario" "$?"
  uv run --offline --no-project --python /usr/bin/python3 --with-requirements "$ROOT/requirement-analyst/scripts/requirements.txt" python -I -B "$ROOT/prd-generator/scripts/write_draft.py" "$TRIAL/workspace/$scenario" --inspect-edits > "$TRIAL/artifacts/$scenario-inspect-edits.json" 2> "$TRIAL/artifacts/$scenario-inspect-edits.stderr"
  printf '%s inspect_edits exit=%s\n' "$scenario" "$?"
done

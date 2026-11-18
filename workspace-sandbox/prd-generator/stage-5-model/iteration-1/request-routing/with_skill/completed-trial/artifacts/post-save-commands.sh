#!/bin/sh
# 检查两份保存后的草稿。
ROOT=/home/collin/orca/PRD-Generator/workspace-sandbox/prd-generator/stage-5-model/iteration-1/current-skill-snapshot
TRIAL=/home/collin/orca/PRD-Generator/.claude/worktrees/agent-ab17c6bd5a2d7e52a/stage-5-trial
for scenario in layout-request manual-layout; do
  uv run --offline --no-project --python /usr/bin/python3 --with-requirements "$ROOT/requirement-analyst/scripts/requirements.txt" python -I -B "$ROOT/prd-generator/scripts/check_sync.py" "$TRIAL/workspace/$scenario" > "$TRIAL/artifacts/$scenario-post-save-check.json" 2> "$TRIAL/artifacts/$scenario-post-save-check.stderr"
  printf '%s post-save check exit=%s\n' "$scenario" "$?"
done

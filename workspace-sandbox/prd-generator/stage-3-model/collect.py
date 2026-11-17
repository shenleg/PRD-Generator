"""归档实际代理返回的试跑目录与耗时并建立人工评审视图，不推测尚未返回的结果。"""

import argparse
import json
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--runs", type=Path, required=True, help="来自实际工作流返回的路径与计量清单")
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).parent / "iteration-1"
REVIEW = ROOT / "tests/results/prd-generator/stage-3-model-review"
evals = json.loads((REVIEW / "evals.json").read_text())
records = json.loads(args.runs.read_text())
for run in records:
    group, config = run["group"], run["configuration"]
    original = Path(run["output_dir"])
    raw = BASE / "raw" / group / config
    shutil.copytree(original, raw)
    if run.get('transcript_file'):
        clean_rows = []
        for line in Path(run['transcript_file']).read_text().splitlines():
            entry = json.loads(line)
            message = entry.get('message', {})
            if entry.get('type') not in ('user', 'assistant'):
                continue
            content = message.get('content')
            if isinstance(content, list):
                content = [block for block in content if isinstance(block, dict) and block.get('type') in ('text', 'tool_use', 'tool_result')]
            if content:
                clean_rows.append({'timestamp': entry.get('timestamp'), 'role': message.get('role'), 'content': content})
        (raw / 'conversation-visible.jsonl').write_text(''.join(json.dumps(entry, ensure_ascii=False) + '\n' for entry in clean_rows))
    case = next(item for item in evals["evals"] if item["eval_name"] == group)
    target = REVIEW / f"eval-{case['id']}-{group}" / config / "run-1"
    outputs = target / "outputs"
    outputs.mkdir(parents=True, exist_ok=False)
    metadata = {"eval_id": case["id"], "eval_name": group, "prompt": case["prompt"], "assertions": case["assertions"]}
    for path in (target / "eval_metadata.json", target.parent.parent / "eval_metadata.json"):
        path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    for path in raw.rglob("requirement.json"):
        # 只展示实际工作区，不把候选副本或冻结输入当成额外交付。
        if "workspaces" not in path.relative_to(raw).parts:
            continue
        metadata = json.loads(path.read_text())
        if not isinstance(metadata.get("prd"), dict):
            continue
        rid = metadata["common"]["requirement_id"]
        if path.parent.name != rid:
            continue
        for filename in ("prd.md", "prd-trace.json", "gap-requests.json"):
            source = path.parent / "prd" / filename
            if source.exists():
                shutil.copyfile(source, outputs / f"{rid}-{filename}")
    for path in raw.rglob("model-response.md"):
        if "skill" not in path.relative_to(raw).parts:
            shutil.copyfile(path, outputs / ("model-response.md" if not (outputs / "model-response.md").exists() else "model-response-" + path.parent.name + ".md"))
    (target / "timing.json").write_text(json.dumps(run["timing"], ensure_ascii=False, indent=2) + "\n")
    (target / "archive.json").write_text(json.dumps({"original_output_dir": str(original), "raw_archive": str(raw.relative_to(ROOT)),
                "configuration": config, "group": group, "human_review": "pending", "agent_report": run.get("agent_report", "")}, ensure_ascii=False, indent=2) + "\n")
print(REVIEW)

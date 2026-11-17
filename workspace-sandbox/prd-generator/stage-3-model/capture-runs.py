"""从已完成工作流结果保存四次模型运行的真实路径、用量与计时，不推断未返回结果。"""

import argparse
import json
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--workflow-output", type=Path, required=True)
parser.add_argument("--transcript-dir", type=Path, required=True)
args = parser.parse_args()
workflow = json.loads(args.workflow_output.read_text())
records = []
for node in workflow["workflowProgress"]:
    if node.get("type") != "workflow_agent" or ":" not in node.get("label", ""):
        continue
    if node.get("state") != "done":
        raise ValueError("模型任务尚未完成，不归档预测结果")
    group, config = node["label"].split(":", 1)
    order = next(index for index, result in enumerate(workflow["result"]) if f"/{group}/{config}/`" in str(result))
    report = workflow["result"][order]
    output = re.search(r"`(/[^`]+/" + re.escape(group) + "/" + re.escape(config) + r"/)`", report).group(1)
    records.append({"group": group, "configuration": config, "output_dir": output, "agent_report": report,
                    "transcript_file": str(args.transcript_dir / f"agent-{node['agentId']}.jsonl"),
                    "timing": {"total_tokens": node["tokens"], "duration_ms": node["durationMs"],
                               "total_duration_seconds": node["durationMs"] / 1000,
                               "measurement_source": "completed_workflow_runtime"}})
if len(records) != 4:
    raise ValueError(f"预期四次实际运行，收到{len(records)}次")
output = Path(__file__).parent / "iteration-1/runs.json"
if output.exists():
    raise FileExistsError(output)
output.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
print(output)

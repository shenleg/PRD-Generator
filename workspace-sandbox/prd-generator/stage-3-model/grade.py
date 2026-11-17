"""按真实模型产物核对客观结构与文件归属，记录计数；不为自然语言忠实性或人工验收签字。"""

import argparse
import importlib.util
import json
from pathlib import Path


def load(name, path):
    """从可信生产path加载name并返回模块；导入错误原样抛出。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    """读取内部JSON留证并返回对象；文件或格式错误直接报告，不跳过失败记录。"""
    return json.loads(path.read_text(encoding="utf-8"))


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--review", type=Path, required=True)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).parent / "iteration-1"
validator = load("model_grading_validator", ROOT / "skill/prd-generator/scripts/validate_prd.py")
renderer = load("model_grading_renderer", ROOT / "skill/prd-generator/scripts/render_info.py")
all_results = []
for eval_dir in sorted(args.review.glob("eval-*")):
    metadata = read(eval_dir / "eval_metadata.json")
    for config in ("with_skill", "without_skill"):
        run = eval_dir / config / "run-1"
        archive = read(run / "archive.json")
        raw = ROOT / archive["raw_archive"]
        expected_inputs = BASE / "inputs" / metadata["eval_name"]
        candidates = []
        for path in raw.rglob("requirement.json"):
            if "skill" not in path.relative_to(raw).parts:
                candidates.append((path.parent, read(path)))
        successful_candidates = set()
        for response_path in raw.rglob('*'):
            if not response_path.is_file() or response_path.suffix not in ('.stdout', '.json') or 'skill' in response_path.relative_to(raw).parts:
                continue
            try:
                response = read(response_path)
                if isinstance(response, dict) and isinstance(response.get('stdout'), str):
                    response = json.loads(response['stdout'])
            except (ValueError, UnicodeError):
                continue
            if isinstance(response, dict) and response.get('generated') is True and response.get('version') == '0.1':
                relative = Path(response['candidate_dir']).relative_to(Path(archive['original_output_dir']))
                successful_candidates.add(raw / relative)
        rows = []
        for original in sorted(expected_inputs.iterdir()):
            rid = original.name
            matches = [(path, value) for path, value in candidates if path.name == rid and "workspaces" in path.relative_to(raw).parts and value.get("common", {}).get("requirement_id") == rid and isinstance(value.get("prd"), dict) and (path / "prd/prd-trace.json").is_file()]
            row = {"requirement_id": rid, "generated": bool(matches), "human_review": "pending"}
            rows.append(row)
            if len(matches) != 1:
                row["error"] = f"工作区产物匹配数量为{len(matches)}，不能当作唯一完整生成"
                continue
            workspace, requirement = matches[0]
            row["workspace"] = str(workspace.relative_to(ROOT))
            row["analysis_unchanged"] = (workspace / "analysis/analysis-result.json").read_bytes() == (original / "analysis/analysis-result.json").read_bytes()
            row["common_unchanged"] = requirement.get("common") == read(original / "requirement.json").get("common")
            row["draft_only"] = requirement.get("prd", {}).get("status") == "draft" and not (workspace / "prd/versions").exists()
            row["program_validation"] = validator.validate_prd(workspace)
            trace = read(workspace / "prd/prd-trace.json")
            row["draft_kind"] = trace["meta"]["draft_kind"]
            row["version"] = requirement["prd"]["version"]
            text = (workspace / "prd/prd.md").read_text()
            blocks = validator._blocks(text, [])
            registry, _ = validator._registry([read(workspace / "analysis/analysis-result.json")])
            row["trace_total"] = len(trace["items"])
            row["valid_trace_count"] = sum(bool(item["analysis_refs"]) and all(ref in registry for ref in item["analysis_refs"]) for item in trace["items"])
            tagged = [item for item in trace["items"] if item["status"] != "abolished" and (item["tag"] != "confirmed" or item["status"] == "to_confirm")]
            row["label_total"] = len(tagged)
            row["label_preserved"] = sum(all(label in blocks["item"].get(item["prd_id"], {}).get("text", "") for label in (["【推断】"] if item["tag"] == "inferred" else ["【暂定】"] if item["tag"] == "assumption" else []) + (["【待确认】"] if item["status"] == "to_confirm" else [])) for item in tagged)
            row["content_hash_valid"] = trace["meta"]["content_hash"] == validator._sha((workspace / "prd/prd.md").read_bytes())
            # 只使用有generated=true真实响应的首次落盘候选，不能误拿先前校验失败的修正材料。
            first = [(path, value) for path, value in candidates if path in successful_candidates and value.get("common", {}).get("requirement_id") == rid and value.get("prd", {}).get("version") == "0.1" and (path / "prd/prd-trace.json").exists()]
            row["repeat_evidence_found"] = bool(first) and row["version"] == "0.2"
            row["repeat_stable"] = False
            if row["repeat_evidence_found"]:
                first_path, _ = first[0]
                old_trace = read(first_path / "prd/prd-trace.json")
                old_text = (first_path / "prd/prd.md").read_text()
                old_body = renderer._take_section(renderer._take_section(old_text, 'info'), 'changes').strip('\r\n')
                new_body = renderer._take_section(renderer._take_section(text, 'info'), 'changes').strip('\r\n')
                row['first_successful_candidate'] = str(first_path.relative_to(ROOT))
                row["repeat_stable"] = old_trace["items"] == trace["items"] and old_body == new_body
        assertions = [
            ("所有预期独立需求均实际生成且当前结构校验无失败", all(row.get("generated") and row.get("program_validation", {}).get("status") in ("pass", "warning") for row in rows)),
            ("分析原始字节及common保持，不发布或合并需求", all(row.get("analysis_unchanged") and row.get("common_unchanged") and row.get("draft_only") for row in rows)),
            ("所有正式条目有有效完整引用及正确正文摘要", all(row.get("trace_total") == row.get("valid_trace_count") and row.get("content_hash_valid") for row in rows)),
            ("风险草稿和可程序识别的逐条标注保持", all(row.get("draft_kind") == "risk_draft" and row.get("label_total") == row.get("label_preserved") for row in rows)),
            ("同输入重复生成至0.2且需求正文与编号保持", all(row.get("repeat_stable") for row in rows)),
        ]
        expectations = [{"text": text, "passed": bool(passed), "evidence": "见本运行outputs/programmatic-verification.json的逐需求计数与实际文件路径"} for text, passed in assertions]
        passed = sum(item["passed"] for item in expectations)
        grading = {"expectations": expectations, "summary": {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations), "pass_rate": passed / len(expectations)},
                   "user_notes_summary": {"uncertainties": ["只评客观结构与文件归属，不评自然语言忠实性或缺口是否必要；警告是否充分解释须查看模型答复。"], "needs_review": ["按已认可业务参考逐条人工核对需求、范围、推断和遗留事项"], "workarounds": []}}
        (run / "grading.json").write_text(json.dumps(grading, ensure_ascii=False, indent=2) + "\n")
        verification = {"group": metadata["eval_name"], "configuration": config, "human_review": "pending", "requirements": rows}
        (run / "outputs/programmatic-verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n")
        all_results.append(verification)
(args.review / "programmatic-summary.json").write_text(json.dumps(all_results, ensure_ascii=False, indent=2) + "\n")
print(args.review / "programmatic-summary.json")

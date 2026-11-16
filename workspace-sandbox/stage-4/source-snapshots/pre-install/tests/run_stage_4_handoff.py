"""运行阶段 4 确定性交接剧本并保留证据；不调用模型，不修改阶段 3 原始记录。"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
# -I 模式显式加载本仓库可信测试目录，不使用当前目录或外部 PYTHONPATH。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_minimal_prd_consumer import ready_patch, feedback_patch
from test_update_analysis import load_module, initial, common, read_json


PRODUCTION = ROOT / "skill/requirement-analyst"


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path) -> dict:
    """向全新 output 运行六个合成场景及三个旧样例消费，返回有指纹的证据清单。

    output 已存在时抛出 FileExistsError，不覆盖旧记录；文件和安装错误直接抛出，
    断言失败立即停止并保留现场。记录仅证明真实脚本运行，不是模型或真实需求试用。
    """
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    consumer = load_module(ROOT / "tools/minimal_prd_consumer.py", "recorded_consumer")
    updater = load_module(PRODUCTION / "scripts/update_analysis.py", "recorded_updater")
    requirement, project = "HANDOFF-TEST", "handoff"

    def apply(case, name, patch, expected="pass"):
        """保存 case/name 的 patch 与实际更新响应，返回响应；失败断言保留原始记录。"""
        workspace = output / case / "workspace"
        _save(output / case / "patches" / f"{name}.json", patch)
        result = updater.update_analysis(workspace, project, patch)
        _save(output / case / "updates" / f"{name}.json", result)
        directory = workspace / "projects" / project / "requirements" / requirement
        if directory.exists():
            shutil.copytree(directory, output / case / "snapshots" / name)
        assert result["status"] == expected, result
        return result

    def call(case, name, **kwargs):
        """保存 case/name 的消费响应，核对受保护文件；kwargs 是本轮明确的调用参数。"""
        workspace = output / case / "workspace"
        directory = workspace / "projects" / project / "requirements" / requirement
        before = {str(p.relative_to(directory)): p.read_bytes() for p in (directory / "analysis").glob("*") if p.is_file()}
        common_before = read_json(directory / "requirement.json")["common"] if directory.exists() else None
        result = consumer.consume(workspace, project, requirement, **kwargs)
        after = {str(p.relative_to(directory)): p.read_bytes() for p in (directory / "analysis").glob("*") if p.is_file()}
        assert before == after
        if common_before is not None:
            assert read_json(directory / "requirement.json")["common"] == common_before
        _save(output / case / "calls" / f"{name}.json", {"options": kwargs, "response": result, "analysis_unchanged": before == after, "common_unchanged": True})
        return result

    result = call("RA-24", "missing")
    assert result["action"] == "analyze" and not result["written"]
    assert not (output / "RA-24/workspace").exists()

    patch = ready_patch()
    patch["set"].update({"meta.analysis_status": "stale", "meta.readiness": "not_ready"})
    apply("RA-25", "initial-stale", patch, "warning")
    assert call("RA-25", "default")["action"] == "reevaluate"
    result = call("RA-25", "insisted", insist_stale=True)
    assert result["status"] == "warning" and result["written"]
    draft = output / "RA-25/workspace/projects/handoff/requirements" / requirement / result["draft_path"]
    assert "基于过期分析" in draft.read_text(encoding="utf-8")

    patch = initial(requirement)
    patch["set"]["meta.analysis_status"] = "completed"
    apply("RA-26", "initial-not-ready", patch)
    result = call("RA-26", "preliminary")
    assert result["status"] == "warning" and result["written"]

    apply("RA-27", "initial", ready_patch())
    assert call("RA-27", "draft-v1")["sync_state"] == "current"
    patch = ready_patch()
    patch.pop("title")
    patch.update({"base_revision": 1, "change_type": "supplement", "summary": "合成修订同步测试", "operations": [], "set": {}})
    apply("RA-27", "supplement", patch)
    assert call("RA-27", "pending", inspect_only=True)["sync_state"] == "pending"
    result = call("RA-27", "draft-v2", expected_revision=2)
    assert result["sync_state"] == "current" and result["revision"] == 2

    patch = ready_patch()
    patch["set"]["meta.readiness"] = "conditionally_ready"
    patch["operations"] += [
        {"op": "add", "collection": "business_assessment.boundaries", "ref": "$boundary", "value": {**common("合成待重评边界"), "status": "to_reassess"}},
        {"op": "add", "collection": "business_assessment.exceptions", "ref": "$withdrawn", "value": {**common("撤销内容哨兵"), "status": "withdrawn"}},
        {"op": "add", "collection": "questions", "ref": "$pending", "value": {"question": "合成范围如何验证？", "priority": "P1", "resolution": "ask_product", "reason": "暂定", "impact": "范围", "options": ["甲", "乙"], "recommendation": "暂用甲", "status": "provisional", "related_ids": ["FR-1"]}},
        {"op": "add", "collection": "assumptions", "ref": "$assumption", "value": {**common("合成暂定范围", tag="assumption"), "related_question": "$pending", "basis": "合成推荐依据", "verification": "产品负责人后续核对合成输入"}},
    ]
    apply("RA-28", "initial-tags", patch)
    result = call("RA-28", "tagged-draft")
    text = (output / "RA-28/workspace/projects/handoff/requirements" / requirement / result["draft_path"]).read_text(encoding="utf-8")
    assert all(value in text for value in ("inferred", "assumption", "待验证", "to_reassess", "HANDOFF-TEST/FR-1"))
    assert "撤销内容哨兵" not in text

    patch = ready_patch()
    patch["operations"] = [op for op in patch["operations"] if op["collection"] != "requirements.acceptance_criteria"]
    apply("RA-29", "initial-no-acceptance", patch)
    assert call("RA-29", "draft-before-template-check")["written"]
    result = call("RA-29", "gap-request", required_sections=("requirements.acceptance_criteria",))
    assert result["action"] == "register_questions" and not result["written"]
    directory = output / "RA-29/workspace/projects/handoff/requirements" / requirement
    analysis = read_json(directory / "analysis/analysis-result.json")
    reviewed = feedback_patch(analysis, result["feedback"])
    update = apply("RA-29", "analyst-reviewed-feedback", reviewed)
    assert update["id_map"]["$handoff_question"] == "Q-1"
    assert call("RA-29", "pending-after-registration", inspect_only=True)["sync_state"] == "pending"
    apply("RA-29", "stale-feedback-rejected", reviewed, "fail")

    samples = []
    for sample_project, sample_id in (("probes", "PROBE-BACKEND"), ("probes", "PROBE-NOTIFICATION"), ("high-low-voltage", "REQ-2026-001")):
        source = ROOT / "workspace-sandbox/stage-3/workspace/projects" / sample_project / "requirements" / sample_id
        workspace = output / "samples/workspace"
        destination = workspace / "projects" / sample_project / "requirements" / sample_id
        shutil.copytree(source, destination)
        before = {p.name: _sha(p) for p in (source / "analysis").iterdir() if p.is_file()}
        result = consumer.consume(workspace, sample_project, sample_id)
        assert result["written"], result
        assert before == {p.name: _sha(p) for p in (destination / "analysis").iterdir() if p.is_file()}
        _save(output / "samples/calls" / f"{sample_id}.json", result)
        samples.append({"project": sample_project, "requirement_id": sample_id, "origin": str(source.relative_to(ROOT)), "analysis_sha256": before, "status": result["status"]})

    sources = [ROOT / "tools/minimal_prd_consumer.py", Path(__file__), ROOT / "tests/test_minimal_prd_consumer.py", ROOT / "tests/test_update_analysis.py", ROOT / "需求分析skill-需求规格说明.md"]
    sources += sorted(p for p in PRODUCTION.rglob("*") if p.is_file() and p.suffix in {".py", ".json"})
    for sample in samples:
        sources += sorted(p for p in (ROOT / sample["origin"]).rglob("*") if p.is_file())
    manifest = {
        "stage": 4, "status": "handoff_scenarios_passed_real_trial_pending", "mode": "deterministic_scripts_no_model_calls",
        "scenarios": [f"RA-{i}" for i in range(24, 30)], "samples": samples,
        "files": {str(path.relative_to(ROOT)): _sha(path) for path in sources},
        "artifacts": {str(path.relative_to(output)): _sha(path) for path in sorted(output.rglob("*")) if path.is_file() and path.name not in {".analysis.lock", ".analysis-transaction.json"}},
        "limits": ["合成场景不是用户真实需求", "旧样例是已保存模型结果的消费，未重新运行分析模型", "缺口登记由场景中明确的分析侧补丁完成，不证明模型自主回流", "未验证实际下游Skill集成或安装后的自动调用", "不宣告阶段4整体验收完成"]}
    _save(output / "run-manifest.json", manifest)
    return manifest


def main(argv=None) -> int:
    """解析 argv 的新证据目录，运行并输出简要 JSON；成功返回 0，错误直接抛出。"""
    parser = argparse.ArgumentParser(description="保留阶段4最小消费者场景证据，不调用模型")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = run(args.output)
    print(json.dumps({"status": manifest["status"], "scenarios": manifest["scenarios"], "samples": len(manifest["samples"]), "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

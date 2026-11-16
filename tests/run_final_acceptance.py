"""最终验收重放：已保存合成采购案例贯穿分析、答疑、结束、报告及消费者；不调用模型。"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = ROOT / "workspace-sandbox/stage-4/simulated-trial-01"
PROJECT = "office-procurement"
REQUIREMENT = "SIM-PROCUREMENT-001"
SCRIPTS = ROOT / "skill/requirement-analyst/scripts"


def _sha(path):
    """返回文件path的SHA-256；读取失败直接抛异常。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path, value):
    """在新路径保存JSON，返回空；路径存在或编码错误直接抛出。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def run(output: Path) -> dict:
    """在不存在的output重放五轮既有补丁并返回验收清单。

    仅调整首轮原始文档路径为新项目相对路径，业务内容/回答/清单不变。
    所有答案来自既有模拟剧本，不声称新模型分析或真实业务确认。
    输出存在、子进程失败或业务断言不符时抛异常并保留现场，不覆盖或清理。
    """
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / "workspace"
    project = workspace / "projects" / PROJECT
    inputs = project / "inputs"
    inputs.mkdir(parents=True)
    shutil.copyfile(ROOT / "tests/fixtures/stage-4-procurement-withdrawal.md", inputs / "original-requirement.md")
    requirement = project / "requirements" / REQUIREMENT
    records = []
    origin = json.loads((ORIGIN / "run-manifest.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("final_report_view", ROOT / "tests/render_trial_reports.py")
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    original_fingerprints = {str(p.relative_to(ORIGIN)): _sha(p)
                             for p in ORIGIN.rglob("*") if p.is_file() and not p.name.startswith(".analysis")}

    def cli(name, script, arguments, expected):
        """执行公开脚本并保存真实响应；expected为规格预期，错配立即断言失败。"""
        command = [sys.executable, "-I", "-B", str(script), *map(str, arguments)]
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
        directory = output / "evidence" / name
        result = json.loads(process.stdout)
        # 证据只保留仓库相对命令路径，不存虚拟环境等本机绝对位置。
        display = ["python", *[str(value).replace(str(ROOT) + "/", "") for value in command[1:]]]
        _save(directory / "process.json", {"command": display, "returncode": process.returncode, "stderr": process.stderr})
        _save(directory / "response.json", result)
        records.append({"record": name, "status": result["status"], "action": result.get("action"),
                        "written": result.get("written"), "returncode": process.returncode})
        assert result["status"] == expected, (name, result)
        assert process.returncode == {"pass": 0, "warning": 1, "fail": 2}[expected], (name, process.stderr)
        return result

    def consume(name, expected, *extra):
        """调用最小消费者公开CLI，返回实际响应；不改分析或隐式补全业务。"""
        return cli(name, ROOT / "tools/minimal_prd_consumer.py",
                   ["--workspace", workspace, "--project", PROJECT, "--requirement", REQUIREMENT, *extra], expected)

    first = consume("00-no-analysis", "warning")
    assert first["action"] == "analyze" and first["written"] is False
    for revision, name in enumerate(origin["applications"], 1):
        patch_path = ORIGIN / "evidence" / name / "patch.json"
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
        relocations = []
        for operation in patch["operations"]:
            if operation["op"] == "add_source" and operation["value"].get("type") == "input_document":
                old = operation["value"]["path"]
                operation["value"]["path"] = "inputs/original-requirement.md"
                relocations.append({"from": Path(old).name, "to": operation["value"]["path"]})
        applied = output / "patches" / f"{name}.json"
        _save(applied, patch)
        _save(output / "provenance" / f"{name}.json", {
            "origin": str(patch_path.relative_to(ROOT)), "origin_sha256": _sha(patch_path),
            "applied_sha256": _sha(applied), "relocations_only": relocations,
            "business_content_and_simulated_answers_unchanged": True,
        })
        response = cli(f"{name}-save", SCRIPTS / "update_analysis.py",
                       ["--workspace", workspace, "--project", PROJECT, "--patch", applied], "pass")
        assert response["written"] is True
        analysis_path = requirement / "analysis/analysis-result.json"
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        assert analysis["meta"]["analysis_revision"] == revision
        validation = cli(f"{name}-validate", SCRIPTS / "validate_analysis.py", [analysis_path], "pass")
        report = renderer.render_report(analysis, validation)
        (analysis_path.parent / "analysis-report.md").write_text(report, encoding="utf-8")
        shutil.copytree(requirement, output / "snapshots" / name)
        if revision == 3:
            drafted = consume("midpoint-draft", "warning", "--expected-revision", "3")
            assert drafted["written"] is True and drafted["sync_state"] == "current"

    analysis_directory = requirement / "analysis"
    before = {p.name: _sha(p) for p in analysis_directory.iterdir() if p.is_file()}
    inspection = consume("final-inspect", "warning", "--inspect-only", "--expected-revision", "5")
    assert inspection["sync_state"] == "pending" and inspection["written"] is False
    stale_revision = consume("old-revision-rejected", "fail", "--expected-revision", "3")
    assert stale_revision["written"] is False
    final = consume("final-draft", "warning", "--expected-revision", "5", "--require-section", "requirements.acceptance_criteria")
    assert final["written"] is True and final["sync_state"] == "current"
    # 原轮次补丁原样重试必须revision冲突，不能重复追加事件或改最终状态。
    retry = cli("old-patch-rejected", SCRIPTS / "update_analysis.py",
                ["--workspace", workspace, "--project", PROJECT, "--patch", output / "patches/round-05.json"], "fail")
    assert retry["written"] is False
    after = {p.name: _sha(p) for p in analysis_directory.iterdir() if p.is_file()}
    assert before == after
    analysis = json.loads((analysis_directory / "analysis-result.json").read_text(encoding="utf-8"))
    original_analysis = json.loads((ORIGIN / "workspace/projects" / PROJECT / "requirements" / REQUIREMENT / "analysis/analysis-result.json").read_text(encoding="utf-8"))
    for field in ("requirements", "questions", "assumptions", "decisions", "business_assessment", "completion_checks", "ux_assessment"):
        assert analysis[field] == original_analysis[field], field
    assert analysis["meta"]["analysis_status"] == "completed"
    assert analysis["meta"]["readiness"] == "not_ready"
    blockers = [q["id"] for q in analysis["questions"] if q["priority"] == "P0" and q["status"] == "open"]
    assert blockers == ["Q-12"], blockers
    events = [json.loads(line) for line in (analysis_directory / "analysis-events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [event["revision"] for event in events] == [1, 2, 3, 4, 5]
    record = json.loads((requirement / "requirement.json").read_text(encoding="utf-8"))
    assert record["prd"] == {"based_on_analysis_revision": 5, "status": "draft", "version": 2}
    draft = (requirement / final["draft_path"]).read_text(encoding="utf-8")
    assert "风险" in draft and "Q-12" in draft and "not_ready" in draft
    assert original_fingerprints == {relative: _sha(ORIGIN / relative) for relative in original_fingerprints}
    manifest = {
        "status": "pass", "mode": "deterministic_replay_of_saved_synthetic_analysis",
        "new_model_call": False, "real_business_approval": False,
        "origin": str(ORIGIN.relative_to(ROOT)), "source_relocation_only": True,
        "records": records, "cli_count": len(records),
        "final": {"analysis_revision": 5, "analysis_status": "completed", "readiness": "not_ready",
                  "open_p0": blockers, "prd_version": 2, "based_on_analysis_revision": 5},
        "analysis_before_final_consumer": before, "analysis_after_final_consumer": after,
        "historical_evidence_unchanged": True,
        "source_fingerprints": {str(p.relative_to(ROOT)): _sha(p) for p in
                                [Path(__file__), SCRIPTS / "update_analysis.py", SCRIPTS / "validate_analysis.py",
                                 ROOT / "tools/minimal_prd_consumer.py", ROOT / "tests/render_trial_reports.py",
                                 ROOT / "tests/fixtures/stage-4-procurement-withdrawal.md"]},
        "artifacts": {str(p.relative_to(output)): _sha(p) for p in sorted(output.rglob("*"))
                      if p.is_file() and not p.name.startswith(".analysis")},
    }
    _save(output / "run-manifest.json", manifest)
    return manifest


def main(argv=None) -> int:
    """解析输出目录并运行实际CLI验收，返回0；输入/保存/断言失败直接抛出并保留证据。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.output)
    print(json.dumps({"status": result["status"], "cli_count": result["cli_count"], "final": result["final"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

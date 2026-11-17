"""在新目录保存阶段 1 合成夹具及真实只读 CLI 诊断，不调用模型或发布器。"""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill/prd-generator/scripts/validate_prd.py"


def _support():
    """加载仓库自身测试辅助模块，不从用户工作区导入代码。"""
    spec = importlib.util.spec_from_file_location("prd_fixture_driver_support", ROOT / "tests/prd_fixture_support.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(output: Path) -> dict:
    """在不存在的 output 构造合成输入并执行 CLI，返回证据清单。

    只读校验器不写业务数据；本驱动负责创建夹具和保存 stdout/stderr/指纹。
    output 已存在抛出 FileExistsError；输入不符合预期抛出 AssertionError，文件异常原样抛出。
    """
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    helper = _support()
    results = []
    for rule in range(15):
        label = "valid" if rule == 0 else "snapshot-valid" if rule == 13 else "snapshot-tampered" if rule == 14 else f"rule-{rule:02d}"
        directory = helper.make_workspace(output / label / "requirement")
        trace_path = directory / "prd/prd-trace.json"
        trace = helper.read_json(trace_path)
        text_path = directory / "prd/prd.md"
        text = text_path.read_text()
        if rule == 1:
            trace.pop("items")
        elif rule == 2:
            trace["meta"]["counters"]["FR"] = 0
        elif rule == 3:
            trace["items"][0]["analysis_refs"] = ["SYNTHETIC-PRD/FR-99"]
        elif rule == 4:
            text = text.replace("PRD-FR-001", "PRD-FR-999")
        elif rule == 5:
            trace["items"][0]["tag"] = "inferred"
        elif rule == 6:
            trace["items"][0]["status"] = "abolished"
        elif rule == 7:
            trace["meta"]["draft_kind"] = "risk_draft"
        elif rule == 8:
            analysis_path = directory / "analysis/analysis-result.json"
            analysis = helper.read_json(analysis_path)
            analysis["requirements"]["functional_requirements"][0]["tag"] = "inferred"
            helper.write_json(analysis_path, analysis)
        elif rule == 9:
            text = text.replace("无适用遗留项", helper.block("gap", "GAPREQ-1", "待分析补充"))
        elif rule == 10:
            text = text.replace("| PRD 版本 | 0.1 |", "| PRD 版本 | 0.2 |")
        elif rule == 11:
            versions = directory / "prd/versions"
            versions.mkdir()
            (versions / "prd-1.0.md").write_text("未登记的合成快照，不是真实发布")
        elif rule == 12:
            path = directory / "prd/gap-requests.json"
            gaps = helper.read_json(path)
            gaps["counters"]["GAPREQ"] = 1
            gaps["requests"] = [{"id": "GAPREQ-1", "needed_for": "功能需求", "description": "合成缺口", "related_analysis_refs": [], "raised_in": "0.1", "status": "handed_over"}]
            helper.write_json(path, gaps)
            text = text.replace("无适用遗留项", helper.block("gap", "GAPREQ-1", "待分析补充"))
        if rule in (13, 14):
            # 明确构造合成发布格式，不调用发布器或声称实际产品经理确认。
            metadata = helper.read_json(directory / "requirement.json")
            metadata["prd"].update(version="1.0", status="released")
            helper.write_json(directory / "requirement.json", metadata)
            text = text.removeprefix(helper.PROMPT + "\n\n").replace("| PRD 版本 | 0.1 |", "| PRD 版本 | 1.0 |").replace("| 状态 | draft |", "| 状态 | released |")
        text_path.write_text(text, encoding="utf-8")
        trace["meta"]["content_hash"] = helper.digest(text.encode())
        helper.write_json(trace_path, trace)
        if rule in (13, 14):
            versions = directory / "prd/versions"
            versions.mkdir()
            snapshots = {}
            for kind, source, name in (("prd", text_path, "prd-1.0.md"), ("trace", trace_path, "prd-trace-1.0.json")):
                content = source.read_bytes()
                (versions / name).write_bytes(content)
                snapshots[kind] = {"path": f"versions/{name}", "sha256": helper.digest(content)}
            common = {"time": "2026-11-17T01:00:00Z", "prd_version": "1.0", "summary": "合成发布格式，无真实批准", "affected_prd_ids": ["PRD-FR-001"], "based_on_analysis_revision": 1, "actor": "user"}
            with (directory / "prd/prd-events.jsonl").open("a") as handle:
                handle.write(json.dumps({**common, "change_type": "release_confirmed", "confirmed_by": "synthetic-test-actor-not-real-approval"}, ensure_ascii=False) + "\n")
                handle.write(json.dumps({**common, "change_type": "release", "snapshots": snapshots}, ensure_ascii=False) + "\n")
            if rule == 14:
                path = versions / "prd-1.0.md"
                path.write_bytes(path.read_bytes() + b"synthetic-tamper")
        before = {p.relative_to(directory).as_posix(): helper.digest(p.read_bytes()) for p in directory.rglob("*") if p.is_file()}
        command = [sys.executable, "-I", "-B", str(SCRIPT), str(directory)]
        process = subprocess.run(command, cwd=output, text=True, capture_output=True)
        response = json.loads(process.stdout)
        after = {p.relative_to(directory).as_posix(): helper.digest(p.read_bytes()) for p in directory.rglob("*") if p.is_file()}
        assert before == after, "校验器修改了夹具"
        expected = "pass" if rule in (0, 13) else "fail"
        expected_rule = None if rule in (0, 13) else 11 if rule == 14 else rule
        assert response["status"] == expected, (label, response)
        if expected_rule:
            assert any(d["rule"] == expected_rule and d["level"] == "fail" for d in response["diagnostics"]), (label, response)
        assert process.returncode == (0 if expected == "pass" else 2)
        record = {"label": label, "expected_rule": expected_rule, "expected_status": expected, "command": command, "returncode": process.returncode, "stdout": process.stdout, "stderr": process.stderr, "response": response, "business_hashes_before": before, "business_hashes_after": after, "readonly": True}
        helper.write_json(output / label / "process.json", record)
        results.append({"label": label, "expected_status": expected, "actual_status": response["status"], "expected_rule": expected_rule, "readonly": True, "process": f"{label}/process.json"})
    source_hashes = {p.relative_to(ROOT).as_posix(): helper.digest(p.read_bytes()) for p in sorted((ROOT / "skill/prd-generator").rglob("*")) if p.is_file()}
    manifest = {"executed_at": datetime.now(timezone.utc).isoformat(), "scope": "阶段1合法工作稿及12条规则的合成反例，只证明格式校验，不是模型生成或真实发布", "status": "pass", "cli_calls": len(results), "results": results, "source_hashes": source_hashes, "model_called": False, "release_executed": False, "stage_2_executed": False}
    helper.write_json(output / "run-manifest.json", manifest)
    return manifest


def main(argv=None) -> int:
    """读取 argv 的新输出目录并执行，输出摘要及退出码；参数错误由 argparse 报告。

    输出目录存在时返回 2，不删除或覆盖证据；其他执行异常保留现场并原样抛出。
    """
    parser = argparse.ArgumentParser(description="保存 PRD 阶段1合成格式检查证据；不调用模型")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run(args.output)
    except FileExistsError:
        print(json.dumps({"status": "fail", "message": "输出目录已存在，拒绝覆盖"}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": result["status"], "cli_calls": result["cli_calls"], "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

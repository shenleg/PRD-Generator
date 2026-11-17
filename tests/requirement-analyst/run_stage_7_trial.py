"""阶段7合成截图试用：将实际只读模型输出机械映射为可追溯补丁并运行真实CLI，不调用模型。"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/stage-7"
SCRIPTS = ROOT / "skill/requirement-analyst/scripts"
UX_FIELDS = ("ui_dependent", "design_pending_items", "visual_recommendations", "interaction_flows")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def make_patch(case: dict, assessment: dict) -> dict:
    """将指定case的实际assessment映射为首次补丁，保留模型四字段、观察和问题原文。

    新来源/条目使用别名；观察事实及页面候选写入现有可追溯条目，业务骨架和清单由
    合成驱动器提供，不声称完整需求由模型自主分析。跨case引用或非法来源抛ValueError。
    """
    materials = {"cases.json": "$input", **{name: "$material" + str(i) for i, name in enumerate(case["materials"], 1)}}
    operations = []
    for name, alias in materials.items():
        operations.append({"op": "add_source", "ref": alias, "value": {"name": name + "（阶段7合成资料）", "path": "inputs/" + name, "type": "input_document", "credibility": "用户批准的合成需求/静态低保真参考，非真实系统或实际点击验证", "last_updated": None, "revision": 1, "adopted_sha256": _sha(FIXTURES / name)}})

    def item(collection, alias, content, name="cases.json", location=None, tag="inferred"):
        """追加有来源的条目操作，不改content；name/location仅作已提供资料定位，返回空。"""
        if name not in materials:
            raise ValueError("引用本case未提供的资料：" + name)
        operations.append({"op": "add", "collection": collection, "ref": alias, "value": {"content": content, "tag": tag, "status": "active", "sources": [{"type": "input_document", "source_id": materials[name], "location": location or "cases.json：" + case["id"]}], "related_ids": []}})

    item("requirements.goals", "$goal", "合成体验能力验证：按本例实际资料范围分析，不把设计建议当既有界面")
    item("requirements.functional_requirements", "$function", case["requirement"], tag="confirmed")
    for i, observation in enumerate(assessment["observations"], 1):
        if observation["material"] != "reference-list.png":
            raise ValueError("截图观察必须以实际图片为证据，不能用文字说明代替看图")
        item("business_assessment.boundaries", f"$observation{i}", observation["content"], observation["material"], observation["location"], observation["tag"])
    for i, page in enumerate(assessment["page_list"], 1):
        if page["origin"] == "observed" and page["material"] != "reference-list.png":
            raise ValueError("已观察页面须有本例截图")
        item("requirements.scenarios", f"$page{i}", page["content"], page["material"], page["location"], "confirmed" if page["origin"] == "observed" else "inferred")
    core, noncore = [], []
    for i, question in enumerate(assessment["questions"], 1):
        alias = f"$question{i}"
        operations.append({"op": "add", "collection": "questions", "ref": alias, "value": {**question, "status": "open", "related_ids": ["$function"]}})
        if question["priority"] == "P0":
            core.append(alias)
        elif question["resolution"] != "ask_dev":
            noncore.append(alias)
    readiness = "not_ready" if core else "conditionally_ready" if noncore else "ready_for_document"
    checks = []
    for i in range(1, 12):
        missing = core if i in (4, 7) else noncore if i == 11 else []
        checks.append({"item": i, "satisfied": not missing, "question_refs": missing, "reason": "实际模型登记的核心规则/设计待决事项未答，保留缺口" if missing else "合成驱动器限定体验验证范围，非完整真实需求业务充分性验收"})
    return {"patch_version": "1.0", "requirement_id": case["id"], "title": case["id"] + "（合成体验分析）", "base_revision": 0, "change_type": "initial_analysis", "actor": "analyst", "summary": "实际模型体验输出机械映射，保留来源、截图事实和设计建议，未提供模拟产品答案", "operations": operations,
            "set": {"meta.input_type": "existing_document", "meta.analysis_status": "clarifying" if core or noncore else "completed", "meta.readiness": readiness, "context.source_ids": list(materials.values()), **{"ux_assessment." + name: assessment[name] for name in UX_FIELDS}}, "completion_checks": checks}


def run(output: Path, model_evidence: Path) -> dict:
    """向全新output重放已保存model_evidence，返回实际保存/校验/消费与文件指纹清单。

    不调用模型或浏览器；output重复时拒绝覆盖。模型结果不符合来源约束、CLI状态不符、
    文件/JSON或超时错误直接抛出并保留现场，不修问题来凑通过。
    """
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    cases = _load(FIXTURES / "cases.json")["cases"]
    model = _load(model_evidence)
    assessments = {a["case_id"]: a for a in model["structured_output"]["assessments"]}
    assert set(assessments) == {c["id"] for c in cases}
    workspace = output / "workspace"
    project = workspace / "projects/ux-demo"
    inputs = project / "inputs"
    inputs.mkdir(parents=True)
    for name in ("cases.json", "reference-list.png", "reference-note.md"):
        shutil.copyfile(FIXTURES / name, inputs / name)
    records, results = [], []

    def cli(record, script, args, expected):
        """真实执行script并保留响应，expected仅用于判分；错码或坏输出断言失败而不覆盖。"""
        command = [sys.executable, "-I", "-B", str(script), *map(str, args)]
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        evidence = output / "evidence" / record
        evidence.mkdir(parents=True, exist_ok=False)
        _save(evidence / "process.json", {"command": command, "returncode": process.returncode, "stderr": process.stderr})
        with (evidence / "stdout.txt").open("x", encoding="utf-8") as stream:
            stream.write(process.stdout)
        response = json.loads(process.stdout)
        _save(evidence / "response.json", response)
        assert (process.returncode, response["status"]) == ({"pass": 0, "warning": 1, "fail": 2}[expected], expected), (record, response)
        records.append({"record": record, "script": script.name, "status": response["status"]})
        return response

    spec = importlib.util.spec_from_file_location("ux_report_renderer", ROOT / "tests/requirement-analyst/render_trial_reports.py")
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    for case in cases:
        patch = make_patch(case, assessments[case["id"]])
        patch_path = output / "patches" / (case["id"] + ".json")
        _save(patch_path, patch)
        response = cli(case["id"] + "-save", SCRIPTS / "update_analysis.py", ["--workspace", workspace, "--project", "ux-demo", "--patch", patch_path], "pass")
        directory = project / "requirements" / case["id"]
        path = directory / "analysis/analysis-result.json"
        validation = cli(case["id"] + "-validate", SCRIPTS / "validate_analysis.py", [path], "pass")
        analysis = _load(path)
        with path.with_name("analysis-report.md").open("x", encoding="utf-8") as stream:
            stream.write(report.render_report(analysis, validation))
        before = {p.name: _sha(p) for p in path.parent.iterdir() if p.is_file()}
        expected = "pass" if analysis["meta"]["readiness"] == "ready_for_document" else "warning"
        draft = cli(case["id"] + "-consume", ROOT / "tools/minimal_prd_consumer.py", ["--workspace", workspace, "--project", "ux-demo", "--requirement", case["id"], "--expected-revision", response["revision"]], expected)
        assert draft["written"]
        assert before == {p.name: _sha(p) for p in path.parent.iterdir() if p.is_file()}
        shutil.copytree(directory, output / "evidence" / (case["id"] + "-save") / "requirement")
        results.append({"id": case["id"], "ui_dependent": analysis["ux_assessment"]["ui_dependent"], "readiness": analysis["meta"]["readiness"], "draft": draft["draft_path"], "analysis_before_consumer": before})
    files = [p for p in SCRIPTS.parent.rglob("*") if p.is_file() and p.suffix in {".md", ".py", ".json", ".txt"}]
    files += [ROOT / "tools/minimal_prd_consumer.py", ROOT / "tests/requirement-analyst/render_trial_reports.py", Path(__file__)]
    manifest = {"stage": 7, "mode": "actual_multimodal_model_output_mechanically_mapped_to_cli", "model_evidence": str(Path(model_evidence).relative_to(ROOT)), "model_evidence_sha256": _sha(model_evidence), "records": records, "results": results,
                "files": {str(p.relative_to(ROOT)): _sha(p) for p in files},
                "artifacts": {str(p.relative_to(output)): _sha(p) for p in sorted(output.rglob("*")) if p.is_file() and p.name not in {".analysis.lock", ".analysis-transaction.json"}},
                "limits": ["原文和静态页面为用户批准的合成资料，不是真实系统或用户研究", "六case共享一次独立只读模型调用，不是六次隔离盲测", "模型实际读取PNG图像，未读HTML源码，未验证点击或后台行为", "四个体验字段/观察/问题为模型实际输出，业务骨架/清单及readiness为驱动器提供，不等于完整业务自主分析", "本驱动器只重放已保存输出，不调用模型或浏览器"]}
    _save(output / "run-manifest.json", manifest)
    return manifest


def main(argv=None) -> int:
    """解析全新output和已保存model-evidence，实际重放后返回0；异常直接抛出并留现场。"""
    parser = argparse.ArgumentParser(description="阶段7已保存图像评估的真实CLI重放，不调用模型")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.output, args.model_evidence.absolute())
    print(json.dumps({"status": "pass", "cases": len(result["results"]), "cli_records": len(result["records"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""阶段6试用：只将已保存的真实模型评估机械映射为补丁，调用实际CLI留证，不重新调用模型。"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/stage-6"
SCRIPTS = ROOT / "skill/requirement-analyst/scripts"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def make_patch(case: dict, assessment: dict, project: Path) -> dict:
    """将case输入和模型assessment机械转换为首次补丁，不改结论、证据正文或问题优先级。

    project用于读取该case指定的资料指纹；返回未分号的补丁。业务条目及清单由合成
    驱动器提供，不声称是独立模型端到端完整需求分析；输入不符或文件错误直接抛出。
    """
    operations = [{"op": "add_source", "ref": "$input", "value": {"name": "阶段6合成需求用例", "path": "inputs/cases.json", "type": "input_document", "credibility": "用户批准的合成技术评估输入，非真实产品需求", "last_updated": None, "revision": 1}}]
    refs = {}
    for index, name in enumerate(case["materials"], 1):
        alias = f"$material{index}"
        refs[name] = alias
        old = name == "old-platform-draft.md"
        value = {"name": name + "（合成技术资料）", "path": "materials/" + name, "type": "project_material", "credibility": "合成场景中的当前技术负责人声明；不是真实系统核验" if not old else "合成历史草稿，现行性未确认", "last_updated": "2020-01-01" if old else "2026-11-01", "revision": 1, "authority": "draft" if old else "current_spec", "adopted_sha256": _sha(project / "materials" / name)}
        if not old:
            value["publication_basis"] = "原合成资料声明于2026-11-01由技术负责人确认，相对参考日2026-11-16有效"
        operations.append({"op": "add_source", "ref": alias, "value": value})
    source = [{"type": "input_document", "source_id": "$input", "location": "cases.json案例" + case["id"]}]
    for collection, alias, content in (("requirements.goals", "$goal", "合成业务目标：核对本需求技术路径及研发前提，不把技术评估当上线承诺"),
                                       ("requirements.functional_requirements", "$function", case["requirement"]),
                                       ("requirements.acceptance_criteria", "$acceptance", "合成评估验收：结论严格限定为原需求范围，逐项核对可用资料与待确认条件；业务遗留问题必须保留，不以技术结论替代产品决定")):
        operations.append({"op": "add", "collection": collection, "ref": alias, "value": {"content": content, "tag": "confirmed" if alias != "$acceptance" else "inferred", "status": "active", "sources": source, "related_ids": ["$function"] if alias == "$acceptance" else []}})
    dev_refs, core, noncore = [], [], []
    for role, questions in (("ask_dev", assessment["dev_questions"]), ("ask_product", assessment["product_questions"])):
        for index, question in enumerate(questions, 1):
            alias = f"${role}{index}"
            priority = question.get("priority", "P1")
            value = {"question": question["question"], "priority": priority, "resolution": role, "reason": question["reason"], "impact": question["impact"], "options": question.get("options", []), "recommendation": question.get("recommendation", "由研发依据当前系统资料或实测核实，不要求产品承诺技术实现"), "status": "open", "related_ids": ["$function"]}
            operations.append({"op": "add", "collection": "questions", "ref": alias, "value": value})
            if role == "ask_dev":
                dev_refs.append(alias)
            elif priority == "P0":
                core.append(alias)
            else:
                noncore.append(alias)
    evidence = []
    for value in assessment["evidence"]:
        if value["material"] not in refs:
            raise ValueError("模型引用了本case未提供的资料，不允许借其他case补证据")
        evidence.append({"content": value["content"], "sources": [{"type": "project_material", "source_id": refs[value["material"]], "location": value["location"]}]})
    technical = {"conclusion": assessment["conclusion"], "evidence": evidence, "credibility": assessment["credibility"], "potential_impact": assessment["potential_impact"], "related_questions": dev_refs, "risks": assessment["risks"]}
    checks = []
    for i in range(1, 12):
        missing = core if i in (4, 7) else noncore if i == 11 else []
        checks.append({"item": i, "satisfied": not missing, "question_refs": missing,
                       "reason": "模型保留的产品取舍未答，不能由技术判断关闭" if missing else "本合成技术评估场景的固定输入与范围已声明；不是完整真实需求业务充分性验收"})
    readiness = "not_ready" if core else "conditionally_ready" if noncore else "ready_for_document"
    return {"patch_version": "1.0", "requirement_id": case["id"], "title": case["id"] + "（阶段6合成技术评估）", "base_revision": 0, "change_type": "initial_analysis", "actor": "analyst", "summary": "将实际只读模型的技术评估原样映射，编号/合法性/保存由更新器执行；业务骨架为合成驱动器提供", "operations": operations,
            "set": {"meta.input_type": "existing_document", "meta.analysis_status": "clarifying" if core or noncore else "completed", "meta.readiness": readiness, "ux_assessment.ui_dependent": False, "context.history_review": {"status": "reviewed" if refs else "not_performed", "reason": "仅采用该case明确指定的合成技术资料，非项目全量历史业务对照" if refs else "该case没有技术资料，不借其他case补证据", "source_ids": list(refs.values())}, "technical_feasibility": technical}, "completion_checks": checks}


def run(output: Path, model_evidence: Path) -> dict:
    """向全新output重放已保存model_evidence的八份评估，返回CLI及来源指纹清单。

    不调用模型。model_evidence须为已记录结构化实际评估；重复目录拒绝覆盖。文件、
    JSON、响应不符和超时直接抛出并保留现场，不修业务结论来凑pass。
    """
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    cases = _load(FIXTURES / "cases.json")["cases"]
    model = _load(model_evidence)
    assessments = {a["case_id"]: a for a in model["structured_output"]["assessments"]}
    assert len(assessments) == len(cases) == 8
    workspace = output / "workspace"
    project = workspace / "projects/feasibility-demo"
    (project / "materials").mkdir(parents=True)
    (project / "inputs").mkdir()
    shutil.copyfile(FIXTURES / "cases.json", project / "inputs/cases.json")
    for material in FIXTURES.glob("*.md"):
        shutil.copyfile(material, project / "materials" / material.name)
    records = []

    def cli(record, script, args, expected):
        """调用实际script，记录进程状态和响应；expected不匹配保留现场并断言失败。"""
        command = [sys.executable, "-I", "-B", str(script), *map(str, args)]
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        directory = output / "evidence" / record
        directory.mkdir(parents=True, exist_ok=False)
        _save(directory / "process.json", {"command": command, "returncode": process.returncode, "stderr": process.stderr})
        with (directory / "stdout.txt").open("x", encoding="utf-8") as stream:
            stream.write(process.stdout)
        response = json.loads(process.stdout)
        _save(directory / "response.json", response)
        assert response["status"] == expected, (record, response)
        assert process.returncode == {"pass": 0, "warning": 1, "fail": 2}[expected], (record, process.stderr)
        records.append({"record": record, "status": expected, "script": script.name})
        return response

    spec = importlib.util.spec_from_file_location("technical_trial_report", ROOT / "tests/render_trial_reports.py")
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    results = []
    for case in cases:
        assessment = assessments[case["id"]]
        patch = make_patch(case, assessment, project)
        patch_path = output / "patches" / (case["id"] + ".json")
        _save(patch_path, patch)
        saved = cli(case["id"] + "-save", SCRIPTS / "update_analysis.py", ["--workspace", workspace, "--project", "feasibility-demo", "--patch", patch_path], "pass")
        directory = project / "requirements" / case["id"]
        analysis_path = directory / "analysis/analysis-result.json"
        validation = cli(case["id"] + "-validate", SCRIPTS / "validate_analysis.py", [analysis_path], "pass")
        analysis = _load(analysis_path)
        with analysis_path.with_name("analysis-report.md").open("x", encoding="utf-8") as stream:
            stream.write(report.render_report(analysis, validation))
        before = {p.name: _sha(p) for p in analysis_path.parent.iterdir() if p.is_file()}
        expected = "pass" if analysis["meta"]["readiness"] == "ready_for_document" else "warning"
        draft = cli(case["id"] + "-consume", ROOT / "tools/minimal_prd_consumer.py", ["--workspace", workspace, "--project", "feasibility-demo", "--requirement", case["id"], "--expected-revision", saved["revision"]], expected)
        assert draft["written"]
        assert before == {p.name: _sha(p) for p in analysis_path.parent.iterdir() if p.is_file()}
        shutil.copytree(directory, output / "evidence" / (case["id"] + "-save") / "requirement")
        results.append({"id": case["id"], "conclusion": analysis["technical_feasibility"]["conclusion"], "readiness": analysis["meta"]["readiness"], "before_consumer": before, "draft": draft["draft_path"]})
    manifest = {"stage": 6, "mode": "actual_read_only_model_assessment_mechanically_mapped_to_cli_patches", "not_real_technical_system": True,
                "model_evidence": str(Path(model_evidence).relative_to(ROOT)) if Path(model_evidence).is_relative_to(ROOT) else str(model_evidence), "model_evidence_sha256": _sha(model_evidence),
                "results": results, "records": records,
                "files": {str(p.relative_to(ROOT)): _sha(p) for p in [*(SCRIPTS.parent.rglob("*.md")), *(SCRIPTS.glob("*.py")), *(SCRIPTS.parent.rglob("*.json")), ROOT / "tools/minimal_prd_consumer.py", ROOT / "tests/render_trial_reports.py", Path(__file__)] if p.is_file()},
                "artifacts": {str(p.relative_to(output)): _sha(p) for p in sorted(output.rglob("*")) if p.is_file() and p.name not in {".analysis.lock", ".analysis-transaction.json"}},
                "limits": ["八case共用一次独立CLI只读模型调用，不是八次隔离盲测", "技术结论、证据正文及问题由模型实际生成；业务条目/清单/就绪度由驱动器机械提供，不是完整需求自主分析", "资料及技术负责人有效性声明均为合成，不证明真实系统能力", "规则9只校验声明结构，不验证证据语义，主会话另对原文核对", "消费者草稿不是研发验证或产品批准发布"]}
    _save(output / "run-manifest.json", manifest)
    return manifest


def main(argv=None) -> int:
    """解析全新output及已保存模型证据路径，执行重放并返回0；输入/运行错误直接抛出。"""
    parser = argparse.ArgumentParser(description="阶段6已保存模型评估的真实CLI保存与交接，不调用模型")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.output, args.model_evidence.absolute())
    print(json.dumps({"status": "pass", "cases": len(result["results"]), "cli_records": len(result["records"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

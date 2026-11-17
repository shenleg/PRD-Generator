"""阶段5合成场景驱动：主会话编写语义补丁、真实CLI执行，保留资料、差异与事件，不调用模型。"""

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skill/requirement-analyst/scripts"
FIXTURES = ROOT / "tests/fixtures/requirement-analyst/stage-5"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _checks(missing=()):
    return [{"item": i, "satisfied": i not in missing, "question_refs": ["$question"] if i in missing else [],
             "reason": "合成场景核心取舍未确定，保留问题" if i in missing else "合成资料足以表达该项；历史范围和技术未知另有声明"} for i in range(1, 12)]


def _item(content, source="$source", *, related=(), tag="confirmed", status="active"):
    return {"content": content, "tag": tag, "status": status,
            "sources": [{"type": "input_document" if source == "$input" else "project_material", "source_id": source, "location": "合成输入/历史资料业务条款"}], "related_ids": list(related)}


def _source(path, source_id=None, *, revision=1, authority="current_published", updated="2026-11-01", project=None):
    value = {"name": path.name + "（合成资料）", "path": str(path.relative_to(project)), "type": "project_material",
             "credibility": "用户批准的合成场景声明，不是真实项目发布", "last_updated": updated, "revision": revision,
             "authority": authority, "adopted_sha256": _sha(path)}
    if authority == "current_published":
        value["publication_basis"] = "合成场景产品负责人确认本版本为当前发布依据，原文件有明确声明"
    if source_id:
        value["source_id"] = source_id
    return value


def _question(text, refs, *, priority="P0", options=None, recommendation=None):
    return {"question": text, "priority": priority, "resolution": "ask_product", "reason": "合成新提议与显式历史资料对照后存在待决事项",
            "impact": "无法确认是否变更或重复建设及相应验收", "options": options or ["沿用当前规则", "提出差异并确认变更", "其他", "暂不确定"],
            "recommendation": recommendation or "未明确批准前建议保留既有规则；推荐不表示产品已采用。", "status": "open", "related_ids": refs}


def run(output: Path) -> dict:
    """向全新output运行RA14～19合成接口链路，返回带实际产物指纹的清单。

    output已存在时拒绝覆盖，失败立即保留现场。语义补丁由主会话按用户授权编写，
    不假称驱动器有通用语义能力或独立模型已完成端到端保存；CLI返回与断言错误直接传播。
    """
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / "workspace"
    project = workspace / "projects/stage5-demo"
    (project / "history").mkdir(parents=True)
    (project / "inputs").mkdir()
    (project / "versions").mkdir()
    for source in (FIXTURES / "history").glob("*.md"):
        shutil.copyfile(source, project / "history" / source.name)
    for name in ("new-batch-delete.md", "new-user-filter.md"):
        shutil.copyfile(FIXTURES / name, project / "inputs" / name)
    shutil.copyfile(project / "history/current-user-deletion.md", project / "versions/user-deletion-v1.md")
    records = []

    def cli(name, script, args, expected):
        """运行真实script，保留命令/响应；expected是规格要求的状态，错误停止并保留现场。"""
        command = [sys.executable, "-I", "-B", str(SCRIPTS / script), *map(str, args)]
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        record = output / "evidence" / name
        record.mkdir(parents=True, exist_ok=False)
        _save(record / "process.json", {"command": command, "returncode": process.returncode, "stderr": process.stderr})
        with (record / "stdout.txt").open("x", encoding="utf-8") as stream:
            stream.write(process.stdout)
        result = json.loads(process.stdout)
        _save(record / "response.json", result)
        records.append({"record": name, "script": script, "status": result["status"]})
        assert result["status"] == expected, (name, result)
        assert process.returncode == {"pass": 0, "warning": 1, "fail": 2}[expected], (name, process.stderr)
        return result

    def apply(name, patch, expected="pass"):
        """原样保存主会话编写的patch，实际提交更新器并快照本次需求，不修改基线快照。"""
        path = output / "patches" / f"{name}.json"
        _save(path, patch)
        result = cli(name, "update_analysis.py", ["--workspace", workspace, "--project", "stage5-demo", "--patch", path], expected)
        directory = project / "requirements" / patch["requirement_id"]
        if directory.exists():
            shutil.copytree(directory, output / "evidence" / name / "requirement")
        return result

    def blank(requirement, title):
        """返回主会话场景首次补丁骨架；仅合成输入，返回新对象，无文件操作。"""
        return {"patch_version": "1.0", "requirement_id": requirement, "title": title + "（合成）", "base_revision": 0,
                "change_type": "initial_analysis", "actor": "analyst", "summary": "合成历史对照场景，不是真实产品决定",
                "operations": [], "set": {"meta.input_type": "existing_document", "meta.analysis_status": "clarifying", "meta.readiness": "not_ready", "ux_assessment.ui_dependent": False}, "completion_checks": _checks()}

    # 先通过真实更新器建立场景中的发布分析。发布权威来自合成输入声明，不从draft或标题推断。
    baseline = blank("HIST-USER-001", "当前用户删除基线")
    live = project / "history/current-user-deletion.md"
    source_value = _source(live, project=project)
    source_value["archived_path"] = "versions/user-deletion-v1.md"
    baseline["operations"] = [
        {"op": "add_source", "ref": "$source", "value": source_value},
        {"op": "add", "collection": "requirements.goals", "ref": "$goal", "value": _item("管理员能安全删除合法的用户，不破坏未完成任务")},
        {"op": "add", "collection": "requirements.functional_requirements", "ref": "$function", "value": _item("管理员通过现有单用户删除入口操作，服务端校验权限", related=["$goal"])},
        {"op": "add", "collection": "requirements.business_rules", "ref": "$rule", "value": _item("存在未完成任务时禁止删除用户，拒绝且用户与任务不变", related=["$function"])},
        {"op": "add", "collection": "requirements.acceptance_criteria", "ref": "$acceptance", "value": _item("管理员删除有未完成任务用户，应拒绝且用户及任务数据不变", related=["$rule"])},
        {"op": "add", "collection": "questions", "ref": "$oldquestion", "value": {**_question("当前未完成任务保护是否覆盖所有删除入口？", ["$rule"]), "status": "answered", "answer": "第一版合成发布规则：有未完成任务一律拒绝，不区分入口", "reason": "原合成基线已确认"}},
    ]
    baseline.update(actor="user", user_statement="合成场景产品负责人确认：HIST-USER-001分析修订1为当前发布分析基线，未批准改变禁止删除规则。")
    baseline["set"].update({"meta.analysis_status": "completed", "meta.readiness": "ready_for_document", "meta.baseline_revision": 1,
                            "context.history_review": {"status": "reviewed", "reason": "显式合成发布依据；并未检索整个项目", "source_ids": ["$source"],
                                "baseline": {"requirement_id": "HIST-USER-001", "analysis_revision": 1, "source_id": "$source", "publication_basis": baseline["user_statement"]}}})
    apply("baseline-v1", baseline)
    baseline_path = output / "evidence/baseline-v1/requirement/analysis/analysis-result.json"
    baseline_bytes = baseline_path.read_bytes()

    # RA14：主会话依据原文写出冲突，并保留问题，未模拟产品批准改变历史。
    conflict = blank("NEW-DELETE-001", "批量删除用户")
    conflict["operations"] = [
        {"op": "add_source", "ref": "$history", "value": _source(live, project=project)},
        {"op": "add_source", "ref": "$input", "value": {"name": "合成批量删除提议", "path": "inputs/new-batch-delete.md", "type": "input_document", "credibility": "助手构造的用户批准测试输入", "last_updated": None, "revision": 1}},
        {"op": "add", "collection": "requirements.goals", "ref": "$goal", "value": _item("减少管理员逐个删除测试用户的操作", "$input")},
        {"op": "add", "collection": "requirements.functional_requirements", "ref": "$function", "value": _item("提议管理员批量删除选中用户，即使其存在未完成任务，任务不得丢失；不是批准后的现行规则", "$input", related=["$goal"])},
        {"op": "add", "collection": "requirements.business_rules", "ref": "$current", "value": _item("指定合成当前发布规则：有未完成任务时禁止删除用户，用户和任务数据不变", "$history")},
        {"op": "add", "collection": "questions", "ref": "$question", "value": _question("新提议与当前禁止删除规则冲突，本期是否变更该规则？", ["$function", "$current"])},
        {"op": "add", "collection": "business_assessment.conflicts", "ref": "$conflict", "value": {**_item("新提议允许删除有未完成任务用户，与当前发布规则的禁止删除及用户不变预期互斥；任务归属也未明确", "$history", related=["$function", "$current"], tag="inferred"), "related_question": "$question"}},
        {"op": "add", "collection": "questions", "ref": "$tasks", "value": _question("若确认允许删除，未完成任务之后归谁负责？", ["$function"])},
    ]
    conflict["completion_checks"] = _checks((3, 4, 5, 6, 7))
    conflict["set"]["context.history_review"] = {"status": "reviewed", "reason": "仅对照明确指定的用户删除历史规则，当前提议存在业务冲突；未获改变基线批准", "source_ids": ["$history"]}
    conflict["set"]["impact_analysis.affected_requirements"] = ["HIST-USER-001/BR-1", "HIST-USER-001/AC-1"]
    conflict["set"]["impact_analysis.proposed_changes"] = ["modify（待批准）：如产品批准放宽禁止规则，须重评单用户及批量删除与任务责任归属；当前只保留建议"]
    # 跨需求必须显式提供目标分析，未扫描工作区。
    path = output / "patches/conflict.json"
    _save(path, conflict)
    cli("RA-14-conflict", "update_analysis.py", ["--workspace", workspace, "--project", "stage5-demo", "--patch", path, "--related-analysis", baseline_path], "pass")
    shutil.copytree(project / "requirements/NEW-DELETE-001", output / "evidence/RA-14-conflict/requirement")

    duplicate = blank("NEW-FILTER-001", "用户筛选重复提议")
    duplicate["set"]["ux_assessment.ui_dependent"] = True
    filter_doc = project / "history/current-user-filter.md"
    duplicate["operations"] = [
        {"op": "add_source", "ref": "$history", "value": _source(filter_doc, project=project)},
        {"op": "add_source", "ref": "$input", "value": {"name": "合成筛选提议", "path": "inputs/new-user-filter.md", "type": "input_document", "credibility": "合成输入", "last_updated": None, "revision": 1}},
        {"op": "add", "collection": "requirements.goals", "ref": "$goal", "value": _item("帮助管理员查找用户", "$input")},
        {"op": "add", "collection": "requirements.functional_requirements", "ref": "$function", "value": _item("提议用户列表按状态、创建时间区间组合筛选，与指定历史功能重合", "$input", tag="confirmed")},
        {"op": "add", "collection": "business_assessment.gaps", "ref": "$gap", "value": _item("已有功能覆盖所提角色、字段及组合范围；没有新差异或缺陷资料，是否重复建设需产品取舍", "$history", related=["$function"], tag="inferred")},
        {"op": "add", "collection": "questions", "ref": "$question", "value": _question("历史已有相同筛选能力，本次复用、补充差异还是按缺陷修复？", ["$function", "$gap"], options=["复用已有功能，不新增重复入口", "补充现有功能未覆盖差异", "提供缺陷复现与预期", "其他", "暂不确定"], recommendation="建议先复用现有功能，避免重复建设；未获确认前不擅自合并或排除。")},
    ]
    duplicate["set"]["context.history_review"] = {"status": "reviewed", "reason": "仅对照用户指定筛选历史资料，发现角色/字段/组合规则重合，尚未做产品取舍", "source_ids": ["$history"]}
    duplicate["completion_checks"] = _checks((3, 4, 7))
    apply("RA-15-duplicate", duplicate)

    # RA16：已明确的同需求变更建议只在当前工作副本保存，已发布快照绝不覆盖。
    proposal = {"patch_version": "1.0", "requirement_id": "HIST-USER-001", "base_revision": 1, "change_type": "supplement", "actor": "user",
                "user_statement": "合成产品确认只研究新增批量入口，仍沿用未完成任务禁止删除规则；这不是更新发布基线。", "summary": "合成同需求变更影响演示",
                "operations": [{"op": "update", "target": "FR-1", "changes": {"content": "管理员通过单用户或拟增加的批量入口删除用户，服务端仍校验管理员权限", "sources": [{"type": "user_answer", "location": "合成场景明确变更提议"}]}}],
                "set": {}, "completion_checks": _checks()}
    apply("RA-16-proposal", proposal)
    working = project / "requirements/HIST-USER-001/analysis/analysis-result.json"
    result = cli("RA-16-impact", "compare_baseline.py", ["--baseline", baseline_path, "--proposal", working], "pass")
    assert result["impact"]["direct"] == ["HIST-USER-001/BR-1"], result
    assert result["impact"]["indirect"] == ["HIST-USER-001/AC-1", "HIST-USER-001/Q-1"], result

    catalog = [_source(project / "history/current-user-deletion.md", "SRC-1", project=project),
               _source(project / "history/current-user-filter.md", "SRC-2", project=project),
               _source(project / "history/legacy-architecture.md", "SRC-3", project=project, authority="draft", updated="2020-01-01")]
    # catalog是待索引元数据，不是已采用证据；采用指纹由分析侧保存，索引自身重新计算sha256。
    for item in catalog:
        item.pop("adopted_sha256")
        item.update(module="用户管理", tags=["删除" if "deletion" in item["path"] else "筛选"], terms=["用户"])
    catalog_path = output / "catalog.json"
    _save(catalog_path, catalog)
    cli("index-v1", "index_sources.py", ["--project-root", project, "--catalog", catalog_path], "pass")
    cli("search-current", "search_project.py", ["--project-root", project, "--query", "未完成任务", "--tag", "删除", "--as-of", "2026-11-16"], "pass")
    old = cli("RA-18-old-material", "search_project.py", ["--project-root", project, "--query", "删除", "--as-of", "2026-11-16", "--max-age-days", "365"], "warning")
    assert any("过期" in d["message"] for d in old["diagnostics"]), old

    # RA17：原采用指纹不变时检查通过；资料原地换版本后索引及采用检查均发现变化。
    cli("RA-17-before", "compare_baseline.py", ["--check-sources", working, "--project-root", project], "pass")
    live.write_bytes((project / "history/user-deletion-v2.md").read_bytes())
    changed = cli("RA-17-detected", "compare_baseline.py", ["--check-sources", working, "--project-root", project], "warning")
    assert changed["needs_reassessment"]
    search = cli("RA-17-old-index", "search_project.py", ["--project-root", project, "--query", "未完成任务", "--tag", "删除", "--as-of", "2026-11-16"], "warning")
    assert search["stale_sources"] and not search["results"], search
    _save(output / "catalog-v2.json", [{**item, "revision": 2} if item["source_id"] == "SRC-1" else item for item in catalog])
    cli("index-v2", "index_sources.py", ["--project-root", project, "--catalog", output / "catalog-v2.json"], "pass")
    cli("search-refreshed", "search_project.py", ["--project-root", project, "--query", "冻结", "--tag", "删除", "--as-of", "2026-11-16"], "pass")
    source2 = _source(live, project=project, revision=2)
    review = {"status": "stale", "reason": "采用的合成发布资料内容已变化，新增冻结规则，先标记过期再重评；旧发布分析快照仍只读", "source_ids": ["$newsource"],
              "baseline": {"requirement_id": "HIST-USER-001", "analysis_revision": 1, "source_id": "SRC-1", "publication_basis": baseline["user_statement"]}}
    # 老发布分析仍是产品确认的分析基线，必须同时保留其来源；新资料不是自动发布分析修订2。
    review["source_ids"].insert(0, "SRC-1")
    # 旧采用来源仍指原地路径，重评后将其作为历史追溯，而当前采用改为新SRC。
    stale = {"patch_version": "1.0", "requirement_id": "HIST-USER-001", "base_revision": 2, "change_type": "new_source_version", "actor": "user",
             "user_statement": "合成场景收到正式用户删除规则第二版，新增审计冻结禁止删除；尚未完成分析重评，不自动改发布分析基线。", "summary": "资料变化先保存stale",
             "operations": [{"op": "add_source", "ref": "$newsource", "value": source2}, {"op": "update", "target": "BR-1", "changes": {"status": "to_reassess"}}, {"op": "update", "target": "AC-1", "changes": {"status": "to_reassess"}},
                            {"op": "update", "target": "Q-1", "changes": {"status": "open", "reason": "合成发布资料第二版新增冻结状态，原已答入口保护问题须重开复核，保留第一版answer"}},
                            {"op": "add", "collection": "questions", "ref": "$question", "value": _question("新冻结规则对单用户与批量删除的判断及验收是否均已重评？", ["BR-1", "AC-1"]) }],
             "set": {"context.history_review": review, "meta.analysis_status": "stale", "meta.readiness": "not_ready"}, "completion_checks": _checks((4, 6, 7))}
    apply("RA-17-stale", stale, "warning")
    review_final = deepcopy(review)
    review_final.update(status="reviewed", reason="已逐项重评新增冻结限制及原未完成任务限制，旧发布分析修订1仍保留，当前采用新资料不等于重发分析基线", source_ids=["SRC-1", "SRC-2"])
    final = {"patch_version": "1.0", "requirement_id": "HIST-USER-001", "base_revision": 3, "change_type": "supplement", "actor": "user",
             "user_statement": "合成产品确认：单用户和批量入口均沿用未完成任务保护，审计冻结用户也一律拒绝且数据不变；该重评不重新发布历史分析。", "summary": "完成冻结状态变更的直接与间接重评",
             "operations": [{"op": "update", "target": "BR-1", "changes": {"content": "有未完成任务或被审计冻结的用户均禁止删除，用户及任务数据不变", "status": "active", "sources": [{"type": "user_answer", "location": "合成新资料重评确认"}, {"type": "project_material", "source_id": "SRC-2", "location": "第二版新增冻结规则"}]}},
                            {"op": "update", "target": "AC-1", "changes": {"content": "分别验证单用户/批量入口删除有未完成任务或审计冻结用户，均拒绝且用户和任务不变", "status": "active", "sources": [{"type": "user_answer", "location": "合成新资料重评确认"}]}},
                            {"op": "update", "target": "Q-1", "changes": {"status": "answered", "answer_update": "第二版复核：未完成任务仍禁止，新增冻结状态同样禁止，覆盖两入口", "reason": "新冻结限制及两入口业务条件已复核，保留原answer作历史依据"}},
                            {"op": "update", "target": "Q-2", "changes": {"status": "answered", "answer": "两入口均按已明确业务状态复核；资料和验收已逐条重评", "reason": "新增冻结限制及间接AC已实际更新，不是只清掉stale标记"}}],
             "set": {"context.history_review": review_final, "meta.analysis_status": "completed", "meta.readiness": "ready_for_document"}, "completion_checks": _checks()}
    apply("RA-17-reevaluated", final)
    # 旧指纹指向原地变动来源需要继续提示；旧版本有归档，不能把历史source当当前采用。
    # 因基线SRC1须保留，检查器应在其archived_path核对旧字节，而当前采用SRC2核对新字节。
    cli("RA-17-final-check", "compare_baseline.py", ["--check-sources", working, "--project-root", project], "pass")

    nohistory = blank("NEW-NO-HISTORY", "无历史资料降级")
    nohistory["operations"] = [{"op": "add", "collection": "requirements.goals", "ref": "$goal", "value": {"content": "合成用户仅提出一个新功能想法", "tag": "confirmed", "status": "active", "sources": [{"type": "user_answer", "location": "合成无历史场景"}]}},
                              {"op": "add", "collection": "questions", "ref": "$question", "value": _question("该想法的核心场景、规则和验收是什么？", ["$goal"])}]
    nohistory["set"]["context.history_review"] = {"status": "not_performed", "reason": "没有任何明确指定或可检索历史资料，未做历史对照，不表示无冲突", "source_ids": []}
    nohistory["completion_checks"] = _checks((2, 3, 4, 6, 7))
    empty_workspace = output / "empty-workspace"
    nohistory_path = output / "patches/RA-19-no-history.json"
    _save(nohistory_path, nohistory)
    cli("RA-19-no-history", "update_analysis.py", ["--workspace", empty_workspace, "--project", "no-history", "--patch", nohistory_path], "pass")
    empty_project = empty_workspace / "projects/no-history"
    cli("RA-19-missing-index", "search_project.py", ["--project-root", empty_project, "--query", "用户"], "warning")
    cli("RA-19-degraded", "compare_baseline.py", ["--proposal", empty_project / "requirements/NEW-NO-HISTORY/analysis/analysis-result.json"], "warning")

    # 报告只按已保存且校验通过的JSON整理，不把机械验证通过写成语义已就绪。
    spec = importlib.util.spec_from_file_location("history_report_renderer", ROOT / "tests/requirement-analyst/render_trial_reports.py")
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    reports = []
    for current_project in (project, empty_project):
        for analysis_path in sorted(current_project.glob("requirements/*/analysis/analysis-result.json")):
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            manifest_sources = json.loads(analysis_path.with_name("source-manifest.json").read_text(encoding="utf-8"))
            related = [(json.loads(baseline_path.read_text(encoding="utf-8")), json.loads(baseline_path.with_name("source-manifest.json").read_text(encoding="utf-8")))] if analysis["requirement_id"] == "NEW-DELETE-001" else []
            validation = renderer.VALIDATOR.validate_analysis(analysis, manifest_sources, related_analyses=related)
            assert validation["status"] == "pass", validation
            report = analysis_path.with_name("analysis-report.md")
            with report.open("x", encoding="utf-8") as stream:
                stream.write(renderer.render_report(analysis, validation))
            reports.append(str(report.relative_to(output)))
    assert baseline_path.read_bytes() == baseline_bytes
    assert _sha(project / "versions/user-deletion-v1.md") == source_value["adopted_sha256"]
    manifest = {"stage": 5, "mode": "user_approved_main_session_semantic_patches_actual_cli", "not_real_published_system": True,
                "records": records, "reports": reports, "scenarios": [f"RA-{i}" for i in range(14, 20)], "baseline_preserved": True,
                "baseline_sha256": hashlib.sha256(baseline_bytes).hexdigest(), "baseline_path": str(baseline_path.relative_to(output)),
                "sources": {str(p.relative_to(ROOT)): _sha(p) for p in sorted(FIXTURES.rglob("*.md"))},
                "artifacts": {str(p.relative_to(output)): _sha(p) for p in sorted(output.rglob("*")) if p.is_file() and p.name not in {".analysis.lock", ".analysis-transaction.json"}},
                "limits": ["合成发布声明不是真实项目发布", "语义补丁主会话编写，独立会话仅只读分析并未完成落盘", "不代表产品已批准改变真实业务基线", "无向量检索或PDF解析", "只保证遵守工作区锁的本地进程，未评估网络文件系统"]}
    _save(output / "run-manifest.json", manifest)
    return manifest


def main(argv=None) -> int:
    """读取全新输出目录并运行合成场景；成功返回0，已存在目录或运行错误保留现场并抛出。"""
    parser = argparse.ArgumentParser(description="阶段5合成历史分析实际CLI证据；不调用模型")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    result = run(args.output)
    print(json.dumps({"status": "pass", "scenarios": result["scenarios"], "records": len(result["records"]), "baseline_preserved": result["baseline_preserved"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

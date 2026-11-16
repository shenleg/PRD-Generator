"""只读校验结构化分析结果，按规格 9.6 输出规则诊断和三态结果。"""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
EXIT_CODES = {"pass": 0, "warning": 1, "fail": 2}


def _pointer(parts: Sequence) -> str:
    """将字段路径编码为 JSON Pointer；根对象用空字符串表示。"""
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def _issue(rule: int, item_id: str, path: str, message: str, level: str = "fail") -> dict:
    """构造统一诊断，不修改分析数据。"""
    return {"rule": rule, "level": level, "item_id": item_id, "path": path, "message": message}


def _result(diagnostics: list[dict]) -> dict:
    """失败优先于警告，同时保留全部诊断以便定位。"""
    status = "pass"
    if diagnostics:
        status = "fail" if any(d["level"] == "fail" for d in diagnostics) else "warning"
    return {
        "status": status,
        "diagnostics": sorted(diagnostics, key=lambda d: (d["rule"], d["path"], d["item_id"])),
    }


def _validators() -> tuple[Draft202012Validator, Draft202012Validator]:
    """加载安装目录中的四份 Schema；注册表不启用网络检索。"""
    resources = []
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        resources.append((path.as_uri(), Resource.from_contents(schema)))
    registry = Registry().with_resources(resources)
    checker = FormatChecker()
    return tuple(
        Draft202012Validator({"$ref": uri}, registry=registry, format_checker=checker)
        for uri in (
            (SCHEMA_DIR / "analysis-result.schema.json").as_uri(),
            (SCHEMA_DIR / "source.schema.json").as_uri() + "#/$defs/manifest",
        )
    )


def _format_errors(data: object, validator: Draft202012Validator, rule: int = 1) -> list[dict]:
    """在输入边界定位结构错误；即使上层容器非法也能输出最近的条目编号。"""
    diagnostics = []
    for error in validator.iter_errors(data):
        node = data
        item_id = "$"
        for part in error.absolute_path:
            if isinstance(node, dict):
                item_id = node.get("id", node.get("source_id", item_id))
                node = node[part]
            else:
                node = node[part]
        if isinstance(node, dict):
            item_id = node.get("id", node.get("source_id", item_id))
        error_rule = 3 if rule == 1 and error.validator == "enum" else rule
        diagnostics.append(_issue(error_rule, str(item_id), _pointer(error.absolute_path), f"格式错误：{error.message}"))
    return diagnostics


def _common_items(analysis: dict):
    """遍历契约内的通用条目；扩展字段不被误当作分析条目。"""
    for section, names in (
        ("requirements", ("goals", "scenarios", "functional_requirements", "business_rules", "constraints", "non_functional_requirements", "acceptance_criteria")),
        ("business_assessment", ("flows", "states", "boundaries", "exceptions", "gaps", "conflicts")),
    ):
        for name in names:
            for index, item in enumerate(analysis[section].get(name, [])):
                yield (section, name, index), item
    for name, items in analysis["requirements"].get("scope", {}).items():
        if name in ("in_scope", "out_of_scope"):
            for index, item in enumerate(items):
                yield ("requirements", "scope", name, index), item
    for name in ("assumptions", "decisions"):
        for index, item in enumerate(analysis[name]):
            yield (name, index), item


def _entries(analysis: dict):
    """遍历通用条目与问题，用于同一需求内的编号和引用检查。"""
    yield from _common_items(analysis)
    for index, question in enumerate(analysis["questions"]):
        yield ("questions", index), question


def _index_documents(documents: Sequence[tuple[dict, list]], diagnostics: list[dict]) -> dict:
    """为显式传入的资料建立编号表；重复编号直接诊断，不猜测应使用哪份记录。"""
    registry = {}
    for analysis, manifest in documents:
        requirement_id = analysis["requirement_id"]
        if requirement_id in registry:
            diagnostics.append(_issue(2, requirement_id, "/requirement_id", "重复提供同一需求的分析结果。"))
            continue
        items = {}
        entries = list(_entries(analysis))
        entries.extend((("source-manifest", i), source) for i, source in enumerate(manifest))
        for path, item in entries:
            item_id = item["id"] if "id" in item else item["source_id"]
            if item_id in items:
                diagnostics.append(_issue(2, item_id, _pointer(path), f"需求 {requirement_id} 中编号重复。"))
            else:
                items[item_id] = item
        registry[requirement_id] = items
    return registry


def _references(analysis: dict):
    """遍历规范定义的条目引用，不扫描正文或未知扩展字段里的普通字符串。"""
    for path, item in _entries(analysis):
        for index, reference in enumerate(item.get("related_ids", [])):
            yield (*path, "related_ids", index), item, reference, False
        if "related_question" in item:
            yield (*path, "related_question"), item, item["related_question"], False
    for index, reference in enumerate(analysis.get("technical_feasibility", {}).get("related_questions", [])):
        yield ("technical_feasibility", "related_questions", index), None, reference, False
    for index, reference in enumerate(analysis.get("impact_analysis", {}).get("affected_requirements", [])):
        yield ("impact_analysis", "affected_requirements", index), None, reference, "/" not in reference


def _check_references(analysis: dict, registry: dict, diagnostics: list[dict]) -> None:
    """检查引用存在及有效条目到已撤销条目的依赖，不修改任何状态。"""
    for path, owner, reference, requirement_only in _references(analysis):
        owner_id = owner["id"] if owner is not None else "$"
        if requirement_only:
            if reference not in registry:
                diagnostics.append(_issue(2, owner_id, _pointer(path), f"未提供被引用需求 {reference} 的分析结果。"))
            continue
        if "/" in reference:
            requirement_id, item_id = reference.split("/", 1)
        else:
            requirement_id, item_id = analysis["requirement_id"], reference
        target = registry.get(requirement_id, {}).get(item_id)
        if target is None:
            diagnostics.append(_issue(2, owner_id, _pointer(path), f"引用编号不存在或未提供关联资料：{reference}。"))
            continue
        if owner is not None and target.get("status") == "withdrawn":
            is_effective = owner["status"] == "active" or (owner["id"].startswith("Q-") and owner["status"] != "dropped")
            if is_effective:
                diagnostics.append(_issue(8, owner_id, _pointer(path), f"仍引用已撤销条目 {reference}；通用条目须待重评，相关问题须按撤销流程废弃。"))


def _check_sources(analysis: dict, manifest: list, diagnostics: list[dict]) -> None:
    """校验条目与技术依据的来源，保留待重评或撤销记录中的来源存在性检查。"""
    source_ids = {source["source_id"] for source in manifest}
    groups = []
    for path, item in _common_items(analysis):
        groups.append((path, item["id"], item["sources"]))
        if item["status"] == "active" and not item["sources"]:
            diagnostics.append(_issue(7, item["id"], _pointer((*path, "sources")), "有效条目至少需要一个来源。"))
    for index, evidence in enumerate(analysis.get("technical_feasibility", {}).get("evidence", [])):
        groups.append((("technical_feasibility", "evidence", index), "$", evidence["sources"]))
    for path, item_id, sources in groups:
        for index, source in enumerate(sources):
            if "source_id" in source and source["source_id"] not in source_ids:
                diagnostics.append(_issue(7, item_id, _pointer((*path, "sources", index, "source_id")), f"来源 {source['source_id']} 不在本需求来源清单中。"))
    for index, source_id in enumerate(analysis.get("context", {}).get("source_ids", [])):
        if source_id not in source_ids:
            diagnostics.append(_issue(7, "$", _pointer(("context", "source_ids", index)), f"项目上下文引用的来源 {source_id} 不存在。"))


def _check_questions(analysis: dict, diagnostics: list[dict]) -> None:
    """按问题状态检查就绪度及当前有效的假设、决策；研发 P1 不阻塞文档就绪。"""
    assumptions = {a["related_question"] for a in analysis["assumptions"] if a["status"] == "active"}
    decisions = {d["related_question"] for d in analysis["decisions"] if d["status"] == "active"}
    readiness = analysis["meta"]["readiness"]
    for index, question in enumerate(analysis["questions"]):
        question_id = question["id"]
        if question["status"] == "open":
            if question["priority"] == "P0" and readiness != "not_ready":
                diagnostics.append(_issue(4, question_id, "/meta/readiness", "存在待回答 P0 问题，就绪度必须为 not_ready。"))
            elif question["priority"] == "P1" and question["resolution"] != "ask_dev" and question_id not in assumptions and readiness == "ready_for_document":
                diagnostics.append(_issue(4, question_id, "/meta/readiness", "待回答 P1 问题没有有效暂定假设，就绪度不得高于 conditionally_ready。"))
        if question["status"] == "provisional" and question_id not in assumptions:
            diagnostics.append(_issue(5, question_id, _pointer(("questions", index, "status")), "暂定问题缺少关联的 active 假设。"))
        if question["status"] == "excluded" and question["priority"] == "P0" and question_id not in decisions:
            diagnostics.append(_issue(6, question_id, _pointer(("questions", index, "status")), "已排除的 P0 问题缺少关联的 active 决策。"))
    questions = {q["id"]: q for q in analysis["questions"]}
    for index, conflict in enumerate(analysis["business_assessment"]["conflicts"]):
        path = _pointer(("business_assessment", "conflicts", index, "related_question"))
        question = questions.get(conflict["related_question"])
        if question is None:
            diagnostics.append(_issue(10, conflict["id"], path, "矛盾未关联本需求内存在的问题条目。"))
        elif conflict["status"] != "withdrawn" and question["status"] == "open" and readiness != "not_ready":
            diagnostics.append(_issue(4, conflict["id"], "/meta/readiness", "存在未处理的矛盾，就绪度必须为 not_ready。"))


def _check_completion(analysis: dict, diagnostics: list[dict]) -> None:
    """核对显式完成清单；问题已关闭并不能代替核心缺口真正满足。"""
    checks = analysis.get("completion_checks")
    if checks is None:
        return
    if {check["item"] for check in checks} != set(range(1, 12)):
        diagnostics.append(_issue(1, "$", "/completion_checks", "完成清单必须包含唯一的 1 至 11 项。"))
    questions = {q["id"]: q for q in analysis["questions"]}
    readiness = analysis["meta"]["readiness"]
    for index, check in enumerate(checks):
        path = _pointer(("completion_checks", index))
        linked = []
        for reference in check["question_refs"]:
            question = questions.get(reference)
            if question is None:
                diagnostics.append(_issue(2, reference, path + "/question_refs", "清单引用的问题不存在。"))
            elif question["status"] == "dropped" and not check["satisfied"]:
                diagnostics.append(_issue(4, reference, path + "/question_refs", "未满足项不能由已废弃问题支撑。"))
            else:
                linked.append(question)
        if check["satisfied"]:
            continue
        required = ("P0",) if check["item"] <= 7 else ("P0", "P1")
        if not any(q["priority"] in required for q in linked):
            diagnostics.append(_issue(4, "$", path + "/question_refs", "未满足项须关联相应优先级的问题：" + "/".join(required) + "。"))
        if (check["item"] <= 7 and readiness != "not_ready") or readiness == "ready_for_document":
            diagnostics.append(_issue(4, "$", "/meta/readiness", f"完成清单第 {check['item']} 项未满足，不能使用当前就绪度。"))


def _check_technical(analysis: dict, diagnostics: list[dict]) -> None:
    """检查技术判断所需证据的结构完整性，不替代研发对结论真实性的确认。"""
    technical = analysis.get("technical_feasibility")
    if technical is None:
        return
    if technical["conclusion"] != "unknown":
        if not technical["evidence"]:
            diagnostics.append(_issue(9, "$", "/technical_feasibility/evidence", "非 unknown 技术结论必须有依据。"))
        for index, evidence in enumerate(technical["evidence"]):
            if not evidence["content"].strip() or not evidence["sources"]:
                diagnostics.append(_issue(9, "$", _pointer(("technical_feasibility", "evidence", index)), "每条技术依据必须有说明和来源。"))
        if not technical["credibility"].strip() or technical["credibility"].strip().lower() == "unknown":
            diagnostics.append(_issue(9, "$", "/technical_feasibility/credibility", "非 unknown 技术结论必须说明可信程度。"))
        if not any(impact.strip() for impact in technical["potential_impact"]):
            diagnostics.append(_issue(9, "$", "/technical_feasibility/potential_impact", "非 unknown 技术结论必须说明潜在影响。"))
    questions = {q["id"]: q for q in analysis["questions"]}
    for index, question_id in enumerate(technical["related_questions"]):
        if question_id not in questions or questions[question_id]["resolution"] != "ask_dev":
            diagnostics.append(_issue(9, question_id, _pointer(("technical_feasibility", "related_questions", index)), "技术确认问题必须指向本需求的 ask_dev 问题。"))


def _check_history(analysis: dict, manifest: list, diagnostics: list[dict]) -> None:
    """仅核对显式采用声明，不把来源存在或检索命中等同于业务对照已完成。"""
    review = analysis.get("context", {}).get("history_review")
    if review is None:
        return  # 旧1.0结果未声明历史对照，保持向后兼容。
    sources = {source["source_id"]: source for source in manifest}
    for source_id in review["source_ids"]:
        source = sources.get(source_id)
        if source is None or "adopted_sha256" not in source:
            diagnostics.append(_issue(7, source_id, "/context/history_review/source_ids", "采用的历史资料必须存在并记录adopted_sha256。"))
    if review["status"] == "not_performed" and (review["source_ids"] or "baseline" in review):
        diagnostics.append(_issue(7, "$", "/context/history_review", "未做历史对照时不得声明已采用资料或当前基线。"))
    if review["status"] == "reviewed" and not review["source_ids"]:
        diagnostics.append(_issue(7, "$", "/context/history_review", "已对照声明必须有实际采用的资料。"))
    if review["status"] == "stale" and (analysis["meta"]["analysis_status"] != "stale" or analysis["meta"]["readiness"] != "not_ready"):
        diagnostics.append(_issue(4, "$", "/meta", "历史依据已变化时必须stale/not_ready，完成重评后再解除。"))
    baseline = review.get("baseline")
    revision = analysis["meta"]["baseline_revision"]
    if baseline is not None:
        source = sources.get(baseline["source_id"], {})
        if (baseline["requirement_id"] != analysis["requirement_id"] or baseline["analysis_revision"] != revision
                or baseline["source_id"] not in review["source_ids"] or source.get("authority") != "current_published"
                or not source.get("publication_basis")):
            diagnostics.append(_issue(7, "$", "/context/history_review/baseline", "基线须对应本需求显式确认的现行发布来源、采用资料及meta.baseline_revision；草稿不作现行基线。"))
    elif revision is not None:
        diagnostics.append(_issue(7, "$", "/meta/baseline_revision", "新历史对照声明中的非空基线修订须有对应发布依据。"))


def validate_analysis(
    analysis: dict,
    source_manifest: list[dict],
    *,
    related_analyses: Sequence[tuple[dict, list[dict]]] = (),
) -> dict:
    """校验分析结果及来源，返回 status 与逐条诊断，不修改输入。

    analysis 是当前结构化结果，source_manifest 是其来源清单；related_analyses
    是显式提供的外部结果及对应清单，仅用于核验引用，不执行自动检索。
    输入数据违规通过 fail 返回；Schema 安装缺失或损坏时抛出文件或 Schema 异常。
    """
    analysis_validator, manifest_validator = _validators()
    documents = [(analysis, source_manifest), *related_analyses]
    diagnostics = []
    for document, manifest in documents:
        diagnostics.extend(_format_errors(document, analysis_validator))
        diagnostics.extend(_format_errors(manifest, manifest_validator, 7))
    if diagnostics:
        # 结构错误不进入条目检查，但已明确的 stale 标记仍须向下游保留。
        if isinstance(analysis, dict) and isinstance(analysis.get("meta"), dict) and analysis["meta"].get("analysis_status") == "stale":
            diagnostics.append(_issue(11, "$", "/meta/analysis_status", "分析已过期；下游须提示重新评估。", "warning"))
        return _result(diagnostics)
    registry = _index_documents(documents, diagnostics)
    _check_references(analysis, registry, diagnostics)
    _check_sources(analysis, source_manifest, diagnostics)
    _check_history(analysis, source_manifest, diagnostics)
    _check_questions(analysis, diagnostics)
    _check_completion(analysis, diagnostics)
    _check_technical(analysis, diagnostics)
    if analysis["meta"]["analysis_status"] == "stale":
        diagnostics.append(_issue(11, "$", "/meta/analysis_status", "分析已过期；下游须提示重新评估。", "warning"))
    return _result(diagnostics)


def _unique_object(pairs: list[tuple]) -> dict:
    """拒绝 JSON 中的重复键，避免静默覆盖用户数据。"""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON 包含重复字段：{key}")
        result[key] = value
    return result


def _invalid_constant(value: str):
    """拒绝 JSON 标准不允许的 NaN 和 Infinity。"""
    raise ValueError(f"JSON 包含非法数值：{value}")


def _load_json(path: Path):
    """读取外部 JSON；文件、编码和解析错误交给命令行边界报告。"""
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)


def main(argv: Sequence[str] | None = None) -> int:
    """读取 argv 指定的分析及来源，输出 JSON，返回 pass=0、warning=1、fail=2。

    argv 为命令行参数，省略时读取进程参数。用户文件错误转为 fail 诊断；
    参数用法错误由 argparse 报告，内部 Schema 安装错误直接抛出。
    """
    parser = argparse.ArgumentParser(description="只读校验需求分析结果，输出 JSON 诊断。")
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--related-analysis", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    documents = []
    diagnostics = []
    for path in [args.analysis, *args.related_analysis]:
        manifest_path = args.source_manifest if path == args.analysis and args.source_manifest is not None else path.with_name("source-manifest.json")
        try:
            analysis = _load_json(path)
        except (OSError, ValueError) as error:
            diagnostics.append(_issue(1, "$", str(path), f"无法读取分析 JSON：{error}"))
            continue
        try:
            manifest = _load_json(manifest_path)
        except (OSError, ValueError) as error:
            diagnostics.append(_issue(7, "$", str(manifest_path), f"无法读取来源清单：{error}"))
            continue
        documents.append((analysis, manifest))
    if diagnostics:
        result = _result(diagnostics)
    else:
        analysis, manifest = documents[0]
        result = validate_analysis(analysis, manifest, related_analyses=documents[1:])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return EXIT_CODES[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

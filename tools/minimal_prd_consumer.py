"""阶段 4 的确定性交接消费者：校验分析、生成保真草稿；不是完整 PRD Generator。"""

import argparse
import copy
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill/requirement-analyst/scripts/validate_analysis.py"
COLLECTIONS = (
    "requirements.goals", "requirements.scenarios", "requirements.functional_requirements",
    "requirements.business_rules", "requirements.constraints", "requirements.non_functional_requirements",
    "requirements.acceptance_criteria", "requirements.scope.in_scope", "requirements.scope.out_of_scope",
    "business_assessment.flows", "business_assessment.states", "business_assessment.boundaries",
    "business_assessment.exceptions", "business_assessment.gaps", "business_assessment.conflicts",
    "assumptions", "decisions",
)
EXIT_CODES = {"pass": 0, "warning": 1, "fail": 2}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _segment(value):
    _require(isinstance(value, str) and bool(value) and value not in {".", ".."}
             and "/" not in value and "\\" not in value
             and not any(c.isspace() or ord(c) < 32 for c in value), "编号必须是无空白的单一路径段。")
    return value


def _safe(root, relative):
    current = root
    for part in Path(relative).parts:
        _require(part not in {"..", "/"}, "路径逃逸工作区。")
        current = current / part
        _require(not current.is_symlink(), f"受管路径不能包含符号链接：{current}")
    return current


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"JSON 包含重复字段：{key}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"JSON 包含非法数值：{value}")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique, parse_constant=_constant)


def _validator():
    spec = importlib.util.spec_from_file_location("handoff_analysis_validator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_analysis


def _items(analysis, section):
    value = analysis
    for key in section.split("."):
        value = value.get(key, {} if key == "scope" else [])
    return value


def _response(status, action, message, **fields):
    return {"status": status, "action": action, "message": message, "written": False, **fields}


def _sync(record, revision):
    if "prd" not in record:
        return "absent"
    prd = record["prd"]
    _require(isinstance(prd, dict), "requirement.json/prd 必须为对象。")
    based = prd.get("based_on_analysis_revision")
    version = prd.get("version")
    _require(type(based) is int and based >= 1 and based <= revision, "PRD 基于的修订号非法或超前，须人工检查。")
    _require(type(version) is int and version >= 1 and prd.get("status") == "draft", "本测试消费者只维护正整数版本、status=draft 的草稿。")
    return "pending" if based < revision else "current"


def _quote(text):
    # 缩进代码块保持原文；来源中的 Markdown/HTML 不能改变外层的标签及状态展示。
    return "\n".join("    " + line for line in str(text).splitlines())


def _render(analysis, record, validation, missing):
    meta = analysis["meta"]
    lines = ["# 简化交接草稿（非完整 PRD）", "", _quote(record["common"].get("title", analysis["requirement_id"])), "",
             f"需求：{analysis['requirement_id']}；基于分析修订：{meta['analysis_revision']}",
             f"analysis_status={meta['analysis_status']}；readiness={meta['readiness']}",
             "待产品负责人确认；本工具不分配正式 PRD 编号、不发布。", ""]
    if meta["analysis_status"] == "stale":
        lines += ["> 基于过期分析：建议先重新评估；本次仅因用户明确坚持生成草稿。", ""]
    if meta["readiness"] == "not_ready":
        lines += ["> 风险：仅为初步草稿，存在未解决缺口，不能作为已就绪需求交付。", ""]
    elif meta["readiness"] == "conditionally_ready":
        lines += ["> 条件就绪：遗留事项、暂定假设与研发确认项仍需处理。", ""]
    for diagnostic in validation["diagnostics"]:
        lines += ["校验提示：", _quote(diagnostic["message"]), ""]
    lines += ["## 分析条目摘录与映射", "", "以下编号仅用于分析追溯，不是正式 PRD 需求编号。", ""]
    for section in COLLECTIONS:
        visible = [item for item in _items(analysis, section) if item["status"] != "withdrawn"]
        if not visible:
            continue
        lines += [f"### {section}", ""]
        for item in visible:
            label = "待重评，非确定内容" if item["status"] == "to_reassess" else "当前条目"
            if item["tag"] == "assumption":
                label += "；暂定假设，待验证"
            elif item["tag"] == "inferred":
                label += "；推断，未经确认"
            lines += [f"映射：{analysis['requirement_id']}/{item['id']} | tag={item['tag']} | status={item['status']} | {label}", "", _quote(item["content"]), ""]
            detail = {k: v for k, v in item.items() if k not in {"id", "content", "tag", "status"}}
            lines += [_quote(json.dumps(detail, ensure_ascii=False, indent=2)), ""]
    if "ux_assessment" in analysis:
        lines += ["## 体验与待设计事项", "", "保留实际界面依赖判断、设计待办及候选流程；视觉建议不是已确认界面或已实现行为。", "", _quote(json.dumps(analysis["ux_assessment"], ensure_ascii=False, indent=2)), ""]
    if "technical_feasibility" in analysis:
        lines += ["## 技术评估与限制", "", "保留原结论、证据和待验证条件；技术判断不等于研发验收、业务就绪或发布批准。", "", _quote(json.dumps(analysis["technical_feasibility"], ensure_ascii=False, indent=2)), ""]
    lines += ["## 遗留事项与问题记录", "", "open/provisional/risk_accepted 及 ask_dev 项保持原状态；推荐选项不是已确认答案。", ""]
    for question in analysis["questions"]:
        if question["status"] == "dropped":
            continue
        lines += [f"映射：{analysis['requirement_id']}/{question['id']} | {question['priority']} | {question['status']} | {question['resolution']}", "", _quote(json.dumps(question, ensure_ascii=False, indent=2)), ""]
    for check in analysis.get("completion_checks", []):
        if not check["satisfied"]:
            lines += [f"完成清单第 {check['item']} 项未满足：", _quote(check["reason"]), ""]
    if missing:
        lines += ["## 待回流缺口", _quote(json.dumps(missing, ensure_ascii=False)), ""]
    return "\n".join(lines) + "\n"


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _save(directory, record, revision, markdown):
    version = record.get("prd", {}).get("version", 0) + 1
    prd = directory / "prd"
    name = f"handoff-draft-v{version}.md"
    draft_created, metadata_committed = False, False
    try:
        prd.mkdir(exist_ok=True)
        _fsync_directory(directory)
        # 草稿先完整落盘，再提交元数据。中断可留下未引用文件，但不会让元数据指向未写完草稿。
        # 已存在的未提交草稿保留并拒绝覆盖，需人工检查，不自动删除或猜测恢复。
        descriptor = os.open(prd / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        draft_created = True
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(markdown.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(prd)
        saved = copy.deepcopy(record)
        saved.setdefault("prd", {}).update({"based_on_analysis_revision": revision, "status": "draft", "version": version})
        descriptor, temporary = tempfile.mkstemp(prefix=".prd-write-", dir=directory)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write((json.dumps(saved, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, directory / "requirement.json")
        metadata_committed = True
        _fsync_directory(directory)
    except OSError as error:
        return _response("fail", "inspect_write", f"草稿保存未完整完成，保留现场，请人工检查后再操作：{error}",
                         written=metadata_committed, draft_created=draft_created, draft_path=f"prd/{name}")
    return _response("pass", "draft_created", "已生成简化草稿，待产品负责人确认。", written=True, draft_path=f"prd/{name}")


def _consume_locked(root, project, requirement, validate, insist_stale, expected_revision, required_sections, related, inspect_only):
    journal = _safe(root, ".analysis-transaction.json")
    if journal.exists() and _load(journal) is not None:
        return _response("fail", "recover_analysis", "存在未完成分析事务；先由更新器恢复，不读取半完成快照。")
    relative = Path("projects") / project / "requirements" / requirement
    directory = _safe(root, relative)
    path = _safe(root, relative / "analysis/analysis-result.json")
    if not path.exists():
        return _response("warning", "analyze", "没有分析结果；先转入需求分析，不生成草稿。")
    analysis = _load(path)
    manifest = _load(_safe(root, relative / "analysis/source-manifest.json"))
    validation = validate(analysis, manifest, related_analyses=related)
    if validation["status"] == "fail":
        return _response("fail", "repair_analysis", "分析校验失败；先回到需求分析修正。", validation=validation)
    revision = analysis["meta"]["analysis_revision"]
    _require(analysis["requirement_id"] == requirement and analysis["context"]["project_id"] == project, "分析身份与调用路径不匹配。")
    record = _load(_safe(root, relative / "requirement.json"))
    _require(isinstance(record, dict) and isinstance(record.get("common"), dict), "缺少 requirement.json/common。")
    _require(record["common"].get("requirement_id") == requirement and record["common"].get("project_id") == project, "requirement.json/common 身份与分析不匹配。")
    _safe(root, relative / "prd")
    sync = _sync(record, revision)
    fields = {"validation": validation, "requirement_id": requirement, "revision": revision, "sync_state": sync}
    _require(expected_revision is None or (type(expected_revision) is int and expected_revision == revision), "分析 revision 冲突；重新读取并确认后再生成。")
    warning = validation["status"] == "warning" or analysis["meta"]["readiness"] != "ready_for_document"
    if inspect_only:
        return _response("warning" if warning else "pass", "inspect", "同步状态由当前分析修订号和草稿基于的修订号比较得出。", **fields)
    if validation["status"] == "warning" and not insist_stale:
        return _response("warning", "reevaluate", "分析已过期；先重新评估，用户明确坚持时才允许生成过期草稿。", **fields)
    missing = [section for section in required_sections if not any(item["status"] == "active" for item in _items(analysis, section))]
    if missing:
        feedback = {"requirement_id": requirement, "base_revision": revision, "change_type": "supplement", "missing_sections": missing,
                    "instruction": "回交需求分析：审阅缺口，登记新问题，重新判定完成清单与就绪度，通过 update_analysis.py 保存；不得自行补成事实。"}
        return _response("warning", "register_questions", "模板需要的章节无有效分析条目；不生成，先回交分析侧。", feedback=feedback, **fields)
    saved = _save(directory, record, revision, _render(analysis, record, validation, missing))
    if saved["status"] == "fail":
        return {**fields, **saved, "sync_state": "current" if saved["written"] else sync}
    return {**fields, **saved, "status": "warning" if warning else "pass", "sync_state": "current"}


def consume(workspace: Path, project_id: str, requirement_id: str, *, insist_stale: bool = False,
            expected_revision: int | None = None, required_sections=(), related_analyses=(), inspect_only: bool = False) -> dict:
    """在共享工作区锁下读取分析并生成最小草稿，返回门禁、校验和同步结果。

    workspace/project_id/requirement_id 定位已有需求，不创建需求。insist_stale 代表用户
    明确坚持使用过期分析；expected_revision 可约束用户看到的版本。required_sections
    为模板明确要求的条目集合路径，空集合回流但不代替业务完整性分析。
    related_analyses 为显式提供的关联结果/来源对，inspect_only 只比较同步而不写草稿。
    可修复的文件、编码和输入错误返回 fail；安装、依赖或内部编程错误直接抛出。
    Linux/Unix 本地工作区；分析只读，仅写 prd/、requirement.json/prd 和共享锁。
    """
    validate = _validator()
    try:
        project, requirement = _segment(project_id), _segment(requirement_id)
        required_sections = tuple(required_sections)
        _require(all(section in COLLECTIONS for section in required_sections), "required_sections 含未知条目集合路径。")
        _require(type(insist_stale) is bool and type(inspect_only) is bool, "调用开关必须为 bool。")
        root = Path(workspace).absolute()
        _require(not any(path.is_symlink() for path in (root, *root.parents)), "工作区路径不能包含符号链接。")
        if not root.exists():
            return _response("warning", "analyze", "没有工作区或分析结果；先转入需求分析。")
        lock = _safe(root, ".analysis.lock")
        descriptor = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "a+b") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            return _consume_locked(root, project, requirement, validate, insist_stale, expected_revision,
                                   tuple(required_sections), related_analyses, inspect_only)
    except (OSError, ValueError, UnicodeError) as error:
        return _response("fail", "reject", str(error))


class _Parser(argparse.ArgumentParser):
    """CLI 参数错误转为 JSON 失败响应；沿用 ArgumentParser 的解析接口。"""

    def error(self, message):
        """将参数错误 message 抛给 main；无返回值，抛出 ValueError。"""
        raise ValueError(message)


def main(argv=None) -> int:
    """解析 argv、输出单一 JSON，返回 pass=0/warning=1/fail=2。

    argv 省略时读取进程参数。输入错误转换为结构化失败，内部安装错误保持可见。
    """
    parser = _Parser(description="阶段4最小交接消费者；不调用模型、不生成完整PRD或发布")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--requirement", required=True)
    parser.add_argument("--insist-stale", action="store_true")
    parser.add_argument("--expected-revision", type=int)
    parser.add_argument("--require-section", action="append", default=[], choices=COLLECTIONS)
    parser.add_argument("--related-analysis", type=Path, action="append", default=[])
    parser.add_argument("--inspect-only", action="store_true")
    try:
        args = parser.parse_args(argv)
        related = [(_load(path), _load(path.with_name("source-manifest.json"))) for path in args.related_analysis]
        result = consume(args.workspace, args.project, args.requirement, insist_stale=args.insist_stale,
                         expected_revision=args.expected_revision, required_sections=args.require_section,
                         related_analyses=related, inspect_only=args.inspect_only)
    except (OSError, ValueError, UnicodeError) as error:
        result = _response("fail", "reject", str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return EXIT_CODES[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

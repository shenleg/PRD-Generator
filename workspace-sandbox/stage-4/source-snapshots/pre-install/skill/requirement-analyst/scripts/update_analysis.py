"""确定性应用补丁 1.0，在工作区锁下校验、编号并以可恢复事务保存分析。"""

import argparse
import base64
import copy
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile


_COLLECTIONS = {
    "requirements.goals": "GOAL", "requirements.scenarios": "SCN",
    "requirements.functional_requirements": "FR", "requirements.business_rules": "BR",
    "requirements.constraints": "CON", "requirements.non_functional_requirements": "NFR",
    "requirements.acceptance_criteria": "AC", "business_assessment.flows": "FLOW",
    "business_assessment.states": "STATE", "business_assessment.boundaries": "BND",
    "business_assessment.exceptions": "EXC", "business_assessment.gaps": "GAP",
    "business_assessment.conflicts": "CNF", "questions": "Q", "assumptions": "ASM",
    "decisions": "DEC", "requirements.scope.in_scope": None,
    "requirements.scope.out_of_scope": None,
}
_SCOPE_PREFIXES = set(_COLLECTIONS.values()) - {None, "Q"}
_SET_FIELDS = {
    "meta": {"input_type", "analysis_status", "readiness"},
    "context": {"project_id", "domain", "source_ids", "domain_terms"},
    "value_assessment": {"problem", "affected_users", "expected_benefits", "success_metrics", "alternatives", "business_value", "necessity"},
    "ux_assessment": {"ui_dependent", "design_pending_items", "visual_recommendations", "interaction_flows"},
    "impact_analysis": {"affected_requirements", "affected_modules", "proposed_changes"},
}
_CHANGE_TYPES = {"initial_analysis", "supplement", "correction", "withdrawal", "new_source_version"}
_EXIT_CODES = {"pass": 0, "warning": 1, "fail": 2}
_LOCK = ".analysis.lock"
_JOURNAL = ".analysis-transaction.json"


class _InputError(Exception):
    """携带用户可修复的补丁、工作区或事务诊断。"""

    def __init__(self, message, path="", item_id="$"):
        super().__init__(message)
        self.path = path
        self.item_id = item_id


def _require(condition, message, path="", item_id="$"):
    """把输入约束转为同一诊断边界，而非依赖 assert。"""
    if not condition:
        raise _InputError(message, path, item_id)


def _failure(error, requirement_id=None, revision=None):
    """保留公共结果形状，失败时不宣称已完成写入。"""
    return {
        "status": "fail", "diagnostics": [{"rule": 1, "level": "fail",
        "item_id": getattr(error, "item_id", "$"), "path": getattr(error, "path", ""),
        "message": str(error)}], "requirement_id": requirement_id,
        "revision": revision, "id_map": {}, "affected_ids": [], "written": False,
    }


def _unique_object(pairs):
    """拒绝重复 JSON 键，避免覆盖正文或协议字段。"""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON 包含重复字段：{key}")
        result[key] = value
    return result


def _invalid_constant(value):
    """拒绝非 JSON 数值 NaN 及 Infinity。"""
    raise ValueError(f"JSON 包含非法数值：{value}")


def _load_json(path):
    """读取严格 JSON；路径、编码与解析错误由公共边界转成诊断。"""
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_invalid_constant)
    except (OSError, ValueError, UnicodeError) as error:
        raise _InputError(f"无法读取 JSON：{error}", str(path)) from error


def _json_bytes(value):
    """稳定编码 JSON，禁止 API 调用方传入非有限数值。"""
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _segment(value, label):
    """限定单一路径段，阻断路径穿越与跨平台分隔符。"""
    _require(isinstance(value, str) and bool(value) and value not in {".", ".."}
             and "/" not in value and "\\" not in value and not Path(value).is_absolute()
             and not any(c.isspace() or ord(c) < 32 for c in value),
             f"{label} 必须是无空白的单一路径段。")
    return value


def _safe(root, relative):
    """拒绝受管路径上的符号链接，避免校验与替换操作指向不同位置。"""
    relative = Path(relative)
    _require(not relative.is_absolute() and ".." not in relative.parts, "受管路径逃逸工作区。", str(relative))
    current = root
    for part in relative.parts:
        current = current / part
        _require(not current.is_symlink(), "受管路径不能包含符号链接。", str(current))
    _require(current.resolve().is_relative_to(root), "受管路径逃逸工作区。", str(current))
    return current


def _read_optional(path):
    """读取原始字节，缺失与空文件保持可区分，供事务恢复比较。"""
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _sync_directory(path):
    """同步目录项，保证事务记录与原子替换在崩溃后的顺序。"""
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(path, content):
    """同目录写入并原子替换；临时文件不承载独立业务状态。"""
    # 新目录也要同步父目录，否则掉电可能保留日志却丢失已创建的目录项。
    missing = []
    parent = path.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir()
        _sync_directory(directory.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=".analysis-write-", dir=path.parent)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    _sync_directory(path.parent)


def _pack(content):
    """在事务 JSON 中无损保存原字节，包括旧事件的完整前缀。"""
    return None if content is None else base64.b64encode(content).decode("ascii")


def _unpack(content):
    """校验并解码事务字节，损坏记录不得变成任意写入。"""
    _require(content is None or isinstance(content, str), "事务字节编码非法。")
    try:
        return None if content is None else base64.b64decode(content, validate=True)
    except ValueError as error:
        raise _InputError("事务字节编码损坏。") from error


def _recover(root):
    """锁内幂等向前完成事务；先比较所有旧/新字节，再触碰任何业务文件。"""
    journal = _safe(root, _JOURNAL)
    if not journal.exists():
        return
    record = _load_json(journal)
    if record is None:
        return
    _require(isinstance(record, dict) and record.get("version") == 1, "无法识别待恢复事务。", str(journal))
    project = _segment(record.get("project_id"), "事务项目编号")
    requirement = _segment(record.get("requirement_id"), "事务需求编号")
    base = Path("projects") / project / "requirements" / requirement
    allowed = {str(base / "analysis" / name) for name in ("analysis-result.json", "source-manifest.json", "analysis-events.jsonl")}
    allowed.update({"workspace.json", str(base / "requirement.json")})
    writes = record.get("writes")
    _require(isinstance(writes, list) and bool(writes), "待恢复事务缺少写入清单。", str(journal))
    decoded = []
    seen = set()
    for entry in writes:
        _require(isinstance(entry, dict) and isinstance(entry.get("path"), str), "事务写入项格式非法。", str(journal))
        name = entry["path"]
        _require(name in allowed and name not in seen, "事务含未授权或重复写入路径。", name)
        seen.add(name)
        path = _safe(root, name)
        before, after = _unpack(entry.get("before")), _unpack(entry.get("after"))
        _require(after is not None, "事务不能删除业务文件。", name)
        append = name.endswith("/analysis-events.jsonl")
        if append:
            _require(after.startswith(before or b""), "事务事件未保留原始前缀。", name)
        if name.endswith("/requirement.json"):
            _require(before is None, "事务不得覆盖既有 common 或 prd。", name)
        current = _read_optional(path)
        # append 的单次 write 也可能被中断；只接受位于已记录前缀与完整新值之间的字节。
        partial_append = append and current is not None and len(current) >= len(before or b"") and after.startswith(current)
        _require(current == before or current == after or partial_append, "事务恢复冲突：文件不再等于记录的旧值或新值；请人工检查，不要删除事务记录。", name)
        decoded.append((path, before, after, current, append))
    for path, before, after, current, append in decoded:
        if current == after:
            continue
        if append:
            # 不重写旧事件；恢复检测完整新字节，避免重复追加同一 revision。
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("ab") as stream:
                stream.write(after[len(current or b""):])
                stream.flush()
                os.fsync(stream.fileno())
            _sync_directory(path.parent)
        else:
            _atomic_write(path, after)
    # 保留持久日志文件，以 null 标记完成，避免删除恢复记录与锁文件。
    _atomic_write(journal, _json_bytes(None))
    return record


def _validator():
    """从安装目录绝对加载唯一校验器，不依赖当前目录或 sys.path。"""
    path = Path(__file__).resolve().with_name("validate_analysis.py")
    spec = importlib.util.spec_from_file_location("_requirement_analysis_validator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_analysis


def _protocol(patch):
    """检查补丁容器及操作形状，防止非法结构进入条目处理逻辑。"""
    _require(isinstance(patch, dict), "补丁必须是对象。")
    required = {"patch_version", "requirement_id", "base_revision", "change_type", "actor", "summary", "operations", "set", "completion_checks"}
    _require(not (set(patch) - required - {"title", "user_statement"}), "补丁含未知顶层字段。")
    _require(required <= set(patch), "补丁缺少必填字段：" + ", ".join(sorted(required - set(patch))))
    _require(patch["patch_version"] == "1.0", "仅支持 patch_version=1.0。", "/patch_version")
    _require(type(patch["base_revision"]) is int and patch["base_revision"] >= 0, "base_revision 必须是非负整数。", "/base_revision")
    _require(isinstance(patch["change_type"], str) and patch["change_type"] in _CHANGE_TYPES, "未知 change_type。", "/change_type")
    _require(patch["actor"] in ("user", "analyst"), "actor 必须是 user 或 analyst。", "/actor")
    _require(isinstance(patch["summary"], str) and patch["summary"].strip(), "summary 不得为空。", "/summary")
    if "user_statement" in patch:
        _require(isinstance(patch["user_statement"], str), "user_statement 必须是字符串。", "/user_statement")
    if patch["actor"] == "user":
        _require(bool(patch.get("user_statement", "").strip()), "actor=user 时必须提供实际 user_statement。", "/user_statement")
    initial = patch["change_type"] == "initial_analysis"
    if initial:
        _require(patch["base_revision"] == 0, "首次分析 base_revision 必须是 0。")
        _require(isinstance(patch.get("title"), str) and patch["title"].strip(), "首次分析必须提供非空 title。", "/title")
    else:
        _require(patch["requirement_id"] is not None, "后续更新必须提供 requirement_id。")
        _require("title" not in patch, "后续更新不能修改 title/common。", "/title")
    if patch["requirement_id"] is not None:
        _segment(patch["requirement_id"], "需求编号")
    _require(isinstance(patch["operations"], list), "operations 必须是数组。", "/operations")
    _require(isinstance(patch["set"], dict), "set 必须是点路径字典。", "/set")
    for field in patch["set"]:
        valid = field == "technical_feasibility" or any(field == section + "." + name for section, names in _SET_FIELDS.items() for name in names)
        _require(valid, f"set 不允许修改字段：{field}", "/set")
    aliases = set()
    shapes = {"add": ({"op", "collection", "ref", "value"}, {"prefix"}),
              "add_source": ({"op", "ref", "value"}, set()),
              "update": ({"op", "target", "changes"}, set()),
              "withdraw": ({"op", "target", "reason"}, set())}
    for index, operation in enumerate(patch["operations"]):
        path = f"/operations/{index}"
        _require(isinstance(operation, dict) and isinstance(operation.get("op"), str) and operation["op"] in shapes, "未知或非法操作。", path)
        required_fields, optional = shapes[operation["op"]]
        _require(required_fields <= set(operation) and not (set(operation) - required_fields - optional), "操作字段缺失或含未知字段。", path)
        if operation["op"] in {"add", "add_source"}:
            ref = operation["ref"]
            _require(isinstance(ref, str) and len(ref) > 1 and ref.startswith("$") and not any(c.isspace() or c in "/\\" for c in ref), "新增对象须提供唯一 $别名。", path)
            _require(ref not in aliases, "新增别名重复。", path, ref)
            aliases.add(ref)
            value = operation["value"]
            _require(isinstance(value, dict) and "id" not in value and "source_id" not in value, "新增 value 必须是对象且不能自行填写 id/source_id。", path)
            if operation["op"] == "add":
                collection = operation["collection"]
                _require(isinstance(collection, str) and collection in _COLLECTIONS, "不支持的条目集合。", path)
                if _COLLECTIONS[collection] is None:
                    _require(isinstance(operation.get("prefix"), str) and operation["prefix"] in _SCOPE_PREFIXES, "scope 条目须指定合法 prefix。", path)
                else:
                    _require("prefix" not in operation, "非 scope 条目不能指定 prefix。", path)
        else:
            _require(isinstance(operation["target"], str) and bool(operation["target"]), "操作 target 必须是编号。", path)
            if operation["op"] == "update":
                changes = operation["changes"]
                _require(isinstance(changes, dict) and "id" not in changes and "source_id" not in changes, "changes 必须是对象且不能修改编号。", path)
                _require(changes.get("status") != "withdrawn", "不能用 update 设置 withdrawn；请使用 withdraw。", path)
            else:
                _require(patch["actor"] == "user", "withdraw 必须由用户明示并记录 user_statement。", path)
                _require(isinstance(operation["reason"], str) and operation["reason"].strip(), "withdraw 必须说明 reason。", path)
    checks = patch["completion_checks"]
    _require(isinstance(checks, list) and len(checks) == 11, "completion_checks 必须恰好十一项。", "/completion_checks")
    items = set()
    for index, check in enumerate(checks):
        path = f"/completion_checks/{index}"
        _require(isinstance(check, dict) and set(check) == {"item", "satisfied", "question_refs", "reason"}, "完成清单字段必须为 item/satisfied/question_refs/reason。", path)
        _require(type(check["item"]) is int and 1 <= check["item"] <= 11 and check["item"] not in items, "完成清单编号须为不重复的 1..11。", path)
        items.add(check["item"])
        _require(type(check["satisfied"]) is bool and isinstance(check["reason"], str) and bool(check["reason"].strip()), "完成清单须提供 satisfied 与非空 reason。", path)
        _require(isinstance(check["question_refs"], list) and all(isinstance(ref, str) for ref in check["question_refs"]), "question_refs 必须是引用数组。", path)


def _blank(requirement, project):
    """创建最小规范骨架；分析内容与可选节仅由补丁提供。"""
    return {"schema_version": "1.0", "requirement_id": requirement,
            "meta": {"analysis_revision": 1, "source_revision": 1, "baseline_revision": None,
                     "input_type": "idea", "analysis_status": "analyzing", "readiness": "not_ready"},
            "context": {"project_id": project},
            "requirements": {name.split(".")[-1]: [] for name in _COLLECTIONS if name.startswith("requirements.") and ".scope." not in name},
            "business_assessment": {name.split(".")[-1]: [] for name in _COLLECTIONS if name.startswith("business_assessment.")},
            "ux_assessment": {"ui_dependent": False}, "questions": [], "assumptions": [], "decisions": []}


def _collection(analysis, name):
    """定位规范条目数组，仅在新增时创建缺省的可选数组。"""
    node = analysis
    parts = name.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
        _require(isinstance(node, dict), "条目集合的上级必须是对象。", name)
    if ".scope." in name:
        node.setdefault("in_scope", [])
        node.setdefault("out_of_scope", [])
    entries = node.setdefault(parts[-1], [])
    _require(isinstance(entries, list), "条目集合必须是数组。", name)
    return entries


def _entries(analysis):
    """只遍历规范条目，扩展正文与未知数组不参与编号或传播。"""
    for name in _COLLECTIONS:
        node = analysis
        for part in name.split("."):
            if not isinstance(node, dict) or part not in node:
                node = []
                break
            node = node[part]
        _require(isinstance(node, list), "既有条目集合不是数组。", name)
        for item in node:
            _require(isinstance(item, dict) and isinstance(item.get("id"), str), "既有条目缺少编号。", name)
            yield item


def _resolve_reference(reference, id_map):
    """只在规范引用位置解释完整别名，不替换正文中的文本。"""
    if isinstance(reference, str) and reference.startswith("$"):
        _require(reference in id_map, f"引用了未定义别名：{reference}")
        return id_map[reference]
    return reference


def _resolve_fields(value, id_map):
    """解析条目的关联编号及来源引用，不递归修改未知扩展字段。"""
    value = copy.deepcopy(value)
    if "related_ids" in value and isinstance(value["related_ids"], list):
        value["related_ids"] = [_resolve_reference(ref, id_map) for ref in value["related_ids"]]
    if "related_question" in value:
        value["related_question"] = _resolve_reference(value["related_question"], id_map)
    if isinstance(value.get("sources"), list):
        for source in value["sources"]:
            if isinstance(source, dict) and "source_id" in source:
                source["source_id"] = _resolve_reference(source["source_id"], id_map)
    return value


def _workspace_state(root):
    """读取工作区注册表并验证写入所需容器，未知字段保持原值。"""
    path = _safe(root, "workspace.json")
    state = _load_json(path) if path.exists() else {"projects": [], "requirement_counters": {}}
    _require(isinstance(state, dict), "workspace.json 必须是对象。", str(path))
    projects = state.setdefault("projects", [])
    counters = state.setdefault("requirement_counters", {})
    _require(isinstance(projects, list) and all(isinstance(p, dict) and isinstance(p.get("project_id"), str) for p in projects), "workspace.projects 必须是含 project_id 的对象数组。", str(path))
    _require(isinstance(counters, dict) and all(isinstance(year, str) and type(n) is int and n >= 0 for year, n in counters.items()), "requirement_counters 必须为非负整数映射。", str(path))
    return state


def _scan_requirements(root):
    """扫描整个工作区的目录与标准编号，防止旧计数器导致重号。"""
    found = {}
    maxima = {}
    projects = _safe(root, "projects")
    if not projects.exists():
        return found, maxima
    for project in sorted(projects.iterdir()):
        _safe(root, project.relative_to(root))
        if not project.is_dir():
            continue
        requirements = _safe(root, project.relative_to(root) / "requirements")
        if not requirements.exists():
            continue
        for directory in sorted(requirements.iterdir()):
            _safe(root, directory.relative_to(root))
            if not directory.is_dir():
                continue
            found.setdefault(directory.name, []).append(directory)
            match = re.fullmatch(r"REQ-([0-9]{4})-([0-9]{3,})", directory.name)
            if match:
                year, number = match.groups()
                maxima[year] = max(maxima.get(year, 0), int(number))
    return found, maxima


def _related_documents(related):
    """接受 API 的分析/来源二元组，或 CLI 显式指定的结果路径。"""
    documents = []
    for item in related:
        if isinstance(item, (str, Path)):
            path = Path(item)
            documents.append((_load_json(path), _load_json(path.with_name("source-manifest.json"))))
        else:
            _require(isinstance(item, (tuple, list)) and len(item) == 2, "related_analyses 项须为结果路径或 (analysis, manifest)。")
            documents.append(item)
    return documents


def _apply(analysis, manifest, patch, project):
    """两遍分配与应用别名，再传播撤销；所有变更仅发生于内存副本。"""
    before_entries = {item["id"]: copy.deepcopy(item) for item in _entries(analysis)}
    _require(len(before_entries) == sum(1 for _ in _entries(analysis)), "既有条目编号重复。")
    maxima = {}
    for item_id in [*before_entries, *(item.get("source_id", "") for item in manifest)]:
        match = re.fullmatch(r"([A-Z]+)-([1-9][0-9]*)", item_id)
        if match:
            prefix, number = match.groups()
            maxima[prefix] = max(maxima.get(prefix, 0), int(number))
    id_map = {}
    for operation in patch["operations"]:
        if operation["op"] not in {"add", "add_source"}:
            continue
        prefix = "SRC" if operation["op"] == "add_source" else (_COLLECTIONS[operation["collection"]] or operation["prefix"])
        maxima[prefix] = maxima.get(prefix, 0) + 1
        id_map[operation["ref"]] = f"{prefix}-{maxima[prefix]}"
    new_sources = {id_map[op["ref"]] for op in patch["operations"] if op["op"] == "add_source"}
    # 先加入新增项，确保 update/withdraw 的目标与依赖不受操作顺序影响。
    for operation in patch["operations"]:
        if operation["op"] == "add":
            value = _resolve_fields(operation["value"], id_map)
            value["id"] = id_map[operation["ref"]]
            _collection(analysis, operation["collection"]).append(value)
        elif operation["op"] == "add_source":
            value = copy.deepcopy(operation["value"])
            value["source_id"] = id_map[operation["ref"]]
            manifest.append(value)
    entries = {item["id"]: item for item in _entries(analysis)}
    withdrawn = set()
    updated = set()
    for operation in patch["operations"]:
        if operation["op"] not in {"update", "withdraw"}:
            continue
        target = _resolve_reference(operation["target"], id_map)
        _require(target in entries, f"目标条目不存在：{target}", "/operations", target)
        item = entries[target]
        if operation["op"] == "withdraw":
            _require(not target.startswith("Q-"), "问题使用 update 设置 dropped，不使用 withdraw。", "/operations", target)
            item["status"] = "withdrawn"
            withdrawn.add(target)
            continue
        _require(item.get("status") != "withdrawn", "不能更新或恢复已撤销条目。", "/operations", target)
        changes = _resolve_fields(operation["changes"], id_map)
        if item.get("tag") == "confirmed":
            _require(changes.get("tag", "confirmed") == "confirmed", "不能以推断覆盖 confirmed 标签。", "/operations", target)
            if "content" in changes and changes["content"] != item.get("content"):
                sources = changes.get("sources", item.get("sources", []))
                evidence = isinstance(sources, list) and any(isinstance(source, dict) and
                    ((source.get("type") == "user_answer" and source not in item.get("sources", [])) or
                     (source.get("type") == "input_document" and source.get("source_id") in new_sources)) for source in sources)
                _require(patch["actor"] == "user" and evidence, "修改 confirmed 正文须有用户明示及本轮 user_answer 或新文档来源。", "/operations", target)
        if target.startswith("Q-") and item.get("status") not in {"open", None} and changes.get("status") == "open":
            _require("answer" not in item or changes.get("answer", item["answer"]) == item["answer"], "重开问题必须保留旧 answer。", "/operations", target)
            _require(isinstance(changes.get("reason"), str) and changes["reason"].strip() and changes["reason"] != item.get("reason"), "重开问题必须更新 reason 说明依据变化。", "/operations", target)
        item.update(changes)
        updated.add(target)
    # 普通关联按“被依赖者→依赖者”传播；无向闭包会经共享目标误伤兄弟功能。
    # 问题还接受反向登记（功能指向问题），而邻接表另供依据变化的重开检查使用。
    edges = {item_id: set() for item_id in entries}
    dependents = {item_id: set() for item_id in entries}
    requirement = analysis["requirement_id"]
    for item_id, item in entries.items():
        refs = list(item.get("related_ids", [])) if isinstance(item.get("related_ids", []), list) else []
        if "related_question" in item:
            refs.append(item["related_question"])
        for ref in refs:
            if not isinstance(ref, str):
                continue
            local = ref[len(requirement) + 1:] if ref.startswith(requirement + "/") else ref
            if local in entries:
                edges[item_id].add(local)
                edges[local].add(item_id)
                dependents[local].add(item_id)
                if local.startswith("Q-") and not item_id.startswith("Q-"):
                    dependents[item_id].add(local)
    reached = set(withdrawn)
    frontier = list(withdrawn)
    while frontier:
        current = frontier.pop()
        for dependent in dependents[current] - reached:
            reached.add(dependent)
            frontier.append(dependent)
    for item_id in reached - withdrawn:
        item = entries[item_id]
        if item.get("status") != "withdrawn":
            item["status"] = "dropped" if item_id.startswith("Q-") else "to_reassess"
    # 新版先重开再重评；用户已明确给出新答案的更正不应被强制改回未回答。
    changed_basis = {item_id for item_id in updated if item_id in before_entries
                     and not item_id.startswith("Q-") and patch["change_type"] == "new_source_version"}
    for question_id, old_question in before_entries.items():
        if not question_id.startswith("Q-") or old_question.get("status") in {"open", "dropped"}:
            continue
        if edges[question_id] & changed_basis and entries[question_id].get("status") != "dropped":
            _require(question_id in updated and entries[question_id].get("status") == "open",
                     "关联依据变化的已关闭问题必须显式 update 重开，保留 answer 并解释 reason。", "/operations", question_id)
    for field, value in patch["set"].items():
        if field == "technical_feasibility":
            value = copy.deepcopy(value)
            if isinstance(value, dict):
                if isinstance(value.get("related_questions"), list):
                    value["related_questions"] = [_resolve_reference(ref, id_map) for ref in value["related_questions"]]
                if isinstance(value.get("evidence"), list):
                    value["evidence"] = [_resolve_fields(evidence, id_map) if isinstance(evidence, dict) else evidence for evidence in value["evidence"]]
            analysis[field] = value
        else:
            section, name = field.split(".")
            if field == "context.project_id":
                _require(value == project, "context.project_id 必须与调用参数一致。", "/set")
            if field in {"context.source_ids", "impact_analysis.affected_requirements"} and isinstance(value, list):
                value = [_resolve_reference(ref, id_map) for ref in value]
            analysis.setdefault(section, {})[name] = copy.deepcopy(value)
    analysis.setdefault("context", {})["project_id"] = project
    if patch["change_type"] == "new_source_version":
        _require(bool(new_sources), "新版文档补丁必须新增来源版本。", "/operations")
        for field, value in (("analysis_status", "stale"), ("readiness", "not_ready")):
            _require(patch["set"].get("meta." + field, value) == value, "新版文档首轮必须保存 stale/not_ready，完成重评后另行 supplement。", "/set")
            analysis["meta"][field] = value
        for item_id in updated:
            if item_id in before_entries and not item_id.startswith("Q-"):
                _require(entries[item_id].get("status") in {"to_reassess", "withdrawn"}, "新版文档影响的既有条目必须先待重评。", "/operations", item_id)
    analysis["completion_checks"] = copy.deepcopy(patch["completion_checks"])
    for check in analysis["completion_checks"]:
        check["question_refs"] = [_resolve_reference(ref, id_map) for ref in check["question_refs"]]
    affected = [item_id for item_id, item in entries.items() if before_entries.get(item_id) != item]
    affected += sorted(new_sources, key=lambda source: int(source.split("-")[1]))
    return id_map, affected, before_entries


def _update_locked(root, project, patch, related, dry_run, validate):
    """在已持锁且完成恢复的工作区内执行预检及事务提交。"""
    state = _workspace_state(root)
    found, maxima = _scan_requirements(root)
    counters = state["requirement_counters"]
    for year, maximum in maxima.items():
        counters[year] = max(counters.get(year, 0), maximum)
    requirement = patch["requirement_id"]
    initial = patch["change_type"] == "initial_analysis"
    if requirement is None:
        year = str(datetime.now(timezone.utc).year)
        number = counters.get(year, 0) + 1
        requirement = f"REQ-{year}-{number:03d}"
    base = Path("projects") / project / "requirements" / requirement
    analysis_path = _safe(root, base / "analysis" / "analysis-result.json")
    manifest_path = _safe(root, base / "analysis" / "source-manifest.json")
    common_path = _safe(root, base / "requirement.json")
    event_path = _safe(root, base / "analysis" / "analysis-events.jsonl")
    if initial:
        _require(requirement not in found and not analysis_path.exists() and not common_path.exists(), "需求编号或目录已存在，不能再次首次创建。", str(analysis_path), requirement)
        analysis = _blank(requirement, project)
        manifest = []
        revision = 0
    else:
        _require(analysis_path.exists(), "需求不存在，请先首次分析。", str(analysis_path), requirement)
        analysis, manifest = _load_json(analysis_path), _load_json(manifest_path)
        _require(isinstance(analysis, dict) and isinstance(analysis.get("meta"), dict), "既有分析缺少 meta。", str(analysis_path))
        _require(analysis.get("requirement_id") == requirement, "目录与结果需求编号不一致。", str(analysis_path))
        revision = analysis["meta"].get("analysis_revision")
        _require(type(revision) is int and revision >= 1, "既有 analysis_revision 非法。", str(analysis_path))
        _require(isinstance(manifest, list) and all(isinstance(source, dict) for source in manifest), "既有来源清单格式非法。", str(manifest_path))
        _require(type(analysis["meta"].get("source_revision")) is int and analysis["meta"]["source_revision"] >= 1, "既有 source_revision 非法。", str(analysis_path))
    _require(patch["base_revision"] == revision, f"修订冲突：base_revision={patch['base_revision']}，当前 revision={revision}；请重新读取并分析，不要只修改数字重试。", "/base_revision", requirement)
    if not initial:
        existing = validate(analysis, manifest, related_analyses=related)
        if existing["status"] == "fail":
            return {**existing, "requirement_id": requirement, "revision": revision,
                    "id_map": {}, "affected_ids": [], "written": False}
    original = copy.deepcopy(analysis)
    original_manifest = copy.deepcopy(manifest)
    id_map, affected, before_entries = _apply(analysis, manifest, patch, project)
    analysis["meta"]["analysis_revision"] = revision + 1
    if not initial and manifest != original_manifest:
        analysis["meta"]["source_revision"] += 1
    result = validate(analysis, manifest, related_analyses=related)
    outcome = {**result, "requirement_id": requirement, "revision": revision + 1,
               "id_map": id_map, "affected_ids": affected, "written": False}
    if result["status"] == "fail":
        return outcome
    if result["status"] == "warning":
        _require(analysis["meta"]["analysis_status"] == "stale" and analysis["meta"]["readiness"] == "not_ready", "warning 只允许保存 stale/not_ready 状态。")
    if not any(item["project_id"] == project for item in state["projects"]):
        state["projects"].append({"project_id": project})
    match = re.fullmatch(r"REQ-([0-9]{4})-([0-9]{3,})", requirement)
    if match:
        year, number = match.groups()
        counters[year] = max(counters.get(year, 0), int(number))
    after_entries = {item["id"]: item for item in _entries(analysis)}
    before_sources = {source["source_id"]: source for source in original_manifest}
    after_sources = {source["source_id"]: source for source in manifest}
    before = {item_id: before_entries.get(item_id, before_sources.get(item_id)) for item_id in affected}
    after = {item_id: after_entries.get(item_id, after_sources.get(item_id)) for item_id in affected}
    event = {"time": datetime.now(timezone.utc).isoformat(), "revision": revision + 1,
             "requirement_id": requirement, "change_type": patch["change_type"],
             "summary": patch["summary"], "affected_ids": affected, "actor": patch["actor"],
             "operations": copy.deepcopy(patch["operations"]), "before": before, "after": after,
             "set": copy.deepcopy(patch["set"]),
             "completion_checks": copy.deepcopy(analysis["completion_checks"]),
             "meta_before": original["meta"] if not initial else None,
             "meta_after": analysis["meta"]}
    if "user_statement" in patch:
        event["user_statement"] = patch["user_statement"]
    event_bytes = _read_optional(event_path)
    if event_bytes:
        _require(event_bytes.endswith(b"\n"), "旧事件日志未以换行结束，不能安全追加。", str(event_path))
        for line in event_bytes.splitlines():
            try:
                old_event = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
            except (ValueError, UnicodeError) as error:
                raise _InputError(f"旧事件日志损坏：{error}", str(event_path)) from error
            _require(isinstance(old_event, dict) and type(old_event.get("revision")) is int and old_event["revision"] <= revision, "旧事件日志修订非法或超前。", str(event_path))
    addition = (json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    targets = [(manifest_path, _json_bytes(manifest)), (analysis_path, _json_bytes(analysis))]
    if initial:
        targets.append((common_path, _json_bytes({"common": {"requirement_id": requirement, "project_id": project, "title": patch["title"], "created_at": event["time"]}})))
    targets.extend([(_safe(root, "workspace.json"), _json_bytes(state)), (event_path, (event_bytes or b"") + addition)])
    record = {"version": 1, "project_id": project, "requirement_id": requirement,
              "patch": copy.deepcopy(patch),
              "writes": [{"path": str(path.relative_to(root)), "before": _pack(_read_optional(path)), "after": _pack(content)} for path, content in targets]}
    if dry_run:
        return outcome
    _atomic_write(_safe(root, _JOURNAL), _json_bytes(record))
    _recover(root)
    outcome["written"] = True
    return outcome


def update_analysis(workspace: Path, project_id: str, patch: dict, *, related_analyses=(), dry_run: bool = False) -> dict:
    """以补丁 1.0 创建或增量更新一个需求，不修改输入对象。

    参数：workspace 指定工作区；project_id 是单段项目编号；patch 是完整补丁；
    related_analyses 为显式关联结果路径或 (分析结果, 来源清单) 二元组序列；
    dry_run 为真时仅预检并返回拟分配编号，不提交本补丁。锁内仍会恢复既有待完成事务。
    返回：含 status、diagnostics、requirement_id、revision、id_map、affected_ids、written
    的结果；revision 为本补丁拟保存或已保存的修订号，written 仅在完整提交后为真。
    异常：用户输入、文件、编码、JSON 及协议错误均返回结构化 fail；
    校验器及 Schema 安装缺失或损坏、程序内部错误仍抛出，避免把安装故障误报成业务问题。
    """
    validate = _validator()
    requirement = patch.get("requirement_id") if isinstance(patch, dict) else None
    try:
        _segment(project_id, "项目编号")
        _protocol(patch)
        # API 边界也检查 JSON 可表示性；不接受 NaN、自定义对象或循环容器。
        _json_bytes(patch)
        root = Path(workspace).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        lock_path = _safe(root, _LOCK)
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            recovered = _recover(root)
            if (recovered is not None and recovered.get("project_id") == project_id
                    and recovered.get("patch") == patch and patch["requirement_id"] is None):
                # 自动编号首次保存没有可供调用方重传的编号；恢复后不能再分配第二个需求。
                return _failure(_InputError("已恢复本首次补丁的 revision=1；请读取该需求，再以返回编号与新修订生成后续补丁。", "/base_revision"),
                                recovered["requirement_id"], 1)
            related = _related_documents(related_analyses)
            return _update_locked(root, project_id, copy.deepcopy(patch), related, dry_run, validate)
    except (_InputError, OSError, UnicodeError, ValueError, TypeError, RecursionError) as error:
        return _failure(error, requirement)


class _Parser(argparse.ArgumentParser):
    """把命令行用法错误也纳入 JSON 诊断。"""

    def error(self, message):
        raise _InputError(f"命令行参数错误：{message}")


def main(argv=None) -> int:
    """运行增量更新命令行并打印唯一 JSON 结果。

    参数：argv 为命令行参数序列，省略时读取进程参数。
    返回：pass=0、warning=1、fail=2；dry-run 不改变状态码语义。
    异常：用户文件、编码、JSON、参数与协议错误转为结构化 fail；
    校验器或 Schema 的安装故障可抛出；--help 按 argparse 惯例退出。
    """
    parser = _Parser(description="校验并以可恢复事务应用需求分析补丁 1.0。")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--project", required=True)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--related-analysis", type=Path, action="append", default=[])
    try:
        args = parser.parse_args(argv)
        patch = _load_json(args.patch)
        result = update_analysis(args.workspace, args.project, patch,
                                 related_analyses=args.related_analysis, dry_run=args.dry_run)
    except (_InputError, OSError, UnicodeError, ValueError) as error:
        result = _failure(error)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return _EXIT_CODES[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

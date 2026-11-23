"""只读校验 PRD 格式、正文定位、分析追溯、缺口及快照；不执行生成、同步或发布。"""

import argparse
from collections import Counter
from collections.abc import Sequence
from functools import lru_cache
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator


SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
ANALYST = Path(__file__).resolve().parents[2] / "requirement-analyst/scripts/validate_analysis.py"
EXIT_CODES = {"pass": 0, "warning": 1, "fail": 2}
KINDS = dict(zip(("goal", "scenario", "functional_requirement", "business_rule", "constraint", "non_functional_requirement", "acceptance_criterion", "flow", "state", "boundary", "exception"), ("GOAL", "SCN", "FR", "BR", "CON", "NFR", "AC", "FLOW", "STATE", "BND", "EXC")))
KIND_SECTIONS = dict(zip(KINDS, ("scope", "scenarios", "functional_requirements", "business_rules", "constraints", "constraints", "acceptance_criteria", "flows_states", "flows_states", "boundaries_exceptions", "boundaries_exceptions")))
PROMPTS = {
    "risk_draft": "本文档基于未就绪的需求分析生成，存在未解决的阻塞问题，仅供沟通，不得作为开发或测试依据。",
    "conditional_draft": "本文档存在待回答的问题和暂定假设，见“遗留事项”。",
    "stale_draft": "本文档基于已过期的分析结果生成，内容可能与最新需求不符。",
    "formal_draft": "草稿，待产品经理确认后发布。",
}
SECTION_KEYS = ("info", "changes", "background", "scope", "glossary", "scenarios", "functional_requirements", "business_rules", "flows_states", "boundaries_exceptions", "constraints", "acceptance_criteria", "ux", "technical", "impact", "residuals", "appendix")
REQUIRED_SECTIONS = ("info", "changes", "scope", "scenarios", "functional_requirements", "business_rules", "boundaries_exceptions", "acceptance_criteria", "residuals", "appendix")
PRD_ID = re.compile(r"\bPRD-(?:GOAL|SCN|FR|BR|CON|NFR|AC|FLOW|STATE|BND|EXC)-\d{3,}\b")
MARKER = re.compile(r"<!--\s*(/?)prd:(section|item|gap|residual)(?:\s+([^<>]*?))?\s*-->")
VERSION = re.compile(r"^(?:0\.[1-9][0-9]*|[1-9][0-9]*\.(?:0|[1-9][0-9]*)(?:-draft)?)$")
HASH = re.compile(r"^sha256:[0-9a-f]{64}$")


def _issue(rule, item_id, path, message, level="fail"):
    """构造包含规则和定位的诊断，不修改任何业务数据。"""
    return {"rule": rule, "level": level, "item_id": str(item_id), "path": str(path), "message": message}


def _result(diagnostics):
    """失败优先于警告，返回稳定排序的完整诊断。"""
    status = "fail" if any(d["level"] == "fail" for d in diagnostics) else "warning" if diagnostics else "pass"
    return {"status": status, "diagnostics": sorted(diagnostics, key=lambda d: (d["rule"], d["path"], d["item_id"], d["message"]))}


def _unique(pairs):
    """拒绝 JSON 重复键，避免不同读取方看到不同内容。"""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON 包含重复字段：{key}")
        result[key] = value
    return result


def _constant(value):
    """拒绝 JSON 的非有限数值，保持摘要算法确定性。"""
    raise ValueError(f"JSON 包含非法数值：{value}")


@lru_cache(maxsize=1)
def _fs():
    """从本 Skill 的固定路径加载文件系统适配器，不依赖 cwd 或模块搜索路径。"""
    path = Path(__file__).resolve().with_name("_load_fs.py")
    spec = importlib.util.spec_from_file_location("prd_validation_fs_loader", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fs


def _has_link(path):
    """检查文件及祖先是否经由链接，包括相对路径的工作目录。"""
    path = path.absolute()
    return any(_fs().is_link(part) for part in (path, *path.parents))


def _read_bytes(path, *, link_message="不读取符号链接路径"):
    """拒绝通过链接读取路径，返回不转换换行的文件原字节。"""
    if _has_link(path):
        raise ValueError(link_message)
    with os.fdopen(_fs().open_readonly(path), "rb") as stream:
        return stream.read()


def _decode_json(raw):
    """解析 UTF-8 JSON，拒绝重复键与非法数值。"""
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant)


def _json(path):
    """严格读取 UTF-8 JSON，解析异常由调用边界处理。"""
    return _decode_json(_read_bytes(path))


def _sha(data):
    """摘要以原始字节计算，不忽略快照或正文的排版变化。"""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def source_digest(analysis_refs: Sequence[str], registry: dict) -> str:
    """计算正式条目的稳定生成依据摘要，返回带 sha256 前缀的字符串。

    analysis_refs 为完整分析引用，registry 为引用到完整条目的只读映射。
    引用不存在抛出 KeyError；无法序列化或含非有限数值抛出 TypeError/ValueError。
    对象键和外部 JSON 排版不影响结果，条目内部数组顺序保留。
    """
    data = [{"analysis_ref": ref, "item": registry[ref]} for ref in sorted(analysis_refs)]
    return _sha(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"))


def section_source_digests(analysis: dict, gaps: dict, *, trace: dict | None = None,
                           source_manifest=None, related_analyses=(), legacy_layout: bool = False) -> dict:
    """返回各业务章节生成时完整依据的稳定摘要，不读取或修改文件。

    analysis/gaps为当前权威分析及缺口候选；trace仅用于定位实际跨来源映射，
    source_manifest为可用来源名称清单，related_analyses仅为显式关联分析。
    legacy_layout用于比较术语仍归附录的旧稿，复现旧附录摘要且不创建术语摘要。
    信息及事件章节由脚本渲染，不参与比较；缺数据、引用或非法JSON值抛出KeyError/TypeError/ValueError。
    摘要相等只证明所记录依据未变，不证明自然语言表达充分或忠实。
    """
    req, business = analysis['requirements'], analysis['business_assessment']
    questions = analysis['questions']
    context = analysis.get('context', {})
    inferred = [item for _, item in _analyst()._entries(analysis) if item.get('tag') == 'inferred' and item.get('status') != 'withdrawn']
    # 上游允许省略可选集合；缺省与空集合不提供生成依据，也不应换掉已有空章节摘要。
    data = {
        'background': analysis.get('value_assessment'),
        'scope': {'goals': req['goals'], 'scope': req.get('scope', {'in_scope': [], 'out_of_scope': []}),
                  'excluded': [q for q in questions if q['status'] == 'excluded'], 'decisions': analysis['decisions']},
        'glossary': context.get('domain_terms', []),
        'scenarios': req['scenarios'], 'functional_requirements': req['functional_requirements'],
        'business_rules': req['business_rules'], 'flows_states': {key: business.get(key, []) for key in ('flows', 'states')},
        'boundaries_exceptions': {key: business[key] for key in ('boundaries', 'exceptions')},
        'constraints': {key: req.get(key, []) for key in ('constraints', 'non_functional_requirements')},
        'acceptance_criteria': req['acceptance_criteria'], 'ux': analysis.get('ux_assessment'),
        'technical': {'assessment': analysis.get('technical_feasibility'), 'ask_dev': [q for q in questions if q['resolution'] == 'ask_dev']},
        'impact': analysis.get('impact_analysis'),
        'residuals': {'questions': questions, 'assumptions': analysis['assumptions'], 'decisions': analysis['decisions'],
                      'gaps': business['gaps'], 'conflicts': business['conflicts'], 'inferred': inferred,
                      'design_pending_items': analysis.get('ux_assessment', {}).get('design_pending_items', [])},
        'appendix': {'source_ids': context.get('source_ids', []), 'sources': [item.get('sources', []) for _, item in _analyst()._entries(analysis)], 'manifest': source_manifest},
    }
    if legacy_layout:
        # 用原载荷核验旧摘要，而不是重写旧稿或跳过旧附录的来源校验。
        del data['glossary']
        del data['appendix']['source_ids']
        data['appendix']['context'] = analysis.get('context')
    labels = dict(zip(SECTION_KEYS[2:], ('背景与价值', '目标与范围', '术语', '用户与场景', '功能需求', '业务规则', '流程与状态', '边界与异常', '约束与非功能需求', '验收条件', '界面与交互', '技术说明与研发确认项', '关联与影响', '遗留事项', '附录')))
    registry, _ = _registry((analysis, *related_analyses))
    # open与handed_over的占位语义相同；分析侧允许单独标记接收，不让它造成已同步正文依据失配。
    requests = [{**gap, 'status': 'closed' if gap['status'] == 'closed' else 'unresolved'} for gap in gaps['requests']]
    result = {}
    for key, value in data.items():
        mapped = sorted({ref for item in (trace or {}).get('items', []) if KIND_SECTIONS.get(item['kind']) == key for ref in item['analysis_refs']})
        payload = {'analysis': value, 'mapped_sources': [{'analysis_ref': ref, 'item': registry[ref]} for ref in mapped],
                   'gap_requests': requests if key == 'residuals' else [gap for gap in requests if gap['needed_for'] in (key, labels[key])]}
        # 验收挂靠功能章节时，其依据变化也必须开放对应章节；不是凭模型推断新的挂靠。
        if key == 'functional_requirements':
            payload['attached_acceptance'] = [item for item in req['acceptance_criteria'] if item.get('related_ids')]
        result[key] = _sha(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8'))
    return result


@lru_cache(maxsize=1)
def _analyst():
    """加载并列安装的唯一分析校验器；损坏安装直接抛出，不复制其业务规则。"""
    spec = importlib.util.spec_from_file_location("prd_upstream_validator", ANALYST)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=None)
def _schema(name):
    """读取本安装的 Schema；安装错误应明确报错而非降级为数据通过。"""
    schema = _json(SCHEMA_DIR / f"{name}.schema.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _structure(data, name, diagnostics, rule=1, path=""):
    """结构错误就地诊断，并阻止不满足结构前提的深层遍历。"""
    errors = list(_schema(name).iter_errors(data))
    for error in errors:
        node = data
        item_id = "$"
        for part in error.absolute_path:
            if isinstance(node, dict):
                item_id = node.get("prd_id", node.get("id", item_id))
            node = node[part]
        if isinstance(node, dict):
            item_id = node.get("prd_id", node.get("id", item_id))
        location = "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in error.absolute_path)
        diagnostics.append(_issue(rule, item_id, path + "/" + location, f"格式错误：{error.message}"))
    return not errors


def _read(path, diagnostics, rule, *, optional=False):
    """将用户文件读取失败转为诊断；缺省的可选资料由上层按 source_id 降级。"""
    try:
        value = _json(path)
        if value is None:
            raise ValueError("必需 JSON 文档不能为 null")
        return value
    except (OSError, ValueError, UnicodeError) as error:
        if not optional:
            diagnostics.append(_issue(rule, "$", path, f"无法读取 JSON：{error}"))
        return None


def _registry(documents):
    """仅索引已验证的显式分析输入，不扫描工作区或把任意扩展误当条目。"""
    registry = {}
    paths = {}
    for analysis in documents:
        rid = analysis["requirement_id"]
        for path, item in _analyst()._entries(analysis):
            ref = f"{rid}/{item['id']}"
            registry[ref] = item
            paths[ref] = path
    return registry, paths


def _blocks(text, diagnostics):
    """解析定位块并拒绝交叉、重复和非法嵌套，记录正文范围用于条目内检查。"""
    stack = []
    blocks = {name: {} for name in ("section", "item", "gap", "residual")}
    for match in MARKER.finditer(text):
        closing, kind, key = match.groups()
        key = (key or "").strip()
        if closing:
            if key or not stack or stack[-1][0] != kind:
                diagnostics.append(_issue(4, key or "$", f"prd.md:{match.start()}", "定位块闭合不匹配或交叉。"))
                continue
            opened_kind, opened_key, begin, section = stack.pop()
            blocks[kind][opened_key] = {"text": text[begin:match.start()], "section": section, "start": begin, "end": match.start()}
        else:
            valid_parent = not stack if kind == "section" else len(stack) == 1 and stack[0][0] == "section"
            if not key or not valid_parent or key in blocks[kind] or any(k == kind and v == key for k, v, *_ in stack):
                diagnostics.append(_issue(4, key or "$", f"prd.md:{match.start()}", "定位块缺少身份、重复或嵌套不合法。"))
                continue
            section = key if kind == "section" else stack[0][1]
            stack.append((kind, key, match.end(), section))
    for kind, key, *_ in stack:
        diagnostics.append(_issue(4, key, "prd.md", f"{kind} 定位块未闭合。"))
    # 正则只认约定标记；不能让拼错标记静默消失。
    if len(re.findall(r"<!--\s*/?prd:", text)) != len(list(MARKER.finditer(text))):
        diagnostics.append(_issue(4, "$", "prd.md", "存在无法识别的 PRD 定位标记。"))
    for key in REQUIRED_SECTIONS:
        if key not in blocks["section"]:
            diagnostics.append(_issue(4, "$", "prd.md", f"缺少必有章节：{key}。"))
    for key in blocks["section"]:
        if key not in SECTION_KEYS:
            diagnostics.append(_issue(4, "$", "prd.md", f"未知章节键：{key}。"))
    ordered = sorted(blocks["section"], key=lambda key: blocks["section"][key]["start"])
    if ordered[:2] != ["info", "changes"]:
        diagnostics.append(_issue(4, "$", "prd.md", "文首章节必须先文档信息再变更记录。"))
    return blocks


INCONSISTENCY = "【与分析不一致】"
CONTENT_SECTIONS = set(SECTION_KEYS) - {"info", "changes", "residuals"}


def manual_inconsistencies(text: str, requirement_id: str) -> dict[str, str]:
    """提取正文中手工不一致的目标及其原始内容，不返回遗留项。

    text 是完整 Markdown，requirement_id 是本需求编号；返回完整目标引用到原文的映射。
    定位块非法或正文标注无法归属有效条目、内容章节时抛出 ValueError。
    条目内标注只属于条目，不传播到所在章节；此函数不判断差异的语义。
    """
    diagnostics = []
    blocks = _blocks(text, diagnostics)
    if diagnostics:
        raise ValueError("；".join(issue["message"] for issue in diagnostics))
    result = {}
    comments = [(match.start(), match.end()) for match in re.finditer(r"<!--[\s\S]*?-->", text)]
    for match in re.finditer(re.escape(INCONSISTENCY), text):
        pos = match.start()
        if any(start <= pos < end for start, end in comments):
            raise ValueError("不一致标注必须位于可见正文，不得藏在注释中")
        containing = [(kind, key, block) for kind in ("item", "gap", "residual")
                      for key, block in blocks[kind].items() if block["start"] <= pos < block["end"]]
        section = next((key for key, block in blocks["section"].items()
                        if block["start"] <= pos < block["end"]), None)
        if containing:
            kind, key, block = containing[0]
            if kind == "residual":
                continue
            if kind != "item" or section not in CONTENT_SECTIONS or not PRD_ID.fullmatch(key):
                raise ValueError(f"不一致标注不能定位有效正文条目：{key}")
            result[f"{requirement_id}/{key}"] = block["text"]
        elif section in CONTENT_SECTIONS:
            result[f"{requirement_id}/prd/sections/{section}"] = blocks["section"][section]["text"]
        else:
            raise ValueError("不一致标注不在可定位的正文内容中")
    return result


def _manual_checks(text, rid, blocks, diagnostics, released):
    """核对手工不一致的目标及遗留项配对；仅检查可见字符串，不代替语义评审。"""
    try:
        targets = manual_inconsistencies(text, rid)
    except ValueError as error:
        diagnostics.append(_issue(8, "$", "prd.md", str(error)))
        targets = {}
    prefix = rid + "/"
    residuals = {}
    for ref, block in blocks["residual"].items():
        # PRD 命名空间的引用即使拼错或指向外部需求也不能落入旧分析遗留项分支。
        manual_ref = bool(re.search(r"/(?:PRD-|prd/)", ref))
        if not manual_ref:
            if INCONSISTENCY in block["text"]:
                diagnostics.append(_issue(8, ref, "prd.md/residuals", "不一致遗留项必须引用本需求的 PRD 正文目标。"))
            continue
        residuals[ref] = block
        suffix = ref[len(prefix):] if ref.startswith(prefix) else ""
        valid = bool(PRD_ID.fullmatch(suffix)) or (suffix.startswith("prd/sections/") and suffix[len("prd/sections/"):] in CONTENT_SECTIONS)
        if not valid or ref not in targets:
            diagnostics.append(_issue(8, ref, "prd.md/residuals", "手工不一致引用无有效且已标注的本需求正文目标。"))
        visible = re.sub(r"<!--.*?-->", "", block["text"], flags=re.S)
        # 要求有实际说明和回交分析措辞；字符串检查不能证明说明的业务充分性。
        remainder = visible.replace(INCONSISTENCY, "")
        # 短距离只用于识别交接说明，避免跨多段拼出措辞；20字不是语义充分性阈值。
        handover = re.search(r"(?:回交|转回|交回|反馈|提交).{0,20}分析|分析.{0,20}(?:回交|转回|交回|反馈|提交)", remainder, re.S)
        if handover:
            remainder = remainder[:handover.start()] + remainder[handover.end():]
        remainder = re.sub(r"差异|说明|建议|处理|事项|确认|[:：\s|，,。；;、*#\-]", "", remainder)
        if block["section"] != "residuals" or INCONSISTENCY not in visible or not handover or not remainder:
            diagnostics.append(_issue(8, ref, "prd.md/residuals", "不一致遗留项须位于遗留章节，含标注、非空差异和回交分析说明。"))
    for ref in targets:
        if ref not in residuals:
            diagnostics.append(_issue(8, ref, "prd.md", "不一致正文缺少对应遗留项。"))
        elif released:
            diagnostics.append(_issue(8, ref, "prd.md", "已发布正文含与分析不一致标注，不得发布。"))
        else:
            diagnostics.append(_issue(8, ref, "prd.md", "存在与分析不一致的内容，不得发布。", "warning"))
    if released and INCONSISTENCY in text and not targets:
        diagnostics.append(_issue(8, "$", "prd.md", "已发布正文含与分析不一致标注，不得发布。"))


def _events(path, diagnostics):
    """读取追加日志并检查公共字段；单行坏 JSON 不覆盖其他可诊断事件。"""
    try:
        lines = _read_bytes(path, link_message="事件文件不允许符号链接").decode("utf-8").splitlines()
    except (OSError, ValueError, UnicodeError) as error:
        diagnostics.append(_issue(1, "$", path, f"无法读取事件日志：{error}"))
        return []
    result = []
    types = {"initial_generation", "sync", "layout_edit", "manual_edit_detected", "gap_request", "submit_review", "return_review", "release_confirmed", "release", "deprecate"}
    for index, line in enumerate(lines, 1):
        try:
            event = json.loads(line, object_pairs_hook=_unique, parse_constant=_constant)
            if not isinstance(event, dict):
                raise ValueError("事件必须为对象")
            if not all(key in event for key in ("time", "prd_version", "change_type", "summary", "affected_prd_ids", "based_on_analysis_revision", "actor")):
                raise ValueError("事件缺少必填字段")
            if event["change_type"] not in types or event["actor"] not in {"user", "prd_generator"}:
                raise ValueError("事件类型或执行者不合法")
            if not isinstance(event["prd_version"], str) or not VERSION.fullmatch(event["prd_version"]):
                raise ValueError("事件版本不合法")
            if not isinstance(event["time"], str) or not event["time"].strip() or not isinstance(event["summary"], str) or not event["summary"].strip():
                raise ValueError("事件时间及说明必须非空")
            if type(event["based_on_analysis_revision"]) is not int or event["based_on_analysis_revision"] < 1:
                raise ValueError("事件分析修订号不合法")
            if not isinstance(event["affected_prd_ids"], list) or any(not isinstance(v, str) or not PRD_ID.fullmatch(v) for v in event["affected_prd_ids"]):
                raise ValueError("受影响编号集合不合法")
            if event["change_type"] == "release_confirmed" and (not isinstance(event.get("confirmed_by"), str) or not event["confirmed_by"].strip()):
                raise ValueError("发布确认事件缺少确认人")
            result.append(event)
        except (ValueError, TypeError) as error:
            diagnostics.append(_issue(1, "$", f"{path}:{index}", f"事件格式错误：{error}"))
    return result


def _history(trace, previous, diagnostics, label):
    """核对显式历史的编号身份和计数器；不从单份文件猜测旧编号。"""
    if not _structure(previous, "prd-trace", diagnostics, 2, label):
        return
    if previous["requirement_id"] != trace["requirement_id"]:
        diagnostics.append(_issue(2, "$", label, "历史追溯属于其他需求。"))
        return
    current = {item["prd_id"]: item for item in trace["items"]}
    for old in previous["items"]:
        new = current.get(old["prd_id"])
        if new is None:
            diagnostics.append(_issue(2, old["prd_id"], label, "历史正式编号被删除。"))
            continue
        # 旧1.0追溯允许没有mapping_key；显式按既有编号补键不改变身份，已有键仍不可重置。
        key_changed = "mapping_key" in old and old["mapping_key"] != new.get("mapping_key")
        if old["kind"] != new["kind"] or old["introduced_in"] != new["introduced_in"] or key_changed or (old["status"] == "abolished" and new["status"] != "abolished"):
            diagnostics.append(_issue(2, old["prd_id"], label, "历史编号身份、引入版本或废止状态被重置。"))
    for prefix, number in previous["meta"]["counters"].items():
        if trace["meta"]["counters"].get(prefix, 0) < number:
            diagnostics.append(_issue(2, "$", label, f"{prefix} 计数器低于历史高水位。"))
    old_ids = {item["prd_id"] for item in previous["items"]}
    for item in trace["items"]:
        _, prefix, number = item["prd_id"].split("-")
        if item["prd_id"] not in old_ids and int(number) <= previous["meta"]["counters"].get(prefix, 0):
            diagnostics.append(_issue(2, item["prd_id"], label, "新编号复用了历史高水位以内的序号。"))


def _snapshots(prd, trace, events, diagnostics):
    """验证发布记录与文件双向覆盖、固定路径及两份原始摘要，并返回历史追溯。"""
    registered = set()
    releases = set()
    history = []
    for event in events:
        if event["change_type"] != "release":
            continue
        version = event["prd_version"]
        if version in releases or version.startswith("0.") or version.endswith("-draft"):
            diagnostics.append(_issue(11, "$", "prd-events.jsonl", "重复或非正式版本的发布记录。"))
        releases.add(version)
        snapshots = event.get("snapshots")
        if not isinstance(snapshots, dict) or set(snapshots) != {"prd", "trace"}:
            diagnostics.append(_issue(11, "$", "prd-events.jsonl", "发布记录缺少两份快照摘要。"))
            continue
        for kind, filename in (("prd", f"versions/prd-{version}.md"), ("trace", f"versions/prd-trace-{version}.json")):
            record = snapshots[kind]
            if not isinstance(record, dict) or record.get("path") != filename or not isinstance(record.get("sha256"), str) or not HASH.fullmatch(record["sha256"]):
                diagnostics.append(_issue(11, "$", "prd-events.jsonl", "快照路径或摘要格式不合法。"))
                continue
            registered.add(filename)
            path = prd / filename
            try:
                content = _read_bytes(path, link_message="快照不得为符号链接")
                if _sha(content) != record["sha256"]:
                    raise ValueError("快照摘要不符")
                if kind == "trace":
                    historical = _decode_json(content)
                    history.append((historical, filename))
            except (OSError, ValueError, UnicodeError) as error:
                diagnostics.append(_issue(11, "$", filename, str(error)))
    versions = prd / "versions"
    try:
        if _has_link(versions):
            diagnostics.append(_issue(11, "$", versions, "快照目录不得为符号链接。"))
        elif versions.exists():
            if not versions.is_dir():
                diagnostics.append(_issue(11, "$", versions, "快照位置必须是目录。"))
            else:
                for path in versions.iterdir():
                    relative = "versions/" + path.name
                    if relative not in registered or _fs().is_link(path) or not path.is_file():
                        diagnostics.append(_issue(11, "$", relative, "快照无对应发布记录或类型不合法。"))
    except OSError as error:
        diagnostics.append(_issue(11, "$", versions, f"无法检查快照目录：{error}"))
    if trace is not None:
        for previous, label in history:
            _history(trace, previous, diagnostics, label)


def _trace_checks(trace, registry, paths, blocks, text, diagnostics, pending):
    """校验编号、引用和正文身份，并仅在已同步时强制当前生成摘要相符。"""
    items = trace["items"]
    counts = Counter(item["prd_id"] for item in items)
    numeric_ids = Counter((item["prd_id"].split("-")[1], int(item["prd_id"].split("-")[2])) for item in items)
    keys = Counter(item["mapping_key"] for item in items if "mapping_key" in item)
    for key, count in keys.items():
        if count > 1:
            diagnostics.append(_issue(2, key, "prd-trace.json/items", "稳定映射键重复。"))
    by_id = {item["prd_id"]: item for item in items}
    for item in items:
        pid = item["prd_id"]
        _, prefix, number = pid.split("-")
        if counts[pid] != 1 or numeric_ids[(prefix, int(number))] != 1 or trace["meta"]["counters"].get(prefix, 0) < int(number) or KINDS[item["kind"]] != prefix:
            diagnostics.append(_issue(2, pid, "prd-trace.json/items", "编号重复、类别前缀不匹配或计数器落后。"))
        refs = item["analysis_refs"]
        values = [registry[ref] for ref in refs if ref in registry]
        if len(values) != len(refs):
            diagnostics.append(_issue(3, pid, "prd-trace.json/items/analysis_refs", "引用不存在或未显式提供关联分析。"))
        if any(value.get("status") == "withdrawn" for value in values) and item["status"] != "abolished":
            diagnostics.append(_issue(3, pid, "prd-trace.json/items/status", "引用已撤销来源的条目必须废止。"))
        if values and len(values) == len(refs) and pending and item["source_digest"] != source_digest(refs, registry):
            diagnostics.append(_issue(3, pid, "prd-trace.json/items/source_digest", "待同步的生成依据已变化：" + ", ".join(refs), "warning"))
        if values and len(values) == len(refs) and item["status"] != "abolished" and not pending:
            ranks = {"assumption": 0, "inferred": 1, "confirmed": 2}
            expected_tag = min((value.get("tag", "confirmed") for value in values), key=ranks.get)
            if item["tag"] != expected_tag:
                diagnostics.append(_issue(5, pid, "prd-trace.json/items/tag", "追溯标签未保留最不确定来源语义。"))
            if any(value.get("status") == "to_reassess" for value in values) and item["status"] != "to_confirm":
                diagnostics.append(_issue(5, pid, "prd-trace.json/items/status", "待重评来源必须保持待确认状态。"))
            if item["source_digest"] != source_digest(refs, registry):
                diagnostics.append(_issue(3, pid, "prd-trace.json/items/source_digest", "已同步条目的生成依据摘要与当前完整来源不符。"))
        content = blocks["item"].get(pid)
        if item["status"] == "abolished":
            if content and content["section"] != "changes":
                diagnostics.append(_issue(6, pid, "prd.md", "已废止条目进入有效章节。"))
        elif not content or content["section"] in {"info", "changes", "residuals", "appendix"}:
            diagnostics.append(_issue(4, pid, "prd.md", "有效条目缺少需求正文中的定位块。"))
        if content and item["status"] != "abolished":
            expected_section = KIND_SECTIONS[item['kind']]
            attached = False
            if item['kind'] == 'acceptance_criterion' and content['section'] == 'functional_requirements':
                linked = {ref.rsplit('/', 1)[0] + '/' + related if '/' not in related else related
                          for ref in refs if ref in registry for related in registry[ref].get('related_ids', [])}
                attached = any(candidate['kind'] == 'functional_requirement' and candidate['status'] != 'abolished'
                               and linked.intersection(candidate['analysis_refs'])
                               and blocks['item'].get(candidate['prd_id'], {}).get('section') == 'functional_requirements' for candidate in items)
            if content['section'] != expected_section and not attached:
                diagnostics.append(_issue(4, pid, 'prd.md', f'条目种类应位于稳定章节{expected_section}，验收仅可按显式关联挂靠功能。'))
            visible = re.sub(r"<!--[\s\S]*?-->", "", content["text"])
            if pid not in PRD_ID.findall(visible):
                diagnostics.append(_issue(4, pid, "prd.md", "条目的可见正文缺少正式编号，隐藏标记不能代替。"))
            for needed, condition in (("【推断】", item["tag"] == "inferred"), ("【暂定】", item["tag"] == "assumption"), ("【待确认】", item["status"] == "to_confirm")):
                if condition and needed not in visible:
                    diagnostics.append(_issue(5, pid, "prd.md", f"条目内缺少 {needed}。"))
            if item["kind"] in {"functional_requirement", "acceptance_criterion"} and any(ref not in visible for ref in refs):
                diagnostics.append(_issue(4, pid, "prd.md", "功能或验收条目未显示完整分析来源。"))
    for pid, content in blocks["item"].items():
        if pid not in by_id:
            diagnostics.append(_issue(4, pid, "prd.md", "正文定位编号未登记追溯。"))
    for match in PRD_ID.finditer(text):
        pid = match.group()
        if pid not in by_id:
            diagnostics.append(_issue(4, pid, "prd.md", "正文正式编号未登记追溯。"))
        elif by_id[pid]["status"] == "abolished":
            changes = blocks["section"].get("changes")
            if not changes or not changes["start"] <= match.start() < changes["end"]:
                diagnostics.append(_issue(6, pid, "prd.md", "废止编号只允许在变更记录出现。"))


def _residuals(analysis, registry, blocks, diagnostics):
    """按分析状态计算必列遗留引用；只核对存在与定位，不伪称语义充分性已证明。"""
    rid = analysis["requirement_id"]
    required = set()
    for question in analysis["questions"]:
        if (question["status"] == "open" and question["priority"] in {"P0", "P1"}) or question["status"] in {"provisional", "risk_accepted"} or (question["resolution"] == "ask_dev" and question["status"] not in {"answered", "dropped", "excluded"}):
            required.add(f"{rid}/{question['id']}")
            for collection in ("assumptions", "decisions"):
                for item in analysis[collection]:
                    if item.get("related_question") == question["id"] and item["status"] != "withdrawn":
                        required.add(f"{rid}/{item['id']}")
    for ref, item in registry.items():
        if not ref.startswith(rid + "/") or item.get("status") == "withdrawn":
            continue
        if item.get("tag") == "inferred" or ref.split("/")[-1].startswith(("GAP-", "CNF-")):
            # 已解决的矛盾由关联问题状态判断，不能把所有历史矛盾永远列作未处理。
            linked = [registry.get(f"{rid}/{q}") for q in item.get("related_ids", []) if q.startswith("Q-")]
            if ref.split("/")[-1].startswith(("GAP-", "CNF-")) and linked and all(q and q.get("status") not in {"open", "provisional"} for q in linked):
                continue
            required.add(ref)
    for index, value in enumerate(analysis["ux_assessment"].get("design_pending_items", [])):
        required.add(f"/ux_assessment/design_pending_items/{index}")
    for ref in required:
        block = blocks["residual"].get(ref)
        if not block or block["section"] != "residuals" or not block["text"].strip():
            diagnostics.append(_issue(8, ref, "prd.md/residuals", "缺少应列遗留项或该项未在遗留章节中定位。"))
    for ref, content in blocks["residual"].items():
        if re.search(r"/(?:PRD-|prd/)", ref):
            continue  # 手工不一致引用由配对检查处理，不冒充分析条目。
        if ref.startswith("/ux_assessment/design_pending_items/"):
            tail = ref.rsplit("/", 1)[-1]
            values = analysis["ux_assessment"].get("design_pending_items", [])
            valid = tail.isdigit() and int(tail) < len(values)
        else:
            valid = ref in registry
        if not valid:
            diagnostics.append(_issue(8, ref, "prd.md/residuals", "遗留项依据不存在。"))


def _gaps(gaps, analysis, registry, paths, blocks, text, diagnostics):
    """核对缺口、接收问题、依据和占位，交接完成不等于问题已解决。"""
    requests = gaps["requests"]
    counts = Counter(item["id"] for item in requests)
    receivers = {}
    for question in analysis["questions"]:
        if "gap_request_ref" in question:
            ref = question["gap_request_ref"]
            if not isinstance(ref, str) or not re.fullmatch(r"GAPREQ-[1-9][0-9]*", ref):
                diagnostics.append(_issue(12, question["id"], "analysis/questions", "缺口接收引用格式不合法。"))
                continue
            receivers.setdefault(ref, []).append(question)
    if gaps["counters"]["GAPREQ"] < max((int(item["id"].split("-")[1]) for item in requests), default=0):
        diagnostics.append(_issue(12, "$", "gap-requests.json/counters", "缺口计数器低于已分配序号。"))
    for gap in requests:
        gid = gap["id"]
        questions = receivers.get(gid, [])
        if counts[gid] != 1:
            diagnostics.append(_issue(12, gid, "gap-requests.json", "缺口编号重复。"))
        if len(questions) > 1 or (gap["status"] != "open" and len(questions) != 1):
            diagnostics.append(_issue(12, gid, "gap-requests.json/status", "缺口没有唯一接收问题。"))
        for ref in gap["related_analysis_refs"]:
            if ref not in registry:
                diagnostics.append(_issue(12, gid, "gap-requests.json/related_analysis_refs", f"缺口引用不存在：{ref}。"))
        placeholder = blocks["gap"].get(gid)
        if gap["status"] != "closed":
            if not placeholder or "待分析补充" not in placeholder["text"]:
                diagnostics.append(_issue(9, gid, "prd.md", "未关闭缺口缺少唯一待分析补充占位。"))
            if gap["status"] == "open":
                diagnostics.append(_issue(12, gid, "gap-requests.json/status", "缺口仍待交接或确认。", "warning"))
        else:
            if placeholder:
                diagnostics.append(_issue(9, gid, "prd.md", "已关闭缺口仍有占位。"))
            if questions and questions[0]["status"] == "open":
                diagnostics.append(_issue(12, gid, "gap-requests.json/status", "接收问题仍 open，不能关闭缺口。"))
            resolution = gap["resolution"]
            for ref in resolution["analysis_refs"]:
                item = registry.get(ref)
                if not item or item.get("status") != "active" or not item.get("content", "").strip():
                    diagnostics.append(_issue(12, gid, "gap-requests.json/resolution", "关闭依据不存在、不是有效内容或仍待重评。"))
                elif resolution["kind"] == "not_needed":
                    path = paths[ref]
                    if not (path[0] == "decisions" or path[:2] == ("requirements", "scope")):
                        diagnostics.append(_issue(12, gid, "gap-requests.json/resolution", "不再需要必须引用分析决策或范围依据。"))
    for gid in set(receivers) - set(counts):
        diagnostics.append(_issue(12, gid, "analysis/questions", "接收问题引用了未登记的缺口。"))
    for gid in set(blocks["gap"]) - set(counts):
        diagnostics.append(_issue(9, gid, "prd.md", "占位未登记缺口。"))
    if text.count("待分析补充") != sum(content["text"].count("待分析补充") for content in blocks["gap"].values()):
        diagnostics.append(_issue(9, "$", "prd.md", "存在定位块之外的游离占位。"))


def _document_info(metadata, trace, blocks, text, diagnostics):
    """校验稿件自身的信息视图及提示，返回可见字段以便状态变更保留原生成信息。"""
    prd = metadata["prd"]
    meta = trace["meta"]
    info = blocks["section"].get("info", {}).get("text", "")
    cells = {}
    for line in info.splitlines():
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) == 2:
            if parts[0] in cells:
                diagnostics.append(_issue(10, "$", "prd.md/info", "文档信息键重复。"))
            # 比较可见值而非HTML转义拼写，使含表格分隔符或换行的合法标题仍能校验。
            cells[parts[0]] = html.unescape(parts[1].replace("<br>", "\n"))
    for key, expected in (("需求编号", trace["requirement_id"]), ("标题", metadata["common"]["title"]), ("PRD 版本", prd["version"]), ("状态", prd["status"]), ("草稿类型", meta["draft_kind"]), ("基于的分析修订号", str(prd["based_on_analysis_revision"]))):
        if cells.get(key) != str(expected).replace("\r\n", "\n").replace("\r", "\n"):
            diagnostics.append(_issue(10, "$", "prd.md/info", f"文档信息 {key} 与权威元数据不符。"))
    for key in ("生成时间", "未覆盖的分析项"):
        if not cells.get(key):
            diagnostics.append(_issue(10, "$", "prd.md/info", f"文档信息缺少 {key}。"))
    if prd["status"] in {"released", "deprecated"}:
        if any(prompt in text for prompt in PROMPTS.values()):
            diagnostics.append(_issue(7, "$", "prd.md", "已发布或废弃稿仍有草稿提示。"))
    elif not text.startswith(PROMPTS[meta["draft_kind"]]):
        diagnostics.append(_issue(7, "$", "prd.md", "文首草稿提示与类型不一致。"))
    return cells


def _metadata(metadata, analysis, trace, blocks, text, diagnostics, pending):
    """校验信息视图，检查当前稿是否遵循分析就绪度；历史快照不与新分析比较。"""
    _document_info(metadata, trace, blocks, text, diagnostics)
    if metadata['prd']['status'] == 'deprecated':
        return
    meta = trace['meta']
    expected_kind = "stale_draft" if analysis["meta"]["analysis_status"] == "stale" else {"not_ready": "risk_draft", "conditionally_ready": "conditional_draft", "ready_for_document": "formal_draft"}[analysis["meta"]["readiness"]]
    if analysis["meta"]["analysis_status"] == "stale" or not pending:
        if meta["draft_kind"] != expected_kind:
            diagnostics.append(_issue(7, "$", "prd-trace.json/meta/draft_kind", "草稿类型与当前分析状态或就绪度不符。"))
    if not pending and meta["generated_under_readiness"] != analysis["meta"]["readiness"]:
        diagnostics.append(_issue(7, "$", "prd-trace.json/meta/generated_under_readiness", "生成时就绪度快照与已同步分析不符。"))


def _patch(patch, metadata, analysis, trace, registry, diagnostics):
    """只读检查编号补丁的结构、身份及读时版本，不分配正式编号。"""
    if not _structure(patch, "numbering-patch", diagnostics, 1, "numbering-patch"):
        return
    if patch["requirement_id"] != analysis["requirement_id"] or patch["base_prd_version"] != metadata["prd"]["version"] or patch["base_analysis_revision"] != analysis["meta"]["analysis_revision"]:
        diagnostics.append(_issue(2, "$", "numbering-patch", "编号补丁身份或读时版本冲突，须重新读取。"))
    seen, bound_ids = set(), set()
    by_key = {item["mapping_key"]: item for item in trace["items"] if "mapping_key" in item}
    by_id = {item["prd_id"]: item for item in trace["items"]}
    for item in patch["items"]:
        key = item["mapping_key"]
        if key in seen:
            diagnostics.append(_issue(2, key, "numbering-patch/items", "补丁映射键重复。"))
        seen.add(key)
        existing = by_key.get(key)
        bound_id = item.get("prd_id", existing["prd_id"] if existing else None)
        if bound_id is not None:
            if bound_id in bound_ids:
                diagnostics.append(_issue(2, key, "numbering-patch/items/prd_id", "同一补丁不能以多个映射键绑定同一既有编号。"))
            bound_ids.add(bound_id)
        if "prd_id" in item:
            located = by_id.get(item["prd_id"])
            if located is None or (existing is not None and existing["prd_id"] != located["prd_id"]) or (located and located.get("mapping_key", key) != key):
                diagnostics.append(_issue(2, key, "numbering-patch/items/prd_id", "不能指定新编号或与既有映射键冲突。"))
            if located is not None and located["kind"] != item["kind"]:
                diagnostics.append(_issue(2, key, "numbering-patch/items/kind", "按正式编号定位的旧条目类别不能改变。"))
        if existing and existing["kind"] != item["kind"]:
            diagnostics.append(_issue(2, key, "numbering-patch/items/kind", "既有映射类别不能改变。"))
        if any(ref not in registry for ref in item["analysis_refs"]):
            diagnostics.append(_issue(3, key, "numbering-patch/items/analysis_refs", "补丁引用未提供或不存在。"))


def validate_upstream(root: Path, analysis: dict, diagnostics: list, *, related_analyses: Sequence[Path] = (), gaps: dict | None = None) -> tuple:
    """只读校验分析和显式关联输入，返回文档及上游结果。

    root 为需求目录，analysis 为已读取分析；diagnostics 收集读取及降级诊断。
    related_analyses 为关联分析路径，gaps 为可选缺口；安装损坏时异常原样抛出。
    """
    upstream = _analyst()
    # 来源名称清单可选，但缺失时不能伪造清单冒充来源已核验。结构和非来源规则仍调用
    # 分析侧同一实现，来源与历史权威性检查暂不可完成，显式警告并保留 source_id。
    documents = []
    missing_manifests = set()
    for path, doc in [(root / "analysis/analysis-result.json", analysis), *[(Path(p), None) for p in related_analyses]]:
        if doc is None:
            doc = _read(path, diagnostics, 3)
        if doc is None:
            continue
        manifest = _read(path.with_name("source-manifest.json"), diagnostics, 1, optional=True)
        if manifest is None:
            missing_manifests.add(id(doc))
            manifest = []
            diagnostics.append(_issue(3, "$", path.with_name("source-manifest.json"), "辅助来源清单不可用，仅显示 source_id；来源和历史权威性未核验。", "warning"))
        documents.append((doc, manifest))
    if not documents:
        return documents, {"status": "fail", "diagnostics": []}
    if missing_manifests:
        # 精确复用上游规则，不复制规则内容；仅跳过缺失清单所依赖的来源检查。
        # 该降级不是上游完整 pass，因此保留上方的 warning，不让其可用于正式发布。
        upstream_issues = []
        analysis_validator, manifest_validator = upstream._validators()
        for doc, manifest in documents:
            upstream_issues.extend(upstream._format_errors(doc, analysis_validator))
            if id(doc) not in missing_manifests:
                upstream_issues.extend(upstream._format_errors(manifest, manifest_validator, 7))
        if not upstream_issues:
            upstream_registry = upstream._index_documents(documents, upstream_issues)
            for doc, manifest in documents:
                upstream._check_references(doc, upstream_registry, upstream_issues)
                upstream._check_questions(doc, upstream_issues)
                upstream._check_completion(doc, upstream_issues)
                upstream._check_technical(doc, upstream_issues)
                available_manifest = manifest if id(doc) not in missing_manifests else None
                upstream._check_sources(doc, available_manifest, upstream_issues)
                upstream._check_history(doc, available_manifest, upstream_issues)
            upstream._check_gap_requests(documents[0][0], gaps, upstream_registry, upstream_issues)
        response = upstream._result(upstream_issues)
    else:
        response = upstream.validate_analysis(documents[0][0], documents[0][1], related_analyses=documents[1:], gap_requests=gaps)
    return documents, response


def validate_prd(requirement_dir: Path, *, related_analyses: Sequence[Path] = (), previous_trace: Path | None = None, numbering_patch: Path | None = None) -> dict:
    """只读校验 requirement_dir 的工作稿，返回三态状态及逐条诊断。

    related_analyses 为调用方显式指定的关联分析路径；previous_trace 为可选历史追溯，
    numbering_patch 为可选待检映射补丁。仅检查已有工作稿，不创建需求、编号或发布快照。
    用户文件、编码、JSON 与协议错误返回 fail；损坏的安装 Schema/分析校验器抛出异常。
    自然语言忠实性和关闭内容充分性仍须人工评审，不由格式 pass 宣称完成。
    """
    root = Path(requirement_dir).absolute()
    prd = root / "prd"
    diagnostics = []
    transaction = prd / '.prd-transaction.json'
    try:
        if _fs().is_link(transaction) or transaction.exists():
            return _result([_issue(1, '$', transaction, 'PRD 保存尚未完成，请先恢复，不能据部分落盘声明有效。')])
    except OSError as error:
        return _result([_issue(1, '$', transaction, f'无法检查 PRD 保存状态：{error}')])
    analysis = _read(root / "analysis/analysis-result.json", diagnostics, 1)
    metadata = _read(root / "requirement.json", diagnostics, 10)
    trace = _read(prd / "prd-trace.json", diagnostics, 1)
    gaps = _read(prd / "gap-requests.json", diagnostics, 12)
    try:
        path = prd / "prd.md"
        data = _read_bytes(path, link_message="正文不得为符号链接")
        text = data.decode("utf-8")
    except (OSError, ValueError, UnicodeError) as error:
        diagnostics.append(_issue(1, "$", path, f"无法读取正文：{error}"))
        text, data = "", b""
    if any(value is None for value in (analysis, metadata, trace, gaps)):
        return _result(diagnostics)
    trace_ok = _structure(trace, "prd-trace", diagnostics, 1, "prd-trace.json")
    gap_ok = _structure(gaps, "gap-request", diagnostics, 12, "gap-requests.json")
    metadata_ok = isinstance(metadata, dict) and isinstance(metadata.get("common"), dict) and isinstance(metadata.get("prd"), dict)
    if metadata_ok:
        pd = metadata["prd"]
        metadata_ok = isinstance(pd.get("version"), str) and bool(VERSION.fullmatch(pd["version"])) and isinstance(pd.get("status"), str) and pd["status"] in {"draft", "in_review", "released", "deprecated"} and type(pd.get("based_on_analysis_revision")) is int and pd["based_on_analysis_revision"] >= 1 and isinstance(metadata["common"].get("title"), str)
    if not metadata_ok:
        diagnostics.append(_issue(10, "$", "requirement.json", "common/prd 结构、版本、状态或分析修订号不合法；不迁移旧消费者整数版本。"))
    documents, response = validate_upstream(root, analysis, diagnostics, related_analyses=related_analyses, gaps=gaps)
    for issue in response["diagnostics"]:
        if issue["level"] == "fail":
            # 缺口协议在两侧同属规则12，保留分类以免已有缺口夹具退化为普通来源错误。
            rule = 12 if issue["rule"] == 12 else 3
            diagnostics.append(_issue(rule, issue["item_id"], "analysis" + issue["path"], "上游校验失败：" + issue["message"]))
    if not trace_ok or not gap_ok or not metadata_ok or response["status"] == "fail":
        return _result(diagnostics)
    rid = analysis["requirement_id"]
    if any(value != rid for value in (trace["requirement_id"], gaps["requirement_id"], metadata["common"].get("requirement_id"))):
        diagnostics.append(_issue(1, "$", "requirement_id", "分析、元数据、追溯及缺口身份不一致。"))
    registry, paths = _registry([doc for doc, _ in documents])
    pending = metadata["prd"]["based_on_analysis_revision"] < analysis["meta"]["analysis_revision"]
    if pending:
        diagnostics.append(_issue(10, "$", "requirement.json/prd/based_on_analysis_revision", "PRD 待同步；当前差异不作为结构失败。", "warning"))
    elif metadata["prd"]["based_on_analysis_revision"] > analysis["meta"]["analysis_revision"]:
        diagnostics.append(_issue(10, "$", "requirement.json/prd/based_on_analysis_revision", "PRD 所依据的分析修订来自未来。"))
    baseline = trace["meta"].get("content_baseline")
    if baseline is not None:
        try:
            baseline_valid = _sha(baseline.encode("utf-8")) == trace["meta"]["content_hash"]
        except UnicodeEncodeError:
            baseline_valid = False
        if not baseline_valid:
            diagnostics.append(_issue(1, "$", "prd-trace.json/meta/content_baseline", "正文基准无法编码为 UTF-8 或摘要与 content_hash 不符。"))
    if trace["meta"]["content_hash"] != _sha(data):
        message = "正文摘要变化，检测到未处理手工修改；须比较含义后处理。"
        if baseline is None:
            message += "旧稿缺少正文基准，比较证据不足。"
        diagnostics.append(_issue(4, "$", "prd.md", message, "warning"))
    blocks = _blocks(text, diagnostics)
    _manual_checks(text, rid, blocks, diagnostics, metadata["prd"]["status"] == "released")
    saved_sections = trace['meta'].get('section_source_digests')
    if saved_sections is not None and not pending:
        current_sections = section_source_digests(analysis, gaps, trace=trace, source_manifest=documents[0][1],
                related_analyses=[doc for doc, _ in documents[1:]], legacy_layout='glossary' not in saved_sections)
        for key, digest in saved_sections.items():
            if key == 'appendix' and any('source-manifest.json' in issue['path'] and issue['level'] == 'warning' for issue in diagnostics):
                continue  # 缺来源名称时仍校验权威条目，不把辅助清单降级伪装成章节依据失败。
            if digest != current_sections[key]:
                diagnostics.append(_issue(3, key, 'prd-trace.json/meta/section_source_digests', '已同步章节依据与当前分析不符。'))
    _trace_checks(trace, registry, paths, blocks, text, diagnostics, pending)
    _residuals(analysis, registry, blocks, diagnostics)
    _gaps(gaps, analysis, registry, paths, blocks, text, diagnostics)
    _metadata(metadata, analysis, trace, blocks, text, diagnostics, pending)
    events = _events(prd / "prd-events.jsonl", diagnostics)
    _snapshots(prd, trace, events, diagnostics)
    if previous_trace is not None:
        previous = _read(Path(previous_trace), diagnostics, 2)
        if previous is not None:
            _history(trace, previous, diagnostics, str(previous_trace))
    if numbering_patch is not None:
        patch = _read(Path(numbering_patch), diagnostics, 1)
        if patch is not None:
            _patch(patch, metadata, analysis, trace, registry, diagnostics)
    return _result(diagnostics)


def main(argv: Sequence[str] | None = None) -> int:
    """校验 argv 指定的需求工作稿，输出单个 JSON，返回 0/1/2 三态退出码。

    argv 省略时读取命令行参数；支持显式关联分析、历史追溯和编号补丁。
    用户数据错误转为诊断；参数错误由 argparse 报告，损坏的安装抛出异常。
    """
    parser = argparse.ArgumentParser(description="只读校验 PRD，不生成、不发布、不写分析。")
    parser.add_argument("requirement_dir", type=Path)
    parser.add_argument("--related-analysis", type=Path, action="append", default=[])
    parser.add_argument("--previous-trace", type=Path)
    parser.add_argument("--numbering-patch", type=Path)
    args = parser.parse_args(argv)
    response = validate_prd(args.requirement_dir, related_analyses=args.related_analysis, previous_trace=args.previous_trace, numbering_patch=args.numbering_patch)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return EXIT_CODES[response["status"]]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    raise SystemExit(main())

"""编排首稿候选校验、编号、信息渲染与受并发保护的保存；不执行同步、评审或发布。"""

import argparse
import base64
from collections.abc import Sequence
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
from functools import lru_cache
import importlib.util
import json
import os
from pathlib import Path
import tempfile


TARGETS = ("prd/prd.md", "prd/prd-trace.json", "prd/gap-requests.json", "requirement.json", "prd/prd-events.jsonl")
JOURNAL = "prd/.prd-transaction.json"
EXIT_CODES = {"pass": 0, "warning": 1, "fail": 2}


@lru_cache(maxsize=None)
def _module(name):
    """从可信的相邻生产文件加载模块，兼容 python -I 和任意调用目录。"""
    spec = importlib.util.spec_from_file_location("prd_writer_" + name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _encode(value):
    """序列化结构化产物；拒绝非有限值，不改变正文原始字节。"""
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _safe(path):
    """拒绝符号链接，防止工作区写入越过用户指定的需求边界。"""
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError(f"不使用符号链接路径：{path}")


def _raw(path):
    """读取文件原始字节；不存在返回 None，其他路径与读取错误原样抛出。"""
    _safe(path)
    return path.read_bytes() if path.exists() else None


def _hash(raw):
    """将可选文件快照转为原始字节摘要，缺文件保持 None。"""
    return None if raw is None else _module("render_info").content_hash(raw)


@contextmanager
def _lock(root):
    """锁定现有需求目录而不在 analysis/ 创建锁；只串行化合作的生成侧写入。"""
    _safe(root)
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _atomic_write(path, raw):
    """同目录准备后原子替换单文件；跨文件完成状态由私有 journal 管理。"""
    _safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".prd-write-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        # 仅清理本调用创建的临时文件，不清理业务文件、候选或他人的事务。
        if temporary.exists():
            temporary.unlink()


def _diagnostic(message, path="$", rule=0):
    """构造保存层诊断，不冒用分析或 PRD 校验器的业务规则。"""
    return {"rule": rule, "level": "fail", "item_id": "$", "path": str(path), "message": str(message)}


def _guard_hash(path, optional=False):
    """记录读时文件状态；可选清单不可读时保留该状态供并发比较，不阻断已声明的降级。"""
    try:
        return _hash(_raw(path))
    except OSError as error:
        if not optional:
            raise
        return "unreadable:" + type(error).__name__


def _guards(root, related):
    """快照实际读取的权威分析及可选来源清单，不读取人用报告或扫描其他需求。"""
    paths = [root / "analysis/analysis-result.json", root / "analysis/source-manifest.json"]
    for path in related:
        paths.extend((Path(path), Path(path).with_name("source-manifest.json")))
    return [{"path": str(path.absolute()), "optional": path.name == "source-manifest.json",
             "sha256": _guard_hash(path, path.name == "source-manifest.json")} for path in dict.fromkeys(paths)]


def _check_guards(guards):
    """分析或来源在读取后变化即拒写；不靠改修订数字掩盖字节级并发。"""
    for guard in guards:
        if _guard_hash(Path(guard["path"]), guard.get("optional", False)) != guard["sha256"]:
            raise ValueError(f"读取后分析或来源已变化，重新读取后再生成：{guard['path']}")


def _read_json(path):
    """严格读取生产 JSON，不接受重复键或非有限值。"""
    _safe(path)
    return _module("validate_prd")._json(path)


def _finish(root, journal):
    """校验事务各目标只处于读时或本事务写后状态，再向前完成；冲突保留 journal。"""
    entries = journal.get("entries", [])
    if journal.get("format") != "prd-draft-transaction-1" or [entry.get("path") for entry in entries] != list(TARGETS):
        raise ValueError("不识别草稿恢复记录，未执行任何业务写入")
    _check_guards(journal["guards"])
    pending = []
    for entry in entries:
        data = base64.b64decode(entry["data"], validate=True)
        if _hash(data) != entry["after"]:
            raise ValueError(f"事务候选摘要不符：{entry['path']}")
        current = _hash(_raw(root / entry["path"]))
        if current not in (entry["before"], entry["after"]):
            raise ValueError(f"草稿文件已被其他操作修改，拒绝覆盖：{entry['path']}")
        pending.append((entry, data))
    # 事件是事务最后一项；保留原始前缀，只在所有产物写好后追加本次事件。
    for entry, data in pending:
        _check_guards(journal["guards"])
        current = _hash(_raw(root / entry["path"]))
        if current not in (entry["before"], entry["after"]):
            raise ValueError(f"写入前文件已变化：{entry['path']}")
        if current != entry["after"]:
            _atomic_write(root / entry["path"], data)
    _check_guards(journal["guards"])
    for entry, _ in pending:
        if _hash(_raw(root / entry["path"])) != entry["after"]:
            raise ValueError(f"保存期间检测到并发修改：{entry['path']}")
    (root / JOURNAL).unlink()


def recover_draft(requirement_dir: Path) -> dict:
    """完成本需求尚未完成的草稿事务，返回实际结果，不创建新生成事件。

    requirement_dir 必须为已有需求目录。仅在分析原始字节和所有目标仍匹配本事务读前/写后状态时恢复；
    发现冲突或 I/O 错误返回 fail，保留候选和 journal，不覆盖其他人的新内容。安装损坏原样抛出。
    """
    root = Path(os.path.abspath(requirement_dir))
    try:
        _safe(Path(requirement_dir))
        with _lock(root):
            journal = _read_json(root / JOURNAL)
            if not isinstance(journal, dict):
                raise ValueError("恢复记录不是对象")
            _finish(root, journal)
            return {**journal["result"], "recovered": True, "written": list(TARGETS)}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"status": "fail", "diagnostics": [_diagnostic(error, JOURNAL)], "written": [], "recovery_required": (root / JOURNAL).exists()}


def _next_version(requirement):
    """首稿固定为0.1；当前阶段只允许未发布工作稿基于同一分析重新生成。"""
    prd = requirement.get("prd")
    if prd is None:
        return "0.1"
    version = prd.get("version")
    validator = _module("validate_prd")
    if not isinstance(version, str) or not validator.VERSION.fullmatch(version) or not version.startswith("0."):
        raise ValueError("旧格式或发布后版本不在阶段3首稿生成范围内，不自动迁移或覆盖")
    if prd.get("status") != "draft":
        raise ValueError("当前不是可重新生成的未发布草稿，评审/发布/废弃流程尚未实现")
    return f"0.{int(version.split('.')[1]) + 1}"


def _gap_document(root, supplied, requirement_id, version, existing):
    """保留已登记缺口及其接收进度；本阶段只允许新增 open 请求，不关闭或重置旧缺口。"""
    gaps = deepcopy(supplied if supplied is not None else existing)
    if gaps is None:
        gaps = {"schema_version": "1.0", "requirement_id": requirement_id, "counters": {"GAPREQ": 0}, "requests": []}
    if not isinstance(gaps, dict):
        raise ValueError("缺口候选必须为版本化对象")
    errors = list(_module("validate_prd")._schema("gap-request").iter_errors(gaps))
    if errors:
        raise ValueError(f"缺口格式错误：{errors[0].message}")
    if gaps["requirement_id"] != requirement_id:
        raise ValueError("缺口需求编号不匹配")
    old = {item["id"]: item for item in (existing or {}).get("requests", [])}
    current = {item["id"]: item for item in gaps["requests"]}
    for key, item in old.items():
        if current.get(key) != item:
            raise ValueError(f"阶段3不得删除、重置或关闭已登记缺口：{key}")
    if existing and gaps["counters"]["GAPREQ"] < existing["counters"]["GAPREQ"]:
        raise ValueError("缺口计数器不得回退")
    for item in gaps["requests"]:
        if item["id"] not in old:
            if int(item["id"].split("-")[1]) <= (existing or {}).get("counters", {}).get("GAPREQ", 0):
                raise ValueError(f"新缺口编号不得复用已有高水位：{item['id']}")
            if item["status"] != "open" or "resolution" in item:
                raise ValueError(f"新缺口只能为 open：{item['id']}")
            item["raised_in"] = version
    return gaps


def write_draft(requirement_dir: Path, *, patch: dict, body: str, gaps: dict | None = None,
                related_analyses: Sequence[Path] = (), allow_stale: bool = False,
                generated_at: str | None = None, candidate_dir: Path | None = None) -> dict:
    """校验并保存首次或同分析输入的重复草稿，返回诊断、编号、版本和真实保存位置。

    patch 仅含获认可协议的编号映射；body 为按编号候选编写的 Markdown，gaps 为可选完整缺口候选。
    related_analyses 只使用调用方显式给出的资料；allow_stale 仅可对应用户实际坚持。
    generated_at 可固定测试时间，默认取实际UTC；candidate_dir 须为需求目录外不存在的新目录。
    校验或并发失败返回 fail 并保留已构造候选；写中失败保留私有 journal，需显式恢复，不报告成功。
    不写 analysis/、其他需求、快照或 common，不执行同步/编辑/评审/发布；安装故障原样抛出。
    """
    root = Path(os.path.abspath(requirement_dir))
    validator, renderer = _module("validate_prd"), _module("render_info")
    candidate = None
    diagnostics = []
    before, payload = {}, {}
    try:
        _safe(Path(requirement_dir))
        with _lock(root):
            if (root / JOURNAL).exists():
                raise ValueError("存在未完成草稿事务，请先使用 --recover；不覆盖部分写入")
            before = {name: _raw(root / name) for name in TARGETS}
            guards = _guards(root, related_analyses)
            gate = _module("check_gate").check_gate(root, allow_stale=allow_stale, related_analyses=related_analyses)
            diagnostics.extend(gate.get("diagnostics", []))
            if not gate["allowed"]:
                return {**gate, "written": [], "generated": False}
            requirement = _read_json(root / "requirement.json")
            analysis = _read_json(root / "analysis/analysis-result.json")
            if candidate_dir is None:
                candidate = Path(tempfile.mkdtemp(prefix="prd-candidate-"))
            else:
                _safe(Path(candidate_dir))
                candidate = Path(os.path.abspath(candidate_dir))
                protected = [root, *(Path(os.path.abspath(path)).parent for path in related_analyses)]
                if any(candidate == parent or parent in candidate.parents for parent in protected):
                    raise ValueError("候选目录必须在正式需求和关联分析目录之外")
                candidate.mkdir(parents=True, exist_ok=False)
            # 先保留模型原始材料；即使编号或渲染阶段失败，也能按真实候选修正而不是丢失现场。
            inputs = candidate / "inputs"
            inputs.mkdir()
            (inputs / "body.md").write_text(body, encoding="utf-8")
            (inputs / "numbering-patch.json").write_bytes(_encode(patch))
            if gaps is not None:
                (inputs / "gap-requests.json").write_bytes(_encode(gaps))
            version = _next_version(requirement)
            previous = _read_json(root / "prd/prd-trace.json") if before["prd/prd-trace.json"] is not None else None
            if "prd" in requirement:
                if requirement["prd"]["based_on_analysis_revision"] != analysis["meta"]["analysis_revision"]:
                    raise ValueError("分析已变化，需阶段4增量同步；首稿入口不整篇覆盖")
                if previous is None or any(before[name] is None for name in TARGETS):
                    raise ValueError("已有工作稿文件不完整，请先恢复，不覆盖已有成果")
                if previous["meta"]["content_hash"] != renderer.content_hash(before["prd/prd.md"]):
                    raise ValueError("工作稿含尚未处理的手工修改，首稿入口不覆盖")
                existing_check = validator.validate_prd(root, related_analyses=related_analyses)
                if existing_check["status"] == "fail":
                    return {**existing_check, "candidate_dir": str(candidate), "written": [], "generated": False}
            elif any(before[name] is not None for name in TARGETS if name not in ("requirement.json", "prd/prd-trace.json")):
                raise ValueError("无 prd 元数据但存在草稿文件，请先核对旧格式或未完成保存")
            if (root / "prd/versions").exists() and any((root / "prd/versions").iterdir()):
                raise ValueError("存在发布快照，首稿入口不覆盖已发布需求")
            related = [_read_json(Path(path)) for path in related_analyses]
            trace = _module("assign_ids").allocate_ids(patch, analysis, requirement, previous_trace=previous,
                        related_analyses=related, version=version, draft_kind=gate["draft_kind"])
            existing_gaps = _read_json(root / "prd/gap-requests.json") if before["prd/gap-requests.json"] is not None else None
            gap_document = _gap_document(root, gaps, analysis["requirement_id"], version, existing_gaps)
            next_requirement = deepcopy(requirement)
            next_requirement["prd"] = {**requirement.get("prd", {}), "based_on_analysis_revision": analysis["meta"]["analysis_revision"], "status": "draft", "version": version}
            timestamp = generated_at or datetime.now(timezone.utc).isoformat()
            events_raw = before["prd/prd-events.jsonl"] or b""
            if events_raw and not events_raw.endswith(b"\n"):
                events_raw += b"\n"
            event = {"time": timestamp, "prd_version": version, "change_type": "initial_generation",
                     "summary": "首次生成工作稿" if "prd" not in requirement else "基于同一分析输入重复生成工作稿",
                     "affected_prd_ids": [item["prd_id"] for item in trace["items"]],
                     "based_on_analysis_revision": analysis["meta"]["analysis_revision"], "actor": "prd_generator"}
            new_events = [event]
            if any(item["id"] not in {old["id"] for old in (existing_gaps or {}).get("requests", [])} for item in gap_document["requests"]):
                new_events.append({**event, "change_type": "gap_request", "summary": "登记生成中发现的分析缺口，保留占位并建议交回需求分析"})
            events_raw += b"".join(_encode(item).replace(b"\n", b" ").rstrip() + b"\n" for item in new_events)
            events = [json.loads(line) for line in events_raw.decode("utf-8").splitlines() if line.strip()]
            changes = "\n".join(f"- {item['time']} · {item['prd_version']} · {item['summary']}" + ("（" + "、".join(item['affected_prd_ids']) + "）" if item['affected_prd_ids'] else "") for item in events)
            text = renderer.render_info(body, next_requirement, trace, generated_at=timestamp,
                        uncovered_analysis=gate.get("uncovered_analysis", ()), changes=changes)
            trace["meta"]["content_hash"] = renderer.content_hash(text.encode("utf-8"))
            payload = {"prd/prd.md": text.encode("utf-8"), "prd/prd-trace.json": _encode(trace),
                       "prd/gap-requests.json": _encode(gap_document), "requirement.json": _encode(next_requirement), "prd/prd-events.jsonl": events_raw}
            for name, raw in payload.items():
                path = candidate / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            for name in ("analysis-result.json", "source-manifest.json"):
                try:
                    raw = _raw(root / "analysis" / name)
                except OSError:
                    if name != "source-manifest.json":
                        raise
                    raw = None  # 可选清单的降级已由门禁完整告警，候选不伪造可读来源。
                if raw is not None:
                    path = candidate / "analysis" / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(raw)
            checked = validator.validate_prd(candidate, related_analyses=related_analyses,
                        previous_trace=root / "prd/prd-trace.json" if previous else None)
            diagnostics.extend(checked["diagnostics"])
            if checked["status"] == "fail":
                return {"status": "fail", "diagnostics": diagnostics, "candidate_dir": str(candidate), "written": [], "generated": False}
            if "prd" in requirement:
                old_sections = validator._blocks(before["prd/prd.md"].decode("utf-8"), [])["section"]
                new_sections = validator._blocks(text, [])["section"]
                stable = lambda sections: {key: value["text"] for key, value in sections.items() if key not in ("info", "changes")}
                if stable(old_sections) != stable(new_sections):
                    raise ValueError("同一分析输入重复生成不得改写需求正文；保留候选，需求修改须交回分析")
            _check_guards(guards)
            for name in TARGETS:
                if _raw(root / name) != before[name]:
                    raise ValueError(f"写前文件已变化，重新读取后再生成：{name}")
            result = {"status": "warning" if diagnostics else "pass", "diagnostics": diagnostics, "version": version,
                      "draft_kind": gate["draft_kind"], "candidate_dir": str(candidate), "generated": True,
                      "mapping": [{"mapping_key": item.get("mapping_key"), "prd_id": item["prd_id"], "analysis_refs": item["analysis_refs"]} for item in trace["items"]]}
            journal = {"format": "prd-draft-transaction-1", "guards": guards, "result": result,
                       "entries": [{"path": name, "before": _hash(before[name]), "after": _hash(payload[name]),
                                    "data": base64.b64encode(payload[name]).decode("ascii")} for name in TARGETS]}
            _atomic_write(root / JOURNAL, _encode(journal))
            _finish(root, journal)
            return {**result, "written": list(TARGETS)}
    except (OSError, ValueError, KeyError, TypeError) as error:
        written = []
        if (root / JOURNAL).exists():
            for name, raw in payload.items():
                try:
                    if raw != before.get(name) and _raw(root / name) == raw:
                        written.append(name)
                except (OSError, ValueError):
                    pass
        return {"status": "fail", "diagnostics": diagnostics + [_diagnostic(error)], "candidate_dir": str(candidate) if candidate else None,
                "written": written, "generated": False, "transaction_complete": False, "recovery_required": (root / JOURNAL).exists()}


def main(argv=None) -> int:
    """执行统一草稿保存或显式恢复；argv 为命令参数，返回 pass0/warning1/fail2。

    单个 JSON 输出真实结果；参数缺失由 argparse 报错，安装故障原样抛出，不自动承认过期分析。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirement_dir", type=Path)
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--body", type=Path)
    parser.add_argument("--gaps", type=Path)
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--related-analysis", action="append", type=Path, default=[])
    parser.add_argument("--allow-stale", action="store_true")
    parser.add_argument("--recover", action="store_true")
    args = parser.parse_args(argv)
    if args.recover:
        if args.patch or args.body or args.gaps:
            parser.error("--recover 不接受新的候选材料")
        result = recover_draft(args.requirement_dir)
    else:
        if not args.patch or not args.body:
            parser.error("保存草稿需要 --patch 和 --body")
        try:
            result = write_draft(args.requirement_dir, patch=_read_json(args.patch), body=args.body.read_text(encoding="utf-8"),
                                gaps=_read_json(args.gaps) if args.gaps else None, candidate_dir=args.candidate_dir,
                                related_analyses=args.related_analysis, allow_stale=args.allow_stale)
        except (OSError, ValueError, KeyError, TypeError) as error:
            result = {"status": "fail", "diagnostics": [_diagnostic(error)], "written": [], "generated": False}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return EXIT_CODES[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

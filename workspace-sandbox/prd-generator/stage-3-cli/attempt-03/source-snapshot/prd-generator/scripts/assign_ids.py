"""分配稳定的 PRD 编号并生成候选追溯；独立写入不修改正文或分析资料。"""

import argparse
from collections.abc import Sequence
from copy import deepcopy
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import tempfile


def _load_validator():
    """加载同目录的追溯校验器，复用唯一摘要与分析索引实现。"""
    spec = importlib.util.spec_from_file_location("prd_numbering_validator", Path(__file__).with_name("validate_prd.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_validator = _load_validator()


def _check_schema(value, name):
    """检查协议结构，错误包含 JSON 路径。"""
    errors = list(_validator._schema(name).iter_errors(value))
    if errors:
        error = sorted(errors, key=lambda e: str(list(e.absolute_path)))[0]
        raise ValueError(f"{name}/{'/'.join(map(str, error.absolute_path))}: {error.message}")


def _registry(documents):
    """索引显式分析资料，拒绝需求或条目身份冲突。"""
    result = {}
    ids = set()
    for doc in documents:
        try:
            rid = doc["requirement_id"]
            if not isinstance(rid, str) or not rid or rid in ids:
                raise ValueError(f"analysis/requirement_id: 重复或非法：{rid}")
            ids.add(rid)
            for _, item in _validator._analyst()._entries(doc):
                ref = f"{rid}/{item['id']}"
                if ref in result:
                    raise ValueError(f"analysis: 条目重复：{ref}")
                result[ref] = item
        except (KeyError, TypeError) as error:
            raise ValueError(f"analysis: 结构不完整：{error}") from error
    return result


def _validate_trace(trace, rid):
    """校验既有追溯的结构、编号身份和计数器高水位。"""
    _check_schema(trace, "prd-trace")
    if trace["requirement_id"] != rid:
        raise ValueError("prd-trace/requirement_id: 需求身份不一致")
    ids, numbers, keys = set(), set(), set()
    for item in trace["items"]:
        pid = item["prd_id"]
        _, prefix, number = pid.split("-")
        numeric = (prefix, int(number))
        key = item.get("mapping_key")
        if pid in ids or numeric in numbers or (key is not None and key in keys):
            raise ValueError(f"prd-trace/items/{pid}: 编号或映射键重复")
        if _validator.KINDS[item["kind"]] != prefix or trace["meta"]["counters"].get(prefix, 0) < int(number):
            raise ValueError(f"prd-trace/items/{pid}: 类别或计数器不合法")
        ids.add(pid)
        numbers.add(numeric)
        if key is not None:
            keys.add(key)


def allocate_ids(patch: dict, analysis: dict, requirement: dict, *, previous_trace: dict | None = None, related_analyses: Sequence[dict] = (), version: str = '0.1', draft_kind: str | None = None) -> dict:
    """基于补丁和只读快照分配编号，返回完整候选追溯，不修改输入。

    patch、analysis、requirement 是当前补丁、主分析和需求元数据；previous_trace
    为既有追溯，related_analyses 为显式关联分析，version 为新条目的引入版本，
    draft_kind 为门禁确定的草稿类型。候选 meta.content_hash 是空正文原始字节
    的摘要，调用方须由 render_info 按实际正文原始字节替换。协议、身份、引用、
    高水位或映射冲突时抛出 ValueError。
    """
    _check_schema(patch, "numbering-patch")
    try:
        rid = requirement["common"]["requirement_id"]
        meta = analysis["meta"]
        base = requirement.get("prd", {}).get("version")
        if rid != analysis["requirement_id"] or rid != patch["requirement_id"]:
            raise ValueError("requirement_id: 补丁、分析和需求身份不一致")
        if patch["base_prd_version"] != base or patch["base_analysis_revision"] != meta["analysis_revision"]:
            raise ValueError("numbering-patch: 读取时版本或分析修订冲突")
        readiness = meta["readiness"]
        expected_kind = "stale_draft" if meta["analysis_status"] == "stale" else {"not_ready": "risk_draft", "conditionally_ready": "conditional_draft", "ready_for_document": "formal_draft"}[readiness]
        if draft_kind is not None and draft_kind != expected_kind:
            raise ValueError("draft_kind: 与分析当前状态和就绪度不一致")
        kind = expected_kind
        if not isinstance(version, str) or not _validator.VERSION.fullmatch(version):
            raise ValueError("version: 引入版本格式不合法")
    except (KeyError, TypeError) as error:
        raise ValueError(f"requirement/analysis: 结构不完整：{error}") from error
    registry = _registry((analysis, *related_analyses))
    if previous_trace is not None:
        _validate_trace(previous_trace, rid)
        for old in previous_trace["items"]:
            missing = [ref for ref in old["analysis_refs"] if ref not in registry]
            if missing:
                raise ValueError(f"prd-trace/items/{old['prd_id']}/analysis_refs: 引用不存在：{missing}")
        trace = deepcopy(previous_trace)
    else:
        trace = {"schema_version": "1.0", "requirement_id": rid, "meta": {"counters": {}}, "items": []}
    trace["meta"].update(draft_kind=kind, generated_under_readiness=readiness, content_hash=_validator._sha(b""))
    by_key = {item["mapping_key"]: item for item in trace["items"] if "mapping_key" in item}
    by_id = {item["prd_id"]: item for item in trace["items"]}
    seen_keys, used_ids = set(), set()
    ranks = {"assumption": 0, "inferred": 1, "confirmed": 2}
    for entry in patch["items"]:
        key, refs, category = entry["mapping_key"], entry["analysis_refs"], entry["kind"]
        if key in seen_keys:
            raise ValueError(f"numbering-patch/items/{key}: 映射键重复")
        seen_keys.add(key)
        missing = [ref for ref in refs if ref not in registry]
        if missing:
            raise ValueError(f"numbering-patch/items/{key}/analysis_refs: 引用不存在：{missing}")
        current = by_key.get(key)
        if "prd_id" in entry:
            located = by_id.get(entry["prd_id"])
            if located is None or (current is not None and current is not located) or (located.get("mapping_key", key) != key):
                raise ValueError(f"numbering-patch/items/{key}/prd_id: 编号不存在或映射冲突")
            current = located
        elif current is None and any("mapping_key" not in item and set(item["analysis_refs"]) == set(refs) for item in trace["items"]):
            raise ValueError(f"numbering-patch/items/{key}: 旧追溯匹配不明确，须指定既有 prd_id")
        if current is not None:
            if current["kind"] != category or current["prd_id"] in used_ids:
                raise ValueError(f"numbering-patch/items/{key}: 类别或编号身份冲突")
            used_ids.add(current["prd_id"])
        values = [registry[ref] for ref in refs]
        try:
            tag = min((value.get("tag", "confirmed") for value in values), key=ranks.__getitem__)
            status = "abolished" if any(value.get("status") == "withdrawn" for value in values) else "to_confirm" if any(value.get("status") == "to_reassess" for value in values) else "active"
            digest = _validator.source_digest(refs, registry)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"numbering-patch/items/{key}: 分析条目或摘要不合法：{error}") from error
        if current is None:
            if status == "abolished":
                continue
            prefix = _validator.KINDS[category]
            number = trace["meta"]["counters"].get(prefix, 0) + 1
            trace["meta"]["counters"][prefix] = number
            current = {"prd_id": f"PRD-{prefix}-{number:03d}", "kind": category, "introduced_in": version}
            trace["items"].append(current)
            by_id[current["prd_id"]] = current
        elif current["status"] == "abolished" and status != "abolished":
            raise ValueError(f"numbering-patch/items/{key}: 已废止编号不能恢复")
        current.update(mapping_key=key, analysis_refs=list(refs), tag=tag, status=status, source_digest=digest)
        by_key[key] = current
    _validate_trace(trace, rid)
    return trace


def _snapshot(path, optional=False):
    """读取原字节并拒绝符号链接；可选缺失以 None 表示。"""
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError(f"{path}: 不允许符号链接")
    try:
        return path.read_bytes()
    except FileNotFoundError:
        if optional:
            return None
        raise


def _decode(data, path):
    """解析严格 JSON，禁止重复键和非有限数值。"""
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_validator._unique, parse_constant=_validator._constant)
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"{path}: {error}") from error


def assign_ids(requirement_dir: Path, patch: dict, *, related_analyses: Sequence[Path] = (), allow_stale: bool = False, write: bool = False) -> dict:
    """读取需求目录生成候选追溯，默认不写入；返回候选追溯。

    related_analyses 是显式关联分析文件路径；allow_stale 控制是否允许过期分析；
    write 为真才在目录锁及原字节并发检查下原子替换追溯，不写正文、事件或元数据。
    文件、协议、过期状态、未完成事务或并发冲突异常以 ValueError/OSError 报告。
    """
    root = Path(requirement_dir).absolute()
    if root.is_symlink() or any(parent.is_symlink() for parent in root.parents):
        raise ValueError(f"{root}: 不允许符号链接")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if write:
            fcntl.flock(fd, fcntl.LOCK_EX)
        paths = [root / "requirement.json", root / "analysis/analysis-result.json", *(Path(p).absolute() for p in related_analyses), root / "prd/prd-trace.json"]
        originals = [_snapshot(p, optional=(i == len(paths) - 1)) for i, p in enumerate(paths)]
        requirement, analysis = (_decode(originals[i], paths[i]) for i in (0, 1))
        related = [_decode(originals[i], paths[i]) for i in range(2, len(paths) - 1)]
        previous = _decode(originals[-1], paths[-1]) if originals[-1] is not None else None
        if analysis.get("meta", {}).get("analysis_status") == "stale" and not allow_stale:
            raise ValueError("analysis/meta/analysis_status: 过期分析须明确允许")
        auxiliary = [root / "analysis/source-manifest.json", root / "prd/gap-requests.json", *(Path(path).absolute().with_name("source-manifest.json") for path in related_analyses)]
        auxiliary_before = [_snapshot(path, optional=True) for path in auxiliary]
        if write:
            spec = importlib.util.spec_from_file_location("prd_numbering_gate", Path(__file__).with_name("check_gate.py"))
            gate_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gate_module)
            gate = gate_module.check_gate(root, allow_stale=allow_stale, related_analyses=related_analyses)
            if not gate["allowed"]:
                raise ValueError("分析门禁拒绝独立编号写入：" + json.dumps(gate["diagnostics"], ensure_ascii=False))
        version = requirement.get("prd", {}).get("version", "0.1")
        trace = allocate_ids(patch, analysis, requirement, previous_trace=previous, related_analyses=related, version=version)
        if write:
            body_path = root / "prd/prd.md"
            body = _snapshot(body_path, optional=True)
            if previous is not None:
                if body is not None and previous["meta"]["content_hash"] != _validator._sha(body):
                    raise ValueError("正文含未处理手工修改，独立编号写入不得重置其摘要")
                trace["meta"]["content_hash"] = previous["meta"]["content_hash"]
            elif body is not None:
                raise ValueError("没有既有追溯却存在正文，不自动接纳旧稿摘要")
            journal = root / "prd/.prd-transaction.json"
            if journal.exists() or journal.is_symlink():
                raise ValueError(f"{journal}: 存在未完成草稿事务，须先恢复")
            for i, path in enumerate(paths):
                if _snapshot(path, optional=(i == len(paths) - 1)) != originals[i]:
                    raise ValueError(f"{path}: 文件并发变化，须重新读取")
            if any(_snapshot(path, optional=True) != original for path, original in zip(auxiliary, auxiliary_before)):
                raise ValueError("来源清单或缺口上下文并发变化，须重新读取")
            target = paths[-1]
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".prd-trace-", delete=False) as temp:
                temp.write((json.dumps(trace, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))
                temp.flush()
                os.fsync(temp.fileno())
                temp_name = temp.name
            if (any(_snapshot(path, optional=(i == len(paths) - 1)) != originals[i] for i, path in enumerate(paths))
                    or any(_snapshot(path, optional=True) != original for path, original in zip(auxiliary, auxiliary_before))
                    or _snapshot(body_path, optional=True) != body or journal.exists() or journal.is_symlink()):
                raise ValueError("写入前文件或事务状态发生并发变化")
            os.replace(temp_name, target)
        return trace
    finally:
        os.close(fd)


def main():
    """解析命令行并输出 JSON 候选；输入或并发错误输出 JSON 并返回非零。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirement_dir", type=Path)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--allow-stale", action="store_true")
    parser.add_argument("--related-analysis", type=Path, action="append", default=[])
    args = parser.parse_args()
    try:
        patch = _decode(_snapshot(args.patch), args.patch)
        result = assign_ids(args.requirement_dir, patch, related_analyses=args.related_analysis, allow_stale=args.allow_stale, write=args.write)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(json.dumps({"status": "fail", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

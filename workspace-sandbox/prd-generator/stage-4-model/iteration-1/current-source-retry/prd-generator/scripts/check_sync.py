"""只读比较分析与既有 PRD 追溯，报告待同步状态和条目差异；不保存任何文件。"""

import argparse
from collections.abc import Sequence
import importlib.util
import json
from pathlib import Path


def _load(name, filename):
    """从安装目录加载依赖，避免依赖调用方的工作目录或 Python 搜索路径。"""
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_numbering = _load("prd_sync_numbering", "assign_ids.py")
_validator = _numbering._validator
_gate = _load("prd_sync_gate", "check_gate.py")


def compare_sources(analysis: dict, requirement: dict, trace: dict, *, related_analyses=()) -> dict:
    """比较只读分析快照和旧追溯，返回修订状态、既有条目分类及未映射的新来源。

    analysis 是主分析，requirement 提供需求身份和 PRD 分析基准，trace 是既有
    追溯；related_analyses 是显式提供的关联分析文档。items 保留旧编号及引用顺序，
    source_digest 是当前完整来源摘要；added 仅含尚未映射且可分配编号的非撤销来源。
    不修改任何输入，也不根据差异推断修订号。结构、身份、编号、未来基准、缺失引用
    或不可摘要的来源抛出 ValueError；安装依赖故障原样抛出。
    """
    try:
        documents = (analysis, *related_analyses)
        analysis_schema, _ = _validator._analyst()._validators()
        for document in documents:
            errors = _validator._analyst()._format_errors(document, analysis_schema)
            if errors:
                issue = errors[0]
                raise ValueError(f"analysis{issue['path']}: {issue['message']}")
        rid = requirement["common"]["requirement_id"]
        prd = requirement["prd"]
        baseline = prd["based_on_analysis_revision"]
        revision = analysis["meta"]["analysis_revision"]
        if rid != analysis["requirement_id"]:
            raise ValueError("requirement_id: 分析和需求身份不一致")
        if type(baseline) is not int or baseline < 1:
            raise ValueError("requirement/prd/based_on_analysis_revision: 分析基准须为正整数")
        if not isinstance(prd["version"], str) or not _validator.VERSION.fullmatch(prd["version"]):
            raise ValueError("requirement/prd/version: PRD 版本无效")
        if baseline > revision:
            raise ValueError("requirement/prd/based_on_analysis_revision: 分析基准来自未来修订")
        _numbering._validate_trace(trace, rid)
        registry = _numbering._registry(documents)
        items = []
        mapped = set()
        for old in trace["items"]:
            refs = old["analysis_refs"]
            missing = [ref for ref in refs if ref not in registry]
            if missing:
                raise ValueError(f"prd-trace/items/{old['prd_id']}/analysis_refs: 引用不存在：{missing}")
            digest = _validator.source_digest(refs, registry)
            statuses = {registry[ref].get("status") for ref in refs}
            # 摘要相同即未变，避免把已同步的撤销或待重评来源反复判定为变化。
            category = "unchanged" if digest == old["source_digest"] else "withdrawn" if "withdrawn" in statuses else "to_reassess" if "to_reassess" in statuses else "modified"
            items.append({"prd_id": old["prd_id"], "analysis_refs": list(refs), "category": category, "source_digest": digest})
            mapped.update(refs)
        kinds = {prefix: kind for kind, prefix in _validator.KINDS.items()}
        _, source_paths = _validator._registry(documents)
        numbered_paths = {('requirements', key) for key in ('goals', 'scenarios', 'functional_requirements', 'business_rules', 'constraints', 'non_functional_requirements', 'acceptance_criteria')}
        numbered_paths.update(('business_assessment', key) for key in ('flows', 'states', 'boundaries', 'exceptions'))
        added = []
        for ref, item in sorted(registry.items()):
            prefix = item["id"].split("-", 1)[0]
            # 关联资料仅为显式引用提供依据，不能把另一个需求的全部功能自动导入本稿。
            if ref.startswith(rid + "/") and source_paths[ref][:2] in numbered_paths and ref not in mapped and prefix in kinds and item.get("status") != "withdrawn":
                added.append({"analysis_ref": ref, "kind": kinds[prefix]})
        return {"pending": revision > baseline, "based_on_analysis_revision": baseline,
                "analysis_revision": revision, "items": items, "added": added}
    except (KeyError, TypeError, AttributeError, OverflowError) as error:
        raise ValueError(f"requirement/analysis/prd-trace: 输入结构或来源摘要无效：{error}") from error


def check_sync(requirement_dir, *, related_analyses=(), allow_stale=False) -> dict:
    """只读检查需求目录，返回标准门禁诊断、allowed 以及可计算的来源比较数据。

    requirement_dir 是已有需求目录；related_analyses 是显式关联分析文件路径，
    allow_stale 表示用户明确允许基于过期分析继续同步。缺辅助清单按分析门禁降级，
    事件日志不参与差异判定。旧正文和追溯不必符合新来源状态，避免正常撤销被拦截。
    用户文件及输入错误返回 fail 诊断，安装执行故障也返回 fail；不向调用方抛出
    这些异常，不创建锁、事务、缓存、正文或事件文件。
    """
    root = Path(requirement_dir).absolute()
    result = {"status": "fail", "diagnostics": [], "allowed": False,
              "pending": None, "based_on_analysis_revision": None,
              "analysis_revision": None, "items": [], "added": []}
    try:
        paths = tuple(Path(path).absolute() for path in related_analyses)
        gate = _gate.check_gate(root, related_analyses=paths, allow_stale=allow_stale)
        result.update(gate)
        diagnostics = result["diagnostics"]
        events = root / "analysis/analysis-events.jsonl"
        try:
            if events.is_symlink() or any(parent.is_symlink() for parent in events.parents):
                raise ValueError("不读取符号链接事件文件")
            events.read_text(encoding="utf-8")
        except (OSError, ValueError, UnicodeError):
            diagnostics.append(_validator._issue(3, "$", events, "辅助分析事件不可用，仅按条目比较生成变更摘要，不推断变更原因。", "warning"))
        # 不调用完整 PRD 校验：待同步旧稿仍保留旧标签、状态和摘要，这是比较的基准。
        requirement = _validator._read(root / "requirement.json", diagnostics, 10)
        analysis = _validator._read(root / "analysis/analysis-result.json", diagnostics, 1)
        trace = _validator._read(root / "prd/prd-trace.json", diagnostics, 1)
        related = [_validator._read(path, diagnostics, 3) for path in paths]
        if all(document is not None for document in (requirement, analysis, trace, *related)):
            result.update(compare_sources(analysis, requirement, trace, related_analyses=related))
            gaps = _validator._read(root / 'prd/gap-requests.json', diagnostics, 12)
            manifest = _validator._read(root / 'analysis/source-manifest.json', diagnostics, 3, optional=True)
            if gaps is not None and _validator._structure(gaps, 'gap-request', diagnostics, 12, 'gap-requests.json'):
                current = _validator.section_source_digests(analysis, gaps, trace=trace, source_manifest=manifest if manifest is not None else [], related_analyses=related)
                previous = trace['meta'].get('section_source_digests', {})
                result['sections'] = [{'section': key, 'category': 'unknown' if key not in previous else 'unchanged' if previous[key] == digest else 'modified', 'source_digest': digest} for key, digest in current.items()]
                result['section_basis_available'] = all(key in previous for key in current)
        result.update(_validator._result(diagnostics))
        result["allowed"] = gate["allowed"] and result["status"] != "fail"
    except Exception as error:
        result["diagnostics"].append(_validator._issue(3, "$", root, f"同步比较失败：{type(error).__name__}: {error}"))
        result.update(_validator._result(result["diagnostics"]))
        result["allowed"] = False
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """解析 argv 并输出单个 JSON 比较结果，返回 pass/warning/fail 对应的三态退出码。

    argv 省略时读取命令行；不提供写入选项。参数错误由 argparse 抛出 SystemExit，
    业务输入故障由 check_sync 转为 JSON fail 诊断。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirement_dir", type=Path)
    parser.add_argument("--related-analysis", type=Path, action="append", default=[])
    parser.add_argument("--allow-stale", action="store_true")
    args = parser.parse_args(argv)
    result = check_sync(args.requirement_dir, related_analyses=args.related_analysis, allow_stale=args.allow_stale)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return _validator.EXIT_CODES[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

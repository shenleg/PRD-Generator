"""阶段5首个切片：只读对照显式指定的同需求分析版本，不裁决语义、不写历史基线。"""

import argparse
from collections import deque
import hashlib
import importlib.util
import json
from pathlib import Path


_COLLECTIONS = (
    "requirements.goals", "requirements.scenarios", "requirements.functional_requirements",
    "requirements.business_rules", "requirements.constraints", "requirements.non_functional_requirements",
    "requirements.acceptance_criteria", "requirements.scope.in_scope", "requirements.scope.out_of_scope",
    "business_assessment.flows", "business_assessment.states", "business_assessment.boundaries",
    "business_assessment.exceptions", "business_assessment.gaps", "business_assessment.conflicts",
    "questions", "assumptions", "decisions",
)


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"JSON包含重复字段：{key}")
        value[key] = item
    return value


def _invalid(value):
    raise ValueError(f"非法JSON数值：{value}")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique, parse_constant=_invalid)


def _gaps(analysis_path):
    """读取显式分析路径所属需求的缺口，不扫描其他需求或将当前缺口冒作历史快照。"""
    path = analysis_path.parent.parent / "prd" / "gap-requests.json"
    return _load(path) if path.exists() else None


def _validator():
    path = Path(__file__).resolve().with_name("validate_analysis.py")
    spec = importlib.util.spec_from_file_location("comparison_validator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_analysis


def _entries(analysis):
    entries = {}
    for collection in _COLLECTIONS:
        values = analysis
        for key in collection.split("."):
            values = values.get(key, {})
        if isinstance(values, list):
            for item in values:
                entries[item["id"]] = {"collection": collection, "value": item}
    return entries


def _impact(baseline, proposal, related, changes, basis_items):
    # related_ids是泛关联，不保证语义依赖；这里只给有向候选，不自动改任何状态。
    # 联合新旧边避免删除引用后丢掉旧受影响项，但不反向走到共享祖先而误伤兄弟功能。
    graph, current = {}, {}
    for document in [baseline, proposal, *related]:
        requirement = document["requirement_id"]
        for item_id, entry in _entries(document).items():
            reference = f"{requirement}/{item_id}"
            current[reference] = entry
            refs = list(entry["value"].get("related_ids", []))
            if "related_question" in entry["value"]:
                refs.append(entry["value"]["related_question"])
            for target in refs:
                target = target if "/" in target else f"{requirement}/{target}"
                graph.setdefault(target, set()).add(reference)
    seeds = set(changes["added"] + changes["modified"] + changes["missing"] + basis_items)
    paths = {seed: [seed] for seed in sorted(seeds)}
    queue = deque(sorted(seeds))
    while queue:
        node = queue.popleft()
        for dependent in sorted(graph.get(node, [])):
            if dependent in paths:
                continue
            paths[dependent] = [*paths[node], dependent]
            queue.append(dependent)
    visible = {ref: path for ref, path in paths.items() if ref not in seeds and ref in current
               and current[ref]["value"].get("status") not in {"withdrawn", "dropped"}}
    acceptance = sorted(ref for ref in (seeds | set(visible)) if ref in current
                        and current[ref]["collection"] == "requirements.acceptance_criteria"
                        and current[ref]["value"]["status"] != "withdrawn")
    return {"changed": sorted(seeds), "direct": sorted(ref for ref, path in visible.items() if len(path) == 2),
            "indirect": sorted(ref for ref, path in visible.items() if len(path) > 2),
            "paths": dict(sorted(visible.items())), "revalidate_acceptance": acceptance,
            "note": "只覆盖显式关联产生的有向影响候选；未建关联及正文隐含依赖仍须语义复核，图可达不等于已批准变更。"}


def _compare(baseline, proposal, related, old_sources, new_sources):
    old, new = _entries(baseline), _entries(proposal)
    requirement = baseline["requirement_id"]
    changes = {"added": [], "modified": [], "missing": [], "unchanged": []}
    details = []
    for item_id in sorted(set(old) | set(new)):
        kind = "added" if item_id not in old else "missing" if item_id not in new else "unchanged" if old[item_id] == new[item_id] else "modified"
        reference = f"{requirement}/{item_id}"
        changes[kind].append(reference)
        if kind != "unchanged":
            details.append({"reference": reference, "change": kind, "before": old.get(item_id), "after": new.get(item_id)})
    before_sources = {s["source_id"]: s for s in old_sources}
    after_sources = {s["source_id"]: s for s in new_sources}
    source_changes = sorted(s for s in set(before_sources) | set(after_sources) if before_sources.get(s) != after_sources.get(s))
    basis_items = sorted({f"{requirement}/{item_id}" for entries in (old, new) for item_id, entry in entries.items()
                          if any(s.get("source_id") in source_changes for s in entry["value"].get("sources", []))})
    sections = ("context", "value_assessment", "ux_assessment", "technical_feasibility", "impact_analysis", "completion_checks")
    non_item_changes = [name for name in sections if baseline.get(name) != proposal.get(name)]
    return {"status": "pass", "requirement_id": requirement, "baseline_revision": baseline["meta"]["analysis_revision"],
            "proposal_revision": proposal["meta"]["analysis_revision"], "changes": changes, "details": details,
            "impact": _impact(baseline, proposal, related, changes, basis_items),
            "source_changes": source_changes, "source_changed_items": basis_items, "non_item_changes": non_item_changes,
            "meta_changes": [name for name in sorted(set(baseline["meta"]) | set(proposal["meta"])) if baseline["meta"].get(name) != proposal["meta"].get(name)],
            "baseline_modified": False, "limits": "仅显式分析版本的机械条目差异；不是删除授权，不证明资料已发布，不识别自然语言矛盾或重复，不代表变更已获批准。"}


def _check_adopted(path, root, related):
    analysis = _load(path)
    manifest = _load(path.with_name("source-manifest.json"))
    validation = _validator()(analysis, manifest, related_analyses=related, gap_requests=_gaps(path))
    if validation["status"] == "fail":
        return {"status": "fail", "validation": validation, "baseline_modified": False}
    review = analysis.get("context", {}).get("history_review")
    if review is None or review["status"] == "not_performed":
        return {"status": "warning", "needs_reassessment": False, "message": "未做历史对照；没有已采用的历史指纹可检查，不表示无冲突。", "changed_sources": [], "baseline_modified": False}
    if root is None:
        raise ValueError("检查采用来源须显式提供--project-root；不猜测来源路径基准。")
    root = root.absolute()
    if any(p.is_symlink() for p in (root, *root.parents)) or not root.is_dir():
        raise ValueError("项目根必须为无符号链接的目录。")
    selected = set(review["source_ids"])
    changed = []
    for source in manifest:
        if source["source_id"] not in selected:
            continue
        # 同一路径原地升级时，只有较新版本已显式采用，才允许用不可变归档核验旧版。
        # 仅建归档但未采用新版本时仍查live路径，不能掩盖未处理的依据变化。
        archived = source.get("archived_path")
        newer_adopted = any(s["source_id"] in selected and s["path"] == source["path"] and s["revision"] > source["revision"] for s in manifest)
        source_path = archived if archived and newer_adopted else source["path"]
        relative = Path(source_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in source_path:
            raise ValueError("采用来源须为显式项目根内的相对路径。")
        current = root
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                raise ValueError("采用来源路径不能含符号链接。")
        if not current.is_file():
            changed.append({"source_id": source["source_id"], "path": source["path"], "reason": "missing"})
        else:
            if current.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("采用来源单文件不得超过8MiB；需按章节拆分。")
            raw = current.read_bytes()
            if len(raw) > 8 * 1024 * 1024:
                raise ValueError("采用来源读取超出8MiB边界。")
            digest = hashlib.sha256(raw).hexdigest()
            if digest != source["adopted_sha256"]:
                changed.append({"source_id": source["source_id"], "path": source["path"], "reason": "content_changed", "adopted_sha256": source["adopted_sha256"], "current_sha256": digest})
    changed_ids = {s["source_id"] for s in changed}
    affected = [f"{analysis['requirement_id']}/{item_id}" for item_id, entry in _entries(analysis).items()
                if any(s.get("source_id") in changed_ids for s in entry["value"].get("sources", []))]
    # 已处于stale的采用声明也不能因文件暂时相同而被自动解除。
    needs = bool(changed) or review["status"] == "stale"
    return {"status": "warning" if needs or validation["status"] == "warning" else "pass", "needs_reassessment": needs,
            "changed_sources": changed, "direct_source_items": sorted(affected), "validation": validation,
            "next_action": "由分析侧读取新资料、产出补丁保存stale/not_ready并重评；本检查不写入任何文件。" if needs else "采用指纹未变化；不代表已检索未采用资料或语义无冲突。", "baseline_modified": False}


class _Parser(argparse.ArgumentParser):
    """将CLI参数错误交给main输出单一JSON；继承标准解析参数接口。"""

    def error(self, message):
        """参数错误时抛出ValueError，不返回；main负责转成结构化诊断。"""
        raise ValueError(message)


def main(argv=None) -> int:
    """解析argv显式基线/提议路径，输出只读对照JSON并返回0/1/2。

    两份结果分别由唯一校验器检查，不把同需求两版本当跨需求资料混入注册表。
    输入、文件或JSON错误返回fail；安装/编程错误直接抛出。无基线时降级，不自动搜索。
    """
    parser = _Parser(description="只读对照同需求分析版本；基线是否现行已发布须由用户另行提供依据")
    parser.add_argument("--baseline", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--proposal", type=Path)
    mode.add_argument("--check-sources", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--related-analysis", type=Path, action="append", default=[])
    try:
        args = parser.parse_args(argv)
        related = [(_load(path), _load(path.with_name("source-manifest.json"))) for path in args.related_analysis]
        if args.check_sources is not None:
            if args.baseline is not None:
                raise ValueError("--check-sources不与--baseline混用。")
            result = _check_adopted(args.check_sources, args.project_root, related)
        else:
            proposal = _load(args.proposal)
            validate = _validator()
            validations = {"proposal": validate(proposal, _load(args.proposal.with_name("source-manifest.json")), related_analyses=related, gap_requests=_gaps(args.proposal))}
            baseline = None
            if args.baseline is not None:
                baseline = _load(args.baseline)
                validations["baseline"] = validate(baseline, _load(args.baseline.with_name("source-manifest.json")), related_analyses=related, gap_requests=_gaps(args.baseline))
            if any(v["status"] == "fail" for v in validations.values()):
                result = {"status": "fail", "message": "输入未通过唯一校验器，不生成差异。", "validations": validations, "baseline_modified": False}
            elif baseline is None:
                result = {"status": "warning", "action": "degraded", "message": "未指定历史基线，未做历史对照，不表示无冲突。", "validations": validations, "baseline_modified": False}
            elif baseline["requirement_id"] != proposal["requirement_id"]:
                raise ValueError("同版本差异仅支持同需求；跨需求语义对照由分析流程处理。")
            else:
                result = _compare(baseline, proposal, [analysis for analysis, _ in related], _load(args.baseline.with_name("source-manifest.json")), _load(args.proposal.with_name("source-manifest.json")))
                result["validations"] = validations
                if any(v["status"] == "warning" for v in validations.values()):
                    result["status"] = "warning"
    except (OSError, ValueError, UnicodeError) as error:
        result = {"status": "fail", "message": str(error), "baseline_modified": False}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return {"pass": 0, "warning": 1, "fail": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

"""只读检查分析输入和需求元数据，决定是否允许生成 PRD 草稿。"""

import argparse
from collections.abc import Sequence
import importlib.util
import json
from pathlib import Path
import sys


def _validator():
    """加载并列 PRD 校验器以复用其上游读取逻辑；安装损坏时抛出异常。"""
    path = Path(__file__).resolve().with_name("validate_prd.py")
    spec = importlib.util.spec_from_file_location("prd_gate_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_gate(requirement_dir: Path, *, allow_stale: bool = False, related_analyses: Sequence[Path] = ()) -> dict:
    """只读检查需求目录并返回门禁状态、诊断和生成上下文。

    allow_stale 表示调用方明确允许过期草稿；related_analyses 是显式关联分析路径。
    用户输入与安装故障均返回 fail 诊断，不写入任何文件；不执行生成或发布。
    """
    result = {"status": "fail", "diagnostics": [], "allowed": False, "draft_kind": None,
              "analysis_revision": None, "base_prd_version": None, "uncovered_analysis": []}
    diagnostics = result["diagnostics"]
    root = Path(requirement_dir).absolute()
    try:
        validator = _validator()
        analysis_path = root / "analysis/analysis-result.json"
        analysis = validator._read(analysis_path, diagnostics, 1)
        metadata = validator._read(root / "requirement.json", diagnostics, 10)
        gaps_path = root / "prd/gap-requests.json"
        gaps = validator._read(gaps_path, diagnostics, 12) if validator._has_link(gaps_path) or gaps_path.exists() else None
        if metadata is not None:
            common = metadata.get("common") if isinstance(metadata, dict) else None
            if not isinstance(common, dict) or any(not isinstance(common.get(k), str) or not common[k].strip() for k in ("requirement_id", "title", "project_id", "created_at")):
                diagnostics.append(validator._issue(10, "$", root / "requirement.json/common", "需求 common 块缺失或不完整，不创建需求。"))
            prd = metadata.get("prd") if isinstance(metadata, dict) else None
            if isinstance(metadata, dict) and "prd" in metadata:
                if not isinstance(prd, dict) or not isinstance(prd.get("version"), str) or not validator.VERSION.fullmatch(prd["version"]):
                    diagnostics.append(validator._issue(10, "$", root / "requirement.json/prd/version", "PRD 版本无效；不迁移旧整数版本。"))
                else:
                    result["base_prd_version"] = prd["version"]
        if analysis is not None:
            _, upstream = validator.validate_upstream(root, analysis, diagnostics, related_analyses=related_analyses, gaps=gaps)
            for issue in upstream["diagnostics"]:
                diagnostics.append(validator._issue(12 if issue["rule"] == 12 else 3, issue["item_id"], str(analysis_path) + issue["path"], "上游校验：" + issue["message"], issue["level"]))
            if upstream["status"] != "fail":
                meta = analysis["meta"]
                result["analysis_revision"] = meta["analysis_revision"]
                result["uncovered_analysis"] = [key for key in ("value_assessment", "technical_feasibility", "impact_analysis") if not analysis.get(key)]
                if not analysis.get("context", {}).get("domain_terms"):
                    result["uncovered_analysis"].append("context.domain_terms")
                if isinstance(metadata, dict) and isinstance(metadata.get("common"), dict) and metadata["common"].get("requirement_id") != analysis["requirement_id"]:
                    diagnostics.append(validator._issue(10, "$", root / "requirement.json/common/requirement_id", "需求编号与分析结果不一致。"))
                stale = meta["analysis_status"] == "stale"
                result["draft_kind"] = "stale_draft" if stale else {"not_ready": "risk_draft", "conditionally_ready": "conditional_draft", "ready_for_document": "formal_draft"}[meta["readiness"]]
                if stale and not any(d["level"] == "warning" and d["path"].endswith("/meta/analysis_status") for d in diagnostics):
                    diagnostics.append(validator._issue(3, "$", str(analysis_path) + "/meta/analysis_status", "分析已过期；请先重新评估。", "warning"))
                result["allowed"] = not (stale and not allow_stale)
        result.update(validator._result(diagnostics))
        if result["status"] == "fail":
            result["allowed"] = False
            result["draft_kind"] = None
    except Exception as error:
        result["diagnostics"].append({"rule": 3, "level": "fail", "item_id": "$", "path": str(root), "message": f"校验器安装或执行故障：{type(error).__name__}: {error}"})
        result["status"] = "fail"
        result["allowed"] = False
        result["draft_kind"] = None
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """读取 argv 指定的门禁参数，输出单个 JSON 并返回三态退出码。

    argv 省略时使用命令行；参数错误由 argparse 抛出 SystemExit。
    """
    parser = argparse.ArgumentParser(description="只读检查 PRD 生成门禁。")
    parser.add_argument("requirement_dir", type=Path)
    parser.add_argument("--allow-stale", action="store_true")
    parser.add_argument("--related-analysis", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    result = check_gate(args.requirement_dir, allow_stale=args.allow_stale, related_analyses=args.related_analysis)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"pass": 0, "warning": 1, "fail": 2}[result["status"]]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    raise SystemExit(main())

"""为生成器格式校验创建明确标记的合成工作区；不生成正式业务文档或发布。"""

import hashlib
import json
from pathlib import Path


PROMPT = "草稿，待产品经理确认后发布。"


def digest(value):
    """计算 value 的原始字节或稳定 JSON 摘要并返回带前缀字符串。

    value 为文件字节或可序列化对象；非法对象及非有限数值抛出序列化异常。
    """
    data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def write_json(path, value):
    """把 value 写入临时 path，返回路径；创建父目录，文件或编码错误原样抛出。

    仅供测试独立目录使用，调用方不得传入历史证据路径。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def block(kind, key, content):
    """把 content 包成 kind/key 定位块并返回 Markdown；不进行文件写入或校验，无预期异常。"""
    return f"<!-- prd:{kind} {key} -->\n{content}\n<!-- /prd:{kind} -->"


def make_workspace(root):
    """在独立 root 构造最小合法合成草稿，返回其需求目录。

    所有内容均为校验夹具，不代表真实需求或用户确认；目录已存在则抛出异常以防覆盖。
    文件写入、JSON 序列化异常原样抛出。
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    source = [{"source_id": "SRC-1", "name": "合成测试资料", "path": "synthetic.md", "type": "input_document", "credibility": "仅供格式测试", "last_updated": None, "revision": 1}]
    item = {"id": "FR-1", "content": "合成查询功能，不代表真实业务", "tag": "confirmed", "status": "active", "sources": [{"type": "input_document", "source_id": "SRC-1", "location": "合成资料第1条"}]}
    analysis = {"schema_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "meta": {"analysis_revision": 1, "source_revision": 1, "baseline_revision": None, "input_type": "existing_document", "analysis_status": "completed", "readiness": "ready_for_document"}, "requirements": {"goals": [], "scenarios": [], "functional_requirements": [item], "business_rules": [], "constraints": [], "non_functional_requirements": [], "acceptance_criteria": [], "scope": {"in_scope": [], "out_of_scope": []}}, "business_assessment": {"flows": [], "states": [], "boundaries": [], "exceptions": [], "gaps": [], "conflicts": []}, "ux_assessment": {"ui_dependent": False, "design_pending_items": []}, "questions": [], "assumptions": [], "decisions": [], "completion_checks": [{"item": i, "satisfied": True, "question_refs": [], "reason": "合成校验夹具，不是业务完成证明"} for i in range(1, 12)]}
    metadata = {"common": {"requirement_id": "SYNTHETIC-PRD", "title": "合成格式夹具", "project_id": "synthetic", "created_at": "2026-11-17T00:00:00Z"}, "prd": {"based_on_analysis_revision": 1, "status": "draft", "version": "0.1"}}
    trace = {"schema_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "meta": {"draft_kind": "formal_draft", "generated_under_readiness": "ready_for_document", "content_hash": "sha256:" + "0" * 64, "counters": {"FR": 1}}, "items": [{"prd_id": "PRD-FR-001", "mapping_key": "synthetic-query", "kind": "functional_requirement", "analysis_refs": ["SYNTHETIC-PRD/FR-1"], "tag": "confirmed", "status": "active", "introduced_in": "0.1", "source_digest": digest([{"analysis_ref": "SYNTHETIC-PRD/FR-1", "item": item}])}]}
    info = "\n".join(["| 字段 | 值 |", "| --- | --- |", "| 需求编号 | SYNTHETIC-PRD |", "| 标题 | 合成格式夹具 |", "| PRD 版本 | 0.1 |", "| 状态 | draft |", "| 草稿类型 | formal_draft |", "| 基于的分析修订号 | 1 |", "| 生成时间 | 2026-11-17T00:00:00Z |", "| 未覆盖的分析项 | technical_feasibility、impact_analysis、value_assessment |"])
    sections = [block("section", "info", info), block("section", "changes", "首次合成夹具"), block("section", "scope", "分析结果中无此项"), block("section", "scenarios", "分析结果中无此项"), block("section", "functional_requirements", "| 正式编号与功能需求 | 分析来源 |\n| --- | --- |\n| <!-- prd:item PRD-FR-001 -->PRD-FR-001：合成查询功能，不代表真实业务；分析来源 SYNTHETIC-PRD/FR-1<!-- /prd:item --> | SYNTHETIC-PRD/FR-1 |"), block("section", "business_rules", "分析结果中无此项"), block("section", "boundaries_exceptions", "分析结果中无此项"), block("section", "acceptance_criteria", "分析结果中无此项"), block("section", "residuals", "无适用遗留项"), block("section", "appendix", "SRC-1")]
    text = PROMPT + "\n\n" + "\n\n".join(sections) + "\n"
    trace["meta"]["content_hash"] = digest(text.encode())
    write_json(root / "analysis/analysis-result.json", analysis)
    write_json(root / "analysis/source-manifest.json", source)
    write_json(root / "requirement.json", metadata)
    write_json(root / "prd/prd-trace.json", trace)
    write_json(root / "prd/gap-requests.json", {"schema_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "counters": {"GAPREQ": 0}, "requests": []})
    (root / "prd/prd.md").write_text(text, encoding="utf-8")
    (root / "prd/prd-events.jsonl").write_text(json.dumps({"time": "2026-11-17T00:00:00Z", "prd_version": "0.1", "change_type": "initial_generation", "summary": "合成格式夹具", "affected_prd_ids": ["PRD-FR-001"], "based_on_analysis_revision": 1, "actor": "prd_generator"}, ensure_ascii=False) + "\n", encoding="utf-8")
    return root


def read_json(path):
    """读取测试 path 并返回 JSON；文件、编码及解析错误原样抛出。"""
    return json.loads(path.read_text(encoding="utf-8"))


def refresh_hash(root):
    """在测试主动改正文后刷新 root 的追溯摘要，返回新摘要；文件及结构错误原样抛出。"""
    path = root / "prd/prd-trace.json"
    trace = read_json(path)
    trace["meta"]["content_hash"] = digest((root / "prd/prd.md").read_bytes())
    write_json(path, trace)
    return trace["meta"]["content_hash"]

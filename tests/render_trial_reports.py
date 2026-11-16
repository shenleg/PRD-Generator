"""主会话使用的试跑报告工具：只把已校验 JSON 整理为 13 章视图，不补全业务事实或随 Skill 安装。"""

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("trial_report_validator", ROOT / "skill/requirement-analyst/scripts/validate_analysis.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
ITEM_FIELDS = {
    "requirements": ("goals", "scenarios", "functional_requirements", "business_rules", "constraints", "non_functional_requirements", "acceptance_criteria"),
    "business_assessment": ("flows", "states", "boundaries", "exceptions", "gaps", "conflicts"),
}


def _cell(value) -> str:
    """转义 Markdown 表格分隔符，保留原值语义。"""
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _table(items: list[dict]) -> str:
    """展示通用条目及来源；空数组不被解释为已评估无问题。"""
    if not items:
        return "当前数组为空；不据此推导已完成分析或不存在风险。\n"
    rows = ["| 编号 | 内容 | 标签 | 状态 | 关联 | 来源 |", "| --- | --- | --- | --- | --- | --- |"]
    for item in items:
        links = item.get("related_ids", []) + ([item["related_question"]] if "related_question" in item else [])
        sources = [f"{source.get('source_id', source['type'])}：{source['location']}" for source in item["sources"]]
        details = [f"{key}={item[key]}" for key in ("basis", "verification", "confirmed_by", "confirmed_at") if key in item]
        content = item["content"] + ("；" + "；".join(details) if details else "")
        rows.append("| " + " | ".join(_cell(value) for value in (item["id"], content, item["tag"], item["status"], "、".join(links), "；".join(sources))) + " |")
    return "\n".join(rows) + "\n"


def _questions(questions: list[dict]) -> str:
    """展示已登记问题而不是重新向用户发出提问。"""
    if not questions:
        return "此分类当前没有问题记录。\n"
    sections = []
    for question in questions:
        sections.append(f"- **{question['id']} / {question['priority']} / {question['resolution']} / {question['status']}**：{question['question']}")
        sections.append(f"  - 原因：{question['reason']}；影响：{question['impact']}")
        sections.append(f"  - 关联：{'、'.join(question['related_ids']) or '未关联具体条目'}")
        sections.append(f"  - 选项：{'；'.join(question['options']) or '无交互选项'}")
        sections.append(f"  - 推荐：{question['recommendation'] or '未填写推荐'}")
        if "answer" in question:
            sections.append(f"  - 已记录回答：{question['answer']}")
    return "\n".join(sections) + "\n"


def render_report(analysis: dict, validation: dict) -> str:
    """把已通过校验的 analysis 和实际 validation 渲染为报告文本，不修改输入。

    返回 13 章 Markdown，仅使用现有条目、问题与元数据。调用方负责先校验；
    本函数不作技术结论或自然语言业务补全，内部契约错误直接抛出。
    """
    common = [item for section, names in ITEM_FIELDS.items() for name in names for item in analysis[section].get(name, [])]
    scope = analysis["requirements"].get("scope")
    if scope is not None:
        common += scope["in_scope"] + scope["out_of_scope"]
    meta = analysis["meta"]
    sections = [
        f"# {analysis['requirement_id']}：需求分析报告\n\n本报告由主会话按用户明确调整的分工独立整理。唯一权威为同目录 analysis-result.json；本报告是数据视图，不新增业务结论。\n",
        "## 1. 理解摘要\n\n" + _table(analysis["requirements"]["goals"] + analysis["requirements"]["scenarios"]),
    ]
    if scope is not None:
        sections.append("### 本期包含\n\n" + _table(scope["in_scope"]) + "\n### 本期不含\n\n" + _table(scope["out_of_scope"]))
    else:
        sections.append("范围尚未单独声明，不能把未提及功能视为已经排除。\n")
    sections.append("## 2. 已确认事项\n\n仅下表中 active 的记录表示当前确认内容；其余状态不可视为当前确定结论。\n\n" + _table([item for item in common if item["tag"] == "confirmed"]))
    sections.append("## 3. 业务价值分析\n\n" + ("```json\n" + json.dumps(analysis["value_assessment"], ensure_ascii=False, indent=2) + "\n```\n" if "value_assessment" in analysis else "未单独填写价值评估；缺陷或原因已明确时不要求额外收益论证，不补造数字。\n"))
    business = analysis["business_assessment"]
    sections.append("## 4. 缺口与矛盾\n\n" + _table(business["gaps"] + business["conflicts"]))
    sections.append("## 5. 待回答问题\n\n下列是登记清单，不表示本轮继续提问；实际提问以 turn-NN.json 为准。\n\n" + _questions([q for q in analysis["questions"] if q["status"] == "open" and q["resolution"] != "ask_dev"]))
    sections.append("## 6. 暂定假设\n\n推荐语不等于已采用假设，只有 active 假设支撑当前结论。\n\n" + _table(analysis["assumptions"]))
    sections.append("## 7. 研发确认项\n\n登记当前能力核查，不要求产品作技术实现承诺。\n\n" + _questions([q for q in analysis["questions"] if q["resolution"] == "ask_dev"]))
    sections.append("## 8. 边界与异常\n\ninferred 的候选场景不是已确认的处理规则。\n\n" + _table(business["boundaries"] + business["exceptions"]))
    sections.append("## 9. 验收条件\n\n待重评草案不能作为已完成的可执行验收。\n\n" + _table(analysis["requirements"]["acceptance_criteria"]))
    review = analysis.get("context", {}).get("history_review")
    if review is None:
        sections.append("## 10. 历史需求关联\n\n本结果未声明历史对照；不能宣称与历史无冲突。\n")
    else:
        sections.append("## 10. 历史需求关联\n\n下列为结果声明的实际采用范围，不代表已查全项目或所有冲突已解决。\n```json\n" + json.dumps(review, ensure_ascii=False, indent=2) + "\n```\n")
    if "impact_analysis" in analysis:
        sections.append("已登记的关联与影响：\n```json\n" + json.dumps(analysis["impact_analysis"], ensure_ascii=False, indent=2) + "\n```\n")
    sections.append("## 11. 技术可行性及风险\n\n本阶段不开展技术可行性评估，现有能力由研发确认；缺省或 unknown 均不表示已有依据支持。\n")
    if "technical_feasibility" in analysis:
        sections.append("```json\n" + json.dumps(analysis["technical_feasibility"], ensure_ascii=False, indent=2) + "\n```\n")
    sections.append("## 12. 用户体验和设计建议\n\n仅保留当前界面依赖判断及登记事项，不扩展完整视觉设计。\n\n```json\n" + json.dumps(analysis["ux_assessment"], ensure_ascii=False, indent=2) + "\n```\n")
    blockers = [q["id"] for q in analysis["questions"] if q["priority"] == "P0" and q["status"] == "open"]
    sections.append(f"## 13. 结论与就绪度\n\n- 分析修订号：`{meta['analysis_revision']}`；来源修订号：`{meta['source_revision']}`。\n- 分析状态：`{meta['analysis_status']}`。\n- 就绪度：`{meta['readiness']}`。\n- 实际校验：`{validation['status']}`。数据合法不代表业务已就绪。\n- **仍 open 的 P0：{'、'.join(blockers) or '无'}。**\n")
    if meta["readiness"] == "not_ready":
        sections.append("**核心缺口仍未解决，不能声明核心验收已完整；只可形成标注风险的初步草稿。**\n")
    elif meta["readiness"] == "conditionally_ready":
        sections.append("草稿必须醒目列出遗留问题、假设与研发确认项。\n")
    elif meta["readiness"] == "ready_for_document":
        sections.append("可进入正式 PRD 草稿流程，但不代表研发已全部确认或产品批准发布。\n")
    sections.append("### 决策记录\n\n" + _table(analysis["decisions"]))
    completion = analysis.get("completion_checks", analysis.get("completion_checklist"))
    sections.append("### 完成清单记录\n\n" + ("```json\n" + json.dumps(completion, ensure_ascii=False, indent=2) + "\n```\n" if completion is not None else "当前 JSON 未提供结构化完成清单；不能据此推断全部满足，需对照 readiness-rules.md 核对。\n"))
    history_note = "历史对照范围按第10节声明，未覆盖部分仍未知。" if review is not None else "未声明开展历史检索与基线对照。"
    sections.append("### 未开展的分析\n\n" + history_note + "技术可行性结论和完整视觉分析未开展；报告没有把缺省解释为已评估无问题。\n")
    return "\n".join(sections)


def main() -> None:
    """读取命令行指定试跑目录，先校验全部正式结果再保存报告；文件/JSON/校验错误直接失败。"""
    parser = argparse.ArgumentParser(description="主会话从已校验试跑 JSON 整理报告，不运行模型。")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    documents = []
    for path in sorted(args.directory.glob("requirements/*/analysis/analysis-result.json")):
        documents.append((json.loads(path.read_text(encoding="utf-8")), json.loads(path.with_name("source-manifest.json").read_text(encoding="utf-8")), path))
    if not documents:
        raise ValueError("指定目录尚无正式模型输出。")
    reports = []
    for analysis, manifest, path in documents:
        result = VALIDATOR.validate_analysis(analysis, manifest, related_analyses=[(a, m) for a, m, p in documents if p != path])
        if result["status"] != "pass":
            raise ValueError(f"拒绝基于未通过校验的结果生成报告：{path} {result}")
        reports.append((path.with_name("analysis-report.md"), render_report(analysis, result)))
    for path, content in reports:
        previous = path.read_text(encoding="utf-8") if path.exists() else None
        if previous != content:
            path.write_text(content, encoding="utf-8")
    print(f"主会话已整理 {len(reports)} 份报告；没有修改分析 JSON。")


if __name__ == "__main__":
    main()

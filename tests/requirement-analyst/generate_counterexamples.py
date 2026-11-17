"""从已审核黄金样例生成 11 份机械反例；仅在明确调用 main 时写入反例目录。"""

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "fixtures/requirement-analyst/high-low-voltage"
OUTPUT = ROOT / "fixtures/requirement-analyst/invalid"
CASES = (
    (1, "structure", "删除必填 ux_assessment"),
    (2, "duplicate-id", "重复 FR-1"),
    (3, "enum", "用 fact 代替合法 tag"),
    (4, "readiness", "有 open P0 却声明 ready_for_document"),
    (5, "assumption", "provisional 问题缺少 active 假设"),
    (6, "decision", "excluded P0 缺少 active 决策"),
    (7, "source", "active 目标没有来源"),
    (8, "withdrawn", "active 条目引用 withdrawn 条目"),
    (9, "technical", "supported 技术结论缺依据、可信程度和影响"),
    (10, "conflict", "矛盾引用不存在的 Q-999"),
    (11, "stale", "分析状态为 stale，应警告而非失败"),
)


def make_counterexample(golden: dict, rule: int) -> dict:
    """复制 golden 并制造 rule 对应的违规，返回变体；未知规则抛 ValueError，原对象不变。"""
    data = copy.deepcopy(golden)
    match rule:
        case 1:
            del data["ux_assessment"]
        case 2:
            data["requirements"]["functional_requirements"].append(copy.deepcopy(data["requirements"]["functional_requirements"][0]))
        case 3:
            data["requirements"]["functional_requirements"][0]["tag"] = "fact"
        case 4:
            data["meta"]["readiness"] = "ready_for_document"
        case 5:
            data["questions"][0]["status"] = "provisional"
        case 6:
            data["questions"][0]["status"] = "excluded"
        case 7:
            data["requirements"]["goals"][0]["sources"] = []
        case 8:
            withdrawn = copy.deepcopy(data["requirements"]["functional_requirements"][0])
            withdrawn.update(id="FR-99", status="withdrawn")
            data["requirements"]["functional_requirements"].append(withdrawn)
            data["requirements"]["functional_requirements"][0]["related_ids"] = ["FR-99"]
        case 9:
            data["technical_feasibility"] = {
                "conclusion": "supported", "evidence": [], "credibility": "unknown",
                "potential_impact": [], "related_questions": [], "risks": [],
            }
        case 10:
            data["business_assessment"]["conflicts"] = [{
                "id": "CNF-1", "content": "反例：关联问题不存在", "tag": "inferred",
                "sources": [{"type": "input_document", "source_id": "SRC-1", "location": "合成反例，不是原文事实"}],
                "status": "active", "related_question": "Q-999",
            }]
        case 11:
            data["meta"]["analysis_status"] = "stale"
        case _:
            raise ValueError(f"未知规则编号：{rule}")
    return data


def main() -> None:
    """读取固定黄金样例并生成反例与期望清单；无参数或返回值，文件和 JSON 错误直接抛出。"""
    golden = json.loads((GOLDEN / "analysis-result.json").read_text(encoding="utf-8"))
    manifest = json.loads((GOLDEN / "source-manifest.json").read_text(encoding="utf-8"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    expected = []
    for rule, slug, reason in CASES:
        filename = f"rule-{rule:02d}-{slug}.json"
        (OUTPUT / filename).write_text(json.dumps(make_counterexample(golden, rule), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        expected.append({"file": filename, "rule": rule, "status": "warning" if rule == 11 else "fail", "reason": reason})
    for filename, value in (("source-manifest.json", manifest), ("cases.json", expected)):
        (OUTPUT / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 {len(expected)} 份反例，黄金样例未修改。")


if __name__ == "__main__":
    main()

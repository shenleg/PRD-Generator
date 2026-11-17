"""验证阶段 1 的产物格式；合成数据仅用于格式测试，不是业务黄金样例。"""

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "skill/requirement-analyst/schemas"
SCHEMA_NAMES = (
    "analysis-result.schema.json",
    "question.schema.json",
    "requirement-item.schema.json",
    "source.schema.json",
)


def make_item(item_id: str = "FR-1") -> dict:
    """按 item_id 构造通用条目并返回新字典，不读取外部数据或抛出业务异常。"""
    return {
        "id": item_id,
        "content": "格式测试内容",
        "tag": "confirmed",
        "sources": [{"type": "user_answer", "location": "第 1 轮回答"}],
        "status": "active",
    }


def make_question() -> dict:
    """返回字段齐全的合成问题，不接受参数或抛出业务异常。"""
    return {
        "id": "Q-1",
        "question": "需要确认什么？",
        "priority": "P0",
        "resolution": "ask_product",
        "reason": "核心规则尚未确定",
        "impact": "无法确定验收预期",
        "options": ["支持", "不支持", "其他", "暂不确定"],
        "recommendation": "支持：用于格式测试",
        "status": "open",
        "related_ids": ["FR-1"],
    }


def make_analysis() -> dict:
    """返回仅含必填节的合成结果；不代表分析完成，不抛出业务异常。"""
    return {
        "schema_version": "1.0",
        "requirement_id": "REQ-2026-001",
        "meta": {
            "analysis_revision": 1,
            "source_revision": 1,
            "baseline_revision": None,
            "input_type": "existing_document",
            "analysis_status": "analyzing",
            "readiness": "not_ready",
        },
        "requirements": {
            "goals": [],
            "scenarios": [],
            "functional_requirements": [],
            "business_rules": [],
            "acceptance_criteria": [],
        },
        "business_assessment": {
            "boundaries": [], "exceptions": [], "gaps": [], "conflicts": []
        },
        "ux_assessment": {"ui_dependent": False},
        "questions": [],
        "assumptions": [],
        "decisions": [],
    }


class SchemaTests(unittest.TestCase):
    """检查四份 Schema 的结构契约，不代替 9.6 的跨条目一致性校验。"""

    @classmethod
    def setUpClass(cls) -> None:
        """从仓库加载 Schema 并建立离线引用表；文件缺失或 JSON 错误直接报错。"""
        cls.schemas = {
            name: json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
            for name in SCHEMA_NAMES
        }
        registry = Registry().with_resources(
            ((SCHEMA_DIR / name).as_uri(), Resource.from_contents(schema))
            for name, schema in cls.schemas.items()
        )
        cls.validators = {
            name: Draft202012Validator(
                {"$ref": (SCHEMA_DIR / name).as_uri()},
                registry=registry,
                format_checker=FormatChecker(),
            )
            for name in SCHEMA_NAMES
        }

    def test_schemas_follow_draft_2020_12(self) -> None:
        """四份文件均为合法的 Draft 2020-12 Schema。"""
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                Draft202012Validator.check_schema(schema)

    def test_human_approved_golden_sample(self) -> None:
        """黄金样例忠于已审核要点：三个 P0 保持待回答，不能把格式通过当成需求就绪。"""
        fixture = Path(__file__).resolve().parents[1] / "fixtures/high-low-voltage/analysis-result.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        self.validators[SCHEMA_NAMES[0]].validate(data)
        self.assertEqual(data["meta"]["readiness"], "not_ready")
        self.assertEqual(
            [q["id"] for q in data["questions"] if q["priority"] == "P0" and q["status"] == "open"],
            ["Q-1", "Q-2", "Q-3"],
        )
        self.assertEqual(data["assumptions"], [])
        self.assertEqual(data["decisions"], [])

    def test_minimal_analysis_and_omitted_optional_sections(self) -> None:
        """未开展的可选分析可以省略，必填数组允许为空。"""
        self.validators[SCHEMA_NAMES[0]].validate(make_analysis())

    def test_required_fields_cannot_be_omitted(self) -> None:
        """分别移除根字段和必填节内部字段，防止裁剪掉必填内容。"""
        original = make_analysis()
        for section in (None, "meta", "requirements", "business_assessment", "ux_assessment"):
            fields = original if section is None else original[section]
            for field in fields:
                with self.subTest(section=section, field=field):
                    data = copy.deepcopy(original)
                    del (data if section is None else data[section])[field]
                    self.assertFalse(self.validators[SCHEMA_NAMES[0]].is_valid(data))

    def test_identifiers_and_revision_types(self) -> None:
        """沿用用户编号，修订号为正整数，未做基线对照用 null 表示。"""
        validator = self.validators[SCHEMA_NAMES[0]]
        data = make_analysis()
        data["requirement_id"] = "CUSTOM-42"
        validator.validate(data)
        for value in ("", "invalid id", "REQ-1/FR-1"):
            with self.subTest(requirement_id=value):
                data["requirement_id"] = value
                self.assertFalse(validator.is_valid(data))
        for field in ("analysis_revision", "source_revision", "baseline_revision"):
            for value in (0, -1, 1.5, "1", True):
                with self.subTest(field=field, value=value):
                    data = make_analysis()
                    data["meta"][field] = value
                    self.assertFalse(validator.is_valid(data))
        data = make_analysis()
        data["meta"]["baseline_revision"] = 2
        validator.validate(data)

    def test_all_declared_enums(self) -> None:
        """规格中的全部枚举值可用，中文展示名或未定义值不能代替标识符。"""
        fields = (
            ("meta", "input_type", ["idea", "existing_document", "attachment", "meeting_notes"]),
            ("meta", "analysis_status", ["analyzing", "clarifying", "paused", "completed", "stale"]),
            ("meta", "readiness", ["not_ready", "conditionally_ready", "ready_for_document"]),
            ("value_assessment", "business_value", ["high", "medium", "low", "unknown"]),
            ("value_assessment", "necessity", ["necessary", "deferrable", "needs_justification", "unknown"]),
        )
        for section, field, values in fields:
            for value in [*values, "未定义"]:
                with self.subTest(section=section, field=field, value=value):
                    data = make_analysis()
                    data.setdefault(section, {})[field] = value
                    self.assertEqual(self.validators[SCHEMA_NAMES[0]].is_valid(data), value in values)
        for field, values in (
            ("priority", ["P0", "P1", "P2", "P3"]),
            ("resolution", ["ask_product", "ask_business", "ask_dev", "ask_design", "lookup", "infer"]),
            ("status", ["open", "answered", "provisional", "risk_accepted", "excluded", "dropped"]),
        ):
            for value in [*values, "未定义"]:
                with self.subTest(field=field, value=value):
                    question = make_question()
                    question[field] = value
                    self.assertEqual(self.validators[SCHEMA_NAMES[1]].is_valid(question), value in values)
        for field, values in (
            ("tag", ["confirmed", "inferred", "assumption"]),
            ("status", ["active", "to_reassess", "withdrawn"]),
        ):
            for value in [*values, "未定义"]:
                with self.subTest(field=field, value=value):
                    item = make_item()
                    item[field] = value
                    self.assertEqual(self.validators[SCHEMA_NAMES[2]].is_valid(item), value in values)

    def test_collection_prefixes_and_item_structures(self) -> None:
        """各类条目使用规定前缀，通用字段和嵌套来源引用都接受校验。"""
        collections = {
            "requirements": {
                "goals": "GOAL", "scenarios": "SCN", "functional_requirements": "FR",
                "business_rules": "BR", "constraints": "CON",
                "non_functional_requirements": "NFR", "acceptance_criteria": "AC",
            },
            "business_assessment": {
                "flows": "FLOW", "states": "STATE", "boundaries": "BND",
                "exceptions": "EXC", "gaps": "GAP", "conflicts": "CNF",
            },
        }
        validator = self.validators[SCHEMA_NAMES[0]]
        for section, fields in collections.items():
            for field, prefix in fields.items():
                with self.subTest(collection=field):
                    data = make_analysis()
                    item = make_item(f"{prefix}-1")
                    if field == "conflicts":
                        item["related_question"] = "Q-1"
                    data[section][field] = [item]
                    validator.validate(data)
                    item["id"] = "ASM-1"
                    self.assertFalse(validator.is_valid(data))
        for field in make_item():
            with self.subTest(missing=field):
                item = make_item()
                del item[field]
                self.assertFalse(self.validators[SCHEMA_NAMES[2]].is_valid(item))

    def test_source_requirements_depend_on_type(self) -> None:
        """文档和项目资料必须有来源编号，用户回答仅凭轮次也能定位。"""
        validator = self.validators[SCHEMA_NAMES[3]]
        for source_type in ("input_document", "project_material", "user_answer"):
            with self.subTest(source_type=source_type):
                source = {"type": source_type, "location": "第 1 节或第 1 轮回答"}
                self.assertEqual(validator.is_valid(source), source_type == "user_answer")
                source["source_id"] = "SRC-1"
                validator.validate(source)
                del source["location"]
                self.assertFalse(validator.is_valid(source))
        for source in (
            {"type": "other", "location": "第 1 节"},
            {"type": "user_answer", "location": ""},
            {"type": "input_document", "location": "第 1 节", "source_id": "FR-1"},
        ):
            with self.subTest(invalid_source=source):
                self.assertFalse(validator.is_valid(source))
        item = make_item()
        item["sources"] = [{"type": "input_document", "location": "第 1 节"}]
        self.assertFalse(self.validators[SCHEMA_NAMES[2]].is_valid(item))

    def test_question_fields_and_reference_syntax(self) -> None:
        """问题字段齐全，关联支持本需求与跨需求引用，查资料问题可无交互选项。"""
        validator = self.validators[SCHEMA_NAMES[1]]
        for field in make_question():
            with self.subTest(missing=field):
                question = make_question()
                del question[field]
                self.assertFalse(validator.is_valid(question))
        for reference in ("FR-1", "REQ-2025-012/BR-6", "CUSTOM-42/AC-1"):
            question = make_question()
            question["related_ids"] = [reference]
            validator.validate(question)
        for reference in ("FR-0", "FR-01", "FR-x", "REQ-1/BR-2/AC-3", "UNKNOWN-1"):
            with self.subTest(reference=reference):
                question = make_question()
                question["related_ids"] = [reference]
                self.assertFalse(validator.is_valid(question))
        question = make_question()
        question.update(resolution="lookup", options=[], recommendation="", answer="资料中的回答")
        validator.validate(question)
        question["id"] = "FR-1"
        self.assertFalse(validator.is_valid(question))

    def test_specialized_item_fields(self) -> None:
        """假设、决策和矛盾必须携带额外字段，决策确认时间必须带时区。"""
        cases = {
            "assumptions": dict(make_item("ASM-1"), basis="推荐项", verification="研发通过接口验证", related_question="Q-1"),
            "decisions": dict(make_item("DEC-1"), confirmed_by="产品负责人", confirmed_at="2026-11-15T10:00:00+08:00", related_question="Q-1"),
            "conflicts": dict(make_item("CNF-1"), related_question="Q-1"),
        }
        validator = self.validators[SCHEMA_NAMES[0]]
        for field, item in cases.items():
            data = make_analysis()
            container = data["business_assessment"] if field == "conflicts" else data
            container[field] = [item]
            validator.validate(data)
            for extra in item.keys() - make_item().keys():
                with self.subTest(collection=field, missing=extra):
                    candidate = copy.deepcopy(data)
                    target = candidate["business_assessment"] if field == "conflicts" else candidate
                    del target[field][0][extra]
                    self.assertFalse(validator.is_valid(candidate))
            item["related_question"] = "FR-1"
            self.assertFalse(validator.is_valid(data))
        data = make_analysis()
        data["decisions"] = [dict(cases["decisions"], related_question="Q-1")]
        for timestamp in ("2026-11-15", "2026-11-15T10:00:00", "not-a-date"):
            with self.subTest(timestamp=timestamp):
                data["decisions"][0]["confirmed_at"] = timestamp
                self.assertFalse(validator.is_valid(data))

    def test_scope_uses_items_not_untraceable_strings(self) -> None:
        """范围声明单独存放为可追溯条目，而不是只有正文的字符串。"""
        data = make_analysis()
        data["requirements"]["scope"] = {"in_scope": [make_item()], "out_of_scope": []}
        validator = self.validators[SCHEMA_NAMES[0]]
        validator.validate(data)
        data["requirements"]["scope"]["in_scope"] = ["没有来源的范围声明"]
        self.assertFalse(validator.is_valid(data))
        data["requirements"]["scope"] = {"in_scope": []}
        self.assertFalse(validator.is_valid(data))

    def test_technical_assessment_shape(self) -> None:
        """技术评估保留规则 9 需要的信息，但不在格式测试中判断依据是否充分。"""
        data = make_analysis()
        technical = {
            "conclusion": "unknown", "evidence": [], "credibility": "unknown",
            "potential_impact": [], "related_questions": [], "risks": [],
        }
        data["technical_feasibility"] = technical
        validator = self.validators[SCHEMA_NAMES[0]]
        for conclusion in ("supported", "conditionally_feasible", "risky", "unknown", "conflicting"):
            technical["conclusion"] = conclusion
            validator.validate(data)
        technical["conclusion"] = "可行"
        self.assertFalse(validator.is_valid(data))
        technical["conclusion"] = "unknown"
        for field in technical:
            with self.subTest(missing=field):
                candidate = copy.deepcopy(data)
                del candidate["technical_feasibility"][field]
                self.assertFalse(validator.is_valid(candidate))
        technical["evidence"] = [{"content": "接口资料中的依据", "sources": [{"type": "project_material", "source_id": "SRC-1", "location": "接口第 2 节"}]}]
        technical["related_questions"] = ["Q-1"]
        validator.validate(data)
        del technical["evidence"][0]["sources"][0]["source_id"]
        self.assertFalse(validator.is_valid(data))

    def test_optional_collection_element_types(self) -> None:
        """可选节的数组元素也有明确格式，不能混入任意对象。"""
        fields = (
            ("context", "source_ids", ["SRC-1"]),
            ("context", "domain_terms", ["术语"]),
            *(("value_assessment", field, ["说明"]) for field in ("affected_users", "expected_benefits", "success_metrics", "alternatives")),
            *(("ux_assessment", field, ["说明"]) for field in ("design_pending_items", "visual_recommendations", "interaction_flows")),
            ("impact_analysis", "affected_requirements", ["CUSTOM-42", "REQ-2025-012/BR-6"]),
            ("impact_analysis", "affected_modules", ["元件读取模块"]),
            ("impact_analysis", "proposed_changes", ["修改原有规则"]),
        )
        validator = self.validators[SCHEMA_NAMES[0]]
        for section, field, values in fields:
            with self.subTest(section=section, field=field):
                data = make_analysis()
                data.setdefault(section, {})[field] = values
                validator.validate(data)
                data[section][field] = [{}]
                self.assertFalse(validator.is_valid(data))

    def test_new_fields_are_forward_compatible(self) -> None:
        """新增字段不破坏已有结果读取，同时已知字段仍受格式约束。"""
        data = make_analysis()
        data["future_section"] = {"new_value": 1}
        data["meta"]["future_field"] = True
        data["requirements"]["functional_requirements"] = [dict(make_item(), future_field="扩展")]
        validator = self.validators[SCHEMA_NAMES[0]]
        validator.validate(data)
        data["ux_assessment"]["ui_dependent"] = "false"
        self.assertFalse(validator.is_valid(data))


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""按规格 9.6 验证只读校验 API 和 CLI；业务变体只在测试内存或临时目录中使用。"""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill/requirement-analyst/scripts/validate_analysis.py"
FIXTURE = ROOT / "tests/fixtures/high-low-voltage"
SPEC = importlib.util.spec_from_file_location("validate_analysis", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sample() -> tuple[dict, list]:
    """返回黄金结果与清单的新副本；无参数，文件或 JSON 错误直接抛出。"""
    return tuple(json.loads((FIXTURE / name).read_text(encoding="utf-8")) for name in ("analysis-result.json", "source-manifest.json"))


def item(item_id: str, **extra) -> dict:
    """返回带 user_answer 来源的合成条目，item_id 指定编号，extra 覆盖字段；不抛出业务异常。"""
    return {
        "id": item_id, "content": "仅用于测试的记录", "tag": "inferred",
        "sources": [{"type": "user_answer", "location": "合成测试第 1 轮"}],
        "status": "active", **extra,
    }


def answered_sample() -> tuple[dict, list]:
    """返回已回答核心问题的合成变体，供就绪度边界测试；文件错误直接抛出。"""
    data, manifest = sample()
    for question in data["questions"]:
        question.update(status="answered", answer="合成测试答案，不写回黄金样例")
    data["meta"]["readiness"] = "ready_for_document"
    return data, manifest


def technical() -> dict:
    """返回信息完整的合成技术评估；仅用于校验信息结构，不声明真实系统能力。"""
    return {
        "conclusion": "supported",
        "evidence": [{"content": "合成技术依据", "sources": [{"type": "project_material", "source_id": "SRC-1", "location": "测试章节"}]}],
        "credibility": "已由测试资料说明", "potential_impact": ["测试模块"],
        "related_questions": ["Q-4"], "risks": [],
    }


class ValidationTests(unittest.TestCase):
    """覆盖 11 条规则及其有效边界；业务内容充分性不在机械测试范围内。"""

    def assert_rule(self, data: dict, manifest: list, rule: int, status: str = "fail", **kwargs) -> dict:
        """校验 data 与 manifest 并断言 rule/status，kwargs 传关联资料；不符时抛 AssertionError，返回结果。"""
        result = MODULE.validate_analysis(data, manifest, **kwargs)
        self.assertEqual(result["status"], status, result)
        self.assertIn(rule, [d["rule"] for d in result["diagnostics"]], result)
        for diagnostic in result["diagnostics"]:
            self.assertEqual(set(diagnostic), {"rule", "level", "item_id", "path", "message"})
        return result

    def test_persisted_rule_counterexamples(self) -> None:
        """11 份持久反例均通过真实 CLI 被识别，并返回预期规则及三态结果。"""
        directory = ROOT / "tests/fixtures/invalid"
        cases = json.loads((directory / "cases.json").read_text(encoding="utf-8"))
        self.assertEqual([case["rule"] for case in cases], list(range(1, 12)))
        for case in cases:
            with self.subTest(rule=case["rule"]):
                path = directory / case["file"]
                before = path.read_bytes()
                process = subprocess.run([sys.executable, "-I", str(SCRIPT), str(path)], capture_output=True, text=True, check=False)
                result = json.loads(process.stdout)
                self.assertEqual(result["status"], case["status"], result)
                self.assertEqual(process.returncode, 1 if case["status"] == "warning" else 2)
                self.assertIn(case["rule"], [diagnostic["rule"] for diagnostic in result["diagnostics"]])
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(process.stderr, "")

    def test_golden_is_pass_but_not_ready(self) -> None:
        """合法保留 P0 缺口的黄金结果通过校验，不自动改成已就绪。"""
        data, manifest = sample()
        before = copy.deepcopy((data, manifest))
        self.assertEqual(MODULE.validate_analysis(data, manifest), {"status": "pass", "diagnostics": []})
        self.assertEqual((data, manifest), before)
        self.assertEqual(data["meta"]["readiness"], "not_ready")

    def test_rule_1_rejects_missing_and_wrong_structures(self) -> None:
        """缺失必填节、错误根类型和嵌套容器都返回格式错误，不崩溃。"""
        for value in (None, [], "invalid", {"meta": {}}):
            with self.subTest(value=value):
                self.assert_rule(value, [], 1)
        for field in ("requirements", "business_assessment", "questions"):
            data, manifest = sample()
            data[field] = None
            self.assert_rule(data, manifest, 1)

    def test_rule_2_duplicate_and_dangling_ids(self) -> None:
        """重复条目、重复来源与悬空引用都必须失败。"""
        data, manifest = sample()
        data["requirements"]["functional_requirements"].append(copy.deepcopy(data["requirements"]["functional_requirements"][0]))
        self.assert_rule(data, manifest, 2)
        data, manifest = sample()
        self.assert_rule(data, manifest + manifest, 2)
        data["questions"][0]["related_ids"] = ["FR-999"]
        self.assert_rule(data, manifest, 2)

    def test_rule_3_identifies_enum_and_item(self) -> None:
        """枚举错误归规则 3，并保留对应条目编号。"""
        data, manifest = sample()
        data["requirements"]["functional_requirements"][0]["tag"] = "已确认"
        result = self.assert_rule(data, manifest, 3)
        self.assertEqual(result["diagnostics"][0]["item_id"], "FR-1")

    def test_rule_4_open_p0_blocks_higher_readiness(self) -> None:
        """任何 open P0 都阻止条件就绪或已就绪。"""
        for readiness in ("conditionally_ready", "ready_for_document"):
            data, manifest = sample()
            data["meta"]["readiness"] = readiness
            self.assert_rule(data, manifest, 4)

    def test_rule_4_product_p1_and_dev_exception(self) -> None:
        """产品 P1 需要答案或有效假设，研发 P1 不单独阻塞文档就绪。"""
        data, manifest = answered_sample()
        data["questions"][3]["status"] = "open"
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")
        question = data["questions"][0]
        question.update(priority="P1", status="open")
        self.assert_rule(data, manifest, 4)
        data["meta"]["readiness"] = "conditionally_ready"
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")
        data["meta"]["readiness"] = "ready_for_document"
        data["assumptions"] = [item("ASM-1", tag="assumption", related_question="Q-1", basis="合成推荐项", verification="测试负责人通过示例验证")]
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")

    def test_rule_5_requires_current_assumption(self) -> None:
        """provisional 不能借用撤销或待重评的假设。"""
        data, manifest = sample()
        data["questions"][0]["status"] = "provisional"
        self.assert_rule(data, manifest, 5)
        assumption = item("ASM-1", tag="assumption", related_question="Q-1", basis="合成依据", verification="研发通过测试验证")
        data["assumptions"] = [assumption]
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")
        for status in ("withdrawn", "to_reassess"):
            assumption["status"] = status
            self.assert_rule(data, manifest, 5)

    def test_rule_6_requires_current_decision(self) -> None:
        """excluded P0 必须有 active 的关联决策，不能使用旧撤销决策。"""
        data, manifest = sample()
        data["questions"][0]["status"] = "excluded"
        self.assert_rule(data, manifest, 6)
        decision = item("DEC-1", tag="confirmed", related_question="Q-1", confirmed_by="测试负责人", confirmed_at="2026-11-15T12:00:00Z")
        data["decisions"] = [decision]
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")
        for status in ("withdrawn", "to_reassess"):
            decision["status"] = status
            self.assert_rule(data, manifest, 6)

    def test_rule_7_checks_sources_and_manifest(self) -> None:
        """active 条目须有来源，填写的来源必须存在，清单本身也必须合法。"""
        data, manifest = sample()
        data["requirements"]["goals"][0]["sources"] = []
        self.assert_rule(data, manifest, 7)
        data["requirements"]["goals"][0]["status"] = "to_reassess"
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")
        data, manifest = sample()
        self.assert_rule(data, [], 7)
        self.assert_rule(data, {}, 7)
        broken = copy.deepcopy(manifest)
        del broken[0]["name"]
        self.assert_rule(data, broken, 7)

    def test_rule_8_withdrawn_references_and_reevaluation(self) -> None:
        """有效条目不能依赖撤销条目，待重评条目及 dropped 问题可以保留旧引用。"""
        data, manifest = sample()
        data["requirements"]["functional_requirements"].append(item("FR-99", status="withdrawn"))
        owner = data["requirements"]["functional_requirements"][0]
        owner["related_ids"] = ["FR-99"]
        self.assert_rule(data, manifest, 8)
        owner["status"] = "to_reassess"
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")
        question = data["questions"][0]
        question["related_ids"] = ["FR-99"]
        self.assert_rule(data, manifest, 8)
        question["status"] = "dropped"
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")

    def test_rule_9_assessed_conclusions_require_evidence(self) -> None:
        """非 unknown 技术判断需要完整依据、来源、可信程度和影响。"""
        data, manifest = sample()
        data["technical_feasibility"] = technical()
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")
        for field, value in (("evidence", []), ("credibility", "unknown"), ("potential_impact", []), ("related_questions", ["Q-1"])):
            with self.subTest(field=field):
                data["technical_feasibility"] = technical()
                data["technical_feasibility"][field] = value
                self.assert_rule(data, manifest, 9)
        data["technical_feasibility"] = technical()
        data["technical_feasibility"]["evidence"][0]["sources"] = []
        self.assert_rule(data, manifest, 9)

    def test_rule_9_unknown_does_not_invent_evidence(self) -> None:
        """unknown 和省略技术评估都合法，不为缺少资料编造依据。"""
        data, manifest = sample()
        data["technical_feasibility"] = {"conclusion": "unknown", "evidence": [], "credibility": "unknown", "potential_impact": [], "related_questions": [], "risks": []}
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")
        del data["technical_feasibility"]
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")

    def test_rule_10_conflict_must_point_to_existing_question(self) -> None:
        """矛盾不能只带格式正确但实际不存在的问题编号。"""
        data, manifest = sample()
        data["business_assessment"]["conflicts"] = [item("CNF-1", related_question="Q-999")]
        self.assert_rule(data, manifest, 10)

    def test_conflict_readiness_and_withdrawal(self) -> None:
        """未处理矛盾阻塞就绪，已处理或已撤销矛盾不再单独阻塞。"""
        data, manifest = answered_sample()
        data["questions"][0].update(priority="P2", status="open")
        conflict = item("CNF-1", related_question="Q-1")
        data["business_assessment"]["conflicts"] = [conflict]
        self.assert_rule(data, manifest, 4)
        conflict["status"] = "withdrawn"
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")
        conflict["status"] = "active"
        data["questions"][0]["status"] = "answered"
        self.assertEqual(MODULE.validate_analysis(data, manifest)["status"], "pass")

    def test_rule_11_stale_warns_but_does_not_hide_failure(self) -> None:
        """stale 单独警告，与其他错误同时出现时保留警告而整体失败。"""
        data, manifest = sample()
        data["meta"]["analysis_status"] = "stale"
        self.assert_rule(data, manifest, 11, "warning")
        data["meta"]["readiness"] = "ready_for_document"
        self.assert_rule(data, manifest, 11)
        del data["requirements"]
        result = self.assert_rule(data, manifest, 11)
        self.assertIn(1, [d["rule"] for d in result["diagnostics"]])

    def test_cross_requirement_references_need_explicit_documents(self) -> None:
        """跨需求引用须核对目标真实存在，不能仅凭编号格式通过。"""
        data, manifest = sample()
        other, other_manifest = sample()
        other["requirement_id"] = "CUSTOM-42"
        data["requirements"]["goals"][0]["related_ids"] = ["CUSTOM-42/FR-1"]
        data["impact_analysis"] = {"affected_requirements": ["CUSTOM-42", "CUSTOM-42/BR-1"]}
        self.assert_rule(data, manifest, 2)
        self.assertEqual(MODULE.validate_analysis(data, manifest, related_analyses=[(other, other_manifest)])["status"], "pass")
        other["requirements"]["functional_requirements"][0]["status"] = "withdrawn"
        self.assert_rule(data, manifest, 8, related_analyses=[(other, other_manifest)])

    def test_failures_do_not_mutate_input(self) -> None:
        """校验失败也不得自动修改就绪度、状态或来源。"""
        data, manifest = sample()
        data["meta"]["readiness"] = "ready_for_document"
        before = copy.deepcopy((data, manifest))
        self.assert_rule(data, manifest, 4)
        self.assertEqual((data, manifest), before)

    def run_cli(self, directory: Path, data: dict, manifest: list) -> tuple:
        """把 data/manifest 写入临时 directory 并运行 CLI；返回进程及输入字节，写入错误直接抛出。"""
        analysis_path = directory / "analysis-result.json"
        source_path = directory / "source-manifest.json"
        analysis_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        source_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        before = analysis_path.read_bytes(), source_path.read_bytes()
        process = subprocess.run([sys.executable, "-I", str(SCRIPT), str(analysis_path)], cwd=directory, capture_output=True, text=True, check=False)
        self.assertEqual((analysis_path.read_bytes(), source_path.read_bytes()), before)
        return process, before

    def test_cli_three_states_and_read_only(self) -> None:
        """CLI 的三态输出、退出码及只读行为保持一致。"""
        for status, code in (("pass", 0), ("warning", 1), ("fail", 2)):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temporary:
                data, manifest = sample()
                if status == "warning":
                    data["meta"]["analysis_status"] = "stale"
                elif status == "fail":
                    data["meta"]["readiness"] = "ready_for_document"
                process, _ = self.run_cli(Path(temporary), data, manifest)
                self.assertEqual(process.returncode, code, process.stderr)
                self.assertEqual(json.loads(process.stdout)["status"], status)
                self.assertEqual(process.stderr, "")

    def test_cli_explicit_manifest_and_related_analysis(self) -> None:
        """CLI 可显式指定来源清单及关联分析，无需自动检索工作区。"""
        data, manifest = sample()
        other, other_manifest = sample()
        other["requirement_id"] = "CUSTOM-42"
        data["requirements"]["goals"][0]["related_ids"] = ["CUSTOM-42/FR-1"]
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            external = directory / "external"
            external.mkdir()
            paths = {
                directory / "analysis.json": data,
                directory / "sources.json": manifest,
                external / "analysis.json": other,
                external / "source-manifest.json": other_manifest,
            }
            for path, value in paths.items():
                path.write_text(json.dumps(value), encoding="utf-8")
            before = {path: path.read_bytes() for path in paths}
            process = subprocess.run([
                sys.executable, "-I", str(SCRIPT), str(directory / "analysis.json"),
                "--source-manifest", str(directory / "sources.json"),
                "--related-analysis", str(external / "analysis.json"),
            ], capture_output=True, text=True, check=False)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertEqual(json.loads(process.stdout)["status"], "pass")
            self.assertEqual({path: path.read_bytes() for path in paths}, before)

    def test_cli_file_and_json_errors_are_structured(self) -> None:
        """缺文件、坏 JSON、重复字段和非标准数值都返回 fail，不输出 traceback。"""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / "analysis-result.json"
            for content in (None, "{broken", '{"meta":1,"meta":2}', '{"x":NaN}'):
                with self.subTest(content=content):
                    if content is not None:
                        path.write_text(content, encoding="utf-8")
                    process = subprocess.run([sys.executable, "-I", str(SCRIPT), str(path)], capture_output=True, text=True, check=False)
                    self.assertEqual(process.returncode, 2)
                    self.assertEqual(json.loads(process.stdout)["diagnostics"][0]["rule"], 1)
                    self.assertNotIn("Traceback", process.stderr)
            data, _ = sample()
            path.write_text(json.dumps(data), encoding="utf-8")
            process = subprocess.run([sys.executable, "-I", str(SCRIPT), str(path)], capture_output=True, text=True, check=False)
            self.assertEqual(json.loads(process.stdout)["diagnostics"][0]["rule"], 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)

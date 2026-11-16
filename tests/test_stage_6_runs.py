"""核对阶段6实际模型评估及CLI保存/校验/草稿证据；测试不重新调用模型。"""

import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

from test_update_analysis import load_module, read_json
from historical_sources import recorded_bytes


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "workspace-sandbox/stage-6"
EXPECTED = {"TECH-READ": "supported", "TECH-CSV": "conditionally_feasible", "TECH-LOAD": "risky", "TECH-NETWORK": "conflicting", "TECH-NO-DOC": "unknown", "TECH-OLD": "unknown", "TECH-PARTIAL": "unknown", "TECH-PRODUCT": "unknown"}


class SavedFeasibilityRuns(unittest.TestCase):
    """按合成原文的明确能力和硬约束判分，不把模型自报完成或结构pass当语义正确。"""

    @classmethod
    def setUpClass(cls) -> None:
        """读取实际记录及唯一校验器；没有实跑产物则失败，不跳过。"""
        cls.selection = read_json(BASE / "run-manifest.json")
        cls.model = read_json(BASE / cls.selection["model_evidence"])
        cls.runs = BASE / cls.selection["attempt"]
        cls.manifest = read_json(cls.runs / "run-manifest.json")
        cls.assessments = {a["case_id"]: a for a in cls.model["structured_output"]["assessments"]}
        cls.cases = {a["id"]: a for a in read_json(ROOT / "tests/fixtures/stage-6/cases.json")["cases"]}
        cls.validator = load_module(ROOT / "skill/requirement-analyst/scripts/validate_analysis.py", "technical_saved_validator")

    def analysis_path(self, case: str) -> Path:
        """返回case当前正式分析路径；不读取或写入，缺文件由调用方读取时报告。"""
        return self.runs / "workspace/projects/feasibility-demo/requirements" / case / "analysis/analysis-result.json"

    def test_actual_installed_skill_and_source_provenance(self) -> None:
        """自然语言实际调用当前Skill及技术参考；保存最小脱敏证据并保留初次错行号尝试。"""
        self.assertEqual(self.model["result_subtype"], "success")
        self.assertFalse(self.model["result_is_error"])
        self.assertNotIn("requirement-analyst", self.model["prompt"])
        self.assertTrue(any(c.get("skill") == "requirement-analyst" for c in self.model["calls"]))
        self.assertTrue(any(c.get("project_relative_path", "").endswith("references/feasibility-assessment.md") for c in self.model["calls"]))
        text = json.dumps(self.model, ensure_ascii=False)
        self.assertNotIn(str(ROOT), text)
        self.assertNotRegex(text, r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
        self.assertTrue((BASE / "model-attempt-01/verification.json").is_file())
        for relative, expected in self.model["raw_records"].items():
            self.assertEqual(hashlib.sha256((BASE / relative).read_bytes()).hexdigest(), expected)
        for case, origin in self.model["case_origins"].items():
            original = next(a for a in read_json(BASE / origin)["structured_output"]["assessments"] if a["case_id"] == case)
            self.assertEqual(self.assessments[case], original)
        evolution = self.model["source_evolution"]
        self.assertEqual(hashlib.sha256((BASE / evolution["before_snapshot"]).read_bytes()).hexdigest(), evolution["before_sha256"])
        self.assertEqual(evolution["affected_case"], "TECH-PARTIAL")
        for relative, expected in self.model["source_fingerprints"].items():
            self.assertEqual(hashlib.sha256(recorded_bytes(relative, 6)).hexdigest(), expected, relative)
        for relative, expected in self.manifest["artifacts"].items():
            self.assertEqual(hashlib.sha256((self.runs / relative).read_bytes()).hexdigest(), expected, relative)
        for relative, expected in self.manifest["files"].items():
            self.assertEqual(hashlib.sha256(recorded_bytes(relative, 6)).hexdigest(), expected, relative)

    def test_ra20_five_judgments_follow_specific_evidence(self) -> None:
        """明确查询/改造/风险/硬约束分别对应支持、有条件、风险、冲突；未知不冒充能力。"""
        self.assertEqual({k: v["conclusion"] for k, v in self.assessments.items()}, EXPECTED)
        for case in ("TECH-READ", "TECH-CSV", "TECH-LOAD", "TECH-NETWORK"):
            actual = self.assessments[case]
            self.assertTrue(actual["evidence"], case)
            self.assertTrue(actual["potential_impact"], case)
            self.assertTrue(actual["credibility"], case)
        csv = json.dumps(self.assessments["TECH-CSV"], ensure_ascii=False)
        self.assertIn("尚未", csv)
        self.assertTrue("改造" in csv or "新增" in csv)
        risk = json.dumps(self.assessments["TECH-LOAD"], ensure_ascii=False)
        self.assertIn("100", risk)
        self.assertIn("内存", risk)
        conflict = json.dumps(self.assessments["TECH-NETWORK"], ensure_ascii=False)
        self.assertIn("公网", conflict)
        self.assertTrue("禁止" in conflict or "不允许" in conflict)

    def test_ra21_no_old_or_partial_data_does_not_become_supported(self) -> None:
        """无资料不借其他case证据，旧草稿不作当前证明，标识查询不扩大成明细分页能力。"""
        self.assertEqual(self.assessments["TECH-NO-DOC"]["evidence"], [])
        for case in ("TECH-NO-DOC", "TECH-OLD", "TECH-PARTIAL", "TECH-PRODUCT"):
            actual = self.assessments[case]
            self.assertEqual(actual["conclusion"], "unknown")
            self.assertTrue(actual["dev_questions"], case)
        self.assertIn("2020", self.assessments["TECH-OLD"]["credibility"])
        self.assertTrue("未确认" in self.assessments["TECH-OLD"]["credibility"] or "不足" in self.assessments["TECH-OLD"]["credibility"])
        self.assertTrue(any("明细" in q["question"] for q in self.assessments["TECH-PARTIAL"]["dev_questions"]))

    def test_product_permissions_stay_product_p0_and_readiness_is_separate(self) -> None:
        """跨项目可见范围保留产品P0，不用ask_dev或unknown掩盖业务核心未定。"""
        case = self.assessments["TECH-PRODUCT"]
        self.assertTrue(any(q["priority"] == "P0" and "项目" in q["question"] for q in case["product_questions"]))
        analysis = read_json(self.analysis_path("TECH-PRODUCT"))
        self.assertEqual(analysis["meta"]["readiness"], "not_ready")
        self.assertTrue(any(q["resolution"] == "ask_product" and q["priority"] == "P0" and q["status"] == "open" for q in analysis["questions"]))
        self.assertTrue(any(q["resolution"] == "ask_dev" for q in analysis["questions"]))
        self.assertEqual(read_json(self.analysis_path("TECH-READ"))["technical_feasibility"]["conclusion"], "supported")
        self.assertFalse(any(q["resolution"] == "ask_product" and q["status"] == "answered" for q in analysis["questions"]))
        partial = read_json(self.analysis_path("TECH-PARTIAL"))
        self.assertEqual(partial["meta"]["readiness"], "not_ready")
        self.assertTrue(any(q["resolution"] == "ask_product" and q["priority"] == "P0" for q in partial["questions"]))

    def test_evidence_locations_are_verifiable_and_case_scoped(self) -> None:
        """最终引用章节条款或真实原句，不接受第一次错误数字行号，也不跨case借资料。"""
        ranges = {"A": range(1, 5), "B": range(5, 8), "C": range(8, 11), "D": range(11, 13)}
        for case, assessment in self.assessments.items():
            for evidence in assessment["evidence"]:
                self.assertIn(evidence["material"], self.cases[case]["materials"])
                location = evidence["location"]
                self.assertNotRegex(location, r"第.*行")
                if evidence["material"] == "current-platform.md":
                    matched = re.fullmatch(r"([ABCD])条(\d+)(?:至(\d+))?", location)
                    self.assertIsNotNone(matched, location)
                    self.assertIn(int(matched[2]), ranges[matched[1]])
                    if matched[3]:
                        self.assertIn(int(matched[3]), ranges[matched[1]])
                else:
                    text = (ROOT / "tests/fixtures/stage-6" / evidence["material"]).read_text(encoding="utf-8")
                    if location not in text:
                        self.assertIn(evidence["material"], ("partial-interface.md",))
                        title = text.splitlines()[0].removeprefix("# ")
                        self.assertIn(location, {f"《{title}》{suffix}" for suffix in ("正文第1段", "正文第2段", "开头资料说明")})
                    else:
                        self.assertIn(location, text)

    def test_model_assessments_are_preserved_in_actual_cli_saved_results(self) -> None:
        """模型结论/证据/影响/风险原样进入真实更新器，只有别名和资料引用被机械转换。"""
        self.assertEqual(len(self.manifest["records"]), 24)
        for case, expected in self.assessments.items():
            path = self.analysis_path(case)
            analysis = read_json(path)
            sources = read_json(path.with_name("source-manifest.json"))
            actual = analysis["technical_feasibility"]
            self.assertEqual(actual["conclusion"], expected["conclusion"])
            for field in ("credibility", "potential_impact", "risks"):
                self.assertEqual(actual[field], expected[field])
            self.assertEqual([e["content"] for e in actual["evidence"]], [e["content"] for e in expected["evidence"]])
            self.assertEqual([e["sources"][0]["location"] for e in actual["evidence"]], [e["location"] for e in expected["evidence"]])
            questions = {q["id"]: q for q in analysis["questions"]}
            self.assertEqual([questions[q]["question"] for q in actual["related_questions"]], [q["question"] for q in expected["dev_questions"]])
            self.assertTrue(all(questions[q]["resolution"] == "ask_dev" for q in actual["related_questions"]))
            validation = self.validator.validate_analysis(analysis, sources)
            self.assertEqual(validation["status"], "pass", (case, validation))
            self.assertEqual(len(path.with_name("analysis-events.jsonl").read_text().splitlines()), 1)

    def test_reports_and_consumer_keep_assessment_conditions_and_analysis_unchanged(self) -> None:
        """实际8份报告与草稿保留技术证据/风险，消费者不改分析且不显示旧“未开展”声明。"""
        for case in self.manifest["results"]:
            path = self.analysis_path(case["id"])
            report = path.with_name("analysis-report.md").read_text(encoding="utf-8")
            draft = (path.parent.parent / case["draft"]).read_text(encoding="utf-8")
            for text in (report, draft):
                self.assertIn(case["conclusion"], text)
                self.assertNotIn("本阶段不开展技术可行性评估", text)
            for field, expected in case["before_consumer"].items():
                self.assertEqual(hashlib.sha256((path.parent / field).read_bytes()).hexdigest(), expected)
            self.assertIn("不等于", draft)

    def test_replay_current_cli_does_not_call_model_or_overwrite_evidence(self) -> None:
        """当前工具用同一实际模型输出重放24次CLI，已有目录拒绝覆盖，不重新付费调用模型。"""
        runner = load_module(ROOT / "tests/run_stage_6_trial.py", "replayed_technical_trial")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-trial"
            result = runner.run(output, BASE / self.selection["model_evidence"])
            self.assertEqual([(r["record"], r["status"]) for r in result["records"]], [(r["record"], r["status"]) for r in self.manifest["records"]])
            with self.assertRaises(FileExistsError):
                runner.run(output, BASE / self.selection["model_evidence"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

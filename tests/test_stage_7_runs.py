"""阶段7实际图像分析与CLI交接证据核对；测试不启动浏览器、不重新调用模型。"""

import hashlib
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest

from test_update_analysis import load_module, read_json


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "workspace-sandbox/stage-7"
UX_FIELDS = ("ui_dependent", "design_pending_items", "visual_recommendations", "interaction_flows")


class SavedUxRuns(unittest.TestCase):
    """独立从合成图像与输入判分，区分截图事实、未知行为、设计建议和产品决策。"""

    @classmethod
    def setUpClass(cls) -> None:
        """读取实际尝试及唯一校验器，缺实跑证据必须失败而不跳过。"""
        cls.selection = read_json(BASE / "run-manifest.json")
        cls.model = read_json(BASE / cls.selection["model_evidence"])
        cls.runs = BASE / cls.selection["attempt"]
        cls.manifest = read_json(cls.runs / "run-manifest.json")
        cls.assessments = {a["case_id"]: a for a in cls.model["structured_output"]["assessments"]}
        cls.cases = {a["id"]: a for a in read_json(ROOT / "tests/fixtures/stage-7/cases.json")["cases"]}
        cls.validator = load_module(ROOT / "skill/requirement-analyst/scripts/validate_analysis.py", "ux_trial_validator")

    def path(self, case: str) -> Path:
        """返回case当前正式分析路径；无文件操作，缺失由调用方读取时报错。"""
        return self.runs / "workspace/projects/ux-demo/requirements" / case / "analysis/analysis-result.json"

    def test_actual_image_read_and_source_fingerprints(self) -> None:
        """实际模型得到PNG图像且未读HTML，来源与产物指纹匹配，不用文字假称看图。"""
        self.assertEqual(self.model["result_subtype"], "success")
        self.assertFalse(self.model["result_is_error"])
        self.assertNotIn("requirement-analyst", self.model["prompt"])
        calls = self.model["calls"]
        self.assertTrue(any(c.get("skill") == "requirement-analyst" for c in calls))
        self.assertTrue(any(c.get("project_relative_path", "").endswith("references/ux-visual-assessment.md") for c in calls))
        image = next(c for c in calls if c.get("project_relative_path") == "tests/fixtures/stage-7/reference-list.png")
        self.assertTrue(image["image_payload_present"])
        self.assertFalse(image["is_error"])
        self.assertFalse(any(c.get("project_relative_path", "").endswith("reference-list.html") for c in calls))
        for mapping, root in ((self.model["source_fingerprints"], ROOT), (self.manifest["files"], ROOT), (self.manifest["artifacts"], self.runs)):
            for relative, expected in mapping.items():
                self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), expected, relative)
        text = json.dumps(self.model, ensure_ascii=False)
        self.assertNotIn(str(ROOT), text)
        self.assertNotRegex(text, r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")

    def test_local_screenshot_authorization_and_real_png(self) -> None:
        """截图为实际1360x900图像，沙箱降级须有本次用户授权，不冒充真实系统。"""
        capture = read_json(BASE / "browser-capture.json")
        self.assertEqual(capture["user_selection"], "授权本次本地截图")
        self.assertTrue(capture["not_a_real_product_page"])
        self.assertTrue(capture["interactivity_not_implemented"])
        raw = (ROOT / capture["screenshot"]).read_bytes()
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", raw[16:24]), (1360, 900))
        self.assertIn("127.0.0.1", capture["authorization_scope"])

    def test_ra22_missing_visual_recommends_minimum_materials_without_invention(self) -> None:
        """复杂页面没参考时只列候选和资料需求，无观察事实、不强制高保真。"""
        assessment = self.assessments["UX-MISSING"]
        self.assertTrue(assessment["ui_dependent"])
        self.assertEqual(assessment["observations"], [])
        self.assertTrue(all(p["origin"] == "proposed" for p in assessment["page_list"]))
        text = json.dumps({k: assessment[k] for k in UX_FIELDS}, ensure_ascii=False)
        self.assertIn("低保真", text)
        self.assertTrue("流程" in text and "状态" in text)
        self.assertIn("待", text)
        self.assertTrue("不要求高保真" in text or "不强制高保真" in text)
        self.assertTrue(any(q["resolution"] == "ask_product" and q["priority"] == "P0" for q in assessment["questions"]))
        self.assertEqual(read_json(self.path("UX-MISSING"))["meta"]["readiness"], "not_ready")

    def test_ra23_backend_has_no_page_or_visual_design_questions(self) -> None:
        """纯后端不凭空补管理页、不要求Figma/视觉稿；接口问题仍可正常登记。"""
        assessment = self.assessments["UX-BACKEND"]
        self.assertFalse(assessment["ui_dependent"])
        self.assertEqual(assessment["observations"], [])
        self.assertEqual(assessment["page_list"], [])
        self.assertEqual(assessment["design_pending_items"], [])
        self.assertFalse(any(q["resolution"] == "ask_design" for q in assessment["questions"]))
        for question in assessment["questions"]:
            self.assertNotRegex(question["question"], r"视觉稿|Figma|按钮|页面|配色")
        self.assertIn("无需视觉稿", " ".join(assessment["visual_recommendations"]))

    def test_screenshot_observations_are_visible_facts_not_hidden_behavior(self) -> None:
        """只把可见标题/筛选/表头/状态列为观察，不从他人数据或按钮推出权限与后台行为。"""
        for case in ("UX-REFERENCE", "UX-CLAIM", "UX-STATES"):
            assessment = self.assessments[case]
            text = " ".join(o["content"] for o in assessment["observations"])
            for visible in ("申请列表", "申请金额", "查看"):
                self.assertIn(visible, text)
            self.assertIn("未", text)
            for observation in assessment["observations"]:
                self.assertEqual(observation["material"], "reference-list.png")
                self.assertTrue(observation["location"])
                self.assertNotIn("后台已经支持", observation["content"])
            for page in assessment["page_list"]:
                if page["origin"] == "proposed":
                    self.assertIn("建议", page["content"])
                else:
                    self.assertEqual(page["material"], "reference-list.png")
        claim = self.assessments["UX-CLAIM"]
        notes = " ".join(claim["design_pending_items"] + claim["interaction_flows"])
        self.assertIn("未展示", notes)
        self.assertTrue("不能证明整个系统不存在" in notes or "不认定" in notes)
        self.assertTrue(any(q["resolution"] == "lookup" for q in claim["questions"]))

    def test_core_cancel_retry_and_metric_rules_stay_product_p0(self) -> None:
        """取消已成功项、重试生效与统计口径是产品核心决策，不降成纯设计样式。"""
        for case, pattern in (("UX-STATES", "取消"), ("UX-CLAIM", "重试|重复"), ("UX-REFERENCE", "跨页|选择"), ("UX-DATA", "指标|口径|时间")):
            self.assertTrue(any(q["resolution"] == "ask_product" and q["priority"] == "P0" and re.search(pattern, q["question"]) for q in self.assessments[case]["questions"]), case)
            self.assertEqual(read_json(self.path(case))["meta"]["readiness"], "not_ready")
        data = self.assessments["UX-DATA"]
        self.assertEqual(data["observations"], [])
        self.assertIn("不预设图表类型", " ".join(data["design_pending_items"]))

    def test_saved_assessments_are_exact_and_source_tags_are_traceable(self) -> None:
        """四字段及问题原样保存，已观察与建议页面分别confirmed/inferred且有对应来源。"""
        self.assertEqual(len(self.manifest["records"]), 18)
        for case, original in self.assessments.items():
            path = self.path(case)
            analysis = read_json(path)
            sources = read_json(path.with_name("source-manifest.json"))
            self.assertEqual(analysis["ux_assessment"], {name: original[name] for name in UX_FIELDS})
            self.assertEqual([{key: q[key] for key in original["questions"][i]} for i, q in enumerate(analysis["questions"])], original["questions"])
            self.assertEqual([b["content"] for b in analysis["business_assessment"]["boundaries"]], [o["content"] for o in original["observations"]])
            source_by_id = {s["source_id"]: s for s in sources}
            for i, page in enumerate(analysis["requirements"]["scenarios"]):
                self.assertEqual(page["content"], original["page_list"][i]["content"])
                self.assertEqual(page["tag"], "confirmed" if original["page_list"][i]["origin"] == "observed" else "inferred")
                self.assertTrue(source_by_id[page["sources"][0]["source_id"]]["path"].endswith(original["page_list"][i]["material"]))
            self.assertEqual(self.validator.validate_analysis(analysis, sources)["status"], "pass")

    def test_reports_drafts_preserve_pending_ux_and_do_not_change_analysis(self) -> None:
        """实际报告与草稿保留每项建议/流程，不宣称已验证设计，消费前后分析字节不变。"""
        for result in self.manifest["results"]:
            path = self.path(result["id"])
            report = path.with_name("analysis-report.md").read_text(encoding="utf-8")
            draft = (path.parent.parent / result["draft"]).read_text(encoding="utf-8")
            for text in (report, draft):
                for field in UX_FIELDS[1:]:
                    for content in self.assessments[result["id"]][field]:
                        self.assertIn(content, text)
                self.assertNotIn("仅保留当前界面依赖判断", text)
            for name, expected in result["analysis_before_consumer"].items():
                self.assertEqual(hashlib.sha256((path.parent / name).read_bytes()).hexdigest(), expected)
            self.assertIn("视觉建议不是已确认", draft)

    def test_replay_current_cli_without_model_or_browser_and_refuse_overwrite(self) -> None:
        """已保存图像分析重放18次实际CLI，不重新调用模型/浏览器，旧目录不能覆盖。"""
        runner = load_module(ROOT / "tests/run_stage_7_trial.py", "replayed_ux_trial")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-trial"
            result = runner.run(output, BASE / self.selection["model_evidence"])
            self.assertEqual([(r["record"], r["status"]) for r in result["records"]], [(r["record"], r["status"]) for r in self.manifest["records"]])
            with self.assertRaises(FileExistsError):
                runner.run(output, BASE / self.selection["model_evidence"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

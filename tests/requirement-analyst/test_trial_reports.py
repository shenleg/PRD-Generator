"""验证主会话整理的试跑报告只展示已有 JSON，不改变事实、标签或状态。"""

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("trial_reports", ROOT / "tests/requirement-analyst/render_trial_reports.py")
REPORTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORTS)


class TrialReportTests(unittest.TestCase):
    """检查用户批准的新报告分工，不把报告整理工具作为分析引擎。"""

    def test_report_has_thirteen_sections_and_preserves_input(self) -> None:
        """已有黄金结果生成 13 章视图，渲染前后 JSON 完全相同。"""
        data = json.loads((ROOT / "tests/fixtures/high-low-voltage/analysis-result.json").read_text(encoding="utf-8"))
        before = copy.deepcopy(data)
        report = REPORTS.render_report(data, {"status": "pass", "diagnostics": []})
        self.assertEqual(data, before)
        self.assertEqual(sum(line.startswith("## ") for line in report.splitlines()), 13)
        self.assertIn("主会话", report)
        self.assertIn("not_ready", report)
        self.assertIn("inferred", report)
        self.assertIn("to_reassess", report)
        self.assertIn("只可形成标注风险的初步草稿", report)

    def test_assessed_technical_section_is_not_reported_as_unperformed(self) -> None:
        """已有技术评估应按原结论展示，不能仍套旧阶段的“未开展”说明。"""
        data = json.loads((ROOT / "tests/fixtures/high-low-voltage/analysis-result.json").read_text(encoding="utf-8"))
        data["technical_feasibility"] = {"conclusion": "supported", "evidence": [{"content": "合成技术资料明确存在所需查询能力", "sources": [{"type": "project_material", "source_id": "SRC-1", "location": "合成接口契约A"}]}], "credibility": "合成有效资料，仅测试展示", "potential_impact": ["复用现有查询，不扩大权限"], "related_questions": [], "risks": []}
        before = copy.deepcopy(data)
        report = REPORTS.render_report(data, {"status": "pass", "diagnostics": []})
        self.assertIn("supported", report)
        self.assertIn("合成接口契约A", report)
        self.assertNotIn("本阶段不开展技术可行性评估", report)
        self.assertNotIn("技术可行性结论和完整视觉分析未开展", report)
        self.assertEqual(data, before)

    def test_ux_assessment_is_not_mislabeled_as_ui_flag_only(self) -> None:
        """已有体验分析按原建议展示，不再错误宣称仅作依赖判断或未开展完整分析。"""
        data = json.loads((ROOT / "tests/fixtures/high-low-voltage/analysis-result.json").read_text(encoding="utf-8"))
        data["ux_assessment"].update(design_pending_items=["待设计：提交中及失败反馈"], visual_recommendations=["建议低保真状态参考"], interaction_flows=["候选：选择后展示结果，待确认"])
        before = copy.deepcopy(data)
        report = REPORTS.render_report(data, {"status": "pass", "diagnostics": []})
        self.assertIn("待设计：提交中及失败反馈", report)
        self.assertNotIn("仅保留当前界面依赖判断", report)
        self.assertNotIn("完整视觉分析未开展", report)
        self.assertEqual(data, before)

    def test_tables_escape_markdown_without_changing_data(self) -> None:
        """正文含表格分隔符时仅转义显示，既有标签和正文数据不被改写。"""
        data = json.loads((ROOT / "tests/fixtures/high-low-voltage/analysis-result.json").read_text(encoding="utf-8"))
        data["requirements"]["goals"][0]["content"] = "A|B\n第二行"
        report = REPORTS.render_report(data, {"status": "pass", "diagnostics": []})
        self.assertIn("A\\|B<br>第二行", report)
        self.assertEqual(data["requirements"]["goals"][0]["content"], "A|B\n第二行")


if __name__ == "__main__":
    unittest.main(verbosity=2)

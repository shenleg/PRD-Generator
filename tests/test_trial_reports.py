"""验证主会话整理的试跑报告只展示已有 JSON，不改变事实、标签或状态。"""

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("trial_reports", ROOT / "tests/render_trial_reports.py")
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

    def test_tables_escape_markdown_without_changing_data(self) -> None:
        """正文含表格分隔符时仅转义显示，既有标签和正文数据不被改写。"""
        data = json.loads((ROOT / "tests/fixtures/high-low-voltage/analysis-result.json").read_text(encoding="utf-8"))
        data["requirements"]["goals"][0]["content"] = "A|B\n第二行"
        report = REPORTS.render_report(data, {"status": "pass", "diagnostics": []})
        self.assertIn("A\\|B<br>第二行", report)
        self.assertEqual(data["requirements"]["goals"][0]["content"], "A|B\n第二行")


if __name__ == "__main__":
    unittest.main(verbosity=2)

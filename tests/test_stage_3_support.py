"""验证阶段 3 证据保存与报告辅助功能，不代替业务场景实跑。"""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    """加载 path 并返回测试模块；文件/导入错误直接抛出。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StageThreeSupportTests(unittest.TestCase):
    """保证清单展示及新版输入只包含声明变化。"""

    def test_v2_fixture_has_only_approved_business_changes(self) -> None:
        """新版仅改权限、上限/全量冲突和日志要求，其他业务原文保持。"""
        old = (ROOT / "tests/fixtures/sample-02-task-management.md").read_text(encoding="utf-8")
        expected = old.replace("（初版）", "（第二版）").replace("所有用户都可以操作。", "创建者和管理员可以操作。").replace("最多导出 1000 条。", "最多导出 5000 条。")
        expected = expected.replace("   如果数据量大的话就导出全部结果，不要丢数据。\n", "").replace("7. 任务跑完之后给用户发个通知。", "7. 任务跑完之后给用户发个通知。\n8. 导出操作需要记录操作日志。")
        self.assertEqual((ROOT / "tests/fixtures/sample-02-task-management-v2.md").read_text(encoding="utf-8"), expected)

    def test_report_shows_current_completion_checks_without_mutation(self) -> None:
        """报告优先展示标准 completion_checks，不误说未提供清单或修改 JSON。"""
        support = load_module(ROOT / "tests/test_update_analysis.py", "support_fixtures")
        reports = load_module(ROOT / "tests/render_trial_reports.py", "stage_three_reports")
        analysis = support.read_json(ROOT / "tests/fixtures/high-low-voltage/analysis-result.json")
        analysis["completion_checks"] = support.checks("Q-1")
        before = deepcopy(analysis)
        report = reports.render_report(analysis, {"status": "pass", "diagnostics": []})
        self.assertIn('"question_refs"', report)
        self.assertNotIn("当前 JSON 未提供结构化完成清单", report)
        self.assertEqual(analysis, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)

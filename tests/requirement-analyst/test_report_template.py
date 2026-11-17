"""检查供人阅读的报告模板是否覆盖规格 9.4，并保留与 JSON 的权威关系。"""

from pathlib import Path
import re
import unittest


TEMPLATE = Path(__file__).resolve().parents[2] / "skill/requirement-analyst/templates/analysis-report.md"


class ReportTemplateTests(unittest.TestCase):
    """验证模板结构，不在阶段 1 引入报告渲染器。"""

    def test_required_thirteen_sections(self) -> None:
        """模板按规格包含全部 13 个分析章节。"""
        content = TEMPLATE.read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"^## \d+\. (.+)$", content, re.MULTILINE), [
            "理解摘要", "已确认事项", "业务价值分析", "缺口与矛盾", "待回答问题", "暂定假设",
            "研发确认项", "边界与异常", "验收条件", "历史需求关联", "技术可行性及风险",
            "用户体验和设计建议", "结论与就绪度",
        ])

    def test_authority_tags_and_omission_guidance(self) -> None:
        """模板不自造事实，明确 JSON 权威、信息标签、状态和未分析原因。"""
        content = TEMPLATE.read_text(encoding="utf-8")
        for marker in ("analysis-result.json", "唯一权威", "confirmed", "inferred", "assumption", "withdrawn", "to_reassess", "meta.readiness", "未开展的分析及原因"):
            with self.subTest(marker=marker):
                self.assertIn(marker, content)


if __name__ == "__main__":
    unittest.main(verbosity=2)

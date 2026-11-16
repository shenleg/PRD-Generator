"""检查阶段 2 Skill 的文件契约与测试材料；不把静态检查当作模型行为测试。"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill/requirement-analyst"
SCENARIOS = [*(f"RA-{number:02d}" for number in range(1, 9)), "RA-12", "RA-13"]
REFERENCES = ("analysis-framework.md", "question-strategy.md", "readiness-rules.md")


def read_skill() -> str:
    """读取 Skill 入口并返回正文；无参数，文件或编码错误直接抛出。"""
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


class SkillContractTests(unittest.TestCase):
    """验证入口、渐进引用及回归材料是否存在，不评判业务输出是否充分。"""

    def test_frontmatter_and_invocation(self) -> None:
        """入口命名及触发描述正确，调试阶段保留直接调用且不隔离当前会话。"""
        content = read_skill()
        self.assertTrue(content.startswith("---\n"))
        frontmatter = content.split("---", 2)[1]
        self.assertRegex(frontmatter, r"(?m)^name: requirement-analyst$")
        description = re.search(r"(?m)^description: (.+)$", frontmatter).group(1)
        for trigger in ("理解需求", "分析需求", "完整性", "矛盾", "追问", "变更"):
            self.assertIn(trigger, description)
        self.assertNotIn("user-invocable: false", frontmatter)
        self.assertNotIn("disable-model-invocation: true", frontmatter)
        self.assertNotIn("context: fork", frontmatter)

    def test_entry_stays_short_and_has_ten_principles(self) -> None:
        """入口不超过约定篇幅，十条硬规则集中呈现而不堆叠分析细则。"""
        content = read_skill()
        self.assertLessEqual(len(content.splitlines()), 120)
        rules = content.split("## 硬规则\n", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(len(re.findall(r"^\d+\. ", rules, re.MULTILINE)), 10)

    def test_core_reference_pointers_resolve(self) -> None:
        """三个核心参考文件存在，入口说明何时加载。"""
        content = read_skill()
        for name in REFERENCES:
            with self.subTest(reference=name):
                self.assertIn(f"references/{name}", content)
                self.assertTrue((SKILL / "references" / name).is_file())

    def test_stage_boundaries(self) -> None:
        """本阶段不提前实现更新、检索或消费者脚本。"""
        for filename in ("update_analysis.py", "index_sources.py", "search_project.py", "compare_baseline.py"):
            self.assertFalse((SKILL / "scripts" / filename).exists())
        content = read_skill()
        self.assertIn("validate_analysis.py", content)
        self.assertIn("analysis-result.json", content)
        self.assertIn("analysis-report.md", content)

    def test_all_required_scenarios_have_scripts(self) -> None:
        """十个场景均先有输入、预设回答和核对清单，不能只列验收编号。"""
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                content = (ROOT / "tests/scenarios" / f"{scenario}.md").read_text(encoding="utf-8")
                for marker in (scenario, "输入", "回答", "核对清单", "依据"):
                    self.assertIn(marker, content)

    def test_sample_two_is_raw_input_not_test_oracle(self) -> None:
        """第二样例逐字提取，参考要点和后续预设回答不混入被测输入。"""
        source = (ROOT / "第二样例：仿真任务管理优化.md").read_text(encoding="utf-8")
        fixture = (ROOT / "tests/fixtures/sample-02-task-management.md").read_text(encoding="utf-8")
        self.assertEqual(fixture, source.split("```\n", 1)[1].split("\n```", 1)[0] + "\n")
        expected = (ROOT / "tests/expected/sample-02-expected.md").read_text(encoding="utf-8")
        self.assertIn("用户已认可修订版", expected)
        self.assertNotIn("埋点", fixture)
        self.assertNotIn("预设回答", fixture)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""验证按 Skill 分类后的现行导航、统一发现、独立驱动及历史证据边界。"""

from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]


class RepositoryLayoutTests(unittest.TestCase):
    """防止目录整理造成漏测、断链、安装漂移或历史证据改写。"""

    def test_current_navigation_links_exist(self):
        """当前维护文档中的本地 Markdown 链接必须存在，历史记录不强改链接。"""
        files = [ROOT / "README.md", ROOT / "tests/README.md", ROOT / "tests/requirement-analyst/README.md", ROOT / "tests/prd-generator/README.md", *sorted((ROOT / "docs").rglob("*.md"))]
        for path in files:
            for target in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if target.startswith(("https://", "http://", "mailto:", "#")):
                    continue
                relative = target.split("#", 1)[0]
                self.assertTrue((path.parent / relative).exists(), f"{path.relative_to(ROOT)} -> {target}")

    def test_aggregate_discovery_matches_both_groups(self):
        """统一入口的测试数量等于两组总和，不能成功运行却静默漏掉一组。"""
        counts = [unittest.TestLoader().discover(str(ROOT / "tests" / name)).countTestCases() for name in ("requirement-analyst", "prd-generator")]
        self.assertTrue(all(count > 0 for count in counts))
        combined = unittest.TestLoader().discover(str(ROOT / "tests")).countTestCases()
        self.assertEqual(combined, sum(counts))

    def test_installation_and_root_classification(self):
        """生产安装目标不变，根目录不保留一排文档和测试脚本包装。"""
        installed = ROOT / ".claude/skills/requirement-analyst"
        self.assertEqual(installed.resolve(), ROOT / "skill/requirement-analyst")
        self.assertTrue({path.name for path in ROOT.glob("*.md")} <= {"README.md", "CLAUDE.md", "AGENTS.md"})
        self.assertEqual(sorted(path.name for path in (ROOT / "tests").glob("*.py")), ["test_all.py"])
        self.assertFalse((ROOT / "skill/prd-generator/SKILL.md").exists())

    def test_replay_help_runs_from_other_directory(self):
        """当前公开重放脚本在隔离模式及其他工作目录下仍可加载帮助，不执行试跑。"""
        scripts = sorted((ROOT / "tests/requirement-analyst").glob("run_*.py")) + sorted((ROOT / "tests/prd-generator").glob("run_*.py"))
        self.assertTrue(scripts)
        for path in scripts:
            with self.subTest(script=path.name):
                response = subprocess.run([sys.executable, "-I", "-B", str(path), "--help"], cwd="/tmp", text=True, capture_output=True, timeout=30)
                self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
                self.assertIn("usage:", response.stdout)


if __name__ == "__main__":
    unittest.main()

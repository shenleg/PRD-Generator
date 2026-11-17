"""验证按 Skill 分类后的现行导航、统一发现、独立驱动及历史证据边界。"""

from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import generate_counterexamples
import material_paths


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
        generator = ROOT / "skill/prd-generator/SKILL.md"
        self.assertTrue(generator.is_file())
        entry = generator.read_text(encoding="utf-8")
        self.assertIn("name: prd-generator", entry)
        self.assertNotIn("context: fork", entry)
        self.assertNotIn("disable-model-invocation: true", entry)
        self.assertNotIn("user-invocable: false", entry)
        self.assertLessEqual(len(entry.splitlines()), 120)

    def test_material_roots_are_classified_by_skill(self):
        """场景、夹具及人工参考都按 Skill 分类，分析侧 31 个场景不得遗漏。"""
        for name in ("scenarios", "fixtures", "expected"):
            directory = ROOT / "tests" / name
            self.assertEqual({path.name for path in directory.iterdir()}, {"requirement-analyst", "prd-generator"})
            self.assertTrue(all(path.is_dir() and not path.is_symlink() for path in directory.iterdir()))
        scenarios = ROOT / "tests/scenarios/requirement-analyst"
        self.assertEqual({path.stem for path in scenarios.glob("RA-*.md")}, {f"RA-{i:02d}" for i in range(1, 32)})
        self.assertEqual(generate_counterexamples.GOLDEN, ROOT / "tests/fixtures/requirement-analyst/high-low-voltage")
        self.assertEqual(generate_counterexamples.OUTPUT, ROOT / "tests/fixtures/requirement-analyst/invalid")

    def test_moved_materials_preserve_content_and_only_update_scenario_navigation(self):
        """夹具与认可正文逐字保留，场景只允许已登记的路径替换，不改验证含义。"""
        manifest = json.loads((ROOT / "tests/results/repository-layout/test-materials/migration.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["materials"])
        for entry in manifest["materials"]:
            with self.subTest(path=entry["to"]):
                self.assertFalse((ROOT / entry["from"]).exists())
                raw = (ROOT / entry["to"]).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry.get("current_sha256", entry["sha256"]))
                if "current_sha256" in entry:
                    self.assertTrue(entry["from"].startswith("tests/scenarios/"))
                    original = subprocess.run(["git", "show", f"{manifest['baseline_commit']}:{entry['from']}"], cwd=ROOT, check=True, capture_output=True).stdout
                    self.assertEqual(hashlib.sha256(original).hexdigest(), entry["sha256"])
                    expected = original.decode("utf-8")
                    for before, after in manifest["scenario_navigation_replacements"]:
                        expected = expected.replace(before, after)
                    self.assertEqual(raw.decode("utf-8"), expected)

    def test_historical_material_paths_are_exact_and_scoped(self):
        """只映射实际迁移文件，生成侧、源码及未知路径不被通配重定向。"""
        for old, new in material_paths.MATERIAL_PATHS.items():
            self.assertEqual(material_paths.current_material_path(old), ROOT / new)
        for relative in ("tests/fixtures/prd-generator/sample-catalog.json", "skill/requirement-analyst/SKILL.md", "tests/fixtures/unknown.md"):
            self.assertEqual(material_paths.current_material_path(relative), ROOT / relative)
        for relative in ("/tmp/material.md", "../material.md"):
            with self.assertRaises(ValueError):
                material_paths.current_material_path(relative)

    def test_material_reader_does_not_hide_missing_or_changed_current_bytes(self):
        """新位置缺失时不回退旧副本，变更后的当前字节不能被历史字节掩盖。"""
        old, new = next(iter(material_paths.MATERIAL_PATHS.items()))
        with tempfile.TemporaryDirectory() as temporary, patch.object(material_paths, "ROOT", Path(temporary)):
            original = Path(temporary) / old
            original.parent.mkdir(parents=True)
            original.write_bytes(b"original material")
            with self.assertRaises(FileNotFoundError):
                material_paths.current_material_path(old).read_bytes()
            current = Path(temporary) / new
            current.parent.mkdir(parents=True, exist_ok=True)
            current.write_bytes(b"changed material")
            self.assertEqual(material_paths.current_material_path(old).read_bytes(), b"changed material")
            self.assertNotEqual(hashlib.sha256(current.read_bytes()).hexdigest(), hashlib.sha256(original.read_bytes()).hexdigest())
            with self.assertRaises(FileNotFoundError):
                material_paths.current_material_path("tests/fixtures/unknown.md").read_bytes()

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

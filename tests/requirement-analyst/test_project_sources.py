"""通过命令行验证项目资料索引与受限检索。"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / "skill/requirement-analyst/scripts"


class ProjectSourcesTests(unittest.TestCase):
    """覆盖真实文件系统上的公开命令边界。"""

    def setUp(self):
        """创建隔离项目；无参数、无返回值，创建失败时传播异常。"""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog = self.root / "catalog.json"

    def cli(self, script, *args):
        """运行指定脚本和参数，返回退出码及 JSON；进程或解析错误会传播。"""
        run = subprocess.run([sys.executable, "-I", "-B", str(SCRIPTS / script),
                              "--project-root", str(self.root), *args],
                             capture_output=True, text=True, check=False)
        return run.returncode, json.loads(run.stdout)

    def test_empty_catalog_is_saved_with_warning(self):
        """首次空清单仍可生成一致索引并提示资料缺失。"""
        self.catalog.write_text("[]", encoding="utf-8")
        code, out = self.cli("index_sources.py", "--catalog", str(self.catalog))
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "warning")
        self.assertTrue((self.root / "index/project-index.json").exists())
        self.assertTrue((self.root / "index/source-index.json").exists())

    def test_search_finds_indexed_text_with_provenance(self):
        """索引后的命中保留位置及来源，未声明权威性不得推断。"""
        (self.root / "rule.txt").write_text("背景\n删除用户前检查未完成任务\n结束", encoding="utf-8")
        self.catalog.write_text(json.dumps([{"source_id": "SRC-1", "name": "正式发布", "path": "rule.txt", "type": "project_material", "credibility": "high", "last_updated": "2026-01-01", "revision": 1}]), encoding="utf-8")
        self.assertEqual(self.cli("index_sources.py", "--catalog", str(self.catalog))[0], 0)
        code, out = self.cli("search_project.py", "--query", "删除", "--as-of", "2026-02-01")
        self.assertEqual(code, 0)
        self.assertEqual(out["results"][0]["source_id"], "SRC-1")
        self.assertEqual(out["results"][0]["authority"], "unconfirmed")
        self.assertEqual(out["results"][0]["location"], "line 2")
        self.assertIn("删除", out["results"][0]["excerpt"])
        self.assertEqual(len(out["results"][0]["sha256"]), 64)

    def indexed(self, updated="2026-01-01"):
        """创建并索引合成历史资料；updated 为业务日期，返回原文件，失败时断言。"""
        source = self.root / "history.txt"
        source.write_text("背景\n禁止删除未完成任务\n", encoding="utf-8")
        self.catalog.write_text(json.dumps([{"source_id": "SRC-1", "name": "历史需求", "path": "history.txt", "type": "project_material", "credibility": "medium", "last_updated": updated, "revision": 2, "authority": "historical_published", "requirement_id": "REQ-1", "module": "任务", "tags": ["删除"], "terms": ["任务"]}]), encoding="utf-8")
        self.assertEqual(self.cli("index_sources.py", "--catalog", str(self.catalog))[0], 0)
        return source

    def test_changed_source_never_returns_new_content(self):
        """索引后资料变化时排除正文并明确提示重新索引。"""
        source = self.indexed()
        source.write_text("禁止删除：新内容", encoding="utf-8")
        code, out = self.cli("search_project.py", "--query", "删除", "--as-of", "2026-01-01")
        self.assertEqual(code, 1)
        self.assertEqual(out["results"], [])
        self.assertEqual(out["stale_sources"][0]["source_id"], "SRC-1")

    def test_inconsistent_indexes_fail(self):
        """两份索引世代不同不能作为可用结果。"""
        self.indexed()
        path = self.root / "index/project-index.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["fingerprint"] = "incorrect"
        path.write_text(json.dumps(value), encoding="utf-8")
        code, out = self.cli("search_project.py", "--query", "删除")
        self.assertEqual((code, out["status"]), (2, "fail"))

    def test_filters_and_excerpt_budget(self):
        """组合元数据筛选及摘要总字符上限。"""
        self.indexed()
        code, out = self.cli("search_project.py", "--query", "删除", "--as-of", "2026-01-01", "--requirement", "req-1", "--module", "任务", "--tag", "删除", "--term", "任务", "--max-chars", "5")
        self.assertEqual(code, 1)
        self.assertTrue(out["truncated"])
        self.assertLessEqual(sum(len(x["excerpt"]) for x in out["results"]), 5)
        _, out = self.cli("search_project.py", "--query", "删除", "--module", "其他")
        self.assertEqual(out["results"], [])
        self.assertIn("未找到不代表无冲突", str(out["diagnostics"]))

    def test_invalid_json_and_paths_fail(self):
        """重复键、非法数值及越界或符号链接资料均被拒绝。"""
        for payload in ('[{"source_id":"SRC-1","source_id":"SRC-2"}]', '[NaN]'):
            self.catalog.write_text(payload, encoding="utf-8")
            self.assertEqual(self.cli("index_sources.py", "--catalog", str(self.catalog))[0], 2)
        (self.root / "link").symlink_to(self.root / "missing")
        for path in ("../outside", "link"):
            item = {"source_id": "SRC-1", "name": "x", "path": path, "type": "project_material", "credibility": "low", "last_updated": None, "revision": 1}
            self.catalog.write_text(json.dumps([item]), encoding="utf-8")
            self.assertEqual(self.cli("index_sources.py", "--catalog", str(self.catalog))[0], 2)

    def test_unknown_and_future_dates_warn(self):
        """未知和未来业务日期均须提示复核，不使用文件 mtime 推断。"""
        self.indexed(None)
        code, out = self.cli("search_project.py", "--query", "删除", "--as-of", "2026-01-01")
        self.assertEqual(code, 1)
        self.assertIn("未知", str(out["diagnostics"]))
        self.indexed("2027-01-01")
        code, out = self.cli("search_project.py", "--query", "删除", "--as-of", "2026-01-01")
        self.assertEqual(code, 1)
        self.assertIn("不可信", str(out["diagnostics"]))

    def test_managed_index_cannot_be_source(self):
        """索引目标不能同时是原始资料，避免索引覆盖自己的输入。"""
        self.indexed()
        item = {"source_id": "SRC-2", "name": "index", "path": "index/source-index.json", "type": "project_material", "credibility": "low", "last_updated": None, "revision": 1}
        self.catalog.write_text(json.dumps([item]), encoding="utf-8")
        before = (self.root / item["path"]).read_bytes()
        self.assertEqual(self.cli("index_sources.py", "--catalog", str(self.catalog))[0], 2)
        self.assertEqual((self.root / item["path"]).read_bytes(), before)

    def test_explicit_catalog_cannot_be_overwritten_by_index_outputs(self):
        """catalog自身放在索引目标时拒绝，而不是把用户显式清单改成索引对象。"""
        directory = self.root / "index"
        directory.mkdir()
        for name in ("source-index.json", "project-index.json"):
            catalog = directory / name
            catalog.write_text("[]\n", encoding="utf-8")
            before = catalog.read_bytes()
            code, result = self.cli("index_sources.py", "--catalog", str(catalog))
            self.assertEqual((code, result["status"]), (2, "fail"), result)
            self.assertEqual(catalog.read_bytes(), before)

    def test_completed_null_transaction_allows_index_and_search(self):
        """更新器完成后留下null日志是正常状态，不能把整个已用工作区永久阻塞。"""
        (self.root / ".analysis-transaction.json").write_text("null\n", encoding="utf-8")
        self.indexed()
        code, out = self.cli("search_project.py", "--query", "删除", "--as-of", "2026-02-01")
        self.assertEqual(code, 0, out)
        self.assertTrue(out["results"])

    def test_pending_transaction_and_unknown_arguments_fail(self):
        """未完成事务或未知 CLI 参数不能写入索引。"""
        self.catalog.write_text("[]", encoding="utf-8")
        (self.root / ".analysis-transaction.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.cli("index_sources.py", "--catalog", str(self.catalog))[0], 2)
        self.assertEqual(self.cli("search_project.py", "--query", "x", "--bogus")[0], 2)
        self.assertFalse((self.root / "index").exists())


if __name__ == "__main__":
    unittest.main()

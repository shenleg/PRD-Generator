"""经公开CLI验证知识沉淀门禁及既有检索，不模拟内部写入器。"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skill/requirement-analyst/scripts"


def encoded(value):
    """规范编码建议以绑定批准；返回字节，不支持的JSON值直接抛异常。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class DomainKnowledgeTests(unittest.TestCase):
    """在独立临时项目运行真实CLI，不将合成确认当成人类批准。"""

    def setUp(self):
        """创建合成来源和建议；无返回值，文件系统错误直接抛出。"""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.project = self.directory / "knowledge-demo"
        (self.project / "inputs").mkdir(parents=True)
        self.source = self.project / "inputs/terms.md"
        self.source.write_text("# 合成术语\n业务角色已确认：采购申请是员工提交的采购请求。仅供测试。\n", encoding="utf-8")
        self.proposal = {
            "proposal_version": "1.0", "project_id": "knowledge-demo", "knowledge_id": "DK-001",
            "category": "domain", "kind": "term", "content": "采购申请：员工提交的采购请求。",
            "scope": "仅用于knowledge-demo合成项目，不适用于真实采购制度。", "simulation": True,
            "basis": {"status": "confirmed", "confirmed_by": "合成业务角色（非真实负责人）", "statement": "已确认本例术语定义。"},
            "sources": [{"path": "inputs/terms.md", "location": "合成术语", "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest()}],
        }
        self.proposal_path = self.directory / "proposal.json"
        self.approval_path = self.directory / "approval.json"
        self.target = self.project / "knowledge/domain/DK-001.json"

    def approve(self):
        """为当前建议生成合成批准记录并返回；不是本次人工试用的确认凭据。"""
        return {"proposal_sha256": hashlib.sha256(encoded(self.proposal)).hexdigest(),
                "decision": "approve", "actor": "测试中的合成用户", "user_statement": "同意将DK-001按所示正文及范围写入合成项目。"}

    def run_cli(self, script, *arguments):
        """运行公开命令并返回退出码及JSON；非JSON输出令测试失败。"""
        process = subprocess.run([sys.executable, "-I", "-B", str(SCRIPTS / script), *map(str, arguments)],
                                 cwd=self.directory, text=True, capture_output=True, check=False)
        self.assertTrue(process.stdout.strip(), process.stderr)
        return process.returncode, json.loads(process.stdout)

    def save(self, approval=None):
        """保存测试输入后执行知识写入CLI，返回真实响应；JSON或进程错误传播。"""
        self.proposal_path.write_bytes(encoded(self.proposal))
        arguments = ["--project-root", self.project, "--proposal", self.proposal_path]
        if approval is not None:
            self.approval_path.write_bytes(encoded(approval))
            arguments += ["--approval", self.approval_path]
        return self.run_cli("save_knowledge.py", *arguments)

    def test_approved_entry_preserves_content_scope_sources_and_confirmation(self):
        """具体批准后原样保存建议和确认，源资料保持只读。"""
        before = self.source.read_bytes()
        approval = self.approve()
        code, response = self.save(approval)
        self.assertEqual((code, response["status"], response["written"]), (0, "pass", True))
        self.assertEqual(response["path"], "knowledge/domain/DK-001.json")
        entry = json.loads(self.target.read_text(encoding="utf-8"))
        self.assertEqual(entry["proposal"], self.proposal)
        self.assertEqual(entry["approval"], approval)
        self.assertEqual(entry["proposal_sha256"], approval["proposal_sha256"])
        self.assertEqual(self.source.read_bytes(), before)

    def test_changed_proposal_requires_new_approval(self):
        """批准绑定整份建议，正文、范围、来源或目标变化均不可复用。"""
        approval = self.approve()
        original = json.loads(json.dumps(self.proposal))
        for field, value in (("content", "采购申请等于采购订单。"), ("scope", "所有真实项目"),
                             ("category", "product"), ("knowledge_id", "DK-002"),
                             ("sources", []), ("simulation", False)):
            with self.subTest(field=field):
                self.proposal = {**original, field: value}
                code, response = self.save(approval)
                self.assertEqual(code, 2)
                self.assertFalse(response["written"])
                self.assertFalse((self.project / "knowledge").exists())

    def test_rejection_or_empty_confirmation_never_writes(self):
        """拒绝、空原话、空确认者或含糊记录都不构成具体批准。"""
        for field, value in (("decision", "reject"), ("user_statement", "  "), ("actor", "")):
            with self.subTest(field=field):
                code, response = self.save({**self.approve(), field: value})
                self.assertEqual(code, 2)
                self.assertFalse(response["written"])
                self.assertFalse((self.project / "knowledge").exists())

    def test_only_confirmed_scoped_knowledge_is_eligible(self):
        """批准不能把推断、未知类别、空范围或跨项目建议变成合格知识。"""
        original = json.loads(json.dumps(self.proposal))
        changes = [("basis", {**original["basis"], "status": "inferred"}),
                   ("basis", {**original["basis"], "status": "unconfirmed"}),
                   ("basis", {**original["basis"], "statement": ""}),
                   ("scope", " "), ("simulation", "false"), ("project_id", "another-project"),
                   ("knowledge_id", "../escape"), ("category", "../inputs"),
                   ("kind", "guess"), ("category", "technical")]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                self.proposal = {**original, field: value}
                code, response = self.save(self.approve())
                self.assertEqual(code, 2)
                self.assertFalse(response["written"])
                self.assertFalse((self.project / "knowledge").exists())

    def test_source_change_invalidates_otherwise_matching_approval(self):
        """来源在批准后变化，不能仍按旧依据写入。"""
        approval = self.approve()
        self.source.write_text("来源已经改变，不再支持原术语。\n", encoding="utf-8")
        code, response = self.save(approval)
        self.assertEqual(code, 2)
        self.assertFalse(response["written"])
        self.assertFalse((self.project / "knowledge").exists())

    def test_source_requires_traceable_in_project_regular_text(self):
        """无依据、缺定位、越界、符号链接和缺失资料都须先拒绝。"""
        link = self.project / "inputs/link.md"
        link.symlink_to(self.source)
        source = self.proposal["sources"][0]
        for sources in ([], [{**source, "location": ""}], [{**source, "path": "../outside.md"}],
                        [{**source, "path": "inputs/link.md"}], [{**source, "path": "inputs/missing.md"}]):
            with self.subTest(sources=sources):
                self.proposal["sources"] = sources
                code, response = self.save(self.approve())
                self.assertEqual(code, 2)
                self.assertFalse(response["written"])
                self.assertFalse((self.project / "knowledge").exists())

    def test_existing_knowledge_is_never_overwritten(self):
        """同编号重试与重新批准的新正文均不能覆盖原知识。"""
        self.assertEqual(self.save(self.approve())[0], 0)
        before = self.target.read_bytes()
        self.proposal["content"] = "新正文仍需另提变更，不得覆盖旧条目。"
        code, response = self.save(self.approve())
        self.assertEqual(code, 2)
        self.assertFalse(response["file_created"])
        self.assertEqual(self.target.read_bytes(), before)

    def test_pending_analysis_transaction_prevents_knowledge_write(self):
        """未完成分析事务阻止知识写入，恢复后正常null日志允许写入。"""
        journal = self.project / ".analysis-transaction.json"
        journal.write_text("{}", encoding="utf-8")
        code, response = self.save(self.approve())
        self.assertEqual(code, 2)
        self.assertFalse(response["written"])
        self.assertFalse((self.project / "knowledge").exists())
        journal.write_text("null", encoding="utf-8")
        self.assertEqual(self.save(self.approve())[0], 0)

    def test_symlink_knowledge_directory_is_rejected(self):
        """知识目录不能通过符号链接把写入重定向到其他目录。"""
        outside = self.directory / "outside"
        outside.mkdir()
        (self.project / "knowledge").symlink_to(outside, target_is_directory=True)
        code, response = self.save(self.approve())
        self.assertEqual(code, 2)
        self.assertFalse(response["written"])
        self.assertEqual(list(outside.iterdir()), [])

    def test_business_and_technical_categories_preserve_specific_scope(self):
        """业务规则和技术限制分别写入对应目录，不隐式扩展适用范围。"""
        for kind, category in (("business_rule", "product"), ("technical_constraint", "technical")):
            with self.subTest(kind=kind):
                self.proposal.update({"kind": kind, "category": category})
                code, response = self.save(self.approve())
                self.assertEqual(code, 0, response)
                entry = json.loads((self.project / response["path"]).read_text(encoding="utf-8"))
                self.assertEqual(entry["proposal"]["scope"], self.proposal["scope"])

    def test_approved_knowledge_can_be_explicitly_indexed_and_found(self):
        """正式写入后显式纳入既有索引，命中仍保留合成范围和来源指纹。"""
        self.assertEqual(self.save(self.approve())[0], 0)
        catalog = self.directory / "catalog.json"
        catalog.write_bytes(encoded([{"source_id": "SRC-1", "name": "合成术语，不是真实规范",
                                      "path": "knowledge/domain/DK-001.json", "type": "project_material",
                                      "credibility": "medium", "last_updated": "2026-11-16", "revision": 1,
                                      "authority": "draft", "terms": ["采购申请"]}]))
        self.assertEqual(self.run_cli("index_sources.py", "--project-root", self.project, "--catalog", catalog)[0], 0)
        code, response = self.run_cli("search_project.py", "--project-root", self.project, "--query", "采购申请",
                                      "--as-of", "2026-11-16")
        # 既有检索会截断单行JSON的摘录，warning仍可包含有效命中。
        self.assertEqual(code, 1, response)
        self.assertTrue(response["truncated"])
        found = response["results"][0]
        self.assertEqual(found["path"], "knowledge/domain/DK-001.json")
        self.assertEqual(found["authority"], "draft")
        self.assertIn("不适用于真实采购制度", found["excerpt"])
        self.assertEqual(found["sha256"], hashlib.sha256(self.target.read_bytes()).hexdigest())

    def test_malformed_inputs_return_single_json_without_writing(self):
        """坏JSON、未知字段或缺字段返回fail，不抛无结构堆栈或创建知识。"""
        self.approval_path.write_bytes(encoded(self.approve()))
        for payload in ('{"project_id":"one","project_id":"two"}', '{"x":NaN}', '[]', '{}'):
            with self.subTest(payload=payload):
                self.proposal_path.write_text(payload, encoding="utf-8")
                code, response = self.run_cli("save_knowledge.py", "--project-root", self.project,
                                              "--proposal", self.proposal_path, "--approval", self.approval_path)
                self.assertEqual(code, 2)
                self.assertFalse(response["written"])
                self.assertFalse((self.project / "knowledge").exists())

    def test_missing_approval_never_creates_knowledge(self):
        """只有建议、没有具体批准时必须拒绝，知识目录尚不创建。"""
        code, response = self.save()
        self.assertEqual(code, 2)
        self.assertEqual(response["status"], "fail")
        self.assertFalse(response["written"])
        self.assertFalse((self.project / "knowledge").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

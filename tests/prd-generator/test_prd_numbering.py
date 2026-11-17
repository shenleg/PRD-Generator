"""覆盖编号分配的稳定性、身份约束和独立写入并发边界。"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock_patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    """从 path 加载测试模块 name 并返回；安装或加载失败原样抛出。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = load("numbering_fixture", Path(__file__).with_name("prd_fixture_support.py"))
numbering = load("numbering", ROOT / "skill/prd-generator/scripts/assign_ids.py")


class NumberingTests(unittest.TestCase):
    """使用隔离的合成需求验证编号协议。"""

    def setUp(self):
        """创建合成输入，不改动仓库中的真实需求。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = support.make_workspace(Path(self.temp.name) / "requirement")
        self.analysis = support.read_json(self.root / "analysis/analysis-result.json")
        self.requirement = support.read_json(self.root / "requirement.json")
        self.trace = support.read_json(self.root / "prd/prd-trace.json")
        self.patch = {"patch_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "base_prd_version": "0.1", "base_analysis_revision": 1, "items": [{"mapping_key": "synthetic-query", "kind": "functional_requirement", "analysis_refs": ["SYNTHETIC-PRD/FR-1"]}]}

    def allocate(self, previous=None):
        """用当前夹具和可选旧追溯分配候选；非法输入抛出 ValueError。"""
        return numbering.allocate_ids(self.patch, self.analysis, self.requirement, previous_trace=previous)

    def test_initial_retry_split_and_high_water(self):
        """首次分配、幂等重试及拆分严格递增且不修改输入。"""
        self.requirement.pop("prd")
        self.patch["base_prd_version"] = None
        original = deepcopy(self.analysis)
        first = self.allocate()
        self.assertEqual(first["items"][0]["prd_id"], "PRD-FR-001")
        self.assertEqual(first["meta"]["content_hash"], support.digest(b""))
        self.assertEqual(self.allocate(first), first)
        self.patch["items"].append({**self.patch["items"][0], "mapping_key": "split"})
        second = self.allocate(first)
        self.assertEqual([i["prd_id"] for i in second["items"]], ["PRD-FR-001", "PRD-FR-002"])
        self.assertEqual(original, self.analysis)

    def test_multiple_refs_digest_and_status(self):
        """多来源取最不确定标签、待重评状态，摘要覆盖完整对象且引用排序稳定。"""
        item = deepcopy(self.analysis["requirements"]["functional_requirements"][0])
        item.update(id="FR-2", tag="assumption", status="to_reassess", related_ids=["FR-1"])
        self.analysis["requirements"]["functional_requirements"].append(item)
        self.patch["items"][0]["analysis_refs"].append("SYNTHETIC-PRD/FR-2")
        result = self.allocate(self.trace)["items"][0]
        self.assertEqual((result["tag"], result["status"]), ("assumption", "to_confirm"))
        self.patch["items"][0]["analysis_refs"].reverse()
        self.assertEqual(result["source_digest"], self.allocate(self.trace)["items"][0]["source_digest"])
        item["related_ids"].append("FR-3")
        self.assertNotEqual(result["source_digest"], self.allocate(self.trace)["items"][0]["source_digest"])

    def test_withdrawn_never_reuses_id(self):
        """撤销已有条目保留编号；首次撤销不消耗编号。"""
        self.analysis["requirements"]["functional_requirements"][0]["status"] = "withdrawn"
        self.assertEqual(self.allocate()["items"], [])
        retired = self.allocate(self.trace)
        self.assertEqual(retired["items"][0]["status"], "abolished")
        self.analysis["requirements"]["functional_requirements"][0]["status"] = "active"
        with self.assertRaisesRegex(ValueError, "废止"):
            self.allocate(retired)

    def test_legacy_requires_explicit_id(self):
        """旧追溯匹配相同来源时必须显式绑定旧编号。"""
        del self.trace["items"][0]["mapping_key"]
        with self.assertRaisesRegex(ValueError, "prd_id"):
            self.allocate(self.trace)
        self.patch["items"][0]["prd_id"] = "PRD-FR-001"
        self.assertEqual(self.allocate(self.trace)["items"][0]["mapping_key"], "synthetic-query")

    def test_reject_invalid_inputs(self):
        """拒绝伪造编号、版本冲突、非法字段和落后高水位。"""
        for field, value in (("base_analysis_revision", 2), ("requirement_id", "OTHER"), ("extra", 1)):
            original = deepcopy(self.patch)
            self.patch[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.allocate(self.trace)
            self.patch = original
        self.patch["items"][0]["prd_id"] = "PRD-FR-002"
        with self.assertRaises(ValueError):
            self.allocate(self.trace)
        del self.patch["items"][0]["prd_id"]
        self.trace["meta"]["counters"]["FR"] = 0
        with self.assertRaises(ValueError):
            self.allocate(self.trace)

    def test_empty_patch_still_checks_version_and_draft_kind(self):
        """没有正式条目的候选也不能绕过版本和过期优先级检查。"""
        self.patch["items"] = []
        with self.assertRaisesRegex(ValueError, "version"):
            numbering.allocate_ids(self.patch, self.analysis, self.requirement, version="invalid")
        self.analysis["meta"]["analysis_status"] = "stale"
        with self.assertRaisesRegex(ValueError, "draft_kind"):
            numbering.allocate_ids(self.patch, self.analysis, self.requirement, draft_kind="formal_draft")
        result = numbering.allocate_ids(self.patch, self.analysis, self.requirement)
        self.assertEqual(result["meta"]["draft_kind"], "stale_draft")

    def test_write_and_transaction_guard(self):
        """默认只读；事务存在时拒绝写入，显式写入只改追溯。"""
        target = self.root / "prd/prd-trace.json"
        before = target.read_bytes()
        numbering.assign_ids(self.root, self.patch)
        self.assertEqual(target.read_bytes(), before)
        journal = self.root / "prd/.prd-transaction.json"
        journal.write_text("{}")
        with self.assertRaisesRegex(ValueError, "事务"):
            numbering.assign_ids(self.root, self.patch, write=True)
        self.assertEqual(target.read_bytes(), before)

    def test_write_preserves_body_hash(self):
        """独立维护既有追溯时使用实际正文摘要，不写入候选空正文摘要。"""
        before = (self.root / "prd/prd.md").read_bytes()
        result = numbering.assign_ids(self.root, self.patch, write=True)
        self.assertEqual(result["meta"]["content_hash"], support.digest(before))
        self.assertEqual(support.read_json(self.root / "prd/prd-trace.json"), result)
        self.assertEqual((self.root / "prd/prd.md").read_bytes(), before)

    def test_independent_write_cannot_bypass_analysis_gate(self):
        """无来源的有效分析在编号维护入口也拒写，不只依赖Skill先运行门禁。"""
        target = self.root / 'prd/prd-trace.json'
        before = target.read_bytes()
        self.analysis['requirements']['functional_requirements'][0]['sources'] = []
        support.write_json(self.root / 'analysis/analysis-result.json', self.analysis)
        with self.assertRaisesRegex(ValueError, '门禁'):
            numbering.assign_ids(self.root, self.patch, write=True)
        self.assertEqual(target.read_bytes(), before)

    def test_independent_write_keeps_manual_edit_evidence(self):
        """未判定含义的手工改动不能通过编号维护重置摘要而被静默认可。"""
        target = self.root / 'prd/prd-trace.json'
        before = target.read_bytes()
        body = self.root / 'prd/prd.md'
        body.write_text(body.read_text().replace('合成查询', '彻底删除'))
        with self.assertRaisesRegex(ValueError, '手工修改'):
            numbering.assign_ids(self.root, self.patch, write=True)
        self.assertEqual(target.read_bytes(), before)

    def test_independent_write_does_not_modify_review_or_release(self):
        """首稿编号工具不能绕过当前阶段边界修改评审或已发布版本。"""
        for state in ('in_review', 'released', 'deprecated'):
            with self.subTest(state=state):
                self.requirement['prd']['status'] = state
                support.write_json(self.root / 'requirement.json', self.requirement)
                with self.assertRaisesRegex(ValueError, '未发布首稿'):
                    numbering.assign_ids(self.root, self.patch, write=True)

    def test_independent_write_preserves_pending_source_digests(self):
        """分析修订变化后独立编号维护不得提前刷新摘要并掩盖条目级同步差异。"""
        target = self.root / 'prd/prd-trace.json'
        before = target.read_bytes()
        self.analysis['meta']['analysis_revision'] = 2
        self.analysis['requirements']['functional_requirements'][0]['content'] = '变更后的合成功能'
        support.write_json(self.root / 'analysis/analysis-result.json', self.analysis)
        self.patch['base_analysis_revision'] = 2
        with self.assertRaisesRegex(ValueError, '待同步'):
            numbering.assign_ids(self.root, self.patch, write=True)
        self.assertEqual(target.read_bytes(), before)

    def test_independent_write_cannot_add_ids_without_body(self):
        """既有正文时新增拆分编号必须走统一写入，不能把合法草稿改成缺正文的追溯。"""
        target = self.root / 'prd/prd-trace.json'
        before = target.read_bytes()
        self.patch['items'].append({**self.patch['items'][0], 'mapping_key': 'split'})
        with self.assertRaisesRegex(ValueError, '统一保存'):
            numbering.assign_ids(self.root, self.patch, write=True)
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(numbering._validator.validate_prd(self.root)['status'], 'pass')

    def test_concurrent_original_bytes_guard(self):
        """写入前源文件原字节变化时拒绝覆盖已有追溯。"""
        target = self.root / "prd/prd-trace.json"
        before = target.read_bytes()
        original = numbering._snapshot
        calls = 0

        def mutate(path, optional=False):
            """在第二轮读取时修改需求文件，模拟非协作写入；返回文件快照。"""
            nonlocal calls
            calls += 1
            if calls == 4:
                (self.root / "requirement.json").write_text(json.dumps(self.requirement) + " ")
            return original(path, optional)

        with mock_patch.object(numbering, "_snapshot", side_effect=mutate), self.assertRaisesRegex(ValueError, "并发"):
            numbering.assign_ids(self.root, self.patch, write=True)
        self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

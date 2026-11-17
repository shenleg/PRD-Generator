"""验证阶段四只读来源比较、稳定摘要与同步门禁；合成夹具不代表真实需求评审。"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill/prd-generator/scripts/check_sync.py"


def load(name, path):
    """从 path 加载名为 name 的测试依赖并返回模块；安装及加载异常原样抛出。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = load("sync_fixture_support", Path(__file__).with_name("prd_fixture_support.py"))
sync = load("prd_sync_check_test", SCRIPT)


def fingerprint(root):
    """返回 root 内目录、链接和文件原字节及修改时间的指纹；文件系统异常原样抛出。"""
    result = {}
    for path in (root, *sorted(root.rglob("*"))):
        kind = "link" if path.is_symlink() else "file" if path.is_file() else "directory"
        value = str(path.readlink()) if kind == "link" else path.read_bytes() if kind == "file" else None
        stat = path.lstat()
        result[str(path.relative_to(root))] = (kind, value, stat.st_mode, stat.st_mtime_ns)
    return result


class SyncCheckTests(unittest.TestCase):
    """在隔离需求目录中覆盖 PG-13、PG-32、PG-34 及失败边界。"""

    def setUp(self):
        """创建合成目录和只读输入快照；返回值为空，文件异常原样抛出。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = support.make_workspace(Path(self.temp.name) / "requirement")
        self.analysis_path = self.root / "analysis/analysis-result.json"
        self.analysis = support.read_json(self.analysis_path)
        self.requirement = support.read_json(self.root / "requirement.json")
        self.trace = support.read_json(self.root / "prd/prd-trace.json")
        self.events = self.root / "analysis/analysis-events.jsonl"
        self.events.write_text("", encoding="utf-8")

    def compare(self, *, related=()):
        """比较当前输入及 related 关联文档并返回结果；非法输入抛出 ValueError。"""
        return sync.compare_sources(self.analysis, self.requirement, self.trace, related_analyses=related)

    def add_source(self, item_id="FR-2", *, status="active"):
        """复制功能来源并按 item_id/status 加入当前分析，返回新条目；键错误原样抛出。"""
        item = deepcopy(self.analysis["requirements"]["functional_requirements"][0])
        item.update(id=item_id, status=status)
        self.analysis["requirements"]["functional_requirements"].append(item)
        return item

    def save(self):
        """保存测试主动修改的三份输入；返回值为空，文件异常原样抛出。"""
        support.write_json(self.analysis_path, self.analysis)
        support.write_json(self.root / "requirement.json", self.requirement)
        support.write_json(self.root / "prd/prd-trace.json", self.trace)

    def rebase_digest(self, *, related=()):
        """按当前分析和 related 更新测试旧追溯摘要；返回值为空，摘要异常原样抛出。"""
        registry = sync._numbering._registry((self.analysis, *related))
        for item in self.trace["items"]:
            item["source_digest"] = sync._validator.source_digest(item["analysis_refs"], registry)

    def cli(self, *args):
        """在需求目录之外运行带 args 的公开 CLI 并返回进程结果；启动异常原样抛出。"""
        return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), str(self.root), *args],
                              cwd=self.temp.name, capture_output=True, text=True)

    def test_unchanged_baseline_and_pure_inputs(self):
        """PG-13 同修订和相同摘要为未变，比较结果也不与输入共享可变引用列表。"""
        before = deepcopy((self.analysis, self.requirement, self.trace))
        result = self.compare()
        self.assertEqual((result["pending"], result["based_on_analysis_revision"], result["analysis_revision"]), (False, 1, 1))
        self.assertEqual(result["items"], [{"prd_id": "PRD-FR-001", "analysis_refs": ["SYNTHETIC-PRD/FR-1"],
                                          "category": "unchanged", "source_digest": self.trace["items"][0]["source_digest"]}])
        self.assertEqual(result["added"], [])
        result["items"][0]["analysis_refs"].append("UNUSED/FR-1")
        self.assertEqual(before, (self.analysis, self.requirement, self.trace))

    def test_revision_only_is_pending_without_item_change(self):
        """PG-13 只增加分析修订会待同步，不把正式条目误判成修改。"""
        self.analysis["meta"]["analysis_revision"] = 2
        result = self.compare()
        self.assertEqual((result["pending"], result["based_on_analysis_revision"], result["analysis_revision"]), (True, 1, 2))
        self.assertEqual([item["category"] for item in result["items"]], ["unchanged"])

    def test_changed_content_is_reported_even_at_same_revision(self):
        """实际差异独立于修订门禁，同修订来源被改动仍报告 modified。"""
        self.analysis["requirements"]["functional_requirements"][0]["content"] = "修改后的合成查询"
        result = self.compare()
        self.assertFalse(result["pending"])
        self.assertEqual(result["items"][0]["category"], "modified")

    def test_label_source_and_relationship_changes(self):
        """PG-32 单独修改标签、来源或关联均改变摘要而保留旧编号。"""
        self.add_source()
        original = deepcopy(self.analysis)
        changes = ({"tag": "inferred"}, {"sources": [{"type": "input_document", "source_id": "SRC-1", "location": "新增合成来源"}]},
                   {"related_ids": ["FR-2"]})
        for change in changes:
            with self.subTest(change=change):
                self.analysis = deepcopy(original)
                self.analysis["requirements"]["functional_requirements"][0].update(change)
                item = self.compare()["items"][0]
                self.assertEqual((item["prd_id"], item["category"]), ("PRD-FR-001", "modified"))
                self.assertNotEqual(item["source_digest"], self.trace["items"][0]["source_digest"])

    def test_complete_extension_fields_change_digest(self):
        """PG-32 只改实际生成的完整扩展字段也必须判定为修改。"""
        item = self.analysis["requirements"]["functional_requirements"][0]
        item["render_context"] = {"priority": "normal", "details": {"中文说明": ["甲", "乙"]}}
        self.rebase_digest()
        item["render_context"]["details"]["中文说明"][1] = "丙"
        self.assertEqual(self.compare()["items"][0]["category"], "modified")

    def test_object_keys_and_json_whitespace_do_not_change_digest(self):
        """PG-34 递归键顺序及外部 JSON 排版不同不产生正式条目差异。"""
        compact = json.dumps(self.analysis, ensure_ascii=False, separators=(",", ":"))
        reordered = json.loads(json.dumps(self.analysis, ensure_ascii=False, sort_keys=True, indent=7),
                               object_pairs_hook=lambda pairs: dict(reversed(pairs)))
        self.assertNotEqual(compact, json.dumps(reordered, ensure_ascii=False, indent=7))
        self.analysis = reordered
        self.assertEqual(self.compare()["items"][0]["category"], "unchanged")
        self.analysis_path.write_text(" \n" + json.dumps(reordered, ensure_ascii=False, indent=7) + "\n", encoding="utf-8")
        self.assertEqual(sync.check_sync(self.root)["items"][0]["category"], "unchanged")

    def test_array_order_is_preserved(self):
        """PG-34 条目内来源、关联和扩展数组顺序改变均不能被稳定摘要排序掉。"""
        self.add_source("FR-2")
        self.add_source("FR-3")
        item = self.analysis["requirements"]["functional_requirements"][0]
        item["sources"].append({**item["sources"][0], "location": "合成资料第2条"})
        item["related_ids"] = ["FR-2", "FR-3"]
        item["extension"] = ["甲", "乙"]
        self.rebase_digest()
        for field in ("sources", "related_ids", "extension"):
            with self.subTest(field=field):
                item[field].reverse()
                self.assertEqual(self.compare()["items"][0]["category"], "modified")
                item[field].reverse()
                self.assertEqual(self.compare()["items"][0]["category"], "unchanged")

    def test_withdrawn_and_to_reassess_classification(self):
        """撤销和待重评来源变化输出专门分类，不要求旧追溯预先采用新状态。"""
        item = self.analysis["requirements"]["functional_requirements"][0]
        for status in ("withdrawn", "to_reassess"):
            with self.subTest(status=status):
                item["status"] = status
                self.assertEqual(self.compare()["items"][0]["category"], status)
                self.assertEqual(self.trace["items"][0]["status"], "active")

    def test_digest_unchanged_takes_priority_over_source_status(self):
        """已同步的撤销和待重评来源不应每次被重复报告为变化。"""
        for status in ("withdrawn", "to_reassess"):
            with self.subTest(status=status):
                self.analysis["requirements"]["functional_requirements"][0]["status"] = status
                self.rebase_digest()
                self.assertEqual(self.compare()["items"][0]["category"], "unchanged")

    def test_multiple_sources_order_and_status_priority(self):
        """多来源完整覆盖依据，外层引用排序稳定，撤销优先于待重评。"""
        second = self.add_source()
        self.trace["items"][0]["analysis_refs"].append("SYNTHETIC-PRD/FR-2")
        self.rebase_digest()
        self.trace["items"][0]["analysis_refs"].reverse()
        self.assertEqual(self.compare()["items"][0]["category"], "unchanged")
        second["status"] = "to_reassess"
        self.assertEqual(self.compare()["items"][0]["category"], "to_reassess")
        self.analysis["requirements"]["functional_requirements"][0]["status"] = "withdrawn"
        self.assertEqual(self.compare()["items"][0]["category"], "withdrawn")
        self.assertEqual(self.compare()["added"], [])

    def test_split_mapping_is_not_reported_as_new_source(self):
        """旧来源一对多时所有映射均受影响，且不误报来源为新增。"""
        second = deepcopy(self.trace["items"][0])
        second.update(prd_id="PRD-FR-002", mapping_key="synthetic-split")
        self.trace["items"].append(second)
        self.trace["meta"]["counters"]["FR"] = 2
        self.analysis["requirements"]["functional_requirements"][0]["content"] = "拆分来源被修改"
        result = self.compare()
        self.assertEqual([item["category"] for item in result["items"]], ["modified", "modified"])
        self.assertEqual(result["added"], [])

    def test_new_active_and_reassessment_but_not_withdrawn_sources(self):
        """新增可分配的有效与待重评条目被发现，撤销新条目不进入 added。"""
        self.add_source("FR-2")
        self.add_source("FR-3", status="to_reassess")
        self.add_source("FR-4", status="withdrawn")
        self.assertEqual(self.compare()["added"], [
            {"analysis_ref": "SYNTHETIC-PRD/FR-2", "kind": "functional_requirement"},
            {"analysis_ref": "SYNTHETIC-PRD/FR-3", "kind": "functional_requirement"}])

    def test_all_allocatable_prefixes_use_canonical_kinds(self):
        """新增类别统一复用 KINDS，不遗漏业务流程、状态及边界等可分配条目。"""
        paths = {"GOAL": ("requirements", "goals"), "SCN": ("requirements", "scenarios"),
                 "FR": ("requirements", "functional_requirements"), "BR": ("requirements", "business_rules"),
                 "CON": ("requirements", "constraints"), "NFR": ("requirements", "non_functional_requirements"),
                 "AC": ("requirements", "acceptance_criteria"), "FLOW": ("business_assessment", "flows"),
                 "STATE": ("business_assessment", "states"), "BND": ("business_assessment", "boundaries"),
                 "EXC": ("business_assessment", "exceptions")}
        for prefix, (section, field) in paths.items():
            item = deepcopy(self.analysis["requirements"]["functional_requirements"][0])
            item["id"] = prefix + "-2"
            self.analysis[section][field].append(item)
        actual = {item["analysis_ref"].split("/")[1].split("-")[0]: item["kind"] for item in self.compare()["added"]}
        self.assertEqual(actual, {prefix: kind for kind, prefix in sync._validator.KINDS.items()})

    def test_meta_and_non_numbered_changes_do_not_rewrite_items(self):
        """meta 和未编号遗留项更新只留给 writer 重汇总，不制造正式条目差异。"""
        self.analysis["meta"].update(analysis_revision=2, readiness="conditionally_ready")
        self.analysis["business_assessment"]["gaps"].append({
            **deepcopy(self.analysis["requirements"]["functional_requirements"][0]), "id": "GAP-1", "content": "新增分析遗留项"})
        self.analysis["ux_assessment"]["design_pending_items"].append("待补视觉资料")
        result = self.compare()
        self.assertTrue(result["pending"])
        self.assertEqual([item["category"] for item in result["items"]], ["unchanged"])
        self.assertEqual(result["added"], [])

    def test_explicit_related_analysis_is_compared_without_mutation(self):
        """跨需求引用参与摘要，但不把关联资料的未引用功能当成本需求新增条目。"""
        related = deepcopy(self.analysis)
        related["requirement_id"] = "RELATED"
        self.trace["items"][0]["analysis_refs"].append("RELATED/FR-1")
        self.rebase_digest(related=(related,))
        related["requirements"]["functional_requirements"][0]["content"] = "关联来源已更正"
        before = deepcopy(related)
        self.assertEqual(self.compare(related=(related,))["items"][0]["category"], "modified")
        self.assertEqual(related, before)
        related["requirements"]["functional_requirements"].append({**deepcopy(related["requirements"]["functional_requirements"][0]), "id": "FR-2"})
        self.assertEqual(self.compare(related=(related,))["added"], [])

    def test_future_baseline_and_invalid_revision_rejected(self):
        """分析基准来自未来或修订不是正整数时拒绝，不静默当作无需同步。"""
        for revision in (2, 0, -1, True, "1", None):
            with self.subTest(baseline=revision):
                self.requirement["prd"]["based_on_analysis_revision"] = revision
                with self.assertRaises(ValueError):
                    self.compare()
        self.requirement["prd"]["based_on_analysis_revision"] = 1
        for revision in (0, True, "1"):
            with self.subTest(analysis_revision=revision):
                self.analysis["meta"]["analysis_revision"] = revision
                with self.assertRaises(ValueError):
                    self.compare()

    def test_missing_references_are_not_treated_as_withdrawn(self):
        """缺失条目或未显式提供的跨需求引用必须报错，不能猜测为撤销。"""
        for ref in ("SYNTHETIC-PRD/FR-99", "RELATED/FR-1"):
            with self.subTest(ref=ref):
                self.trace["items"][0]["analysis_refs"] = [ref]
                with self.assertRaisesRegex(ValueError, "引用不存在"):
                    self.compare()

    def test_identity_conflicts_rejected(self):
        """主分析、需求、追溯身份及显式关联分析的重复身份均不能混用。"""
        self.requirement["common"]["requirement_id"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "身份"):
            self.compare()
        self.requirement["common"]["requirement_id"] = "SYNTHETIC-PRD"
        self.trace["requirement_id"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "身份"):
            self.compare()
        self.trace["requirement_id"] = "SYNTHETIC-PRD"
        with self.assertRaisesRegex(ValueError, "重复"):
            self.compare(related=(deepcopy(self.analysis),))
        self.add_source("FR-1")
        with self.assertRaisesRegex(ValueError, "重复"):
            self.compare()

    def test_invalid_structure_number_and_nonfinite_digest_rejected(self):
        """无效结构、编号类别、高水位、映射键重复和非有限摘要输入均拒绝。"""
        before = deepcopy(self.trace)
        changes = (lambda: self.trace["meta"]["counters"].update(FR=0),
                   lambda: self.trace["items"][0].update(kind="business_rule"),
                   lambda: self.trace["items"][0].update(prd_id="PRD-FR-000"),
                   lambda: self.trace["items"].append(deepcopy(self.trace["items"][0])))
        for change in changes:
            with self.subTest(change=change):
                self.trace = deepcopy(before)
                change()
                with self.assertRaises(ValueError):
                    self.compare()
        self.trace = before
        self.analysis["requirements"]["functional_requirements"][0]["extension"] = float("nan")
        with self.assertRaises(ValueError):
            self.compare()
        for analysis in (None, [], {}, {"meta": {}}):
            with self.subTest(analysis=analysis), self.assertRaises(ValueError):
                sync.compare_sources(analysis, self.requirement, self.trace)

    def test_directory_and_cli_are_readonly_with_real_differences(self):
        """PG-13 API 和任意 cwd 的公开 CLI 报告差异，目录指纹前后完全不变。"""
        self.analysis["meta"]["analysis_revision"] = 2
        self.analysis["requirements"]["functional_requirements"][0]["content"] = "本次更新的查询功能"
        self.save()
        before = fingerprint(self.root)
        result = sync.check_sync(self.root)
        process = self.cli()
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        self.assertEqual(json.loads(process.stdout), result)
        self.assertEqual((result["status"], result["allowed"], result["pending"]), ("pass", True, True))
        self.assertEqual(result["items"][0]["category"], "modified")
        self.assertEqual(before, fingerprint(self.root))

    def test_directory_does_not_validate_old_status_against_new_withdrawal(self):
        """新分析撤销或待重评不应因旧稿仍有效而被完整 PRD 校验错误拦截。"""
        for status in ("withdrawn", "to_reassess"):
            with self.subTest(status=status):
                self.analysis["meta"]["analysis_revision"] = 2
                self.analysis["requirements"]["functional_requirements"][0]["status"] = status
                self.save()
                before = fingerprint(self.root)
                result = sync.check_sync(self.root)
                self.assertTrue(result["allowed"], result)
                self.assertEqual(result["items"][0]["category"], status)
                self.assertEqual(before, fingerprint(self.root))

    def test_stale_without_insistence_is_denied_but_still_compared(self):
        """过期未坚持时 allowed 为假，仍报告 pending/差异，明确允许后仅为过期草稿。"""
        self.analysis["meta"].update(analysis_status="stale", analysis_revision=2)
        self.analysis["requirements"]["functional_requirements"][0]["content"] = "过期来源的差异"
        self.save()
        before = fingerprint(self.root)
        denied = sync.check_sync(self.root)
        self.assertEqual((denied["status"], denied["allowed"], denied["pending"]), ("warning", False, True))
        self.assertEqual(denied["items"][0]["category"], "modified")
        allowed = sync.check_sync(self.root, allow_stale=True)
        self.assertEqual((allowed["status"], allowed["allowed"], allowed["draft_kind"]), ("warning", True, "stale_draft"))
        process = self.cli("--allow-stale")
        self.assertEqual(process.returncode, 1, process.stderr + process.stdout)
        self.assertTrue(json.loads(process.stdout)["allowed"])
        self.assertEqual(before, fingerprint(self.root))

    def test_missing_auxiliary_events_and_manifest_degrade(self):
        """辅助事件与清单缺失仅降级，按实际来源比较且诊断不臆造变更原因。"""
        self.events.rename(self.events.with_suffix(".backup"))
        manifest = self.root / "analysis/source-manifest.json"
        manifest.rename(manifest.with_suffix(".backup"))
        before = fingerprint(self.root)
        result = sync.check_sync(self.root)
        self.assertEqual((result["status"], result["allowed"]), ("warning", True))
        self.assertEqual(result["items"][0]["category"], "unchanged")
        self.assertTrue(any("source_id" in issue["message"] for issue in result["diagnostics"]))
        self.assertTrue(any("不推断变更原因" in issue["message"] for issue in result["diagnostics"]))
        self.assertEqual(self.cli().returncode, 1)
        self.assertEqual(before, fingerprint(self.root))

    def test_authoritative_gate_cannot_be_bypassed_by_missing_auxiliary(self):
        """缺辅助文件也不能跳过有效分析的来源检查，拒绝结果保持只读。"""
        self.analysis["requirements"]["functional_requirements"][0]["sources"] = []
        self.save()
        manifest = self.root / "analysis/source-manifest.json"
        manifest.rename(manifest.with_suffix(".backup"))
        before = fingerprint(self.root)
        result = sync.check_sync(self.root)
        self.assertEqual((result["status"], result["allowed"]), ("fail", False))
        self.assertTrue(any("至少需要一个来源" in issue["message"] for issue in result["diagnostics"]))
        self.assertEqual(before, fingerprint(self.root))

    def test_directory_failure_and_cli_fail_exit(self):
        """未来基准、无效 JSON 和追溯不存在时输出 JSON fail，拒绝但不保存。"""
        self.requirement["prd"]["based_on_analysis_revision"] = 2
        self.save()
        before = fingerprint(self.root)
        process = self.cli()
        self.assertEqual(process.returncode, 2, process.stderr + process.stdout)
        result = json.loads(process.stdout)
        self.assertEqual((result["status"], result["allowed"]), ("fail", False))
        self.assertTrue(any("未来" in issue["message"] for issue in result["diagnostics"]))
        self.assertEqual(before, fingerprint(self.root))
        self.analysis_path.write_text("{", encoding="utf-8")
        self.assertEqual(sync.check_sync(self.root)["status"], "fail")
        target = self.root / "prd/prd-trace.json"
        target.rename(target.with_suffix(".backup"))
        self.assertFalse(sync.check_sync(self.root)["allowed"])

    def test_related_analysis_cli_and_missing_related_reference(self):
        """公开 CLI 只接收显式关联路径，跨需求引用缺失不能隐式扫描工作区。"""
        related = deepcopy(self.analysis)
        related["requirement_id"] = "RELATED"
        related_path = Path(self.temp.name) / "related/analysis-result.json"
        support.write_json(related_path, related)
        support.write_json(related_path.with_name("source-manifest.json"), support.read_json(self.root / "analysis/source-manifest.json"))
        self.trace["items"][0]["analysis_refs"].append("RELATED/FR-1")
        self.rebase_digest(related=(related,))
        self.save()
        self.assertFalse(sync.check_sync(self.root)["allowed"])
        before = fingerprint(Path(self.temp.name))
        process = self.cli("--related-analysis", str(related_path))
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        self.assertTrue(json.loads(process.stdout)["allowed"])
        self.assertEqual(before, fingerprint(Path(self.temp.name)))

    def test_symlink_and_installation_failure_are_failures(self):
        """拒绝跟随用户追溯链接，依赖安装故障也必须明确报告 fail。"""
        target = self.root / "prd/prd-trace.json"
        backup = target.with_suffix(".backup")
        target.rename(backup)
        target.symlink_to(backup)
        before = fingerprint(self.root)
        result = sync.check_sync(self.root)
        self.assertEqual((result["status"], result["allowed"]), ("fail", False))
        self.assertEqual(before, fingerprint(self.root))
        with patch.object(sync._gate, "check_gate", side_effect=RuntimeError("损坏安装")):
            result = sync.check_sync(self.root)
        self.assertEqual((result["status"], result["allowed"]), ("fail", False))


if __name__ == "__main__":
    unittest.main()

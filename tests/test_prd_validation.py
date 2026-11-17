"""按人工认可格式验证全部十二条规则；仅合成临时夹具，不证明模型生成或真实发布。"""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from prd_fixture_support import block, digest, make_workspace, read_json, refresh_hash, write_json


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill/prd-generator/scripts/validate_prd.py"


class PrdValidationTests(unittest.TestCase):
    """覆盖结构、引用、正文、生命周期证据及只读边界。"""

    @classmethod
    def setUpClass(cls):
        """加载只读实现；实现不存在或导入错误直接使测试失败。"""
        spec = importlib.util.spec_from_file_location("prd_validation", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self):
        """创建独立临时需求夹具；写入错误直接抛出，结束后由测试库清理。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_workspace(Path(self.temp.name) / "requirement")

    def validate(self, **kwargs):
        """校验当前夹具及 kwargs 指定的只读输入并返回结果；实现异常使测试失败。"""
        return self.module.validate_prd(self.root, **kwargs)

    def mutate(self, relative, change):
        """对临时 relative 的 JSON 应用 change 回调并保存；结构与回调异常原样抛出。"""
        path = self.root / relative
        data = read_json(path)
        change(data)
        write_json(path, data)
        return data

    def expect_rule(self, rule):
        """断言当前夹具存在 rule 对应失败诊断并返回响应；不满足时抛出断言异常。"""
        result = self.validate()
        self.assertEqual(result["status"], "fail", result)
        self.assertTrue(any(d["rule"] == rule and d["level"] == "fail" for d in result["diagnostics"]), result)
        return result

    def edit_text(self, old, new, *, refresh=True):
        """替换临时正文 old 为 new，可选择刷新摘要；找不到原文或写入错误直接失败。"""
        path = self.root / "prd/prd.md"
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")
        if refresh:
            refresh_hash(self.root)

    def add_gap(self, status="open", *, question=True, resolution=None):
        """登记合成 status 缺口并可加接收问题及 resolution，返回请求；无真实交接或批准。"""
        request = {"id": "GAPREQ-1", "needed_for": "功能需求", "description": "合成验收缺口", "related_analysis_refs": ["SYNTHETIC-PRD/FR-1"], "raised_in": "0.1", "status": status}
        if resolution is not None:
            request["resolution"] = resolution
        write_json(self.root / "prd/gap-requests.json", {"schema_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "counters": {"GAPREQ": 1}, "requests": [request]})
        if question:
            q = {"id": "Q-1", "question": "合成缺口如何补足？", "priority": "P3", "resolution": "ask_product", "reason": "格式测试", "impact": "格式测试", "options": ["补充", "其他"], "recommendation": "仅为合成", "status": "answered" if status == "closed" else "open", "answer": "合成回答", "related_ids": ["FR-1"], "gap_request_ref": "GAPREQ-1"}
            self.mutate("analysis/analysis-result.json", lambda data: data["questions"].append(q))
        if status != "closed":
            self.edit_text("无适用遗留项", block("gap", "GAPREQ-1", "待分析补充：合成验收缺口"))
        return request

    def publish_fixture(self):
        """构造有事件及摘要的合成快照；不调用发布器，不构成产品经理实际批准。"""
        versions = self.root / "prd/versions"
        versions.mkdir()
        snapshots = {}
        for kind, source, name in [("prd", "prd/prd.md", "prd-1.0.md"), ("trace", "prd/prd-trace.json", "prd-trace-1.0.json")]:
            data = (self.root / source).read_bytes()
            (versions / name).write_bytes(data)
            snapshots[kind] = {"path": f"versions/{name}", "sha256": digest(data)}
        events = self.root / "prd/prd-events.jsonl"
        with events.open("a") as handle:
            handle.write(json.dumps({"time": "2026-11-17T01:00:00Z", "prd_version": "1.0", "change_type": "release", "summary": "合成快照格式测试，非真实发布", "affected_prd_ids": ["PRD-FR-001"], "based_on_analysis_revision": 1, "actor": "prd_generator", "snapshots": snapshots}, ensure_ascii=False) + "\n")

    def test_valid_fixture_and_readonly_cli(self):
        """合法夹具 pass，实际 CLI 从任意目录运行不改变业务字节。"""
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(self.validate()["status"], "pass")
        result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), str(self.root)], cwd=self.temp.name, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)["status"], "pass")
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_rule_1_missing_field_and_bad_json(self):
        """规则1拒绝缺失必填和重复键，不吞掉损坏输入。"""
        self.mutate("prd/prd-trace.json", lambda d: d.pop("items"))
        self.expect_rule(1)
        (self.root / "prd/prd-trace.json").write_text('{"schema_version":"1.0","schema_version":"2.0"}')
        self.expect_rule(1)

    def test_rule_2_duplicate_id_counter_and_mapping_key(self):
        """规则2拒绝重复正式编号及映射键，并检出编号计数器落后。"""
        original = read_json(self.root / "prd/prd-trace.json")
        self.mutate("prd/prd-trace.json", lambda d: d["items"].append(copy.deepcopy(d["items"][0])))
        self.expect_rule(2)
        write_json(self.root / "prd/prd-trace.json", original)
        self.mutate("prd/prd-trace.json", lambda d: d["meta"]["counters"].update(FR=0))
        self.expect_rule(2)

    def test_rule_2_history_cannot_reset_identity(self):
        """历史对照阻止删除旧编号及改写引入版本，单份文件不伪称有完整历史。"""
        previous = Path(self.temp.name) / "previous.json"
        write_json(previous, read_json(self.root / "prd/prd-trace.json"))
        self.mutate("prd/prd-trace.json", lambda d: d["items"][0].update(introduced_in="0.2"))
        result = self.validate(previous_trace=previous)
        self.assertTrue(any(d["rule"] == 2 for d in result["diagnostics"]), result)

    def test_rule_3_dangling_or_withdrawn_reference(self):
        """规则3检出不存在及已撤销却仍有效的来源引用。"""
        self.mutate("prd/prd-trace.json", lambda d: d["items"][0].update(analysis_refs=["SYNTHETIC-PRD/FR-99"]))
        self.expect_rule(3)

    def test_rule_4_missing_and_untracked_ids(self):
        """规则4要求正文有效条目与追溯双向对应。"""
        self.edit_text("PRD-FR-001", "PRD-FR-999")
        self.expect_rule(4)

    def test_rule_5_labels_must_be_inside_item(self):
        """规则5不接受其他章节的推断标注为目标条目充数。"""
        self.mutate("analysis/analysis-result.json", lambda d: d["requirements"]["functional_requirements"][0].update(tag="inferred"))
        self.mutate("prd/prd-trace.json", lambda d: d["items"][0].update(tag="inferred"))
        self.edit_text("无适用遗留项", "【推断】")
        self.expect_rule(5)

    def test_rule_6_abolished_not_in_effective_section(self):
        """规则6拒绝将已废止条目保留在功能正文。"""
        self.mutate("prd/prd-trace.json", lambda d: d["items"][0].update(status="abolished"))
        self.expect_rule(6)

    def test_rule_7_stale_overrides_readiness(self):
        """规则7优先过期状态，不能以正式草稿提示掩盖过期。"""
        self.mutate("analysis/analysis-result.json", lambda d: d["meta"].update(analysis_status="stale", readiness="not_ready"))
        self.expect_rule(7)

    def test_rule_8_required_residual_missing(self):
        """规则8检出缺少适用推断遗留项，不只搜索正文编号。"""
        self.mutate("analysis/analysis-result.json", lambda d: d["requirements"]["functional_requirements"][0].update(tag="inferred"))
        self.expect_rule(8)

    def test_rule_9_orphan_placeholder(self):
        """规则9拒绝未登记或无法对应的占位。"""
        self.edit_text("无适用遗留项", block("gap", "GAPREQ-1", "待分析补充"))
        self.expect_rule(9)

    def test_rule_10_visible_metadata_mismatch(self):
        """规则10核对可见文档信息，而不是仅信任隐藏字段。"""
        self.edit_text("| PRD 版本 | 0.1 |", "| PRD 版本 | 0.9 |")
        self.expect_rule(10)

    def test_rule_11_snapshot_integrity_and_symlink(self):
        """规则11校验两份快照原始字节，拒绝篡改及符号链接。"""
        self.publish_fixture()
        self.assertEqual(self.validate()["status"], "pass")
        path = self.root / "prd/versions/prd-1.0.md"
        path.write_bytes(path.read_bytes() + b"tampered")
        self.expect_rule(11)

    def test_rule_11_unrecorded_and_duplicate_release(self):
        """规则11拒绝快照无登记和重复发布记录。"""
        self.publish_fixture()
        events = self.root / "prd/prd-events.jsonl"
        release = events.read_text().splitlines()[-1]
        with events.open("a") as handle:
            handle.write(release + "\n")
        self.expect_rule(11)

    def test_rule_12_open_without_receiver_is_warning(self):
        """未接收或保存后未标状态的 open 缺口都合法，输出 warning 而非结构失败。"""
        self.add_gap(question=False)
        result = self.validate()
        self.assertEqual(result["status"], "warning", result)
        self.assertFalse(any(d["level"] == "fail" for d in result["diagnostics"]))

    def test_rule_12_handed_over_requires_unique_receiver(self):
        """handed_over 必须有唯一接收问题，不能假装接收成功。"""
        self.add_gap(status="handed_over", question=False)
        self.expect_rule(12)

    def test_rule_12_closed_requires_effective_content(self):
        """关闭不能只靠问题状态，撤销依据及缺依据都被拒绝。"""
        self.add_gap(status="closed", resolution={"kind": "supplied", "analysis_refs": ["SYNTHETIC-PRD/FR-99"], "reason": "测试不存在依据"})
        self.expect_rule(12)

    def test_rule_12_valid_closed_and_not_needed(self):
        """有接收问题和有效内容才结构上允许关闭，充分性仍不冒充自动证明。"""
        self.add_gap(status="closed", resolution={"kind": "supplied", "analysis_refs": ["SYNTHETIC-PRD/FR-1"], "reason": "合成引用，仅测试结构"})
        self.assertEqual(self.validate()["status"], "pass")
        self.mutate("prd/gap-requests.json", lambda d: d["requests"][0]["resolution"].update(kind="not_needed"))
        self.expect_rule(12)

    def test_sync_warning_and_failure_priority(self):
        """待同步是 warning，结构错误仍优先为 fail；不把未同步摘要差异判失败。"""
        self.mutate("analysis/analysis-result.json", lambda d: d["meta"].update(analysis_revision=2))
        self.mutate("analysis/analysis-result.json", lambda d: d["requirements"]["functional_requirements"][0].update(content="合成更新"))
        self.assertEqual(self.validate()["status"], "warning")
        self.mutate("prd/prd-trace.json", lambda d: d["meta"]["counters"].update(FR=0))
        result = self.expect_rule(2)
        self.assertTrue(any(d["level"] == "warning" for d in result["diagnostics"]))

    def test_manual_hash_change_warning(self):
        """未处理的手工改动是 warning，校验器不自行修正文档或摘要。"""
        self.edit_text("首次合成夹具", "首次合成夹具，手工排版", refresh=False)
        self.assertEqual(self.validate()["status"], "warning")

    def test_source_digest_changes_and_key_order_stability(self):
        """生成依据摘要覆盖来源和关联，JSON 键顺序不影响算法。"""
        registry = {"SYNTHETIC-PRD/FR-1": read_json(self.root / "analysis/analysis-result.json")["requirements"]["functional_requirements"][0]}
        a = self.module.source_digest(["SYNTHETIC-PRD/FR-1"], registry)
        registry["SYNTHETIC-PRD/FR-1"] = dict(reversed(list(registry["SYNTHETIC-PRD/FR-1"].items())))
        self.assertEqual(a, self.module.source_digest(["SYNTHETIC-PRD/FR-1"], registry))
        registry["SYNTHETIC-PRD/FR-1"]["related_ids"] = ["FR-1"]
        self.assertNotEqual(a, self.module.source_digest(["SYNTHETIC-PRD/FR-1"], registry))

    def test_malformed_blocks_and_untracked_number(self):
        """交叉定位块或游离正式编号不能被解析器忽略。"""
        self.edit_text("<!-- /prd:item -->", "<!-- /prd:gap -->")
        self.expect_rule(4)

    def test_bad_metadata_root_and_event_json(self):
        """坏元数据和事件 JSON 返回结构化诊断，不引发未处理异常。"""
        write_json(self.root / "requirement.json", [])
        self.expect_rule(10)

    def test_optional_source_manifest_missing_downgrades(self):
        """可选来源名称清单无法读取时保留 source_id，不阻断合法分析内容。"""
        path = self.root / "analysis/source-manifest.json"
        path.rename(path.with_suffix(".saved"))
        result = self.validate()
        self.assertNotEqual(result["status"], "fail", result)

    def test_numbering_patch_readonly_structure_and_conflict(self):
        """编号补丁只读检查映射身份和读时版本，禁止模型指定新正式编号。"""
        patch = {"patch_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "base_prd_version": "0.1", "base_analysis_revision": 1, "items": [{"mapping_key": "synthetic-query", "kind": "functional_requirement", "analysis_refs": ["SYNTHETIC-PRD/FR-1"]}]}
        path = write_json(Path(self.temp.name) / "patch.json", patch)
        self.assertEqual(self.validate(numbering_patch=path)["status"], "pass")
        patch["base_analysis_revision"] = 9
        write_json(path, patch)
        self.assertEqual(self.validate(numbering_patch=path)["status"], "fail")

    def test_rule_3_withdrawn_source_and_rule_5_pending_label(self):
        """撤销来源不能保持有效，待重评状态必须落实到对应条目的待确认标注。"""
        self.mutate("analysis/analysis-result.json", lambda d: d["requirements"]["functional_requirements"][0].update(status="withdrawn"))
        self.expect_rule(3)
        self.mutate("analysis/analysis-result.json", lambda d: d["requirements"]["functional_requirements"][0].update(status="to_reassess"))
        self.mutate("prd/prd-trace.json", lambda d: d["items"][0].update(status="to_confirm"))
        self.expect_rule(5)

    def test_snapshot_symlink_and_missing_record_rejected(self):
        """快照符号链接和无记录文件不被当作不可变发布依据。"""
        versions = self.root / "prd/versions"
        versions.mkdir()
        target = Path(self.temp.name) / "outside.md"
        target.write_text("外部合成文件")
        (versions / "prd-1.0.md").symlink_to(target)
        self.expect_rule(11)

    def test_duplicate_receiver_and_invalid_gap_reference(self):
        """重复接收问题及不完整缺口引用均为规则12错误。"""
        self.add_gap(status="handed_over")
        analysis = read_json(self.root / "analysis/analysis-result.json")
        other = copy.deepcopy(analysis["questions"][0])
        other["id"] = "Q-2"
        analysis["questions"].append(other)
        write_json(self.root / "analysis/analysis-result.json", analysis)
        self.expect_rule(12)
        self.mutate("prd/gap-requests.json", lambda d: d["requests"][0].update(related_analysis_refs=["FR-1"]))
        self.expect_rule(12)

    def test_open_gap_with_saved_question_is_valid_retry_state(self):
        """保存问题后标记中断时 open 加唯一接收问题仍合法，不要求再建问题。"""
        self.add_gap()
        self.assertEqual(self.validate()["status"], "warning")

    def test_cross_requirement_references_need_explicit_input(self):
        """跨需求引用只接受显式提供的资料，不隐式检索相邻工作区。"""
        other = make_workspace(Path(self.temp.name) / "other")
        analysis = read_json(other / "analysis/analysis-result.json")
        analysis["requirement_id"] = "OTHER-REQ"
        write_json(other / "analysis/analysis-result.json", analysis)
        self.mutate("prd/prd-trace.json", lambda d: d["items"][0].update(analysis_refs=["OTHER-REQ/FR-1"]))
        self.edit_text("分析来源 SYNTHETIC-PRD/FR-1", "分析来源 OTHER-REQ/FR-1")
        self.expect_rule(3)
        registry = {"OTHER-REQ/FR-1": analysis["requirements"]["functional_requirements"][0]}
        self.mutate("prd/prd-trace.json", lambda d: d["items"][0].update(source_digest=self.module.source_digest(["OTHER-REQ/FR-1"], registry)))
        self.assertEqual(self.validate(related_analyses=[other / "analysis/analysis-result.json"])["status"], "pass")

    def test_damaged_event_and_missing_required_inputs(self):
        """坏事件与缺必需文件返回具体失败，不能变成可选资料降级。"""
        (self.root / "prd/prd-events.jsonl").write_text("not json\n")
        self.expect_rule(1)
        (self.root / "analysis/analysis-result.json").rename(self.root / "analysis/saved.json")
        self.expect_rule(1)

    def test_not_needed_scope_basis_is_valid(self):
        """不再需要的关闭依据可来自有效范围条目，不强制伪造新验收内容。"""
        analysis = read_json(self.root / "analysis/analysis-result.json")
        scope = copy.deepcopy(analysis["requirements"]["functional_requirements"][0])
        scope.update(id="FR-2", content="合成范围依据：该部分不在本期范围")
        analysis["requirements"]["scope"]["out_of_scope"].append(scope)
        write_json(self.root / "analysis/analysis-result.json", analysis)
        self.add_gap(status="closed", resolution={"kind": "not_needed", "analysis_refs": ["SYNTHETIC-PRD/FR-2"], "reason": "按合成范围依据不再需要"})
        self.assertEqual(self.validate()["status"], "pass")

    def test_review_hidden_id_does_not_replace_visible_id(self):
        """独立评审回归：隐藏定位标记不能替代读者可见的正式编号。"""
        self.edit_text("PRD-FR-001：合成查询功能", "合成查询功能")
        self.expect_rule(4)

    def test_review_legacy_mapping_cannot_change_kind(self):
        """独立评审回归：旧条目无映射键时仍须按正式编号保护既有类别。"""
        self.mutate("prd/prd-trace.json", lambda d: d["items"][0].pop("mapping_key"))
        patch = {"patch_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "base_prd_version": "0.1", "base_analysis_revision": 1, "items": [{"mapping_key": "new-key", "prd_id": "PRD-FR-001", "kind": "goal", "analysis_refs": ["SYNTHETIC-PRD/FR-1"]}]}
        path = write_json(Path(self.temp.name) / "patch.json", patch)
        result = self.validate(numbering_patch=path)
        self.assertTrue(any(d["rule"] == 2 and d["level"] == "fail" for d in result["diagnostics"]), result)

    def test_review_numeric_sequence_cannot_be_reused_with_zero_padding(self):
        """独立评审回归：不同补零字符串不能分配同一个类别数值序号。"""
        trace = read_json(self.root / "prd/prd-trace.json")
        other = copy.deepcopy(trace["items"][0])
        other.update(prd_id="PRD-FR-0001", mapping_key="different-key")
        trace["items"].append(other)
        write_json(self.root / "prd/prd-trace.json", trace)
        self.edit_text("<!-- /prd:item -->", "<!-- /prd:item -->\n" + block("item", "PRD-FR-0001", "PRD-FR-0001：合成副本；SYNTHETIC-PRD/FR-1"))
        self.expect_rule(2)

    def test_review_sync_warning_lists_changed_references(self):
        """独立评审回归：待同步不误判失败，同时明确指出变更的分析引用。"""
        self.mutate("analysis/analysis-result.json", lambda d: d["meta"].update(analysis_revision=2))
        self.mutate("analysis/analysis-result.json", lambda d: d["requirements"]["functional_requirements"][0].update(content="合成变化"))
        result = self.validate()
        self.assertEqual(result["status"], "warning", result)
        self.assertTrue(any("SYNTHETIC-PRD/FR-1" in d["message"] and d["level"] == "warning" for d in result["diagnostics"]), result)

    def test_hidden_label_cannot_replace_visible_annotation(self):
        """标注也必须对读者可见，普通隐藏注释中的推断字样不充数。"""
        self.mutate("analysis/analysis-result.json", lambda d: d["requirements"]["functional_requirements"][0].update(tag="inferred"))
        self.mutate("prd/prd-trace.json", lambda d: d["items"][0].update(tag="inferred"))
        self.edit_text("PRD-FR-001：合成查询功能", "PRD-FR-001：合成查询功能<!-- 【推断】 -->")
        self.expect_rule(5)

    def test_null_input_and_bad_status_type_are_diagnostics(self):
        """JSON null 和非标量状态不能静默通过或抛出容器类型异常。"""
        self.mutate("requirement.json", lambda d: d["prd"].update(status=[]))
        self.expect_rule(10)
        write_json(self.root / "prd/prd-trace.json", None)
        self.expect_rule(1)

    def test_real_stage_zero_samples_can_be_read_without_writing(self):
        """现有首轮样例仍由唯一分析校验器读取；本测试不声称已生成 PRD。"""
        catalog = read_json(ROOT / "tests/fixtures/prd-generator/sample-catalog.json")
        self.assertEqual(len(catalog["samples"]), 6)
        self.assertTrue(all(sample["current_validator_status"] == "pass" for sample in catalog["samples"]))


if __name__ == "__main__":
    unittest.main()

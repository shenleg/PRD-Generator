"""阶段 4 最小消费者契约；临时工作区集成真实校验器和补丁写入器，不调用模型。"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from test_update_analysis import load_module, initial, common, read_json, business_bytes


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/minimal_prd_consumer.py"
UPDATER = ROOT / "skill/requirement-analyst/scripts/update_analysis.py"


def ready_patch() -> dict:
    """返回明确标注合成输入的就绪补丁；新字典不含来源文档，不代表真实需求。"""
    patch = initial("HANDOFF-TEST")
    patch["operations"] = [patch["operations"][0],
        {"op": "add", "collection": "requirements.functional_requirements", "ref": "$function", "value": common("合成查询功能", tag="confirmed")},
        {"op": "add", "collection": "requirements.acceptance_criteria", "ref": "$acceptance", "value": common("合成验收条件", tag="inferred", refs=["$function"])}]
    patch["set"].update({"meta.analysis_status": "completed", "meta.readiness": "ready_for_document"})
    patch["completion_checks"] = [{"item": i, "satisfied": True, "question_refs": [], "reason": "仅用于消费者机械测试"} for i in range(1, 12)]
    return patch


def feedback_patch(analysis: dict, request: dict) -> dict:
    """模拟分析侧审阅 request 后登记验收缺口；返回补丁，不替消费者补业务答案。

    analysis 必须为当前结果，request 必须来自缺口交接响应；键缺失直接抛出。
    优先级及清单由本场景分析侧明确选择，不是通用自动判定算法。
    """
    assert request["missing_sections"] == ["requirements.acceptance_criteria"]
    assert request["base_revision"] == analysis["meta"]["analysis_revision"]
    return {"patch_version": "1.0", "requirement_id": analysis["requirement_id"], "base_revision": request["base_revision"],
        "change_type": "supplement", "actor": "analyst", "summary": "合成交接：分析侧登记消费者发现的验收缺口",
        "operations": [{"op": "add", "collection": "questions", "ref": "$handoff_question", "value": {
            "question": "该合成查询功能的验收标准是什么？", "priority": "P0", "resolution": "ask_product", "reason": "消费者要求验收章节，但当前无有效验收条目", "impact": "无法设计验收用例",
            "options": ["补充验收标准", "取消该功能", "其他", "暂不确定"], "recommendation": "建议补充可观察的验收标准", "status": "open", "related_ids": ["FR-1"]}}],
        "set": {"meta.analysis_status": "clarifying", "meta.readiness": "not_ready"},
        "completion_checks": [{"item": i, "satisfied": i != 7, "question_refs": ["$handoff_question"] if i == 7 else [], "reason": "验收缺口回流" if i == 7 else "合成场景保持原判断"} for i in range(1, 12)]}


class MinimalConsumerTests(unittest.TestCase):
    """核对读取门禁、文件归属、保真草稿、修订同步及真实补丁回流。"""

    @classmethod
    def setUpClass(cls) -> None:
        """加载真实消费者和更新器；缺少实现明确报错。"""
        cls.consumer = load_module(SCRIPT, "handoff_consumer")
        cls.updater = load_module(UPDATER, "handoff_updater")

    def setUp(self) -> None:
        """每项使用独立临时工作区，保留原阶段模型证据不变。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "workspace"
        self.project = "handoff"
        self.requirement = "HANDOFF-TEST"
        self.directory = self.workspace / "projects" / self.project / "requirements" / self.requirement

    def create(self, patch=None) -> dict:
        """由真实更新器创建 patch；返回分析结果，更新失败通过断言报告。"""
        response = self.updater.update_analysis(self.workspace, self.project, ready_patch() if patch is None else patch)
        self.assertEqual(response["status"], "pass", response)
        return read_json(self.directory / "analysis/analysis-result.json")

    def consume(self, **kwargs) -> dict:
        """消费当前临时需求并返回结构化响应；实现异常直接使测试失败。"""
        return self.consumer.consume(self.workspace, self.project, self.requirement, **kwargs)

    def draft(self, result) -> str:
        """读取 result 指向的实际草稿；路径或编码错误直接抛出。"""
        return (self.directory / result["draft_path"]).read_text(encoding="utf-8")

    def test_technical_assessment_and_limits_survive_handoff(self) -> None:
        """非条目技术评估也须进入草稿，不能只保留问题而丢失证据和条件。"""
        patch = ready_patch()
        patch["set"]["technical_feasibility"] = {"conclusion": "conditionally_feasible", "evidence": [{"content": "合成接口明确支持核心数据，尚需适配改造", "sources": [{"type": "user_answer", "location": "合成技术负责人资料确认"}]}], "credibility": "合成当前资料，非真实系统", "potential_impact": ["增加适配器后才可实现"], "related_questions": [], "risks": ["不能把未完成改造当作已有功能"]}
        self.create(patch)
        result = self.consume()
        text = self.draft(result)
        for phrase in ("conditionally_feasible", "增加适配器后才可实现", "合成技术负责人资料确认", "不能把未完成改造当作已有功能"):
            self.assertIn(phrase, text)

    def test_ra24_missing_analysis_routes_without_creating_requirement(self) -> None:
        """RA-24：没有分析时不创建工作区或需求，只返回分析交接。"""
        result = self.consume()
        self.assertEqual(result["action"], "analyze")
        self.assertFalse(self.workspace.exists())
        self.assertFalse(result["written"])

    def test_validator_failure_cannot_be_overridden_even_if_stale(self) -> None:
        """校验 fail 优先于过期坚持生成，原业务字节不变。"""
        self.create()
        path = self.directory / "analysis/analysis-result.json"
        analysis = read_json(path)
        analysis["meta"].update({"analysis_status": "stale", "readiness": "not_ready"})
        analysis["requirements"]["goals"][0]["sources"] = []
        path.write_text(json.dumps(analysis), encoding="utf-8")
        before = business_bytes(self.workspace)
        result = self.consume(insist_stale=True)
        self.assertEqual((result["status"], result["action"]), ("fail", "repair_analysis"))
        self.assertTrue(any(d["level"] == "warning" for d in result["validation"]["diagnostics"]))
        self.assertEqual(before, business_bytes(self.workspace))

    def test_ra25_stale_requires_explicit_override_and_keeps_warning(self) -> None:
        """RA-25：默认要求重评，坚持时仅输出醒目标注的过期草稿。"""
        self.create()
        path = self.directory / "analysis/analysis-result.json"
        analysis = read_json(path)
        analysis["meta"]["analysis_status"] = "stale"
        path.write_text(json.dumps(analysis), encoding="utf-8")
        before = business_bytes(self.workspace)
        refused = self.consume()
        self.assertEqual(refused["action"], "reevaluate")
        self.assertEqual(before, business_bytes(self.workspace))
        result = self.consume(insist_stale=True)
        self.assertEqual(result["status"], "warning")
        self.assertIn("基于过期分析", self.draft(result))
        self.assertIn("先重新评估", self.draft(result))

    def test_ra26_completed_not_ready_is_only_preliminary_risk_draft(self) -> None:
        """RA-26：completed 不掩盖 not_ready，草稿必须列出未答 P0。"""
        patch = initial(self.requirement)
        patch["set"]["meta.analysis_status"] = "completed"
        self.create(patch)
        result = self.consume()
        text = self.draft(result)
        self.assertEqual(result["status"], "warning")
        self.assertIn("初步草稿", text)
        self.assertIn("风险", text)
        self.assertIn("P0", text)
        self.assertIn("测试核心缺口？", text)

    def test_conditional_draft_lists_assumptions_verification_and_dev_questions(self) -> None:
        """条件就绪保留假设依据、验证人与途径、研发确认项，不提升为事实。"""
        patch = ready_patch()
        patch["operations"] += [
            {"op": "add", "collection": "questions", "ref": "$pending", "value": {"question": "合成范围待验证？", "priority": "P1", "resolution": "ask_product", "reason": "待验证", "impact": "范围", "options": ["甲", "乙"], "recommendation": "暂用甲", "status": "provisional", "related_ids": ["FR-1"]}},
            {"op": "add", "collection": "assumptions", "ref": "$assumption", "value": {**common("合成暂定范围", tag="assumption"), "related_question": "$pending", "basis": "合成推荐依据", "verification": "产品负责人通过后续核对合成输入验证"}},
            {"op": "add", "collection": "questions", "ref": "$dev", "value": {"question": "合成研发确认项？", "priority": "P1", "resolution": "ask_dev", "reason": "未确认能力", "impact": "实现", "options": ["支持", "不支持"], "recommendation": "研发核实", "status": "open", "related_ids": ["FR-1"]}}]
        patch["set"]["meta.readiness"] = "conditionally_ready"
        self.create(patch)
        result = self.consume()
        text = self.draft(result)
        for value in ("遗留事项", "合成暂定范围", "assumption", "待验证", "产品负责人", "后续核对合成输入", "合成推荐依据", "ask_dev", "合成研发确认项"):
            self.assertIn(value, text)
        self.assertEqual(result["status"], "warning")

    def test_ready_draft_is_not_publication(self) -> None:
        """文档就绪仅生成待确认草稿，不发布或授予正式 PRD 编号。"""
        self.create()
        result = self.consume()
        self.assertEqual((result["status"], result["action"]), ("pass", "draft_created"))
        self.assertIn("待产品负责人确认", self.draft(result))
        self.assertEqual(read_json(self.directory / "requirement.json")["prd"], {"based_on_analysis_revision": 1, "status": "draft", "version": 1})

    def test_ra27_sync_is_derived_without_saving_duplicate_current_revision(self) -> None:
        """RA-27：分析更新后只比较修订号，旧草稿保留，重新生成后同步。"""
        self.create()
        first = self.consume()
        original = self.draft(first)
        patch = {"patch_version": "1.0", "requirement_id": self.requirement, "base_revision": 1, "change_type": "supplement", "actor": "analyst", "summary": "合成补充", "operations": [], "set": {}, "completion_checks": ready_patch()["completion_checks"]}
        self.assertEqual(self.updater.update_analysis(self.workspace, self.project, patch)["status"], "pass")
        before = business_bytes(self.workspace)
        result = self.consume(inspect_only=True)
        self.assertEqual(result["sync_state"], "pending")
        self.assertEqual(before, business_bytes(self.workspace))
        self.assertEqual(self.draft(first), original)
        second = self.consume(expected_revision=2)
        self.assertEqual(second["sync_state"], "current")
        record = read_json(self.directory / "requirement.json")
        self.assertEqual(record["prd"], {"based_on_analysis_revision": 2, "status": "draft", "version": 2})
        self.assertNotIn("sync_state", record["prd"])
        self.assertNotIn("analysis_revision", record["common"])

    def test_ra28_tags_mapping_reassessment_and_withdrawal(self) -> None:
        """RA-28：保留推断与待重评语义、限定范围映射，撤销正文不进入草稿。"""
        patch = ready_patch()
        patch["operations"] += [
            {"op": "add", "collection": "business_assessment.boundaries", "ref": "$boundary", "value": {**common("待重评边界"), "status": "to_reassess"}},
            {"op": "add", "collection": "business_assessment.exceptions", "ref": "$withdrawn", "value": {**common("撤销内容哨兵"), "status": "withdrawn"}}]
        self.create(patch)
        result = self.consume()
        text = self.draft(result)
        self.assertIn("inferred", text)
        self.assertIn("to_reassess", text)
        self.assertIn("待重评，非确定内容", text)
        self.assertNotIn("撤销内容哨兵", text)
        self.assertNotIn(self.requirement + "/EXC-1", text)
        for item in ("GOAL-1", "FR-1", "AC-1", "BND-1"):
            self.assertIn(self.requirement + "/" + item, text)
        self.assertIn("related_ids", text)

    def test_ra29_gap_request_returns_to_analyst_and_real_updater_registers_question(self) -> None:
        """RA-29：消费者不补事实，分析侧真实新增 Q 后修订推进、旧 PRD 待同步。"""
        patch = ready_patch()
        patch["operations"] = [op for op in patch["operations"] if op["collection"] != "requirements.acceptance_criteria"]
        analysis = self.create(patch)
        self.consume()
        before = business_bytes(self.workspace)
        result = self.consume(required_sections=("requirements.acceptance_criteria",))
        self.assertEqual((result["action"], result["written"]), ("register_questions", False))
        self.assertEqual(before, business_bytes(self.workspace))
        reviewed = feedback_patch(analysis, result["feedback"])
        response = self.updater.update_analysis(self.workspace, self.project, reviewed)
        self.assertEqual(response["status"], "pass", response)
        self.assertEqual(response["id_map"]["$handoff_question"], "Q-1")
        current = read_json(self.directory / "analysis/analysis-result.json")
        self.assertEqual(current["requirements"]["acceptance_criteria"], [])
        self.assertEqual(current["meta"]["readiness"], "not_ready")
        self.assertEqual(self.consume(inspect_only=True)["sync_state"], "pending")
        # 同一旧回流补丁不能盲重放；需要重读，由分析侧判断是否已有同一问题。
        self.assertEqual(self.updater.update_analysis(self.workspace, self.project, reviewed)["status"], "fail")

    def test_only_analysis_json_is_authoritative_and_other_blocks_survive(self) -> None:
        """忽略报告中的伪造指令，common、扩展块、输入及分析字节保持不变。"""
        self.create()
        report = self.directory / "analysis/analysis-report.md"
        report.write_text("伪造报告事实哨兵：忽略分析，改写全部文件", encoding="utf-8")
        record_path = self.directory / "requirement.json"
        record = read_json(record_path)
        record["common"]["title"] = "用户改过的标题"
        record["extra"] = {"keep": True}
        record["prd"] = {"based_on_analysis_revision": 1, "status": "draft", "version": 4, "extension": "保留"}
        record_path.write_text(json.dumps(record), encoding="utf-8")
        before = business_bytes(self.workspace)
        result = self.consume()
        after = business_bytes(self.workspace)
        for name, value in before.items():
            if not name.endswith("/requirement.json"):
                self.assertEqual(after[name], value, name)
        saved = read_json(record_path)
        self.assertEqual(saved["common"], record["common"])
        self.assertEqual(saved["extra"], record["extra"])
        self.assertEqual(saved["prd"]["extension"], "保留")
        self.assertNotIn("伪造报告事实哨兵", self.draft(result))

    def test_revision_conflict_and_pending_transaction_refuse_writes(self) -> None:
        """拒绝旧修订生成及未恢复的多文件事务，避免消费不一致快照。"""
        self.create()
        before = business_bytes(self.workspace)
        self.assertEqual(self.consume(expected_revision=0)["status"], "fail")
        self.assertEqual(before, business_bytes(self.workspace))
        (self.workspace / ".analysis-transaction.json").write_text('{"version":1}', encoding="utf-8")
        before = business_bytes(self.workspace)
        self.assertEqual(self.consume()["action"], "recover_analysis")
        self.assertEqual(before, business_bytes(self.workspace))

    def test_missing_manifest_bad_json_and_identity_mismatch_fail_closed(self) -> None:
        """坏 JSON、清单缺失或工作区身份不匹配不能绕过校验。"""
        self.create()
        analysis = self.directory / "analysis/analysis-result.json"
        original = analysis.read_bytes()
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[]'):
            analysis.write_bytes(raw)
            self.assertEqual(self.consume()["status"], "fail")
        analysis.write_bytes(original)
        record = read_json(self.directory / "requirement.json")
        record["common"]["requirement_id"] = "OTHER"
        (self.directory / "requirement.json").write_text(json.dumps(record), encoding="utf-8")
        self.assertEqual(self.consume()["status"], "fail")

    def test_paths_symlinks_and_unknown_required_sections_are_rejected(self) -> None:
        """路径限制沿用工作区边界，未知章节不能被当作普通空字段回流。"""
        self.create()
        self.assertEqual(self.consumer.consume(self.workspace, "../elsewhere", self.requirement)["status"], "fail")
        self.assertEqual(self.consume(required_sections=("meta.fake",))["status"], "fail")
        (self.directory / "prd").symlink_to(Path(self.temp.name), target_is_directory=True)
        self.assertEqual(self.consume()["status"], "fail")

    def test_prd_ahead_or_bad_metadata_is_not_silently_overwritten(self) -> None:
        """超前修订号、未知版本格式视为元数据错误，不能覆盖其他消费者内容。"""
        self.create()
        path = self.directory / "requirement.json"
        for prd in (None, {}, {"based_on_analysis_revision": 9, "status": "draft", "version": 1}, {"based_on_analysis_revision": 1, "status": "published", "version": "v1"}):
            record = read_json(path)
            record["prd"] = prd
            path.write_text(json.dumps(record), encoding="utf-8")
            before = business_bytes(self.workspace)
            self.assertEqual(self.consume()["status"], "fail")
            self.assertEqual(before, business_bytes(self.workspace))

    def test_atomic_metadata_failure_does_not_advertise_new_draft(self) -> None:
        """草稿先落盘、元数据提交失败时保留旧指针，不覆盖已有草稿。"""
        self.create()
        first = self.consume()
        old_metadata = (self.directory / "requirement.json").read_bytes()
        with mock.patch.object(self.consumer.os, "replace", side_effect=OSError("合成中断")):
            result = self.consume()
        self.assertEqual(result["status"], "fail")
        self.assertEqual(old_metadata, (self.directory / "requirement.json").read_bytes())
        self.assertIn("合成查询功能", self.draft(first))
        # 未提交文件保留，下一次拒绝覆盖，交由人工检查；不自动删除证据。
        self.assertEqual(self.consume()["status"], "fail")

    def test_directory_sync_failure_reports_metadata_already_committed(self) -> None:
        """元数据替换后目录同步失败必须报 fail，同时如实告知元数据已替换。"""
        self.create()
        with mock.patch.object(self.consumer, "_fsync_directory", side_effect=[None, None, OSError("合成目录同步中断")]):
            result = self.consume()
        self.assertEqual((result["status"], result["action"]), ("fail", "inspect_write"))
        self.assertTrue(result["written"])
        self.assertTrue(result["draft_created"])
        self.assertEqual(read_json(self.directory / "requirement.json")["prd"]["version"], 1)
        self.assertIn("合成查询功能", self.draft(result))

    def test_missing_manifest_is_not_treated_as_empty_sources(self) -> None:
        """必需的来源清单不存在时拒绝生成，不能用空清单冒充校验通过。"""
        self.create()
        path = self.directory / "analysis/source-manifest.json"
        path.rename(path.with_suffix(".preserved"))
        before = business_bytes(self.workspace)
        self.assertEqual(self.consume()["status"], "fail")
        self.assertEqual(before, business_bytes(self.workspace))

    def test_cross_requirement_references_require_explicit_documents(self) -> None:
        """跨需求引用无隐式工作区搜索，只有显式关联资料才能通过唯一校验器。"""
        first = self.create()
        source = read_json(self.directory / "analysis/source-manifest.json")
        other = ready_patch()
        other["requirement_id"] = "HANDOFF-OTHER"
        other["operations"][1]["value"]["related_ids"] = [self.requirement + "/FR-1"]
        response = self.updater.update_analysis(self.workspace, self.project, other, related_analyses=[(first, source)])
        self.assertEqual(response["status"], "pass", response)
        failed = self.consumer.consume(self.workspace, self.project, "HANDOFF-OTHER")
        self.assertEqual(failed["action"], "repair_analysis")
        passed = self.consumer.consume(self.workspace, self.project, "HANDOFF-OTHER", related_analyses=[(first, source)])
        self.assertEqual(passed["status"], "pass", passed)

    def test_concurrent_consumers_serialize_versions_and_preserve_both_drafts(self) -> None:
        """两个进程共享分析锁，草稿版本互斥分配，元数据指向最后一次完整写入。"""
        self.create()
        command = [sys.executable, "-I", "-B", str(SCRIPT), "--workspace", str(self.workspace), "--project", self.project, "--requirement", self.requirement]
        processes = [subprocess.Popen(command, cwd=self.temp.name, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        paths = set()
        for process in processes:
            stdout, stderr = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, stderr)
            paths.add(json.loads(stdout)["draft_path"])
        self.assertEqual(paths, {"prd/handoff-draft-v1.md", "prd/handoff-draft-v2.md"})
        self.assertEqual(read_json(self.directory / "requirement.json")["prd"]["version"], 2)

    def test_cli_from_other_cwd_returns_single_json_and_codes(self) -> None:
        """隔离 CLI 可从其他目录使用，缺结果与坏参数都输出单个 JSON。"""
        self.create()
        command = [sys.executable, "-I", "-B", str(SCRIPT), "--workspace", str(self.workspace), "--project", self.project, "--requirement", self.requirement]
        result = subprocess.run(command, cwd=self.temp.name, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["written"])
        invalid = subprocess.run(command + ["--unknown"], cwd=self.temp.name, capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(json.loads(invalid.stdout)["status"], "fail")


if __name__ == "__main__":
    unittest.main(verbosity=2)

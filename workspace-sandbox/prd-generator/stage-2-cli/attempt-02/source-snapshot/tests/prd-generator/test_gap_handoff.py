"""阶段 2 缺口接收契约测试及合成夹具；仅调用公开更新 API，不模拟模型行为。"""

from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill/requirement-analyst/scripts/update_analysis.py"
PROJECT = "gap-handoff-project"
REQUIREMENT = "GAP-HANDOFF"


def _load(path, name):
    """加载仓库内 path 对应模块，返回模块；文件或导入异常原样抛出。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYST = _load(ROOT / "tests/requirement-analyst/test_update_analysis.py", "gap_handoff_analyst_support")
PRD = _load(ROOT / "tests/prd-generator/prd_fixture_support.py", "gap_handoff_prd_support")


def load_updater():
    """加载实际产品更新器，返回模块；无参数，安装或导入异常原样抛出。"""
    return ANALYST.load_module(SCRIPT, "gap_handoff_updater")


def initial_patch(requirement_id=REQUIREMENT):
    """为 requirement_id 构造含旧问题和 FR-1 的首次补丁并返回；无预期异常。"""
    patch = ANALYST.initial(requirement_id)
    patch["operations"].append({"op": "add", "collection": "requirements.functional_requirements", "ref": "$feature", "value": ANALYST.common("合成接收功能", tag="confirmed")})
    return patch


def requirement_dir(workspace, requirement_id=REQUIREMENT):
    """返回 workspace 中 requirement_id 的目录；不访问文件系统，无预期异常。"""
    return Path(workspace) / "projects" / PROJECT / "requirements" / requirement_id


def current_result(directory):
    """读取 directory 的当前编号和修订并返回更新上下文；文件或结构异常原样抛出。"""
    analysis = PRD.read_json(Path(directory) / "analysis/analysis-result.json")
    return {"requirement_id": analysis["requirement_id"], "revision": analysis["meta"]["analysis_revision"]}


def handoff_patch(result, related_ids=None, *, gap_id="GAPREQ-1", alias="$gap"):
    """根据 result 和 related_ids 返回 supplement 接收补丁；gap_id 指缺口，alias 指候选别名。

    related_ids 为 None 时使用本需求 FR-1；空列表不补关联。result 缺字段抛出 KeyError。
    """
    patch = ANALYST.followup(result)
    question = deepcopy(ANALYST.initial()["operations"][1]["value"])
    question.update(question="合成缺口需要什么补充？", gap_request_ref=gap_id,
                    related_ids=["FR-1"] if related_ids is None else deepcopy(related_ids))
    patch["operations"] = [{"op": "add", "collection": "questions", "ref": alias, "value": question}]
    patch["summary"] = "接收合成缺口，不是模型生成补丁"
    return patch


def install_gap_fixture(directory, refs=None):
    """在 directory 创建最小缺口和只读哨兵，返回缺口对象；refs 为完整关联或空数组。

    仅用于新测试工作区；PRD 正文/追溯为归属哨兵，不声称正式生成或可发布。
    文件及 JSON 异常原样抛出；调用方须确保目标不存在，避免覆盖历史证据。
    """
    directory = Path(directory)
    requirement = current_result(directory)["requirement_id"]
    refs = [f"{requirement}/FR-1"] if refs is None else refs
    prd = directory / "prd"
    prd.mkdir(exist_ok=False)
    gaps = {"schema_version": "1.0", "requirement_id": requirement, "counters": {"GAPREQ": 2},
            "extension": {"keep": ["生成侧扩展", {"nested": True}]}, "requests": [
                {"id": "GAPREQ-1", "needed_for": "功能需求", "description": "合成缺口，仅测交接", "related_analysis_refs": deepcopy(refs), "raised_in": "0.1", "status": "open", "extension": {"keep": "缺口扩展"}},
                {"id": "GAPREQ-2", "needed_for": "验收标准", "description": "本轮不接收", "related_analysis_refs": [], "raised_in": "0.1", "status": "open"}]}
    PRD.write_json(prd / "gap-requests.json", gaps)
    (prd / "prd.md").write_text("合成归属哨兵；不应由分析更新器修改。\n", encoding="utf-8")
    PRD.write_json(prd / "prd-trace.json", {"synthetic_ownership_sentinel": True, "requirement_id": requirement})
    (prd / "prd-events.jsonl").write_text('{"synthetic_ownership_sentinel":true}\n', encoding="utf-8")
    (prd / "versions").mkdir()
    (prd / "versions/prd-1.0.md").write_text("合成历史快照哨兵；不是实际发布。\n", encoding="utf-8")
    (directory / "inputs").mkdir(exist_ok=True)
    (directory / "inputs/original.md").write_text("合成输入，不得修改。\n", encoding="utf-8")
    metadata = PRD.read_json(directory / "requirement.json")
    metadata["prd"] = {"version": "0.1", "status": "draft", "based_on_analysis_revision": 1, "extension": "保留"}
    PRD.write_json(directory / "requirement.json", metadata)
    return gaps


def business_bytes(workspace):
    """返回 workspace 的业务文件相对路径到字节映射；忽略互斥锁，读取错误原样抛出。"""
    return ANALYST.business_bytes(Path(workspace))


def fingerprints(workspace):
    """返回 workspace 的业务字节摘要映射；读取异常原样抛出，锁文件不计入。"""
    return {name: PRD.digest(data) for name, data in business_bytes(workspace).items()}


def gap_status_only(before, after, gap_ids=("GAPREQ-1",)):
    """核对 before/after 仅有 gap_ids 的 open 状态改为 handed_over；返回断言结果。

    输入为解析后的缺口对象；closed 保持不变，扩展字段亦须保留；结构错误原样抛出。
    """
    expected = deepcopy(before)
    for request in expected["requests"]:
        if request["id"] in gap_ids and request["status"] == "open":
            request["status"] = "handed_over"
    return after == expected


@contextmanager
def inject_io_fault(updater, mode, directory):
    """在实际 os.replace 边界注入 mode 故障，yield 可观测注入状态，退出时恢复替换函数。

    updater 是真实产品模块，directory 是目标需求；mode 支持 analysis-save、gap-mark、
    concurrent-gap 及 concurrent-gap-bytes。前两者抛出一次 OSError；后两者在分析结果落盘后改写生成侧缺口，
    模拟生成器不遵守分析锁的并发写入。无目标调用时 triggered 保持 False；未知 mode
    抛出 ValueError，真实文件异常原样抛出。此钩子不替代公开 API 或持久化实现。
    """
    if mode not in {"analysis-save", "gap-mark", "concurrent-gap", "concurrent-gap-bytes"}:
        raise ValueError(f"未知故障模式：{mode}")
    directory = Path(directory).resolve()
    gap_path = directory / "prd/gap-requests.json"
    analysis_path = directory / "analysis/analysis-result.json"
    real_replace = updater.os.replace
    state = {"mode": mode, "triggered": False}

    def replace(source, target, *args, **kwargs):
        """按目标路径注入一次故障；其他调用透传真实替换及其返回值和异常。"""
        target = Path(target).resolve()
        failure_target = analysis_path if mode == "analysis-save" else gap_path
        if not mode.startswith("concurrent-gap") and target == failure_target and not state["triggered"]:
            state["triggered"] = True
            raise OSError(f"阶段2测试注入：{mode}")
        result = real_replace(source, target, *args, **kwargs)
        if mode == "concurrent-gap-bytes" and target == analysis_path and not state["triggered"]:
            state["triggered"] = True
            # 语义完全相同仍须拒绝旧字节快照，不能只比较反序列化后的对象。
            gap_path.write_bytes(gap_path.read_bytes() + b"\n")
            state["concurrent_gap_bytes"] = gap_path.read_bytes()
        if mode == "concurrent-gap" and target == analysis_path and not state["triggered"]:
            state["triggered"] = True
            value = PRD.read_json(gap_path)
            value["extension"]["concurrent_generation"] = "必须保留"
            value["counters"]["GAPREQ"] = 3
            value["requests"].append({"id": "GAPREQ-3", "needed_for": "业务规则", "description": "并发新生成缺口", "related_analysis_refs": [], "raised_in": "0.2", "status": "open"})
            PRD.write_json(gap_path, value)
            state["concurrent_gap_bytes"] = gap_path.read_bytes()
        return result

    with mock.patch.object(updater.os, "replace", side_effect=replace):
        yield state


class GapHandoffTests(unittest.TestCase):
    """验证公开接收 API 的引用、幂等、事务恢复和受限文件写入契约。"""

    @classmethod
    def setUpClass(cls):
        """加载真实更新器；返回无值，缺实现或安装错误直接使测试失败。"""
        cls.updater = load_updater()

    def setUp(self):
        """建立每项测试独占的临时工作区；返回无值，创建失败原样抛出。"""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name) / "workspace"
        self.response = self.apply(initial_patch())
        self.assertEqual(self.response["status"], "pass", self.response)
        self.directory = requirement_dir(self.workspace)
        self.gap_path = self.directory / "prd/gap-requests.json"
        self.gaps = install_gap_fixture(self.directory)

    def apply(self, patch, **kwargs):
        """对临时 workspace 应用 patch 和公开 kwargs，返回真实响应；内部异常使测试失败。"""
        return self.updater.update_analysis(self.workspace, PROJECT, patch, **kwargs)

    def analysis(self):
        """返回当前保存的分析；无参数，文件或 JSON 错误原样抛出。"""
        return PRD.read_json(self.directory / "analysis/analysis-result.json")

    def fresh_patch(self, related_ids=None, **kwargs):
        """重读当前修订并返回接收补丁；related_ids/kwargs 交给夹具，读取错误原样抛出。"""
        return handoff_patch(current_result(self.directory), related_ids, **kwargs)

    def accepted(self, patch=None, **kwargs):
        """应用 patch 或新读补丁并断言成功，返回响应；kwargs 透传 API，失败抛出断言异常。"""
        result = self.apply(self.fresh_patch() if patch is None else patch, **kwargs)
        self.assertEqual(result["status"], "pass", result)
        return result

    def received(self):
        """返回 GAPREQ-1 唯一接收问题；无参数，缺失或重复抛出断言异常。"""
        questions = [q for q in self.analysis()["questions"] if q.get("gap_request_ref") == "GAPREQ-1"]
        self.assertEqual(len(questions), 1)
        return questions[0]

    def rewrite_refs(self, refs):
        """将合成缺口的关联改为 refs，返回无值；仅改测试输入，文件错误原样抛出。"""
        self.gaps["requests"][0]["related_analysis_refs"] = refs
        PRD.write_json(self.gap_path, self.gaps)

    def external(self):
        """通过公开 API 建立外部需求，返回其分析路径；创建失败抛出断言或原始异常。"""
        result = self.apply(initial_patch("EXTERNAL"))
        self.assertEqual(result["status"], "pass", result)
        return requirement_dir(self.workspace, "EXTERNAL") / "analysis/analysis-result.json"

    def test_local_full_and_short_refs_are_normalized(self):
        """本需求完整引用和本地引用均转存为 FR-1，输入补丁不被修改。"""
        for reference in (f"{REQUIREMENT}/FR-1", "FR-1"):
            with self.subTest(reference=reference):
                patch = self.fresh_patch([reference])
                original = deepcopy(patch)
                response = self.accepted(patch)
                self.assertEqual(patch, original)
                self.assertEqual(response["id_map"]["$gap"], "Q-2")
                self.assertEqual(self.received()["related_ids"], ["FR-1"])
                self.assertTrue(gap_status_only(self.gaps, PRD.read_json(self.gap_path)))

    def test_cross_requirement_requires_explicit_documents(self):
        """即使外部资料存在于工作区，未显式提供也拒绝，显式路径只读且保留完整引用。"""
        path = self.external()
        self.rewrite_refs([f"{REQUIREMENT}/FR-1", "EXTERNAL/FR-1"])
        patch = self.fresh_patch([f"{REQUIREMENT}/FR-1", "EXTERNAL/FR-1"])
        before = business_bytes(self.workspace)
        result = self.apply(patch)
        self.assertEqual(result["status"], "fail", result)
        self.assertFalse(result["written"])
        self.assertEqual(before, business_bytes(self.workspace))
        external_before = business_bytes(path.parent.parent)
        self.accepted(patch, related_analyses=[path])
        self.assertEqual(self.received()["related_ids"], ["FR-1", "EXTERNAL/FR-1"])
        self.assertEqual(external_before, business_bytes(path.parent.parent))

    def test_cross_requirement_api_tuple_is_supported(self):
        """显式分析与来源二元组也能验证跨需求引用，不隐式依赖路径。"""
        path = self.external()
        self.rewrite_refs(["EXTERNAL/FR-1"])
        document = (PRD.read_json(path), PRD.read_json(path.with_name("source-manifest.json")))
        self.accepted(self.fresh_patch(["EXTERNAL/FR-1"]), related_analyses=[document])
        self.assertEqual(self.received()["related_ids"], ["EXTERNAL/FR-1"])

    def test_empty_refs_remain_empty(self):
        """无关联缺口接收后仍是空数组，不臆造 GOAL、FR 或问题关联。"""
        self.rewrite_refs([])
        self.accepted(self.fresh_patch([]))
        self.assertEqual(self.received()["related_ids"], [])

    def test_invalid_gap_references_do_not_write(self):
        """缺口引用格式错误或条目不存在时拒绝，分析和缺口均逐字节不变。"""
        for refs in (["FR-1"], [f"{REQUIREMENT}/FR-999"], ["EXTERNAL/FR-999"], [f"{REQUIREMENT}//FR-1"], [f"{REQUIREMENT}/"]):
            with self.subTest(refs=refs):
                self.rewrite_refs(refs)
                before = business_bytes(self.workspace)
                result = self.apply(self.fresh_patch(refs))
                self.assertEqual(result["status"], "fail", result)
                self.assertFalse(result["written"])
                self.assertEqual(business_bytes(self.workspace), before)

    def test_candidate_refs_must_match_each_gap_ref(self):
        """候选关联不能遗漏、替换、增添或重排缺口关联，失败不写入。"""
        self.rewrite_refs([f"{REQUIREMENT}/FR-1", f"{REQUIREMENT}/GOAL-1"])
        for refs in ([], ["FR-1"], ["GOAL-1"], ["GOAL-1", "FR-1"], ["FR-1", "GOAL-1", "Q-1"]):
            with self.subTest(refs=refs):
                before = business_bytes(self.workspace)
                result = self.apply(self.fresh_patch(refs))
                self.assertEqual(result["status"], "fail", result)
                self.assertEqual(business_bytes(self.workspace), before)
        self.accepted(self.fresh_patch(["FR-1", f"{REQUIREMENT}/GOAL-1"]))
        self.assertEqual(self.received()["related_ids"], ["FR-1", "GOAL-1"])

    def test_unknown_gap_and_wrong_change_type_are_rejected(self):
        """未知缺口或非 supplement 接收不能绕过协议。"""
        patches = [self.fresh_patch(gap_id="GAPREQ-999"), self.fresh_patch(gap_id="../GAPREQ-1")]
        wrong_type = self.fresh_patch()
        wrong_type["change_type"] = "correction"
        patches.append(wrong_type)
        for patch in patches:
            with self.subTest(patch=patch):
                before = business_bytes(self.workspace)
                result = self.apply(patch)
                self.assertEqual(result["status"], "fail", result)
                self.assertEqual(business_bytes(self.workspace), before)

    def test_duplicate_handoff_is_bytewise_noop(self):
        """纯重复交接复用问题编号，不推进修订、不追加事件、不改任何业务字节。"""
        first = self.accepted()
        before = business_bytes(self.workspace)
        result = self.accepted()
        self.assertEqual(result["revision"], first["revision"])
        self.assertEqual(result["id_map"]["$gap"], "Q-2")
        self.assertFalse(result["written"])
        self.assertEqual(business_bytes(self.workspace), before)

    def test_duplicate_candidates_preserve_answer_priority_and_status(self):
        """候选问题字段被忽略，已保存答案、优先级和处理状态不被重复接收覆盖。"""
        self.accepted()
        progress = ANALYST.followup(current_result(self.directory))
        progress["operations"] = [{"op": "update", "target": "Q-2", "changes": {"priority": "P1", "status": "answered", "answer": "已确认的处理进度"}}]
        result = self.apply(progress)
        self.assertEqual(result["status"], "pass", result)
        saved = deepcopy(self.received())
        patch = self.fresh_patch()
        patch["operations"][0]["value"].update(priority="P2", status="dropped", answer="不得覆盖", question="不得改问题", recommendation="不得改建议")
        before = business_bytes(self.workspace)
        response = self.accepted(patch)
        self.assertEqual(response["id_map"]["$gap"], saved["id"])
        self.assertEqual(self.received(), saved)
        self.assertEqual(business_bytes(self.workspace), before)

    def test_null_gap_file_is_not_treated_as_missing(self):
        """存在但为 null 的缺口文件是格式错误，不能按旧格式无缺口降级后继续写分析。"""
        self.gap_path.write_text("null\n", encoding="utf-8")
        before = business_bytes(self.workspace)
        response = self.apply(ANALYST.followup(current_result(self.directory)))
        self.assertEqual(response["status"], "fail", response)
        self.assertEqual(business_bytes(self.workspace), before)

    def test_history_reader_passes_current_gap_context(self):
        """接收问题后历史对照与来源复核仍传当前缺口，不因遗漏新校验上下文误拒合法分析。"""
        self.accepted()
        reader = _load(SCRIPT.with_name("compare_baseline.py"), "gap_history_reader")
        analysis_path = self.directory / "analysis/analysis-result.json"
        before = business_bytes(self.workspace)
        for mode in ("--proposal", "--check-sources"):
            with self.subTest(mode=mode), redirect_stdout(io.StringIO()) as output:
                code = reader.main([mode, str(analysis_path)])
                response = json.loads(output.getvalue())
                self.assertEqual(code, 1, response)
                self.assertEqual(response["status"], "warning", response)
        self.assertEqual(business_bytes(self.workspace), before)

    def test_two_adds_for_one_gap_are_rejected_without_write(self):
        """同一补丁含同缺口的冲突候选时拒绝保存，不猜测优先级，也不建立重复问题。"""
        patch = self.fresh_patch()
        second = deepcopy(patch["operations"][0])
        second["ref"] = "$same_gap"
        second["value"]["priority"] = "P2"
        patch["operations"].append(second)
        before = business_bytes(self.workspace)
        result = self.apply(patch)
        self.assertEqual(result["status"], "fail", result)
        self.assertEqual(business_bytes(self.workspace), before)
        self.assertFalse(any("gap_request_ref" in q for q in self.analysis()["questions"]))

    def test_duplicate_with_other_changes_commits_once(self):
        """重复接收不阻止同补丁中的真实增量，也不额外消耗问题编号。"""
        first = self.accepted()
        patch = self.fresh_patch()
        value = deepcopy(ANALYST.initial()["operations"][1]["value"])
        value["related_ids"] = ["FR-1"]
        patch["operations"].append({"op": "add", "collection": "questions", "ref": "$ordinary", "value": value})
        result = self.accepted(patch)
        self.assertEqual(result["revision"], first["revision"] + 1)
        self.assertEqual(result["id_map"], {"$gap": "Q-2", "$ordinary": "Q-3"})
        self.assertTrue(result["written"])

    def test_duplicate_with_changed_set_is_not_noop(self):
        """只有分析内容不变才算纯重复，set 引入真实变化仍保存新修订。"""
        first = self.accepted()
        patch = self.fresh_patch()
        patch["set"] = {"ux_assessment.ui_dependent": True}
        result = self.accepted(patch)
        self.assertEqual(result["revision"], first["revision"] + 1)
        self.assertTrue(self.analysis()["ux_assessment"]["ui_dependent"])

    def test_stale_revision_is_rejected_even_for_duplicate(self):
        """旧补丁即使只是重复接收仍拒绝，调用方必须重读当前修订。"""
        stale = self.fresh_patch()
        self.accepted(stale)
        before = business_bytes(self.workspace)
        result = self.apply(stale)
        self.assertEqual(result["status"], "fail", result)
        self.assertFalse(result["written"])
        self.assertEqual(business_bytes(self.workspace), before)

    def test_closed_gap_is_not_reopened_or_rewritten(self):
        """重复接收 closed 缺口保留状态和生成侧 resolution，不自行关闭或重开。"""
        self.accepted()
        closed = PRD.read_json(self.gap_path)
        closed["requests"][0].update(status="closed", resolution={"kind": "supplied", "analysis_refs": [f"{REQUIREMENT}/FR-1"], "reason": "合成生成侧核实依据"})
        PRD.write_json(self.gap_path, closed)
        before = business_bytes(self.workspace)
        self.accepted()
        self.assertEqual(business_bytes(self.workspace), before)

    def test_analysis_save_failure_never_marks_gap(self):
        """分析实际替换失败时缺口仍 open，沿原 journal 恢复后重读重试不会重复登记。"""
        patch = self.fresh_patch()
        gap_before = self.gap_path.read_bytes()
        with inject_io_fault(self.updater, "analysis-save", self.directory) as fault:
            result = self.apply(patch)
        self.assertTrue(fault["triggered"])
        self.assertEqual(result["status"], "fail", result)
        self.assertFalse(result["written"])
        self.assertEqual(self.gap_path.read_bytes(), gap_before)
        self.assertEqual(len(self.analysis()["questions"]), 1)
        self.assertIsNotNone(PRD.read_json(self.workspace / ".analysis-transaction.json"))
        # 恢复会保存原补丁的 revision=2；旧 base_revision=1 仍须拒绝。
        recovered = self.apply(patch)
        self.assertEqual(recovered["status"], "fail", recovered)
        self.assertEqual(self.analysis()["meta"]["analysis_revision"], 2)
        self.assertEqual(self.gap_path.read_bytes(), gap_before)
        self.assertIsNone(PRD.read_json(self.workspace / ".analysis-transaction.json"))
        before_events = (self.directory / "analysis/analysis-events.jsonl").read_bytes()
        retried = self.accepted()
        self.assertEqual(retried["revision"], 2)
        self.assertEqual(self.received()["id"], "Q-2")
        self.assertEqual((self.directory / "analysis/analysis-events.jsonl").read_bytes(), before_events)

    def test_mark_failure_reports_saved_revision_and_retry_preserves_progress(self):
        """保存后标记中断返回 fail/written=true，重读重试只补标记并保留其间回答。"""
        gap_before = self.gap_path.read_bytes()
        with inject_io_fault(self.updater, "gap-mark", self.directory) as fault:
            result = self.apply(self.fresh_patch())
        self.assertTrue(fault["triggered"])
        self.assertEqual(result["status"], "fail", result)
        self.assertTrue(result["written"])
        self.assertEqual(result["revision"], 2)
        self.assertEqual(self.received()["id"], "Q-2")
        self.assertEqual(self.gap_path.read_bytes(), gap_before)
        progress = ANALYST.followup(current_result(self.directory))
        progress["operations"] = [{"op": "update", "target": "Q-2", "changes": {"status": "answered", "answer": "中断后已答复", "priority": "P1"}}]
        response = self.apply(progress)
        self.assertEqual(response["status"], "pass", response)
        saved_question = deepcopy(self.received())
        saved_analysis = business_bytes(self.directory / "analysis")
        retry = self.fresh_patch()
        retry["operations"][0]["value"].update(status="dropped", answer="不要覆盖", priority="P2")
        retried = self.accepted(retry)
        self.assertEqual(retried["revision"], 3)
        self.assertFalse(retried["written"])
        self.assertEqual(saved_analysis, business_bytes(self.directory / "analysis"))
        self.assertEqual(self.received(), saved_question)
        self.assertTrue(gap_status_only(self.gaps, PRD.read_json(self.gap_path)))

    def test_concurrent_gap_rewrite_is_not_overwritten(self):
        """分析保存期间生成侧改写缺口时拒绝标记，保留并发内容和已保存接收问题。"""
        with inject_io_fault(self.updater, "concurrent-gap", self.directory) as fault:
            result = self.apply(self.fresh_patch())
        self.assertTrue(fault["triggered"])
        self.assertEqual(result["status"], "fail", result)
        self.assertTrue(result["written"])
        self.assertEqual(result["revision"], 2)
        self.assertEqual(self.gap_path.read_bytes(), fault["concurrent_gap_bytes"])
        self.assertEqual(self.received()["id"], "Q-2")
        concurrent = PRD.read_json(self.gap_path)
        events = (self.directory / "analysis/analysis-events.jsonl").read_bytes()
        self.accepted()
        self.assertTrue(gap_status_only(concurrent, PRD.read_json(self.gap_path)))
        self.assertEqual((self.directory / "analysis/analysis-events.jsonl").read_bytes(), events)

    def test_concurrent_gap_whitespace_change_also_conflicts(self):
        """即使并发只改序列化空白，读时与标记前字节不等也必须拒绝覆盖。"""
        with inject_io_fault(self.updater, "concurrent-gap-bytes", self.directory) as fault:
            result = self.apply(self.fresh_patch())
        self.assertTrue(fault["triggered"])
        self.assertEqual(result["status"], "fail", result)
        self.assertTrue(result["written"])
        self.assertEqual(result["revision"], 2)
        self.assertEqual(PRD.read_json(self.gap_path), self.gaps)
        self.assertEqual(self.gap_path.read_bytes(), fault["concurrent_gap_bytes"])
        self.assertEqual(self.received()["id"], "Q-2")

    def test_dry_run_previews_without_writing(self):
        """无 pending 事务时 dry-run 只校验和预分配，不保存问题或标记缺口。"""
        before = business_bytes(self.workspace)
        preview = self.apply(self.fresh_patch(), dry_run=True)
        self.assertEqual(preview["status"], "pass", preview)
        self.assertFalse(preview["written"])
        self.assertEqual(preview["id_map"]["$gap"], "Q-2")
        self.assertEqual(business_bytes(self.workspace), before)
        saved = self.accepted()
        self.assertEqual(saved["id_map"], preview["id_map"])

    def test_dry_run_still_recovers_pending_analysis_transaction(self):
        """dry-run 不豁免原有 journal 恢复，但不提前完成本次缺口标记。"""
        patch = self.fresh_patch()
        with inject_io_fault(self.updater, "analysis-save", self.directory) as fault:
            failed = self.apply(patch)
        self.assertTrue(fault["triggered"])
        self.assertEqual(failed["status"], "fail", failed)
        gap_before = self.gap_path.read_bytes()
        result = self.apply(patch, dry_run=True)
        self.assertEqual(result["status"], "fail", result)
        self.assertEqual(self.analysis()["meta"]["analysis_revision"], 2)
        self.assertEqual(self.received()["id"], "Q-2")
        self.assertEqual(self.gap_path.read_bytes(), gap_before)
        self.assertIsNone(PRD.read_json(self.workspace / ".analysis-transaction.json"))
        before = business_bytes(self.workspace)
        preview = self.apply(self.fresh_patch(), dry_run=True)
        self.assertEqual(preview["status"], "pass", preview)
        self.assertFalse(preview["written"])
        self.assertEqual(business_bytes(self.workspace), before)

    def test_gap_reference_cannot_be_transferred_by_update(self):
        """已有接收关联不能通过 update 转移、清除或伪装成另一个缺口。"""
        self.accepted()
        for reference in ("GAPREQ-2", None, ""):
            with self.subTest(reference=reference):
                patch = ANALYST.followup(current_result(self.directory))
                patch["operations"] = [{"op": "update", "target": "Q-2", "changes": {"gap_request_ref": reference}}]
                before = business_bytes(self.workspace)
                result = self.apply(patch)
                self.assertEqual(result["status"], "fail", result)
                self.assertEqual(business_bytes(self.workspace), before)

    def test_handoff_only_changes_owned_files_and_target_status(self):
        """只改分析归属文件及对应缺口状态，其他需求、正文、追溯、版本和元数据不动。"""
        external = self.external()
        other = external.parent.parent / "prd"
        other.mkdir()
        (other / "gap-requests.json").write_text('{"sentinel":"其他需求缺口，不得访问"}\n', encoding="utf-8")
        before = business_bytes(self.workspace)
        self.accepted()
        after = business_bytes(self.workspace)
        base = self.directory.relative_to(self.workspace).as_posix()
        allowed = {f"{base}/analysis/analysis-result.json", f"{base}/analysis/source-manifest.json", f"{base}/analysis/analysis-events.jsonl", f"{base}/prd/gap-requests.json", "workspace.json", ".analysis-transaction.json"}
        changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
        self.assertLessEqual(changed, allowed)
        self.assertIn(f"{base}/analysis/analysis-result.json", changed)
        self.assertIn(f"{base}/prd/gap-requests.json", changed)
        self.assertTrue(gap_status_only(self.gaps, PRD.read_json(self.gap_path)))

    def test_old_questions_without_gap_ref_remain_compatible(self):
        """旧问题无 gap_request_ref 仍可读取和更新，新增接收不污染原问题或旧关联。"""
        old_question = deepcopy(self.analysis()["questions"][0])
        self.assertNotIn("gap_request_ref", old_question)
        self.accepted()
        self.assertEqual(self.analysis()["questions"][0], old_question)
        patch = ANALYST.followup(current_result(self.directory))
        patch["operations"] = [{"op": "update", "target": "Q-1", "changes": {"status": "answered", "answer": "旧问题正常答复"}}]
        result = self.apply(patch)
        self.assertEqual(result["status"], "pass", result)
        self.assertNotIn("gap_request_ref", self.analysis()["questions"][0])


if __name__ == "__main__":
    unittest.main()

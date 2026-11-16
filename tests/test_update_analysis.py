"""阶段 3 补丁写入契约回归；仅在临时工作区写入，不用合成数据冒充模型行为。"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill/requirement-analyst/scripts/update_analysis.py"
VALIDATOR_PATH = SCRIPT.with_name("validate_analysis.py")


def load_module(path: Path, name: str):
    """按 path 加载测试目标并返回模块；路径/导入错误直接抛出。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checks(question: str = "$question") -> list[dict]:
    """构造十一项未满足且关联 question 的机械清单；返回新列表，不读取业务原文。"""
    return [{"item": i, "satisfied": False, "question_refs": [question], "reason": "测试中尚待确认"} for i in range(1, 12)]


def common(content: str = "测试条目", *, tag: str = "inferred", refs: list | None = None) -> dict:
    """构造有用户回答来源的条目值；refs 可指定显式依赖，返回无正式编号的字典。"""
    value = {"content": content, "tag": tag, "status": "active", "sources": [{"type": "user_answer", "location": "合成测试输入"}]}
    if refs is not None:
        value["related_ids"] = refs
    return value


def initial(requirement_id=None) -> dict:
    """返回编号由脚本分配的最小首次补丁；requirement_id 可测试用户自带编号。"""
    return {
        "patch_version": "1.0", "requirement_id": requirement_id, "title": "合成测试，不是真实需求",
        "base_revision": 0, "change_type": "initial_analysis", "actor": "analyst", "summary": "测试首次分析",
        "operations": [
            {"op": "add", "collection": "requirements.goals", "ref": "$goal", "value": common("已确认目标", tag="confirmed")},
            {"op": "add", "collection": "questions", "ref": "$question", "value": {
                "question": "测试核心缺口？", "priority": "P0", "resolution": "ask_product", "reason": "尚不明确", "impact": "无法验收",
                "options": ["方案甲", "方案乙", "其他", "暂不确定"], "recommendation": "建议甲，先确认范围", "status": "open", "related_ids": ["$goal"]}},
        ],
        "set": {"meta.input_type": "existing_document", "meta.analysis_status": "clarifying", "meta.readiness": "not_ready", "ux_assessment.ui_dependent": False},
        "completion_checks": checks(),
    }


def followup(result: dict, *, change_type: str = "supplement") -> dict:
    """根据实际返回 result 构造下一修订空操作补丁；返回独立字典，调用者补充变化。"""
    return {"patch_version": "1.0", "requirement_id": result["requirement_id"], "base_revision": result["revision"],
            "change_type": change_type, "actor": "analyst", "summary": "继续分析", "operations": [], "set": {}, "completion_checks": checks("Q-1")}


def read_json(path: Path):
    """读取 path 并返回 JSON；文件、编码、格式错误直接抛出。"""
    return json.loads(path.read_text(encoding="utf-8"))


def business_bytes(workspace: Path) -> dict:
    """返回工作区业务文件原始字节；排除仅作互斥的锁文件，其他错误直接抛出。"""
    return {str(p.relative_to(workspace)): p.read_bytes() for p in workspace.rglob("*") if p.is_file() and p.name != ".analysis.lock"}


class UpdateAnalysisTests(unittest.TestCase):
    """验证编号、状态保护、只写归属文件、并发与事件持久化。"""

    @classmethod
    def setUpClass(cls) -> None:
        """加载实际脚本；缺实现时明确失败，不跳过契约测试。"""
        cls.updater = load_module(SCRIPT, "tested_updater")
        cls.validator = load_module(VALIDATOR_PATH, "updater_validator")

    def setUp(self) -> None:
        """每项测试使用独立临时目录，防止修改已提交的阶段 2 证据。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "workspace"

    def apply(self, patch: dict, **kwargs) -> dict:
        """将 patch 应用到临时项目，返回脚本实际结果；脚本异常让测试失败。"""
        return self.updater.update_analysis(self.workspace, "project-a", patch, **kwargs)

    def analysis_dir(self, result: dict) -> Path:
        """按实际 result 中的需求编号定位分析目录，不假设年份。"""
        return self.workspace / "projects/project-a/requirements" / result["requirement_id"] / "analysis"

    def create(self, patch: dict | None = None) -> tuple[dict, dict]:
        """应用首次 patch 并断言成功，返回脚本响应和实际保存结果。"""
        response = self.apply(initial() if patch is None else patch)
        self.assertEqual(response["status"], "pass", response)
        return response, read_json(self.analysis_dir(response) / "analysis-result.json")

    def test_initial_allocates_requirement_and_item_ids(self) -> None:
        """首次创建工作区、common 和编号；结果与来源通过唯一校验器。"""
        patch = initial()
        untouched = deepcopy(patch)
        result, analysis = self.create(patch)
        self.assertEqual(patch, untouched)
        self.assertRegex(result["requirement_id"], r"^REQ-\d{4}-001$")
        self.assertEqual(result["id_map"]["$goal"], "GOAL-1")
        self.assertEqual(result["id_map"]["$question"], "Q-1")
        self.assertEqual(analysis["questions"][0]["related_ids"], ["GOAL-1"])
        self.assertEqual(analysis["meta"]["analysis_revision"], 1)
        self.assertEqual(analysis["meta"]["source_revision"], 1)
        self.assertEqual(self.validator.validate_analysis(analysis, read_json(self.analysis_dir(result) / "source-manifest.json"))["status"], "pass")
        record = read_json(self.analysis_dir(result).parent / "requirement.json")
        self.assertEqual(record["common"]["project_id"], "project-a")
        self.assertRegex(record["common"]["created_at"], r"^\d{4}-\d{2}-\d{2}T.*(?:Z|\+00:00)$")
        self.assertNotIn("analysis_revision", record["common"])
        self.assertTrue(read_json(self.workspace / "workspace.json")["projects"])

    def test_forward_alias_source_and_literal_are_distinct(self) -> None:
        """引用可前向解析，正文中的 $source 保持原文，不进行全字符串替换。"""
        patch = initial()
        patch["operations"][0]["value"]["content"] = "正文 $source 不是引用"
        patch["operations"][0]["value"]["sources"] = [{"type": "input_document", "source_id": "$source", "location": "第1行"}]
        patch["operations"].append({"op": "add_source", "ref": "$source", "value": {
            "name": "原文", "path": "inputs/original.md", "type": "input_document", "credibility": "用户提供", "last_updated": None, "revision": 1}})
        result, analysis = self.create(patch)
        self.assertEqual(analysis["requirements"]["goals"][0]["content"], "正文 $source 不是引用")
        self.assertEqual(analysis["requirements"]["goals"][0]["sources"][0]["source_id"], "SRC-1")
        self.assertEqual(result["id_map"]["$source"], "SRC-1")

    def test_three_updates_append_events_and_preserve_unknown_fields(self) -> None:
        """连续三轮补丁每轮 pass，未涉及条目及扩展字段不漂移，事件保留旧字节。"""
        patch = initial("CUSTOM-42")
        patch["operations"][0]["value"]["extension"] = {"keep": [1, 2]}
        result, analysis = self.create(patch)
        original_goal = deepcopy(analysis["requirements"]["goals"][0])
        directory = self.analysis_dir(result)
        old_bytes = (directory / "analysis-events.jsonl").read_bytes()
        for n in range(3):
            patch = followup(result)
            patch["operations"] = [{"op": "add", "collection": "business_assessment.boundaries", "ref": "$boundary", "value": common(f"边界{n}")}]
            result = self.apply(patch)
            self.assertEqual(result["status"], "pass", result)
            current = (directory / "analysis-events.jsonl").read_bytes()
            self.assertTrue(current.startswith(old_bytes))
            old_bytes = current
        analysis = read_json(directory / "analysis-result.json")
        self.assertEqual(analysis["meta"]["analysis_revision"], 4)
        self.assertEqual(analysis["requirements"]["goals"][0], original_goal)
        events = [json.loads(line) for line in old_bytes.splitlines()]
        self.assertEqual([e["revision"] for e in events], [1, 2, 3, 4])
        for event in events:
            self.assertTrue({"time", "revision", "change_type", "summary", "affected_ids", "actor"} <= event.keys())

    def test_invalid_patch_and_conflict_do_not_write(self) -> None:
        """非法状态和旧 revision 都拒绝，结果/事件/来源/计数字节不变。"""
        result, _ = self.create()
        before = business_bytes(self.workspace)
        bad = followup(result)
        bad["set"] = {"meta.readiness": "ready_for_document"}
        self.assertEqual(self.apply(bad)["status"], "fail")
        self.assertEqual(business_bytes(self.workspace), before)
        bad = followup(result)
        bad["base_revision"] = 0
        self.assertEqual(self.apply(bad)["status"], "fail")
        self.assertEqual(business_bytes(self.workspace), before)

    def test_invalid_initial_creates_no_business_result(self) -> None:
        """首次失败不创建需求/common/来源/事件，也不占用需求序号。"""
        patch = initial()
        patch["operations"][1]["value"]["priority"] = "P9"
        self.assertEqual(self.apply(patch)["status"], "fail")
        self.assertEqual(business_bytes(self.workspace), {})
        result, _ = self.create()
        self.assertTrue(result["requirement_id"].endswith("-001"))

    def test_dry_run_does_not_consume_ids_or_revision(self) -> None:
        """预检显示编号映射但无业务写入，正式保存仍从相同起点编号。"""
        response = self.apply(initial(), dry_run=True)
        self.assertEqual(response["status"], "pass", response)
        self.assertFalse(response["written"])
        self.assertEqual(business_bytes(self.workspace), {})
        result, _ = self.create()
        self.assertEqual(result["requirement_id"], response["requirement_id"])

    def test_user_id_and_global_counter(self) -> None:
        """用户标准编号占序号，项目之间共享当年计数；自定义编号不强制重命名。"""
        result, _ = self.create()
        year = result["requirement_id"].split("-")[1]
        self.create(initial(f"REQ-{year}-040"))
        result = self.updater.update_analysis(self.workspace, "project-b", initial())
        self.assertEqual(result["requirement_id"], f"REQ-{year}-041")
        custom, _ = self.create(initial("TASK-X"))
        self.assertEqual(custom["requirement_id"], "TASK-X")

    def test_invalid_followup_does_not_consume_source_or_item_numbers(self) -> None:
        """被拒的新增来源和条目只存在于内存，下次合法补丁仍分配同一编号。"""
        result, _ = self.create()
        patch = followup(result)
        patch["operations"] = [
            {"op": "add_source", "ref": "$source", "value": {"name": "新增资料", "path": "inputs/extra.md", "type": "input_document", "credibility": "测试", "last_updated": None, "revision": 1}},
            {"op": "add", "collection": "requirements.business_rules", "ref": "$rule", "value": common("新增规则")},
        ]
        patch["set"] = {"meta.readiness": "ready_for_document"}
        before = business_bytes(self.workspace)
        self.assertEqual(self.apply(patch)["status"], "fail")
        self.assertEqual(business_bytes(self.workspace), before)
        patch["set"] = {}
        response = self.apply(patch)
        self.assertEqual(response["status"], "pass", response)
        self.assertEqual(response["id_map"], {"$source": "SRC-1", "$rule": "BR-1"})
        self.assertEqual(read_json(self.analysis_dir(result) / "analysis-result.json")["meta"]["source_revision"], 2)

    def test_confirmed_content_requires_explicit_user_evidence(self) -> None:
        """推断不能覆盖 confirmed；明示更正保留原始事件并更新证据。"""
        result, _ = self.create()
        patch = followup(result, change_type="correction")
        patch["operations"] = [{"op": "update", "target": "GOAL-1", "changes": {"content": "更正后的目标", "tag": "inferred"}}]
        before = business_bytes(self.workspace)
        self.assertEqual(self.apply(patch)["status"], "fail")
        self.assertEqual(business_bytes(self.workspace), before)
        patch.update(actor="user", user_statement="目标明确改成更正后的目标")
        patch["operations"][0]["changes"].update(tag="confirmed", sources=[{"type": "user_answer", "location": "更正原话"}])
        updated = self.apply(patch)
        self.assertEqual(updated["status"], "pass", updated)
        event_text = (self.analysis_dir(result) / "analysis-events.jsonl").read_text(encoding="utf-8")
        self.assertIn("已确认目标", event_text)
        self.assertIn("更正后的目标", event_text)
        self.assertIn("目标明确改成更正后的目标", event_text)

    def test_explicit_correction_can_answer_without_spurious_reopening(self) -> None:
        """用户已经明确新答案的更正可直接登记 answered，新版文档才强制先重开。"""
        result, _ = self.create()
        patch = followup(result)
        patch["operations"] = [{"op": "update", "target": "Q-1", "changes": {"status": "answered", "answer": "旧答案"}}]
        result = self.apply(patch)
        self.assertEqual(result["status"], "pass", result)
        patch = followup(result, change_type="correction")
        patch.update(actor="user", user_statement="目标改成新目标，这就是新的明确答案")
        patch["operations"] = [
            {"op": "update", "target": "GOAL-1", "changes": {"content": "新的明确目标", "sources": [{"type": "user_answer", "location": "本轮明确更正"}]}},
            {"op": "update", "target": "Q-1", "changes": {"status": "answered", "answer": "本轮明确更正"}},
        ]
        response = self.apply(patch)
        self.assertEqual(response["status"], "pass", response)

    def test_new_version_reopens_closed_question_and_preserves_answer(self) -> None:
        """新版变化关联已关闭问题，缺少重开被拒；重开保留旧 answer 并说明原因。"""
        result, _ = self.create()
        patch = followup(result)
        patch["operations"] = [{"op": "update", "target": "Q-1", "changes": {"status": "answered", "answer": "旧版本确认"}}]
        result = self.apply(patch)
        patch = followup(result, change_type="new_source_version")
        patch["operations"] = [
            {"op": "add_source", "ref": "$v2", "value": {"name": "新版", "path": "inputs/v2.md", "type": "input_document", "credibility": "用户提供", "last_updated": None, "revision": 2}},
            {"op": "update", "target": "GOAL-1", "changes": {"status": "to_reassess"}},
        ]
        before = business_bytes(self.workspace)
        self.assertEqual(self.apply(patch)["status"], "fail")
        self.assertEqual(business_bytes(self.workspace), before)
        patch["operations"].append({"op": "update", "target": "Q-1", "changes": {"status": "open", "reason": "新版改变相关依据，需要重新评估"}})
        response = self.apply(patch)
        self.assertEqual(response["status"], "warning", response)
        analysis = read_json(self.analysis_dir(result) / "analysis-result.json")
        self.assertEqual(analysis["questions"][0]["answer"], "旧版本确认")
        self.assertEqual(analysis["questions"][0]["status"], "open")

    def test_withdraw_cascades_and_never_reuses_ids(self) -> None:
        """撤销保留原对象，问题废弃、验收待重评，新条目不复用撤销编号。"""
        patch = initial()
        patch["operations"].append({"op": "add", "collection": "requirements.acceptance_criteria", "ref": "$ac", "value": common("相关验收", refs=["$goal"])})
        result, _ = self.create(patch)
        patch = followup(result, change_type="withdrawal")
        patch.update(actor="user", user_statement="取消原目标，但另一个核心目标还需明确")
        patch["operations"] = [
            {"op": "withdraw", "target": "GOAL-1", "reason": "用户取消"},
            {"op": "add", "collection": "questions", "ref": "$newq", "value": deepcopy(initial()["operations"][1]["value"])},
            {"op": "add", "collection": "requirements.goals", "ref": "$newgoal", "value": common("另一个目标")},
        ]
        patch["operations"][1]["value"]["related_ids"] = ["$newgoal"]
        patch["completion_checks"] = checks("$newq")
        response = self.apply(patch)
        self.assertEqual(response["status"], "pass", response)
        analysis = read_json(self.analysis_dir(result) / "analysis-result.json")
        self.assertEqual(analysis["requirements"]["goals"][0]["status"], "withdrawn")
        self.assertEqual(analysis["questions"][0]["status"], "dropped")
        self.assertEqual(analysis["requirements"]["acceptance_criteria"][0]["status"], "to_reassess")
        self.assertEqual(response["id_map"]["$newgoal"], "GOAL-2")
        self.assertTrue({"GOAL-1", "Q-1", "AC-1"} <= set(response["affected_ids"]))

    def test_withdraw_does_not_spread_through_shared_ancestors(self) -> None:
        """撤销传播沿依赖方向，不能经共享目标误伤未变的兄弟功能及其问题。"""
        patch = initial()
        question = deepcopy(patch["operations"][1]["value"])
        question["related_ids"] = ["$first"]
        patch["operations"] += [
            {"op": "add", "collection": "requirements.functional_requirements", "ref": "$first", "value": common("撤销的功能", refs=["$goal"])},
            {"op": "add", "collection": "requirements.functional_requirements", "ref": "$second", "value": common("不变的功能", refs=["$goal"])},
            {"op": "add", "collection": "requirements.acceptance_criteria", "ref": "$ac", "value": common("共享验收", refs=["$first", "$second"])},
            {"op": "add", "collection": "questions", "ref": "$withdrawq", "value": question},
        ]
        result, before = self.create(patch)
        patch = followup(result, change_type="withdrawal")
        patch.update(actor="user", user_statement="只取消第一个功能，其余保持")
        patch["operations"] = [{"op": "withdraw", "target": "FR-1", "reason": "用户明确取消第一个功能"}]
        response = self.apply(patch)
        self.assertEqual(response["status"], "pass", response)
        after = read_json(self.analysis_dir(result) / "analysis-result.json")
        self.assertEqual(after["requirements"]["goals"], before["requirements"]["goals"])
        self.assertEqual(after["requirements"]["functional_requirements"][1], before["requirements"]["functional_requirements"][1])
        self.assertEqual(after["questions"][0], before["questions"][0])
        self.assertEqual(after["questions"][1]["status"], "dropped")
        self.assertEqual(after["requirements"]["acceptance_criteria"][0]["status"], "to_reassess")

    def test_new_source_version_warns_and_old_source_remains(self) -> None:
        """新版保留旧来源，source_revision 加一；stale 可持久化但返回 warning。"""
        patch = initial()
        source = {"name": "文档v1", "path": "inputs/v1.md", "type": "input_document", "credibility": "用户提供", "last_updated": None, "revision": 1}
        patch["operations"].append({"op": "add_source", "ref": "$v1", "value": source})
        result, _ = self.create(patch)
        patch = followup(result, change_type="new_source_version")
        patch["set"] = {"meta.analysis_status": "stale"}
        patch["operations"] = [{"op": "add_source", "ref": "$v2", "value": {**source, "name": "文档v2", "path": "inputs/v2.md", "revision": 2}}]
        response = self.apply(patch)
        self.assertEqual(response["status"], "warning", response)
        self.assertTrue(response["written"])
        directory = self.analysis_dir(result)
        self.assertEqual([s["source_id"] for s in read_json(directory / "source-manifest.json")], ["SRC-1", "SRC-2"])
        self.assertEqual(read_json(directory / "analysis-result.json")["meta"]["source_revision"], 2)

    def test_no_overwrite_of_common_prd_inputs_or_workspace_extensions(self) -> None:
        """更新不覆盖用户标题、prd块、输入或工作区扩展字段。"""
        result, _ = self.create()
        directory = self.analysis_dir(result).parent
        record = read_json(directory / "requirement.json")
        record["common"]["title"] = "用户修改的标题"
        record["prd"] = {"version": "v1", "status": "draft", "based_on_analysis_revision": 1}
        (directory / "requirement.json").write_text(json.dumps(record), encoding="utf-8")
        (directory / "inputs").mkdir(exist_ok=True)
        (directory / "inputs/original.md").write_text("用户所有", encoding="utf-8")
        workspace = read_json(self.workspace / "workspace.json")
        workspace["extension"] = {"keep": True}
        (self.workspace / "workspace.json").write_text(json.dumps(workspace), encoding="utf-8")
        before_common = (directory / "requirement.json").read_bytes()
        response = self.apply(followup(result))
        self.assertEqual(response["status"], "pass", response)
        self.assertEqual((directory / "requirement.json").read_bytes(), before_common)
        self.assertEqual((directory / "inputs/original.md").read_text(encoding="utf-8"), "用户所有")
        self.assertEqual(read_json(self.workspace / "workspace.json")["extension"], {"keep": True})

    def test_rejects_whole_result_id_changes_and_unknown_operations(self) -> None:
        """不存在整份替换、物理删除或模型指定新编号的旁路。"""
        for mutate in (
            lambda p: p.update(analysis={}),
            lambda p: p["set"].update({"requirements.goals": []}),
            lambda p: p["set"].update({"meta.analysis_revision": 99}),
            lambda p: p["operations"][0]["value"].update(id="GOAL-99"),
            lambda p: p["operations"].append({"op": "delete", "target": "GOAL-1"}),
            lambda p: p["operations"].append(deepcopy(p["operations"][0])),
            lambda p: p["operations"][1]["value"].update(related_ids=["$missing"]),
            lambda p: p.update(base_revision=True),
        ):
            with self.subTest(mutate=mutate):
                patch = initial()
                mutate(patch)
                self.assertEqual(self.apply(patch)["status"], "fail")
                self.assertEqual(business_bytes(self.workspace), {})

    def test_path_escape_is_rejected(self) -> None:
        """编号不能作为路径穿越，受管理路径的符号链接也不能写到工作区外。"""
        for requirement_id in ("..", ".", "../outside", "/absolute", "a\\b"):
            with self.subTest(requirement_id=requirement_id):
                self.assertEqual(self.apply(initial(requirement_id))["status"], "fail")
        self.workspace.mkdir(exist_ok=True)
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.workspace / "projects").symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.apply(initial())["status"], "fail")
        self.assertEqual(list(outside.iterdir()), [])

    def test_interrupted_commit_recovers_once_before_revision_check(self) -> None:
        """单文件替换中断留下事务，下次先恢复整笔再拒绝旧修订，事件不重复。"""
        real_replace = self.updater.os.replace
        injected = False

        def fail_result_once(source, target, *args, **kwargs):
            """只在正式结果的首次替换注入故障，模拟校验后落盘中断。"""
            nonlocal injected
            if Path(target).name == "analysis-result.json" and not injected:
                injected = True
                raise OSError("测试注入：结果替换中断")
            return real_replace(source, target, *args, **kwargs)

        patch = initial("RECOVERY-CASE")
        with mock.patch.object(self.updater.os, "replace", side_effect=fail_result_once):
            response = self.apply(patch)
        self.assertTrue(injected)
        self.assertEqual(response["status"], "fail", response)
        response = self.apply(patch)
        self.assertEqual(response["status"], "fail", response)
        directory = self.workspace / "projects/project-a/requirements/RECOVERY-CASE/analysis"
        analysis = read_json(directory / "analysis-result.json")
        self.assertEqual(analysis["meta"]["analysis_revision"], 1)
        self.assertEqual(len((directory / "analysis-events.jsonl").read_text(encoding="utf-8").splitlines()), 1)
        self.assertEqual(self.validator.validate_analysis(analysis, read_json(directory / "source-manifest.json"))["status"], "pass")
        response = self.apply(followup({"requirement_id": "RECOVERY-CASE", "revision": 1}))
        self.assertEqual(response["status"], "pass", response)

    def test_partial_event_recovery_does_not_duplicate_auto_numbered_requirement(self) -> None:
        """首次自动编号中断且只写半条事件，恢复续写同一事件，不再创建第二个需求。"""
        real_recover = self.updater._recover
        injected = False

        def interrupt_append(root):
            """写前记录存在时模拟业务文件已换新、事件只写半行的断电状态。"""
            nonlocal injected
            journal = root / ".analysis-transaction.json"
            record = read_json(journal) if journal.exists() else None
            if record is None or injected:
                return real_recover(root)
            injected = True
            for entry in record["writes"]:
                target = root / entry["path"]
                after = self.updater._unpack(entry["after"])
                if target.name == "analysis-events.jsonl":
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(after[:len(after) // 2])
                else:
                    self.updater._atomic_write(target, after)
            raise OSError("测试注入：事件只追加半行")

        patch = initial()
        with mock.patch.object(self.updater, "_recover", side_effect=interrupt_append):
            failed = self.apply(patch)
        self.assertTrue(injected)
        self.assertEqual(failed["status"], "fail")
        recovered = self.apply(patch)
        self.assertEqual(recovered["status"], "fail")
        self.assertTrue(recovered["requirement_id"].endswith("-001"), recovered)
        directories = list((self.workspace / "projects/project-a/requirements").iterdir())
        self.assertEqual(len(directories), 1)
        directory = directories[0] / "analysis"
        events = [json.loads(line) for line in (directory / "analysis-events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([e["revision"] for e in events], [1])
        self.assertIsNone(read_json(self.workspace / ".analysis-transaction.json"))
        response = self.apply(followup({"requirement_id": recovered["requirement_id"], "revision": 1}))
        self.assertEqual(response["status"], "pass", response)

    def test_scope_prefix_and_reference_explicitness(self) -> None:
        """scope 按实际类别编号，未显式提供的跨需求不能仅凭格式通过。"""
        patch = initial()
        patch["operations"].append({"op": "add", "collection": "requirements.scope.in_scope", "prefix": "FR", "ref": "$scope", "value": common("本期范围")})
        result, analysis = self.create(patch)
        self.assertEqual(result["id_map"]["$scope"], "FR-1")
        self.assertEqual(analysis["requirements"]["scope"]["out_of_scope"], [])
        patch = followup(result)
        patch["operations"] = [{"op": "add", "collection": "requirements.business_rules", "ref": "$cross", "value": common("跨需求依赖", refs=["MISSING/BR-1"])}]
        before = business_bytes(self.workspace)
        self.assertEqual(self.apply(patch)["status"], "fail")
        self.assertEqual(business_bytes(self.workspace), before)

    def test_withdrawal_without_statement_or_status_bypass_fails(self) -> None:
        """撤销须明示且只能走 withdraw，不能利用 update 或恢复旧编号绕过。"""
        result, _ = self.create()
        for operation in (
            {"op": "withdraw", "target": "GOAL-1", "reason": "没有用户原话"},
            {"op": "update", "target": "GOAL-1", "changes": {"status": "withdrawn"}},
            {"op": "update", "target": "GOAL-1", "changes": {"id": "GOAL-99"}},
        ):
            patch = followup(result)
            patch["operations"] = [operation]
            before = business_bytes(self.workspace)
            self.assertEqual(self.apply(patch)["status"], "fail")
            self.assertEqual(business_bytes(self.workspace), before)

    def test_cli_isolated_outside_repository_and_rejects_bad_json(self) -> None:
        """CLI 在非仓库 cwd 与隔离模式运行，坏 JSON 给结构化失败而非 traceback。"""
        patch_file = Path(self.temp.name) / "patch.json"
        command = [sys.executable, "-I", "-B", str(SCRIPT), "--workspace", str(self.workspace), "--project", "project-a", "--patch", str(patch_file)]
        patch_file.write_text(json.dumps(initial()), encoding="utf-8")
        response = subprocess.run(command, cwd=self.temp.name, capture_output=True, text=True, check=False)
        self.assertEqual(response.returncode, 0, response.stderr + response.stdout)
        self.assertTrue(json.loads(response.stdout)["written"])
        for bad in ('{"patch_version":"1.0","patch_version":"2.0"}', '{"base_revision":NaN}', "{"):
            with self.subTest(bad=bad):
                patch_file.write_text(bad, encoding="utf-8")
                response = subprocess.run(command, cwd=self.temp.name, capture_output=True, text=True, check=False)
                self.assertEqual(response.returncode, 2, response.stderr)
                self.assertEqual(json.loads(response.stdout)["status"], "fail")

    def test_concurrent_same_revision_only_one_writer_wins(self) -> None:
        """两个进程提交同一 base_revision，独占锁内只允许一个成功。"""
        result, _ = self.create()
        patch_file = Path(self.temp.name) / "concurrent.json"
        patch_file.write_text(json.dumps(followup(result)), encoding="utf-8")
        command = [sys.executable, "-I", "-B", str(SCRIPT), "--workspace", str(self.workspace), "--project", "project-a", "--patch", str(patch_file)]
        workers = [subprocess.Popen(command, cwd=self.temp.name, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        responses = [w.communicate(timeout=60) for w in workers]
        self.assertEqual(sorted(w.returncode for w in workers), [0, 2], responses)
        events = (self.analysis_dir(result) / "analysis-events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(events), 2)
        self.assertEqual(read_json(self.analysis_dir(result) / "analysis-result.json")["meta"]["analysis_revision"], 2)


class CompletionCheckTests(unittest.TestCase):
    """声明式清单可被机械检查，但不替代业务是否满足的实际判断。"""

    @classmethod
    def setUpClass(cls) -> None:
        """加载只读校验器和旧黄金样例；缺文件时直接失败。"""
        cls.validator = load_module(VALIDATOR_PATH, "checks_validator")
        cls.golden = read_json(ROOT / "tests/fixtures/high-low-voltage/analysis-result.json")
        cls.manifest = read_json(ROOT / "tests/fixtures/high-low-voltage/source-manifest.json")

    def test_old_result_without_checklist_remains_valid(self) -> None:
        """新增清单字段不破坏既有 schema_version=1.0 的旧结果。"""
        self.assertEqual(self.validator.validate_analysis(self.golden, self.manifest)["status"], "pass")

    def test_checklist_requires_complete_unique_numbers_and_questions(self) -> None:
        """清单不完整、重复编号或缺口没有问题关联时必须失败。"""
        for values in (checks("Q-1")[:-1], checks("Q-1") + [checks("Q-1")[0]], [{**v, "question_refs": []} for v in checks("Q-1")]):
            with self.subTest(values=values):
                analysis = deepcopy(self.golden)
                analysis["completion_checks"] = values
                self.assertEqual(self.validator.validate_analysis(analysis, self.manifest)["status"], "fail")

    def test_noncore_missing_requires_p1_and_caps_readiness(self) -> None:
        """非核心未满足项至少关联P1且最多条件就绪，不能用P2或已就绪掩盖。"""
        analysis = deepcopy(self.golden)
        for q in analysis["questions"]:
            q.update(status="answered", answer="仅测试完成清单关系")
        analysis["questions"][0]["priority"] = "P1"
        analysis["completion_checks"] = [{"item": i, "satisfied": i != 11, "question_refs": ["Q-1"] if i == 11 else [], "reason": "测试声明"} for i in range(1, 12)]
        analysis["meta"]["readiness"] = "conditionally_ready"
        self.assertEqual(self.validator.validate_analysis(analysis, self.manifest)["status"], "pass")
        analysis["meta"]["readiness"] = "ready_for_document"
        self.assertEqual(self.validator.validate_analysis(analysis, self.manifest)["status"], "fail")
        analysis["meta"]["readiness"] = "conditionally_ready"
        analysis["questions"][0]["priority"] = "P2"
        self.assertEqual(self.validator.validate_analysis(analysis, self.manifest)["status"], "fail")

    def test_core_missing_cannot_become_ready_even_if_question_closed(self) -> None:
        """关闭问题不等于清单满足；未满足核心项独立阻止文档就绪。"""
        analysis = deepcopy(self.golden)
        analysis["completion_checks"] = checks("Q-1")
        for question in analysis["questions"]:
            question["status"] = "answered"
            question["answer"] = "只是关闭，不代表核心已可表达"
        analysis["meta"]["readiness"] = "ready_for_document"
        self.assertEqual(self.validator.validate_analysis(analysis, self.manifest)["status"], "fail")


if __name__ == "__main__":
    unittest.main(verbosity=2)

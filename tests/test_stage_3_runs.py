"""核对阶段 3 保存的真实模型补丁和脚本写入证据；重跑不会调用模型。"""

from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "workspace-sandbox/stage-3"


def load(path: Path):
    """读取 path 的 JSON；缺失或格式错误直接失败，不能跳过未发生的试跑。"""
    return json.loads(path.read_text(encoding="utf-8"))


def entries(analysis: dict) -> list[dict]:
    """按规范收集 analysis 通用条目及问题；返回列表，不把扩展字段当容器。"""
    values = []
    for section, fields in (("requirements", ("goals", "scenarios", "functional_requirements", "business_rules", "constraints", "non_functional_requirements", "acceptance_criteria")), ("business_assessment", ("flows", "states", "boundaries", "exceptions", "gaps", "conflicts"))):
        values += [item for field in fields for item in analysis[section].get(field, [])]
    values += analysis["questions"] + analysis["assumptions"] + analysis["decisions"]
    return values


class StageThreeModelRuns(unittest.TestCase):
    """源版本、实际提问、增量语义和持久化分别核对，不用模型自评代替。"""

    @classmethod
    def setUpClass(cls) -> None:
        """加载真实记录和统一校验器；证据不存在则明确失败。"""
        cls.manifest = load(RUNS / "run-manifest.json")
        cls.turns = load(RUNS / "turns.json")
        spec = importlib.util.spec_from_file_location("stage_three_validator", ROOT / "skill/requirement-analyst/scripts/validate_analysis.py")
        cls.validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.validator)

    def documents(self, project: str) -> dict:
        """返回 project 当前全部正式结果；对应文件缺失或格式错误直接抛出。"""
        return {a["requirement_id"]: (a, path) for path in sorted((RUNS / "workspace/projects" / project / "requirements").glob("*/analysis/analysis-result.json")) for a in [load(path)]}

    def turn(self, group: str, name: str) -> dict:
        """定位唯一 group/name 实际对话；缺失或重复由断言报告。"""
        matches = [t for t in self.turns if t["group"] == group and t["name"] == name]
        self.assertEqual(len(matches), 1, (group, name))
        return matches[0]

    def test_current_sources_match_actual_run(self) -> None:
        """当前 Skill、脚本、Schema 和输入必须与本次实跑源指纹相符。"""
        self.assertEqual(self.manifest["stage"], 3)
        self.assertGreaterEqual(len(self.manifest["files"]), 19)
        for relative, expected in self.manifest["files"].items():
            with self.subTest(file=relative):
                self.assertNotIn("__pycache__", Path(relative).parts)
                self.assertNotEqual(Path(relative).suffix, ".pyc")
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected)

    def test_rule_evolution_is_scoped_and_keeps_original_evidence(self) -> None:
        """新规则的定点重评保留旧源码与实际修复，不能只重写哈希伪装全量盲跑。"""
        for change in self.manifest["source_evolution"]:
            current = (ROOT / change["file"]).read_text(encoding="utf-8")
            snapshot = (RUNS / change["before_snapshot"]).read_text(encoding="utf-8")
            self.assertEqual(snapshot.count(change["old_text"]), 1)
            self.assertEqual(snapshot.replace(change["old_text"], change["new_text"], 1), current)
            if change["kind"] == "scoped_behavior_recheck":
                for record in change["records"]:
                    self.assertEqual(load(RUNS / record / "response.json")["status"], "pass")
        self.assertEqual(self.manifest["model_execution"], "explicit_source_load_not_installed_trigger")

    def test_all_formal_results_use_patches_and_have_eleven_checks(self) -> None:
        """两业务样例及五探针均经真实脚本保存，最终全部 pass 且有报告。"""
        counts = {"high-low-voltage": 1, "task-management": 5, "probes": 5}
        for project, expected in counts.items():
            docs = self.documents(project)
            self.assertEqual(len(docs), expected)
            for analysis, path in docs.values():
                with self.subTest(path=path):
                    validation = self.validator.validate_analysis(analysis, load(path.with_name("source-manifest.json")), related_analyses=[(a, load(p.with_name("source-manifest.json"))) for a, p in docs.values() if p != path])
                    self.assertEqual(validation["status"], "pass", validation)
                    self.assertEqual({c["item"] for c in analysis["completion_checks"]}, set(range(1, 12)))
                    self.assertTrue(path.with_name("analysis-report.md").is_file())
                    events = [json.loads(line) for line in path.with_name("analysis-events.jsonl").read_text(encoding="utf-8").splitlines()]
                    self.assertEqual([e["revision"] for e in events], list(range(1, analysis["meta"]["analysis_revision"] + 1)))
                    self.assertEqual(events[0]["change_type"], "initial_analysis")
        for record in self.manifest["records"]:
            directory = RUNS / record
            raw = (directory / "patch.json").read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), load(directory / "provenance.json")["patch_sha256"])
            response = load(directory / "response.json")
            if response["status"] != "fail":
                self.assertTrue(response["written"])
                analysis = load(directory / "analysis/analysis-result.json")
                self.assertEqual(response["revision"], analysis["meta"]["analysis_revision"])

    def test_current_writer_replays_all_model_patches_without_drift(self) -> None:
        """按原顺序在临时工作区重放真实补丁，当前脚本输出须与每次保存快照一致。"""
        spec = importlib.util.spec_from_file_location("replay_updater", ROOT / "skill/requirement-analyst/scripts/update_analysis.py")
        updater = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(updater)
        fixed_time = datetime.fromisoformat(self.manifest["replay_time"])

        class RecordedClock(datetime):
            """固定试跑年份，避免将来跨年导致自动需求编号不同。"""

            @classmethod
            def now(cls, tz=None):
                """返回记录时刻；tz 指定转换时区，不影响业务分析。"""
                return fixed_time.astimezone(tz) if tz is not None else fixed_time.replace(tzinfo=None)

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(updater, "datetime", RecordedClock):
            workspace = Path(temporary) / "workspace"
            for record in self.manifest["records"]:
                directory = RUNS / record
                project = directory.parent.name
                original = load(directory / "response.json")
                response = updater.update_analysis(workspace, project, load(directory / "patch.json"))
                self.assertEqual(response["status"], original["status"], (record, response))
                self.assertEqual(response["written"], original["written"], record)
                if not response["written"]:
                    continue
                self.assertEqual(response["id_map"], original["id_map"], record)
                self.assertEqual(response["affected_ids"], original["affected_ids"], record)
                saved = workspace / "projects" / project / "requirements" / response["requirement_id"] / "analysis"
                self.assertEqual(load(saved / "analysis-result.json"), load(directory / "analysis/analysis-result.json"), record)
                self.assertEqual(load(saved / "source-manifest.json"), load(directory / "analysis/source-manifest.json"), record)

    def test_stage_two_initial_questions_and_conflicts_regress(self) -> None:
        """本次首次仍拆五项、优先操作规则，且原文矛盾未被后续答案提前关闭。"""
        turn = self.turn("task-management", "initial")
        self.assertEqual(len(turn["asked_refs"]), 3)
        asked = turn["asked_questions"]
        for pattern in (r"权限|谁|哪些.*(?:人|用户)|角色", r"之前|旧.*规则|运行中", r"1000|上限|超.*条|导出.*数量"):
            self.assertTrue(any(re.search(pattern, q["question"]) for q in asked), asked)
        conflicts = []
        for record in turn["records"]:
            analysis = load(RUNS / record / "analysis/analysis-result.json")
            conflicts += analysis["business_assessment"]["conflicts"]
            self.assertEqual(analysis["meta"]["readiness"], "not_ready")
            questions = {q["id"]: q for q in analysis["questions"]}
            for conflict in analysis["business_assessment"]["conflicts"]:
                self.assertEqual(questions[conflict["related_question"]]["status"], "open")
        self.assertGreaterEqual(len(conflicts), 2)

    def test_no_reasking_after_answer_or_uncertainty(self) -> None:
        """当前补丁机制保留上下文，不重复问已回答的权限/旧规则或暂定数量。"""
        first = self.turn("task-management", "initial")
        second = self.turn("task-management", "answers")
        # 部分回答可沿用原编号追问剩余内容；不能把同编号直接等同于重复提问。
        first_questions = dict(zip(first["asked_refs"], first["asked_questions"]))
        second_questions = dict(zip(second["asked_refs"], second["asked_questions"]))
        for reference in set(first_questions) & set(second_questions):
            self.assertNotEqual(first_questions[reference]["question"], second_questions[reference]["question"])
            self.assertTrue(second_questions[reference].get("answer"))
            self.assertRegex(second_questions[reference]["question"], r"关联.*结果")
        for question in second["asked_questions"]:
            self.assertNotRegex(question["question"], r"(?:谁|哪些用户).*删|运行中.*(?:能否|是否|可以).*删|超过1000.*多少")
        found = []
        for record in second["records"]:
            analysis = load(RUNS / record / "analysis/analysis-result.json")
            for question in analysis["questions"]:
                if question["status"] == "provisional":
                    assumptions = [a for a in analysis["assumptions"] if a["status"] == "active" and a["related_question"] == question["id"]]
                    self.assertTrue(assumptions)
                    found += assumptions
        self.assertTrue(found)
        self.assertTrue(all(a["tag"] == "assumption" and a["basis"] and a["verification"] for a in found))

    def test_edges_remain_inferred_not_invented_rules(self) -> None:
        """第一样例有组合增长，第二样例有混选及导出生命周期/权限/等待边界。"""
        first = next(iter(self.documents("high-low-voltage").values()))[0]
        self.assertTrue(any(re.search(r"增长|增加|扩大|爆炸", i["content"]) and re.search(r"规模|数量|组合", i["content"]) and i["tag"] == "inferred" for i in first["business_assessment"]["boundaries"]))
        turn = self.turn("task-management", "answers")
        items = [i for record in turn["records"] for i in entries(load(RUNS / record / "analysis/analysis-result.json")) if "content" in i]
        for pattern in (r"混.*(?:选|运行)|(?:选|批).*(?:同时|包含).*运行", r"未完成|运行中.*导出|导出.*运行中", r"(?:导出|结果).*(?:权限|授权|访问)", r"超时|等待|耗时"):
            self.assertTrue(any(re.search(pattern, i["content"]) and i["tag"] == "inferred" for i in items), pattern)

    def test_resolved_conflicts_do_not_leave_opposed_rules_active(self) -> None:
        """实际遗漏回归：冲突已裁决或暂定后，旧候选保留但不得仍作当前有效规则。"""
        stop = self.turn("task-management", "stop")
        states = {load(RUNS / record / "analysis/analysis-result.json")["requirement_id"]: load(RUNS / record / "analysis/analysis-result.json") for record in stop["records"]}
        deletion = states["REQ-2026-003"]
        rules = {i["id"]: i for i in deletion["requirements"]["business_rules"]}
        self.assertEqual(rules["BR-1"]["status"], "to_reassess")
        self.assertRegex(rules["BR-1"]["content"], r"所有用户")
        self.assertEqual(rules["BR-2"]["status"], "active")
        self.assertEqual(next(q for q in deletion["questions"] if q["id"] == "Q-1")["status"], "answered")
        export = states["REQ-2026-005"]
        rules = {i["id"]: i for i in export["requirements"]["business_rules"]}
        for old in ("BR-1", "BR-2"):
            self.assertEqual(rules[old]["status"], "to_reassess")
        self.assertEqual(rules["BR-3"]["tag"], "assumption")
        self.assertEqual(export["assumptions"][0]["status"], "active")

    def test_end_and_limit_do_not_close_p0(self) -> None:
        """用户结束无新提问，上限控制独立计数，最终仍保留核心缺口。"""
        for project in ("high-low-voltage", "task-management"):
            stop = self.turn(project, "stop")
            self.assertEqual(stop["asked_refs"], [])
            self.assertEqual(stop["control_questions"], [])
            self.assertTrue(any(q["priority"] == "P0" and q["status"] == "open" for a, _ in self.documents(project).values() for q in a["questions"]))
        limit = self.turn("high-low-voltage", "limit")
        self.assertEqual(limit["asked_refs"], [])
        self.assertEqual(len(limit["control_questions"]), 1)

    def test_probes_are_now_formal_outputs_and_keep_dynamic_questioning(self) -> None:
        """新探针均经补丁保存；后端不问视觉，缺陷及已知原因不追问价值。"""
        docs = self.documents("probes")
        self.assertFalse(docs["PROBE-BACKEND"][0]["ux_assessment"]["ui_dependent"])
        for name, expected in (("defect", 0), ("notification", 1), ("notification-with-reason", 0)):
            turn = self.turn("probes", name)
            self.assertEqual(len(turn["asked_refs"]), expected)
        for question in self.turn("probes", "backend")["asked_questions"]:
            self.assertNotRegex(question["question"], r"视觉稿|按钮位置|是否需要登录|是否支持中文")
        self.assertGreaterEqual(len(self.turn("probes", "idea")["asked_refs"]), 1)
        for turn in self.turns:
            self.assertLessEqual(len(turn["asked_refs"]), 3)
            self.assertTrue(turn["assistant_message"].strip())
            for q in turn["asked_questions"]:
                self.assertIn(q["priority"], ("P0", "P1"))
                self.assertTrue(q["recommendation"])

    def test_version_diff_and_unchanged_items_are_preserved(self) -> None:
        """模型真实逐项 diff 可定位变化；新版不改无关需求或无关条目。"""
        comparison = load(RUNS / "dialogue/new-version-diff.json")
        self.assertTrue(comparison["items"])
        kinds = {item["change"] for item in comparison["items"]}
        self.assertTrue({"added", "modified", "deleted", "unchanged"} <= kinds)
        text = json.dumps(comparison, ensure_ascii=False)
        self.assertRegex(text, r"5000")
        self.assertRegex(text, r"日志")
        for turn in (self.turn("task-management", "new-version"), self.turn("task-management", "reevaluated")):
            for record in turn["records"]:
                directory = RUNS / record
                after = load(directory / "analysis/analysis-result.json")
                events = [json.loads(line) for line in (directory / "analysis/analysis-events.jsonl").read_text(encoding="utf-8").splitlines()]
                event = events[-1]
                for unaffected in comparison.get("unchanged_item_refs", []):
                    requirement, item_id = unaffected.split("/", 1)
                    if requirement == after["requirement_id"]:
                        self.assertNotIn(item_id, event["affected_ids"], (record, item_id))
                if event["change_type"] == "new_source_version":
                    self.assertTrue(any(q["status"] == "open" and q.get("answer") for q in after["questions"]))
        touched = {load(RUNS / record / "response.json")["requirement_id"] for turn in (self.turn("task-management", "new-version"), self.turn("task-management", "reevaluated")) for record in turn["records"]}
        self.assertTrue(touched <= {"REQ-2026-003", "REQ-2026-005"})
        initial_sources = load(RUNS / "evidence/task-management/initial-04/analysis/source-manifest.json")
        current = self.documents("task-management")["REQ-2026-005"][1]
        latest_sources = load(current.with_name("source-manifest.json"))
        self.assertGreater(len(latest_sources), len(initial_sources))
        self.assertEqual(latest_sources[:len(initial_sources)], initial_sources)

    def test_incremental_scenarios_have_actual_evidence(self) -> None:
        """补充冲突、更正撤销、新版重开及失败修复必须有实际记录，不能只自报通过。"""
        supplemental = self.turn("task-management", "conflicting-supplement")
        self.assertTrue(supplemental["records"])
        conflicts = [i for record in supplemental["records"] for i in load(RUNS / record / "analysis/analysis-result.json")["business_assessment"]["conflicts"] if i["status"] != "withdrawn"]
        self.assertTrue(any(re.search(r"运行|删除", c["content"]) for c in conflicts))
        correction = self.turn("task-management", "correction")
        self.assertTrue(any("5000" in (RUNS / record / "analysis/analysis-events.jsonl").read_text(encoding="utf-8") for record in correction["records"]))
        withdrawal = self.turn("task-management", "withdrawal")
        analysis = load(RUNS / withdrawal["records"][0] / "analysis/analysis-result.json")
        self.assertTrue(any(i["status"] == "withdrawn" for i in analysis["requirements"]["functional_requirements"]))
        self.assertTrue(all(q["status"] == "dropped" for q in analysis["questions"] if int(q["id"].split("-")[1]) <= 8))
        excluded = [q for q in analysis["questions"] if q["status"] == "excluded"]
        self.assertTrue(excluded)
        self.assertTrue(any(d["status"] == "active" and d["related_question"] == excluded[0]["id"] for d in analysis["decisions"]))
        stale = self.turn("task-management", "new-version")
        self.assertTrue(any(load(RUNS / r / "response.json")["status"] == "warning" for r in stale["records"]))
        self.assertTrue(all(load(RUNS / r / "analysis/analysis-result.json")["meta"]["analysis_status"] == "stale" for r in stale["records"]))
        self.assertTrue(self.turn("task-management", "reevaluated")["records"])
        failure = self.turn("high-low-voltage", "injected-failure")
        self.assertTrue(all(load(RUNS / r / "response.json")["status"] == "fail" for r in failure["records"]))
        fixed = self.turn("high-low-voltage", "repaired")
        self.assertTrue(all(load(RUNS / r / "response.json")["status"] == "pass" for r in fixed["records"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

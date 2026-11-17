"""核对主会话采购撤回模拟试用的补丁和真实 CLI 交接；测试本身不调用模型。"""

import hashlib
import json
from pathlib import Path
import unittest

from test_update_analysis import load_module, read_json
from historical_sources import recorded_bytes


ROOT = Path(__file__).resolve().parents[2]
TRIAL = ROOT / "workspace-sandbox/stage-4/simulated-trial-01"
DIRECTORY = TRIAL / "workspace/projects/office-procurement/requirements/SIM-PROCUREMENT-001"


class SimulatedBusinessTrialTests(unittest.TestCase):
    """按源码、逐轮输入、正式结果和下游产物分别检查，不把模拟试用叫真实验收。"""

    @classmethod
    def setUpClass(cls) -> None:
        """加载最终清单及唯一校验器；缺少实际执行证据即失败。"""
        cls.manifest = read_json(TRIAL / "run-manifest.json")
        cls.turns = read_json(TRIAL / "turns.json")
        cls.validator = load_module(ROOT / "skill/requirement-analyst/scripts/validate_analysis.py", "simulated_trial_validator")

    def test_sources_and_execution_scope_are_traceable(self) -> None:
        """源码有指纹，主会话模拟及用户批准的执行方式调整均可追溯，不冒充独立盲测。"""
        source = read_json(TRIAL / "source-fingerprints.json")
        for relative, expected in source["files"].items():
            self.assertEqual(hashlib.sha256(recorded_bytes(relative, 4)).hexdigest(), expected, relative)
        self.assertTrue(self.manifest["not_real_user_requirement"])
        self.assertEqual(self.manifest["execution"], "main_session_authored_simulation_then_actual_cli")
        adjustment = read_json(TRIAL / "driver/execution-adjustment.json")
        self.assertEqual(adjustment["user_selection"], "主会话直接试用 (Recommended)")
        for relative, expected in self.manifest["artifacts"].items():
            self.assertEqual(hashlib.sha256((TRIAL / relative).read_bytes()).hexdigest(), expected, relative)

    def test_initial_analysis_does_not_preanswer_conflict_or_permission(self) -> None:
        """首轮没有未来模拟答案，状态冲突保持待答；每轮只展示少量关键问题。"""
        first = TRIAL / "evidence" / self.manifest["applications"][0]
        analysis = read_json(first / "requirement/analysis/analysis-result.json")
        self.assertEqual(analysis["meta"]["readiness"], "not_ready")
        conflicts = analysis["business_assessment"]["conflicts"]
        self.assertTrue(conflicts)
        questions = {q["id"]: q for q in analysis["questions"]}
        self.assertTrue(any(questions[c["related_question"]]["status"] == "open" for c in conflicts))
        self.assertFalse(any(q.get("answer") for q in analysis["questions"]))
        for turn in self.turns:
            self.assertLessEqual(len(turn["asked_questions"]), 3)
            self.assertTrue(turn["assistant_message"].strip())
        self.assertTrue(self.turns[0]["asked_questions"])

    def test_only_actual_simulated_answers_are_used(self) -> None:
        """实际提供的回答逐字来自模拟答案库，结束不是答案或风险接受。"""
        bank = read_json(TRIAL / "driver/scenario.json")["business_answer_bank"]
        for turn in self.turns:
            for answer in turn["provided_answers"]:
                self.assertIn(answer["topic"], bank)
                self.assertEqual(answer["statement"], bank[answer["topic"]])
        last = self.turns[-1]
        self.assertEqual(last["user_input"], bank["stop"])
        self.assertEqual(last["asked_questions"], [])
        self.assertEqual(last["provided_answers"], [])
        self.assertEqual(last["control_questions"], [])
        # 数量20只在第二轮模拟回答后成为业务规则，不能提前当成现有系统事实。
        for record in ("round-01", "round-02"):
            snapshot = read_json(TRIAL / "evidence" / record / "requirement/analysis/analysis-result.json")
            self.assertFalse(any("20" in item["content"] for item in snapshot["requirements"]["business_rules"]))
        snapshot = read_json(TRIAL / "evidence/round-03/requirement/analysis/analysis-result.json")
        self.assertTrue(any("20" in item["content"] and item["tag"] == "confirmed" for item in snapshot["requirements"]["business_rules"]))

    def test_actual_cli_updates_are_valid_and_append_history(self) -> None:
        """模型候选原字节提交真实 CLI，每次合法保存带完成清单与连续修订事件。"""
        for record in self.manifest["applications"]:
            directory = TRIAL / "evidence" / record
            result = read_json(directory / "response.json")
            provenance = read_json(directory / "provenance.json")
            self.assertEqual(hashlib.sha256((directory / "patch.json").read_bytes()).hexdigest(), provenance["patch_sha256"])
            origin = Path(provenance["origin"])
            if not origin.is_absolute():
                origin = ROOT / origin
            self.assertEqual(origin.read_bytes(), (directory / "patch.json").read_bytes())
            self.assertEqual(read_json(directory / "process.json")["returncode"], {"pass": 0, "warning": 1, "fail": 2}[result["status"]])
            if not result["written"]:
                continue
            analysis_path = directory / "requirement/analysis/analysis-result.json"
            analysis = read_json(analysis_path)
            validation = self.validator.validate_analysis(analysis, read_json(analysis_path.with_name("source-manifest.json")))
            self.assertEqual(validation["status"], "pass", validation)
            self.assertEqual({c["item"] for c in analysis["completion_checks"]}, set(range(1, 12)))
            events = [json.loads(line) for line in analysis_path.with_name("analysis-events.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([event["revision"] for event in events], list(range(1, analysis["meta"]["analysis_revision"] + 1)))

    def test_final_readiness_does_not_hide_open_core_questions(self) -> None:
        """最终状态按实际清单与遗留问题判断，不因结束或校验通过强行就绪。"""
        analysis = read_json(DIRECTORY / "analysis/analysis-result.json")
        self.assertEqual(analysis["meta"]["analysis_status"], "completed")
        blockers = [q for q in analysis["questions"] if q["status"] == "open" and q["priority"] == "P0"]
        if blockers or any(not c["satisfied"] for c in analysis["completion_checks"] if c["item"] <= 7):
            self.assertEqual(analysis["meta"]["readiness"], "not_ready")
        self.assertTrue(any(q["resolution"] == "ask_dev" and q["status"] == "open" for q in analysis["questions"]))
        self.assertEqual(analysis.get("technical_feasibility", {}).get("conclusion", "unknown"), "unknown")
        rules = analysis["requirements"]["business_rules"]
        self.assertFalse(any("提交过的申请都" in item["content"] and item["status"] == "active" for item in rules))

    def test_real_consumer_preserves_analysis_and_marks_actual_limits(self) -> None:
        """实际消费者只写草稿及 prd 块；草稿标签、追溯和风险与最终分析一致。"""
        evidence = TRIAL / "evidence" / self.manifest["consumer_record"]
        result = read_json(evidence / "response.json")
        self.assertTrue(result["written"], result)
        self.assertEqual(result["action"], "draft_created")
        analysis = read_json(DIRECTORY / "analysis/analysis-result.json")
        text = (DIRECTORY / result["draft_path"]).read_text(encoding="utf-8")
        self.assertIn(analysis["meta"]["readiness"], text)
        self.assertIn("ask_dev", text)
        self.assertIn("待产品负责人确认", text)
        self.assertIn("SIM-PROCUREMENT-001/", text)
        if analysis["meta"]["readiness"] == "not_ready":
            self.assertIn("初步草稿", text)
            self.assertEqual(result["status"], "warning")
        for name, expected in self.manifest["analysis_before_consumer"].items():
            self.assertEqual(hashlib.sha256((DIRECTORY / "analysis" / name).read_bytes()).hexdigest(), expected, name)
        prd = read_json(DIRECTORY / "requirement.json")["prd"]
        self.assertEqual(prd["based_on_analysis_revision"], analysis["meta"]["analysis_revision"])
        self.assertEqual(prd["status"], "draft")


if __name__ == "__main__":
    unittest.main(verbosity=2)

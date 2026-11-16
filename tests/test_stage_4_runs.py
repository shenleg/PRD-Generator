"""独立核对阶段 4 已保存交接证据并重放当前消费者；不调用模型。"""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from test_update_analysis import load_module, read_json
from historical_sources import recorded_bytes


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "workspace-sandbox/stage-4"


def digest(path: Path) -> str:
    """返回 path 的原字节 SHA-256；文件不存在或不可读时直接抛出。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SavedHandoffRuns(unittest.TestCase):
    """交接语义由具体响应、草稿、事件和只读原件核对，不使用自报完成替代。"""

    @classmethod
    def setUpClass(cls) -> None:
        """读取选择清单与实际尝试，缺证据必须报错而不是跳过。"""
        cls.selection = read_json(BASE / "run-manifest.json")
        cls.runs = BASE / f"attempt-{cls.selection['attempt']:02d}"
        cls.manifest = read_json(cls.runs / "run-manifest.json")

    def call(self, case: str, name: str) -> dict:
        """读取 case/name 实际消费响应并返回；缺失或坏 JSON 直接抛出。"""
        return read_json(self.runs / case / "calls" / f"{name}.json")["response"]

    def directory(self, case: str) -> Path:
        """返回 case 的合成需求目录；不读取或修改文件，不产生异常。"""
        return self.runs / case / "workspace/projects/handoff/requirements/HANDOFF-TEST"

    def draft(self, case: str, name: str) -> str:
        """按 case/name 的真实响应读取草稿；文件或路径错误直接抛出。"""
        response = self.call(case, name)
        return (self.directory(case) / response["draft_path"]).read_text(encoding="utf-8")

    def test_provenance_hashes_and_partial_stage_status(self) -> None:
        """历史源码与业务证据指纹保持，当前验收仅更新用户批准的代验状态。"""
        self.assertEqual(self.selection["status"], "scoped_complete_downstream_integration_deferred")
        self.assertEqual(self.manifest["mode"], "deterministic_scripts_no_model_calls")
        self.assertEqual(self.manifest["scenarios"], [f"RA-{i}" for i in range(24, 30)])
        for relative, expected in self.manifest["files"].items():
            self.assertEqual(hashlib.sha256(recorded_bytes(relative, 4)).hexdigest(), expected, relative)
        for relative, expected in self.manifest["artifacts"].items():
            self.assertEqual(digest(self.runs / relative), expected, relative)
        old = read_json(BASE / "attempt-01/RA-25/updates/initial-stale.json")
        self.assertEqual(old["status"], "fail")
        self.assertFalse(old["written"])
        self.assertIn("stale/not_ready", old["diagnostics"][0]["message"])

    def test_proxy_trial_acceptance_keeps_provenance_and_business_blocker(self) -> None:
        """用户批准只满足试用验收条件，不伪造真实来源、不关闭P0或豁免剩余集成。"""
        decision = read_json(BASE / self.selection["acceptance_record"])
        self.assertEqual(decision["user_statement"], "把模拟案例当做真实需求验收吧")
        self.assertEqual(decision["trial_gate_status"], "satisfied_by_user_approved_simulation")
        self.assertEqual(self.selection["trial_gate_status"], decision["trial_gate_status"])
        self.assertTrue(decision["not_real_user_requirement"])
        trial = BASE / decision["accepted_trial"]
        original = read_json(trial / "run-manifest.json")
        self.assertTrue(original["not_real_user_requirement"])
        analysis = read_json(trial / "workspace/projects/office-procurement/requirements/SIM-PROCUREMENT-001/analysis/analysis-result.json")
        self.assertEqual(analysis["meta"]["readiness"], "not_ready")
        self.assertEqual(next(q for q in analysis["questions"] if q["id"] == "Q-12")["status"], "open")
        # 原代验决定保留历史待办；后续用户另行批准延期集成，并已实际完成安装调用收口。
        self.assertEqual(len(decision["remaining"]), 2)
        closure = read_json(BASE / self.selection["closure_record"])
        self.assertEqual(closure["status"], self.selection["status"])
        self.assertEqual(closure["installation_status"], "pass")
        self.assertEqual(self.selection["pending"], [])
        self.assertEqual(self.selection["deferred"], ["实际下游测试Skill集成"])
        self.assertEqual(closure["deferred"][0]["item"], self.selection["deferred"][0])

    def test_ra24_to_ra26_actual_gates(self) -> None:
        """无结果只交接、过期默认拦截、坚持及未就绪草稿均有醒目限制。"""
        missing = self.call("RA-24", "missing")
        self.assertEqual((missing["action"], missing["written"]), ("analyze", False))
        self.assertFalse((self.runs / "RA-24/workspace").exists())
        stale = self.call("RA-25", "default")
        self.assertEqual((stale["action"], stale["written"]), ("reevaluate", False))
        self.assertIn("基于过期分析", self.draft("RA-25", "insisted"))
        self.assertEqual(self.call("RA-25", "insisted")["status"], "warning")
        text = self.draft("RA-26", "preliminary")
        for marker in ("初步草稿", "风险", "P0", "not_ready", "completed"):
            self.assertIn(marker, text)

    def test_ra27_actual_sync_and_owned_blocks(self) -> None:
        """实际分析补丁推进修订号，pending 推导后重新同步；保留两份草稿。"""
        self.assertEqual(self.call("RA-27", "pending")["sync_state"], "pending")
        self.assertFalse(self.call("RA-27", "pending")["written"])
        self.assertEqual(self.call("RA-27", "draft-v2")["sync_state"], "current")
        directory = self.directory("RA-27")
        record = read_json(directory / "requirement.json")
        self.assertEqual(record["prd"], {"based_on_analysis_revision": 2, "status": "draft", "version": 2})
        self.assertNotIn("analysis_revision", record["common"])
        self.assertIn("基于分析修订：1", self.draft("RA-27", "draft-v1"))
        self.assertIn("基于分析修订：2", self.draft("RA-27", "draft-v2"))

    def test_ra28_actual_labels_and_no_withdrawn_content(self) -> None:
        """保存的草稿含推断、假设、验证、待重评与映射，未摘录撤销正文。"""
        text = self.draft("RA-28", "tagged-draft")
        for marker in ("inferred", "assumption", "待验证", "合成推荐依据", "产品负责人后续核对", "to_reassess", "待重评，非确定内容", "HANDOFF-TEST/FR-1", "HANDOFF-TEST/AC-1"):
            self.assertIn(marker, text)
        self.assertNotIn("撤销内容哨兵", text)
        self.assertNotIn("HANDOFF-TEST/EXC-1", text)
        for path in self.runs.glob("RA-*/calls/*.json"):
            record = read_json(path)
            self.assertTrue(record["analysis_unchanged"], path)
            self.assertTrue(record["common_unchanged"], path)

    def test_ra29_actual_registration_preserves_gap_and_old_draft(self) -> None:
        """真实分析更新器登记新 Q 并留事件，缺口未被编造答案关闭，旧草稿待同步。"""
        gap = self.call("RA-29", "gap-request")
        self.assertEqual((gap["action"], gap["written"]), ("register_questions", False))
        self.assertEqual(gap["feedback"]["missing_sections"], ["requirements.acceptance_criteria"])
        update = read_json(self.runs / "RA-29/updates/analyst-reviewed-feedback.json")
        self.assertEqual(update["id_map"]["$handoff_question"], "Q-1")
        directory = self.directory("RA-29")
        analysis = read_json(directory / "analysis/analysis-result.json")
        self.assertEqual(analysis["meta"]["analysis_revision"], 2)
        self.assertEqual(analysis["meta"]["readiness"], "not_ready")
        self.assertEqual(analysis["requirements"]["acceptance_criteria"], [])
        self.assertEqual([(q["id"], q["priority"], q["status"]) for q in analysis["questions"]], [("Q-1", "P0", "open")])
        check = next(c for c in analysis["completion_checks"] if c["item"] == 7)
        self.assertFalse(check["satisfied"])
        events = [json.loads(line) for line in (directory / "analysis/analysis-events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([e["revision"] for e in events], [1, 2])
        self.assertEqual(events[-1]["change_type"], "supplement")
        self.assertIn("Q-1", events[-1]["affected_ids"])
        self.assertEqual(self.call("RA-29", "pending-after-registration")["sync_state"], "pending")
        self.assertEqual(read_json(directory / "requirement.json")["prd"]["based_on_analysis_revision"], 1)
        self.assertEqual(read_json(self.runs / "RA-29/updates/stale-feedback-rejected.json")["status"], "fail")

    def test_saved_model_results_are_only_consumed_not_reanalyzed(self) -> None:
        """三个旧样例消费覆盖三种就绪度；源分析、来源、事件和报告全部原样保留。"""
        readiness = set()
        for sample in self.manifest["samples"]:
            destination = self.runs / "samples/workspace/projects" / sample["project"] / "requirements" / sample["requirement_id"]
            analysis = read_json(destination / "analysis/analysis-result.json")
            readiness.add(analysis["meta"]["readiness"])
            for name, expected in sample["analysis_sha256"].items():
                self.assertEqual(digest(destination / "analysis" / name), expected)
                self.assertEqual(digest(ROOT / sample["origin"] / "analysis" / name), expected)
            result = read_json(self.runs / "samples/calls" / f"{sample['requirement_id']}.json")
            self.assertTrue(result["written"])
            self.assertEqual(result["revision"], analysis["meta"]["analysis_revision"])
        self.assertEqual(readiness, {"not_ready", "conditionally_ready", "ready_for_document"})

    def test_current_scripts_replay_scenarios_without_overwriting_evidence(self) -> None:
        """当前消费者和更新器在新目录重放，关键响应相同，已存在目录拒绝覆盖。"""
        runner = load_module(ROOT / "tests/run_stage_4_handoff.py", "replayed_handoff")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-run"
            result = runner.run(output)
            self.assertEqual(result["scenarios"], self.manifest["scenarios"])
            for path in self.runs.glob("RA-*/calls/*.json"):
                replayed = read_json(output / path.relative_to(self.runs))
                self.assertEqual(replayed, read_json(path), path)
            with self.assertRaises(FileExistsError):
                runner.run(output)


if __name__ == "__main__":
    unittest.main(verbosity=2)

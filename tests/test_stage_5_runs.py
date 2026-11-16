"""阶段5保存的合成CLI场景独立判分及重放；不调用模型，不用自报pass代替证据。"""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from test_update_analysis import load_module, read_json


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "workspace-sandbox/stage-5"


class SavedHistoryRuns(unittest.TestCase):
    """从真实补丁、来源、diff、状态和历史字节核对RA14～19，各场景不互相冒充。"""

    @classmethod
    def setUpClass(cls) -> None:
        """读取当前尝试及唯一校验器，证据缺失时明确失败。"""
        cls.selection = read_json(BASE / "run-manifest.json")
        cls.runs = BASE / cls.selection["attempt"]
        cls.manifest = read_json(cls.runs / "run-manifest.json")
        cls.project = cls.runs / "workspace/projects/stage5-demo"
        cls.validator = load_module(ROOT / "skill/requirement-analyst/scripts/validate_analysis.py", "saved_history_validator")

    def result(self, name: str) -> dict:
        """读取name实际CLI响应；缺文件或坏JSON直接抛出，不静默跳过。"""
        return read_json(self.runs / "evidence" / name / "response.json")

    def snapshot(self, name: str) -> dict:
        """读取name更新器实际快照并返回分析；未保存成功将明确失败。"""
        return read_json(self.runs / "evidence" / name / "requirement/analysis/analysis-result.json")

    def test_sources_artifacts_and_authorized_semantic_scope(self) -> None:
        """真实产物指纹匹配，主会话落盘授权和合成性质明确，不伪造独立端到端。"""
        for relative, expected in self.manifest["artifacts"].items():
            self.assertEqual(hashlib.sha256((self.runs / relative).read_bytes()).hexdigest(), expected, relative)
        for relative, expected in self.selection["files"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected, relative)
        semantic = read_json(BASE / "semantic-execution.json")
        self.assertEqual(semantic["user_selection"], "主会话完成落盘 (Recommended)")
        self.assertFalse(semantic["independent_read"]["candidate_files_created"])
        self.assertTrue(self.manifest["not_real_published_system"])
        self.assertEqual(self.manifest["mode"], "user_approved_main_session_semantic_patches_actual_cli")

    def test_ra14_conflict_is_open_and_baseline_unchanged(self) -> None:
        """具体互斥预期形成CNF及open P0，不自动取舍或改发布基线。"""
        analysis = self.snapshot("RA-14-conflict")
        self.assertEqual(analysis["meta"]["readiness"], "not_ready")
        conflict = analysis["business_assessment"]["conflicts"][0]
        self.assertIn("未完成任务", conflict["content"])
        self.assertIn("互斥", conflict["content"])
        question = next(q for q in analysis["questions"] if q["id"] == conflict["related_question"])
        self.assertEqual((question["priority"], question["status"]), ("P0", "open"))
        self.assertIsNone(analysis["meta"]["baseline_revision"])
        path = self.runs / self.manifest["baseline_path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.manifest["baseline_sha256"])
        validation = self.validator.validate_analysis(analysis, read_json(self.runs / "evidence/RA-14-conflict/requirement/analysis/source-manifest.json"),
            related_analyses=[(read_json(path), read_json(path.with_name("source-manifest.json")))])
        self.assertEqual(validation["status"], "pass", validation)

    def test_ra15_duplicate_has_real_alternatives_not_assumed_merge(self) -> None:
        """角色/筛选能力重合有出处，复用、补差异和缺陷选项仍等待产品回答。"""
        analysis = self.snapshot("RA-15-duplicate")
        question = analysis["questions"][0]
        self.assertEqual(question["status"], "open")
        for value in ("复用", "差异", "缺陷"):
            self.assertTrue(any(value in option for option in question["options"]))
        self.assertEqual(analysis["decisions"], [])
        self.assertEqual(analysis["assumptions"], [])
        self.assertEqual(analysis["context"]["history_review"]["status"], "reviewed")

    def test_ra16_explicit_direct_indirect_and_revalidation_paths(self) -> None:
        """实际差异输出定位BR直接和AC/已答问题间接影响，当前工作副本不替换发布快照。"""
        result = self.result("RA-16-impact")
        self.assertEqual(result["impact"]["direct"], ["HIST-USER-001/BR-1"])
        self.assertEqual(result["impact"]["indirect"], ["HIST-USER-001/AC-1", "HIST-USER-001/Q-1"])
        self.assertEqual(result["impact"]["paths"]["HIST-USER-001/AC-1"], ["HIST-USER-001/FR-1", "HIST-USER-001/BR-1", "HIST-USER-001/AC-1"])
        self.assertIn("HIST-USER-001/AC-1", result["impact"]["revalidate_acceptance"])
        self.assertFalse(result["baseline_modified"])
        self.assertEqual(self.snapshot("RA-16-proposal")["meta"]["baseline_revision"], 1)

    def test_ra17_changes_stale_reopening_and_real_reevaluation(self) -> None:
        """资料变化实际走检测、排除旧索引、stale保存、问题重开、规则和AC重评。"""
        self.assertTrue(self.result("RA-17-detected")["needs_reassessment"])
        self.assertEqual(self.result("RA-17-old-index")["results"], [])
        stale = self.snapshot("RA-17-stale")
        self.assertEqual((stale["meta"]["analysis_status"], stale["meta"]["readiness"]), ("stale", "not_ready"))
        self.assertEqual(stale["context"]["history_review"]["status"], "stale")
        old_question = next(q for q in stale["questions"] if q["id"] == "Q-1")
        self.assertEqual(old_question["status"], "open")
        self.assertIn("第一版", old_question["answer"])
        final = self.snapshot("RA-17-reevaluated")
        self.assertEqual(final["meta"]["analysis_status"], "completed")
        self.assertEqual(final["context"]["history_review"]["status"], "reviewed")
        self.assertIn("冻结", final["requirements"]["business_rules"][0]["content"])
        self.assertIn("冻结", final["requirements"]["acceptance_criteria"][0]["content"])
        self.assertEqual(final["meta"]["baseline_revision"], 1)
        self.assertEqual(len(read_json(self.project / "requirements/HIST-USER-001/analysis/source-manifest.json")), 2)
        self.assertFalse(self.result("RA-17-final-check")["needs_reassessment"])
        self.assertEqual((self.project / "versions/user-deletion-v1.md").read_bytes(), (ROOT / "tests/fixtures/stage-5/history/current-user-deletion.md").read_bytes())

    def test_ra18_old_material_and_ra19_separate_empty_project(self) -> None:
        """年龄警告有真实业务时间，独立空项目明确未对照、不伪造检索或技术结论。"""
        old = self.result("RA-18-old-material")
        self.assertTrue(any("过期" in d["message"] for d in old["diagnostics"]))
        self.assertTrue(any(item["authority"] == "draft" for item in old["results"]))
        empty = self.runs / "empty-workspace/projects/no-history"
        analysis = read_json(empty / "requirements/NEW-NO-HISTORY/analysis/analysis-result.json")
        self.assertEqual(analysis["context"]["history_review"]["status"], "not_performed")
        self.assertEqual(analysis["context"]["history_review"]["source_ids"], [])
        self.assertIsNone(analysis["meta"]["baseline_revision"])
        self.assertFalse((empty / "history").exists())
        self.assertFalse((empty / "index").exists())
        self.assertEqual(self.result("RA-19-missing-index")["results"], [])
        self.assertEqual(self.result("RA-19-degraded")["action"], "degraded")
        self.assertIn("未做历史对照", self.result("RA-19-degraded")["message"])
        report = (empty / "requirements/NEW-NO-HISTORY/analysis/analysis-report.md").read_text(encoding="utf-8")
        self.assertIn("not_performed", report)
        self.assertIn("未做历史对照", report)
        self.assertEqual(len(self.manifest["reports"]), 4)

    def test_installed_skill_loads_history_reference_on_natural_request(self) -> None:
        """实际CLI自然触发模型调用历史参考，识别冲突与未批准状态，未声称已改写基线。"""
        evidence = read_json(BASE / self.selection["installed_verification"])
        self.assertEqual(evidence["status"], "pass")
        self.assertEqual(evidence["result_subtype"], "success")
        self.assertFalse(evidence["result_is_error"])
        self.assertNotIn("requirement-analyst", evidence["prompt"])
        self.assertTrue(any(c.get("skill") == "requirement-analyst" for c in evidence["calls"]))
        self.assertTrue(any(c.get("project_relative_path", "").endswith("references/historical-retrieval.md") for c in evidence["calls"]))
        for phrase in ("冲突", "任务"):
            self.assertIn(phrase, evidence["answer"])
        self.assertRegex(evidence["answer"], r"未批准|未获批")
        self.assertRegex(evidence["answer"], r"未写入文件|没有写入或修改文件")
        for relative, expected in evidence["source_fingerprints"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected, relative)
        self.assertNotIn(str(ROOT), json.dumps(evidence, ensure_ascii=False))

    def test_current_tools_replay_all_scenarios_and_preserve_existing_evidence(self) -> None:
        """用全新目录重放真实CLI链路，已存在目录拒绝覆盖；不重调用模型。"""
        runner = load_module(ROOT / "tests/run_stage_5_trial.py", "replay_history_scenarios")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "fresh"
            replay = runner.run(output)
            self.assertEqual(replay["scenarios"], [f"RA-{i}" for i in range(14, 20)])
            self.assertEqual([(r["record"], r["status"]) for r in replay["records"]], [(r["record"], r["status"]) for r in self.manifest["records"]])
            with self.assertRaises(FileExistsError):
                runner.run(output)


if __name__ == "__main__":
    unittest.main(verbosity=2)

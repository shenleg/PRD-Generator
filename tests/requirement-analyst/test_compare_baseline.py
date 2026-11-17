"""阶段5首个公共CLI切片：显式分析对照，只读历史基线，不进行语义裁决。"""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_minimal_prd_consumer import ready_patch
from test_update_analysis import load_module, read_json


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill/requirement-analyst/scripts/compare_baseline.py"


class CompareBaselineCliTests(unittest.TestCase):
    """通过进程、输出及文件原字节验证，不耦合脚本内部函数。"""

    def setUp(self) -> None:
        """用真实更新器构造已校验合成分析；不把该测试输入声称为真实发布需求。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        updater = load_module(ROOT / "skill/requirement-analyst/scripts/update_analysis.py", "comparison_fixture_writer")
        result = updater.update_analysis(self.root / "workspace", "history-test", ready_patch())
        self.assertEqual(result["status"], "pass", result)
        directory = self.root / "workspace/projects/history-test/requirements/HANDOFF-TEST/analysis"
        self.analysis = read_json(directory / "analysis-result.json")
        self.manifest = read_json(directory / "source-manifest.json")
        self.baseline = self.save("baseline", self.analysis)

    def save(self, directory: str, analysis: dict) -> Path:
        """将给定合成analysis及同来源写入独立directory，返回结果路径；文件错误直接抛出。"""
        target = self.root / directory
        target.mkdir()
        path = target / "analysis-result.json"
        path.write_text(json.dumps(analysis, ensure_ascii=False), encoding="utf-8")
        path.with_name("source-manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        return path

    def run_cli(self, *args: str) -> tuple[int, dict]:
        """从非仓库目录运行真实CLI，返回退出码和单个JSON；非法输出直接使测试失败。"""
        process = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *map(str, args)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(process.stderr, "", process.stderr)
        return process.returncode, json.loads(process.stdout)

    def test_explicit_same_requirement_diff_preserves_both_inputs(self) -> None:
        """同需求按稳定编号识别改动、缺项及新增；missing不等于获准删除基线。"""
        proposal = deepcopy(self.analysis)
        proposal["meta"]["analysis_revision"] = 2
        proposal["requirements"]["functional_requirements"][0]["content"] = "合成修改：增加批量查询"
        proposal["requirements"]["acceptance_criteria"] = []
        item = deepcopy(proposal["requirements"]["business_rules"] or proposal["requirements"]["goals"])[0]
        item.update(id="BR-1", content="合成新增规则")
        proposal["requirements"]["business_rules"] = [item]
        path = self.save("proposal", proposal)
        before = {p: p.read_bytes() for p in self.root.rglob("*.json")}
        code, result = self.run_cli("--baseline", self.baseline, "--proposal", path)
        self.assertEqual((code, result["status"]), (0, "pass"), result)
        self.assertEqual(result["changes"]["added"], ["HANDOFF-TEST/BR-1"])
        self.assertEqual(result["changes"]["modified"], ["HANDOFF-TEST/FR-1"])
        self.assertEqual(result["changes"]["missing"], ["HANDOFF-TEST/AC-1"])
        self.assertEqual(result["changes"]["unchanged"], ["HANDOFF-TEST/GOAL-1"])
        self.assertFalse(result["baseline_modified"])
        self.assertIn("不是删除授权", result["limits"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*.json")})

    def test_direct_indirect_impacts_follow_references_not_shared_ancestors(self) -> None:
        """FR变动影响依赖它的BR及间接AC，但不沿共享GOAL误伤兄弟FR；环不会无限遍历。"""
        baseline = deepcopy(self.analysis)
        goal = baseline["requirements"]["goals"][0]
        function = baseline["requirements"]["functional_requirements"][0]
        function["related_ids"] = ["GOAL-1"]
        sibling = deepcopy(function)
        sibling.update(id="FR-2", content="无关兄弟功能")
        baseline["requirements"]["functional_requirements"].append(sibling)
        rule = deepcopy(goal)
        rule.update(id="BR-1", content="依赖目标功能的规则", related_ids=["FR-1"])
        baseline["requirements"]["business_rules"] = [rule]
        baseline["requirements"]["acceptance_criteria"][0]["related_ids"] = ["BR-1"]
        base = self.save("graph-base", baseline)
        proposal = deepcopy(baseline)
        proposal["requirements"]["functional_requirements"][0]["content"] = "功能发生变化"
        path = self.save("graph-proposal", proposal)
        code, result = self.run_cli("--baseline", base, "--proposal", path)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["impact"]["direct"], ["HANDOFF-TEST/BR-1"])
        self.assertEqual(result["impact"]["indirect"], ["HANDOFF-TEST/AC-1"])
        self.assertEqual(result["impact"]["revalidate_acceptance"], ["HANDOFF-TEST/AC-1"])
        self.assertEqual(result["impact"]["paths"]["HANDOFF-TEST/AC-1"], ["HANDOFF-TEST/FR-1", "HANDOFF-TEST/BR-1", "HANDOFF-TEST/AC-1"])
        self.assertNotIn("HANDOFF-TEST/FR-2", result["impact"]["paths"])
        # 已建立显式引用若形成环，也只输出每个候选一次。
        proposal["requirements"]["functional_requirements"][0]["related_ids"].append("AC-1")
        cycle = self.save("graph-cycle", proposal)
        self.assertEqual(self.run_cli("--baseline", base, "--proposal", cycle)[0], 0)

    def test_fail_precedes_stale_warning_and_has_no_diff(self) -> None:
        """非法条目与stale并存时整体fail，不因为用户指定基线就接受坏数据。"""
        invalid = deepcopy(self.analysis)
        invalid["meta"]["analysis_status"] = "stale"
        invalid["requirements"]["goals"][0]["sources"] = []
        path = self.save("invalid", invalid)
        code, result = self.run_cli("--baseline", self.baseline, "--proposal", path)
        self.assertEqual((code, result["status"]), (2, "fail"))
        self.assertNotIn("changes", result)
        self.assertTrue(any(d["level"] == "warning" for d in result["validations"]["proposal"]["diagnostics"]))

    def test_missing_history_degrades_but_invalid_proposal_still_fails(self) -> None:
        """没有历史只说明未做对照，不能绕过新结果校验或凭空宣布无冲突。"""
        code, result = self.run_cli("--proposal", self.baseline)
        self.assertEqual((code, result["status"], result["action"]), (1, "warning", "degraded"))
        self.assertIn("未做历史对照", result["message"])
        invalid = self.save("invalid-no-baseline", {})
        code, result = self.run_cli("--proposal", invalid)
        self.assertEqual((code, result["status"]), (2, "fail"))

    def test_withdrawal_and_reassessment_are_changes_not_physical_deletion(self) -> None:
        """撤销、待重评和扩展字段变动保留完整before/after，不误认新增或静默忽略。"""
        proposal = deepcopy(self.analysis)
        proposal["meta"]["analysis_revision"] = 2
        proposal["requirements"]["functional_requirements"][0]["status"] = "withdrawn"
        proposal["requirements"]["acceptance_criteria"][0]["status"] = "to_reassess"
        proposal["requirements"]["goals"][0]["review_note"] = "合成扩展字段"
        path = self.save("status-change", proposal)
        code, result = self.run_cli("--baseline", self.baseline, "--proposal", path)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["changes"]["missing"], [])
        self.assertEqual(set(result["changes"]["modified"]), {"HANDOFF-TEST/GOAL-1", "HANDOFF-TEST/FR-1", "HANDOFF-TEST/AC-1"})
        item = next(d for d in result["details"] if d["reference"] == "HANDOFF-TEST/FR-1")
        self.assertEqual(item["before"]["value"]["status"], "active")
        self.assertEqual(item["after"]["value"]["status"], "withdrawn")

    def test_non_item_and_source_changes_are_not_silently_unchanged(self) -> None:
        """来源修订或非条目节变化单独列出；同SRC换依据也能定位直接采用者。"""
        baseline = deepcopy(self.analysis)
        source = {"source_id": "SRC-1", "name": "合成资料", "path": "policy.md", "type": "project_material", "credibility": "测试", "last_updated": None, "revision": 1}
        self.manifest = [source]
        baseline["requirements"]["functional_requirements"][0]["sources"] = [{"type": "project_material", "source_id": "SRC-1", "location": "第1条"}]
        base = self.save("source-base", baseline)
        proposal = deepcopy(baseline)
        proposal["ux_assessment"]["design_pending_items"] = ["新增待设计事项"]
        self.manifest = [{**source, "revision": 2}]
        path = self.save("source-proposal", proposal)
        code, result = self.run_cli("--baseline", base, "--proposal", path)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["non_item_changes"], ["ux_assessment"])
        self.assertEqual(result["source_changes"], ["SRC-1"])
        self.assertIn("HANDOFF-TEST/FR-1", result["source_changed_items"])
        self.assertIn("HANDOFF-TEST/AC-1", result["impact"]["revalidate_acceptance"])

    def test_valid_stale_is_warning_not_silent_pass(self) -> None:
        """合法过期结果保留warning，机械差异仍可查看但不等于重评完成。"""
        proposal = deepcopy(self.analysis)
        proposal["meta"].update(analysis_status="stale", readiness="not_ready")
        path = self.save("stale", proposal)
        code, result = self.run_cli("--baseline", self.baseline, "--proposal", path)
        self.assertEqual((code, result["status"]), (1, "warning"))
        self.assertEqual(result["validations"]["proposal"]["status"], "warning")
        self.assertEqual(result["changes"]["modified"], [])

    def test_wrong_identity_bad_json_and_unknown_option_are_structured_failures(self) -> None:
        """不把不同需求当同一基线，也不吞重复JSON键、NaN或未知CLI参数。"""
        proposal = deepcopy(self.analysis)
        proposal["requirement_id"] = "OTHER-TEST"
        path = self.save("other", proposal)
        code, result = self.run_cli("--baseline", self.baseline, "--proposal", path)
        self.assertEqual((code, result["status"]), (2, "fail"))
        for raw in ('{"x":1,"x":2}', '{"x":NaN}'):
            path.write_text(raw, encoding="utf-8")
            code, result = self.run_cli("--baseline", self.baseline, "--proposal", path)
            self.assertEqual((code, result["status"]), (2, "fail"))
        code, result = self.run_cli("--proposal", self.baseline, "--unknown")
        self.assertEqual((code, result["status"]), (2, "fail"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

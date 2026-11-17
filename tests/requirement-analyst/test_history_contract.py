"""阶段5历史依据采用与基线声明的公开CLI契约；所有资料为用户批准的合成夹具。"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_update_analysis import initial, read_json


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skill/requirement-analyst/scripts"


class HistoryContractCliTests(unittest.TestCase):
    """通过真实更新器和只读检查CLI核对来源采用、旧结果兼容及基线保护。"""

    def setUp(self) -> None:
        """创建独立合成资料和工作区；临时目录不接触原试跑证据。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.material = self.root / "policy.md"
        self.material.write_text("合成现行业务规范：待审批申请可撤回。\n", encoding="utf-8")
        self.workspace = self.root / "workspace"
        self.directory = self.workspace / "projects/demo/requirements/HIST-TEST/analysis"

    def command(self, script: str, *args) -> tuple[int, dict]:
        """真实运行script，返回退出码及单JSON；CLI非结构化错误直接使测试失败。"""
        process = subprocess.run([sys.executable, "-I", "-B", str(SCRIPTS / script), *map(str, args)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(process.stderr, "", process.stderr)
        return process.returncode, json.loads(process.stdout)

    def patch(self) -> dict:
        """返回携带显式发布依据和采用指纹的合成首次补丁，未执行任何写入。"""
        patch = initial("HIST-TEST")
        patch["operations"].insert(0, {"op": "add_source", "ref": "$history", "value": {
            "name": "合成业务规范", "path": "policy.md", "type": "project_material", "credibility": "合成正式规则供测试",
            "last_updated": None, "revision": 1, "authority": "current_published", "publication_basis": "合成场景负责人明确此文为当前发布版，不是真实项目发布",
            "adopted_sha256": hashlib.sha256(self.material.read_bytes()).hexdigest()}})
        patch["set"]["context.history_review"] = {"status": "reviewed", "reason": "仅完成手动指定规范对照，不代表已查全项目", "source_ids": ["$history"],
            "baseline": {"requirement_id": "HIST-TEST", "analysis_revision": 1, "source_id": "$history", "publication_basis": "合成场景产品负责人确认当前发布分析修订1"}}
        patch["set"]["meta.baseline_revision"] = 1
        patch["actor"] = "user"
        patch["user_statement"] = "合成确认：以HIST-TEST已发布分析修订1为当前变更依据；仅用于测试。"
        return patch

    def apply(self, patch: dict, name="patch") -> tuple[int, dict]:
        """把patch存为新的测试输入，调用真实更新器并返回实际响应；已有输入不覆盖。"""
        path = self.root / f"{name}.json"
        with path.open("x", encoding="utf-8") as stream:
            json.dump(patch, stream, ensure_ascii=False)
        return self.command("update_analysis.py", "--workspace", self.workspace, "--project", "demo", "--patch", path)

    def test_explicit_baseline_and_adopted_source_roundtrip(self) -> None:
        """只有明示确认的发布依据能登记基线，采用来源别名由脚本转正式编号。"""
        code, result = self.apply(self.patch())
        self.assertEqual((code, result["status"]), (0, "pass"), result)
        analysis = read_json(self.directory / "analysis-result.json")
        self.assertEqual(analysis["meta"]["baseline_revision"], 1)
        self.assertEqual(analysis["context"]["history_review"]["source_ids"], ["SRC-1"])
        self.assertEqual(analysis["context"]["history_review"]["baseline"]["source_id"], "SRC-1")
        manifest = read_json(self.directory / "source-manifest.json")
        self.assertEqual(manifest[0]["adopted_sha256"], hashlib.sha256(self.material.read_bytes()).hexdigest())

    def test_baseline_cannot_be_inferred_or_declared_without_publication_basis(self) -> None:
        """基线登记不能因文件存在自动确认，也不能只写修订号绕开发布依据。"""
        for index, mutation in enumerate(("analyst", "draft", "no_review", "bad_revision", "bad_hash")):
            patch = self.patch()
            if mutation == "analyst":
                patch["actor"] = "analyst"
            elif mutation == "draft":
                patch["operations"][0]["value"]["authority"] = "draft"
            elif mutation == "no_review":
                del patch["set"]["context.history_review"]
            elif mutation == "bad_revision":
                patch["set"]["meta.baseline_revision"] = 9
            else:
                patch["operations"][0]["value"]["adopted_sha256"] = "invalid"
            code, result = self.apply(patch, f"reject-{index}")
            self.assertEqual((code, result["status"]), (2, "fail"), (mutation, result))
            self.assertFalse((self.directory / "analysis-result.json").exists())

    def test_legacy_baseline_cannot_be_cleared_by_analyst(self) -> None:
        """旧1.0非空基线即使没有history_review，也受protocol层的用户明示保护。"""
        self.assertEqual(self.apply(initial("HIST-TEST"), "legacy-initial")[0], 0)
        path = self.directory / "analysis-result.json"
        legacy = read_json(path)
        legacy["meta"]["baseline_revision"] = 3
        path.write_text(json.dumps(legacy), encoding="utf-8")
        before = path.read_bytes()
        patch = {"patch_version": "1.0", "requirement_id": "HIST-TEST", "base_revision": 1, "change_type": "supplement", "actor": "analyst", "summary": "尝试清空旧基线", "operations": [], "set": {"meta.baseline_revision": None}, "completion_checks": legacy["completion_checks"]}
        code, result = self.apply(patch, "legacy-clear")
        self.assertEqual((code, result["status"]), (2, "fail"), result)
        self.assertEqual(path.read_bytes(), before)
        self.assertIn("用户明示", result["diagnostics"][0]["message"])

    def test_source_fingerprint_changes_return_stale_candidate_without_writes(self) -> None:
        """已采用资料字节改变时只读检测给出受影响来源，不自行落盘状态或覆盖基线。"""
        self.assertEqual(self.apply(self.patch())[0], 0)
        path = self.directory / "analysis-result.json"
        before = path.read_bytes()
        code, result = self.command("compare_baseline.py", "--check-sources", path, "--project-root", self.root)
        self.assertEqual((code, result["status"], result["needs_reassessment"]), (0, "pass", False), result)
        self.material.write_text("合成新版规范：撤回须按新状态规则处理。\n", encoding="utf-8")
        code, result = self.command("compare_baseline.py", "--check-sources", path, "--project-root", self.root)
        self.assertEqual((code, result["status"], result["needs_reassessment"]), (1, "warning", True), result)
        self.assertEqual(result["changed_sources"][0]["source_id"], "SRC-1")
        self.assertEqual(before, path.read_bytes())
        self.assertIn("补丁", result["next_action"])

    def test_archived_baseline_bytes_only_used_after_newer_source_is_explicitly_adopted(self) -> None:
        """归档旧基线不掩盖当前资料变化；仅新版本已采用时才按归档校验旧依据。"""
        patch = self.patch()
        archived = self.root / "policy-v1.md"
        archived.write_bytes(self.material.read_bytes())
        patch["operations"][0]["value"]["archived_path"] = "policy-v1.md"
        self.assertEqual(self.apply(patch)[0], 0)
        self.material.write_text("合成第二版规则\n", encoding="utf-8")
        path = self.directory / "analysis-result.json"
        self.assertTrue(self.command("compare_baseline.py", "--check-sources", path, "--project-root", self.root)[1]["needs_reassessment"])
        current = read_json(path)
        manifest = read_json(path.with_name("source-manifest.json"))
        followup = {"patch_version": "1.0", "requirement_id": "HIST-TEST", "base_revision": 1, "change_type": "supplement", "actor": "analyst", "summary": "仅测试显式采用新来源，业务问题仍open",
                    "operations": [{"op": "add_source", "ref": "$next", "value": {**{k: v for k, v in manifest[0].items() if k not in {"source_id", "archived_path"}}, "revision": 2, "adopted_sha256": hashlib.sha256(self.material.read_bytes()).hexdigest()}}],
                    "set": {"context.history_review": {**current["context"]["history_review"], "source_ids": ["SRC-1", "$next"]}}, "completion_checks": current["completion_checks"]}
        self.assertEqual(self.apply(followup, "adopt-next")[0], 0)
        code, result = self.command("compare_baseline.py", "--check-sources", path, "--project-root", self.root)
        self.assertEqual((code, result["needs_reassessment"]), (0, False), result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

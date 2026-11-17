"""核对阶段8实际人工批准与CLI证据，不重新模拟批准或调用模型。"""

import hashlib
import json
from pathlib import Path
import unittest

from historical_sources import recorded_bytes
from material_paths import current_material_path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "workspace-sandbox/stage-8"
TRIAL = BASE / "trial-01"
PROJECT = TRIAL / "workspace/projects/knowledge-demo"


def read_json(path):
    """读取保存的证据并返回；path为证据文件，缺失或非法JSON直接抛出。"""
    return json.loads(path.read_text(encoding="utf-8"))


class SavedKnowledgeRuns(unittest.TestCase):
    """验证实际保存的确认范围、内容保真、门禁及检索链路。"""

    def test_actual_approval_is_specific_and_limited_to_simulation(self):
        """实际用户选择绑定DK-001准确内容，不扩大为真实业务规范或提交授权。"""
        decision = read_json(TRIAL / "approval-decision.json")
        proposal = read_json(TRIAL / "proposal.json")
        approval = read_json(TRIAL / "approval.json")
        canonical = json.dumps(proposal, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        fingerprint = hashlib.sha256(canonical).hexdigest()
        self.assertTrue(decision["actual_human_approval"])
        self.assertEqual(decision["user_selection"], "批准 DK-001")
        self.assertEqual(approval["user_statement"], decision["user_selection"])
        self.assertEqual(approval["proposal_sha256"], fingerprint)
        self.assertEqual(decision["proposal_sha256"], fingerprint)
        self.assertIn(proposal["content"], decision["question"])
        self.assertIn(proposal["scope"], decision["question"])
        self.assertTrue(proposal["simulation"])
        self.assertIn("不是真实产品确认", proposal["basis"]["statement"])
        self.assertIn("不批准真实业务规范", decision["question"])
        self.assertIn("不授权提交或推送", decision["scope"])

    def test_actual_write_preserves_proposal_approval_and_sources(self):
        """正式知识仅含获批术语，来源不变，推断及未确认规则没有入库。"""
        proposal = read_json(TRIAL / "proposal.json")
        entry_path = PROJECT / "knowledge/domain/DK-001.json"
        entry = read_json(entry_path)
        self.assertEqual(entry["proposal"], proposal)
        self.assertEqual(entry["approval"], read_json(TRIAL / "approval.json"))
        for source in proposal["sources"]:
            self.assertEqual(hashlib.sha256((PROJECT / source["path"]).read_bytes()).hexdigest(), source["sha256"])
        self.assertEqual(sorted(str(p.relative_to(PROJECT)) for p in (PROJECT / "knowledge").rglob("*.json")),
                         ["knowledge/domain/DK-001.json"])
        self.assertNotIn("1000", entry["proposal"]["content"])
        self.assertNotIn("30分钟", entry["proposal"]["content"])
        review = read_json(TRIAL / "suggestion-review.json")
        self.assertFalse(review["independent_model_call"])
        self.assertFalse(review["blind_test"])
        self.assertEqual({item["classification"] for item in review["not_proposed"]}, {"inferred", "unconfirmed"})
        verification = read_json(TRIAL / "verification.json")
        self.assertEqual(verification["source_sha256_before"], verification["source_sha256_after"])
        self.assertEqual(hashlib.sha256(entry_path.read_bytes()).hexdigest(), verification["entry_sha256"])

    def test_saved_cli_chain_refuses_missing_approval_and_overwrite(self):
        """缺批准拒绝、首次成功、重复拒绝、显式索引及截断命中均有真实响应。"""
        expected = {"missing-approval": (2, "fail"), "save": (0, "pass"),
                    "repeat-save": (2, "fail"), "index": (0, "pass"), "search": (1, "warning")}
        for name, (code, status) in expected.items():
            with self.subTest(name=name):
                evidence = read_json(TRIAL / f"{name}-evidence.json")
                self.assertEqual(evidence["returncode"], code)
                self.assertEqual(evidence["stdout"]["status"], status)
                self.assertIn("python", evidence["command"])
                self.assertEqual(evidence["stderr"], "")
        self.assertFalse(read_json(TRIAL / "missing-approval-evidence.json")["knowledge_directory_exists"])
        self.assertFalse(read_json(TRIAL / "repeat-save-evidence.json")["stdout"]["file_created"])
        found = read_json(TRIAL / "search-evidence.json")["stdout"]
        self.assertTrue(found["truncated"])
        self.assertEqual(found["results"][0]["authority"], "draft")
        self.assertIn("合成验收专用", found["results"][0]["excerpt"])
        self.assertEqual(found["results"][0]["sha256"], read_json(TRIAL / "verification.json")["entry_sha256"])

    def test_trial_fingerprints_match_actual_source_and_artifacts(self):
        """旧试跑源码绑定阶段8提交，业务证据漂移仍失败，不改旧指纹。"""
        manifest = read_json(BASE / "run-manifest.json")
        self.assertTrue(manifest["knowledge_written"])
        self.assertEqual(manifest["status"], "completed_with_actual_user_approval_in_simulated_project")
        for mapping, directory in ((manifest["source_fingerprints"], ROOT), (manifest["artifacts"], TRIAL)):
            self.assertTrue(mapping)
            for relative, expected in mapping.items():
                with self.subTest(path=relative):
                    # 源码绑定原执行版本；资料和产物仍读取当前字节，不能用历史副本掩盖改动。
                    if directory == ROOT and (relative.startswith("skill/") or relative.endswith(".py")):
                        raw = recorded_bytes(relative, 8)
                    else:
                        path = current_material_path(relative) if directory == ROOT else directory / relative
                        raw = path.read_bytes()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)

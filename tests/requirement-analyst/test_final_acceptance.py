"""通过最终验收驱动公开入口与保存证据核对完整生命周期；不调用模型或代替业务签核。"""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from test_update_analysis import load_module
from historical_sources import recorded_bytes
from material_paths import current_material_path


ROOT = Path(__file__).resolve().parents[2]
TRIAL = ROOT / "workspace-sandbox/final-acceptance/attempt-01"


class FinalAcceptanceTests(unittest.TestCase):
    """核对现行参考一致性、真实CLI链路以及新目录重放边界。"""

    def test_question_routes_reach_enabled_history_and_ux_references(self):
        """问题分工不能被旧阶段文字误导为禁用已实现的检索或体验分析。"""
        content = (ROOT / "skill/requirement-analyst/references/question-strategy.md").read_text(encoding="utf-8")
        self.assertNotIn("也不运行历史检索", content)
        self.assertNotIn("本阶段不展开完整视觉分析", content)
        self.assertIn("historical-retrieval.md", content)
        self.assertIn("ux-visual-assessment.md", content)

    def test_lifecycle_preserves_core_blocker_and_prd_revision_sync(self):
        """五轮保存后仍保留open P0，修订变化使旧草稿待同步，不因结束变ready。"""
        manifest = json.loads((TRIAL / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "pass")
        self.assertFalse(manifest["new_model_call"])
        self.assertFalse(manifest["real_business_approval"])
        self.assertEqual(manifest["cli_count"], 16)
        self.assertEqual(manifest["final"], {"analysis_revision": 5, "analysis_status": "completed",
                         "readiness": "not_ready", "open_p0": ["Q-12"], "prd_version": 2,
                         "based_on_analysis_revision": 5})
        self.assertEqual(manifest["analysis_before_final_consumer"], manifest["analysis_after_final_consumer"])
        records = {record["record"]: record for record in manifest["records"]}
        self.assertEqual(records["00-no-analysis"]["action"], "analyze")
        self.assertEqual(records["old-revision-rejected"]["status"], "fail")
        self.assertEqual(records["old-patch-rejected"]["status"], "fail")
        self.assertEqual(records["final-draft"]["status"], "warning")
        self.assertTrue(records["final-draft"]["written"])

    def test_saved_source_and_artifact_fingerprints_match(self):
        """旧试跑源码绑定原验收提交，业务产物仍核对当前字节，历史证据不改。"""
        manifest = json.loads((TRIAL / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["historical_evidence_unchanged"])
        for mapping, directory in ((manifest["source_fingerprints"], ROOT), (manifest["artifacts"], TRIAL)):
            for relative, expected in mapping.items():
                with self.subTest(path=relative):
                    # 旧源码只证明当时执行；现行产品由下方公开驱动另行重跑，不重写旧指纹。
                    if directory == ROOT and (relative.startswith("skill/") or relative.endswith(".py")):
                        raw = recorded_bytes(relative, "final")
                    else:
                        path = current_material_path(relative) if directory == ROOT else directory / relative
                        raw = path.read_bytes()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)

    def test_current_public_driver_replays_and_refuses_existing_output(self):
        """当前公开驱动完整执行16条CLI，既有输出目录必须拒绝且不覆盖。"""
        driver = load_module(ROOT / "tests/requirement-analyst/run_final_acceptance.py", "final_acceptance_driver")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-run"
            manifest = driver.run(output)
            self.assertEqual(manifest["cli_count"], 16)
            self.assertEqual(manifest["final"]["readiness"], "not_ready")
            before = (output / "run-manifest.json").read_bytes()
            with self.assertRaises(FileExistsError):
                driver.run(output)
            self.assertEqual((output / "run-manifest.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)

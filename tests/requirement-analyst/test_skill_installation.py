"""核对用户授权的真实CLI脱敏验证证据；不读取本地原始会话，不重新调用模型。"""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

from test_update_analysis import read_json
from historical_sources import recorded_bytes


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "workspace-sandbox/stage-4/installation"


class InstalledSkillTests(unittest.TestCase):
    """从真实工具轨迹最小提取验证安装与上下文；不把脱敏摘要称为公开原始会话。"""

    @classmethod
    def setUpClass(cls) -> None:
        """读取可入库的脱敏证据，缺失或坏JSON直接使测试失败。"""
        cls.evidence = read_json(BASE / "verification.json")

    def test_installation_trace_and_source_hashes(self) -> None:
        """当前入口仍指唯一生产目录；历史自动调用证据绑定阶段4收口提交，不冒充阶段5新行为。"""
        evidence = self.evidence
        self.assertEqual(evidence["status"], "pass")
        self.assertEqual((ROOT / evidence["skill_installation"]).resolve(), ROOT / evidence["target"])
        for relative, expected in evidence["files"].items():
            self.assertEqual(hashlib.sha256(recorded_bytes(relative, 4, installed=True)).hexdigest(), expected, relative)
        text = json.dumps(evidence, ensure_ascii=False)
        self.assertNotIn(str(ROOT), text)
        self.assertNotRegex(text, r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
        self.assertEqual(evidence["source_authorization"]["user_selection"], "仅脱敏证据 (Recommended)")
        self.assertFalse(evidence["redaction"]["raw_records_committed"])

    def test_natural_prompt_auto_invokes_hidden_skill(self) -> None:
        """不点名技能的自然语言触发实际Skill调用，菜单隐藏且读取按需参考。"""
        first = self.evidence["turns"][0]
        self.assertNotIn("requirement-analyst", first["prompt"])
        self.assertNotIn("SKILL.md", first["prompt"])
        self.assertFalse(first["skill_visible_in_user_list"])
        self.assertFalse(first["skill_visible_in_slash_menu"])
        skill = next(c for c in first["calls"] if c["tool"] == "Skill" and c["skill"] == "requirement-analyst")
        self.assertTrue(skill["result_present"])
        self.assertFalse(skill["is_error"])
        self.assertEqual(first["result_subtype"], "success")
        self.assertFalse(first["result_is_error"])
        self.assertIn("理解", first["answer"])
        self.assertTrue(any(c["tool"] == "Read" and c["project_relative_path"].startswith(".claude/skills/requirement-analyst/references/") for c in first["calls"]))

    def test_same_session_resolves_previous_option_answers(self) -> None:
        """会话以文件内脱敏别名关联；第二轮未重复业务事实仍正确承接上轮A选项。"""
        first, second = self.evidence["turns"]
        self.assertTrue(self.evidence["same_original_session_verified"])
        self.assertEqual(first["conversation_alias"], second["conversation_alias"])
        self.assertNotIn("派单", second["prompt"])
        self.assertNotIn("先完成", second["prompt"])
        for phrase in ("派单前可以撤回", "派单完成后不能撤回", "以先完成的操作为准", "推荐尚未视为已确认"):
            self.assertIn(phrase, second["answer"])
        self.assertEqual(second["result_subtype"], "success")

    def test_permission_mode_and_local_raw_records_exclusion(self) -> None:
        """权限不绕过；原始烟测路径被忽略，仓库测试不依赖这些本地文件存在。"""
        for turn in self.evidence["turns"]:
            self.assertEqual(turn["tools"], ["Skill", "Read"])
            self.assertEqual(turn["permission_mode"], "dontAsk")
            self.assertEqual(turn["permission_prompts"], "none")
        self.assertTrue(self.evidence["failed_setup"]["preserved_locally"])
        ignored = subprocess.run(["git", "check-ignore", "workspace-sandbox/stage-4/installation/attempt-02/stdout.jsonl", "workspace-sandbox/stage-4/installation/run-manifest.json"], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(len(ignored.stdout.splitlines()), 2)
        self.assertEqual(read_json(ROOT / "workspace-sandbox/stage-4/closure-decision.json")["status"], "scoped_complete_downstream_integration_deferred")


if __name__ == "__main__":
    unittest.main(verbosity=2)

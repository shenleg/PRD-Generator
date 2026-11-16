"""阶段6沿用唯一规则9的公共CLI回归；不新增技术判定器、不调用模型。"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_minimal_prd_consumer import ready_patch
from test_update_analysis import read_json, business_bytes


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill/requirement-analyst/scripts/update_analysis.py"


class FeasibilityCliTests(unittest.TestCase):
    """验证所有结论字段可保存，坏证据或混淆责任方不得落盘。"""

    def setUp(self) -> None:
        """创建独立工作区，文件/进程异常不静默跳过。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.number = 0

    def apply(self, patch: dict) -> tuple[int, dict]:
        """通过实际CLI应用新的patch输入，返回退出码和JSON；输入文件不覆盖。"""
        self.number += 1
        path = self.root / f"patch-{self.number}.json"
        with path.open("x", encoding="utf-8") as stream:
            json.dump(patch, stream, ensure_ascii=False)
        result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--workspace", str(self.workspace), "--project", "technical", "--patch", str(path)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.stderr, "", result.stderr)
        return result.returncode, json.loads(result.stdout)

    def technical(self, conclusion: str) -> dict:
        """返回测试声明结构，不证明真实能力；conclusion指定待验证枚举，返回新字典。"""
        return {"conclusion": conclusion, "evidence": [] if conclusion == "unknown" else [{"content": "合成明确技术资料依据", "sources": [{"type": "user_answer", "location": "合成资料核验输入"}]}], "credibility": "资料不足" if conclusion == "unknown" else "合成当前资料，非真实系统核验", "potential_impact": ["限定本合成操作范围，不承诺上线"], "related_questions": [], "risks": ["结论不替代研发验证"]}

    def test_all_five_conclusions_roundtrip_without_new_schema(self) -> None:
        """已有1.0技术结构经真实更新器保存五种结论，不另造规则9实现。"""
        for conclusion in ("supported", "conditionally_feasible", "risky", "unknown", "conflicting"):
            with self.subTest(conclusion=conclusion):
                patch = ready_patch()
                patch["requirement_id"] = "CLI-" + conclusion
                patch["set"]["technical_feasibility"] = self.technical(conclusion)
                code, response = self.apply(patch)
                self.assertEqual((code, response["status"]), (0, "pass"), response)
                saved = read_json(self.workspace / "projects/technical/requirements" / patch["requirement_id"] / "analysis/analysis-result.json")
                self.assertEqual(saved["technical_feasibility"], patch["set"]["technical_feasibility"])
                self.assertEqual(saved["schema_version"], "1.0")

    def test_invalid_nonunknown_evidence_fails_rule9_and_preserves_old_files(self) -> None:
        """空壳支持结论不允许保存，旧revision、来源、事件及正文原字节不变。"""
        patch = ready_patch()
        patch["set"]["technical_feasibility"] = self.technical("supported")
        self.assertEqual(self.apply(patch)[0], 0)
        before = business_bytes(self.workspace)
        for conclusion in ("supported", "conditionally_feasible", "risky", "conflicting"):
            bad = self.technical(conclusion)
            bad["evidence"] = []
            followup = {"patch_version": "1.0", "requirement_id": patch["requirement_id"], "base_revision": 1, "change_type": "supplement", "actor": "analyst", "summary": "测试拒绝无依据结论", "operations": [], "set": {"technical_feasibility": bad}, "completion_checks": patch["completion_checks"]}
            code, response = self.apply(followup)
            self.assertEqual((code, response["status"]), (2, "fail"))
            self.assertTrue(any(d["rule"] == 9 for d in response["diagnostics"]))
            self.assertEqual(before, business_bytes(self.workspace))

    def test_technical_questions_cannot_point_to_product_decision(self) -> None:
        """把产品取舍挂成技术确认会由同一规则9拒绝，不能只靠合法Q编号凑通过。"""
        patch = ready_patch()
        patch["set"]["meta.readiness"] = "conditionally_ready"
        patch["operations"].append({"op": "add", "collection": "questions", "ref": "$product", "value": {"question": "合成产品范围要如何取舍？", "priority": "P1", "resolution": "ask_product", "reason": "业务未定", "impact": "范围", "options": ["甲", "乙"], "recommendation": "待产品决定", "status": "open", "related_ids": ["$function"]}})
        technical = self.technical("unknown")
        technical["related_questions"] = ["$product"]
        patch["set"]["technical_feasibility"] = technical
        code, response = self.apply(patch)
        self.assertEqual((code, response["status"]), (2, "fail"))
        self.assertTrue(any(d["rule"] == 9 for d in response["diagnostics"]))
        self.assertFalse((self.workspace / "projects/technical/requirements" / patch["requirement_id"] / "analysis/analysis-result.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

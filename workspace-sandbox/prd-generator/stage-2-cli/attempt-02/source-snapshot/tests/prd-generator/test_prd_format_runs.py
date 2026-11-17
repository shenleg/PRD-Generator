"""核对阶段 1 保存证据并在新临时目录重放；不把合成校验称为模型或发布验收。"""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from prd_fixture_support import digest, read_json


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "workspace-sandbox/prd-generator/stage-1/attempt-02"


class PrdFormatEvidenceTests(unittest.TestCase):
    """验证校验证据的来源绑定、十二条规则诊断及不覆盖约束。"""

    def test_saved_diagnostics_and_readonly_hashes(self):
        """保存的十五次 CLI 调用均符合预期，覆盖十二条规则且业务指纹未变。"""
        manifest = read_json(EVIDENCE / "run-manifest.json")
        self.assertEqual(manifest["cli_calls"], 15)
        rules = set()
        for case in manifest["results"]:
            response = read_json(EVIDENCE / case["process"])
            self.assertEqual(response["business_hashes_before"], response["business_hashes_after"])
            self.assertEqual(response["response"]["status"], case["expected_status"])
            self.assertEqual(json.loads(response["stdout"]), response["response"])
            self.assertEqual(response["returncode"], 0 if case["expected_status"] == "pass" else 2)
            if case["expected_rule"]:
                rules.add(case["expected_rule"])
                self.assertTrue(any(item["rule"] == case["expected_rule"] and item["level"] == "fail" for item in response["response"]["diagnostics"]))
            directory = EVIDENCE / case["label"] / "requirement"
            self.assertEqual(response["business_hashes_after"], {p.relative_to(directory).as_posix(): digest(p.read_bytes()) for p in directory.rglob("*") if p.is_file()})
        self.assertEqual(rules, set(range(1, 13)))
        self.assertFalse(manifest["model_called"])
        self.assertFalse(manifest["release_executed"])

    def test_historical_sources_match_saved_checks(self):
        """封存校验绑定阶段1原提交；当前代码由下方新目录重放，不改旧指纹。"""
        manifest = read_json(EVIDENCE / "run-manifest.json")
        for relative, expected in manifest["source_hashes"].items():
            raw = subprocess.run(["git", "show", f"36b584a:{relative}"], cwd=ROOT,
                                 check=True, capture_output=True).stdout
            self.assertEqual(digest(raw), expected, relative)

    def test_public_driver_replays_and_refuses_existing_output(self):
        """公开测试驱动在新目录重跑真实校验器，并拒绝覆盖已有证据。"""
        spec = importlib.util.spec_from_file_location("prd_format_trial", ROOT / "tests/prd-generator/run_prd_format_checks.py")
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "new-run"
            result = driver.run(output)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["cli_calls"], 15)
            with self.assertRaises(FileExistsError):
                driver.run(output)


if __name__ == "__main__":
    unittest.main()

"""验证阶段5公开CLI留证可重跑、源码可核验且不覆盖旧材料；不调用模型。"""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent


class PrdEditRunsTests(unittest.TestCase):
    """覆盖完整编辑留证驱动，不把合成CLI称为真实模型或人工验收。"""

    def test_public_edit_evidence_and_no_overwrite(self):
        """十个分支真实运行并保留前后指纹，既有输出路径必须拒绝覆盖。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'trial'
            command = [sys.executable, '-I', '-B', str(SCRIPTS / 'run_prd_edits.py'), '--output', str(target)]
            result = subprocess.run(command, cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads((target / 'manifest.json').read_text())
            self.assertEqual(manifest['status'], 'pass')
            self.assertFalse(manifest['model_invocation'])
            self.assertEqual(len(manifest['cases']), 10)
            self.assertTrue(all(case['analysis_unchanged'] and case['result'] == 'pass' for case in manifest['cases']))
            spec = importlib.util.spec_from_file_location('edit_runs_fixture', SCRIPTS / 'prd_fixture_support.py')
            fixture = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(fixture)
            for relative, expected in manifest['source_fingerprints'].items():
                self.assertEqual(expected, fixture.digest((ROOT / 'skill' / relative).read_bytes()))
            before = (target / 'manifest.json').read_bytes()
            refused = subprocess.run(command, cwd=directory, capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(before, (target / 'manifest.json').read_bytes())

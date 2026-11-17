"""验证阶段4公开CLI驱动的证据、隔离重放和不覆盖既有运行；不调用模型或认领人工通过。"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from prd_fixture_support import digest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).with_name('run_prd_sync.py')


class PrdSyncRunsTests(unittest.TestCase):
    """通过公开脚本生成真实同步产物，检查可审计性与明确的执行类型。"""

    def test_help_from_other_directory(self):
        """隔离解释器从任意目录仍能定位测试辅助和生产代码。"""
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), '--help'], cwd='/', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--output', result.stdout)

    def test_public_evidence_and_no_overwrite(self):
        """十四分支保存输入、真实响应及前后文件，源码可核对且重复路径拒绝覆盖。"""
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'new-sync-run'
            result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), '--output', str(output)], cwd='/', capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest_path = output / 'manifest.json'
            manifest_raw = manifest_path.read_bytes()
            manifest = json.loads(manifest_raw)
            self.assertEqual(manifest['status'], 'pass', manifest)
            self.assertFalse(manifest['model_invocation'])
            self.assertEqual(manifest['human_review'], 'pending')
            self.assertEqual(len(manifest['cases']), 14)
            for key, value in manifest['source_fingerprints'].items():
                self.assertEqual(digest((output / 'source-snapshot' / key).read_bytes()), value)
                self.assertEqual(digest((ROOT / 'skill' / key).read_bytes()), value)
            for case in manifest['cases']:
                self.assertEqual(case['status'], 'pass', case)
                folder = output / case['scenario']
                self.assertTrue((folder / 'input/analysis/analysis-result.json').is_file())
                for name in ('check', 'sync', 'validate'):
                    call = json.loads((folder / 'calls' / name / 'response.json').read_text())
                    self.assertIn(call['exit_code'], (0, 1), call)
                    self.assertIn('before', call)
                    self.assertIn('after', call)
                    self.assertTrue(call['command'])
                self.assertTrue((folder / 'calls/sync/before/prd/prd.md').is_file())
                self.assertTrue((folder / 'calls/sync/after/prd/prd.md').is_file())
                self.assertEqual(case['out_of_scope_item_changes'], 0)
                self.assertTrue(case['analysis_unchanged'])
            refused = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), '--output', str(output)], cwd='/', capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(manifest_path.read_bytes(), manifest_raw)


if __name__ == '__main__':
    unittest.main()

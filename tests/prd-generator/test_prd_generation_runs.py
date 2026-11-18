"""验证场景驱动的隔离运行、证据保留及新目录重放。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('run_prd_generation.py')


class GenerationRunsTests(unittest.TestCase):
    """只运行合成数据，不依赖阶段最终评审记录。"""

    def test_help_from_other_directory(self):
        """隔离模式下任意 cwd 的帮助可用。"""
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), '--help'], cwd='/', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--output', result.stdout)

    def test_default_template_positions_glossary_before_scenarios(self):
        """默认模板在范围和场景之间展示稳定术语章标记。"""
        template = SCRIPT.parents[2] / 'skill/prd-generator/templates/prd.md'
        text = template.read_text(encoding='utf-8')
        self.assertLess(text.index('<!-- prd:section scope -->'), text.index('<!-- prd:section glossary -->'))
        self.assertLess(text.index('<!-- prd:section glossary -->'), text.index('<!-- prd:section scenarios -->'))
        self.assertEqual(text.count('<!-- prd:section glossary -->'), 1)

    def test_evidence_and_replay(self):
        """每次使用新目录，保留真实命令、指纹及未完成人工审核标志。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('first', 'replay'):
                output = root / name
                run = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), '--output', str(output)], cwd='/', capture_output=True, text=True, timeout=120)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                manifest = json.loads((output / 'manifest.json').read_text())
                self.assertFalse(manifest['model_run'])
                self.assertTrue(manifest['source_fingerprints'])
                self.assertTrue((output / manifest['source_snapshot'] / 'prd-generator/scripts/write_draft.py').is_file())
                self.assertEqual(manifest['human_review'], 'pending')
                self.assertEqual(manifest['scenarios']['PG-26']['programmatic'], 'pass')
                self.assertEqual(set(manifest['scenarios']), {'PG-01', 'PG-02', 'PG-03', 'PG-04', 'PG-05', 'PG-06', 'PG-07', 'PG-08', 'PG-09', 'PG-10', 'PG-11', 'PG-20', 'PG-21', 'PG-26'})
                for scenario, entry in manifest['scenarios'].items():
                    self.assertEqual(entry['programmatic'], 'pass', (scenario, entry))
                    self.assertEqual(entry['human_review'], 'pending')
                    calls = list((output / scenario).glob('gate.json'))
                    self.assertTrue(calls, scenario)
                    call = json.loads(calls[0].read_text())
                    self.assertTrue(call['command'])
                    self.assertIn('before', call)
                    self.assertIn('after', call)
                for branch in ('with-terms', 'empty-terms'):
                    self.assertTrue((output / 'PG-10' / branch / 'validate.json').is_file())
                self.assertTrue((output / 'PG-20/ui/write.json').is_file())
                self.assertTrue((output / 'PG-08/assign-legacy.json').is_file())
                step = json.loads((output / 'PG-26/write.json').read_text())
                self.assertEqual(set(step), {'command', 'cwd', 'stdout', 'stderr', 'exit_code', 'before', 'after'})
                self.assertTrue((output / 'PG-26/before/analysis/analysis-result.json').is_file())
                self.assertTrue((output / 'PG-26/after/prd/prd.md').is_file())
                refused = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), '--output', str(output)], cwd='/', capture_output=True, text=True)
                self.assertNotEqual(refused.returncode, 0)
                self.assertEqual(json.loads((output / 'manifest.json').read_text()), manifest)


if __name__ == '__main__':
    unittest.main()

"""验证生成门禁、上游降级及只读 CLI 边界。"""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from prd_fixture_support import make_workspace, read_json, write_json

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill/prd-generator/scripts/check_gate.py"


class GateTests(unittest.TestCase):
    """门禁使用合成分析，不能替代真实需求评审。"""

    @classmethod
    def setUpClass(cls):
        """加载门禁模块；路径或安装错误直接抛出。"""
        spec = importlib.util.spec_from_file_location("gate_test", SCRIPT)
        cls.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gate)

    def setUp(self):
        """创建独立合成工作区，返回值为空；文件错误直接抛出。"""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_workspace(Path(self.tmp.name) / "req")

    def update_analysis(self, change):
        """对分析执行 change 并保存；回调或文件异常原样抛出。"""
        path = self.root / "analysis/analysis-result.json"
        data = read_json(path)
        change(data)
        write_json(path, data)

    def test_ready_and_readonly_cli(self):
        """正式就绪通过，任意 cwd 执行 CLI 不改变任何文件。"""
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.gate.check_gate(self.root)
        self.assertEqual((result['status'], result['allowed'], result['draft_kind']), ('pass', True, 'formal_draft'))
        self.assertEqual(set(result['uncovered_analysis']), {'value_assessment', 'technical_feasibility', 'impact_analysis'})
        cli = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), str(self.root)], cwd=self.tmp.name, capture_output=True, text=True)
        self.assertEqual(cli.returncode, 0, cli.stderr + cli.stdout)
        self.assertEqual(json.loads(cli.stdout), result)
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_missing_invalid_and_installation_failure(self):
        """PG01/02 缺失、无效 JSON、上游必填错误及安装故障均拒绝。"""
        path = self.root / 'analysis/analysis-result.json'
        original = path.read_bytes()
        path.rename(path.with_suffix('.bak'))
        self.assertFalse(self.gate.check_gate(self.root)['allowed'])
        path.write_text('{')
        self.assertEqual(self.gate.check_gate(self.root)['status'], 'fail')
        path.write_bytes(original)
        self.update_analysis(lambda d: d.pop('requirements'))
        self.assertFalse(self.gate.check_gate(self.root)['allowed'])
        with patch.object(self.gate, '_validator', side_effect=FileNotFoundError('broken installation')):
            self.assertEqual(self.gate.check_gate(self.root)['status'], 'fail')

    def test_stale_priority_and_explicit_override(self):
        """PG03 过期优先且必须显式允许，即使缺可选来源仍告警。"""
        self.update_analysis(lambda d: d['meta'].update(analysis_status='stale'))
        (self.root / 'analysis/source-manifest.json').rename(self.root / 'analysis/source-backup.json')
        denied = self.gate.check_gate(self.root)
        self.assertEqual((denied['status'], denied['allowed'], denied['draft_kind']), ('warning', False, 'stale_draft'))
        accepted = self.gate.check_gate(self.root, allow_stale=True)
        self.assertTrue(accepted['allowed'])
        self.assertTrue(any('过期' in d['message'] for d in accepted['diagnostics']))
        cli = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), str(self.root), '--allow-stale'], capture_output=True, text=True)
        self.assertEqual(cli.returncode, 1)
        self.assertTrue(json.loads(cli.stdout)['allowed'])

    def test_common_version_and_missing_manifest(self):
        """首次没有 prd 块可通过，旧整数版本和缺 common 拒绝。"""
        path = self.root / 'requirement.json'
        data = read_json(path)
        data.pop('prd')
        write_json(path, data)
        self.assertIsNone(self.gate.check_gate(self.root)['base_prd_version'])
        self.assertTrue(self.gate.check_gate(self.root)['allowed'])
        data['prd'] = {'version': 1}
        write_json(path, data)
        self.assertFalse(self.gate.check_gate(self.root)['allowed'])
        data.pop('common')
        write_json(path, data)
        self.assertEqual(self.gate.check_gate(self.root)['status'], 'fail')

    def test_readiness_mappings(self):
        """三种就绪度映射对应草稿等级，不跳过上游校验。"""
        for readiness, kind in [('not_ready', 'risk_draft'), ('conditionally_ready', 'conditional_draft'), ('ready_for_document', 'formal_draft')]:
            with self.subTest(readiness=readiness):
                self.update_analysis(lambda d: d['meta'].update(readiness=readiness))
                result = self.gate.check_gate(self.root)
                self.assertEqual(result['draft_kind'], kind, result)

    def test_missing_manifest_keeps_source_requirement(self):
        """来源清单降级仅跳过清单依赖项，不能让无来源的有效条目变合法。"""
        self.update_analysis(lambda data: data['requirements']['functional_requirements'][0].update(sources=[]))
        self.assertFalse(self.gate.check_gate(self.root)['allowed'])
        (self.root / 'analysis/source-manifest.json').rename(self.root / 'analysis/source-backup.json')
        result = self.gate.check_gate(self.root)
        self.assertEqual(result['status'], 'fail', result)
        self.assertFalse(result['allowed'])
        self.assertTrue(any('至少需要一个来源' in issue['message'] for issue in result['diagnostics']))

    def test_missing_manifest_keeps_history_state_consistency(self):
        """历史依据声明stale不能因清单缺省继续冒充ready的正式草稿。"""
        self.update_analysis(lambda data: data.update(context={'history_review': {'status': 'stale', 'source_ids': [], 'reason': '合成历史依据变化，尚未重新评估'}}))
        (self.root / 'analysis/source-manifest.json').rename(self.root / 'analysis/source-backup.json')
        result = self.gate.check_gate(self.root)
        self.assertEqual(result['status'], 'fail', result)
        self.assertFalse(result['allowed'])
        self.assertTrue(any('历史依据已变化' in issue['message'] for issue in result['diagnostics']), result)

    def test_parallel_install(self):
        """技能并列安装时从工作目录之外读取自己的脚本与 schema。"""
        install = Path(self.tmp.name) / 'install'
        shutil.copytree(ROOT / 'skill/prd-generator', install / 'prd-generator')
        shutil.copytree(ROOT / 'skill/requirement-analyst', install / 'requirement-analyst')
        cli = subprocess.run([sys.executable, '-I', '-B', str(install / 'prd-generator/scripts/check_gate.py'), str(self.root)], cwd=self.tmp.name, capture_output=True, text=True)
        self.assertEqual(cli.returncode, 0, cli.stderr + cli.stdout)
        self.assertTrue(json.loads(cli.stdout)['allowed'])


if __name__ == '__main__':
    unittest.main()

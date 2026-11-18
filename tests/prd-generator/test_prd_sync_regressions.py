"""回归独立复核确认的章节越界、旧键碰撞和真实双进程交接竞争；不修改历史证据。"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch as mock_patch

from prd_fixture_support import block, read_json, refresh_hash, write_json
from prd_sync_support import (ROOT, add_gap_fixture, advance_analysis, load_script, make_sync_workspace,
                              mapping_patch, refresh_section_sources, replace_section, row, section_text, snapshot)


class PrdSyncRegressionTests(unittest.TestCase):
    """用可复现输入检验确定性边界，不以自然语言字符串断言代替业务语义评审。"""

    def setUp(self):
        """创建私有临时旧稿与当前生产入口，测试结束由临时目录库清理。"""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = make_sync_workspace(self.base / 'requirement')
        self.writer = load_script('write_draft')
        self.body = (self.root / 'prd/prd.md').read_text()
        self.count = 0

    def save(self, **kwargs):
        """按当前读时版本保存同步候选并返回响应；kwargs覆盖独立候选材料，不吞实现错误。"""
        self.count += 1
        return self.writer.write_draft(self.root, sync=True, patch=kwargs.pop('patch', mapping_patch(self.root)),
                body=kwargs.pop('body', self.body), candidate_dir=self.base / f'candidate-{self.count}', **kwargs)

    def test_unchanged_scope_cannot_be_rewritten(self):
        """回归：仅改查询时不得顺带把“本期不含支付”偷换成“本期包含支付”。"""
        analysis = read_json(self.root / 'analysis/analysis-result.json')
        analysis['requirements']['scope']['out_of_scope'].append({**deepcopy(analysis['requirements']['functional_requirements'][0]), 'id': 'FR-3', 'content': '本期不含支付功能'})
        write_json(self.root / 'analysis/analysis-result.json', analysis)
        self.body = replace_section(self.body, 'scope', '本期不含支付功能；依据 SYNTHETIC-PRD/FR-3。')
        (self.root / 'prd/prd.md').write_text(self.body)
        refresh_hash(self.root)
        refresh_section_sources(self.root)
        advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'][0].update(content='合成条件查询功能，不代表真实业务'))
        before = snapshot(self.root)
        result = self.save(body=self.body.replace('合成查询', '合成条件查询').replace('本期不含支付功能', '本期包含支付功能'))
        self.assertEqual(result['status'], 'fail', result)
        self.assertTrue(any('scope' in issue['message'] for issue in result['diagnostics']))
        self.assertEqual(before, snapshot(self.root))

    def test_only_glossary_changes_when_terms_are_added_updated_or_removed(self):
        """新增、更新和移除可选术语章不开放附录改写，也不放行未标记正文。"""
        trace_path = self.root / 'prd/prd-trace.json'
        scenario_marker = '<!-- prd:section scenarios -->'
        current = ''
        for terms in (['查询窗口：查询可用时段。'], ['查询窗口：仅工作日的查询时段。'], []):
            with self.subTest(terms=terms):
                advance_analysis(self.root, lambda a: a.setdefault('context', {}).update(domain_terms=terms))
                before = read_json(trace_path)
                comparison = load_script('check_sync').check_sync(self.root)
                self.assertEqual(comparison['status'], 'pass', comparison)
                self.assertEqual({s['section'] for s in comparison['sections'] if s['category'] == 'modified'}, {'glossary'})
                next_block = block('section', 'glossary', '# 术语\n- ' + terms[0]) + '\n\n' if terms else ''
                candidate = self.body.replace(current + scenario_marker, next_block + scenario_marker, 1)
                guarded = snapshot(self.root)
                for invalid in (replace_section(candidate, 'appendix', '无关改写'), candidate + '\n游离的新规则\n'):
                    refused = self.save(body=invalid)
                    self.assertEqual(refused['status'], 'fail', refused)
                    self.assertEqual(snapshot(self.root), guarded)
                saved = self.save(body=candidate)
                self.assertEqual(saved['status'], 'pass', saved)
                self.body = (self.root / 'prd/prd.md').read_text(encoding='utf-8')
                self.assertEqual('<!-- prd:section glossary -->' in self.body, bool(terms))
                self.assertEqual(section_text(self.body, 'appendix').strip(), 'SRC-1')
                after = read_json(trace_path)
                self.assertEqual(before['items'], after['items'])
                self.assertEqual(before['meta']['section_source_digests']['appendix'], after['meta']['section_source_digests']['appendix'])
                current = next_block

    def test_new_function_in_wrong_section_refused(self):
        """回归：新增功能不能以合法编号藏到业务规则章节并被宣布同步完成。"""
        advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'].append({**deepcopy(a['requirements']['functional_requirements'][0]), 'id': 'FR-3', 'content': '新增统计功能'}))
        patch = mapping_patch(self.root, [{'mapping_key': 'new-statistics', 'kind': 'functional_requirement', 'analysis_refs': ['SYNTHETIC-PRD/FR-3']}])
        body = replace_section(self.body, 'business_rules', '| 功能 | 分析来源 |\n| --- | --- |\n' + row('PRD-FR-003', '新增统计功能', 'SYNTHETIC-PRD/FR-3'))
        before = snapshot(self.root)
        result = self.save(body=body, patch=patch)
        self.assertEqual(result['status'], 'fail', result)
        self.assertEqual(before, snapshot(self.root))

    def test_acceptance_can_attach_only_to_explicit_function(self):
        """章节归属保护保留规格4.4允许的显式AC挂靠功能，不误拦截合法模板组织。"""
        analysis = advance_analysis(self.root, lambda a: a['requirements']['acceptance_criteria'].append({**deepcopy(a['requirements']['functional_requirements'][0]), 'id': 'AC-1', 'content': '查询只返回条件匹配记录', 'related_ids': ['FR-1']}))
        patch = mapping_patch(self.root, [{'mapping_key': 'attached-ac', 'kind': 'acceptance_criterion', 'analysis_refs': ['SYNTHETIC-PRD/AC-1']}])
        candidate = load_script('assign_ids').allocate_ids(patch, analysis, read_json(self.root / 'requirement.json'), previous_trace=read_json(self.root / 'prd/prd-trace.json'), version='0.2')
        body = replace_section(self.body, 'functional_requirements', section_text(self.body, 'functional_requirements') + '\n' + row(candidate['items'][-1]['prd_id'], '查询只返回条件匹配记录', 'SYNTHETIC-PRD/AC-1'))
        result = self.save(body=body, patch=patch)
        self.assertNotEqual(result['status'], 'fail', result)
        self.assertEqual(load_script('validate_prd').validate_prd(self.root)['status'], 'pass')

    def test_generated_legacy_key_avoids_real_mapping_keys(self):
        """回归：合法既有键legacy:PRD-FR-001不能与旧无键条目的自动补键碰撞。"""
        trace = read_json(self.root / 'prd/prd-trace.json')
        trace['items'][0].pop('mapping_key')
        trace['items'][1]['mapping_key'] = 'legacy:PRD-FR-001'
        write_json(self.root / 'prd/prd-trace.json', trace)
        advance_analysis(self.root)
        result = self.save()
        self.assertNotEqual(result['status'], 'fail', result)
        final = read_json(self.root / 'prd/prd-trace.json')['items']
        self.assertEqual([item['prd_id'] for item in final], ['PRD-FR-001', 'PRD-FR-002'])
        self.assertNotEqual(final[0]['mapping_key'], final[1]['mapping_key'])
        self.assertEqual(final[1]['mapping_key'], 'legacy:PRD-FR-001')

    def test_explicit_new_source_can_enrich_stable_mapping(self):
        """多来源补丁并入新增依据仍保留旧编号，并记为修改而非误判未变拒绝合法定向更新。"""
        advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'].append({**deepcopy(a['requirements']['functional_requirements'][0]), 'id': 'FR-3', 'content': '查询结果附带统计数'}))
        patch = mapping_patch(self.root, [{'mapping_key': 'synthetic-query', 'kind': 'functional_requirement', 'analysis_refs': ['SYNTHETIC-PRD/FR-3', 'SYNTHETIC-PRD/FR-1']}])
        text = self.body.replace('合成查询功能，不代表真实业务；分析来源 SYNTHETIC-PRD/FR-1', '合成查询结果附带统计数，不代表真实业务；分析来源 SYNTHETIC-PRD/FR-1、SYNTHETIC-PRD/FR-3')
        result = self.save(body=text, patch=patch)
        self.assertNotEqual(result['status'], 'fail', result)
        trace = read_json(self.root / 'prd/prd-trace.json')
        self.assertEqual(len(trace['items']), 2)
        self.assertEqual(trace['items'][0]['prd_id'], 'PRD-FR-001')
        self.assertEqual(trace['items'][0]['analysis_refs'], ['SYNTHETIC-PRD/FR-1', 'SYNTHETIC-PRD/FR-3'])
        event = json.loads((self.root / 'prd/prd-events.jsonl').read_text().splitlines()[-1])
        self.assertEqual(event['affected_prd_ids'], ['PRD-FR-001'])
        self.assertIn('修改：PRD-FR-001', event['summary'])

    def test_legacy_missing_section_evidence_is_explicit_warning(self):
        """兼容旧trace时不伪造旧章节摘要；明确警告须人工核对，成功后建立新依据。"""
        trace = read_json(self.root / 'prd/prd-trace.json')
        trace['meta'].pop('section_source_digests')
        write_json(self.root / 'prd/prd-trace.json', trace)
        advance_analysis(self.root)
        result = self.save()
        self.assertEqual(result['status'], 'warning', result)
        self.assertTrue(any('章节依据证据' in issue['message'] for issue in result['diagnostics']))
        self.assertIn('旧稿章节依据不足', (self.root / 'prd/prd.md').read_text())
        self.assertTrue(read_json(self.root / 'prd/prd-trace.json')['meta']['section_source_digests'])

    def test_explicit_old_analysis_must_match_baseline(self):
        """旧分析须匹配旧基准修订，不能拿当前分析补成“旧证据”。"""
        trace = read_json(self.root / 'prd/prd-trace.json')
        trace['meta'].pop('section_source_digests')
        write_json(self.root / 'prd/prd-trace.json', trace)
        old = self.base / 'old/analysis-result.json'
        write_json(old, read_json(self.root / 'analysis/analysis-result.json'))
        write_json(old.with_name('source-manifest.json'), read_json(self.root / 'analysis/source-manifest.json'))
        advance_analysis(self.root)
        bad = self.base / 'bad/analysis-result.json'
        write_json(bad, read_json(self.root / 'analysis/analysis-result.json'))
        before = snapshot(self.root)
        self.assertEqual(self.save(previous_analysis=bad)['status'], 'fail')
        self.assertEqual(before, snapshot(self.root))
        result = self.save(previous_analysis=old)
        self.assertEqual(result['status'], 'pass', result)

    def test_optional_section_digest_validation_and_handover_compatibility(self):
        """选填字段结构及已同步依据失配会失败，单独open到handed_over标记不制造失配。"""
        add_gap_fixture(self.root, gap_status='open')
        gaps = read_json(self.root / 'prd/gap-requests.json')
        gaps['requests'][0]['status'] = 'handed_over'
        write_json(self.root / 'prd/gap-requests.json', gaps)
        self.assertNotEqual(load_script('validate_prd').validate_prd(self.root)['status'], 'fail')
        trace = read_json(self.root / 'prd/prd-trace.json')
        trace['meta']['section_source_digests']['scope'] = 'sha256:' + '0' * 64
        write_json(self.root / 'prd/prd-trace.json', trace)
        self.assertEqual(load_script('validate_prd').validate_prd(self.root)['status'], 'fail')

    def test_real_process_handover_serializes_with_generator(self):
        """真实子进程在生成侧替换前竞争同一目录锁；等待后发现快照冲突，不覆盖任一方。"""
        add_gap_fixture(self.root, gap_status='open')
        advance_analysis(self.root)
        gaps = read_json(self.root / 'prd/gap-requests.json')
        gaps['counters']['GAPREQ'] = 2
        gaps['requests'].append({'id': 'GAPREQ-2', 'needed_for': 'business_rules', 'description': '导出权限未分析', 'related_analysis_refs': ['SYNTHETIC-PRD/FR-2'], 'raised_in': '0.2', 'status': 'open'})
        body = replace_section((self.root / 'prd/prd.md').read_text(), 'business_rules', block('gap', 'GAPREQ-2', '待分析补充：导出权限'))
        script = self.base / 'concurrent_marker.py'
        script.write_text('''"""仅在临时夹具中运行分析侧真实标记并观察生成侧目录锁。"""
import fcntl, importlib.util, json, os, sys
from pathlib import Path
root, source = Path(sys.argv[1]), Path(sys.argv[2])
spec = importlib.util.spec_from_file_location('concurrent_analysis', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
path = root / 'prd/gap-requests.json'
snapshot = path.read_bytes()
fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    print('unexpected_unlocked', flush=True)
    fcntl.flock(fd, fcntl.LOCK_UN)
except BlockingIOError:
    print('blocked_on_shared_directory_lock', flush=True)
finally:
    os.close(fd)
try:
    module._mark_handoffs(root, path, snapshot, ['GAPREQ-1'])
    print(json.dumps({'marked': True}), flush=True)
except (module._InputError, ValueError, OSError) as error:
    print(json.dumps({'marked': False, 'error': str(error)}), flush=True)
''')
        child = None
        atomic = self.writer._atomic_write
        def competing(path, raw):
            """在真实原子替换前启动外部标记者，确认其等待目录锁后继续生成侧保存。"""
            nonlocal child
            if path == self.root / 'prd/gap-requests.json':
                child = subprocess.Popen([sys.executable, '-I', '-B', str(script), str(self.root), str(ROOT / 'skill/requirement-analyst/scripts/update_analysis.py')], cwd=self.base, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.assertEqual(child.stdout.readline().strip(), 'blocked_on_shared_directory_lock')
            return atomic(path, raw)
        try:
            with mock_patch.object(self.writer, '_atomic_write', competing):
                result = self.save(body=body, gaps=gaps)
            self.assertNotEqual(result['status'], 'fail', result)
            stdout, stderr = child.communicate(timeout=30)
            self.assertEqual(child.returncode, 0, stderr)
            marker = json.loads(stdout.strip())
            self.assertFalse(marker['marked'], marker)
            self.assertIn('发生变化', marker['error'])
            final = read_json(self.root / 'prd/gap-requests.json')
            self.assertEqual(len(final['requests']), 2)
            self.assertEqual(final['requests'][0]['status'], 'open')
            # 真正重读后重试允许完成交接，且生成侧新增的GAPREQ-2不会丢失。
            definition = importlib.util.spec_from_file_location('retry_updater', ROOT / 'skill/requirement-analyst/scripts/update_analysis.py')
            module = importlib.util.module_from_spec(definition)
            definition.loader.exec_module(module)
            module._mark_handoffs(self.root, self.root / 'prd/gap-requests.json', (self.root / 'prd/gap-requests.json').read_bytes(), ['GAPREQ-1'])
            final = read_json(self.root / 'prd/gap-requests.json')
            self.assertEqual(final['requests'][0]['status'], 'handed_over')
            self.assertEqual(final['requests'][1]['id'], 'GAPREQ-2')
        finally:
            if child is not None and child.poll() is None:
                child.kill()
                child.communicate()


if __name__ == '__main__':
    unittest.main()

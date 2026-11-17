"""验证真实同步保存、最小改写、编号历史、缺口核实及并发恢复；均为隔离合成需求。"""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch as mock_patch

from prd_fixture_support import block, read_json, refresh_hash, write_json
from prd_sync_support import (ROOT, add_gap_fixture, advance_analysis, load_script, make_sync_workspace,
                              mapping_patch, replace_section, row, section_text, snapshot)


class PrdSyncWriteTests(unittest.TestCase):
    """以生产入口检验同步保存边界，不把格式夹具当作模型语义通过。"""

    def setUp(self):
        """创建含未变对照项的隔离旧稿，并加载当前统一写入器；失败不跳过。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = make_sync_workspace(self.base / 'requirement')
        self.writer = load_script('write_draft')
        self.old_text = (self.root / 'prd/prd.md').read_text()
        self.counter = 0

    def save(self, **kwargs):
        """保存当前分析的同步候选并返回响应；kwargs允许覆盖正文/补丁/缺口和测试开关。"""
        self.counter += 1
        return self.writer.write_draft(self.root, sync=kwargs.pop('sync', True), patch=kwargs.pop('patch', mapping_patch(self.root)),
                    body=kwargs.pop('body', self.old_text), candidate_dir=self.base / f'candidate-{self.counter}',
                    generated_at='2026-11-17T04:00:00Z', **kwargs)

    def assert_saved(self, result):
        """断言result是实际完成的同步，并返回新追溯；程序失败抛出断言异常。"""
        self.assertNotEqual(result['status'], 'fail', result)
        self.assertTrue(result['synced'], result)
        self.assertEqual(len(result['written']), 5)
        checked = load_script('validate_prd').validate_prd(self.root)
        self.assertNotEqual(checked['status'], 'fail', checked)
        return read_json(self.root / 'prd/prd-trace.json')

    def test_directed_content_update_and_ownership(self):
        """PG-14修改指定内容并保留未变原字节、编号、common、其他块和整个分析目录。"""
        advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'][0].update(content='合成条件查询功能，不代表真实业务'))
        before = snapshot(self.root)
        body = self.old_text.replace('合成查询', '合成条件查询')
        result = self.save(body=body)
        trace = self.assert_saved(result)
        self.assertEqual(result['version'], '0.2')
        old = self.writer._parsed(self.old_text)['item']['PRD-FR-002']
        text = (self.root / 'prd/prd.md').read_text()
        new = self.writer._parsed(text)['item']['PRD-FR-002']
        self.assertEqual(self.writer._raw_item(self.old_text, old), self.writer._raw_item(text, new))
        self.assertEqual([i['prd_id'] for i in trace['items']], ['PRD-FR-001', 'PRD-FR-002'])
        self.assertEqual([i['introduced_in'] for i in trace['items']], ['0.1', '0.1'])
        after = snapshot(self.root)
        for name in before:
            if name.startswith('analysis/'):
                self.assertEqual(before[name], after[name])
        metadata = read_json(self.root / 'requirement.json')
        self.assertEqual(metadata['common'], json.loads(before['requirement.json'])['common'])
        self.assertEqual(metadata['other_owner'], {'keep': '不能覆盖其他块'})
        self.assertTrue(after['prd/prd-events.jsonl'].startswith(before['prd/prd-events.jsonl']))
        event = json.loads(after['prd/prd-events.jsonl'].splitlines()[-1])
        self.assertEqual(event['change_type'], 'sync')
        self.assertEqual(event['affected_prd_ids'], ['PRD-FR-001'])
        self.assertIn('就绪度', event['summary'])
        self.assertIn('遗留事项', event['summary'])

    def test_revision_only_sync_does_not_rewrite_items(self):
        """PG-13/34只有修订递增或JSON重排时更新信息事件，所有正式条目原字节保持。"""
        analysis = advance_analysis(self.root)
        (self.root / 'analysis/analysis-result.json').write_text(json.dumps(analysis, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
        old_trace = read_json(self.root / 'prd/prd-trace.json')
        self.assert_saved(self.save())
        self.assertEqual(old_trace['items'], read_json(self.root / 'prd/prd-trace.json')['items'])
        text = (self.root / 'prd/prd.md').read_text()
        self.assertEqual(section_text(self.old_text, 'functional_requirements'), section_text(text, 'functional_requirements'))
        self.assertEqual(json.loads((self.root / 'prd/prd-events.jsonl').read_text().splitlines()[-1])['affected_prd_ids'], [])

    def test_unaffected_rewrite_or_remapping_rejected(self):
        """未变条目的润色、定位标记变化和映射篡改均拒绝，不被新版本掩盖。"""
        advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'][0].update(content='合成条件查询功能，不代表真实业务'))
        before = snapshot(self.root)
        for body in (self.old_text.replace('合成导出', '合成下载'), self.old_text.replace('<!-- prd:item PRD-FR-002 -->', '<!--  prd:item PRD-FR-002 -->')):
            result = self.save(body=body)
            self.assertEqual(result['status'], 'fail', result)
            self.assertEqual(before, snapshot(self.root))
            self.assertTrue(Path(result['candidate_dir']).exists())
        patch = mapping_patch(self.root, [{'mapping_key': 'synthetic-export', 'kind': 'functional_requirement', 'analysis_refs': ['SYNTHETIC-PRD/FR-1']}])
        self.assertEqual(self.save(patch=patch)['status'], 'fail')
        self.assertEqual(before, snapshot(self.root))

    def test_withdrawal_then_addition_keeps_high_water(self):
        """PG-15/16废止不删除身份，后续新增递增且不复用旧号或改引入版本。"""
        advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'][0].update(status='withdrawn'))
        rows = section_text(self.old_text, 'functional_requirements').splitlines()
        body = replace_section(self.old_text, 'functional_requirements', '\n'.join(line for line in rows if 'prd:item PRD-FR-001' not in line))
        trace = self.assert_saved(self.save(body=body))
        self.assertEqual(trace['items'][0]['status'], 'abolished')
        self.assertEqual(trace['meta']['counters']['FR'], 2)
        self.old_text = (self.root / 'prd/prd.md').read_text()
        analysis = advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'].append({**deepcopy(a['requirements']['functional_requirements'][1]), 'id': 'FR-3', 'content': '新增合成统计功能'}))
        patch = mapping_patch(self.root, [{'mapping_key': 'new-statistics', 'kind': 'functional_requirement', 'analysis_refs': ['SYNTHETIC-PRD/FR-3']}])
        candidate = load_script('assign_ids').allocate_ids(patch, analysis, read_json(self.root / 'requirement.json'), previous_trace=trace, version='0.3')
        pid = candidate['items'][-1]['prd_id']
        body = replace_section(self.old_text, 'functional_requirements', section_text(self.old_text, 'functional_requirements') + '\n' + row(pid, '新增合成统计功能', 'SYNTHETIC-PRD/FR-3'))
        trace = self.assert_saved(self.save(body=body, patch=patch))
        self.assertEqual(pid, 'PRD-FR-003')
        self.assertEqual([i['introduced_in'] for i in trace['items']], ['0.1', '0.1', '0.3'])
        self.assertEqual(trace['items'][0]['status'], 'abolished')
        self.assertIn('PRD-FR-001', section_text((self.root / 'prd/prd.md').read_text(), 'changes'))

    def test_omitted_new_analysis_mapping_rejected(self):
        """新增有效分析项不能被空补丁静默忽略。"""
        advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'].append({**deepcopy(a['requirements']['functional_requirements'][1]), 'id': 'FR-3'}))
        before = snapshot(self.root)
        self.assertEqual(self.save()['status'], 'fail')
        self.assertEqual(before, snapshot(self.root))

    def test_to_reassess_keeps_uncertainty(self):
        """PG-14待重评来源同步为to_confirm，不能保留确定语气或丢掉待确认标注。"""
        advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'][0].update(status='to_reassess'))
        body = self.old_text.replace('合成查询功能，不代表真实业务；', '合成查询功能，不代表真实业务【待确认】；')
        trace = self.assert_saved(self.save(body=body))
        self.assertEqual(trace['items'][0]['status'], 'to_confirm')

    def test_only_tag_change_updates_marks_and_residuals(self):
        """PG-32正文不变而标签变成推断时，更新适用标注及遗留项，不重编号。"""
        advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'][0].update(tag='inferred'))
        body = self.old_text.replace('合成查询功能，不代表真实业务；', '合成查询功能，不代表真实业务【推断】；')
        body = replace_section(body, 'residuals', block('residual', 'SYNTHETIC-PRD/FR-1', '推断：合成查询功能，不代表真实业务'))
        trace = self.assert_saved(self.save(body=body))
        self.assertEqual(trace['items'][0]['tag'], 'inferred')
        self.assertEqual(trace['items'][0]['prd_id'], 'PRD-FR-001')

    def close_candidate(self, kind='supplied', ref='AC-1'):
        """返回当前缺口的关闭候选与移除占位正文；kind/ref只是测试依据，生产仍须完整校验。"""
        gaps = read_json(self.root / 'prd/gap-requests.json')
        gaps['requests'][0].update(status='closed', resolution={'kind': kind, 'analysis_refs': ['SYNTHETIC-PRD/' + ref], 'reason': '以当前有效分析明确补足或不再需要的依据为准'})
        return gaps, replace_section((self.root / 'prd/prd.md').read_text(), 'acceptance_criteria', '分析结果中无此项')

    def test_gap_supplied_closes_and_preserves_extensions(self):
        """PG-31实际AC补足且唯一问题已答后才关闭，并替换占位、保留历史与扩展。"""
        add_gap_fixture(self.root, question_status='answered')
        analysis = advance_analysis(self.root, lambda a: a['requirements']['acceptance_criteria'].append({**deepcopy(a['requirements']['functional_requirements'][0]), 'id': 'AC-1', 'content': '查询返回与条件匹配的结果', 'related_ids': ['FR-1']}))
        gaps, body = self.close_candidate()
        patch = mapping_patch(self.root, [{'mapping_key': 'query-acceptance', 'kind': 'acceptance_criterion', 'analysis_refs': ['SYNTHETIC-PRD/AC-1']}])
        trace = load_script('assign_ids').allocate_ids(patch, analysis, read_json(self.root / 'requirement.json'), previous_trace=read_json(self.root / 'prd/prd-trace.json'), version='0.2')
        body = replace_section(body, 'acceptance_criteria', '| 验收条件 | 分析来源 |\n| --- | --- |\n' + row(trace['items'][-1]['prd_id'], '查询返回与条件匹配的结果', 'SYNTHETIC-PRD/AC-1'))
        body = replace_section(body, 'residuals', '无适用遗留项')
        self.assert_saved(self.save(body=body, gaps=gaps, patch=patch))
        final = read_json(self.root / 'prd/gap-requests.json')
        self.assertEqual(final['requests'][0]['status'], 'closed')
        self.assertEqual(final['extension'], '封装扩展')
        self.assertEqual(final['requests'][0]['extension'], {'keep': '缺口扩展'})
        self.assertNotIn('待分析补充', (self.root / 'prd/prd.md').read_text())

    def test_not_needed_closes_with_real_scope_basis(self):
        """PG-31不再需要必须引用有效范围依据，不能只写生成器解释。"""
        add_gap_fixture(self.root, question_status='answered')
        advance_analysis(self.root, lambda a: a['requirements']['scope']['out_of_scope'].append({**deepcopy(a['requirements']['functional_requirements'][0]), 'id': 'FR-3', 'content': '本期不做查询验收扩展，该模板项不再需要'}))
        gaps, body = self.close_candidate(kind='not_needed', ref='FR-3')
        body = replace_section(body, 'scope', '本期不含：查询验收扩展；依据 SYNTHETIC-PRD/FR-3。')
        body = replace_section(body, 'residuals', '无适用遗留项')
        self.assert_saved(self.save(body=body, gaps=gaps))

    def test_handed_over_or_answer_without_content_stays_open(self):
        """PG-31保留分支：已交接或只有问题回答不自动关闭缺口，原占位继续可追踪。"""
        add_gap_fixture(self.root)
        advance_analysis(self.root)
        body = (self.root / 'prd/prd.md').read_text()
        self.assert_saved(self.save(body=body))
        self.assertEqual(read_json(self.root / 'prd/gap-requests.json')['requests'][0]['status'], 'handed_over')
        self.old_text = (self.root / 'prd/prd.md').read_text()
        advance_analysis(self.root, lambda a: a['questions'][0].update(status='answered', answer='已经回复，但验收仍未写入分析'))
        self.assert_saved(self.save(body=self.old_text))
        self.assertIn('待分析补充', (self.root / 'prd/prd.md').read_text())
        self.assertEqual(read_json(self.root / 'prd/gap-requests.json')['requests'][0]['status'], 'handed_over')

    def test_invalid_gap_closures_and_identity_edits_refused(self):
        """接收仍open、无效依据、失效依据、非范围的不再需要及改写原缺口均不能保存。"""
        add_gap_fixture(self.root)
        advance_analysis(self.root)
        gaps, body = self.close_candidate(ref='FR-1')
        before = snapshot(self.root)
        self.assertEqual(self.save(body=body, gaps=gaps)['status'], 'fail')
        self.assertEqual(before, snapshot(self.root))
        advance_analysis(self.root, lambda a: a['questions'][0].update(status='answered', answer='仅为合成回答'))
        before = snapshot(self.root)
        for kind, ref in (('supplied', 'AC-999'), ('not_needed', 'FR-1')):
            gaps, body = self.close_candidate(kind=kind, ref=ref)
            self.assertEqual(self.save(body=body, gaps=gaps)['status'], 'fail')
            self.assertEqual(before, snapshot(self.root))
        gaps['requests'][0]['description'] = '借关闭换了另一个问题'
        self.assertEqual(self.save(body=body, gaps=gaps)['status'], 'fail')
        self.assertEqual(before, snapshot(self.root))

    def test_provisional_supply_keeps_assumption_and_residuals(self):
        """PG-31暂定内容补足后可关闭，但AC标注、问题、假设依据和验证方式不能消失。"""
        add_gap_fixture(self.root)
        def provisional(analysis):
            """构造真实可校验的暂定验收分析，返回None；夹具结构错误原样抛出。"""
            analysis['questions'][0].update(status='provisional', priority='P1')
            source = deepcopy(analysis['requirements']['functional_requirements'][0]['sources'])
            analysis['assumptions'].append({'id': 'ASM-1', 'content': '查询验收暂按只返回条件匹配结果', 'tag': 'assumption',
                'status': 'active', 'sources': source, 'related_question': 'Q-1', 'basis': '产品尚待核对验收口径', 'verification': '产品后续核对验收样例'})
            analysis['requirements']['acceptance_criteria'].append({'id': 'AC-1', 'content': '只返回与查询条件匹配的结果',
                'tag': 'assumption', 'status': 'active', 'sources': source, 'related_ids': ['FR-1', 'ASM-1']})
        analysis = advance_analysis(self.root, provisional)
        gaps, body = self.close_candidate(ref='AC-1')
        patch = mapping_patch(self.root, [{'mapping_key': 'provisional-ac', 'kind': 'acceptance_criterion', 'analysis_refs': ['SYNTHETIC-PRD/AC-1']}])
        trace = load_script('assign_ids').allocate_ids(patch, analysis, read_json(self.root / 'requirement.json'), previous_trace=read_json(self.root / 'prd/prd-trace.json'), version='0.2')
        body = replace_section(body, 'acceptance_criteria', '| 验收条件 | 分析来源 |\n| --- | --- |\n' + row(trace['items'][-1]['prd_id'], '只返回与查询条件匹配的结果', 'SYNTHETIC-PRD/AC-1', '【暂定】'))
        body = replace_section(body, 'residuals', block('residual', 'SYNTHETIC-PRD/Q-1', '查询验收如何判定？ask_product，暂定口径待验证') + '\n' +
                               block('residual', 'SYNTHETIC-PRD/ASM-1', '查询验收暂按只返回条件匹配结果；产品尚待核对验收口径；产品后续核对验收样例'))
        self.assert_saved(self.save(body=body, patch=patch, gaps=gaps))
        final = (self.root / 'prd/prd.md').read_text()
        self.assertIn('【暂定】', final)
        self.assertIn('产品后续核对验收样例', final)
        self.assertEqual(read_json(self.root / 'prd/gap-requests.json')['requests'][0]['status'], 'closed')

    def test_missing_or_ambiguous_receiver_cannot_close(self):
        """缺失或重复接收对应关系时上游拒绝并保留原缺口，不猜配对、不修改分析。"""
        add_gap_fixture(self.root, question_status='answered')
        advance_analysis(self.root)
        original = read_json(self.root / 'analysis/analysis-result.json')
        for questions in ([], [*original['questions'], {**original['questions'][0], 'id': 'Q-2'}]):
            analysis = deepcopy(original)
            analysis['questions'] = questions
            write_json(self.root / 'analysis/analysis-result.json', analysis)
            before = snapshot(self.root)
            gaps, body = self.close_candidate(ref='FR-1')
            self.assertEqual(self.save(body=body, gaps=gaps)['status'], 'fail')
            self.assertEqual(before, snapshot(self.root))

    def test_unreadable_auxiliaries_degrade_without_writing_analysis(self):
        """辅助清单和事件缺失仍可按权威分析同步，信息记录降级并显示全部警告。"""
        advance_analysis(self.root)
        # 临时目录中文件移动模拟不可读，不删除或覆盖任何历史资料。
        for name in ('source-manifest.json', 'analysis-events.jsonl'):
            (self.root / 'analysis' / name).rename(self.base / ('saved-' + name))
        before = snapshot(self.root)
        result = self.save()
        self.assert_saved(result)
        self.assertEqual(result['status'], 'warning')
        text = (self.root / 'prd/prd.md').read_text()
        self.assertIn('变更原因说明降级', text)
        self.assertIn('来源名称降级', text)
        self.assertEqual({k: v for k, v in before.items() if k.startswith('analysis/')}, {k: v for k, v in snapshot(self.root).items() if k.startswith('analysis/')})

    def test_conflict_and_manual_change_do_not_overwrite(self):
        """写前版本冲突或未处理手改拒写；不靠重算摘要接纳未知正文。"""
        advance_analysis(self.root)
        patch = mapping_patch(self.root)
        patch['base_prd_version'] = '0.9'
        before = snapshot(self.root)
        self.assertEqual(self.save(patch=patch)['status'], 'fail')
        self.assertEqual(before, snapshot(self.root))
        (self.root / 'prd/prd.md').write_text(self.old_text + '\n手工新增规则\n')
        before = snapshot(self.root)
        self.assertEqual(self.save()['status'], 'fail')
        self.assertEqual(before, snapshot(self.root))

    def test_concurrent_gap_handover_cannot_be_overwritten(self):
        """分析侧在读取后标记handed_over时，生成侧拒绝覆盖而非把其重置成open。"""
        add_gap_fixture(self.root, gap_status='open')
        advance_analysis(self.root)
        body = (self.root / 'prd/prd.md').read_text()
        original = self.writer._check_guards
        def concurrent(guards):
            """模拟唯一接收成功后的并发标记；返回原守卫结果，错误原样抛出。"""
            gaps = read_json(self.root / 'prd/gap-requests.json')
            gaps['requests'][0]['status'] = 'handed_over'
            write_json(self.root / 'prd/gap-requests.json', gaps)
            return original(guards)
        with mock_patch.object(self.writer, '_check_guards', concurrent):
            result = self.save(body=body)
        self.assertEqual(result['status'], 'fail', result)
        self.assertEqual(read_json(self.root / 'prd/gap-requests.json')['requests'][0]['status'], 'handed_over')
        self.assertEqual(read_json(self.root / 'requirement.json')['prd']['version'], '0.1')

    def test_interruption_recovers_once_without_duplicate_sync_event(self):
        """复用事务恢复同步中断，恢复不重复追加sync事件，也不产生新的版本。"""
        advance_analysis(self.root)
        atomic = self.writer._atomic_write
        calls = 0
        def fail_second_file(path, raw):
            """在journal与正文保存后模拟I/O中断；其他写入调用原实现并返回其结果。"""
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError('合成同步写中断')
            return atomic(path, raw)
        with mock_patch.object(self.writer, '_atomic_write', fail_second_file):
            failed = self.save()
        self.assertEqual(failed['status'], 'fail', failed)
        self.assertTrue(failed['recovery_required'])
        recovered = self.writer.recover_draft(self.root)
        self.assert_saved(recovered)
        self.assertEqual(recovered['version'], '0.2')
        events = [json.loads(line) for line in (self.root / 'prd/prd-events.jsonl').read_text().splitlines()]
        self.assertEqual(sum(e['change_type'] == 'sync' for e in events), 1)

    def test_stale_requires_actual_opt_in(self):
        """过期优先于就绪度，未坚持拒写，坚持后只保存stale_draft。"""
        advance_analysis(self.root, lambda a: a['meta'].update(analysis_status='stale'))
        before = snapshot(self.root)
        refused = self.save()
        self.assertFalse(refused.get('generated', False))
        self.assertEqual(before, snapshot(self.root))
        result = self.save(allow_stale=True)
        self.assert_saved(result)
        self.assertEqual(result['draft_kind'], 'stale_draft')

    def test_default_entry_or_no_pending_or_deprecated_refused(self):
        """默认首稿入口不绕过同步，无待同步变化及废弃状态不能用同步编辑。"""
        self.assertEqual(self.save()['status'], 'fail')
        advance_analysis(self.root)
        before = snapshot(self.root)
        self.assertEqual(self.save(sync=False)['status'], 'fail')
        self.assertEqual(before, snapshot(self.root))
        metadata = read_json(self.root / 'requirement.json')
        metadata['prd']['status'] = 'deprecated'
        write_json(self.root / 'requirement.json', metadata)
        self.assertEqual(self.save()['status'], 'fail')

    def test_public_cli_uses_explicit_sync_mode(self):
        """公开CLI在隔离调用目录下保存同步，并返回单个JSON及真实三态退出码。"""
        advance_analysis(self.root)
        patch_path = write_json(self.base / 'patch.json', mapping_patch(self.root))
        body_path = self.base / 'body.md'
        body_path.write_text(self.old_text)
        process = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'skill/prd-generator/scripts/write_draft.py'), str(self.root), '--sync', '--patch', str(patch_path), '--body', str(body_path), '--candidate-dir', str(self.base / 'cli-candidate')], cwd=self.base, capture_output=True, text=True)
        result = json.loads(process.stdout)
        self.assertIn(process.returncode, (0, 1), process.stderr + process.stdout)
        self.assert_saved(result)


if __name__ == '__main__':
    unittest.main()

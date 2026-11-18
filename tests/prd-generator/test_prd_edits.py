"""验证编辑保存、真实差异比较、手改检测与坚持保留的事务边界；语义结论不由夹具代签。"""

from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from prd_fixture_support import block, digest, make_workspace, read_json, write_json


SCRIPTS = Path(__file__).resolve().parents[2] / 'skill/prd-generator/scripts'


def load(name):
    """从可信生产目录加载 name 并返回模块；安装和导入错误原样抛出。"""
    spec = importlib.util.spec_from_file_location('edit_test_' + name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrdEditTests(unittest.TestCase):
    """覆盖已有未发布稿的编辑与恢复，不把结构通过当作自然语言分流证明。"""

    @classmethod
    def setUpClass(cls):
        """加载真实生产入口，导入故障不跳过。"""
        cls.writer = load('write_draft')
        cls.renderer = cls.writer._module('render_info')
        cls.validator = cls.writer._module('validate_prd')

    def setUp(self):
        """用真实首稿入口建立独立工作稿；合成数据只为程序边界测试。"""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        fixture = make_workspace(self.base / 'fixture')
        self.root = self.base / 'requirement'
        for name in ('analysis-result.json', 'source-manifest.json'):
            write_json(self.root / 'analysis' / name, read_json(fixture / 'analysis' / name))
        metadata = read_json(fixture / 'requirement.json')
        metadata.pop('prd')
        metadata['foreign'] = {'must': 'remain'}
        write_json(self.root / 'requirement.json', metadata)
        self.numbering = {'patch_version': '1.0', 'requirement_id': 'SYNTHETIC-PRD', 'base_prd_version': None,
                          'base_analysis_revision': 1, 'items': [{'mapping_key': 'synthetic-query', 'kind': 'functional_requirement',
                                                              'analysis_refs': ['SYNTHETIC-PRD/FR-1']}]}
        result = self.writer.write_draft(self.root, patch=self.numbering, body=(fixture / 'prd/prd.md').read_bytes().decode(),
                                       candidate_dir=self.base / 'initial', generated_at='2026-11-17T00:00:00Z')
        self.assertNotEqual(result['status'], 'fail', result)
        self.counter = 0

    def text(self):
        """返回当前正文，保留原始换行；读取或编码错误使测试失败。"""
        return (self.root / 'prd/prd.md').read_bytes().decode('utf-8')

    def snapshot(self):
        """返回正式目录全部文件原始字节，用于归属及拒写断言；读取错误原样抛出。"""
        return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}

    def edit(self, mode='layout', **kwargs):
        """提交绑定真实读时版本及摘要的编辑，返回生产结果；每次使用不同候选目录。"""
        self.counter += 1
        metadata = read_json(self.root / 'requirement.json')
        analysis = read_json(self.root / 'analysis/analysis-result.json')
        values = {'mode': mode, 'base_prd_version': metadata['prd']['version'],
                  'base_analysis_revision': analysis['meta']['analysis_revision'],
                  'base_content_hash': digest((self.root / 'prd/prd.md').read_bytes()),
                  'summary': '合成测试：已核对指定差异', 'candidate_dir': self.base / f'edit-{self.counter}',
                  'generated_at': '2026-11-17T01:00:00Z'}
        if mode == 'layout':
            values.update(body=self.text().replace('合成查询', '**合成查询**'), meaning_reviewed=True)
        values.update(kwargs)
        return self.writer.edit_draft(self.root, **values)

    def manual(self, *, scope=False):
        """模拟用户已手工改变业务正文，返回旧稿；不主动更新摘要或伪造分析。"""
        previous = self.text()
        current = previous.replace('合成查询功能', '查询并导出全部数据功能') if not scope else previous.replace(
            '<!-- prd:section scope -->\n分析结果中无此项', '<!-- prd:section scope -->\n支持跨租户导出')
        (self.root / 'prd/prd.md').write_bytes(current.encode())
        return previous

    def marked(self, *, scope=False):
        """返回只添加不一致标注与遗留说明的候选；保持原遗留文字和用户手改内容。"""
        text = self.text()
        if scope:
            text = text.replace('<!-- prd:section scope -->', '<!-- prd:section scope -->\n【与分析不一致】', 1)
            ref = 'SYNTHETIC-PRD/prd/sections/scope'
        else:
            text = text.replace('PRD-FR-001：', 'PRD-FR-001：【与分析不一致】', 1)
            ref = 'SYNTHETIC-PRD/PRD-FR-001'
        parsed = self.writer._parsed(text)
        residual = parsed['section']['residuals']
        note = block('residual', ref, '【与分析不一致】差异：用户扩大导出范围；建议回交分析确认后再同步。')
        return text[:residual['end']] + '\n' + note + '\n' + text[residual['end']:]

    def test_generation_establishes_exact_baseline(self):
        """首稿正文、比较基准和原始字节摘要在同一事务中一致。"""
        trace = read_json(self.root / 'prd/prd-trace.json')
        self.assertEqual(trace['meta']['content_baseline'], self.text())
        self.assertEqual(trace['meta']['content_hash'], digest(self.text().encode()))

    def test_unchanged_inspection_is_read_only(self):
        """只读查看不会写事件、版本或其他文件，不误报未改稿。"""
        before = self.snapshot()
        response = self.writer.inspect_edits(self.root)
        self.assertNotEqual(response['status'], 'fail', response)
        self.assertFalse(response['changed'])
        self.assertEqual(response['diff'], '')
        self.assertEqual(response['written'], [])
        self.assertEqual(before, self.snapshot())

    def test_full_diff_includes_non_numbered_scope(self):
        """实际差异比较覆盖非编号范围，不只发现正式条目变化。"""
        self.manual(scope=True)
        before = self.snapshot()
        response = self.writer.inspect_edits(self.root)
        self.assertTrue(response['changed'], response)
        self.assertTrue(response['baseline_available'])
        self.assertIn('支持跨租户导出', response['diff'])
        self.assertIn('scope', response['affected_sections'])
        self.assertEqual(response['affected_prd_ids'], [])
        self.assertEqual(before, self.snapshot())

    def test_layout_increments_version_and_preserves_identity(self):
        """排版后次版本递增、摘要一致，编号来源及分析和其他元数据块保持。"""
        before = self.snapshot()
        old_trace = read_json(self.root / 'prd/prd-trace.json')
        response = self.edit()
        self.assertNotEqual(response['status'], 'fail', response)
        self.assertTrue(response['edited'])
        self.assertEqual(response['version'], '0.2')
        trace = read_json(self.root / 'prd/prd-trace.json')
        self.assertEqual(trace['items'], old_trace['items'])
        for key in ('counters', 'section_source_digests', 'draft_kind', 'generated_under_readiness'):
            self.assertEqual(trace['meta'][key], old_trace['meta'][key])
        self.assertEqual(trace['meta']['content_baseline'], self.text())
        self.assertEqual(trace['meta']['content_hash'], digest(self.text().encode()))
        metadata = read_json(self.root / 'requirement.json')
        self.assertEqual(metadata['foreign'], {'must': 'remain'})
        for name in ('analysis/analysis-result.json', 'analysis/source-manifest.json', 'prd/gap-requests.json'):
            self.assertEqual((self.root / name).read_bytes(), before[name])
        self.assertEqual(read_json(self.root / 'requirement.json')['prd']['based_on_analysis_revision'], 1)
        import json
        self.assertEqual(json.loads((self.root / 'prd/prd-events.jsonl').read_text().splitlines()[-1])['change_type'], 'layout_edit')

    def test_layout_requires_explicit_semantic_review(self):
        """未经逐差异核对不能仅以“排版”名义刷新摘要。"""
        before = self.snapshot()
        response = self.edit(meaning_reviewed=False)
        self.assertEqual(response['status'], 'fail', response)
        self.assertEqual(before, self.snapshot())

    def test_layout_keeps_stable_ids_and_references(self):
        """即使声明已语义核对，改编号或删引用仍拒写。"""
        before = self.snapshot()
        for text in (self.text().replace('PRD-FR-001', 'PRD-FR-002'),
                     self.text().replace('SYNTHETIC-PRD/FR-1', 'SYNTHETIC-PRD/FR-2')):
            response = self.edit(body=text)
            self.assertEqual(response['status'], 'fail', response)
            self.assertEqual(before, self.snapshot())

    def test_manual_layout_only_after_comparison(self):
        """用户先改排版后，仍需取得真实差异及语义核对才保存并刷新摘要。"""
        (self.root / 'prd/prd.md').write_bytes(self.text().replace('合成查询', '**合成查询**').encode())
        observed = self.writer.inspect_edits(self.root)
        self.assertTrue(observed['changed'])
        self.assertIn('合成查询', observed['diff'])
        response = self.edit(body=self.text())
        self.assertNotEqual(response['status'], 'fail', response)
        self.assertFalse(self.writer.inspect_edits(self.root)['changed'])

    def test_detection_only_appends_event_and_is_idempotent(self):
        """显式检测保留手改和旧摘要，不升版本；重试同一手改不重复事件。"""
        self.manual()
        before = self.snapshot()
        response = self.edit('detect')
        self.assertEqual(response['status'], 'warning', response)
        self.assertEqual(response['version'], '0.1')
        self.assertEqual(response['written'], ['prd/prd-events.jsonl'])
        for name, raw in before.items():
            if name != 'prd/prd-events.jsonl':
                self.assertEqual((self.root / name).read_bytes(), raw)
        detected = self.snapshot()
        again = self.edit('detect')
        self.assertTrue(again['already_recorded'], again)
        self.assertEqual(again['written'], [])
        self.assertEqual(detected, self.snapshot())
        self.assertTrue(self.writer.inspect_edits(self.root)['changed'])

    def test_detection_does_not_invent_manual_changes(self):
        """未变化正文没有手改事件，也不会因检测而增加版本。"""
        before = self.snapshot()
        response = self.edit('detect')
        self.assertEqual(response['status'], 'fail', response)
        self.assertEqual(before, self.snapshot())

    def test_keep_requires_real_user_confirmation(self):
        """未收到坚持保留的回答时不提前执行标注保存分支。"""
        self.manual()
        before = self.snapshot()
        response = self.edit('keep', body=self.marked(), keep_confirmed=False)
        self.assertEqual(response['status'], 'fail', response)
        self.assertEqual(before, self.snapshot())

    def test_keep_pairs_item_marker_and_residual_and_blocks_release(self):
        """用户坚持后保留真实手改，成对标注、升一次次版本，摘要更新但仍不得发布。"""
        self.manual()
        self.assertNotEqual(self.edit('detect')['status'], 'fail')
        response = self.edit('keep', body=self.marked(), keep_confirmed=True)
        self.assertEqual(response['status'], 'warning', response)
        self.assertEqual(response['version'], '0.2')
        self.assertIn('查询并导出全部数据功能', self.text())
        self.assertIn('【与分析不一致】', self.text())
        self.assertNotIn('无适用遗留项', self.text())
        self.assertTrue(any('不得发布' in issue['message'] for issue in response['diagnostics']))
        self.assertFalse(self.writer.inspect_edits(self.root)['changed'])
        self.assertEqual(self.validator.validate_prd(self.root)['status'], 'warning')

    def test_keep_accepts_removing_invalid_empty_residual_notice(self):
        """真实模型首次候选正确移除“无遗留项”，不能被误当成更改需求而拒绝。"""
        self.manual()
        response = self.edit('keep', body=self.marked().replace('无适用遗留项', ''), keep_confirmed=True)
        self.assertEqual(response['status'], 'warning', response)
        self.assertNotIn('无适用遗留项', self.text())
        self.assertIn('查询并导出全部数据功能', self.text())

    def test_keep_does_not_erase_substantive_residual_prose(self):
        """空集合提示的例外不能扩大为删除真实遗留说明的许可。"""
        text = self.text().replace('无适用遗留项', '需研发确认导出性能')
        (self.root / 'prd/prd.md').write_bytes(text.encode())
        trace = read_json(self.root / 'prd/prd-trace.json')
        trace['meta'].update(content_hash=digest(text.encode()), content_baseline=text)
        write_json(self.root / 'prd/prd-trace.json', trace)
        self.manual()
        before = self.snapshot()
        response = self.edit('keep', body=self.marked().replace('需研发确认导出性能', ''), keep_confirmed=True)
        self.assertEqual(response['status'], 'fail', response)
        self.assertEqual(before, self.snapshot())

    def test_keep_supports_non_numbered_section(self):
        """非编号范围变化也必须有稳定目标和对应遗留项，不能漏检。"""
        self.manual(scope=True)
        response = self.edit('keep', body=self.marked(scope=True), keep_confirmed=True)
        self.assertEqual(response['status'], 'warning', response)
        self.assertIn('SYNTHETIC-PRD/prd/sections/scope', self.text())
        self.assertIn('支持跨租户导出', self.text())

    def test_keep_cannot_skip_marker_or_change_more_business_text(self):
        """坚持保留不能漏标，也不能在保存标注时夹带另一项内容改写。"""
        self.manual()
        before = self.snapshot()
        for candidate in (self.text(), self.marked().replace('查询并导出全部数据功能', '彻底删除所有记录')):
            response = self.edit('keep', body=candidate, keep_confirmed=True)
            self.assertEqual(response['status'], 'fail', response)
            self.assertEqual(before, self.snapshot())

    def test_keep_requires_all_changed_targets(self):
        """同时改条目及范围时，仅给条目标注仍拒写。"""
        self.manual()
        (self.root / 'prd/prd.md').write_bytes(self.text().replace('<!-- prd:section scope -->\n分析结果中无此项',
                                                                  '<!-- prd:section scope -->\n新增跨租户权限').encode())
        before = self.snapshot()
        response = self.edit('keep', body=self.marked(), keep_confirmed=True)
        self.assertEqual(response['status'], 'fail', response)
        self.assertEqual(before, self.snapshot())

    def test_keep_rejects_unlocated_business_changes(self):
        """章节外新规则可被检测，但不能伪装成已有条目的合法保留。"""
        self.manual()
        (self.root / 'prd/prd.md').write_bytes((self.text() + '\n新增规定：全部记录可直接删除。\n').encode())
        self.assertIn('全部记录', self.writer.inspect_edits(self.root)['diff'])
        before = self.snapshot()
        response = self.edit('keep', body=self.marked(), keep_confirmed=True)
        self.assertEqual(response['status'], 'fail', response)
        self.assertEqual(before, self.snapshot())

    def test_missing_baseline_is_not_silently_reconstructed(self):
        """旧稿已改但无基准时明确证据不足；匹配的显式旧正文才可恢复比较。"""
        trace = read_json(self.root / 'prd/prd-trace.json')
        trace['meta'].pop('content_baseline')
        write_json(self.root / 'prd/prd-trace.json', trace)
        old = self.manual()
        inspected = self.writer.inspect_edits(self.root)
        self.assertTrue(inspected['changed'])
        self.assertFalse(inspected['baseline_available'])
        self.assertIsNone(inspected['diff'])
        before = self.snapshot()
        response = self.edit('keep', body=self.marked(), keep_confirmed=True)
        self.assertEqual(response['status'], 'fail', response)
        self.assertEqual(before, self.snapshot())
        previous = self.base / 'previous.md'
        previous.write_bytes(old.encode())
        response = self.edit('keep', body=self.marked(), keep_confirmed=True, previous_body=previous)
        self.assertEqual(response['status'], 'warning', response)
        self.assertFalse(self.writer.inspect_edits(self.root)['changed'])

    def test_wrong_explicit_old_body_rejected(self):
        """显式旧稿摘要不符时不覆盖已存有效基准，不输出伪造差异。"""
        previous = self.base / 'wrong.md'
        previous.write_bytes(b'not the old document')
        before = self.snapshot()
        response = self.writer.inspect_edits(self.root, previous_body=previous)
        self.assertEqual(response['status'], 'fail', response)
        self.assertEqual(before, self.snapshot())

    def test_legacy_unchanged_body_can_establish_baseline(self):
        """旧追溯无基准但正文未改时保持兼容，下一次合法编辑建立基准。"""
        trace = read_json(self.root / 'prd/prd-trace.json')
        trace['meta'].pop('content_baseline')
        write_json(self.root / 'prd/prd-trace.json', trace)
        self.assertFalse(self.writer.inspect_edits(self.root)['changed'])
        result = self.edit()
        self.assertNotEqual(result['status'], 'fail', result)
        self.assertEqual(read_json(self.root / 'prd/prd-trace.json')['meta']['content_baseline'], self.text())

    def test_raw_crlf_difference_is_not_normalized_away(self):
        """原始字节摘要保留换行变化，CRLF 差异仍能被比较检出。"""
        current = self.text().replace('\n', '\r\n')
        (self.root / 'prd/prd.md').write_bytes(current.encode())
        response = self.writer.inspect_edits(self.root)
        self.assertTrue(response['changed'], response)
        self.assertTrue(response['diff'])
        self.assertEqual(response['content_hash'], digest(current.encode()))

    def test_edit_rejects_read_time_conflicts(self):
        """版本、分析修订或当前实际正文摘要任一与读时不符即拒写。"""
        before = self.snapshot()
        for kwargs in ({'base_prd_version': '0.9'}, {'base_analysis_revision': 2}, {'base_content_hash': 'sha256:' + '0' * 64}):
            result = self.edit(**kwargs)
            self.assertEqual(result['status'], 'fail', result)
            self.assertEqual(before, self.snapshot())

    def test_pending_layout_cannot_advance_analysis_baseline(self):
        """待同步时不借排版消除修订差或假称已同步。"""
        analysis = read_json(self.root / 'analysis/analysis-result.json')
        analysis['meta']['analysis_revision'] = 2
        write_json(self.root / 'analysis/analysis-result.json', analysis)
        before = self.snapshot()
        result = self.edit()
        self.assertEqual(result['status'], 'fail', result)
        self.assertIn('待同步', str(result))
        self.assertEqual(before, self.snapshot())

    def test_layout_cannot_clear_existing_inconsistency(self):
        """一次后续排版不能把已保留的不一致状态洗成可发布。"""
        self.manual()
        self.assertNotEqual(self.edit('keep', body=self.marked(), keep_confirmed=True)['status'], 'fail')
        before = self.snapshot()
        result = self.edit(body=self.text().replace('【与分析不一致】', ''))
        self.assertEqual(result['status'], 'fail', result)
        self.assertEqual(before, self.snapshot())
        self.assertNotEqual(self.edit()['status'], 'fail')
        self.assertEqual(self.validator.validate_prd(self.root)['status'], 'warning')

    def test_same_input_and_sync_do_not_clear_inconsistency(self):
        """重新生成与未变分析同步都不能无依据清除手工不一致。"""
        self.manual()
        self.assertNotEqual(self.edit('keep', body=self.marked(), keep_confirmed=True)['status'], 'fail')
        before = self.snapshot()
        numbering = deepcopy(self.numbering)
        numbering['base_prd_version'] = '0.2'
        result = self.writer.write_draft(self.root, patch=numbering, body=self.text().replace('【与分析不一致】', ''),
                                        candidate_dir=self.base / 'repeat-clear')
        self.assertEqual(result['status'], 'fail', result)
        self.assertEqual(before, self.snapshot())
        analysis = read_json(self.root / 'analysis/analysis-result.json')
        analysis['meta']['analysis_revision'] = 2
        write_json(self.root / 'analysis/analysis-result.json', analysis)
        numbering['base_analysis_revision'] = 2
        result = self.writer.write_draft(self.root, patch=numbering, body=self.text().replace('【与分析不一致】', ''),
                                        sync=True, candidate_dir=self.base / 'sync-clear')
        self.assertEqual(result['status'], 'fail', result)

    def test_candidate_failure_retains_raw_materials(self):
        """编辑候选定位损坏时保留输入和差异，不改正式业务文件。"""
        before = self.snapshot()
        result = self.edit(body=self.text().replace('<!-- /prd:item -->', '', 1))
        self.assertEqual(result['status'], 'fail', result)
        self.assertEqual(before, self.snapshot())
        self.assertTrue((Path(result['candidate_dir']) / 'inputs/body.md').exists())
        self.assertTrue((Path(result['candidate_dir']) / 'inputs/edit-review.json').exists())

    def test_concurrent_metadata_change_after_validation_refused(self):
        """候选校验后他人修改其他元数据块时仍拒绝覆盖，不只比较版本。"""
        actual = self.validator.validate_prd
        def concurrent(*args, **kwargs):
            """真实候选校验后模拟外部修改，返回原响应；写入错误原样抛出。"""
            response = actual(*args, **kwargs)
            metadata = read_json(self.root / 'requirement.json')
            metadata['foreign'] = {'changed': 'concurrent'}
            write_json(self.root / 'requirement.json', metadata)
            return response
        old_text = self.text()
        with patch.object(self.validator, 'validate_prd', side_effect=concurrent):
            result = self.edit()
        self.assertEqual(result['status'], 'fail', result)
        self.assertEqual(self.text(), old_text)
        self.assertEqual(read_json(self.root / 'requirement.json')['foreign'], {'changed': 'concurrent'})

    def test_edit_interruption_recovers_without_duplicate_event(self):
        """编辑跨文件中断复用既有恢复，正文与基准一致且事件只追加一次。"""
        atomic = self.writer._atomic_write
        def interrupted(path, raw):
            """在正式追溯替换点制造故障，其余调用真实原子写入；可抛 OSError。"""
            if path == self.root / 'prd/prd-trace.json':
                raise OSError('synthetic edit interruption')
            return atomic(path, raw)
        with patch.object(self.writer, '_atomic_write', side_effect=interrupted):
            result = self.edit()
        self.assertEqual(result['status'], 'fail', result)
        self.assertTrue(result['recovery_required'])
        self.assertEqual(result['written'], ['prd/prd.md'])
        recovered = self.writer.recover_draft(self.root)
        self.assertNotEqual(recovered['status'], 'fail', recovered)
        self.assertFalse(self.writer.inspect_edits(self.root)['changed'])
        self.assertEqual(len((self.root / 'prd/prd-events.jsonl').read_text().splitlines()), 2)

    def test_detection_recovery_reports_only_event_write(self):
        """只记录手改的事务恢复不能把未变正文和分析误报为本次写入。"""
        self.manual()
        before = self.snapshot()
        atomic = self.writer._atomic_write
        def interrupted(path, raw):
            """在事件替换时注入故障；其余调用真实原子替换，可抛 OSError。"""
            if path == self.root / 'prd/prd-events.jsonl':
                raise OSError('synthetic detect event interruption')
            return atomic(path, raw)
        with patch.object(self.writer, '_atomic_write', side_effect=interrupted):
            failed = self.edit('detect')
        self.assertEqual(failed['status'], 'fail', failed)
        self.assertTrue(failed['recovery_required'])
        recovered = self.writer.recover_draft(self.root)
        self.assertEqual(recovered['status'], 'warning', recovered)
        self.assertEqual(recovered['written'], ['prd/prd-events.jsonl'])
        for name, raw in before.items():
            if name != 'prd/prd-events.jsonl':
                self.assertEqual((self.root / name).read_bytes(), raw)

    def test_generation_cannot_wash_corrupt_baseline(self):
        """旧基准损坏时重复生成不能靠覆盖字段把损坏证据洗掉。"""
        trace = read_json(self.root / 'prd/prd-trace.json')
        trace['meta']['content_baseline'] += 'corrupt'
        write_json(self.root / 'prd/prd-trace.json', trace)
        before = self.snapshot()
        numbering = deepcopy(self.numbering)
        numbering['base_prd_version'] = '0.1'
        response = self.writer.write_draft(self.root, patch=numbering, body=self.text(), candidate_dir=self.base / 'corrupt-repeat')
        self.assertEqual(response['status'], 'fail', response)
        self.assertEqual(before, self.snapshot())

    def test_marker_mentioned_in_event_summary_is_not_new_target(self):
        """事件说明中的标注名称不在changes章制造伪目标，重复生成仍保留真实不一致。"""
        self.manual()
        response = self.edit('keep', body=self.marked(), keep_confirmed=True, summary='用户接受【与分析不一致】标注并坚持保留')
        self.assertNotEqual(response['status'], 'fail', response)
        numbering = deepcopy(self.numbering)
        numbering['base_prd_version'] = '0.2'
        response = self.writer.write_draft(self.root, patch=numbering, body=self.text(), candidate_dir=self.base / 'marked-repeat')
        self.assertEqual(response['status'], 'warning', response)
        self.assertTrue(any('不得发布' in issue['message'] for issue in response['diagnostics']))

    def test_cli_layout_and_inspection_use_public_entry(self):
        """真实公开 CLI 能只读比较并保存排版，参数不依赖测试私有接口。"""
        import json
        inspected = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / 'write_draft.py'), str(self.root), '--inspect-edits'],
                                   capture_output=True, text=True)
        observed = json.loads(inspected.stdout)
        self.assertFalse(observed['changed'], observed)
        candidate = self.base / 'candidate.md'
        candidate.write_bytes(self.text().replace('合成查询', '**合成查询**').encode())
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / 'write_draft.py'), str(self.root), '--edit', 'layout',
                    '--base-prd-version', '0.1', '--base-analysis-revision', '1', '--base-content-hash', observed['content_hash'],
                    '--body', str(candidate), '--meaning-reviewed', '--edit-summary', '标题加粗，语义保持',
                    '--candidate-dir', str(self.base / 'cli-candidate')], capture_output=True, text=True)
        response = json.loads(result.stdout)
        self.assertIn(result.returncode, (0, 1), response)
        self.assertEqual(response['version'], '0.2')
        self.assertTrue(response['edited'])
        self.assertRegex(self.text(), r'\| \*\*0\.2\*\*<br>[^|]+ \| 标题加粗，语义保持 \|')
        self.assertIn('### 0.2 明细\n\n- **受影响编号**：PRD-FR-001', self.text())

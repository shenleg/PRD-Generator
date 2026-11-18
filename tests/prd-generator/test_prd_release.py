"""经真实 CLI 验证阶段 6，使用完全隔离的合成数据和测试确认，不代表业务同意。"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from prd_fixture_support import block, digest, read_json, write_json
from prd_sync_support import advance_analysis, load_script, make_sync_workspace, mapping_patch, replace_section, snapshot


REPO = Path(__file__).resolve().parents[2]
PRD = REPO / 'skill/prd-generator/scripts'
ANALYST = REPO / 'skill/requirement-analyst/scripts/update_analysis.py'
TEST_PM = '合成产品经理（仅用于程序测试）'
RID = 'SYNTHETIC-PRD'


class PrdReleaseTests(unittest.TestCase):
    """验证公开生命周期、不可变历史和同版本并发；测试失败不视为验收。"""

    def setUp(self):
        """准备独立需求，仅复制上游文件；每个场景从真实首稿生成开始。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.workspace = self.base / 'workspace'
        self.root = self.workspace / 'projects/synthetic/requirements' / RID
        self.fixture = make_sync_workspace(self.base / 'input-fixture')
        shutil.copytree(self.fixture / 'analysis', self.root / 'analysis')
        requirement = read_json(self.fixture / 'requirement.json')
        requirement.pop('prd')
        write_json(self.root / 'requirement.json', requirement)
        self.sequence = 0
        self.evidence = []
        if evidence_root := os.environ.get('PRD_STAGE6_EVIDENCE'):
            self.addCleanup(self.save_evidence, Path(evidence_root) / self._testMethodName)

    def save_evidence(self, destination):
        """保存本次实际命令、序列指纹及输入和最终工作区；拒绝覆盖旧证据。"""
        destination.mkdir(parents=True, exist_ok=False)
        write_json(destination / 'invocations.json', self.evidence)
        shutil.copytree(self.workspace, destination / 'workspace')
        shutil.copytree(self.base / 'inputs', destination / 'inputs')

    def cli(self, script, *args, analyst=False):
        """执行指定生产入口并验证 JSON/退出码一致；不能执行的命令直接令测试失败。"""
        command = [sys.executable, '-I', '-B', str(ANALYST if analyst else PRD / script)]
        command += list(map(str, args if analyst else (self.root, *args)))
        before = snapshot(self.root) if self.evidence_enabled() else {}
        run = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        result = json.loads(run.stdout)
        if self.evidence_enabled():
            self.evidence.append({'command': command, 'exit_code': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr,
                'before': {name: digest(raw) for name, raw in before.items()},
                'after': {name: digest(raw) for name, raw in snapshot(self.root).items()}})
        self.assertEqual(run.returncode, {'pass': 0, 'warning': 1, 'fail': 2}[result['status']], (result, run.stderr))
        return result

    def evidence_enabled(self):
        """判断是否显式指定新留证目录；不创建文件，无预期异常。"""
        return bool(os.environ.get('PRD_STAGE6_EVIDENCE'))

    def body(self):
        """读取当前 Markdown 原始换行；读取或编码错误直接失败。"""
        return (self.root / 'prd/prd.md').read_bytes().decode('utf-8')

    def write(self, body, *flags, numbering=None):
        """把合成 Markdown 与编号补丁交给真实草稿 CLI，返回实际保存状态。"""
        self.sequence += 1
        directory = self.base / 'inputs' / str(self.sequence)
        directory.mkdir(parents=True)
        body_path = directory / 'body.md'
        body_path.write_bytes(body.encode('utf-8'))
        patch_path = write_json(directory / 'numbering.json', numbering if numbering is not None else mapping_patch(self.root))
        return self.cli('write_draft.py', '--patch', patch_path, '--body', body_path, *flags,
                        '--candidate-dir', self.base / f'candidate-{self.sequence}')

    def edit(self, mode, body=None):
        """经真实编辑入口记录手改或保存已核对候选；只使用合成的坚持分支。"""
        self.sequence += 1
        observed = self.body().encode('utf-8')
        prd = read_json(self.root / 'requirement.json')['prd']
        revision = read_json(self.root / 'analysis/analysis-result.json')['meta']['analysis_revision']
        args = ['--edit', mode, '--base-prd-version', prd['version'], '--base-analysis-revision', revision,
                '--base-content-hash', digest(observed), '--edit-summary', '合成测试，已核对实际差异',
                '--candidate-dir', self.base / f'candidate-{self.sequence}']
        if body is not None:
            candidate = self.base / 'inputs' / str(self.sequence) / 'edit.md'
            candidate.parent.mkdir(parents=True)
            candidate.write_bytes(body.encode('utf-8'))
            args.extend(['--body', candidate, '--meaning-reviewed' if mode == 'layout' else '--keep-confirmed'])
        return self.cli('write_draft.py', *args)

    def generate(self, *, readiness='ready_for_document', stale=False, dev=False, gap=False):
        """生成合法首稿，按参数准备就绪度、非阻塞研发项或缺口；首稿失败直接失败。"""
        body = (self.fixture / 'prd/prd.md').read_bytes().decode('utf-8')
        up = self.root / 'analysis/analysis-result.json'
        analysis = read_json(up)
        analysis['meta']['readiness'] = readiness
        if stale:
            analysis['meta']['analysis_status'] = 'stale'
        if readiness != 'ready_for_document' or dev:
            resolution = 'ask_dev' if dev else 'ask_product'
            question = '仅需研发核实查询引擎对既有索引的支持' if dev else '待产品确认分析中的业务范围'
            analysis['questions'].append({'id': 'Q-1', 'question': question, 'priority': 'P0' if readiness == 'not_ready' else 'P1',
                'resolution': resolution, 'reason': '合成前置条件', 'impact': '仅实现' if dev else '需求范围',
                'options': ['甲', '乙'], 'recommendation': '待核实', 'status': 'open', 'related_ids': ['FR-1']})
            body = replace_section(body, 'residuals', block('residual', RID + '/Q-1', f'{question}（{resolution}）'))
        write_json(up, analysis)
        flags = ['--allow-stale'] if stale else []
        if gap:
            body = replace_section(body, 'acceptance_criteria', block('gap', 'GAPREQ-1', '待分析补充：查询验收阈值没有分析依据'))
            flags += ['--gaps', write_json(self.base / 'inputs/gap-input.json', {'schema_version': '1.0', 'requirement_id': RID,
                'counters': {'GAPREQ': 1}, 'requests': [{'id': 'GAPREQ-1', 'needed_for': 'acceptance_criteria',
                    'description': '查询验收阈值缺分析依据', 'related_analysis_refs': [RID + '/FR-1'], 'raised_in': '0.1', 'status': 'open'}]})]
        patch_doc = {'patch_version': '1.0', 'requirement_id': RID, 'base_prd_version': None, 'base_analysis_revision': 1,
                     'items': [{key: item[key] for key in ('mapping_key', 'kind', 'analysis_refs')} for item in read_json(self.fixture / 'prd/prd-trace.json')['items']]}
        result = self.write(body, *flags, numbering=patch_doc)
        self.assertTrue(result['generated'], result)
        return result

    def lifecycle(self, action='check', *flags):
        """调用真实生命周期 CLI，返回结果，不补造未传入的确认。"""
        return self.cli('snapshot_release.py', action, *flags)

    def check_action(self, action='release'):
        """获取操作绑定并断言检查不触碰工作区；返回可以确认的响应。"""
        before = snapshot(self.root)
        result = self.lifecycle('check', '--for-action', action)
        self.assertEqual(before, snapshot(self.root))
        self.assertEqual(result['status'], 'pass', result)
        return result

    def transition(self, action):
        """执行读后绑定的合成状态迁移，验证确实保存；真实发布未授权。"""
        checked = self.check_action(action)
        args = ['--binding', checked['binding']]
        if action in {'release', 'deprecate'}:
            args += ['--confirmed-by', TEST_PM, '--confirmed-at', datetime.now(timezone.utc).isoformat()]
        result = self.lifecycle(action, *args)
        self.assertTrue(result['applied'], result)
        return checked, result

    def refuse(self, *args, contains=()):
        """执行拒绝分支，确认没有业务写入并检查各独立诊断。"""
        before = snapshot(self.root)
        result = self.lifecycle(*args)
        self.assertEqual('fail', result['status'], result)
        self.assertFalse(result['applied'], result)
        self.assertEqual([], result['written'])
        self.assertEqual(before, snapshot(self.root))
        diagnostics = json.dumps(result['diagnostics'], ensure_ascii=False)
        for expected in contains:
            self.assertIn(expected, diagnostics)
        return result

    def events(self):
        """解析真实追加事件；无事件、读取或解析失败直接报告。"""
        return [json.loads(line) for line in (self.root / 'prd/prd-events.jsonl').read_text().splitlines()]

    def analysis_patch(self, operations, *, change_type='supplement', user_statement=None):
        """给分析侧正式 CLI 提交合成操作及可选测试用户发言，返回实际修订；失败直接报告。"""
        up = read_json(self.root / 'analysis/analysis-result.json')
        target = self.base / 'inputs' / f"analysis-r{up['meta']['analysis_revision'] + 1}.json"
        patch_doc = {'patch_version': '1.0', 'requirement_id': RID, 'base_revision': up['meta']['analysis_revision'],
            'change_type': change_type, 'actor': 'analyst', 'summary': '合成分析更新，非真实需求', 'operations': operations,
            'set': {}, 'completion_checks': up['completion_checks']}
        if user_statement is not None:
            patch_doc.update(actor='user', user_statement=user_statement)
        patch_path = write_json(target, patch_doc)
        result = self.cli('update_analysis.py', '--workspace', self.workspace, '--project', 'synthetic', '--patch', patch_path, analyst=True)
        self.assertNotEqual('fail', result['status'], result)
        return result

    def test_pg04_risk_draft_cannot_submit(self):
        """未就绪首稿保留风险和遗留；真正提审入口拒写。"""
        self.assertEqual(self.generate(readiness='not_ready')['draft_kind'], 'risk_draft')
        self.assertIn('仅供沟通', self.body())
        self.refuse('submit-review', contains=('risk_draft',))

    def test_pg05_conditional_can_submit_but_cannot_release(self):
        """有条件稿能送审，仍保留 P1，产品经理确认不能绕过就绪度。"""
        self.assertEqual(self.generate(readiness='conditionally_ready')['draft_kind'], 'conditional_draft')
        self.assertIn(RID + '/Q-1', self.body())
        self.transition('submit-review')
        self.refuse('release', '--confirmed-by', TEST_PM, '--confirmed-at', datetime.now(timezone.utc).isoformat(), contains=('conditionally_ready',))

    def test_pg12_placeholder_blocks_even_with_ready_analysis(self):
        """合法占位及结构不成对的占位均阻断，不能只报未评审。"""
        result = self.generate(gap=True)
        self.assertEqual(result['draft_kind'], 'formal_draft')
        changes = self.body().split('<!-- prd:section changes -->', 1)[1].split('<!-- /prd:section -->', 1)[0]
        self.assertIn('登记生成中发现的分析缺口', changes)
        self.assertIn('首次生成工作稿', changes)
        self.assertEqual(changes.count('PRD-FR-001'), 1)
        self.refuse('release', contains=('GAPREQ-1', '占位'))
        path = self.root / 'prd/prd.md'
        path.write_text(self.body().replace('<!-- prd:gap GAPREQ-1 -->', '<!-- prd:gap GAPREQ-2 -->'), encoding='utf-8')
        self.refuse('release', contains=('GAPREQ-1', 'GAPREQ-2'))

    def test_pg19_unhandled_and_kept_content_both_block(self):
        """真实手改未处理不得发布；坚持保留后摘要合法也不能发布。"""
        self.generate()
        self.transition('submit-review')
        (self.root / 'prd/prd.md').write_text(self.body().replace('合成查询功能', '查询并导出全部数据'), encoding='utf-8')
        self.refuse('release', contains=('手改',))
        self.assertTrue(self.edit('detect')['detected'])
        candidate = replace_section(self.body(), 'residuals', block('residual', RID + '/PRD-FR-001',
            '【与分析不一致】手改扩大范围，建议转回需求分析核实。')).replace('PRD-FR-001：', 'PRD-FR-001：【与分析不一致】', 1)
        self.assertTrue(self.edit('keep', candidate)['edited'])
        self.assertEqual(read_json(self.root / 'prd/prd-trace.json')['meta']['content_hash'], digest(self.body().encode()))
        self.refuse('release', contains=('与分析不一致', 'PRD-FR-001'))

    def test_pg22_gate_diagnostics_and_missing_confirmation(self):
        """验证权威分析、过期、修订、结构、评审和确认，并能同时报告多个问题。"""
        self.generate()
        self.refuse('release', contains=('in_review', 'confirmation'))
        self.transition('submit-review')
        check = self.check_action()
        self.refuse('release', '--binding', check['binding'], contains=('confirmation',))
        self.refuse('release', '--binding', check['binding'], '--confirmed-by', TEST_PM, '--confirmed-at', '2026-11-18', contains=('时区',))
        advance_analysis(self.root, lambda a: a['meta'].update(analysis_status='stale'))
        (self.root / 'prd/prd.md').write_text(self.body().replace('<!-- /prd:item -->', '', 1), encoding='utf-8')
        self.refuse('release', '--binding', check['binding'], contains=('过期', '待同步', '定位块', 'confirmation', 'binding'))
        invalid = read_json(self.root / 'analysis/analysis-result.json')
        invalid.pop('requirements')
        write_json(self.root / 'analysis/analysis-result.json', invalid)
        self.refuse('release', contains=('最新分析须校验通过', '定位块', 'confirmation'))

    def test_stale_draft_is_not_reviewable(self):
        """过期草稿是明确例外生成，不因合法保存而可提审。"""
        self.assertEqual(self.generate(stale=True)['draft_kind'], 'stale_draft')
        self.refuse('submit-review', contains=('stale_draft', '过期'))

    def test_pg23_publish_is_bound_read_only_and_never_repeated(self):
        """仅明示合成确认后创建只读定稿，登记两个原始摘要及准确确认人和时间。"""
        self.generate()
        self.transition('submit-review')
        old = snapshot(self.root)
        previous_items = read_json(self.root / 'prd/prd-trace.json')['items']
        checked, released = self.transition('release')
        self.assertEqual((checked['version'], checked['target_version'], released['version']), ('0.1', '1.0', '1.0'))
        self.assertEqual(read_json(self.root / 'requirement.json')['prd']['status'], 'released')
        self.assertNotIn('草稿，待产品经理确认后发布。', self.body())
        self.assertEqual(previous_items, read_json(self.root / 'prd/prd-trace.json')['items'])
        confirmation, release = self.events()[-2:]
        self.assertEqual((confirmation['change_type'], confirmation['confirmed_by'], confirmation['prd_version']), ('release_confirmed', TEST_PM, '1.0'))
        self.assertIsNotNone(datetime.fromisoformat(confirmation['time']).utcoffset())
        overview = [line for line in self.body().splitlines() if line.startswith('| **')]
        self.assertEqual([line.split('**')[1] for line in overview], ['1.0', '1.0', '0.1', '0.1'])
        self.assertIn(release['summary'], overview[0])
        self.assertIn(confirmation['summary'], overview[1])
        for key, original in (('prd', 'prd.md'), ('trace', 'prd-trace.json')):
            metadata = release['snapshots'][key]
            path = self.root / 'prd' / metadata['path']
            self.assertEqual(path.read_bytes(), (self.root / 'prd' / original).read_bytes())
            self.assertEqual(digest(path.read_bytes()), metadata['sha256'])
            self.assertEqual(path.stat().st_mode & 0o222, 0)
        after = snapshot(self.root)
        self.assertTrue(after['prd/prd-events.jsonl'].startswith(old['prd/prd-events.jsonl']))
        for name in old.keys() - {'prd/prd.md', 'prd/prd-trace.json', 'prd/prd-events.jsonl', 'requirement.json'}:
            self.assertEqual(after[name], old[name])
        self.assertEqual(self.cli('validate_prd.py')['status'], 'pass')
        self.refuse('release', '--binding', checked['binding'], contains=('in_review',))

    def test_pg24_sync_layout_interleaving_and_new_baseline(self):
        """真实发布后逐步改稿；只前移修订升次版，内容同步升主版，旧快照不改。"""
        self.generate()
        self.transition('submit-review')
        self.transition('release')
        history = {name: data for name, data in snapshot(self.root).items() if name.startswith('prd/versions/')}
        layout = self.edit('layout', self.body().replace('合成查询功能', '**合成查询功能**'))
        self.assertEqual(layout['version'], '1.1-draft', layout)
        advance_analysis(self.root)
        self.assertEqual(self.write(self.body(), '--sync')['version'], '1.2-draft')
        for expected, word in [('2.0-draft', '合成查询指定范围'), ('3.0-draft', '合成查询限定分组')]:
            old = read_json(self.root / 'analysis/analysis-result.json')['requirements']['functional_requirements'][0]['content']
            self.analysis_patch([{'op': 'update', 'target': 'FR-1', 'changes': {'content': word,
                'sources': [{'type': 'user_answer', 'location': f'本轮合成用户更正：{word}'}]}}],
                change_type='correction', user_statement=f'本合成测试仅确认查询改为：{word}')
            self.assertEqual(self.write(self.body().replace(old, word), '--sync')['version'], expected)
            if expected == '2.0-draft':
                self.assertEqual(self.edit('layout', self.body().replace('合成导出功能', '**合成导出功能**'))['version'], '2.1-draft')
        self.assertEqual(self.check_action('submit-review')['baseline_version'], '1.0')
        self.assertEqual(len(list((self.root / 'prd/versions').iterdir())), 2)
        self.assertEqual(self.write(self.body(), '--sync')['status'], 'fail')
        self.transition('submit-review')
        self.assertEqual(self.transition('release')[1]['baseline_version'], '3.0')
        self.assertEqual({name: (self.root / name).read_bytes() for name in history}, history)

    def test_sync_from_release_and_layout_only_release(self):
        """同一 1.0 基线的独立分支覆盖直接内容同步以及单独排版再发布。"""
        self.generate()
        self.transition('submit-review')
        self.transition('release')
        old_root = self.root
        self.root = self.workspace / 'layout-branch'
        shutil.copytree(old_root, self.root)
        self.assertEqual(self.edit('layout', self.body().replace('合成查询功能', '**合成查询功能**'))['version'], '1.1-draft')
        self.refuse('release', contains=('in_review',))
        self.transition('submit-review')
        self.assertEqual(self.transition('release')[1]['version'], '1.1')
        self.root = old_root
        advance_analysis(self.root, lambda a: a['requirements']['functional_requirements'][0].update(content='合成查询单个分组'))
        result = self.write(self.body().replace('合成查询功能，不代表真实业务', '合成查询单个分组'), '--sync')
        self.assertEqual(result['version'], '2.0-draft', result)
        self.assertEqual(self.check_action('submit-review')['baseline_version'], '1.0')

    def test_legacy_appendix_and_release_remain_readable_after_glossary_split(self):
        """旧附录摘要仍可校验；同步迁移术语时已发布快照的字节保持不变。"""
        self.generate()
        term = '查询窗口：允许发起查询的时间段。'
        analysis_path = self.root / 'analysis/analysis-result.json'
        analysis = read_json(analysis_path)
        analysis['context'] = {'source_ids': ['SRC-1'], 'domain_terms': [term]}
        write_json(analysis_path, analysis)
        prd_path = self.root / 'prd/prd.md'
        legacy_body = replace_section(self.body(), 'appendix', f'SRC-1\n\n- {term}').replace('、context.domain_terms', '')
        prd_path.write_text(legacy_body, encoding='utf-8')
        trace_path = self.root / 'prd/prd-trace.json'
        trace = read_json(trace_path)
        meta = trace['meta']
        meta.update(content_baseline=legacy_body, content_hash=digest(legacy_body.encode('utf-8')))
        del meta['section_source_digests']['glossary']
        # 用旧协议的实际摘要载荷构造夹具，不调用新版的兼容分支生成预期。
        meta['section_source_digests']['appendix'] = digest({'analysis': {'context': analysis['context'],
            'sources': [item['sources'] for item in analysis['requirements']['functional_requirements']],
            'manifest': read_json(self.root / 'analysis/source-manifest.json')}, 'mapped_sources': [], 'gap_requests': []})
        write_json(trace_path, trace)
        old = snapshot(self.root)
        self.assertEqual(self.cli('validate_prd.py')['status'], 'pass')
        self.assertEqual({s['category'] for s in self.cli('check_sync.py')['sections']}, {'unchanged'})
        self.assertEqual(old, snapshot(self.root))
        repeated = self.write(self.body())
        self.assertEqual(repeated['status'], 'pass', repeated)
        self.assertEqual(read_json(trace_path)['meta']['section_source_digests'], meta['section_source_digests'])
        self.transition('submit-review')
        self.transition('release')
        history = {name: data for name, data in snapshot(self.root).items() if name.startswith('prd/versions/')}
        self.assertEqual(self.cli('validate_prd.py')['status'], 'pass')
        advance_analysis(self.root)
        glossary = block('section', 'glossary', f'# 术语\n- {term}')
        candidate = replace_section(self.body(), 'appendix', 'SRC-1')
        candidate = candidate.replace('<!-- prd:section scenarios -->', glossary + '\n\n<!-- prd:section scenarios -->', 1)
        synced = self.write(candidate, '--sync')
        self.assertTrue(synced['generated'], synced)
        self.assertEqual(synced['status'], 'warning', synced)
        self.assertTrue(any('glossary' in issue['message'] for issue in synced['diagnostics']), synced)
        self.assertEqual(self.body().count(term), 1)
        self.assertEqual(self.cli('validate_prd.py')['status'], 'pass')
        self.assertEqual({name: (self.root / name).read_bytes() for name in history}, history)

    def test_pg25_both_snapshot_digests_detect_tampering(self):
        """真实发布后各取独立副本篡改一份，校验失败且不回写摘要。"""
        self.generate()
        self.transition('submit-review')
        self.transition('release')
        self.assertEqual(self.cli('validate_prd.py')['status'], 'pass')
        original = self.root
        for name in ('prd-1.0.md', 'prd-trace-1.0.json'):
            with self.subTest(name=name):
                self.root = self.base / name
                shutil.copytree(original, self.root)
                location = self.root / 'prd/versions' / name
                location.chmod(0o644)
                location.write_bytes(location.read_bytes() + b'\nsynthetic corruption\n')
                before = snapshot(self.root)
                validation = self.cli('validate_prd.py')
                self.assertEqual(validation['status'], 'fail')
                self.assertTrue(any(name in i['path'] and '摘要不符' in i['message'] for i in validation['diagnostics']), validation)
                self.assertEqual(snapshot(self.root), before)
        self.root = original

    def test_pg30_real_handoff_and_status_change_keep_gap_blocking(self):
        """真实接收及仅答复状态变化后，正式同步保留占位，发布独立拒绝。"""
        self.generate(gap=True)
        added = {'op': 'add', 'collection': 'questions', 'ref': '$gap', 'value': {'question': '怎样补足查询验收阈值？',
            'priority': 'P3', 'resolution': 'ask_product', 'reason': '尚无依据', 'impact': '待核实', 'options': ['补足', '暂不确定'],
            'recommendation': '保留缺口', 'status': 'open', 'related_ids': ['FR-1'], 'gap_request_ref': 'GAPREQ-1'}}
        result = self.analysis_patch([added])
        question_id = result['id_map']['$gap']
        for current in ('open', 'answered'):
            if current == 'answered':
                self.analysis_patch([{'op': 'update', 'target': question_id, 'changes': {'status': 'answered', 'answer': '收到了回复，尚未得到可用阈值'}}])
            seen = snapshot(self.root)
            self.assertTrue(self.write(self.body(), '--sync')['synced'])
            self.assertEqual({name: raw for name, raw in snapshot(self.root).items() if name.startswith('analysis/')},
                             {name: raw for name, raw in seen.items() if name.startswith('analysis/')})
            self.assertEqual(read_json(self.root / 'prd/gap-requests.json')['requests'][0]['status'], 'handed_over')
            self.assertIn('待分析补充', self.body())
            self.transition('submit-review')
            self.refuse('release', contains=('handed_over', 'GAPREQ-1', '占位'))

    def test_pg33_open_development_question_is_not_a_release_blocker(self):
        """满足核心清单时 ask_dev 在定稿仍可见，且不是缺口或假技术结论。"""
        self.assertEqual(self.generate(dev=True)['draft_kind'], 'formal_draft')
        self.transition('submit-review')
        self.transition('release')
        text = (self.root / 'prd/versions/prd-1.0.md').read_text()
        self.assertIn(RID + '/Q-1', text)
        self.assertIn('ask_dev', text)
        self.assertEqual(read_json(self.root / 'prd/gap-requests.json')['requests'], [])

    def test_return_same_version_invalidates_previous_confirmation(self):
        """同版本退回再提审后，旧绑定不能成为新评审的确认。"""
        self.generate()
        self.transition('submit-review')
        old = self.check_action()
        self.assertEqual(self.transition('return-review')[1]['version'], '0.1')
        self.transition('submit-review')
        self.assertNotEqual(old['binding'], self.check_action()['binding'])
        self.refuse('release', '--binding', old['binding'], '--confirmed-by', TEST_PM, '--confirmed-at', datetime.now(timezone.utc).isoformat(), contains=('重新确认',))

    def test_deprecation_keeps_history_and_does_not_auto_trigger_on_all_withdrawn(self):
        """全部撤销仅提示；产品经理明示废弃后禁止同步并保留旧历史。"""
        self.generate()
        self.transition('submit-review')
        self.transition('release')
        prior = {name: data for name, data in snapshot(self.root).items() if name.startswith('prd/versions/')}
        advance_analysis(self.root, lambda a: [entry.update(status='withdrawn') for entry in a['requirements']['functional_requirements']])
        body = replace_section(self.body(), 'functional_requirements', '分析结果中无此项')
        updated = self.write(body, '--sync')
        self.assertTrue(updated['synced'], updated)
        self.assertTrue(any('是否废弃' in i['message'] for i in updated['diagnostics']), updated)
        self.assertEqual(read_json(self.root / 'requirement.json')['prd']['status'], 'draft')
        self.refuse('deprecate', contains=('confirmation',))
        _, retired = self.transition('deprecate')
        self.assertEqual((retired['prd_status'], retired['baseline_version']), ('deprecated', '1.0'))
        advance_analysis(self.root)
        before = snapshot(self.root)
        self.assertEqual(self.write(self.body(), '--sync')['status'], 'fail')
        self.assertEqual(before, snapshot(self.root))
        self.assertEqual({name: (self.root / name).read_bytes() for name in prior}, prior)

    def test_return_and_deprecate_allow_stale_analysis_without_sync(self):
        """评审退回、无基线废弃不靠最新版业务就绪；保留原分析基准而非冒称同步。"""
        self.generate()
        self.transition('submit-review')
        advance_analysis(self.root, lambda a: a['meta'].update(analysis_status='stale'))
        self.assertTrue(self.transition('return-review')[1]['pending'])
        _, retired = self.transition('deprecate')
        self.assertEqual((retired['version'], retired['based_on_analysis_revision'], retired['baseline_version']), ('0.1', 1, None))
        self.assertEqual(retired['prd_status'], 'deprecated')
        self.assertFalse((self.root / 'prd/versions').exists())

    def test_snapshot_collision_is_not_overwritten_at_commit(self):
        """候选校验后出现同名快照，真实提交拒绝覆盖，不新增第二份快照或发布事件。"""
        self.generate()
        self.transition('submit-review')
        checked = self.check_action()
        module = load_script('snapshot_release')
        actual = module._writer._commit_payload
        collision = self.root / 'prd/versions/prd-1.0.md'

        def add_collision(*args):
            """在提交交界写入独立合成文件；原提交应拒写且保留该文件。"""
            collision.parent.mkdir()
            collision.write_bytes(b'concurrent synthetic snapshot')
            return actual(*args)

        with patch.object(module._writer, '_commit_payload', side_effect=add_collision):
            failed = module.manage_release(self.root, action='release', binding=checked['binding'],
                confirmed_by=TEST_PM, confirmed_at=datetime.now(timezone.utc).isoformat())
        self.assertEqual(failed['status'], 'fail', failed)
        self.assertFalse(failed['applied'])
        self.assertEqual(collision.read_bytes(), b'concurrent synthetic snapshot')
        self.assertFalse((collision.parent / 'prd-trace-1.0.json').exists())
        self.assertNotIn('release', [event['change_type'] for event in self.events()])

    def test_release_conflict_or_interruption_never_overwrites_snapshot(self):
        """注入候选校验后的分析修订及部分快照写入中断，验证拒写与幂等恢复。"""
        self.generate()
        self.transition('submit-review')
        module = load_script('snapshot_release')
        writer = module._writer
        checked = self.check_action()
        real_commit = writer._commit_payload

        def concurrent(*args):
            """在真实候选校验后推进分析，再调用实际提交；冲突可见。"""
            advance_analysis(self.root)
            return real_commit(*args)

        before = snapshot(self.root)
        confirmation = {'action': 'release', 'binding': checked['binding'], 'confirmed_by': TEST_PM, 'confirmed_at': datetime.now(timezone.utc).isoformat()}
        with patch.object(writer, '_commit_payload', side_effect=concurrent):
            failed = module.manage_release(self.root, **confirmation)
        self.assertFalse(failed['applied'], failed)
        self.assertEqual({k: v for k, v in snapshot(self.root).items() if not k.startswith('analysis/')},
                         {k: v for k, v in before.items() if not k.startswith('analysis/')})
        self.assertTrue(self.write(self.body(), '--sync')['synced'])
        self.transition('submit-review')
        confirmation.update(binding=self.check_action()['binding'], confirmed_at=datetime.now(timezone.utc).isoformat())
        real_write = writer._atomic_write

        def interrupted(path, raw, **kwargs):
            """在第二份测试快照写入处中断；第一份由真实不可覆盖入口写入。"""
            if path == self.root / 'prd/versions/prd-trace-1.0.json':
                raise OSError('synthetic stage6 interruption')
            return real_write(path, raw, **kwargs)

        with patch.object(writer, '_atomic_write', side_effect=interrupted):
            failed = module.manage_release(self.root, **confirmation)
        self.assertTrue(failed['recovery_required'], failed)
        self.assertFalse(failed['applied'], failed)
        partial = (self.root / 'prd/versions/prd-1.0.md').read_bytes()
        self.refuse('release', contains=('未完成 PRD 事务',))
        recovered = self.cli('write_draft.py', '--recover')
        self.assertTrue(recovered['recovered'], recovered)
        self.assertEqual(partial, (self.root / 'prd/versions/prd-1.0.md').read_bytes())
        self.assertEqual(sum(event['change_type'] == 'release' for event in self.events()), 1)
        self.assertEqual(self.cli('validate_prd.py')['status'], 'pass')

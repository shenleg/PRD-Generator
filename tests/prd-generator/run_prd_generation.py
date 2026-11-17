"""在全新目录运行合成 PRD CLI 场景并保存可重放证据；不代替模型或人工评审。"""
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'skill/prd-generator/scripts'
spec = importlib.util.spec_from_file_location('fixture', Path(__file__).with_name('prd_fixture_support.py'))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
PROMPTS = {'formal_draft': '草稿，待产品经理确认后发布。', 'risk_draft': '本文档基于未就绪的需求分析生成，存在未解决的阻塞问题，仅供沟通，不得作为开发或测试依据。', 'conditional_draft': '本文档存在待回答的问题和暂定假设，见“遗留事项”。', 'stale_draft': '本文档基于已过期的分析结果生成，内容可能与最新需求不符。'}


def snapshot(root):
    """返回 root 中文件相对路径到 SHA-256 的映射；读取错误向调用者抛出。"""
    return {str(p.relative_to(root)): fixture.digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}


def run_step(folder, name, script, args, root):
    """执行生产 script 及 args，保存命令、输出、退出码和 root 前后指纹；返回解析后的 JSON，异常原样抛出。"""
    before = snapshot(root)
    command = [sys.executable, '-I', '-B', str(SCRIPTS / script), *map(str, args)]
    result = subprocess.run(command, cwd='/', capture_output=True, text=True, timeout=60)
    record = {'command': command, 'cwd': '/', 'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode, 'before': before, 'after': snapshot(root)}
    fixture.write_json(folder / (name + '.json'), record)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f'{name}: 非 JSON 响应，见 {folder / (name + ".json")}') from error


def make_input(folder, missing=False, invalid=False, readiness='ready_for_document', stale=False, scenario=''):
    """在 folder 创建独立合成输入并返回需求目录及候选正文；文件和序列化错误原样抛出。"""
    sample = fixture.make_workspace(folder / 'synthetic-fixture')
    body = (sample / 'prd/prd.md').read_text(encoding='utf-8')
    root = folder / 'requirement'
    root.mkdir()
    metadata = fixture.read_json(sample / 'requirement.json')
    metadata.pop('prd')
    fixture.write_json(root / 'requirement.json', metadata)
    if not missing:
        analysis = fixture.read_json(sample / 'analysis/analysis-result.json')
        analysis['meta']['readiness'] = readiness
        if stale:
            analysis['meta']['analysis_status'] = 'stale'
        questions = analysis['questions']
        if readiness in ('not_ready', 'conditionally_ready'):
            questions.append({'id': 'Q-1', 'question': '合成范围如何确定？', 'priority': 'P0' if readiness == 'not_ready' else 'P1', 'resolution': 'ask_product', 'reason': '范围未确定', 'impact': '范围', 'options': ['甲', '乙'], 'recommendation': '待确认', 'status': 'open', 'related_ids': ['FR-1']})
        if scenario in ('PG-06', 'PG-21'):
            questions.append({'id': 'Q-1', 'question': '合成技术能力是否支持？', 'priority': 'P1', 'resolution': 'ask_dev', 'reason': '能力未确认', 'impact': '实现', 'options': ['支持', '不支持'], 'recommendation': '研发核实', 'status': 'open', 'related_ids': ['FR-1']})
        if scenario in ('PG-06', 'PG-07'):
            qid = 'Q-2' if scenario == 'PG-06' else 'Q-1'
            questions.append({'id': qid, 'question': '合成范围如何验证？', 'priority': 'P1', 'resolution': 'ask_product', 'reason': '暂定范围', 'impact': '范围', 'options': ['甲', '乙'], 'recommendation': '暂用甲', 'status': 'provisional', 'related_ids': ['FR-1']})
            analysis['assumptions'].append({'id': 'ASM-1', 'content': '合成暂定范围', 'tag': 'assumption', 'status': 'active', 'sources': analysis['requirements']['functional_requirements'][0]['sources'], 'related_question': qid, 'basis': '合成推荐依据', 'verification': '产品负责人后续核对'})
        items = analysis['requirements']['functional_requirements']
        if scenario in ('PG-07', 'PG-08', 'PG-09'):
            item = dict(items[0], id='FR-2', content='合成对照条目')
            item['status'] = 'withdrawn' if scenario == 'PG-08' else 'to_reassess' if scenario == 'PG-09' else 'active'
            item['tag'] = 'inferred' if scenario in ('PG-07', 'PG-09') else 'confirmed'
            items.append(item)
        if scenario == 'PG-07':
            items.append(dict(items[0], id='FR-3', content='合成假设条目', tag='assumption', related_ids=['ASM-1']))
        if scenario == 'PG-20-ui':
            analysis['ux_assessment'] = {'ui_dependent': True, 'design_pending_items': ['合成待设计状态']}
        if invalid:
            analysis.pop('requirements')
        fixture.write_json(root / 'analysis/analysis-result.json', analysis)
        shutil.copy2(sample / 'analysis/source-manifest.json', root / 'analysis/source-manifest.json')
    return root, body


def check(condition, message):
    """断言 condition 成立；失败时抛出带 message 的 AssertionError，成功返回 None。"""
    if not condition:
        raise AssertionError(message)


def generate(folder, root, body, kind, stale=False, repeat=False, scenario=''):
    """通过公开 CLI 分配、保存和校验合成草稿；返回首次追溯及正文，失败抛出异常。"""
    patch = {'patch_version': '1.0', 'requirement_id': 'SYNTHETIC-PRD', 'base_prd_version': None, 'base_analysis_revision': 1, 'items': [{'mapping_key': 'synthetic-query', 'kind': 'functional_requirement', 'analysis_refs': ['SYNTHETIC-PRD/FR-1']}]}
    analysis = fixture.read_json(root / 'analysis/analysis-result.json')
    for item in analysis['requirements']['functional_requirements'][1:]:
        if item['status'] != 'withdrawn':
            patch['items'].append({'mapping_key': 'synthetic-' + item['id'], 'kind': 'functional_requirement', 'analysis_refs': ['SYNTHETIC-PRD/' + item['id']]})
    patch_path = fixture.write_json(folder / 'patch.json', patch)
    # 候选正文是显式合成夹具，绝非模型生成。
    body = body.replace(PROMPTS['formal_draft'], PROMPTS[kind], 1)
    extra = ['--allow-stale'] if stale else []
    allocated = run_step(folder, 'assign', 'assign_ids.py', [root, '--patch', patch_path, *extra], root)
    check(allocated.get('status') != 'fail' and len(allocated.get('items', [])) == len(patch['items']), '编号候选失败')
    for item in allocated['items'][1:]:
        src = next(x for x in analysis['requirements']['functional_requirements'] if x['id'] == item['analysis_refs'][0].split('/')[-1])
        labels = ('【推断】' if item['tag'] == 'inferred' else '【暂定】' if item['tag'] == 'assumption' else '') + ('【待确认】' if item['status'] == 'to_confirm' else '')
        row = f"\n| {fixture.block('item', item['prd_id'], item['prd_id'] + '：' + labels + src['content'] + '；分析来源 ' + item['analysis_refs'][0])} | {item['analysis_refs'][0]} |"
        marker = '<!-- /prd:item --> | SYNTHETIC-PRD/FR-1 |'
        body = body.replace(marker, marker + row)
    residuals = []
    for q in analysis['questions']:
        residuals.append(fixture.block('residual', 'SYNTHETIC-PRD/' + q['id'], q['question'] + ' ' + q['resolution']))
    for a in analysis['assumptions']:
        residuals.append(fixture.block('residual', 'SYNTHETIC-PRD/' + a['id'], a['content'] + ' ' + a['basis'] + ' ' + a['verification']))
    for item in analysis['requirements']['functional_requirements']:
        if item['status'] != 'withdrawn' and item['tag'] == 'inferred':
            residuals.append(fixture.block('residual', 'SYNTHETIC-PRD/' + item['id'], '推断：' + item['content']))
    for i, item in enumerate(analysis['ux_assessment']['design_pending_items']):
        residuals.append(fixture.block('residual', f'/ux_assessment/design_pending_items/{i}', item))
    if residuals:
        body = body.replace('无适用遗留项', '\n'.join(residuals))
    if scenario == 'PG-20-ui':
        body += '\n' + fixture.block('section', 'ux', '合成待设计状态，尚无视觉资料') + '\n'
    gap_args = []
    if scenario == 'PG-11':
        (folder / 'template.md').write_text('模板必填：特殊业务验收信息\n', encoding='utf-8')
        gaps = {'schema_version': '1.0', 'requirement_id': 'SYNTHETIC-PRD', 'counters': {'GAPREQ': 1}, 'requests': [{'id': 'GAPREQ-1', 'needed_for': 'acceptance_criteria', 'description': '模板要求的特殊业务验收信息尚未分析', 'related_analysis_refs': ['SYNTHETIC-PRD/FR-1'], 'raised_in': '0.1', 'status': 'open'}]}
        gap_args = ['--gaps', fixture.write_json(folder / 'gaps.json', gaps)]
        body = body.replace('<!-- prd:section acceptance_criteria -->\n分析结果中无此项', '<!-- prd:section acceptance_criteria -->\n' + fixture.block('gap', 'GAPREQ-1', '待分析补充：特殊业务验收信息'))
        body = body.replace('<!-- prd:section residuals -->', '<!-- prd:section residuals -->\n建议回分析补充 GAPREQ-1。')
    body_path = folder / 'body.md'
    body_path.write_text(body, encoding='utf-8')
    saved = run_step(folder, 'write', 'write_draft.py', [root, '--patch', patch_path, '--body', body_path, '--candidate-dir', folder / 'candidate', *gap_args, *extra], root)
    check(saved.get('generated') is True, '统一保存失败')
    validated = run_step(folder, 'validate', 'validate_prd.py', [root], root)
    check(validated.get('status') != 'fail', 'PRD 校验失败')
    trace = fixture.read_json(root / 'prd/prd-trace.json')
    text = (root / 'prd/prd.md').read_text(encoding='utf-8')
    check(trace['meta']['draft_kind'] == kind and text.startswith(PROMPTS[kind]), '草稿类型或提示不一致')
    check(fixture.read_json(root / 'requirement.json')['prd']['status'] == 'draft', '状态不是草稿')
    if repeat:
        patch['base_prd_version'] = '0.1'
        second_patch = fixture.write_json(folder / 'patch-repeat.json', patch)
        repeated_body = folder / 'body-repeat.md'
        repeated_body.write_text(text, encoding='utf-8')
        shutil.copy2(root / 'prd/prd-trace.json', folder / 'trace-first.json')
        second = run_step(folder, 'write-repeat', 'write_draft.py', [root, '--patch', second_patch, '--body', repeated_body, '--candidate-dir', folder / 'candidate-repeat'], root)
        check(second.get('generated') is True, '重复保存失败')
        check(run_step(folder, 'validate-repeat', 'validate_prd.py', [root, '--previous-trace', folder / 'trace-first.json'], root).get('status') != 'fail', '重复校验失败')
        again = fixture.read_json(root / 'prd/prd-trace.json')
        new_text = (root / 'prd/prd.md').read_text(encoding='utf-8')
        blocks = lambda value: re.findall(r'<!-- prd:item [^>]+ -->.*?<!-- /prd:item -->', value, re.S)
        check(trace['items'] == again['items'] and blocks(text) == blocks(new_text), '条目正文或追溯身份变化')
        check(fixture.read_json(root / 'requirement.json')['prd']['version'] == '0.2', '重复版本未递增')
    return trace, text


def main(argv=None):
    """解析 argv 并执行独立场景，返回进程退出码；参数错误由 argparse 抛出。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='必须不存在的证据目录')
    args = parser.parse_args(argv)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for name in ('prd-generator', 'requirement-analyst'):
        shutil.copytree(ROOT / 'skill' / name, out / 'source-snapshot' / name, ignore=shutil.ignore_patterns('__pycache__'))
    # 所有公开调用执行本次冻结的相邻Skill，避免并行开发期间前后源码不一致。
    global SCRIPTS
    SCRIPTS = out / 'source-snapshot/prd-generator/scripts'
    manifest = {'model_run': False, 'human_review': 'pending', 'input': 'synthetic, not real business', 'scenarios': {},
                'source_snapshot': 'source-snapshot', 'source_fingerprints': snapshot(out / 'source-snapshot')}
    cases = [('PG-01', {'missing': True}), ('PG-02', {'invalid': True}), ('PG-03', {'stale': True}), ('PG-04', {'readiness': 'not_ready'}), ('PG-05', {'readiness': 'conditionally_ready'}), *[(name, {}) for name in ('PG-06', 'PG-07', 'PG-08', 'PG-09', 'PG-10', 'PG-11', 'PG-20', 'PG-21', 'PG-26')]]
    failed = False
    for name, options in cases:
        folder = out / name
        folder.mkdir()
        scope = {'PG-01': '缺失分析拒绝及只读', 'PG-02': '必填字段缺失拒绝及只读', 'PG-03': '过期门禁、显式允许与提示', 'PG-04': '就绪度映射及提示', 'PG-05': '就绪度映射及提示', 'PG-06': '正式草稿、研发问题及假设', 'PG-10': '空章节与未覆盖字段', 'PG-20': '有无界面两分支', 'PG-21': '技术评估缺省及研发问题', 'PG-26': '重复生成的条目正文、追溯和版本'}
        entry = {'status': 'partial', 'programmatic': 'pending', 'programmatic_scope': scope.get(name, '合成场景程序检查'), 'human_review': 'pending'}
        manifest['scenarios'][name] = entry
        try:
            root, body = make_input(folder, scenario=name, **options)
            shutil.copytree(root, folder / 'before')
            before = snapshot(root)
            if not options.get('missing') and not options.get('invalid'):
                analysis_cli = SCRIPTS.parents[1] / 'requirement-analyst/scripts/validate_analysis.py'
                checked = run_step(folder, 'analysis-validation', str(analysis_cli), [root / 'analysis/analysis-result.json', '--source-manifest', root / 'analysis/source-manifest.json'], root)
                check(checked.get('status') != 'fail', '上游分析校验失败：' + str(checked))
            gate = run_step(folder, 'gate', 'check_gate.py', [root], root)
            if options.get('missing') or options.get('invalid'):
                check(not gate.get('allowed') and gate.get('status') == 'fail', '门禁未拒绝')
                check(snapshot(root) == before, '拒绝时文件改变')
            else:
                if options.get('stale'):
                    check(not gate.get('allowed') and gate.get('draft_kind') == 'stale_draft', '过期门禁未拒绝')
                    check(snapshot(root) == before, '过期拒绝时文件改变')
                    gate = run_step(folder, 'gate-allow-stale', 'check_gate.py', [root, '--allow-stale'], root)
                check(gate.get('allowed'), '门禁未允许')
                kind = gate['draft_kind']
                trace, text = generate(folder, root, body, kind, stale=options.get('stale', False), repeat=name == 'PG-26', scenario=name)
                check(snapshot(root / 'analysis') == snapshot(folder / 'before/analysis'), '分析文件改变')
                if name == 'PG-10':
                    check('分析结果中无此项' in text and 'value_assessment' in text and 'impact_analysis' in text, '空节或缺省信息不符')
                if name == 'PG-20':
                    check('<!-- prd:section ui' not in text, '无界面依赖却生成界面章节')
                if name == 'PG-21':
                    check('technical_feasibility' in text and 'ask_dev' in text and 'SYNTHETIC-PRD/Q-1' in text, '缺省技术评估或研发问题未保留')
                if name == 'PG-06':
                    check(all(x in text for x in ('ask_dev', '合成暂定范围', '合成推荐依据', '产品负责人后续核对')), '研发问题或假设未保留')
                if name == 'PG-07':
                    check([x['tag'] for x in trace['items']] == ['confirmed', 'inferred', 'assumption'] and all(x in text for x in ('【推断】', '【暂定】', 'SYNTHETIC-PRD/ASM-1', 'SYNTHETIC-PRD/FR-2')), '推断或假设未保留')
                if name == 'PG-08':
                    check(len(trace['items']) == 1 and '合成对照条目' not in text, '撤销条目进入有效内容')
                    legacy = fixture.make_workspace(folder / 'legacy')
                    old_analysis = fixture.read_json(legacy / 'analysis/analysis-result.json')
                    old_analysis['requirements']['functional_requirements'][0]['status'] = 'withdrawn'
                    fixture.write_json(legacy / 'analysis/analysis-result.json', old_analysis)
                    old_patch = {'patch_version': '1.0', 'requirement_id': 'SYNTHETIC-PRD', 'base_prd_version': '0.1', 'base_analysis_revision': 1, 'items': [{'mapping_key': 'synthetic-query', 'kind': 'functional_requirement', 'analysis_refs': ['SYNTHETIC-PRD/FR-1']}]}
                    result = run_step(folder, 'assign-legacy', 'assign_ids.py', [legacy, '--patch', fixture.write_json(folder / 'legacy-patch.json', old_patch)], legacy)
                    check(result['items'][0]['status'] == 'abolished' and result['meta']['counters']['FR'] == 1, '废止编号未保留')
                    fixture.write_json(legacy / 'prd/prd-trace.json', result)
                    old_analysis['requirements']['functional_requirements'].append(dict(old_analysis['requirements']['functional_requirements'][0], id='FR-2', status='active', content='新的合成功能'))
                    fixture.write_json(legacy / 'analysis/analysis-result.json', old_analysis)
                    old_patch['items'] = [{'mapping_key': 'new-query', 'kind': 'functional_requirement', 'analysis_refs': ['SYNTHETIC-PRD/FR-2']}]
                    next_result = run_step(folder, 'assign-legacy-next', 'assign_ids.py', [legacy, '--patch', fixture.write_json(folder / 'legacy-next-patch.json', old_patch)], legacy)
                    check([(x['prd_id'], x['status']) for x in next_result['items']] == [('PRD-FR-001', 'abolished'), ('PRD-FR-002', 'active')], '新条目复用了废止编号')
                if name == 'PG-09':
                    check(trace['items'][1]['status'] == 'to_confirm' and trace['items'][0]['status'] == 'active' and '【推断】【待确认】' in text, '待重评状态未保留')
                if name == 'PG-11':
                    gaps = fixture.read_json(root / 'prd/gap-requests.json')
                    check(gaps['counters']['GAPREQ'] == 1 and gaps['requests'][0]['status'] == 'open' and text.count('<!-- prd:gap GAPREQ-1 -->') == 1, '缺口及占位不一致')
                if name == 'PG-20':
                    branch = folder / 'ui'
                    branch.mkdir()
                    ui_root, ui_body = make_input(branch, scenario='PG-20-ui')
                    shutil.copytree(ui_root, branch / 'before')
                    ui_checked = run_step(branch, 'analysis-validation', str(SCRIPTS.parents[1] / 'requirement-analyst/scripts/validate_analysis.py'), [ui_root / 'analysis/analysis-result.json', '--source-manifest', ui_root / 'analysis/source-manifest.json'], ui_root)
                    check(ui_checked.get('status') != 'fail', '界面分支分析校验失败')
                    ui_gate = run_step(branch, 'gate', 'check_gate.py', [ui_root], ui_root)
                    check(ui_gate.get('allowed'), '界面分支门禁拒绝')
                    _, ui_text = generate(branch, ui_root, ui_body, ui_gate['draft_kind'], scenario='PG-20-ui')
                    check('<!-- prd:section ux -->' in ui_text and '/ux_assessment/design_pending_items/0' in ui_text and '合成待设计状态' in ui_text, '界面事项未定位')
                    check(snapshot(ui_root / 'analysis') == snapshot(branch / 'before/analysis'), '界面分支分析文件改变')
                    shutil.copytree(ui_root, branch / 'after')
            entry['programmatic'] = 'pass'
        except Exception as error:
            entry['programmatic'] = 'fail'
            entry['error'] = str(error)
            failed = True
        finally:
            if (folder / 'requirement').exists():
                shutil.copytree(folder / 'requirement', folder / 'after')
            fixture.write_json(out / 'manifest.json', manifest)
    fixture.write_json(out / 'manifest.json', manifest)
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())

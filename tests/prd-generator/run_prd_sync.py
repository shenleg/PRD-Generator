"""在全新目录运行阶段4公开CLI并保留原始证据；合成候选不冒充模型定向改写。"""

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'skill/prd-generator/scripts'


def _load(name):
    """加载可信测试辅助name并返回模块，兼容隔离解释器；导入故障原样抛出。"""
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fixture = _load('prd_fixture_support')
support = _load('prd_sync_support')
CASES = ('PG-13', 'PG-14', 'PG-15', 'PG-16', 'PG-31-supplied', 'PG-31-not-needed',
         'PG-31-provisional', 'PG-31-retain-open', 'PG-31-retain-answer', 'PG-32-tag',
         'PG-32-sources', 'PG-32-related', 'PG-34', 'auxiliary-fallback')


def prepare_case(folder, name):
    """在全新folder构造name场景，返回需求路径、候选正文、映射和可选缺口；I/O或未知场景抛错。

    输入明确为合成夹具；返回的候选仅供程序驱动，不可提供给实际模型作为参考答案。
    """
    root = support.make_sync_workspace(folder / 'requirement')
    text = (root / 'prd/prd.md').read_text()
    gaps = None
    additions = []
    if name in ('PG-31-supplied', 'PG-31-not-needed', 'PG-31-provisional', 'PG-31-retain-open', 'PG-31-retain-answer'):
        support.add_gap_fixture(root, question_status='open' if name.endswith('open') or name.endswith('provisional') else 'answered')
        text = (root / 'prd/prd.md').read_text()
    if name == 'PG-16':
        # 合成已废止编号历史，不把此准备动作称为执行了撤销CLI；撤销真实链路另由PG-15留证。
        analysis = fixture.read_json(root / 'analysis/analysis-result.json')
        analysis['requirements']['functional_requirements'][0]['status'] = 'withdrawn'
        fixture.write_json(root / 'analysis/analysis-result.json', analysis)
        trace = fixture.read_json(root / 'prd/prd-trace.json')
        trace['items'][0].update(status='abolished', source_digest=fixture.digest([{'analysis_ref': 'SYNTHETIC-PRD/FR-1', 'item': analysis['requirements']['functional_requirements'][0]}]))
        fixture.write_json(root / 'prd/prd-trace.json', trace)
        text = support.replace_section(text, 'functional_requirements', '\n'.join(line for line in support.section_text(text, 'functional_requirements').splitlines() if 'prd:item PRD-FR-001' not in line))
        text = support.replace_section(text, 'changes', '合成旧稿：PRD-FR-001 已废止，保留编号历史。')
        (root / 'prd/prd.md').write_text(text, encoding='utf-8')
        fixture.refresh_hash(root)
        support.refresh_section_sources(root)

    def change(analysis):
        """按当前场景变更合成权威分析，返回None；不读参考答案，错误原样抛出。"""
        first = analysis['requirements']['functional_requirements'][0]
        source = deepcopy(first['sources'])
        if name == 'PG-14':
            first['content'] = '合成查询只返回条件匹配记录，不代表真实业务'
        elif name == 'PG-15':
            first['status'] = 'withdrawn'
        elif name == 'PG-16':
            analysis['requirements']['functional_requirements'].append({**deepcopy(analysis['requirements']['functional_requirements'][1]), 'id': 'FR-3', 'content': '新增合成统计功能'})
        elif name == 'PG-32-tag':
            first['tag'] = 'inferred'
        elif name == 'PG-32-sources':
            first['sources'][0]['location'] = '合成资料重新定位到第2条'
        elif name == 'PG-32-related':
            first['related_ids'] = ['FR-2']
        elif name == 'PG-31-not-needed':
            analysis['requirements']['scope']['out_of_scope'].append({**deepcopy(first), 'id': 'FR-3', 'content': '本期不扩展查询验收，该模板验收信息不再需要'})
        elif name in ('PG-31-supplied', 'PG-31-provisional'):
            assumption = name.endswith('provisional')
            analysis['requirements']['acceptance_criteria'].append({'id': 'AC-1', 'content': '查询只返回与输入条件匹配的记录', 'tag': 'assumption' if assumption else 'confirmed', 'status': 'active', 'sources': source, 'related_ids': ['FR-1', 'ASM-1'] if assumption else ['FR-1']})
            if assumption:
                analysis['questions'][0].update(status='provisional', priority='P1')
                analysis['assumptions'].append({'id': 'ASM-1', 'content': '查询验收暂按仅返回条件匹配记录', 'tag': 'assumption', 'status': 'active', 'sources': source, 'related_question': 'Q-1', 'basis': '产品尚待核对验收口径', 'verification': '产品后续核对验收样例'})
    analysis = support.advance_analysis(root, change)
    if name == 'PG-14':
        text = text.replace('合成查询功能，不代表真实业务', analysis['requirements']['functional_requirements'][0]['content'])
    elif name == 'PG-15':
        text = support.replace_section(text, 'functional_requirements', '\n'.join(line for line in support.section_text(text, 'functional_requirements').splitlines() if 'prd:item PRD-FR-001' not in line))
    elif name == 'PG-16':
        additions = [{'mapping_key': 'new-statistics', 'kind': 'functional_requirement', 'analysis_refs': ['SYNTHETIC-PRD/FR-3']}]
    elif name == 'PG-32-tag':
        text = text.replace('合成查询功能，不代表真实业务；', '合成查询功能，不代表真实业务【推断】；')
        text = support.replace_section(text, 'residuals', fixture.block('residual', 'SYNTHETIC-PRD/FR-1', '推断：合成查询功能，不代表真实业务'))
    elif name == 'PG-32-sources':
        text = text.replace('合成查询功能，不代表真实业务；', '合成查询功能，不代表真实业务（来源位置：合成资料重新定位到第2条）；')
    elif name == 'PG-32-related':
        text = text.replace('合成查询功能，不代表真实业务；', '合成查询功能，不代表真实业务（关联 SYNTHETIC-PRD/FR-2）；')
    if name in ('PG-31-supplied', 'PG-31-provisional'):
        additions = [{'mapping_key': 'query-acceptance', 'kind': 'acceptance_criterion', 'analysis_refs': ['SYNTHETIC-PRD/AC-1']}]
    patch = support.mapping_patch(root, additions)
    trace = support.load_script('assign_ids').allocate_ids(patch, analysis, fixture.read_json(root / 'requirement.json'), previous_trace=fixture.read_json(root / 'prd/prd-trace.json'), version='0.2')
    if name == 'PG-16':
        text = support.replace_section(text, 'functional_requirements', support.section_text(text, 'functional_requirements') + '\n' + support.row(trace['items'][-1]['prd_id'], '新增合成统计功能', 'SYNTHETIC-PRD/FR-3'))
    elif name in ('PG-31-supplied', 'PG-31-provisional', 'PG-31-not-needed'):
        gaps = fixture.read_json(root / 'prd/gap-requests.json')
        gaps['requests'][0].update(status='closed', resolution={'kind': 'not_needed' if name.endswith('not-needed') else 'supplied', 'analysis_refs': ['SYNTHETIC-PRD/FR-3' if name.endswith('not-needed') else 'SYNTHETIC-PRD/AC-1'], 'reason': '当前有效范围明确无需该验收模板项' if name.endswith('not-needed') else '有效AC-1已提供查询验收口径，暂定状态按分析保留'})
        if name.endswith('not-needed'):
            text = support.replace_section(text, 'scope', '本期不含：扩展查询验收；依据 SYNTHETIC-PRD/FR-3。')
            text = support.replace_section(text, 'acceptance_criteria', '本期不再需要该模板验收项，见范围依据 SYNTHETIC-PRD/FR-3。')
        else:
            suffix = '【暂定】' if name.endswith('provisional') else ''
            text = support.replace_section(text, 'acceptance_criteria', '| 验收条件 | 分析来源 |\n| --- | --- |\n' + support.row(trace['items'][-1]['prd_id'], '查询只返回与输入条件匹配的记录', 'SYNTHETIC-PRD/AC-1', suffix))
        residual = '无适用遗留项'
        if name.endswith('provisional'):
            residual = fixture.block('residual', 'SYNTHETIC-PRD/Q-1', '查询验收如何判定？ask_product，暂定口径待验证') + '\n' + fixture.block('residual', 'SYNTHETIC-PRD/ASM-1', '查询验收暂按仅返回条件匹配记录；产品尚待核对验收口径；产品后续核对验收样例')
        text = support.replace_section(text, 'residuals', residual)
    if name == 'PG-34':
        (root / 'analysis/analysis-result.json').write_text(json.dumps(analysis, ensure_ascii=False, sort_keys=True, separators=(',', ':')), encoding='utf-8')
    if name == 'auxiliary-fallback':
        for filename in ('source-manifest.json', 'analysis-events.jsonl'):
            (root / 'analysis' / filename).rename(folder / ('unavailable-' + filename))
    return root, text, patch, gaps


def run_step(folder, name, script, args, root):
    """执行公开script/args并保存前后字节、输出和退出码，返回JSON；非JSON或工具故障抛错。"""
    before = support.snapshot(root)
    destination = folder / 'calls' / name
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copytree(root, destination / 'before')
    command = [sys.executable, '-I', '-B', str(SCRIPTS / script), *map(str, args)]
    process = subprocess.run(command, cwd='/', capture_output=True, text=True, timeout=90)
    shutil.copytree(root, destination / 'after')
    fixture.write_json(destination / 'response.json', {'command': command, 'cwd': '/', 'stdout': process.stdout, 'stderr': process.stderr, 'exit_code': process.returncode,
        'before': {key: fixture.digest(value) for key, value in before.items()}, 'after': {key: fixture.digest(value) for key, value in support.snapshot(root).items()}})
    return json.loads(process.stdout), process.returncode


def run(output):
    """在不存在的output执行全部程序场景并返回manifest；失败保留证据并逐项记录，不伪造通过。"""
    output.mkdir(parents=True, exist_ok=False)
    snapshot_dir = output / 'source-snapshot'
    for skill in ('prd-generator', 'requirement-analyst'):
        shutil.copytree(ROOT / 'skill' / skill, snapshot_dir / skill, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    manifest = {'stage': 4, 'execution': 'synthetic_public_cli', 'model_invocation': False, 'human_review': 'pending',
                'source_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                'source_fingerprints': {str(path.relative_to(snapshot_dir)): fixture.digest(path.read_bytes()) for path in sorted(snapshot_dir.rglob('*')) if path.is_file()}, 'cases': []}
    for name in CASES:
        folder = output / name
        folder.mkdir()
        try:
            root, body, patch, gaps = prepare_case(folder, name)
            before = support.snapshot(root)
            shutil.copytree(root, folder / 'input')
            (folder / 'candidate.md').write_text(body, encoding='utf-8')
            fixture.write_json(folder / 'patch.json', patch)
            args = [root, '--sync', '--patch', folder / 'patch.json', '--body', folder / 'candidate.md', '--candidate-dir', folder / 'candidate']
            if gaps is not None:
                fixture.write_json(folder / 'gaps.json', gaps)
                args += ['--gaps', folder / 'gaps.json']
            compared, code = run_step(folder, 'check', 'check_sync.py', [root], root)
            if code not in (0, 1) or not compared['allowed'] or not compared['pending'] or support.snapshot(root) != before:
                raise AssertionError('只读比较未得到预期结果或改写了文件')
            result, code = run_step(folder, 'sync', 'write_draft.py', args, root)
            if code not in (0, 1) or not result.get('synced') or len(result.get('written', [])) != 5:
                raise AssertionError('同步未完成：' + str(result))
            checked, code = run_step(folder, 'validate', 'validate_prd.py', [root], root)
            if code not in (0, 1) or checked['status'] == 'fail':
                raise AssertionError('同步产物不合法：' + str(checked))
            after = support.snapshot(root)
            if any(after.get(key) != raw for key, raw in before.items() if key.startswith('analysis/')):
                raise AssertionError('生成侧写入了分析')
            old = fixture.read_json(folder / 'input/prd/prd-trace.json')
            new = fixture.read_json(root / 'prd/prd-trace.json')
            old_text = (folder / 'input/prd/prd.md').read_text()
            new_text = (root / 'prd/prd.md').read_text()
            blocks_old, blocks_new = support.load_script('write_draft')._parsed(old_text), support.load_script('write_draft')._parsed(new_text)
            unchanged = [item['prd_id'] for item in compared['items'] if item['category'] == 'unchanged']
            for pid in unchanged:
                if pid in blocks_old['item'] and support.load_script('write_draft')._raw_item(old_text, blocks_old['item'][pid]) != support.load_script('write_draft')._raw_item(new_text, blocks_new['item'][pid]):
                    raise AssertionError('未变条目字节变化：' + pid)
            final_gaps = fixture.read_json(root / 'prd/gap-requests.json')
            if name.startswith('PG-31-'):
                expected = 'handed_over' if 'retain' in name else 'closed'
                if final_gaps['requests'][0]['status'] != expected:
                    raise AssertionError('缺口去留与场景不一致')
            manifest['cases'].append({'scenario': name, 'status': 'pass', 'program_status': result['status'], 'version': result['version'],
                'existing_ids': len(old['items']), 'stable_ids': sum(item['prd_id'] in {current['prd_id'] for current in new['items']} for item in old['items']),
                'unchanged_items': len(unchanged), 'out_of_scope_item_changes': 0, 'analysis_unchanged': True, 'evidence': str(folder)})
        except Exception as error:
            manifest['cases'].append({'scenario': name, 'status': 'fail', 'error': f'{type(error).__name__}: {error}', 'evidence': str(folder)})
    manifest['status'] = 'pass' if all(case['status'] == 'pass' for case in manifest['cases']) else 'fail'
    fixture.write_json(output / 'manifest.json', manifest)
    return manifest


def main(argv=None):
    """解析argv的新输出目录并执行留证；返回0成功、2失败，目录已存在或参数错误不覆盖。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.output.absolute())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())

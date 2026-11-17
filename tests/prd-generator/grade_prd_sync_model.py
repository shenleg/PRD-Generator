"""依据冻结输入与真实模型产物评分阶段4客观断言；不认证自然语言充分性或人工验收。"""

import argparse
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]


def _load_support():
    """加载可信测试辅助并返回；错误原样抛出，不从模型输出目录导入代码。"""
    for name in ('prd_fixture_support', 'prd_sync_support'):
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


support = _load_support()
fixture = sys.modules['prd_fixture_support']


def _assertions(root, source):
    """比较单份root工作稿与冻结source输入，返回客观条件及实测证据；I/O或协议错误抛出。"""
    before, after = support.snapshot(source), support.snapshot(root)
    old_req, new_req = fixture.read_json(source / 'requirement.json'), fixture.read_json(root / 'requirement.json')
    analysis = fixture.read_json(root / 'analysis/analysis-result.json')
    old_trace, trace = fixture.read_json(source / 'prd/prd-trace.json'), fixture.read_json(root / 'prd/prd-trace.json')
    old_text, text = (source / 'prd/prd.md').read_text(), (root / 'prd/prd.md').read_text()
    comparison = support.load_script('check_sync').compare_sources(analysis, old_req, old_trace)
    old_blocks, blocks = support.load_script('write_draft')._parsed(old_text), support.load_script('write_draft')._parsed(text)
    events = [json.loads(line) for line in after['prd/prd-events.jsonl'].splitlines() if line.strip()]
    sync_events = [event for event in events if event['change_type'] == 'sync']
    complete = (new_req['prd']['version'] == '0.2' and new_req['prd']['status'] == 'draft'
                and new_req['prd']['based_on_analysis_revision'] == analysis['meta']['analysis_revision']
                and len(sync_events) == 1)
    unchanged = [item['prd_id'] for item in comparison['items'] if item['category'] == 'unchanged']
    stable = True
    for pid in unchanged:
        if pid not in old_blocks['item']:
            continue
        stable = stable and pid in blocks['item'] and old_blocks['item'][pid]['section'] == blocks['item'][pid]['section']
        if pid in blocks['item']:
            stable = stable and support.load_script('write_draft')._raw_item(old_text, old_blocks['item'][pid]) == support.load_script('write_draft')._raw_item(text, blocks['item'][pid])
    by_id = {item['prd_id']: item for item in trace['items']}
    ids = all(item['prd_id'] in by_id and item['introduced_in'] == by_id[item['prd_id']]['introduced_in'] and item.get('mapping_key') == by_id[item['prd_id']].get('mapping_key') for item in old_trace['items'])
    ids = ids and all(value >= old_trace['meta']['counters'].get(prefix, 0) for prefix, value in trace['meta']['counters'].items())
    for item in trace['items']:
        if item['prd_id'] not in {old['prd_id'] for old in old_trace['items']}:
            _, prefix, number = item['prd_id'].split('-')
            ids = ids and int(number) > old_trace['meta']['counters'].get(prefix, 0) and item['introduced_in'] == '0.2'
    mapped = {ref for item in trace['items'] for ref in item['analysis_refs']}
    ids = ids and all(item['analysis_ref'] in mapped for item in comparison['added'])
    owned = all(after.get(key) == value for key, value in before.items() if key.startswith('analysis/'))
    owned = owned and {key: value for key, value in old_req.items() if key != 'prd'} == {key: value for key, value in new_req.items() if key != 'prd'}
    owned = owned and after['prd/prd-events.jsonl'].startswith(before['prd/prd-events.jsonl'])
    allowed = set(support.load_script('write_draft').TARGETS)
    owned = owned and all(key in allowed for key in set(before) | set(after) if before.get(key) != after.get(key))
    tag = True
    registry = support.load_script('assign_ids')._registry((analysis,))
    ranks = {'assumption': 0, 'inferred': 1, 'confirmed': 2}
    for item in trace['items']:
        if item['status'] == 'abolished':
            continue
        expected_tag = min((registry[ref].get('tag', 'confirmed') for ref in item['analysis_refs']), key=ranks.__getitem__)
        tag = tag and item['tag'] == expected_tag
        if expected_tag == 'inferred':
            tag = tag and '【推断】' in blocks['item'].get(item['prd_id'], {}).get('text', '') and all(ref in blocks['residual'] for ref in item['analysis_refs'])
    gaps = fixture.read_json(root / 'prd/gap-requests.json')
    closed = None
    if gaps['requests']:
        gap = gaps['requests'][0]
        if root.name == 'PG-31-retain-answer':
            closed = gap['status'] == 'handed_over' and 'GAPREQ-1' in blocks['gap'] and '待分析补充' in blocks['gap']['GAPREQ-1']['text']
        else:
            expected_kind = 'not_needed' if root.name.endswith('not-needed') else 'supplied'
            expected_ref = 'SYNTHETIC-PRD/FR-3' if root.name.endswith('not-needed') else 'SYNTHETIC-PRD/AC-1'
            closed = gap['status'] == 'closed' and gap.get('resolution', {}).get('kind') == expected_kind and expected_ref in gap.get('resolution', {}).get('analysis_refs', []) and 'GAPREQ-1' not in blocks['gap']
        original = fixture.read_json(source / 'prd/gap-requests.json')
        closed = closed and all(gap.get(key) == value for key, value in original['requests'][0].items() if key not in ('status', 'resolution'))
    provisional = True
    if root.name == 'PG-31-provisional':
        provisional = '【暂定】' in blocks['section']['acceptance_criteria']['text'] and all(ref in blocks['residual'] for ref in ('SYNTHETIC-PRD/Q-1', 'SYNTHETIC-PRD/ASM-1'))
        provisional = provisional and all(value in blocks['section']['residuals']['text'] for value in ('产品尚待核对验收口径', '产品后续核对验收样例'))
    checked = support.load_script('validate_prd').validate_prd(root)
    return {'complete': complete, 'stable': stable, 'ids': ids, 'owned': owned, 'tag': tag, 'gaps': closed, 'provisional': provisional,
            'valid': complete and checked['status'] != 'fail', 'program_status': checked['status'], 'validation': checked,
            'unchanged_items': len(unchanged), 'old_ids': len(old_trace['items']), 'new_ids': len(trace['items']),
            'version': new_req['prd']['version'], 'sync_events': len(sync_events), 'workspace_unchanged': before == after}


def grade(iteration, evals_path, tasks=()):
    """对iteration两配置逐项评分并返回汇总；tasks可只选已完成任务，缺证据不猜通过。

    写派生grading与verification，不修改模型产物；任务筛选时另存局部汇总，不能冒充最终全部结果。
    """
    evals = fixture.read_json(evals_path)
    result = {'stage': 4, 'semantic_review': 'pending_human', 'runs': []}
    for evaluation in evals['evals']:
        task = evaluation['name']
        if tasks and task not in tasks:
            continue
        for config in ('with_skill', 'old_skill'):
            run = iteration / task / config
            evidence = {}
            for source in sorted((iteration / 'inputs' / task).iterdir()):
                try:
                    location = run / 'execution-location.json'
                    actual = run / fixture.read_json(location)['archived_trial'] if location.exists() else run / 'completed-trial' if (run / 'completed-trial/workspace').is_dir() else run
                    evidence[source.name] = _assertions(actual / 'workspace' / source.name, source)
                except Exception as error:
                    evidence[source.name] = {'error': f'{type(error).__name__}: {error}'}
            keys = ['complete', 'stable', 'ids', 'owned'] + (['tag'] if task == 'directed-items' else ['gaps', 'provisional']) + ['valid']
            expectations = []
            for text, key in zip(evaluation['assertions'], keys):
                applicable = {name: case.get(key) for name, case in evidence.items() if case.get(key) is not None or 'error' in case}
                passed = bool(applicable) and all(value is True for value in applicable.values())
                expectations.append({'text': text, 'passed': passed, 'evidence': json.dumps(applicable, ensure_ascii=False) + '；逐场景证据见verification.json'})
            passed = sum(expectation['passed'] for expectation in expectations)
            timing_path = run / 'timing.json'
            timing = fixture.read_json(timing_path) if timing_path.exists() else {}
            metrics_path = run / 'metrics.json'
            metrics = fixture.read_json(metrics_path) if metrics_path.exists() else {}
            claims = []
            report = actual / 'outputs/model-response.md'
            if report.exists() and '已人工逐章' in report.read_text():
                claims.append({'claim': '模型说明中的“已人工逐章”', 'type': 'process', 'verified': False,
                               'evidence': '执行者是模型，只计AI辅助核对，不是用户或指定负责人的人工评审；正式意见仍待用户提供。'})
            grading = {'expectations': expectations, 'execution_metrics': metrics, 'summary': {'passed': passed, 'failed': len(expectations) - passed,
                       'total': len(expectations), 'pass_rate': passed / len(expectations)}, 'timing': timing,
                       'claims': claims, 'user_notes_summary': {'uncertainties': ['自然语言忠实性和缺口充分性仍须人工审阅'], 'needs_review': [], 'workarounds': []},
                       'eval_feedback': {'overall': '旧Skill仅作未实现功能的边界对照；单次运行不证明统计稳定性，语义不由字符串断言认证。'}}
            fixture.write_json(run / 'verification.json', evidence)
            fixture.write_json(run / 'grading.json', grading)
            result['runs'].append({'task': task, 'configuration': config, **grading['summary'],
                                 'all_tasks_synced': all(case.get('complete', False) for case in evidence.values()),
                                 'all_inputs_unchanged': all(case.get('workspace_unchanged', False) for case in evidence.values()),
                                 'evidence': str(run)})
    suffix = '-' + '-'.join(tasks) if tasks else ''
    fixture.write_json(iteration / ('programmatic-summary' + suffix + '.json'), result)
    return result


def main(argv=None):
    """解析argv指定的冻结运行及评审断言，输出评分JSON；返回0，输入故障原样抛出。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=Path, required=True)
    parser.add_argument('--evals', type=Path, required=True)
    parser.add_argument('--task', action='append', choices=['directed-items', 'gap-resolution'], default=[])
    args = parser.parse_args(argv)
    print(json.dumps(grade(args.iteration.absolute(), args.evals.absolute(), args.task), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

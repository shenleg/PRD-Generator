"""从实际文件和多轮归档评分阶段 6，生成 Skill Creator 评审输入；不替代人工判断。"""

import argparse
import difflib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


def _load_local(name):
    """加载同目录维护脚本，返回模块；导入失败原样抛出。"""
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_prep = _load_local('prepare_prd_release_model')
CREATOR = Path.home() / '.claude/skills/skill-creator'
ASSERTIONS = {
    'conditional-review': (
        '有条件稿保持 0.1，实际进入 in_review 且仅追加一次提审',
        '只读发布检查明确报告 conditionally_ready，模型未尝试发布',
        '任何轮次均无发布确认、发布事件或版本快照',
        '分析、非 PRD 元数据、编号、缺口与现行业务正文保持',
    ),
    'confirm-and-sync': (
        '首轮实际提审并检查通过；等待明确答复，未提前发布',
        '收到合成确认后定稿 1.0，确认人、时间、快照摘要和权限均正确',
        '仅更新受影响功能，发布后同步到 2.0-draft 且返回 draft',
        '旧 1.0 基线的两份快照原字节未改，无第二次发布',
        '各阶段分析、非 PRD 元数据、编号及缺口均未被模型改动',
    ),
}


def _json(path):
    """读实际 JSON，文件及解码错误原样抛出。"""
    return json.loads(path.read_text(encoding='utf-8'))


def _events(root):
    """解析真实追加事件；异常时不生成合成事件。"""
    return [json.loads(line) for line in (root / 'prd/prd-events.jsonl').read_text().splitlines() if line.strip()]


def _metadata(root):
    """返回除 prd 块之外的需求元数据，错误原样抛出。"""
    result = _json(root / 'requirement.json')
    result.pop('prd')
    return result


def _trace(root):
    """读取当前稿的追溯条目；文件和结构问题原样抛出。"""
    return _json(root / 'prd/prd-trace.json')['items']


def _identities(root):
    """返回编号、映射、引用和引入版本以核对同步未换身份。"""
    return [tuple(i.get(key) for key in ('prd_id', 'mapping_key', 'analysis_refs', 'introduced_in')) for i in _trace(root)]


def _business_body(root):
    """取文档信息和变更记录以外的业务内容，供精确比较，不判断语义。"""
    body = (root / 'prd/prd.md').read_bytes().decode()
    begin, marker = body.index('<!-- prd:section changes -->'), '<!-- /prd:section -->'
    return body[body.index(marker, begin) + len(marker):]


def _masked_item(text):
    """仅遮蔽合成 FR-1 正文，保留稳定定位、来源列及其余字节；非唯一返回 None。"""
    start, end = '<!-- prd:item PRD-FR-001 -->', '<!-- /prd:item -->'
    if text.count(start) != 1:
        return None
    offset = text.index(start) + len(start)
    closing = text.find(end, offset)
    if closing < 0:
        return None
    return text[:offset] + text[closing:]


def _released(root):
    """读取真实发布相关事件和快照摘要；任何新业务版本都可见。"""
    return ([e for e in _events(root) if e['change_type'] in ('release', 'release_confirmed')],
            _prep._hashes(root / 'prd/versions'))


def _seen(root):
    """查找模型实际保存的结构化 CLI 响应，不从最终叙述推断脚本已执行。"""
    for path in sorted((root / 'artifacts').rglob('*.json')):
        if 'candidate' in path.parts:
            continue
        try:
            data = _json(path)
        except (ValueError, OSError):
            continue
        for entry in (data, data.get('response') if isinstance(data, dict) else None):
            if isinstance(entry, dict) and 'action' in entry and 'diagnostics' in entry:
                yield path, entry


def _grade_case(group, initial, run, driver):
    """对一个实际运行评分，返回可验证断言及实际依据；阶段缺失不视作成功。"""
    final = run / 'workspace' / _prep.REQ
    first = run / 'round-1' / _prep.REQ
    if not first.exists():
        raise ValueError(f'首轮缺归档：{first}')
    initial_meta = _metadata(initial)
    first_state = _json(first / 'requirement.json')['prd']
    final_state = _json(final / 'requirement.json')['prd']
    first_events, first_snapshots = _released(first)
    final_events, final_snapshots = _released(final)
    submitted = first_state['status'] == 'in_review' and first_state['version'] == '0.1' and sum(
        e['change_type'] == 'submit_review' for e in _events(first)) == 1
    check_attempts = list(_seen(run))
    no_release_call = not any(row.get('action') == 'release' for _, row in check_attempts)
    first_protected = _prep._hashes(first / 'analysis') == _prep._hashes(initial / 'analysis') and _metadata(first) == initial_meta
    if group == 'conditional-review':
        checked = any(row['action'] == 'check' and row.get('check_for') == 'release' and row['status'] == 'fail'
                      and row.get('readiness') == 'conditionally_ready' for _, row in check_attempts)
        return [
            (submitted and first_state == final_state, f'首轮与最终元数据：{first_state}；提审事件逐项核对。'),
            (checked and no_release_call, '在 artifacts 核对实际 check/for=release、就绪度及响应；是否讲清 P1 另由人工判断。'),
            (not first_events and not first_snapshots and not final_events and not final_snapshots, '初轮及最终事件与 versions 目录均无发布产物。'),
            (first_protected and _prep._hashes(final / 'analysis') == _prep._hashes(initial / 'analysis') and _metadata(final) == initial_meta
             and _trace(initial) == _trace(final) and _business_body(initial) == _business_body(final)
             and (initial / 'prd/gap-requests.json').read_bytes() == (final / 'prd/gap-requests.json').read_bytes(),
             '比较分析文件摘要、其他元数据、追溯映射、缺口与固定信息块以外正文原字节。'),
        ]
    handoff = run / 'round-2' / _prep.REQ
    gate = any(row['action'] == 'check' and row.get('check_for') == 'release' and row['status'] == 'pass'
               and row.get('version') == '0.1' and row.get('target_version') == '1.0' for _, row in check_attempts)
    release_valid = preserved = synced = False
    protected = first_protected and _metadata(final) == initial_meta and _identities(initial) == _identities(final) and (
        initial / 'prd/gap-requests.json').read_bytes() == (final / 'prd/gap-requests.json').read_bytes()
    if handoff.exists():
        confirmation = driver.get('confirmation', {})
        r_events, r_snapshots = _released(handoff)
        release_meta = _json(handoff / 'requirement.json')['prd']
        release_valid = (release_meta['version'] == '1.0' and release_meta['status'] == 'released' and len(r_events) == 2 and len(r_snapshots) == 2
                         and r_events[0].get('confirmed_by') == confirmation.get('confirmed_by') and r_events[0].get('time') == confirmation.get('confirmed_at')
                         and r_events[0].get('change_type') == 'release_confirmed' and r_events[1].get('change_type') == 'release'
                         and all(meta['sha256'] == r_snapshots[Path(meta['path']).name]
                                 for meta in r_events[1]['snapshots'].values())
                         and all(p.stat().st_mode & 0o222 == 0 for p in (handoff / 'prd/versions').iterdir()))
        preserved = release_valid and r_snapshots == final_snapshots and r_events == final_events
        old, new = _business_body(handoff), _business_body(final)
        before, after = driver.get('old_text', ''), driver.get('new_text', '')
        scoped = _masked_item(old)
        synced = bool(before and after and before in old and new != old and scoped is not None and _masked_item(new) == scoped
                      and final_state['version'] == '2.0-draft' and final_state['status'] == 'draft'
                      and final_state['based_on_analysis_revision'] == driver.get('analysis_revision')
                      and _events(final)[-1]['change_type'] == 'sync' and _events(final)[-1]['affected_prd_ids'] == ['PRD-FR-001'])
        protected = (protected and _metadata(handoff) == initial_meta and _trace(handoff) == _trace(initial)
                     and _prep._hashes(handoff / 'analysis') == _prep._hashes(initial / 'analysis')
                     and _prep._hashes(final / 'analysis') == driver.get('analysis_after_external_update'))
    else:
        protected = protected and _prep._hashes(final / 'analysis') == _prep._hashes(initial / 'analysis')
    return [
        (submitted and gate and not first_events and not first_snapshots, '核对首轮归档、实际只读检查响应、提审记录、无快照；是否明确提出待确认问题另由人工评审。'),
        (release_valid, '第二轮归档和驱动时间对照 release_confirmed；核对权限、摘要和 release 事件。'),
        (synced, f'比较两个阶段业务正文和事件；当前实际元数据 {final_state}。'),
        (preserved, '第二轮 1.0 快照与最后一轮逐文件原始摘要及两条发布日志一致。'),
        (protected, '逐轮比较分析目录、common 及其他元数据，编号/映射/引入版本和缺口不变；分析仅允许测试驱动单独更新。'),
    ]


def grade(iteration: Path, output: Path) -> list:
    """读取已完成四份试跑，生成新评审目录、正式汇总和静态页面；缺失或冲突抛出错误。"""
    provenance = _json(iteration / 'input-provenance.json')
    output.mkdir(parents=True, exist_ok=False)
    summaries = []
    for row in provenance['runs']:
        group, index, variant = row['name'], row['eval_id'], row['config']
        run = Path(row['path'])
        initial = iteration / 'preparation' / group / 'workspace' / _prep.REQ
        trial = output / f'eval-{index}-{group}'
        if not trial.exists():
            trial.mkdir()
            _prep._write_json(trial / 'eval_metadata.json', {'eval_id': index, 'eval_name': group,
                              'prompt': row['prompt'], 'assertions': list(ASSERTIONS[group])})
        dest = trial / variant / 'run-1'
        outputs = dest / 'outputs'
        outputs.mkdir(parents=True)
        followup = run / 'driver.json'
        driver = _json(followup) if followup.exists() else {}
        for item in sorted((run / 'outputs').iterdir()):
            shutil.copy2(item, outputs / item.name)
        final = run / 'workspace' / _prep.REQ
        for key, root in [('01-送审前', initial), ('02-首轮', run / 'round-1' / _prep.REQ),
                          ('03-定稿', run / 'round-2' / _prep.REQ), ('04-最终', final)]:
            if root.exists():
                shutil.copy2(root / 'prd/prd.md', outputs / (key + '.md'))
        shutil.copy2(final / 'prd/prd-events.jsonl', outputs / '05-最终事件.jsonl')
        shutil.copy2(final / 'requirement.json', outputs / '06-最终元数据.json')
        shutil.copy2(final / 'analysis/analysis-result.json', outputs / '07-最终分析.json')
        diff = difflib.unified_diff(_business_body(initial).splitlines(keepends=True), _business_body(final).splitlines(keepends=True),
                                   fromfile='输入实际业务正文', tofile='最后一轮实际业务正文')
        (outputs / '08-业务正文差异.txt').write_text(''.join(diff) or '业务正文原字节不变。\n', encoding='utf-8')
        expectations = [{'text': text, 'passed': bool(passed), 'evidence': evidence}
                        for text, (passed, evidence) in zip(ASSERTIONS[group], _grade_case(group, initial, run, driver), strict=True)]
        count = sum(i['passed'] for i in expectations)
        summary = {'passed': count, 'failed': len(expectations) - count, 'total': len(expectations), 'pass_rate': count / len(expectations)}
        _prep._write_json(dest / 'grading.json', {'expectations': expectations, 'summary': summary})
        shutil.copy2(run / 'timing.json', dest / 'timing.json')
        summaries.append({'task': group, 'config': variant, **summary})
    _prep._write_json(output / 'grading-summary.json', summaries)
    module_path = CREATOR / 'scripts/aggregate_benchmark.py'
    spec = importlib.util.spec_from_file_location('stage6_benchmark', module_path)
    aggregate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aggregate)
    results = aggregate.load_run_results(output)
    ordered = {name: results[name] for name in ('with_skill', 'old_skill')}
    aggregate.load_run_results = lambda _: ordered
    benchmark = aggregate.generate_benchmark(output, skill_name='prd-generator', skill_path='skill/prd-generator')
    benchmark['metadata'].update(runs_per_configuration=1, executor_model='sonnet (Agent tool alias)', analyzer_model='deterministic artifact grading')
    benchmark['notes'] = ['每配置每组一次；同一模型会话的后续轮不算新样本。', '旧 Skill 如实拒绝是正确处理能力边界；不能计作成功执行新增操作。',
                          '数字来自实际产物；原因与确认措辞需人工核对。时间与 token 不作为效率结论。']
    _prep._write_json(output / 'benchmark.json', benchmark)
    (output / 'benchmark.md').write_text(aggregate.generate_markdown(benchmark), encoding='utf-8')
    subprocess.run([sys.executable, str(CREATOR / 'eval-viewer/generate_review.py'), str(output), '--skill-name', 'prd-generator',
                    '--benchmark', str(output / 'benchmark.json'), '--static', str(output / 'review.html')], check=True)
    return summaries


def main(argv=None) -> int:
    """读取 CLI 运行目录和新评审目录，输出分数；失败由调用者保留现场。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(grade(args.iteration.absolute(), args.output.absolute()), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

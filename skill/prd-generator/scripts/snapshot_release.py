"""检查 PRD 生命周期门禁，显式提审、退回、废弃或创建不可覆盖的定稿快照。"""

import argparse
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path


_spec = importlib.util.spec_from_file_location('prd_lifecycle_writer', Path(__file__).with_name('write_draft.py'))
_writer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_writer)
_validator = _writer._module('validate_prd')
_renderer = _writer._module('render_info')
_ACTIONS = ('submit-review', 'return-review', 'release', 'deprecate')
_STATES = {'submit-review': ('in_review', 'submit_review', '提交产品经理评审'),
           'return-review': ('draft', 'return_review', '评审退回工作稿'),
           'release': ('released', 'release', '发布为现行基线'),
           'deprecate': ('deprecated', 'deprecate', '产品经理确认废弃需求，保留历史')}


def _saved_view(root, snapshots):
    """检查当前稿及历史持久化一致性，独立于最新分析；用于退回及废弃。"""
    issues = []
    requirement = _writer._read_json(root / 'requirement.json')
    trace = _writer._read_json(root / 'prd/prd-trace.json')
    gaps = _writer._read_json(root / 'prd/gap-requests.json')
    text = _writer._raw(root / 'prd/prd.md').decode('utf-8')
    prd, common = requirement['prd'], requirement['common']
    if prd['status'] not in {'draft', 'in_review', 'released', 'deprecated'} or type(prd['based_on_analysis_revision']) is not int or prd['based_on_analysis_revision'] < 1:
        raise ValueError('工作稿状态或基准修订非法')
    latest = _writer._workspace_version(prd, snapshots)
    events = _validator._events(root / 'prd/prd-events.jsonl', issues)
    trace_ok = _validator._structure(trace, 'prd-trace', issues, 1, 'prd-trace.json')
    _validator._snapshots(root / 'prd', trace if trace_ok else None, events, issues)
    gap_ok = _validator._structure(gaps, 'gap-request', issues, 12, 'gap-requests.json')
    blocks = _validator._blocks(text, issues)
    info = {}
    if trace_ok:
        if trace['requirement_id'] != common['requirement_id'] or (gap_ok and gaps['requirement_id'] != trace['requirement_id']):
            issues.append(_validator._issue(1, '$', 'requirement_id', '本需求的持久化文件身份不一致。'))
        info = _validator._document_info(requirement, trace, blocks, text, issues)
        expected = trace['meta']['content_hash']
        if _writer._hash(text.encode('utf-8')) != expected:
            issues.append(_validator._issue(4, '$', 'prd.md', '正文摘要变化，存在未处理手改；先比较并处理。'))
        baseline = trace['meta'].get('content_baseline')
        if baseline is not None and _writer._hash(baseline.encode('utf-8')) != expected:
            issues.append(_validator._issue(1, '$', 'prd-trace.json/meta/content_baseline', '工作稿正文基准的摘要不符。'))
        if prd['status'] == 'released' and any(
            observed != snapshots[path] for observed, path in zip((text.encode('utf-8'), _writer._raw(root / 'prd/prd-trace.json')), _writer._release_targets(latest))
        ):
            issues.append(_validator._issue(11, '$', 'prd/versions', '当前定稿的正文或追溯与其发布快照不符。'))
    return _validator._result(issues), requirement, trace, gaps, text, events, info, latest


def _review_event(events, prd):
    """返回当前版本最后一次未退回、与分析基准匹配的提审记录。"""
    for event in reversed(events):
        if event['prd_version'] == prd['version'] and event['change_type'] in {'submit_review', 'return_review'}:
            if event['change_type'] == 'submit_review' and event['based_on_analysis_revision'] == prd['based_on_analysis_revision']:
                return event
            return None
    return None


def _gates(root, action, related, view):
    """分别检查已知阻断项；独立运行发布条件，避免只返回第一个失败原因。"""
    storage, requirement, trace, gaps, text, events, _, latest = view
    prd = requirement['prd']
    issues = list(storage['diagnostics'])
    target = None
    review = _review_event(events, prd)
    analysis = _validator._read(root / 'analysis/analysis-result.json', [], 3)
    meta = analysis.get('meta') if isinstance(analysis, dict) else None
    revision = meta.get('analysis_revision') if isinstance(meta, dict) else None
    readiness = meta.get('readiness') if isinstance(meta, dict) else None
    if action in {'submit-review', 'release'}:
        gate = _writer._module('check_gate').check_gate(root, related_analyses=related)
        checked = _validator.validate_prd(root, related_analyses=related)
        issues.extend(gate['diagnostics'])
        issues.extend(issue for issue in checked['diagnostics'] if issue not in issues)
        if gate['status'] != 'pass':
            issues.append(_validator._issue(3, '$', 'analysis/analysis-result.json', '最新分析须校验通过且未过期。'))
        if type(revision) is not int or revision != prd['based_on_analysis_revision']:
            issues.append(_validator._issue(10, '$', 'requirement.json/prd/based_on_analysis_revision', 'PRD 待同步或无法证明分析基准一致。'))
        if checked['status'] != 'pass':
            issues.append(_validator._issue(1, '$', 'prd', 'PRD 校验必须为 pass；请处理列出的警告或错误。'))
    if action == 'submit-review':
        if prd['status'] != 'draft':
            issues.append(_validator._issue(10, '$', 'requirement.json/prd/status', '只有 draft 可提交评审。'))
        kind = trace.get('meta', {}).get('draft_kind') if isinstance(trace, dict) and isinstance(trace.get('meta'), dict) else None
        if kind not in ('formal_draft', 'conditional_draft'):
            issues.append(_validator._issue(7, '$', 'prd-trace.json/meta/draft_kind', f'{kind} 不得提交评审；仅正式或有条件草稿可评审。'))
    elif action == 'return-review':
        if prd['status'] != 'in_review' or review is None:
            issues.append(_validator._issue(10, '$', 'requirement.json/prd/status', '只有已正式提交评审的 in_review 可退回。'))
    elif action == 'deprecate':
        if prd['status'] == 'deprecated':
            issues.append(_validator._issue(10, '$', 'requirement.json/prd/status', '需求已经废弃；保留文件，仅可查看。'))
    else:
        if readiness != 'ready_for_document':
            issues.append(_validator._issue(3, '$', 'analysis/meta/readiness', f'当前就绪度为 {readiness or "未知"}，发布需要 ready_for_document。'))
        blocks = _validator._blocks(text, [])
        for gid, block in blocks['gap'].items():
            issues.append(_validator._issue(9, gid, f"prd.md/{block['section']}", '存在待分析补充占位，不能发布。'))
        if isinstance(gaps, dict) and isinstance(gaps.get('requests'), list):
            for gap in gaps['requests']:
                if isinstance(gap, dict) and gap.get('status') != 'closed':
                    issues.append(_validator._issue(12, gap.get('id', '$'), 'gap-requests.json', f"缺口 {gap.get('status')} 未关闭；接收不代表内容已补足。"))
        if _validator.INCONSISTENCY in text and not any(_validator.INCONSISTENCY in issue['message'] for issue in issues):
            issues.append(_validator._issue(4, '$', 'prd.md', '存在【与分析不一致】标注，不能发布。'))
        if prd['status'] != 'in_review' or review is None:
            issues.append(_validator._issue(10, '$', 'requirement.json/prd/status', '必须先提交该版评审并处于 in_review。'))
        if prd['version'].startswith('0.'):
            target = '1.0'
        elif prd['version'].endswith('-draft'):
            target = prd['version'].removesuffix('-draft')
        if target is None or latest and _writer._version_key(target) <= _writer._version_key(latest):
            issues.append(_validator._issue(11, '$', 'prd/versions', '无法分配比历史基线更新且未使用的定稿版本。'))
    return issues, target, revision, readiness, review


def _instant(value):
    """解析带时区的时间，拒绝日期或无时区记录。"""
    stamp = datetime.fromisoformat(value.removesuffix('Z') + ('+00:00' if value.endswith('Z') else ''))
    if stamp.utcoffset() is None:
        raise ValueError('确认时间需包含时区')
    return stamp


def _payload(before, view, action, target, confirmed_by, confirmed_at, timestamp):
    """构造已核对的状态变更或定稿；快照摘要只覆盖最终原始字节。"""
    _, requirement, trace, _, body, events, info, _ = view
    requirement, trace = deepcopy(requirement), deepcopy(trace)
    status, event_type, summary = _STATES[action]
    prd = requirement['prd']
    prd.update(status=status, version=target or prd['version'])
    event = {'time': timestamp, 'prd_version': prd['version'], 'change_type': event_type, 'summary': summary,
             'affected_prd_ids': [], 'based_on_analysis_revision': prd['based_on_analysis_revision'], 'actor': 'prd_generator'}
    if action == 'release':
        added = [{**event, 'time': confirmed_at, 'change_type': 'release_confirmed', 'actor': 'user',
                  'confirmed_by': confirmed_by, 'summary': '产品经理明示确认发布该送审稿'}, event]
    else:
        if action == 'deprecate':
            event.update(time=confirmed_at, actor='user', confirmed_by=confirmed_by)
        added = [event]
    rendered = _renderer.render_info(body, requirement, trace, generated_at=info['生成时间'],
        uncovered_analysis=() if info['未覆盖的分析项'] == '无' else (info['未覆盖的分析项'],),
        changes=_renderer.render_changes([*events, *added]))
    raw = rendered.encode('utf-8')
    trace['meta'].update(content_baseline=rendered, content_hash=_writer._hash(raw))
    trace_bytes = _writer._encode(trace)
    payload = {**before, 'requirement.json': _writer._encode(requirement), 'prd/prd.md': raw, 'prd/prd-trace.json': trace_bytes}
    if action == 'release':
        names = _writer._release_targets(prd['version'])
        payload.update(zip(names, (raw, trace_bytes)))
        event['snapshots'] = {kind: {'path': name.removeprefix('prd/'), 'sha256': _writer._hash(payload[name])}
                              for kind, name in zip(('prd', 'trace'), names)}
    log = before['prd/prd-events.jsonl']
    if log and not log.endswith(b'\n'):
        log += b'\n'
    payload['prd/prd-events.jsonl'] = log + b''.join((json.dumps(item, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8') for item in added)
    return payload


def _check_view(root):
    """在候选目录检查文件自身；退回或废弃并不确认已同步或语义正确。"""
    return _saved_view(root, _writer._snapshot_inputs(root, []))[0]


def manage_release(requirement_dir: Path, *, action: str, check_for: str = 'release', binding: str | None = None,
                   confirmed_by: str | None = None, confirmed_at: str | None = None,
                   related_analyses: Sequence[Path] = (), candidate_dir: Path | None = None) -> dict:
    """只读检查或提交生命周期操作，返回业务状态、诊断及实际写入位置。

    action 为 check 或四种显式写操作；check_for 选择只读的目标操作。binding 为该次检查返回值；
    发布和废弃还需调用方提供产品经理实际确认的姓名与带时区时间。本地脚本不认证身份。
    related_analyses 是显式关联资料；candidate_dir 是业务目录外尚不存在的留证目录。
    用户输入、门禁、读写冲突或中断返回 fail，未完成事务留待统一恢复；安装错误不冒充批准。
    """
    root = Path(os.path.abspath(requirement_dir))
    before, payload, candidate = {}, {}, None
    result = {'action': action, 'written': [], 'applied': False, 'diagnostics': []}
    try:
        _writer._safe(Path(requirement_dir))
        target_action = check_for if action == 'check' else action
        if target_action not in _ACTIONS:
            raise ValueError('未知生命周期操作')
        if confirmed_by is not None or confirmed_at is not None:
            if action not in {'release', 'deprecate'}:
                raise ValueError('只有显式发布或废弃接受确认记录')
        if action == 'check' and (binding is not None or candidate_dir is not None):
            raise ValueError('只读检查不接受绑定值或候选写入目录')
        with _writer._lock(root):
            if (root / _writer.JOURNAL).exists():
                raise ValueError('存在未完成 PRD 事务，先用 write_draft.py --recover')
            before = {name: _writer._raw(root / name) for name in _writer.TARGETS}
            if any(raw is None for raw in before.values()):
                raise ValueError('缺少现有工作稿文件，先生成或恢复')
            guards = _writer._guards(root, related_analyses)
            snapshots = _writer._snapshot_inputs(root, guards)
            view = _saved_view(root, snapshots)
            issues, target, revision, readiness, review = _gates(root, target_action, related_analyses, view)
            prd, latest = view[1]['prd'], view[-1]
            baseline_verified = latest is not None and not any(issue['rule'] == 11 for issue in view[0]['diagnostics'])
            result.update(check_for=target_action, requirement_id=view[1]['common']['requirement_id'],
                          version=prd['version'], prd_status=prd['status'], based_on_analysis_revision=prd['based_on_analysis_revision'],
                          analysis_revision=revision, readiness=readiness, target_version=target,
                          pending=revision > prd['based_on_analysis_revision'] if type(revision) is int else None,
                          baseline_version=latest, baseline_verified=baseline_verified, diagnostics=issues)
            _writer._check_guards(guards)
            if any(_writer._raw(root / name) != raw for name, raw in before.items()):
                raise ValueError('检查期间候选已变化，请重读')
            observed = _writer._hash(_writer._encode({'action': target_action, 'files': {name: _writer._hash(raw) for name, raw in before.items()}, 'guards': guards}))
            if action != 'check' and binding != observed:
                issues.append(_validator._issue(10, '$', 'binding', '缺少检查绑定值或送审稿已变；重新检查，发布须重新确认。'))
            timestamp = datetime.now(timezone.utc)
            if action in {'release', 'deprecate'}:
                try:
                    if not isinstance(confirmed_by, str) or not confirmed_by.strip() or not isinstance(confirmed_at, str):
                        raise ValueError('缺少产品经理明示确认的人和时间')
                    stamp = _instant(confirmed_at)
                    if stamp > timestamp or action == 'release' and review and stamp < _instant(review['time']):
                        raise ValueError('确认时间不可在未来或早于该稿提交评审')
                except ValueError as error:
                    issues.append(_validator._issue(10, '$', 'confirmation', f'无有效产品经理确认：{error}。'))
            result.update(_validator._result(issues))
            if result['status'] != 'pass':
                return result
            if action == 'check':
                return {**result, 'binding': observed}
            if action == 'release':
                for name in _writer._release_targets(target):
                    before[name] = _writer._raw(root / name)
                    if before[name] is not None:
                        raise ValueError(f'快照已存在，不覆盖：{name}')
            payload = _payload(before, view, action, target, confirmed_by, confirmed_at, timestamp.isoformat())
            candidate = _writer._new_candidate(root, candidate_dir, related_analyses)
            result['candidate_dir'] = str(candidate)
            state_only = action in {'return-review', 'deprecate'}
            if (not _writer._stage_payload(root, candidate, payload, related_analyses, True, issues,
                                           snapshots=snapshots, check=_check_view if state_only else None) or issues):
                return {**result, 'status': 'fail', 'diagnostics': issues}
            saved = {**result, 'version': target or prd['version'], 'prd_status': _STATES[action][0],
                     'baseline_version': target or latest, 'baseline_verified': bool(target) or baseline_verified, 'applied': True}
            return _writer._commit_payload(root, before, payload, guards, saved)
    except (OSError, ValueError, KeyError, AttributeError, TypeError) as error:
        if (root / _writer.JOURNAL).exists():
            for name, raw in payload.items():
                try:
                    if raw != before[name] and _writer._raw(root / name) == raw:
                        result['written'].append(name)
                except (OSError, ValueError):
                    pass
        return {**result, 'status': 'fail', 'diagnostics': result['diagnostics'] + [_writer._diagnostic(error)],
                'recovery_required': (root / _writer.JOURNAL).exists()}


def main(argv: Sequence[str] | None = None) -> int:
    """运行指定生命周期操作，输出单个 JSON 和三态退出码；参数错误由 argparse 报告。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('requirement_dir', type=Path)
    parser.add_argument('action', choices=('check', *_ACTIONS))
    parser.add_argument('--for-action', choices=_ACTIONS, default='release', help='只读检查的目标操作')
    parser.add_argument('--binding', help='同一操作的只读检查返回值')
    parser.add_argument('--confirmed-by')
    parser.add_argument('--confirmed-at', help='产品经理实际确认的带时区时间')
    parser.add_argument('--related-analysis', action='append', default=[], type=Path)
    parser.add_argument('--candidate-dir', type=Path)
    args = parser.parse_args(argv)
    result = manage_release(args.requirement_dir, action=args.action, check_for=args.for_action,
        binding=args.binding, confirmed_by=args.confirmed_by, confirmed_at=args.confirmed_at,
        related_analyses=args.related_analysis, candidate_dir=args.candidate_dir)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return _writer.EXIT_CODES[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())

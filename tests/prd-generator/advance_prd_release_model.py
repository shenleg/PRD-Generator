"""归档阶段 6 实际轮次，并单独推进合成分析；模型仍负责提审、发布和同步。"""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

_spec = importlib.util.spec_from_file_location('release_model_input', Path(__file__).with_name('prepare_prd_release_model.py'))
_prep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_prep)


def freeze_round(run: Path, name: str) -> Path:
    """复制真实工作区到 run/name，返回隔离需求目录；不覆盖已有归档。"""
    target = run / name
    shutil.copytree(run / 'workspace', target)
    return target / _prep.REQ


def confirm(run: Path) -> dict:
    """在实际模型已经提审、提出确认且没有发布后，生成合成测试回复。

    仅供操作者阅读首轮输出并确认模型确已提问后调用。不写业务文件或调用发布入口；归档冲突抛异常。
    """
    if not (run / 'outputs/model-response.md').is_file():
        raise ValueError('未保存真实首轮说明')
    root = run / 'workspace' / _prep.REQ
    metadata = json.loads((root / 'requirement.json').read_text())
    if metadata['prd'] != {'version': '0.1', 'status': 'in_review', 'based_on_analysis_revision': 1} or (root / 'prd/versions').exists():
        raise ValueError('首轮未处于预期送审版本或存在提前发布')
    if any(json.loads(line)['change_type'] in {'release', 'release_confirmed'}
           for line in (root / 'prd/prd-events.jsonl').read_text().splitlines()):
        raise ValueError('已经出现发布或确认事件，不能认可首轮结束状态')
    freeze_round(run, 'round-1')
    record = {'confirmed_by': '合成测试产品经理（仅限本次隔离试跑）',
              'confirmed_at': datetime.now(timezone.utc).isoformat(), 'requirement_id': 'SYNTHETIC-PRD',
              'submitted_version': '0.1', 'analysis_revision': 1, 'target_version': '1.0', 'synthetic': True}
    _prep._write_json(run / 'driver-confirmation.json', record)
    return record


def advance(run: Path, skill_root: Path) -> dict:
    """归档完成的合成 1.0，再用同级分析 Skill 更新一次实际功能，返回留证记录。

    skill_root 为本次模型使用的冻结生成 Skill；仅写 run 内的隔离分析，错误原样抛出、不回退快照。
    """
    record = json.loads((run / 'driver-confirmation.json').read_text())
    root = run / 'workspace' / _prep.REQ
    metadata = json.loads((root / 'requirement.json').read_text())
    event_log = [json.loads(line) for line in (root / 'prd/prd-events.jsonl').read_text().splitlines()]
    if metadata['prd']['status'] != 'released' or metadata['prd']['version'] != '1.0' or [e['change_type'] for e in event_log[-2:]] != ['release_confirmed', 'release']:
        raise ValueError('没有实际完成确认发布；不向同步轮推进')
    if (event_log[-2].get('confirmed_by'), event_log[-2].get('time')) != (record['confirmed_by'], record['confirmed_at']):
        raise ValueError('模型写入的确认人与确认时间和测试回答不符')
    freeze_round(run, 'round-2')
    current = json.loads((root / 'analysis/analysis-result.json').read_text())
    old = current['requirements']['functional_requirements'][0]['content']
    new = '合成查询仅返回用户选定分组中的记录，不代表真实业务'
    patch = {'patch_version': '1.0', 'requirement_id': current['requirement_id'], 'base_revision': 1,
             'change_type': 'correction', 'actor': 'user', 'summary': '阶段 6 合成试跑：测试驱动独立更正 FR-1',
             'user_statement': f'仅在本次合成需求中，把查询改为：{new}。其他规则不动。',
             'operations': [{'op': 'update', 'target': 'FR-1', 'changes': {'content': new,
                             'sources': [{'type': 'user_answer', 'location': '阶段 6 模拟发布之后的新一轮合成更正'}]}}],
             'set': {}, 'completion_checks': current['completion_checks']}
    driver_path = run / 'driver-analysis-patch.json'
    _prep._write_json(driver_path, patch)
    updater = skill_root.parent / 'requirement-analyst/scripts/update_analysis.py'
    command = [sys.executable, '-I', '-B', str(updater), '--workspace', str(run / 'workspace'), '--project', 'synthetic', '--patch', str(driver_path)]
    before = _prep._hashes(root)
    process = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    result = json.loads(process.stdout)
    after = _prep._hashes(root)
    response = {'confirmation': record, 'old_text': old, 'new_text': new, 'analysis_revision': result.get('revision'),
                'argv': command, 'exit_code': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr,
                'before': before, 'after': after, 'analysis_after_external_update': _prep._hashes(root / 'analysis')}
    _prep._write_json(run / 'driver.json', response)
    if process.returncode != 0 or response['analysis_revision'] != 2 or any(
            after[name] != expected for name, expected in before.items() if not name.startswith('analysis/')):
        raise ValueError('分析侧更正未合法推进至修订 2，或者修改了不属于分析的产物')
    return response


def main(argv=None) -> int:
    """运行单一阶段驱动并输出证据；文件及前置条件错误直接失败。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('step', choices=('freeze-first', 'confirm', 'advance'))
    parser.add_argument('--skill-root', type=Path)
    args = parser.parse_args(argv)
    if args.step == 'freeze-first':
        print(freeze_round(args.run, 'round-1'))
    elif args.step == 'confirm':
        print(json.dumps(confirm(args.run), ensure_ascii=False))
    else:
        if args.skill_root is None:
            parser.error('advance 须指定实际试跑所用的 --skill-root')
        result = advance(args.run, args.skill_root)
        print(json.dumps({key: result[key] for key in ('analysis_revision', 'old_text', 'new_text')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""用当前冻结源码重放实际模型的原始编辑候选；不是新的模型调用，不改原运行证据。"""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location('edit_replay_runner', Path(__file__).with_name('run_prd_edits.py'))
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)


def replay(iteration, output):
    """在新 output 重放四份实际模型候选并留证，返回清单；缺原候选或路径冲突抛异常。

    iteration 指向已归档模型运行。手改组选择真实首轮被拒的候选，以验证空集合提示修复；
    修改请求组选择真实成功候选。保留原输入和检测事件顺序，不改造模型的需求正文。
    """
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'source-snapshot'
    shutil.copytree(ROOT / 'skill', source, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    scripts = source / 'prd-generator/scripts'
    results = []
    for group, cases, mode in [('request-routing', ('layout-request', 'manual-layout'), 'layout'),
                                ('manual-content', ('manual-item', 'manual-scope'), 'keep')]:
        run = iteration / group / 'with_skill'
        candidates = sorted((run / 'completed-trial/artifacts').rglob('edit-review.json'))
        for case in cases:
            folder = output / group / case
            root = folder / 'requirement'
            shutil.copytree(run / 'workspace' / case, root)
            before = runner.snapshot(root)
            actual_hash = runner.fixture.digest((root / 'prd/prd.md').read_bytes())
            available = [(path, json.loads(path.read_text())) for path in candidates]
            matching = [(path, review) for path, review in available if review.get('mode') == mode and review.get('base_content_hash') == actual_hash]
            if not matching:
                raise ValueError('未找到真实模型候选：' + group + '/' + case)
            review_path, review = matching[0]
            body_path = review_path.with_name('body.md')
            if not body_path.is_file():
                raise ValueError('原始模型候选正文缺失：' + str(body_path))
            shutil.copyfile(body_path, folder / 'model-candidate.md')
            if mode == 'keep':
                first_events = [json.loads(line) for line in (run / 'first-round-trial/workspace' / case / 'prd/prd-events.jsonl').read_text().splitlines()]
                detect_event = next(item for item in reversed(first_events) if item['change_type'] == 'manual_edit_detected')
                detected = runner.invoke(folder / 'detect', scripts, root, '--edit', 'detect',
                         '--base-prd-version', review['base_prd_version'], '--base-analysis-revision', review['base_analysis_revision'],
                         '--base-content-hash', actual_hash, '--edit-summary', detect_event['summary'], '--candidate-dir', folder / 'detect-candidate')
                if detected['response']['status'] == 'fail':
                    raise ValueError('原检测顺序重放失败')
            response = runner.invoke(folder / 'save', scripts, root, '--edit', mode, '--body', folder / 'model-candidate.md',
                        '--base-prd-version', review['base_prd_version'], '--base-analysis-revision', review['base_analysis_revision'],
                        '--base-content-hash', actual_hash, '--edit-summary', review['summary'],
                        '--meaning-reviewed' if mode == 'layout' else '--keep-confirmed', '--candidate-dir', folder / 'candidate')['response']
            trace = runner.fixture.read_json(root / 'prd/prd-trace.json')
            raw = (root / 'prd/prd.md').read_bytes()
            after = runner.snapshot(root)
            analysis_unchanged = all(after[key] == value for key, value in before.items() if key.startswith('analysis/'))
            passed = response.get('edited') is True and response['status'] != 'fail' and response['version'] == '0.2'
            passed = passed and analysis_unchanged and trace['meta']['content_hash'] == runner.fixture.digest(raw) and trace['meta']['content_baseline'] == raw.decode()
            if mode == 'keep':
                passed = passed and '无适用遗留项' not in raw.decode() and any('不得发布' in issue['message'] for issue in response['diagnostics'])
            results.append({'task': group, 'case': case, 'result': 'pass' if passed else 'fail', 'program_status': response['status'],
                            'model_candidate_path': str(body_path), 'model_candidate_sha256': runner.fixture.digest(body_path.read_bytes()),
                            'analysis_unchanged': analysis_unchanged, 'before': before, 'after': after})
    manifest = {'stage': 5, 'execution': 'actual_model_candidate_current_source_replay', 'new_model_invocation': False,
                'human_review': 'pending', 'source_fingerprints': runner.snapshot(source), 'cases': results,
                'status': 'pass' if all(item['result'] == 'pass' for item in results) else 'fail'}
    runner.fixture.write_json(output / 'manifest.json', manifest)
    return manifest


def main(argv=None):
    """解析原iteration及新output，执行重放并返回0/2；输入和证据错误直接报告。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    result = replay(args.iteration.absolute(), args.output.absolute())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())

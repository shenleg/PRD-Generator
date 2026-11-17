"""用当前冻结源码重放实际模型已成功的同步候选；保留模型原件，不称为新模型调用。"""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[2]


def _runner():
    """加载可信公开CLI驱动并返回模块；导入故障原样抛出，不执行模型输出中的代码。"""
    spec = importlib.util.spec_from_file_location('model_sync_replay_runner', Path(__file__).with_name('run_prd_sync.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _successful_candidate(actual, scenario):
    """从实际响应定位scenario的成功候选输入，返回路径及响应文件；不凭目录顺序挑失败草稿。"""
    candidates = []
    response_paths = [*(actual / 'artifacts' / scenario).glob('*.json'), *(actual / 'outputs' / scenario).glob('*.json')]
    for path in sorted(response_paths):
        try:
            response = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(response, dict) and isinstance(response.get('stdout'), str):
            try:
                response = json.loads(response['stdout'])
            except ValueError:
                continue
        if not isinstance(response, dict) or not response.get('generated') or not response.get('synced') or not response.get('candidate_dir'):
            continue
        recorded = Path(response['candidate_dir'])
        parts = recorded.parts
        if 'artifacts' in parts:
            candidate = actual / 'artifacts' / Path(*parts[parts.index('artifacts') + 1:])
        else:
            candidate = recorded
        if not candidate.is_relative_to(actual) or not (candidate / 'inputs/body.md').is_file():
            raise ValueError(f'成功响应候选不在已归档trial内：{recorded}')
        candidates.append((candidate, path))
    unique = {candidate: response for candidate, response in candidates}
    if len(unique) != 1:
        raise ValueError(f'{scenario}成功候选不唯一：{len(unique)}')
    return next(iter(unique.items()))


def replay(iteration, output):
    """在不存在的output重放iteration全部with_skill成功候选并返回清单；失败逐项留证不覆盖原件。"""
    runner = _runner()
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'source-snapshot'
    for name in ('prd-generator', 'requirement-analyst'):
        shutil.copytree(ROOT / 'skill' / name, source / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    manifest = {'stage': 4, 'execution': 'current_source_replay_of_actual_model_candidates', 'model_invocation': False,
                'semantic_review': 'pending_human', 'source_iteration': str(iteration), 'cases': [],
                'source_fingerprints': {str(path.relative_to(source)): runner.fixture.digest(path.read_bytes()) for path in sorted(source.rglob('*')) if path.is_file()}}
    for task in ('directed-items', 'gap-resolution'):
        run = iteration / task / 'with_skill'
        location = run / 'execution-location.json'
        actual = run / runner.fixture.read_json(location)['archived_trial'] if location.exists() else run / 'completed-trial' if (run / 'completed-trial/workspace').is_dir() else run
        for frozen in sorted((iteration / 'inputs' / task).iterdir()):
            name = frozen.name
            folder = output / task / name
            folder.mkdir(parents=True)
            root = folder / 'requirement'
            shutil.copytree(frozen, root)
            try:
                candidate, response = _successful_candidate(actual, name)
                shutil.copytree(candidate / 'inputs', folder / 'model-inputs')
                inputs = folder / 'model-inputs'
                args = [root, '--sync', '--patch', inputs / 'numbering-patch.json', '--body', inputs / 'body.md', '--candidate-dir', folder / 'current-candidate']
                if (inputs / 'gap-requests.json').exists():
                    args += ['--gaps', inputs / 'gap-requests.json']
                before = runner.support.snapshot(root)
                result, code = runner.run_step(folder, 'sync', 'write_draft.py', args, root)
                checked, checked_code = runner.run_step(folder, 'validate', 'validate_prd.py', [root], root)
                unchanged = all(runner.support.snapshot(root).get(key) == raw for key, raw in before.items() if key.startswith('analysis/'))
                passed = code in (0, 1) and result.get('synced') and checked_code in (0, 1) and unchanged
                manifest['cases'].append({'task': task, 'scenario': name, 'status': 'pass' if passed else 'fail',
                    'program_status': result['status'], 'analysis_unchanged': unchanged, 'version': result.get('version'),
                    'model_response': str(response), 'model_candidate': str(candidate), 'candidate': result.get('candidate_dir'),
                    'legacy_section_basis_warning': any('章节依据证据' in issue['message'] for issue in result.get('diagnostics', [])),
                    'note': '冻结模型输入为新增章节摘要协议前的合法旧追溯；明确保留证据不足警告，整章最小化由人工评审，不补造旧依据。'})
            except Exception as error:
                manifest['cases'].append({'task': task, 'scenario': name, 'status': 'fail', 'error': f'{type(error).__name__}: {error}'})
    manifest['status'] = 'pass' if all(item['status'] == 'pass' for item in manifest['cases']) else 'fail'
    runner.fixture.write_json(output / 'manifest.json', manifest)
    return manifest


def main(argv=None):
    """读取argv的已归档模型运行与新输出目录，返回0成功或2失败；参数和路径错误不覆盖。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = replay(args.iteration.absolute(), args.output.absolute())
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())

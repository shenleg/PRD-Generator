"""在新目录通过公开 CLI 留证阶段5编辑分支；合成候选不冒充模型或人工语义验收。"""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location('edit_cli_fixture', Path(__file__).with_name('prd_fixture_support.py'))
fixture = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fixture)


def snapshot(root):
    """返回 root 中全部文件的原始摘要；文件错误原样抛出，不忽略业务文件。"""
    return {str(path.relative_to(root)): fixture.digest(path.read_bytes()) for path in sorted(root.rglob('*')) if path.is_file()}


def prepare_case(folder, scripts):
    """在新 folder 构造合成分析并用公开首稿入口生成工作稿，返回需求目录。

    scripts 指定冻结的生产脚本目录。前置输入明确为合成，不把准备时的分析写入计入生成只读断言。
    已有路径、首稿失败或文件错误抛出异常，不覆盖历史证据。
    """
    folder.mkdir(parents=True, exist_ok=False)
    seed = fixture.make_workspace(folder / 'fixture')
    analysis = fixture.read_json(seed / 'analysis/analysis-result.json')
    analysis['requirements']['functional_requirements'][0]['content'] = '用户可以导出当前筛选结果'
    requirement = folder / 'requirement'
    fixture.write_json(requirement / 'analysis/analysis-result.json', analysis)
    fixture.write_json(requirement / 'analysis/source-manifest.json', fixture.read_json(seed / 'analysis/source-manifest.json'))
    metadata = fixture.read_json(seed / 'requirement.json')
    metadata.pop('prd')
    metadata['common']['title'] = '合成导出需求（非真实业务）'
    metadata['foreign_extension'] = {'keep': '由其他维护者管理'}
    fixture.write_json(requirement / 'requirement.json', metadata)
    patch = {'patch_version': '1.0', 'requirement_id': 'SYNTHETIC-PRD', 'base_prd_version': None, 'base_analysis_revision': 1,
             'items': [{'mapping_key': 'synthetic-query', 'kind': 'functional_requirement', 'analysis_refs': ['SYNTHETIC-PRD/FR-1']}]}
    fixture.write_json(folder / 'initial-patch.json', patch)
    body = (seed / 'prd/prd.md').read_bytes().decode().replace('合成查询功能，不代表真实业务', '用户可以导出当前筛选结果')
    (folder / 'initial-body.md').write_bytes(body.encode())
    result = invoke(folder / 'generation', scripts, requirement, '--patch', folder / 'initial-patch.json', '--body', folder / 'initial-body.md',
                    '--candidate-dir', folder / 'initial-candidate')
    if not result['response'].get('generated') or result['response']['status'] == 'fail':
        raise ValueError('合成首稿准备失败：' + json.dumps(result, ensure_ascii=False))
    return requirement


def invoke(output, scripts, requirement, *arguments):
    """执行真实公开写入/检查 CLI 并保存命令、stdout、stderr和退出码，返回响应证据。

    output 必须不存在；scripts 是冻结生产目录，requirement 为隔离需求。非 JSON 输出抛出解析错误。
    """
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, '-I', '-B', str(scripts / 'write_draft.py'), str(requirement), *(str(value) for value in arguments)]
    result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
    (output / 'stdout.json').write_text(result.stdout, encoding='utf-8')
    (output / 'stderr.txt').write_text(result.stderr, encoding='utf-8')
    evidence = {'command': command, 'returncode': result.returncode, 'response': json.loads(result.stdout)}
    fixture.write_json(output / 'call.json', evidence)
    return evidence


def mark_manual(text, *, scope=False):
    """给合成手改内容添加目标及遗留标注，返回候选；只供程序夹具，不喂给模型。"""
    if scope:
        text = text.replace('<!-- prd:section scope -->', '<!-- prd:section scope -->\n【与分析不一致】', 1)
        ref = 'SYNTHETIC-PRD/prd/sections/scope'
    else:
        text = text.replace('PRD-FR-001：', 'PRD-FR-001：【与分析不一致】', 1)
        ref = 'SYNTHETIC-PRD/PRD-FR-001'
    note = fixture.block('residual', ref, '【与分析不一致】差异：手工扩大导出范围，建议回交分析核实后同步。')
    return text.replace('无适用遗留项', '无适用遗留项\n' + note)


def run(output):
    """在新 output 冻结源码并运行编辑分支，返回含客观断言的清单；失败不覆盖任何旧证据。"""
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'source-snapshot'
    shutil.copytree(ROOT / 'skill', source, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    scripts = source / 'prd-generator/scripts'
    cases = ['unchanged', 'layout', 'manual-layout', 'detect', 'keep-item', 'keep-section', 'missing-baseline',
             'no-confirmation', 'unreviewed-layout', 'read-conflict']
    records = []
    for name in cases:
        folder = output / 'cases' / name
        root = prepare_case(folder, scripts)
        original = snapshot(root)
        old = (root / 'prd/prd.md').read_bytes().decode()
        if name in {'manual-layout', 'detect', 'keep-item', 'keep-section', 'missing-baseline', 'no-confirmation'}:
            text = old.replace('用户可以', '**用户可以**') if name == 'manual-layout' else old.replace('当前筛选结果', '全部数据')
            if name == 'keep-section':
                text = old.replace('<!-- prd:section scope -->\n分析结果中无此项', '<!-- prd:section scope -->\n允许跨租户导出')
            (root / 'prd/prd.md').write_bytes(text.encode())
        if name == 'missing-baseline':
            trace = fixture.read_json(root / 'prd/prd-trace.json')
            trace['meta'].pop('content_baseline')
            fixture.write_json(root / 'prd/prd-trace.json', trace)
        before = snapshot(root)
        shutil.copytree(root, folder / 'before')
        observed = invoke(folder / 'inspect', scripts, root, '--inspect-edits')['response']
        common = ['--base-prd-version', '0.1', '--base-analysis-revision', '1', '--base-content-hash', observed['content_hash'],
                  '--edit-summary', '合成CLI边界验证，不代表自然语言人工签核', '--candidate-dir', folder / 'edit-candidate']
        result = None
        if name == 'unchanged':
            passed = not observed['changed'] and snapshot(root) == before
        elif name == 'detect':
            result = invoke(folder / 'action', scripts, root, '--edit', 'detect', *common)['response']
            passed = result['status'] == 'warning' and result['written'] == ['prd/prd-events.jsonl'] and result['version'] == '0.1'
        else:
            current = (root / 'prd/prd.md').read_bytes().decode()
            mode = 'keep' if name in {'keep-item', 'keep-section', 'no-confirmation'} else 'layout'
            candidate = mark_manual(current, scope=name == 'keep-section') if mode == 'keep' else current.replace('用户可以', '用户可')
            (folder / 'candidate.md').write_bytes(candidate.encode())
            flags = [] if name in {'no-confirmation', 'unreviewed-layout'} else ['--keep-confirmed' if mode == 'keep' else '--meaning-reviewed']
            if name == 'read-conflict':
                common[common.index('0.1')] = '0.9'
            result = invoke(folder / 'action', scripts, root, '--edit', mode, '--body', folder / 'candidate.md', *common, *flags)['response']
            should_fail = name in {'missing-baseline', 'no-confirmation', 'unreviewed-layout', 'read-conflict'}
            passed = result['status'] == 'fail' and snapshot(root) == before if should_fail else result.get('edited') and result['version'] == '0.2' and result['status'] != 'fail'
            if not should_fail:
                trace = fixture.read_json(root / 'prd/prd-trace.json')
                passed = passed and trace['meta']['content_hash'] == fixture.digest((root / 'prd/prd.md').read_bytes()) and trace['meta']['content_baseline'] == (root / 'prd/prd.md').read_bytes().decode()
                if mode == 'keep':
                    passed = passed and any('不得发布' in item['message'] for item in result['diagnostics'])
        after = snapshot(root)
        unchanged_analysis = all(after[key] == value for key, value in original.items() if key.startswith('analysis/'))
        passed = bool(passed and unchanged_analysis)
        shutil.copytree(root, folder / 'after')
        records.append({'case': name, 'result': 'pass' if passed else 'fail', 'before': before, 'after': after,
                        'analysis_unchanged': unchanged_analysis, 'program_status': (result or observed)['status']})
    manifest = {'stage': 5, 'execution': 'synthetic_public_cli', 'model_invocation': False, 'human_review': 'pending',
                'source_fingerprints': snapshot(source), 'cases': records, 'status': 'pass' if all(item['result'] == 'pass' for item in records) else 'fail'}
    fixture.write_json(output / 'manifest.json', manifest)
    return manifest


def main(argv=None):
    """从 argv 取得新输出目录，执行留证并返回0或2；路径冲突及运行故障直接报告。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.output.absolute())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())

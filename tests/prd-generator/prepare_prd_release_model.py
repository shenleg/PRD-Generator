"""冻结阶段 6 新旧 Skill 和两组相同的合成起点；不运行模型或泄露后续回答。"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASELINE = 'b2ac4cf75fbd074215f8290ce8f875509241e50c'
PROGRAM_EVIDENCE = ROOT / 'workspace-sandbox/prd-generator/stage-6-cli/attempt-02'
REQ = Path('projects/synthetic/requirements/SYNTHETIC-PRD')
TASKS = (
    ('conditional-review', 'test_pg05_conditional_can_submit_but_cannot_release',
     '请把这个需求的 PRD 提交评审，然后检查一下能不能定稿。如果现在还不能定稿，告诉我卡在哪、下一步找谁处理。现在不要发布。'),
    ('confirm-and-sync', 'test_pg33_open_development_question_is_not_a_release_blocker',
     '请把这份 PRD 提交评审。如果现在具备定稿条件，请把具体需求、送审版本、分析修订和要定稿的版本告诉我，等我明确答复后再发布。现在不要发布。'),
)


def _write_json(path, data):
    """在新路径保存可核对的 JSON；目录缺失、路径已占用或编码错误原样抛出。"""
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def _hashes(root):
    """返回 root 下各普通文件的原始字节摘要；读取错误原样抛出。"""
    return {p.relative_to(root).as_posix(): 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def _freeze_skills(output):
    """从已验证冻结源码和阶段 5 提交创建新旧 Skill 快照，不读取历史模型产物。"""
    approved = PROGRAM_EVIDENCE / 'source-snapshot/skill'
    if _hashes(approved) != _hashes(ROOT / 'skill'):
        raise ValueError('当前 Skill 与阶段 6 程序回归冻结源码不一致，先验证再试跑')
    shutil.copytree(approved, output / 'current-skill')
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASELINE, '--', 'skill/'], cwd=ROOT, text=True)
    for name in names.splitlines():
        path = output / 'stage-5-skill' / Path(name).relative_to('skill')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(subprocess.check_output(['git', 'show', f'{BASELINE}:{name}'], cwd=ROOT))


def prepare(output: Path) -> dict:
    """为新试跑目录创建四份隔离工作区、输入清单和源码摘要，返回清单。

    output 必须不存在；复用两份已验证的合成分析，借冻结的生产首稿 CLI 重新生成起点。
    旧版与新版仅 Skill 不同，阶段 6 程序案例的已发布产物、参考及后续回答不提供给模型。
    文件冲突、快照漂移、旧版读取或首稿失败原样报错，已生成材料不覆盖。
    """
    output = output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    _freeze_skills(output)
    manifest = {'stage': 6, 'kind': 'synthetic_preparation', 'model_invocation': False, 'old_source_commit': BASELINE,
                'current_fingerprints': _hashes(output / 'current-skill'),
                'old_fingerprints': _hashes(output / 'stage-5-skill'), 'runs': []}
    for number, (name, case, prompt) in enumerate(TASKS, 1):
        input_case = PROGRAM_EVIDENCE / case
        build = output / 'preparation' / name
        seed = build / 'workspace' / REQ
        source = input_case / 'workspace' / REQ
        shutil.copytree(source / 'analysis', seed / 'analysis')
        metadata = json.loads((source / 'requirement.json').read_text())
        metadata.pop('prd')
        _write_json(seed / 'requirement.json', metadata)
        inputs = input_case / 'inputs/1'
        command = [sys.executable, '-I', '-B', str(output / 'current-skill/prd-generator/scripts/write_draft.py'),
                   str(seed), '--patch', str(inputs / 'numbering.json'), '--body', str(inputs / 'body.md'),
                   '--candidate-dir', str(build / 'candidate')]
        process = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        _write_json(build / 'initial-generation.json', {'argv': command, 'exit_code': process.returncode,
                                                       'stdout': process.stdout, 'stderr': process.stderr})
        if process.returncode != 0 or not json.loads(process.stdout).get('generated'):
            raise ValueError(f'{name} 的隔离首稿未得到 pass，见 {build}')
        initial = _hashes(seed)
        for config, skill_name in (('with_skill', 'current-skill'), ('old_skill', 'stage-5-skill')):
            run = output / f'eval-{number}-{name}' / config / 'run-1'
            workspace = run / 'workspace'
            shutil.copytree(build / 'workspace', workspace)
            (run / 'outputs').mkdir()
            (run / 'artifacts').mkdir()
            _write_json(run / 'initial-fingerprints.json', initial)
            manifest['runs'].append({'eval_id': number, 'name': name, 'config': config, 'prompt': prompt,
                                     'path': str(run), 'requirement': str(workspace / REQ),
                                     'skill_root': str(output / skill_name / 'prd-generator')})
        _write_json(output / f'eval-{number}-{name}' / 'eval_metadata.json', {
            'eval_id': number, 'eval_name': name, 'prompt': prompt, 'assertions': []})
    _write_json(output / 'input-provenance.json', manifest)
    return manifest


def main(argv=None) -> int:
    """解析输出路径并准备四份输入；准备失败保留现场，CLI 返回非零。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    result = prepare(args.output)
    print(json.dumps(result['runs'], ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

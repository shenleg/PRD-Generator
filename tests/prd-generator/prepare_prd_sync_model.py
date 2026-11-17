"""冻结阶段4模型试跑的输入与新旧Skill快照；模型输入不含程序候选、参考答案或预设回答。"""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[2]


def _runner():
    """加载可信CLI输入构造器并返回模块；导入故障原样抛出，不从试跑目录执行代码。"""
    spec = importlib.util.spec_from_file_location('sync_model_fixture_runner', Path(__file__).with_name('run_prd_sync.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(output, baseline):
    """在已有iteration输出根的新子目录冻结输入，baseline指定编辑前双Skill快照；返回清单。

    所有准备材料明确为合成需求，source和input目录已存在则拒绝覆盖；文件错误原样抛出。
    不运行模型、不登记场景通过、不把程序构造候选放入模型可读目录。
    """
    runner = _runner()
    source = output / 'current-skill-snapshot'
    for name in ('prd-generator', 'requirement-analyst'):
        shutil.copytree(ROOT / 'skill' / name, source / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    temporary_inputs = output / 'preparation-only'
    temporary_inputs.mkdir(parents=True, exist_ok=False)
    tasks = [
        {'id': 1, 'name': 'directed-items', 'cases': ['PG-14', 'PG-16', 'PG-32-tag']},
        {'id': 2, 'name': 'gap-resolution', 'cases': ['PG-31-supplied', 'PG-31-not-needed', 'PG-31-provisional', 'PG-31-retain-answer']},
    ]
    provenance = []
    for task in tasks:
        for scenario in task['cases']:
            folder = temporary_inputs / scenario
            folder.mkdir()
            root, _, _, _ = runner.prepare_case(folder, scenario)
            target = output / 'inputs' / task['name'] / scenario
            shutil.copytree(root, target)
            provenance.append({'task': task['name'], 'scenario': scenario, 'synthetic': True,
                               'path': str(target), 'files': {key: runner.fixture.digest(raw) for key, raw in runner.support.snapshot(target).items()}})
        for config in ('with_skill', 'old_skill'):
            run = output / task['name'] / config
            shutil.copytree(output / 'inputs' / task['name'], run / 'workspace')
            (run / 'outputs').mkdir()
            prompt = (
                '这些是明确标记的合成需求，已有人用旧PRD，分析侧已更新。请按当前权威分析逐需求增量同步，保留未变条目原字节与编号，'
                '使用工具分配新增编号，不要整篇润色。若存在缺口，核对原描述、唯一接收问题和实际分析内容，充分或有明确不再需要依据才关闭；'
                '只有交接或回答但缺少所需内容则保留并说明，暂定补足保留标注、假设依据和验证方式。'
                '本任务不授权修改analysis、其他元数据块、发布、安装或Git操作。若你加载的Skill明确不支持同步，请说明能力边界并保持工作稿不变，勿绕过其边界自写实现。'
                '仅使用给定Skill目录中的生产工具，不读测试源码、人工参考、其他运行或preparation-only。'
                f'工作区为 {run / "workspace"}，各场景为独立合成需求，不能合并；产物和最终说明保存到 {run / "outputs"}。'
                '同步候选、补丁、工具响应及修正过程另存在本run的artifacts目录，每轮失败保留，最多连续修正3次。'
                '请在outputs下保存每份最终PRD、trace和gap副本，以及model-response.md（逐场景的完成或拒绝、缺口依据、警告和路径）。'
            )
            skill_root = source if config == 'with_skill' else baseline
            metadata = {'eval_id': task['id'], 'eval_name': task['name'], 'config': config, 'prompt': prompt,
                        'skill_root': str(skill_root), 'input_root': str(run / 'workspace'), 'assertions': []}
            runner.fixture.write_json(run / 'eval_metadata.json', metadata)
        runner.fixture.write_json(output / task['name'] / 'eval_metadata.json', {'eval_id': task['id'], 'eval_name': task['name'], 'prompt': '按当前权威分析定向同步各隔离需求，逐缺口核实充分性，其他边界不变。', 'assertions': []})
    manifest = {'stage': 4, 'execution': 'model_input_preparation', 'model_invocation': False, 'baseline': str(baseline),
                'current_source': str(source), 'tasks': tasks, 'inputs': provenance,
                'source_fingerprints': {str(path.relative_to(source)): runner.fixture.digest(path.read_bytes()) for path in sorted(source.rglob('*')) if path.is_file()}}
    runner.fixture.write_json(output / 'input-provenance.json', manifest)
    return manifest


def main(argv=None):
    """从argv读取iteration根与旧快照并冻结输入，返回0；参数及文件冲突错误直接报告。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    args = parser.parse_args(argv)
    result = prepare(args.output.absolute(), args.baseline.absolute())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

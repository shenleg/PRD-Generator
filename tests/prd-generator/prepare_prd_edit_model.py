"""冻结阶段5模型输入和新旧Skill；不提供程序候选、人工参考或预设后续回答。"""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location('edit_model_inputs', Path(__file__).with_name('run_prd_edits.py'))
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)


def prepare(output):
    """在已建 iteration 根的新子目录冻结输入和当前源码，返回清单；已有路径或准备失败抛异常。

    output 应含旧版 old-skill-snapshot；只准备本地合成资料，不运行模型、不修改正式需求或旧证据。
    """
    source = output / 'current-skill-snapshot'
    shutil.copytree(ROOT / 'skill', source, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    scripts = source / 'prd-generator/scripts'
    tasks = [{'id': 1, 'name': 'request-routing', 'cases': ['content-request', 'ambiguous-request', 'layout-request', 'manual-layout']},
             {'id': 2, 'name': 'manual-content', 'cases': ['manual-item', 'manual-scope']}]
    assertions = {
        'request-routing': ['内容请求仅建议回交且产物不变', '含义变化措辞不按排版直接保存', '纯排版实际保存0.2并有layout_edit',
                            '手工纯排版经比较后处理', '编号引用和分析目录保持', '编辑后摘要与正文基准一致'],
        'manual-content': ['手工内容变化有实际比较及检测事件', '首轮没有预先保留或撤销用户修改', '用户回答后两份均保存成对不一致',
                           '遗留项及校验明确不得发布', '编号引用和分析目录保持', '处理后摘要一致且保留事件']}
    provenance = []
    for task in tasks:
        for case in task['cases']:
            folder = output / 'preparation-only' / case
            root = runner.prepare_case(folder, scripts)
            text = (root / 'prd/prd.md').read_bytes().decode()
            if case == 'manual-layout':
                text = text.replace('用户可以', '**用户可以**')
            elif case == 'manual-item':
                text = text.replace('当前筛选结果', '全部数据')
            elif case == 'manual-scope':
                text = text.replace('<!-- prd:section scope -->\n分析结果中无此项', '<!-- prd:section scope -->\n允许跨租户导出')
            (root / 'prd/prd.md').write_bytes(text.encode())
            target = output / 'inputs' / task['name'] / case
            shutil.copytree(root, target)
            provenance.append({'task': task['name'], 'case': case, 'synthetic': True, 'path': str(target), 'files': runner.snapshot(target)})
        if task['name'] == 'request-routing':
            request = ('请分别处理四份独立的合成需求：content-request：把导出当前筛选结果改为导出全部数据；'
                       'ambiguous-request：帮我润色，把“用户可以导出当前筛选结果”改成“系统必须自动导出当前筛选结果”；'
                       'layout-request：把“用户可以导出当前筛选结果”润色为“用户可导出当前筛选结果”，不改变任何规则；'
                       'manual-layout：我已经手工给功能中的“用户可以”加粗，请核对确实只有这项排版改动后处理。')
        else:
            request = ('manual-item 和 manual-scope 两份独立需求的文档都被我手工改过。'
                       '请检查实际改动，记录检测结果并告诉我下一步应该怎么处理；先不要替我保留、撤回或修改分析。'
                       '如果需要我决定，请具体说明并提问，然后停下等待回答。')
        for config in ('with_skill', 'old_skill'):
            run = output / task['name'] / config
            shutil.copytree(output / 'inputs' / task['name'], run / 'workspace')
            (run / 'outputs').mkdir()
            (run / 'artifacts').mkdir()
            skill_root = source if config == 'with_skill' else output / 'old-skill-snapshot'
            prompt = (request + '\n这些输入明确为合成验证，不代表真实业务。按你加载的Skill能力处理；若Skill明确不支持编辑，说明边界并保持工作稿不变，不自写实现绕过边界。'
                      '只使用给定Skill目录内的生产工具；不读测试源码、人工参考、preparation-only、其他运行或其他版本的Skill。'
                      '不修改analysis、common、其他元数据块，不发布、安装、Git操作或删除文件。'
                      '候选、逐次脚本JSON响应和运行命令保存在本run的artifacts中，最多连续修正三次，失败材料保留。'
                      f'加载的Skill根是 {skill_root}；工作区是 {run / "workspace"}；最终说明保存到 {run / "outputs/model-response.md"}。'
                      '最终说明逐场景区分实际保存、拒绝、警告、未执行，不把AI语义判断冒充人工评审。'
                      '不要在候选中顺带润色其他内容。')
            metadata = {'eval_id': task['id'], 'eval_name': task['name'], 'config': config, 'prompt': prompt,
                        'skill_root': str(skill_root), 'assertions': assertions[task['name']]}
            runner.fixture.write_json(run / 'eval_metadata.json', metadata)
        runner.fixture.write_json(output / task['name'] / 'eval_metadata.json',
                                  {'eval_id': task['id'], 'eval_name': task['name'], 'prompt': request, 'assertions': assertions[task['name']]})
    manifest = {'stage': 5, 'execution': 'model_input_preparation', 'model_invocation': False,
                'source_fingerprints': runner.snapshot(source), 'tasks': tasks, 'inputs': provenance}
    runner.fixture.write_json(output / 'input-provenance.json', manifest)
    return manifest


def main(argv=None):
    """从 argv 取得已有 iteration 根并准备新子目录，返回0；路径冲突与输入失败直接报告。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    result = prepare(args.output.absolute())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

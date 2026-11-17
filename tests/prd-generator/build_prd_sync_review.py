"""汇总阶段4实际模型评分并调用Skill Creator生成静态评审页；不自制HTML或代签语义认可。"""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


def _json(path):
    """读取可信评分或运行记录path并返回对象；文件及解析错误原样抛出，不填造缺失指标。"""
    return json.loads(path.read_text())


def _new_json(path, value):
    """将value新建到path，不覆盖已封存报告；路径、序列化或已存在错误原样抛出。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def build(iteration, report, creator):
    """汇总iteration的两组实际运行到新report并返回评审路径；creator为已安装Skill Creator目录。

    使用其官方聚合函数及generate_review.py；只复制展示副本，不改变模型原件。
    缺评分、计时或实际输出时失败，不把未执行记录当完成；外部脚本错误原样抛出。
    """
    report.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('sync_benchmark_aggregate', creator / 'scripts/aggregate_benchmark.py')
    aggregate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aggregate)
    configs = {'with_skill': [], 'old_skill': []}
    runs = []
    view = report / 'view-data'
    for eval_id, task in ((1, 'directed-items'), (2, 'gap-resolution')):
        for index, config in enumerate(configs, 1):
            source = iteration / task / config
            grading, timing, metadata = (_json(source / filename) for filename in ('grading.json', 'timing.json', 'eval_metadata.json'))
            metrics = _json(source / 'metrics.json')
            location = source / 'execution-location.json'
            actual = source / _json(location)['archived_trial'] if location.exists() else source / 'completed-trial' if (source / 'completed-trial/workspace').is_dir() else source
            target = view / f'{eval_id}-{task}-{index:02d}-{config}'
            outputs = target / 'outputs'
            outputs.mkdir(parents=True)
            # 评审器只嵌入outputs直接文件，因此平铺真实最终文件的原字节副本，不改模型自己的目录布局。
            for case_index, requirement in enumerate(sorted((actual / 'workspace').iterdir()), 1):
                for file_index, filename in enumerate(('prd.md', 'prd-trace.json', 'gap-requests.json'), 1):
                    shutil.copy2(requirement / 'prd' / filename, outputs / f'{case_index:02d}-{file_index:02d}-{requirement.name}-{filename}')
            shutil.copy2(actual / 'outputs/model-response.md', outputs / 'model-response.md')
            _new_json(target / 'eval_metadata.json', metadata)
            _new_json(target / 'grading.json', grading)
            value = {'eval_id': eval_id, 'run_number': 1, **grading['summary'],
                     'time_seconds': timing['total_duration_seconds'], 'tokens': timing['total_tokens'],
                     'tool_calls': metrics['total_tool_calls'], 'errors': metrics.get('errors_encountered', 0),
                     'expectations': grading['expectations'], 'notes': ['语义仍待人工评审；原始执行、worktree路径调整及当前源码重放分别留证。']}
            configs[config].append(value)
            runs.append({'eval_id': eval_id, 'eval_name': task, 'configuration': config, 'run_number': 1,
                         'result': {key: value[key] for key in ('pass_rate', 'passed', 'failed', 'total', 'time_seconds', 'tokens', 'tool_calls', 'errors')},
                         'expectations': grading['expectations'], 'notes': value['notes']})
    benchmark = {'metadata': {'skill_name': 'prd-generator', 'executor_model': 'opus（Agent工具配置）',
                 'analyzer_model': '主线程程序汇总', 'timestamp': datetime.now(timezone.utc).isoformat(),
                 'evals_run': [1, 2], 'runs_per_configuration': 1,
                 'skill_path': str(iteration / 'current-skill-snapshot/prd-generator')},
                 'runs': runs, 'run_summary': aggregate.aggregate_results(configs),
                 'notes': ['旧Skill尚未实现同步，正确拒绝只表示能力边界；不能据此证明相对其他已实现方案的质量优势。',
                           '每组每配置一次运行，不可解释为统计稳定性；计时包括隔离路径调整和证据整理。',
                           '未变字节与文件归属等保护断言也可在正确拒绝时通过；完成断言、缺口去留和标签断言共同区分实际同步。',
                           '条目组实际成功前有环境阻断及取消启动，原件均保留；这里统计最终有真实保存的任务，不是首次成功率或全量尝试成功率。',
                           '条目组使用current-source-retry，缺口组使用current-skill-snapshot；随后用最终当前源码分别重放真实成功候选，不冒充新模型调用。',
                           '模型报告中“已人工逐章”只计AI辅助核对，不能作为用户人工认可；自然语言忠实性、缺口充分性及旧稿整章保护降级仍须用户审阅。']}
    _new_json(report / 'benchmark.json', benchmark)
    with (report / 'benchmark.md').open('x', encoding='utf-8') as stream:
        stream.write(aggregate.generate_markdown(benchmark))
    html = report / 'review.html'
    subprocess.run([sys.executable, '-I', '-B', str(creator / 'eval-viewer/generate_review.py'), str(view), '--skill-name', 'prd-generator 阶段4', '--benchmark', str(report / 'benchmark.json'), '--static', str(html)], check=True)
    return {'benchmark': str(report / 'benchmark.json'), 'review': str(html), 'model_outputs': str(view)}


def main(argv=None):
    """从argv读取实际运行、全新报告目录和评审工具位置，返回0；参数或材料缺失直接报告。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--skill-creator', type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(build(args.iteration.absolute(), args.report.absolute(), args.skill_creator.absolute()), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

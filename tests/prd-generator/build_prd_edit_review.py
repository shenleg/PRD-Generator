"""使用 Skill Creator 官方汇总和评审工具生成阶段5静态页面，不自行绘制评测图表。"""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


CREATOR = Path('/home/collin/.claude/skills/skill-creator')


def build(workspace):
    """为已评分 workspace 写官方benchmark及静态review，返回页面；缺工具或运行失败抛异常。

    workspace 为本阶段新建的评审目录。仅调整两组各一次的真实样本数和展示顺序，不增造运行。
    """
    spec = importlib.util.spec_from_file_location('official_edit_benchmark', CREATOR / 'scripts/aggregate_benchmark.py')
    aggregate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aggregate)
    results = aggregate.load_run_results(workspace)
    ordered = {name: results[name] for name in ('with_skill', 'old_skill')}
    aggregate.load_run_results = lambda _: ordered
    benchmark = aggregate.generate_benchmark(workspace, skill_name='prd-generator', skill_path='skill/prd-generator')
    benchmark['metadata'].update(runs_per_configuration=1, executor_model='sonnet (Agent tool alias; exact served model ID not exposed)', analyzer_model='deterministic artifact grading')
    benchmark['notes'] = ['每配置每组仅一次，共四份模型执行，不是稳定通过率估计。',
                          '保护断言通过不证明语义分流正确，人工仍需看实际差异。',
                          '旧Skill按已声明边界拒绝不是程序故障，但不计编辑完成。',
                          '时间与token保留通知原值；部分run有后续轮及调度暂停，不据此作效率结论。',
                          '用户坚持保留的回答来自已批准合成剧本，不是真实业务签核。']
    (workspace / 'benchmark.json').write_text(json.dumps(benchmark, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (workspace / 'benchmark.md').write_text(aggregate.generate_markdown(benchmark), encoding='utf-8')
    page = workspace / 'review.html'
    subprocess.run([sys.executable, str(CREATOR / 'eval-viewer/generate_review.py'), str(workspace),
                    '--skill-name', 'prd-generator', '--benchmark', str(workspace / 'benchmark.json'), '--static', str(page)], check=True)
    return page


def main(argv=None):
    """读取 argv 指定的评审工作区并生成页面，返回0；已有材料由调用方按新目录组织。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args(argv)
    print(build(args.workspace.absolute()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

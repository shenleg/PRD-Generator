"""依据已归档的真实模型文件评分客观边界，准备官方评审工具输入；不把字符串检查当语义验收。"""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location('edit_grade_runner', Path(__file__).with_name('run_prd_edits.py'))
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)
_WRITER_SPEC = importlib.util.spec_from_file_location('edit_grade_writer', ROOT / 'skill/prd-generator/scripts/write_draft.py')
writer = importlib.util.module_from_spec(_WRITER_SPEC)
_WRITER_SPEC.loader.exec_module(writer)


def events(root):
    """读取已留证追加事件并返回列表；缺失或格式错误原样抛出，不造成功记录。"""
    return [json.loads(line) for line in (root / 'prd/prd-events.jsonl').read_text().splitlines() if line.strip()]


def intact(initial, final):
    """验证分析、非prd元数据及追溯身份保持，返回保护断言；读取错误原样抛出。"""
    analysis = runner.snapshot(initial / 'analysis') == runner.snapshot(final / 'analysis')
    old, new = runner.fixture.read_json(initial / 'requirement.json'), runner.fixture.read_json(final / 'requirement.json')
    old.pop('prd'); new.pop('prd')
    old_trace, new_trace = runner.fixture.read_json(initial / 'prd/prd-trace.json'), runner.fixture.read_json(final / 'prd/prd-trace.json')
    return analysis and old == new and old_trace['items'] == new_trace['items'] and old_trace['meta']['counters'] == new_trace['meta']['counters']


def saved(root, event_type):
    """核对实际版本、事件及非失败校验，返回是否成功保存；不代替含义核对。"""
    metadata = runner.fixture.read_json(root / 'requirement.json')
    result = writer._module('validate_prd').validate_prd(root)
    return metadata['prd']['version'] == '0.2' and any(item['change_type'] == event_type for item in events(root)) and result['status'] != 'fail'


def hash_matches(root):
    """检查正文摘要和比较基准均为当前原始正文，返回断言；读取/结构错误原样抛出。"""
    trace = runner.fixture.read_json(root / 'prd/prd-trace.json')
    raw = (root / 'prd/prd.md').read_bytes()
    return trace['meta']['content_hash'] == runner.fixture.digest(raw) and trace['meta'].get('content_baseline') == raw.decode('utf-8')


def grade(iteration, output):
    """评分 iteration 中四份已完成运行并写新 output 评审目录，返回摘要；缺实际产物时抛异常。

    output 已存在拒绝覆盖。首轮/后续、旧Skill正确拒绝及保护断言分开，不把未支持功能计为完成。
    """
    output.mkdir(parents=True, exist_ok=False)
    summaries = []
    for eval_id, group in ((1, 'request-routing'), (2, 'manual-content')):
        for config in ('with_skill', 'old_skill'):
            run = iteration / group / config
            completed = run / 'completed-trial'
            workspace = completed / 'workspace'
            if not workspace.is_dir():
                raise ValueError('缺少实际完成归档：' + str(completed))
            initial = run / 'workspace'
            cases = sorted(path.name for path in workspace.iterdir() if path.is_dir())
            notes, checks = [], []
            def check(text, passed, evidence):
                """追加带实际证据的客观断言，不以叙述替代文件检查。"""
                checks.append({'text': text, 'passed': bool(passed), 'evidence': evidence})
            if group == 'request-routing':
                for case, label in (('content-request', '内容修改请求未直接改稿'), ('ambiguous-request', '含义变化措辞未按排版保存')):
                    check(label, runner.snapshot(initial / case) == runner.snapshot(workspace / case),
                          f'{case}：初始与实际最终目录全部原始文件摘要比较；交接表述及理由另由人工阅读。')
                for case, label in (('layout-request', '纯措辞润色实际保存为0.2并记录layout_edit'),
                                    ('manual-layout', '手工排版经实际比较后保存为0.2')):
                    check(label, saved(workspace / case, 'layout_edit'), f'{case}/requirement.json、prd-events.jsonl及当前源码校验。')
                check('所有需求的编号引用、分析与其他元数据保持', all(intact(initial / case, workspace / case) for case in cases),
                      '逐需求比较分析全目录、requirement.json除prd块、trace.items及counters。')
                check('两份排版处理后正文摘要和基准一致', all(saved(workspace / case, 'layout_edit') and hash_matches(workspace / case)
                                                                  for case in ('layout-request', 'manual-layout')),
                      '需要实际排版保存；旧版保持未处理的手工排版不能因未写文件算完成。')
                notes.append('前两项只证明未越权写入，具体范围/触发条件分流理由仍须人工评审；旧Skill正确拒绝不算程序故障。')
            else:
                first = run / 'first-round-trial/workspace'
                first_unchanged = all(all(value == runner.snapshot(first / case).get(name) for name, value in runner.snapshot(initial / case).items()
                                          if name != 'prd/prd-events.jsonl') for case in cases)
                detected = all(any(item['change_type'] == 'manual_edit_detected' and item.get('handling') == 'detect' for item in events(first / case)) for case in cases)
                check('两份手改首轮均记录实际检测事件', detected,
                      '首轮事件中manual_edit_detected/handling=detect；原始检测响应和diff保存在artifacts。')
                check('首轮未提前保留或撤回用户手改', first_unchanged,
                      '首轮与输入除追加事件外的全部文件原字节比较；模拟回答在实际提问后才提供。')
                marked = all(saved(workspace / case, 'manual_edit_detected') and bool(writer._module('validate_prd').manual_inconsistencies(
                    (workspace / case / 'prd/prd.md').read_text(), 'SYNTHETIC-PRD')) for case in cases)
                check('模拟用户坚持后两份均保存不一致标注', marked,
                      '检查真实最终0.2版本、事件、原内容标注及结构化配对；模拟回答不是真实业务签核。')
                blocked = all(any('不得发布' in item['message'] for item in writer._module('validate_prd').validate_prd(workspace / case)['diagnostics']) for case in cases)
                check('对应遗留项及校验明确不得发布', marked and blocked,
                      '当前校验器逐目标检查配对并输出warning，不声称执行阶段6发布API。')
                no_empty_notice = all(writer._without_empty_residual_notice((workspace / case / 'prd/prd.md').read_text()) ==
                                      (workspace / case / 'prd/prd.md').read_text() for case in cases)
                check('新增遗留项后不再声称无遗留项', marked and no_empty_notice,
                      '真实模型发现的附加质量断言：原最终稿仍有空集合提示；修复后原首候选另行当前源码重放，不改写原模型产物。')
                check('编号引用、分析与其他元数据保持', all(intact(initial / case, workspace / case) for case in cases),
                      '比较分析目录、非prd元数据、trace.items与counters。')
                check('处理后正文摘要一致且保留检测事件', all(hash_matches(workspace / case) for case in cases) and detected and marked,
                      '比较当前正文原字节、content_hash和content_baseline，并核对首轮及最终事件。')
                notes.append('遗留说明是否充分、保留是否忠于用户手改仍须人工阅读；PG-19完整发布拒绝未执行。')
            review = output / f'eval-{eval_id}-{group}' / config / 'run-1'
            outputs = review / 'outputs'
            outputs.mkdir(parents=True)
            for file in (completed / 'outputs').iterdir():
                if file.is_file():
                    shutil.copyfile(file, outputs / file.name)
            for case in cases:
                for relative, suffix in [('prd/prd.md', 'final.md'), ('prd/prd-trace.json', 'trace.json'),
                                         ('analysis/analysis-result.json', 'analysis.json'), ('prd/prd-events.jsonl', 'events.jsonl')]:
                    shutil.copyfile(workspace / case / relative, outputs / f'{case}-{suffix}')
                initial_text = (initial / case / 'prd/prd.md').read_bytes()
                final_text = (workspace / case / 'prd/prd.md').read_bytes()
                comparison = writer._module('render_info').compare_content(final_text, {'meta': {'content_hash': runner.fixture.digest(initial_text),
                                                                                              'content_baseline': initial_text.decode()}})
                (outputs / f'{case}-actual-diff.txt').write_text(comparison['diff'], encoding='utf-8')
            metadata = runner.fixture.read_json(run / 'eval_metadata.json')
            runner.fixture.write_json(review / 'eval_metadata.json', metadata)
            runner.fixture.write_json(review.parent.parent / 'eval_metadata.json', {'eval_id': eval_id, 'eval_name': group, 'prompt': metadata['prompt']})
            if (run / 'timing.json').exists():
                shutil.copyfile(run / 'timing.json', review / 'timing.json')
            count = sum(item['passed'] for item in checks)
            result = {'expectations': checks, 'summary': {'passed': count, 'failed': len(checks)-count, 'total': len(checks), 'pass_rate': count/len(checks)},
                      'claims': [{'claim': '已获最终人工语义验收', 'type': 'quality', 'verified': False, 'evidence': '本脚本不代签，待用户评审。'}],
                      'user_notes_summary': {'uncertainties': notes, 'needs_review': ['语义分流、措辞不改含义、保留手改及遗留说明充分性'],
                                             'workarounds': ['模型运行于私有worktree，完成后归档；原共享输入保持原样。']},
                      'eval_feedback': {'overall': '每配置每组仅一次运行，不能据此估计稳定通过率；文件保护断言不区分语言分流质量。'}}
            runner.fixture.write_json(review / 'grading.json', result)
            summaries.append({'task': group, 'config': config, **result['summary']})
    runner.fixture.write_json(output / 'grading-summary.json', summaries)
    return summaries


def main(argv=None):
    """读取 argv 中iteration和新输出目录并评分，返回0；缺真实证据或路径冲突直接报告。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(grade(args.iteration.absolute(), args.output.absolute()), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

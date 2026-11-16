"""模拟业务方结束后保存当前结果；保留未回答核心问题，不再追问或替业务裁决。"""

import json
from pathlib import Path


TRIAL=Path('/root/orca/projects/test-skill/workspace-sandbox/stage-4/simulated-trial-01')
DIRECTORY=TRIAL/'workspace/projects/office-procurement/requirements/SIM-PROCUREMENT-001'
analysis=json.loads((DIRECTORY/'analysis/analysis-result.json').read_text())
statement=json.loads((TRIAL/'driver/scenario.json').read_text())['business_answer_bank']['stop']
patch=dict(patch_version='1.0',requirement_id='SIM-PROCUREMENT-001',base_revision=analysis['meta']['analysis_revision'],change_type='supplement',actor='user',user_statement=statement,summary='模拟业务方明确结束；只结束追问，不回答Q-12、不接受风险、不关闭研发事项。',operations=[],set={'meta.analysis_status':'completed','meta.readiness':'not_ready'},completion_checks=analysis['completion_checks'])
dialogue=dict(assistant_message='已停止追问。当前方案已明确创建人权限、可撤状态、执行时并发判定、逐条部分失败、原编号草稿与新审批轮次、最多20条输入、重试不重复执行及最小日志信息。Q-12已撤回项的成功/失败汇总分类仍未回答，保持P0/open；Q-10/Q-11为研发能力待核查。完成清单第4、6、7项仍未满足，analysis_status=completed、readiness=not_ready，仅交接风险初稿。',asked_questions=[],control_questions=[])
for relative,value in [('driver/stop.json',dict(provided_answers=[],user_input=statement)),('candidates/round-05.json',patch),('dialogue/round-05.json',dialogue)]:
    path=TRIAL/relative;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

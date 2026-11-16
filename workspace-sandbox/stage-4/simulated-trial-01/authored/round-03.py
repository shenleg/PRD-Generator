"""吸收第二轮模拟业务回答，明确批次、审批衔接和输入域，继续澄清重试及日志。"""

import json
from pathlib import Path


TRIAL=Path('/root/orca/projects/test-skill/workspace-sandbox/stage-4/simulated-trial-01')
DIRECTORY=TRIAL/'workspace/projects/office-procurement/requirements/SIM-PROCUREMENT-001'
analysis=json.loads((DIRECTORY/'analysis/analysis-result.json').read_text())
bank=json.loads((TRIAL/'driver/scenario.json').read_text())['business_answer_bank']
topics=['batch_result','approval_resubmit','selection_and_limit']
answers=[dict(topic=t,statement=bank[t]) for t in topics]
statement='\n'.join(a['statement'] for a in answers)
source=[dict(type='user_answer',location='模拟业务方第2轮回答；助手构造，非真实用户产品决定')]
operations=[]


def update(target, **changes):
    """只登记当前 target 字段变化，交真实脚本校验保存；返回空，不执行写入。"""
    operations.append(dict(op='update',target=target,changes=changes))


def add(collection, alias, content, refs, tag='confirmed'):
    """使用第2轮实际模拟输入形成新条目；返回空，不分配正式编号。"""
    operations.append(dict(op='add',collection=collection,ref=alias,value=dict(content=content,tag=tag,status='active',sources=source,related_ids=refs)))


for target,topic in [('Q-5','batch_result'),('Q-8','approval_resubmit'),('Q-6','selection_and_limit')]:
    update(target,status='answered',answer=bank[topic],reason='模拟业务方第2轮已明确回答，保留原问题与本轮实际输入。')
add('requirements.business_rules','$batch','逐条处理；不能撤的保持不变，不因一条失败回滚其他成功项。结果列成功数、失败数，每条失败给申请编号和原因；无权限不得泄漏申请详情。',['FR-1','Q-5','BR-6'])
add('requirements.business_rules','$approval','撤回成功后旧审批待办失效，审批人再操作明确提示申请已撤回且不再生效。原编号重提开启新审批轮次，不复用上次通过结果，各轮历史记录均保留。',['FR-1','Q-8','BR-5','BR-10'])
add('requirements.business_rules','$selection','只处理本次勾选的可见行，不是筛选全量；翻页不保留勾选。沿用模拟业务方明确的单页最多20条，一批最多20条；空选不发请求，超过20条的请求整体拒绝且不改变任何申请。服务端仍须校验实际权限与状态。',['FR-1','Q-6','BR-8'])
update('BND-2',content='不同状态及执行时权限变化的混选批次按逐条执行结果处理，保留合法成功项，失败项不变且不给出无权访问的详情。',tag='confirmed',sources=source,related_ids=['$batch','BR-7','BR-8','BR-9'])
update('BND-3',content='本次输入只含当前页明确勾选的可见申请，翻页清空勾选；0条不发送、1至20条进入逐条判断、超过20条整体拒绝且全不变。20来自第2轮模拟回答，不是分析者推定的系统事实。',tag='confirmed',sources=source,related_ids=['$selection'])
update('FLOW-1',content='创建人从当前页勾选申请（空选不提交，超过20条整体拒绝）→逐条以执行时状态与权限判定→成功回原编号草稿、旧审批待办失效，失败项不变→展示逐条与汇总结果→修改后以原编号发起新审批轮次，保留各轮历史。',status='active',tag='inferred',sources=[dict(type='user_answer',location='模拟业务方第1、2轮回答')],related_ids=['FR-1','BR-7','BR-8','BR-9','BR-10','$batch','$approval','$selection'])
update('GAP-1',content='初始状态、权限、并发、重提衔接和输入范围已明确；重复操作业务预期Q-7与最小日志口径Q-9仍待回答，研发能力Q-10/Q-11仍待核查。',sources=source,related_ids=['Q-7','Q-9','Q-10','Q-11'])
add('requirements.acceptance_criteria','$acbatch','一批混有合法与不合法申请时，合法项成功撤回，失败项不变，不整批回滚；反馈成功数、失败数和各失败项原因，权限失败不泄露详情。',['$batch','BR-7','BR-8'],tag='inferred')
add('requirements.acceptance_criteria','$acapproval','撤回后用旧待办审批应提示已撤回且不生效；修改后以原编号重提应开启新一轮审批，不能直接沿用上次通过结果，旧轮记录仍可查。',['$approval','BR-10'],tag='inferred')
add('requirements.acceptance_criteria','$acselection','检查空选择不提交、翻页后不保留勾选；分别提交1、20和21条：合法边界批次逐条判断，21条整体拒绝且任一申请均未改变。',['$selection'],tag='inferred')
refs={4:['Q-7'],6:['Q-7'],7:['Q-7'],11:['Q-9']}
patch=dict(patch_version='1.0',requirement_id='SIM-PROCUREMENT-001',base_revision=analysis['meta']['analysis_revision'],change_type='supplement',actor='user',user_statement=statement,summary='吸收第2轮已发生的模拟回答，补齐混选结果、旧审批失效与重提、新输入边界；不提前回答重复操作及日志问题。',operations=operations,set={'meta.analysis_status':'clarifying','meta.readiness':'not_ready'},completion_checks=[dict(item=i,satisfied=i not in refs,question_refs=refs.get(i,[]),reason=('重复操作结果仍影响核心规则与验收。' if i<=7 else '逐条日志预期尚未确认。') if i in refs else '原文及前两轮实际模拟输入已可表达；历史未对照、技术未核实和界面设计缺资料均明确登记。') for i in range(1,12)])
questions={q['id']:q for q in analysis['questions']}
asked=[dict(ref=target,topic=topic,**{k:questions[target][k] for k in ['question','priority','options','recommendation']}) for target,topic in [('Q-7','repeat_and_audit'),('Q-9','repeat_and_audit')]]
dialogue=dict(assistant_message='已理解：批次逐条成功或失败、失败不回滚其他成功项；旧审批失效，原编号重提开启新轮次；只处理当前页勾选、最多20条，21条整体拒绝。这些数量来自本轮模拟回答。剩余两项要问：重复点击/重试的业务结果和留痕，以及沿用日志的最小追溯信息。当前接口和并发实现仍交研发核查，不请产品承诺技术方案。',asked_questions=asked,control_questions=[])
for relative,value in [('driver/answer-02.json',dict(provided_answers=answers,user_input=statement)),('candidates/round-03.json',patch),('dialogue/round-03.json',dialogue)]:
    path=TRIAL/relative;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

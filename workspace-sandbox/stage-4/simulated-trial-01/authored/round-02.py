"""主会话吸收第一轮实际给出的模拟回答，保存补丁并提出第二轮问题；非独立盲测。"""

import json
from pathlib import Path


TRIAL=Path('/root/orca/projects/test-skill/workspace-sandbox/stage-4/simulated-trial-01')
DIRECTORY=TRIAL/'workspace/projects/office-procurement/requirements/SIM-PROCUREMENT-001'
analysis=json.loads((DIRECTORY/'analysis/analysis-result.json').read_text())
bank=json.loads((TRIAL/'driver/scenario.json').read_text())['business_answer_bank']
topics=['eligible_status_and_destination','permission','concurrency']
answers=[dict(topic=t,statement=bank[t]) for t in topics]
statement='\n'.join(a['statement'] for a in answers)
operations=[]
source=[dict(type='user_answer',location='模拟业务方第1轮回答；助手构造，非真实用户产品决定')]


def update(target, **changes):
    """登记对已保存 target 的字段变化；返回空，不执行正式写入或吞掉异常。"""
    operations.append(dict(op='update',target=target,changes=changes))


def add(collection, alias, content, refs, tag='confirmed'):
    """按第一轮已给出的模拟证据登记新条目；返回空，不填正式编号。"""
    operations.append(dict(op='add',collection=collection,ref=alias,value=dict(content=content,tag=tag,status='active',sources=source,related_ids=refs)))


for target,topic in [('Q-1','eligible_status_and_destination'),('Q-2','permission'),('Q-3','concurrency'),('Q-4','eligible_status_and_destination')]:
    update(target,status='answered',answer=bank[topic],reason='模拟业务方第1轮已明确；Q-4为状态回答中主动补充的撤回去向及编号，不重复追问。' if target=='Q-4' else '模拟业务方第1轮明确回答；保留原始问题与实际模拟答案。')
for target in ['BR-1','BR-2']:
    update(target,status='to_reassess',reason='该原文候选口径已被第1轮模拟裁决否定或限定，保留原文来源，不再视为现行规则。')
update('CNF-1',status='to_reassess',reason='Q-1已裁决；保留初始冲突证据，当前口径由新规则单独表达。')
add('requirements.business_rules','$allowed','仅待审批，以及审批通过但尚未下单的申请允许撤回；已下单、执行采购、收货完成、已取消均不允许。',['FR-1','Q-1'])
add('requirements.business_rules','$permission','本期只有申请创建人能撤回自己的申请；采购管理员不能代撤，不新增其他角色或代办权限，批量入口不扩大既有可见范围。',['FR-1','Q-2','BR-4'])
add('requirements.business_rules','$race','按每条申请真正执行时的最新状态和权限判定。下单先成功则撤回失败并提示状态已变化、未撤回；撤回先成功则后续基于旧状态的下单或审批不得再成功；审批通过但未下单仍可撤回。',['FR-1','Q-3'])
add('requirements.business_rules','$destination','撤回成功后原申请回到草稿，保留原申请编号与各次已存在的审批历史，允许修改后重新提交；旧待办及重提轮次尚待Q-8确认。',['FR-1','Q-4','BR-5'])
update('BND-1',content='并发业务预期已明确：逐条按执行时最新状态和权限判断，下单与撤回只能按有效先后结果生效；具体实现机制仍待研发核查。',tag='confirmed',sources=source,related_ids=['$race','Q-11'])
add('requirements.acceptance_criteria','$aceligible','创建人对自己待审批或通过未下单的申请成功撤回后，原申请回草稿、编号不变、原审批历史仍可查。',['$allowed','$permission','$destination'],tag='inferred')
add('requirements.acceptance_criteria','$acinvalid','非创建人、无权访问或执行时处于已下单/执行采购/收货完成/已取消状态的申请不能被撤回，不因批量入口扩大可见范围或改变该申请。',['$allowed','$permission'],tag='inferred')
add('requirements.acceptance_criteria','$acrace','分别让下单和撤回先成功：前者后续撤回失败并显示状态变化，后者后续旧状态下单/审批不再成功；审批先通过但未下单仍满足可撤范围。',['$race'],tag='inferred')
refs={3:['Q-8'],4:['Q-5','Q-6','Q-7'],6:['Q-5','Q-6','Q-7'],7:['Q-5','Q-6','Q-7','Q-8'],11:['Q-9']}
patch=dict(patch_version='1.0',requirement_id='SIM-PROCUREMENT-001',base_revision=analysis['meta']['analysis_revision'],change_type='supplement',actor='user',user_statement=statement,summary='仅吸收模拟业务方第1轮状态、权限、并发回答，撤回去向是该回答主动补充；不提前使用其他答案。',operations=operations,set={'meta.analysis_status':'clarifying','meta.readiness':'not_ready'},completion_checks=[dict(item=i,satisfied=i not in refs,question_refs=refs.get(i,[]),reason=('仍需澄清审批衔接、混选输入或重复操作，核心验收未完整。' if i<=7 else '逐条日志业务预期待确认。') if i in refs else '依据原文及第1轮已给出的模拟回答满足；历史对照未做、技术能力待研发、界面依赖已登记。') for i in range(1,12)])
questions={q['id']:q for q in analysis['questions']}
asked=[]
for target,topic in [('Q-5','batch_result'),('Q-8','approval_resubmit'),('Q-6','selection_and_limit')]:
    q=questions[target]
    asked.append(dict(ref=target,topic=topic,**{k:q[k] for k in ['question','priority','options','recommendation']}))
dialogue=dict(assistant_message='已理解：仅创建人可撤自己的待审批或通过未下单申请，执行时重验权限和状态；成功回原编号草稿，并发时以有效先后结果判定，技术实现待研发。原文互斥候选不再作当前规则。下一轮只问三件事：部分失败如何保留与反馈、旧审批及重提如何衔接、一次选择的准确输入范围与边界。',asked_questions=asked,control_questions=[])
for relative,value in [('driver/answer-01.json',dict(provided_answers=answers,user_input=statement)),('candidates/round-02.json',patch),('dialogue/round-02.json',dialogue)]:
    path=TRIAL/relative;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

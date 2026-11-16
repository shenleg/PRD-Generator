"""吸收第三轮重复操作与日志的模拟回答；识别并登记尚未回答的汇总分类衍生缺口。"""

import json
from pathlib import Path


TRIAL=Path('/root/orca/projects/test-skill/workspace-sandbox/stage-4/simulated-trial-01')
DIRECTORY=TRIAL/'workspace/projects/office-procurement/requirements/SIM-PROCUREMENT-001'
analysis=json.loads((DIRECTORY/'analysis/analysis-result.json').read_text())
bank=json.loads((TRIAL/'driver/scenario.json').read_text())['business_answer_bank']
statement=bank['repeat_and_audit']
source=[dict(type='user_answer',location='模拟业务方第3轮回答；助手构造，非真实用户产品决定')]
operations=[]


def update(target, **changes):
    """登记已有 target 的本轮变化；返回空，所有实际写入由更新器完成。"""
    operations.append(dict(op='update',target=target,changes=changes))


def add(collection, alias, content, refs, tag='confirmed', status='active'):
    """登记由本轮模拟证据支持的条目；返回空，编号由脚本分配。"""
    operations.append(dict(op='add',collection=collection,ref=alias,value=dict(content=content,tag=tag,status=status,sources=source,related_ids=refs)))


for target in ['Q-7','Q-9']:
    update(target,status='answered',answer=statement,reason='模拟业务方第3轮已回答重复撤回行为及最小审计信息；没有提供已撤回项的批次汇总分类。')
add('requirements.business_rules','$repeat','重复点击或网络重试时，已撤回申请不再执行撤回，返回已撤回，不重复写成功撤回日志。',['FR-1','Q-7'])
add('requirements.business_rules','$audit','沿用现有日志查询，不新增日志页面；至少可查操作人、时间、申请编号、原状态、新状态及逐条操作结果，失败原因也应可查询。现有能力是否具备仍由研发确认。',['CON-1','Q-9','Q-11'])
update('EXC-1',content='重复点击/网络重试遇到已撤回申请时，不再次执行，不重复成功撤回日志，返回已撤回；该项在成功/失败汇总中的分类尚待新问题确认。',tag='confirmed',sources=source,related_ids=['$repeat','$qaggregate'])
question=dict(question='已撤回的重复项，应计入成功数、失败数，还是另列“未执行/已撤回”数量？',priority='P0',resolution='ask_product',reason='Q-7已明确重复项不再次执行，Q-5此前要求成功/失败汇总；两条合在一起仍缺少重复项的汇总分类。这是新输出决策，不重复询问已明确的重试行为。',impact='同一批次含重复已撤回项时，无法判定成功/失败汇总的正确数字。',options=['计入失败，原因已撤回','计入成功，但说明未再次执行','单列未执行/已撤回','其他','暂不确定'],recommendation='建议单列未执行/已撤回，避免将未发生的撤回计为本次成功；需业务明确采用，当前仅是推荐。',status='open',related_ids=['BR-11','$repeat'])
operations.append(dict(op='add',collection='questions',ref='$qaggregate',value=question))
add('business_assessment.gaps','$aggregate','重复项不再次执行，但在成功/失败汇总中的归类未定；不能自行决定计成功、计失败或新增汇总分类。',['$qaggregate','BR-11','$repeat'],tag='inferred')
update('GAP-1',status='to_reassess',content='初始问题已由前三轮模拟回答处理；当前业务阻塞转由独立的新汇总分类缺口记录，研发能力仍待Q-10/Q-11核查。本条保留初始缺口的追溯，不作为未回答的原问题重复追问。',sources=source,related_ids=['$qaggregate','Q-10','Q-11'])
add('requirements.acceptance_criteria','$acretry','对已经成功撤回的申请重复提交时，应返回已撤回，不再次改变申请，不新增重复的成功撤回日志；该项汇总分类待Q-12，不把推荐选项当最终预期。',['$repeat','$qaggregate'],tag='inferred',status='to_reassess')
add('requirements.acceptance_criteria','$acaudit','成功与失败的逐条操作都能按申请编号查询到业务要求的操作人、时间、原新状态、结果及失败原因；不新增查询页面。',['$audit'],tag='inferred')
refs={4:['$qaggregate'],6:['$qaggregate'],7:['$qaggregate']}
patch=dict(patch_version='1.0',requirement_id='SIM-PROCUREMENT-001',base_revision=analysis['meta']['analysis_revision'],change_type='supplement',actor='user',user_statement=statement,summary='第3轮模拟回答明确重试不重复执行与审计信息；发现已撤回项汇总分类的新业务缺口，不以推荐补答案。',operations=operations,set={'meta.analysis_status':'clarifying','meta.readiness':'not_ready'},completion_checks=[dict(item=i,satisfied=i not in refs,question_refs=refs.get(i,[]),reason='含重复已撤回项的批次汇总分类未定，核心输出验收仍缺可判定口径。' if i in refs else '前三轮模拟输入和登记事项足以表达该项；研发能力未核实不等于业务规则未定。') for i in range(1,12)])
dialogue=dict(assistant_message='已理解：已撤回申请重试只返回已撤回，不再次执行或重复写成功日志；逐条审计信息明确且不新建日志页面。还发现一个新衍生问题：之前只定义成功/失败汇总，却没有定义“已撤回而未再次执行”的项归哪一类。这不是重问重试怎么处理，需要单独决定，当前保持未就绪。',asked_questions=[dict(ref='$qaggregate',topic='repeat_result_aggregation',**{k:question[k] for k in ['question','priority','options','recommendation']})],control_questions=[])
for relative,value in [('driver/answer-03.json',dict(provided_answers=[dict(topic='repeat_and_audit',statement=statement)],user_input=statement)),('candidates/round-04.json',patch),('dialogue/round-04.json',dialogue)]:
    path=TRIAL/relative;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

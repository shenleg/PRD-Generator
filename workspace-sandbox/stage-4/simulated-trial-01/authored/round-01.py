"""保存主会话本轮分析形成的首次补丁和对话；不模拟回答、不修改正式分析。"""

import json
from pathlib import Path


ROOT = Path('/root/orca/projects/test-skill')
TRIAL = ROOT / 'workspace-sandbox/stage-4/simulated-trial-01'
operations = []


def add(collection, alias, content, line, *, tag='confirmed', status='active', related=(), **extra):
    """构造本轮主会话分析条目并追加操作；line 定位输入条款，返回新增别名；不执行写入。"""
    value = dict(content=content, tag=tag, status=status, sources=[dict(type='input_document', source_id='$source', location=f'模拟原文第{line}条')], related_ids=list(related), **extra)
    operations.append(dict(op='add', collection=collection, ref=alias, value=value))
    return alias


def question(alias, text, priority, reason, impact, options, recommendation, related, resolution='ask_product'):
    """构造真实登记的问题；返回问题字典，缺键或非法调用由后续真实校验器报告。"""
    value=dict(question=text, priority=priority, resolution=resolution, reason=reason, impact=impact, options=options + ['其他', '暂不确定'], recommendation=recommendation, status='open', related_ids=related)
    operations.append(dict(op='add', collection='questions', ref=alias, value=value))
    return dict(ref=alias, **value)


operations.append(dict(op='add_source', ref='$source', value=dict(name='办公采购申请批量撤回（模拟原始记录）', path=str(ROOT/'tests/fixtures/stage-4-procurement-withdrawal.md'), type='input_document', credibility='助手构造的模拟业务输入，非真实产品决定', last_updated=None, revision=1)))
add('requirements.goals','$goal','减少申请填错或重复提交后，员工找采购同事退回的来回沟通；不编造节省时间或收益数字。','1')
add('requirements.scenarios','$scenario','员工在现有采购申请网页列表中选择多条申请撤回，修正后重新提交；可操作角色与状态尚待澄清。','1、3',related=['$goal'])
add('requirements.functional_requirements','$function','在现有采购申请列表增加批量撤回能力；保留申请与审批历史，使申请能够修改后重新提交。','1、5',related=['$goal','$scenario'])
add('requirements.business_rules','$all','原文候选口径：提交过的申请都应该能撤回；不是已裁决的最终状态范围。','2',related=['$function'])
add('requirements.business_rules','$pending','原文候选口径：只有待审批的申请可以撤回；与同条其他说法冲突。','2',related=['$function'])
add('requirements.business_rules','$approved','原文候选口径：审批通过但还没下单的申请也应能撤回。','2',related=['$function'])
add('requirements.business_rules','$visibility','批量入口不能扩大既有数据可见范围；创建人与采购管理员的具体操作权限未定。','3',related=['$function'])
add('requirements.business_rules','$history','撤回不删除原申请，原审批记录必须保留。','5',related=['$function'])
add('requirements.business_rules','$partial','一批中存在不能撤回的申请时，不应卡住其他申请；需要给出成功数、失败数及失败原因。','4',related=['$function'])
add('requirements.constraints','$reuse','沿用现有网页列表与操作日志，不另建采购系统。','6',related=['$function'])
add('requirements.constraints','$nochange','本次不改变既有审批规则和采购下单规则。','6',related=['$function'])
add('requirements.scope.in_scope','$scopein','现有网页列表上的批量撤回及其结果反馈、申请保留和重提衔接。','1、4、5、6',related=['$function'],prefix='CON')
add('requirements.scope.out_of_scope','$scopeout','移动端与消息通知本期不做；不新建采购系统。','6',prefix='CON')
# prefix 属于操作协议而非条目值。
for operation in operations:
    if operation.get('collection','').startswith('requirements.scope.'):
        operation['prefix'] = operation['value'].pop('prefix')
add('business_assessment.flows','$flow','候选流程：选择申请→发起撤回→逐条反馈→修改后重新提交；成功后状态与旧审批衔接还未明确。','1、4、5',tag='inferred',status='to_reassess',related=['$function'])
add('business_assessment.boundaries','$race','候选并发边界：审批、下单与撤回同时发生时，需要可判定的最终结果；实现机制尚未评估。','5',tag='inferred',related=['$function'])
add('business_assessment.boundaries','$mixed','候选混选边界：一批包含不同状态或执行时已失去权限的申请；处理结果需逐条明确。','3、4、5',tag='inferred',related=['$function'])
add('business_assessment.boundaries','$selection','候选输入边界：选择范围、空选择、单次数量限制和超限结果尚未规定；不假设系统现有上限。','1、4',tag='inferred',related=['$function'])
add('business_assessment.exceptions','$repeat','候选异常：重复点击或网络重试可能重复撤回或写重复日志，业务预期尚未确定。','1、5、6',tag='inferred',related=['$function'])
q1=question('$qstatus','最终允许撤回哪些状态的申请？','P0','原文第2条的全部已提交、仅待审批及通过未下单三种口径互相矛盾。','无法判定合法撤回状态。',['仅待审批','待审批和审批通过但未下单'],'建议待审批及通过未下单均可，能满足更正诉求，但必须由业务确认。',['$all','$pending','$approved'])
q2=question('$qpermission','本期谁能撤回哪些人的申请？','P0','第3条明确未定创建人与管理员的权限。','可能引入越权批量操作。',['仅创建人撤自己的','创建人加采购管理员代撤'],'建议仅创建人，先保持最小权限边界。',['$visibility'])
q3=question('$qrace','撤回与审批或下单同时发生时，以什么业务结果判定成功或失败？','P0','原文禁止已购买后又撤回，但未规定按执行时还是页面快照判断及先后结果。','可能出现撤回与下单均成功的矛盾。',['执行时最新状态与权限逐条判定，先成功者生效','以页面打开时状态为准'],'建议以执行时最新状态判定，并明确先后动作的业务结果；实现方式交研发。',['$race','$function'])
question('$qdestination','撤回成功后原申请变为什么状态，重新提交是否沿用申请编号？','P0','可修改后重提没有定义状态和身份。','核心状态流程不能还原。',['原申请回草稿并沿用编号','产生新的申请'],'建议回草稿保留原申请编号，避免历史断链。',['$flow','$history'])
question('$qpartial','同批部分失败时，已成功项是否保留，结果逐条需要显示什么？','P0','不应卡住其他申请不等于已明确回滚和最终反馈。','无法验收混选批次。',['逐条处理，保留成功并给失败原因','任一失败则整批不变'],'建议逐条处理，与原文部分失败不阻塞意图一致。',['$partial','$mixed'])
question('$qselection','一次提交对应哪些已选申请，空选择、最大数量及超限时如何处理？','P0','未说明仅勾选、跨页或筛选全量；数量边界没有依据。','输入范围和边界验收不明确。',['只处理当前明确勾选的申请，明确单批边界','处理筛选结果全量'],'建议仅明确勾选范围；上限须业务结合实际列表确认，不能凭空给数。',['$selection'])
question('$qrepeat','重复点击或重试遇到已撤回申请时，业务结果和成功日志如何处理？','P0','重复撤回可能改变结果或重复留痕。','同一撤回的业务含义及重试验收不明确。',['返回已撤回，不再次撤回或重复成功留痕','按新撤回再次处理'],'建议已撤回不再执行，用可识别结果防重复。',['$repeat'])
question('$qapproval','撤回后旧审批待办如何失效，重提是否启动新审批轮次？','P0','历史保留不等于待办失效和重提流程明确。','旧审批可能继续生效或错误沿用上次结果。',['旧待办失效，重提开启新审批轮次','沿用原审批待办与通过结果'],'建议保留历史但开启新轮次，避免旧决定套用修改后的申请。',['$history','$flow'])
question('$qaudit','沿用日志时至少需要哪些可查询信息，本期是否需要新增查询页面？','P1','已有日志字段未提供，产品的最小追溯预期仍需说明。','影响操作追溯及范围。',['记录逐条操作与结果，沿用查询页面','只记录批次数量汇总'],'建议保留逐条结果以便追溯失败。',['$reuse'])
question('$qapi','是否有可复用的批量接口，现有权限与状态校验能否覆盖本次操作？','P1','原文第7条要求核查，未提供接口资料。','研发需确认复用范围，不能假设已有能力。',['已有且满足','需要新增或调整'],'由研发查接口及权限资料确认，不由产品保证实现。',['$function','$reuse'],resolution='ask_dev')
question('$qtech','现有状态变更、并发控制和日志字段能否支撑确认后的业务预期？','P1','尚无系统或技术资料。','影响实现与测试准备。',['现有能力满足','需要补充改造'],'研发核实能力与影响，不预设数据库锁或事务方案。',['$race','$repeat','$reuse'],resolution='ask_dev')
add('business_assessment.conflicts','$conflict','第2条同时出现全部已提交、仅待审批、通过但未下单也可撤回，当前无法视作同一状态规则。','2',tag='inferred',related=['$all','$pending','$approved'],related_question='$qstatus')
add('business_assessment.gaps','$gap','角色、撤回状态、并发先后、重提衔接及输入与重试边界未齐，无法形成完整核心验收。','2、3、4、5',tag='inferred',related=['$qstatus','$qpermission','$qrace','$qdestination','$qpartial','$qselection','$qrepeat','$qapproval'])
add('requirements.acceptance_criteria','$acdraft','验收草案：从现有列表选择合法申请撤回，保留申请及审批历史并显示逐条结果；合法状态、权限、并发和重试结果仍待确认，不能作为完整验收。','1、3、4、5',tag='inferred',status='to_reassess',related=['$function','$qstatus','$qpermission','$qrace','$qrepeat'])
refs={2:['$qpermission'],3:['$qdestination','$qapproval'],4:['$qstatus','$qpermission'],5:['$qstatus'],6:['$qrace','$qpartial','$qselection','$qrepeat'],7:['$qstatus','$qpartial','$qrepeat','$qapproval'],11:['$qaudit']}
patch=dict(patch_version='1.0',requirement_id='SIM-PROCUREMENT-001',title='办公采购申请批量撤回（模拟试用）',base_revision=0,change_type='initial_analysis',actor='analyst',summary='主会话首次分析模拟原文，登记状态冲突及权限、并发、衔接和边界缺口，未使用未来模拟回答。',operations=operations,set={'meta.input_type':'existing_document','meta.analysis_status':'clarifying','meta.readiness':'not_ready','context.project_id':'office-procurement','context.source_ids':['$source'],'value_assessment.problem':'填错或重复申请后需找采购同事退回，沟通往返。','value_assessment.affected_users':['申请员工','采购人员'],'value_assessment.expected_benefits':['减少修正申请的来回沟通'],'value_assessment.success_metrics':[],'ux_assessment.ui_dependent':True,'ux_assessment.design_pending_items':['批量入口与逐条结果呈现待设计；无具体视觉稿，不代定样式。']},completion_checks=[dict(item=i,satisfied=i not in refs,question_refs=refs.get(i,[]),reason={1:'目标与原因已由原文明确；不编造收益指标。',8:'本阶段未做历史检索与基线对照，已明确记录。',9:'已有接口、并发及日志能力登记ask_dev，未下技术可行性结论。',10:'明确依赖现有网页列表，缺少的交互设计资料已登记。'}.get(i,'对应核心或追溯问题尚未回答。')) for i in range(1,12)])
asked=[]
for q,topic in [(q1,'eligible_status_and_destination'),(q2,'permission'),(q3,'concurrency')]:
    asked.append({k:q[k] for k in ['ref','question','priority','options','recommendation']}|dict(topic=topic))
dialogue=dict(assistant_message='当前理解：在现有采购网页列表提供批量撤回，减少误填或重复申请的沟通；保留申请和审批历史，不扩可见权限。原文撤回状态矛盾，权限和并发预期未定。首轮先确认可撤状态、谁可操作、与审批下单并发的业务结果；不先决定界面样式或技术方案。',asked_questions=asked,control_questions=[])
for relative,value in [('candidates/round-01.json',patch),('dialogue/round-01.json',dialogue)]:
    path=TRIAL/relative;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')

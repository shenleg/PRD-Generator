"""将人工撰写的需求陈述序列化为编号补丁与候选正文。"""
import json, pathlib, subprocess
O=pathlib.Path(__file__).parent
P=O/'skill/prd-generator/scripts'
REQ=O/'skill/requirement-analyst/scripts/requirements.txt'
PY=['uv','run','--offline','--no-project','--python','/usr/bin/python3','--with-requirements',str(REQ),'python','-I','-B']
# 每项内容按需求分析独立整理；方括号中的分析编号用于建立追溯。
DATA={
'002':{
'GOAL-1':'任务列表内容增多时，帮助用户找到目标任务。',
'SCN-1':'用户在仿真任务列表中查找目标任务；具体角色未区分。',
'FR-1':'任务列表应支持按常用条件筛选；条件清单及含义尚待确认。',
'NFR-1':'筛选应快；实际规模及可接受响应时间尚未确定。',
'CON-1':'尽快上线，本期尽量不影响仿真引擎；这不是确定发布日期或绝对禁止引擎修改。',
'AC-1':'待条件、匹配及响应口径确认后，以已知样本核对单条件、多条件、清空、无结果和失败，并在双方确认的负载下测量响应。',
'FLOW-1':'候选流程：进入列表、设置条件、触发筛选、查看结果；触发方式和匹配语义未定。',
'BND-1':'未选或清空条件、多条件和无匹配时的可见范围待确认；不能默认交集或全部用户任务。',
'EXC-1':'筛选失败或耗时较长时，旧结果是否有效以及如何区分失败和空结果待确认。',
'overview':'本稿仅组织列表筛选；删除、状态、导出和通知分别成稿。此为分析拆分，不代表其他功能被排除。'},
'003':{
'GOAL-1':'提供对选中作业的批量删除；需求来源未说明更具体的价值原因。',
'SCN-1':'用户选中作业后点击删除；相关角色及授权存在冲突。',
'FR-1':'支持选中作业后批量删除；跨页选择及删除后的数据状态未定义。',
'BR-1':'原文称批量删除所有用户均可操作；该陈述与另一删除权限陈述存在待解冲突，不作为最终授权。',
'BR-2':'原文称工程创建者和管理员可以删除任务，其他人只能看；适用对象与前述作业是否相同待确认。',
'BR-3':'删除按之前逻辑处理，但旧逻辑未提供；不能推断软硬删除、结果保留或运行中处理。',
'CON-1':'要求尽快上线，本期尽量不影响仿真引擎；不是硬期限或绝对禁止引擎变更。',
'AC-1':'待对象关系、授权、删除效果及批量失败策略确认后，验证授权与未授权用户对选中集合的操作及关联结果，覆盖运行中、对象不存在、混合权限和重复执行。',
'FLOW-1':'已知动作仅为选中作业并点击删除；权限识别、执行处理及结果呈现是待确认的候选流程。',
'BND-1':'运行中对象能否删除、对执行及结果的影响未知；不默认停止任务或软删除。',
'BND-2':'未选、跨页、筛选变更、混合权限及对象已被删除时，实际选中和删除集合待定义。',
'EXC-1':'部分对象不可删除、权限或状态变化、部分失败及重复操作时，整批拒绝还是部分成功待定。',
'overview':'本稿共同讨论批量删除、删除权限及既有删除处理，避免遗漏其相互关系；不把作业和任务视为已经确认的同一对象。'},
'004':{
'GOAL-1':'修复任务状态显示不准确，并使展示及时反映进展。',
'SCN-1':'用户查看任务状态时曾遇到显示不正确；触发条件、位置及实际与预期值缺失。',
'FR-1':'修复任务状态有时显示不正确的问题；受影响入口和正确状态规则待明确。',
'NFR-1':'状态应实时；实际变化到用户可见的可接受延迟未定义。',
'CON-1':'尽快上线且本期尽量不影响仿真引擎；未确认发布日期或引擎修改方案。',
'AC-1':'根据用户提供的复现样例和状态规则核对实际与显示，并测量更新延迟；覆盖连续变化、重新进入和更新不可用。预期及阈值未确认前不能验收。',
'FLOW-1':'候选流程为实际状态变化后界面展示相应状态；状态集合、转移和延迟仍待定义。',
'BND-1':'连续变化、任务结束或失败、重新进入时可能出现旧状态或遗漏；需明确可见状态及回退规则。',
'EXC-1':'无法获取最新状态或更新中断时，旧状态如何标识、恢复后如何核对均待确认。',
'overview':'本稿讨论状态正确性及更新预期；结束通知另成稿，不能代替状态修复。受影响页面尚未确定。'},
'005':{
'GOAL-1':'改善仿真结果导出不方便的问题，提供表格导出。',
'SCN-1':'用户导出仿真结果；单任务、所选任务或其他范围，以及任务是否必须完成均未确定。',
'FR-1':'仿真结果应能以表格导出常用字段；字段、行粒度与文件格式待确认。',
'BR-1':'原文称最多导出1000条；这是数量冲突的一方，不可自行认定为最终截断规则。',
'BR-2':'原文又称数据量大时导出全部结果、不要丢数据；全部的对象、授权及时间范围尚未定义。',
'CON-1':'格式需与之前的报告一致；旧报告缺失，不能指定 CSV、XLSX 或固定列。',
'CON-2':'尽快上线且本期尽量不影响仿真引擎；没有硬期限或绝对禁改引擎的约束。',
'AC-1':'待对象、数量、权限、内容及一致性确认后，按已知有权结果集逐行核对字段和格式；覆盖空结果、1000条、超1000条、未完成、权限不足、数据变化和部分失败。',
'FLOW-1':'候选流程为选定有权结果范围、发起导出、等待并取得表格；范围、权限和输出内容均待确认。',
'BND-1':'未完成或失败任务的部分结果能否导出待定，不能将仿真结果直接等同于已完成最终结果。',
'BND-2':'可导出的工程、任务及字段范围未知；删除权限不能自动推广为导出权限。',
'BND-3':'空结果、恰好1000条和超过1000条均需确认处理；大量数据的等待及超时策略未知。',
'EXC-1':'读取、生成或下载部分失败时，成功与部分成功如何判定待定义，不能静默漏行。',
'EXC-2':'导出期间数据或权限变化时，全部结果对应的时间点待确认；不假定已有快照能力。',
'overview':'本稿覆盖结果表格、字段、格式、数量和完整性；不将全部解释为所有用户的结果，也不凭空排除其他格式。'},
'006':{
'GOAL-1':'任务跑完后向用户发送通知；原文未说明更具体的价值原因。',
'SCN-1':'任务结束后某类用户收到通知；接收者身份尚未确定。',
'FR-1':'任务跑完后发送通知；触发状态、接收对象、渠道、内容及送达预期待确认。',
'CON-1':'尽快上线，本期尽量不影响仿真引擎；未给出硬期限或通知实现机制。',
'AC-1':'待触发、对象、渠道及内容确认后，分别核对应通知和不应通知的任务，以及重复事件、权限变化和发送失败；目前不能判定送达预期。',
'FLOW-1':'候选流程为达到确认的结束条件、识别有权接收者、通过确认渠道发送；各环节尚未确定。',
'BND-1':'失败、取消、重试再次结束及重复事件是否触发通知、次数如何计算均待定。',
'BND-2':'接收者离开工程、任务不可访问或通知包含敏感结果时，接收权限与可见内容待确认。',
'EXC-1':'用户不在线、渠道不可用或发送失败时的记录、重试及业务处理未规定。',
'overview':'本稿独立讨论任务结束通知；触发语义需与状态需求最终确认的结束语义一致，不代表排除其他通知。'} }
K={'GOAL':'goal','SCN':'scenario','FR':'functional_requirement','BR':'business_rule','CON':'constraint','NFR':'non_functional_requirement','AC':'acceptance_criterion','FLOW':'flow','BND':'boundary','EXC':'exception'}
S={'GOAL':'background','SCN':'scenarios','FR':'functional_requirements','BR':'business_rules','CON':'constraints','NFR':'constraints','AC':'acceptance_criteria','FLOW':'flows_states','BND':'boundaries_exceptions','EXC':'boundaries_exceptions'}
SECTIONS=[('background','背景与目标'),('scope','范围'),('scenarios','场景'),('functional_requirements','功能需求'),('business_rules','业务规则'),('flows_states','流程'),('boundaries_exceptions','边界与异常'),('constraints','约束及非功能'),('acceptance_criteria','验收草案'),('ux','交互待定'),('technical','技术可行性'),('impact','影响分析'),('residuals','遗留事项'),('appendix','来源')]
def jwrite(path,val): path.write_text(json.dumps(val,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for suffix, texts in DATA.items():
 rid='REQ-2026-'+suffix; root=O/'workspaces'/rid; run=O/'runs'/rid; analysis=json.loads((root/'analysis/analysis-result.json').read_text());
 items=[{'mapping_key':k,'kind':K[k.split('-')[0]],'analysis_refs':[rid+'/'+k]} for k in texts if k!='overview']
 patch={'patch_version':'1.0','requirement_id':rid,'base_prd_version':None,'base_analysis_revision':1,'items':items}; jwrite(run/'patch.json',patch)
 args=PY+[str(P/'assign_ids.py'),str(root),'--patch',str(run/'patch.json')]; x=subprocess.run(args,capture_output=True,text=True); (run/'assign.stdout').write_text(x.stdout);(run/'assign.stderr').write_text(x.stderr)
 if x.returncode: print(rid,'assign fail',x.stdout,x.stderr); continue
 trace=json.loads(x.stdout); entries={i['mapping_key']:i for i in trace['items']}; sections={k:[] for k,_ in SECTIONS}; sections['scope'].append(texts['overview']); sections['business_rules'].append('未列为已确认规则的细节均需澄清，不应推定。'); sections['technical'].append('技术可行性未覆盖；需研发核实现有能力与引擎影响。');sections['impact'].append('影响分析未覆盖；需确认范围和依赖。'); sections['ux'].append('现有界面资料不足，交互方案待业务规则确认后确定。'); sections['appendix'].append('依据：本需求 analysis/analysis-result.json，分析修订 1；源资料以 analysis/source-manifest.json 为准。')
 for key,val in texts.items():
  if key=='overview': continue
  entry=entries[key]; pid=entry['prd_id']; labels=('【推断】' if entry['tag']=='inferred' else '【暂定】' if entry['tag']=='assumption' else '')+('【待确认】' if entry['status']=='to_confirm' else '')
  sections[S[key.split('-')[0]]].append(f'<!-- prd:item {pid} -->\n**{pid}** {labels}{val} 依据：{rid}/{key}\n<!-- /prd:item -->')
 # 遗留引用保留原分析表述和问题文本，防止丢失限定及待确认项。
 def rec(obj):
  if isinstance(obj,dict):
   if 'id' in obj and (obj.get('tag')=='inferred' or obj['id'].startswith(('GAP-','CNF-'))):
    ref=rid+'/'+obj['id']; sections['residuals'].append(f'<!-- prd:residual {ref} -->\n{ref}【推断】{obj.get("content","")}\n<!-- /prd:residual -->')
   for v in obj.values(): rec(v)
  elif isinstance(obj,list):
   for v in obj: rec(v)
 rec({k:analysis[k] for k in ['requirements','business_assessment']})
 for q in analysis['questions']:
  if q['status'] in ('open','provisional','risk_accepted'):
   ref=rid+'/'+q['id'];sections['residuals'].append(f'<!-- prd:residual {ref} -->\n{ref} {q["priority"]} 待答：{q["question"]}\n<!-- /prd:residual -->')
 for n,value in enumerate(analysis['ux_assessment']['design_pending_items']):
  ref=f'/ux_assessment/design_pending_items/{n}';sections['residuals'].append(f'<!-- prd:residual {ref} -->\n界面待定：{value}\n<!-- /prd:residual -->')
 body='\n\n'.join(f'<!-- prd:section {key} -->\n## {title}\n\n'+('\n\n'.join(sections[key]) or '尚无已确认内容。')+'\n<!-- /prd:section -->' for key,title in SECTIONS)+'\n';(run/'body.md').write_text(body)
 jwrite(run/'gaps.json',{'schema_version':'1.0','requirement_id':rid,'counters':{'GAPREQ':0},'requests':[]})
 print(rid,'prepared')

"""将人工选定的表述与分析问题序列化为独立候选，并运行冻结脚本。"""
import json
import subprocess
from pathlib import Path

O = Path(__file__).resolve().parent.parent
S = O / 'skill/prd-generator/scripts'
REQ = O / 'skill/requirement-analyst/scripts/requirements.txt'
UV = ['uv','run','--offline','--no-project','--python','/usr/bin/python3','--with-requirements',str(REQ),'python','-I','-B']
# 每条正文为依据分析单独选定的表述，保留原有不确定性及冲突。
DATA = {
'003': [
('goal','goal','GOAL-1','goal','为选中的作业提供批量删除；删除效果与授权未定，新增价值原因未单独说明。'),
('scenario','scenario','SCN-1','scenario','用户选中作业后点击删除；原文分别提到工程创建者、管理员及其他用户，授权陈述冲突。'),
('delete','functional_requirement','FR-1','functional','作业支持选中后批量删除；跨页选择与删除后数据状态未说明。'),
('scope','functional_requirement','FR-2','scope','【推断】在同一删除动作下分析批量删除、删除权限和既有处理规则；作业与任务是否同一对象未确认，不表示合并概念。没有明确排除项。'),
('all_users','business_rule','BR-1','rule','原文称所有用户都可以操作作业批量删除；这不是最终授权规则。'),
('creators','business_rule','BR-2','rule','原文又称工程创建者和管理员可以删除任务、其他人只能看；不能推广至其他功能的权限。'),
('previous','business_rule','BR-3','rule','删除需按之前的逻辑处理，但该逻辑未提供；不能推断删除方式、运行中处理或结果保留。'),
('constraint','constraint','CON-1','constraint','尽快上线且本期尽量不影响仿真引擎；没有硬期限，也非绝对禁止引擎变更。'),
('acceptance','acceptance_criterion','AC-1','acceptance','【推断】【待确认】确认对象、授权、删除效果和批量失败策略后，使用授权及未授权用户核对所选对象与关联结果状态，并覆盖运行中、已不存在、混合权限和重复执行；目前不能判定删除成功。'),
('flow','flow','FLOW-1','flow','【推断】【待确认】已知操作只有选中作业并点击删除；识别对象及权限、执行处理和呈现结果仍是候选步骤。'),
('running','boundary','BND-1','boundary','【推断】运行中任务是否允许删除，以及对仿真执行和结果的影响未定；不能据引擎约束推断软删除或停止任务。'),
('selection','boundary','BND-2','boundary','【推断】未选、跨页、筛选变化及所选对象含无权限或已删除对象时，实际删除集合需明确，避免误删。'),
('failure','exception','EXC-1','boundary','【推断】权限或状态变化、部分不允许或失败以及重复点击时，是整批拒绝还是部分成功未定；成功反馈不能掩盖未删除或误删。')],
'004': [
('goal','goal','GOAL-1','goal','修复状态显示不准确，并及时反映任务进展；准确性判定和实时阈值尚未给出。'),
('scenario','scenario','SCN-1','scenario','用户查看任务状态时曾有显示错误；复现步骤、任务阶段、位置和实际及预期值均缺失。'),
('fix','functional_requirement','FR-1','functional','修复之前有时任务状态显示不对的问题。'),
('scope','functional_requirement','FR-2','scope','【推断】本稿处理状态正确性与用户可见更新预期；完成通知另行分析，不能代替状态修复。受影响页面未定，未提及页面不自动排除。'),
('constraint','constraint','CON-1','constraint','尽快上线且本期尽量不影响仿真引擎；没有确定日期，也未确认可以或必须修改引擎。'),
('realtime','non_functional_requirement','NFR-1','constraint','状态要实时；从实际变化到用户可见更新的可接受延迟未定义。'),
('acceptance','acceptance_criterion','AC-1','acceptance','【推断】【待确认】根据用户提供的复现场景及状态规则核对实际变化和显示，检查错误不再出现并测量可见延迟；覆盖连续变化、重新进入及更新不可用。缺少预期值与延迟口径，尚非完整验收。'),
('flow','flow','FLOW-1','flow','【推断】【待确认】候选流程为任务实际状态变化后界面展示相应状态；状态集合、转移及延迟未定，流程无法完整验收。'),
('boundary','boundary','BND-1','boundary','【推断】快速连续变化、结束或失败及重新进入时可能出现旧状态或漏掉中间状态；应保留哪些状态与哪些回退非法需业务定义。'),
('failure','exception','EXC-1','boundary','【推断】更新中断时旧状态可能被误认为当前状态；显示最后已知、未知或其他反馈及恢复后的核对方式尚未确认。')],
'005': [
('goal','goal','GOAL-1','goal','改善仿真结果导出不方便的问题，提供表格导出。'),
('scenario','scenario','SCN-1','scenario','用户希望导出仿真结果；是单个任务、所选任务还是其他范围尚不明确，也未限定必须完成。'),
('export','functional_requirement','FR-1','functional','支持将仿真结果导出成表格并包含常用字段；字段和文件格式未给出。'),
('scope','functional_requirement','FR-2','scope','【推断】本稿覆盖导出字段、格式、数量和完整性，不把全部扩展为所有用户的结果；未明确提出的格式或方式不自动排除。'),
('limit','business_rule','BR-1','rule','原文称最多导出1000条；这是冲突一方，不是最终截断规则。'),
('all','business_rule','BR-2','rule','原文称数据量大时导出全部结果、不要丢数据；大量及全部的对象、授权和时间范围未定义。'),
('oldformat','constraint','CON-1','constraint','格式需与之前的报告一致；旧报告缺失，不能指定 CSV、XLSX 或固定列。'),
('constraint','constraint','CON-2','constraint','尽快上线且本期尽量不影响仿真引擎；不是硬期限或绝对不改引擎。'),
('acceptance','acceptance_criterion','AC-1','acceptance','【推断】【待确认】业务规则确认后，核对有权导出结果的行、字段和格式，覆盖空结果、1000条、超过1000条、未完成、权限不足、数据变化及部分失败，避免静默截断或漏行；当前仅为验收草案。'),
('flow','flow','FLOW-1','flow','【推断】【待确认】候选流程为选定有权访问的结果范围、发起导出、等待生成并取得表格；范围、权限、生命周期、数量和内容均未定。'),
('lifecycle','boundary','BND-1','boundary','【推断】未完成、失败或只有部分结果时能否导出待确认；当时结果不等同于完整最终结果。'),
('permission','boundary','BND-2','boundary','【推断】可导出的工程、任务和字段范围未知；不能把删除权限推广到导出，也不将全部理解为无授权跨用户访问。'),
('quantity','boundary','BND-3','boundary','【推断】空结果、恰好及超过1000条均需处理；大量结果的等待、超时和分批策略未定，不能自行设上限或截断。'),
('failure','exception','EXC-1','boundary','【推断】读取、生成或下载部分失败时，成功与部分成功的含义需确认，不能静默漏行。'),
('consistency','exception','EXC-2','boundary','【推断】导出期间结果产生、删除或权限变化时，全量的时间点未定；不假定已有快照能力。')],
'006': [
('goal','goal','GOAL-1','goal','在任务跑完后通知用户；具体要解决的问题未说明。'),
('scenario','scenario','SCN-1','scenario','任务跑完后某类用户收到通知；接收者是提交者、工程创建者、关注者还是其他人未说明。'),
('notify','functional_requirement','FR-1','functional','任务跑完后发送通知；触发状态、对象、渠道、内容与送达预期未给出。'),
('scope','functional_requirement','FR-2','scope','【推断】独立分析结束通知，不合并到状态显示；触发含义需与最终确认的结束语义一致。其他通知场景不视为已排除。'),
('constraint','constraint','CON-1','constraint','尽快上线且本期尽量不影响仿真引擎；没有硬期限，也未确定通知机制。'),
('acceptance','acceptance_criterion','AC-1','acceptance','【推断】【待确认】确认触发、对象、渠道和内容后，分别测试应通知及不应通知的状态，核对正确接收者在指定渠道收到可识别任务与结果的通知；覆盖重复事件、权限变化和发送失败。送达预期尚不能判定。'),
('flow','flow','FLOW-1','flow','【推断】【待确认】候选流程为任务达到已确认结束条件、识别有权接收者、通过已确认渠道发送并识别任务与结果；这些规则仍未确认。'),
('events','boundary','BND-1','boundary','【推断】失败、取消、重试再结束及重复事件是否触发、属于同一次完成与否尚待规则；不能固定发送次数。'),
('permission','boundary','BND-2','boundary','【推断】接收者离开工程、无法访问任务或通知含敏感结果时，接收对象与可见内容需匹配；不能援引删除权限默认通知可见性。'),
('failure','exception','EXC-1','boundary','【推断】用户离线、渠道不可用或发送失败时是否重试、记录失败未定；不假设现有通知平台或重试次数。')]
}

def run(script, args, out):
    """运行冻结脚本并保存输出；参数为脚本名、参数和记录路径，返回退出码及响应。"""
    p = subprocess.run(UV + [str(S / (script + '.py'))] + list(map(str,args)), capture_output=True, text=True)
    out.with_suffix('.stdout').write_text(p.stdout)
    out.with_suffix('.stderr').write_text(p.stderr)
    try: value = json.loads(p.stdout)
    except ValueError: value = {}
    return p.returncode, value

def main():
    """按人工文段生成四份候选并执行编号、写入、重复和校验；不修改分析。"""
    for suffix, rows in DATA.items():
        rid='REQ-2026-'+suffix; d=O/'workspaces'/rid; a=O/'artifacts'/rid
        analysis=json.loads((d/'analysis/analysis-result.json').read_text())
        patch={'patch_version':'1.0','requirement_id':rid,'base_prd_version':None,'base_analysis_revision':analysis['meta']['analysis_revision'],'items':[{'mapping_key':key,'kind':kind,'analysis_refs':[rid+'/'+ref]} for key,kind,ref,section,text in rows]}
        (a/'patch.json').write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n')
        rc, trace=run('assign_ids',[d,'--patch',a/'patch.json'],a/'assign')
        if rc: continue
        ids={x['mapping_key']:x['prd_id'] for x in trace['items']}
        def section(key,title,content): return '<!-- prd:section '+key+' -->\n# '+title+'\n'+content+'\n<!-- /prd:section -->\n\n'
        def item(row,table=False):
            key,kind,ref,sec,text=row; pid=ids[key]; source=rid+'/'+ref
            if table: return f'| <!-- prd:item {pid} -->{pid} | {text} | {source}<!-- /prd:item --> |'
            return f'<!-- prd:item {pid} -->{pid}：{text} 分析来源：{source}。<!-- /prd:item -->'
        def items(sec): return '\n\n'.join(item(r) for r in rows if r[3]==sec) or '分析结果中无此项。'
        def table(sec):
            matching=[r for r in rows if r[3]==sec]
            return '| 编号 | 内容 | 分析来源 |\n| --- | --- | --- |\n'+'\n'.join(item(r,True) for r in matching) if matching else '分析结果中无此项。'
        body='本文档基于未就绪的需求分析生成，存在未解决的阻塞问题，仅供沟通，不得作为开发或测试依据。\n\n'
        body+=section('info','文档信息','')+section('changes','变更记录','首次生成草稿。')
        value=analysis.get('value_assessment',{}); body+=section('background','背景与价值',value.get('problem','分析结果中无此项。')+' 未提供量化价值结论。')
        body+=section('scope','目标与范围',items('goal')+'\n\n'+items('scope'))
        body+=section('scenarios','用户与场景',items('scenario'))
        body+=section('functional_requirements','功能需求',table('functional'))
        body+=section('business_rules','业务规则',items('rule'))
        body+=section('flows_states','流程与状态',items('flow'))
        body+=section('boundaries_exceptions','边界与异常',items('boundary'))
        body+=section('constraints','约束与非功能需求',items('constraint'))
        body+=section('acceptance_criteria','验收条件',table('acceptance'))
        if analysis.get('ux_assessment',{}).get('ui_dependent'):
            body+=section('ux','界面与交互','具体设计资料与待确认事项见遗留事项；不能据此假定现有界面或渠道。')
        body+=section('technical','研发确认项','未开展技术可行性评估，具体研发核实事项见遗留事项。')
        residual=[]
        def add(ref,text): residual.append(f'<!-- prd:residual {ref} -->{ref}：{text}<!-- /prd:residual -->')
        for q in analysis.get('questions',[]):
            if q.get('status') in ('open','provisional','risk_accepted'):
                desc=f"{q.get('priority','')}，{q.get('resolution','')}，{q.get('status','')}：{q.get('question','')}"
                if q.get('recommendation'): desc+=' 建议（尚未采纳）：'+q['recommendation']
                if q.get('impact'): desc+=' 影响：'+q['impact']
                add(rid+'/'+q['id'],desc)
        for key in ('gaps','conflicts'):
            for x in analysis.get('business_assessment',{}).get(key,[]):
                if x.get('status')!='withdrawn': add(rid+'/'+x['id'],'【推断】'+x['content'])
        for key in ('assumptions','decisions'):
            for x in analysis.get(key,[]):
                if x.get('status')!='withdrawn': add(rid+'/'+x['id'],json.dumps(x,ensure_ascii=False))
        for row in rows:
            if '【推断】' in row[4]: add(rid+'/'+row[2],row[4])
        for i,x in enumerate(analysis.get('ux_assessment',{}).get('design_pending_items',[])): add('/ux_assessment/design_pending_items/'+str(i),x)
        body+=section('residuals','遗留事项','\n\n'.join(residual) or '分析结果中无此项。')
        body+=section('appendix','附录','领域词汇：'+ '、'.join(analysis['context'].get('domain_terms',[]))+'。来源：'+ '、'.join(analysis['context'].get('source_ids',[]))+'。未开展历史需求对照。')
        (a/'candidate.md').write_text(body)
        rc,result=run('write_draft',[d,'--patch',a/'patch.json','--body',a/'candidate.md','--candidate-dir',a/'run-1'],a/'write-1')
        if rc: continue
        (a/'prd-v0.1.md').write_bytes((d/'prd/prd.md').read_bytes()); (a/'trace-v0.1.json').write_bytes((d/'prd/prd-trace.json').read_bytes())
        patch['base_prd_version']=result['version']; (a/'patch-repeat.json').write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n')
        run('write_draft',[d,'--patch',a/'patch-repeat.json','--body',a/'candidate.md','--candidate-dir',a/'repeat'],a/'repeat')
        run('validate_prd',[d],a/'validate')

if __name__=='__main__': main()

"""为阶段4单测、公开CLI和模型任务准备隔离合成输入；不修改历史资料或真实需求。"""

from copy import deepcopy
from functools import lru_cache
import importlib.util
import json
from pathlib import Path

from prd_fixture_support import block, digest, make_workspace, read_json, refresh_hash, write_json


ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=None)
def load_script(name):
    """加载当前源码的生产name模块并返回；导入、依赖错误原样抛出，不跳过测试。"""
    spec = importlib.util.spec_from_file_location('sync_support_' + name, ROOT / 'skill/prd-generator/scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def refresh_section_sources(root):
    """按root明确构造的合成旧稿刷新章节依据并返回映射；只用于测试准备，文件或协议错误抛出。"""
    trace = read_json(root / 'prd/prd-trace.json')
    manifest_path = root / 'analysis/source-manifest.json'
    manifest = read_json(manifest_path) if manifest_path.exists() else []
    digests = load_script('validate_prd').section_source_digests(read_json(root / 'analysis/analysis-result.json'),
                read_json(root / 'prd/gap-requests.json'), trace=trace, source_manifest=manifest)
    trace['meta']['section_source_digests'] = digests
    write_json(root / 'prd/prd-trace.json', trace)
    return digests


def section_text(body, key):
    """从body取得key章节内文并返回；定位损坏或缺失抛出ValueError/KeyError。"""
    return load_script('write_draft')._parsed(body)['section'][key]['text']


def replace_section(body, key, content):
    """仅替换body中key章节内文为content并返回；定位错误原样抛出，不写业务文件。"""
    span = load_script('write_draft')._parsed(body)['section'][key]
    return body[:span['start']] + '\n' + content.strip('\n') + '\n' + body[span['end']:]


def row(pid, content, ref, suffix=''):
    """构造含pid/content/ref的功能表格行；suffix是适用标注，返回Markdown，无预期异常。"""
    return f'| <!-- prd:item {pid} -->{pid}：{content}；分析来源 {ref}{suffix}<!-- /prd:item --> | {ref} |'


def make_sync_workspace(root):
    """创建含两项功能的独立root合成旧稿并返回路径；已存在或写入错误原样抛出。"""
    root = make_workspace(root)
    analysis = read_json(root / 'analysis/analysis-result.json')
    second = deepcopy(analysis['requirements']['functional_requirements'][0])
    second.update(id='FR-2', content='合成导出功能，不代表真实业务')
    analysis['requirements']['functional_requirements'].append(second)
    write_json(root / 'analysis/analysis-result.json', analysis)
    trace = read_json(root / 'prd/prd-trace.json')
    extra = deepcopy(trace['items'][0])
    extra.update(prd_id='PRD-FR-002', mapping_key='synthetic-export', analysis_refs=['SYNTHETIC-PRD/FR-2'],
                 source_digest=digest([{'analysis_ref': 'SYNTHETIC-PRD/FR-2', 'item': second}]))
    trace['items'].append(extra)
    trace['meta']['counters']['FR'] = 2
    write_json(root / 'prd/prd-trace.json', trace)
    text = (root / 'prd/prd.md').read_text()
    text = replace_section(text, 'functional_requirements', section_text(text, 'functional_requirements') + '\n' + row('PRD-FR-002', second['content'], 'SYNTHETIC-PRD/FR-2'))
    (root / 'prd/prd.md').write_text(text, encoding='utf-8')
    refresh_hash(root)
    metadata = read_json(root / 'requirement.json')
    metadata['other_owner'] = {'keep': '不能覆盖其他块'}
    write_json(root / 'requirement.json', metadata)
    (root / 'analysis/analysis-events.jsonl').write_text(json.dumps({'revision': 1, 'requirement_id': 'SYNTHETIC-PRD', 'summary': '合成旧稿分析，非业务确认'}, ensure_ascii=False) + '\n', encoding='utf-8')
    refresh_section_sources(root)
    return root


def advance_analysis(root, change=None):
    """对root的合成分析递增修订并执行可选change回调，返回新版分析；错误原样抛出。"""
    analysis = read_json(root / 'analysis/analysis-result.json')
    analysis['meta']['analysis_revision'] += 1
    if change:
        change(analysis)
    write_json(root / 'analysis/analysis-result.json', analysis)
    with (root / 'analysis/analysis-events.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'revision': analysis['meta']['analysis_revision'], 'requirement_id': analysis['requirement_id'], 'summary': '合成指定分析变化，仅用于验证同步'}, ensure_ascii=False) + '\n')
    return analysis


def mapping_patch(root, additions=()):
    """返回root当前读时版本的独立编号补丁；additions仅为新增映射，不预分配编号，读写错误抛出。"""
    return {'patch_version': '1.0', 'requirement_id': 'SYNTHETIC-PRD',
            'base_prd_version': read_json(root / 'requirement.json')['prd']['version'],
            'base_analysis_revision': read_json(root / 'analysis/analysis-result.json')['meta']['analysis_revision'],
            'items': list(additions)}


def add_gap_fixture(root, *, question_status='open', gap_status='handed_over'):
    """向root合成旧稿登记唯一接收缺口，返回缺口文档；状态为测试输入，不代表真实分析接收。"""
    gap = {'id': 'GAPREQ-1', 'needed_for': 'acceptance_criteria', 'description': '查询功能的验收条件尚缺',
           'related_analysis_refs': ['SYNTHETIC-PRD/FR-1'], 'raised_in': '0.1', 'status': gap_status,
           'extension': {'keep': '缺口扩展'}}
    gaps = {'schema_version': '1.0', 'requirement_id': 'SYNTHETIC-PRD', 'counters': {'GAPREQ': 1}, 'requests': [gap], 'extension': '封装扩展'}
    write_json(root / 'prd/gap-requests.json', gaps)
    analysis = read_json(root / 'analysis/analysis-result.json')
    question = {'id': 'Q-1', 'question': '查询功能以什么条件验收？', 'priority': 'P3', 'resolution': 'ask_product',
                'reason': '合成验收缺口', 'impact': '仅供测试', 'options': ['补足', '不再需要'], 'recommendation': '先补分析',
                'status': question_status, 'related_ids': ['FR-1'], 'gap_request_ref': 'GAPREQ-1'}
    if question_status == 'answered':
        question['answer'] = '已收到回复；仍须核实有效分析条目，不能只凭这句关闭'
    analysis['questions'].append(question)
    write_json(root / 'analysis/analysis-result.json', analysis)
    text = (root / 'prd/prd.md').read_text()
    text = replace_section(text, 'acceptance_criteria', block('gap', 'GAPREQ-1', '待分析补充：查询功能的验收条件尚缺'))
    text = replace_section(text, 'residuals', '验收缺口 GAPREQ-1 尚未核实。')
    (root / 'prd/prd.md').write_text(text, encoding='utf-8')
    refresh_hash(root)
    refresh_section_sources(root)
    return gaps


def snapshot(root):
    """返回root所有业务文件的相对路径和原始字节，用于只读及文件归属断言；读取错误抛出。"""
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}

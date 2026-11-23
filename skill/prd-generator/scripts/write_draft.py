"""编排首稿、显式同步与经语义核对的编辑保存；复用候选、并发及恢复，不评审或发布。"""

import argparse
import base64
from collections.abc import Sequence
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import importlib.util
import json
import os
import re
from collections import Counter
from pathlib import Path
import sys
import tempfile


TARGETS = ("prd/prd.md", "prd/prd-trace.json", "prd/gap-requests.json", "requirement.json", "prd/prd-events.jsonl")
JOURNAL = "prd/.prd-transaction.json"
EXIT_CODES = {"pass": 0, "warning": 1, "fail": 2}


@lru_cache(maxsize=None)
def _module(name):
    """从可信的相邻生产文件加载模块，兼容 python -I 和任意调用目录。"""
    spec = importlib.util.spec_from_file_location("prd_writer_" + name, Path(__file__).resolve().with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _encode(value):
    """序列化结构化产物；拒绝非有限值，不改变正文原始字节。"""
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _safe(path):
    """拒绝符号链接，防止工作区写入越过用户指定的需求边界。"""
    if _module("validate_prd")._has_link(path):
        raise ValueError(f"不使用符号链接路径：{path}")


def _raw(path):
    """读取文件原始字节；不存在返回 None，其他路径与读取错误原样抛出。"""
    try:
        return _module("validate_prd")._read_bytes(path, link_message=f"不使用符号链接路径：{path}")
    except FileNotFoundError:
        return None


def _has_journal(root):
    """识别正常或链接形式的事务记录，不把悬空链接当作可写的空位。"""
    return os.path.lexists(root / JOURNAL)


def _hash(raw):
    """将可选文件快照转为原始字节摘要，缺文件保持 None。"""
    return None if raw is None else _module("render_info").content_hash(raw)


@contextmanager
def _lock(root):
    """锁定现有需求目录，与分析侧串行化同一需求的写入；不在 analysis/ 创建锁。"""
    _safe(root)
    with _module("validate_prd")._fs().requirement_lock(root):
        yield


def _atomic_write(path, raw, *, new_readonly=False):
    """准备后原子替换；定稿快照改用只读、不可替换的新建。"""
    _safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 快照临时名不进入 versions/，避免进程中断后未完成写入被误认成无发布记录的历史快照。
    temporary_dir = path.parent.parent if new_readonly else path.parent
    descriptor, name = tempfile.mkstemp(prefix=".prd-write-", dir=temporary_dir)
    temporary = Path(name)
    windows_snapshot = new_readonly and os.name == "nt"
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            if new_readonly and not windows_snapshot:
                os.fchmod(stream.fileno(), 0o444)
            os.fsync(stream.fileno())
        if windows_snapshot:
            # Windows rename 不覆盖同名目标。先关闭句柄并设只读，避免留下难以删除的只读硬链接。
            _module('validate_prd')._fs().set_snapshot_readonly(temporary, True)
            os.rename(temporary, path)
            temporary = None
        elif new_readonly:
            # POSIX rename 会替换同名目标，硬链接才可原子拒绝碰撞。
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
            temporary = None
        _module("validate_prd")._fs().sync_directory(path.parent)
    finally:
        # 失败时仅还原本调用的临时文件属性，不改目标或他人的事务。
        if temporary is not None and temporary.exists():
            if windows_snapshot:
                _module('validate_prd')._fs().set_snapshot_readonly(temporary, False)
            temporary.unlink()


def _diagnostic(message, path="$", rule=0):
    """构造保存层诊断，不冒用分析或 PRD 校验器的业务规则。"""
    return {"rule": rule, "level": "fail", "item_id": "$", "path": str(path), "message": str(message)}


def _guard_hash(path, optional=False):
    """记录读时文件状态；可选清单不可读时保留该状态供并发比较，不阻断已声明的降级。"""
    try:
        return _hash(_raw(path))
    except OSError as error:
        if not optional:
            raise
        return "unreadable:" + type(error).__name__


def _guards(root, related, sync=False, previous_analysis=None):
    """快照实际读取的权威及辅助资料；同步额外保护用于说明原因的分析事件。"""
    paths = [root / "analysis/analysis-result.json", root / "analysis/source-manifest.json"]
    if sync:
        paths.append(root / "analysis/analysis-events.jsonl")
    for path in (*related, *((previous_analysis,) if previous_analysis is not None else ())):
        paths.extend((Path(path), Path(path).with_name("source-manifest.json")))
    return [{"path": str(path.absolute()), "optional": path.name in ("source-manifest.json", "analysis-events.jsonl"),
             "sha256": _guard_hash(path, path.name in ("source-manifest.json", "analysis-events.jsonl"))} for path in dict.fromkeys(paths)]


def _check_guards(guards):
    """分析或来源在读取后变化即拒写；不靠改修订数字掩盖字节级并发。"""
    for guard in guards:
        if _guard_hash(Path(guard["path"]), guard.get("optional", False)) != guard["sha256"]:
            raise ValueError(f"读取后分析或来源已变化，重新读取后再生成：{guard['path']}")


def _read_json(path):
    """严格读取生产 JSON，不接受重复键或非有限值。"""
    return _module("validate_prd")._json(path)


def _release_targets(version):
    """从有效正式版本派生本需求的两个新建目标，拒绝工作稿或任意路径。"""
    if not isinstance(version, str) or not _module('validate_prd').VERSION.fullmatch(version) or version.startswith('0.') or version.endswith('-draft'):
        raise ValueError('快照目标必须使用正式发布版本号')
    return (f'prd/versions/prd-{version}.md', f'prd/versions/prd-trace-{version}.json')


def _snapshot_inputs(root, guards):
    """读取已有快照作为候选校验证据，同时保护原始字节不被并发替换。"""
    directory = root / 'prd/versions'
    _safe(directory)
    snapshots = {}
    fs = _module('validate_prd')._fs()
    for path in sorted(directory.iterdir()) if directory.exists() else ():
        if fs.is_link(path) or not path.is_file():
            raise ValueError(f'快照必须是普通文件：{path}')
        raw = _raw(path)
        if raw is None:
            raise ValueError(f'快照读取期间已变化：{path}')
        # 版本谱系比对的是跨平台协议键，不是操作系统的本地路径表示。
        snapshots[path.relative_to(root).as_posix()] = raw
        guards.append({'path': str(path), 'sha256': _hash(raw)})
    return snapshots


def _finish(root, journal):
    """校验事务各目标只处于读时或本事务写后状态，再向前完成；冲突保留 journal。"""
    entries = journal.get("entries", [])
    kind = journal.get('format')
    if kind == 'prd-draft-transaction-1':
        new_snapshots = ()
    elif kind == 'prd-release-transaction-1' and journal['result'].get('action') == 'release':
        new_snapshots = _release_targets(journal['result']['version'])
    else:
        raise ValueError('不识别 PRD 恢复记录，未执行任何业务写入')
    if [entry.get('path') for entry in entries] != list(new_snapshots + TARGETS):
        raise ValueError('事务写入目标不符合工作区协议')
    _check_guards(journal["guards"])
    pending = []
    for entry in entries:
        data = base64.b64decode(entry["data"], validate=True)
        if _hash(data) != entry["after"]:
            raise ValueError(f"事务候选摘要不符：{entry['path']}")
        path = root / entry['path']
        current = _hash(_raw(path))
        if entry['path'] in new_snapshots and (entry['before'] is not None or (current == entry['after'] and path.stat().st_mode & 0o222)):
            raise ValueError(f'快照必须是本事务新建的只读文件：{entry["path"]}')
        if current not in (entry["before"], entry["after"]):
            raise ValueError(f"草稿文件已被其他操作修改，拒绝覆盖：{entry['path']}")
        pending.append((entry, data))
    # 事件是事务最后一项；保留原始前缀，只在所有产物写好后追加本次事件。
    for entry, data in pending:
        _check_guards(journal["guards"])
        current = _hash(_raw(root / entry["path"]))
        if current not in (entry["before"], entry["after"]):
            raise ValueError(f"写入前文件已变化：{entry['path']}")
        if current != entry["after"]:
            if entry['path'] in new_snapshots:
                _atomic_write(root / entry['path'], data, new_readonly=True)
            else:
                _atomic_write(root / entry['path'], data)
    _check_guards(journal["guards"])
    for entry, _ in pending:
        if _hash(_raw(root / entry["path"])) != entry["after"]:
            raise ValueError(f"保存期间检测到并发修改：{entry['path']}")
    (root / JOURNAL).unlink()


def recover_draft(requirement_dir: Path) -> dict:
    """完成本需求尚未完成的草稿事务，返回实际结果，不创建新生成事件。

    requirement_dir 必须为已有需求目录。仅在分析原始字节和所有目标仍匹配本事务读前/写后状态时恢复；
    发现冲突或 I/O 错误返回 fail，保留候选和 journal，不覆盖其他人的新内容。安装损坏原样抛出。
    """
    root = Path(os.path.abspath(requirement_dir))
    try:
        _safe(Path(requirement_dir))
        with _lock(root):
            journal = _read_json(root / JOURNAL)
            if not isinstance(journal, dict):
                raise ValueError("恢复记录不是对象")
            _finish(root, journal)
            written = list(TARGETS) if journal['result'].get('generated') else [entry['path'] for entry in journal['entries'] if entry['before'] != entry['after']]
            return {**journal['result'], 'recovered': True, 'written': written}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"status": "fail", "diagnostics": [_diagnostic(error, JOURNAL)], "written": [], "recovery_required": _has_journal(root)}


def _new_candidate(root, supplied, protected=()):
    """建立正式需求和只读输入目录外的新候选目录，返回路径；冲突或越界抛出异常。"""
    if supplied is None:
        return Path(tempfile.mkdtemp(prefix='prd-candidate-'))
    _safe(Path(supplied))
    path = Path(os.path.abspath(supplied))
    parents = [root, *(Path(os.path.abspath(item)).parent for item in protected)]
    # 系统临时目录别名和大小写不敏感文件系统可能让不同拼写落到同一目录。
    fs = _module('validate_prd')._fs()
    resolved = path.resolve()
    ancestor_keys = {fs.path_key(part) for part in (resolved, *resolved.parents)}
    if any(fs.path_key(parent.resolve()) in ancestor_keys for parent in parents):
        raise ValueError('候选目录必须在正式需求和关联分析目录之外')
    path.mkdir(parents=True, exist_ok=False)
    return path


def _stage_payload(root, candidate, payload, related, previous, diagnostics, *, snapshots=None, check=None):
    """复制候选及既有快照证据，再执行指定校验；不触碰正式产物。"""
    for name, raw in {**(snapshots or {}), **payload}.items():
        path = candidate / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    for name in ('analysis-result.json', 'source-manifest.json'):
        try:
            raw = _raw(root / 'analysis' / name)
        except OSError:
            if name != 'source-manifest.json':
                raise
            raw = None  # 辅助清单不可读的降级由门禁展示，不补造可读来源。
        if raw is not None:
            path = candidate / 'analysis' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    checked = (check(candidate) if check else _module('validate_prd').validate_prd(
        candidate, related_analyses=related, previous_trace=root / 'prd/prd-trace.json' if previous else None))
    diagnostics.extend(checked['diagnostics'])
    return checked['status'] != 'fail'


def _commit_payload(root, before, payload, guards, result):
    """核对全部读时文件后用既有事务保存，返回真实写入位置；冲突或中断保留现场。"""
    _check_guards(guards)
    new_snapshots = _release_targets(result['version']) if result.get('action') == 'release' else ()
    targets = new_snapshots + TARGETS
    for name in targets:
        if (name in new_snapshots and before[name] is not None) or _raw(root / name) != before[name]:
            raise ValueError(f'写前文件已变化或快照已存在，重新读取后再处理：{name}')
    journal = {'format': 'prd-release-transaction-1' if new_snapshots else 'prd-draft-transaction-1', 'guards': guards, 'result': result,
               'entries': [{'path': name, 'before': _hash(before[name]), 'after': _hash(payload[name]),
                            'data': base64.b64encode(payload[name]).decode('ascii')} for name in targets]}
    _atomic_write(root / JOURNAL, _encode(journal))
    _finish(root, journal)
    # 既有生成/同步响应沿用完整目标清单；编辑和生命周期报告实际变化文件。
    written = list(TARGETS) if result.get('generated') else [name for name in targets if before[name] != payload[name]]
    return {**result, 'written': written}


def _preserve_manual_marks(before, after, requirement_id):
    """拒绝以排版、重复生成或未经核实的同步清除既有不一致；不替代分析内容核实。"""
    validator = _module('validate_prd')
    original = validator.manual_inconsistencies(before, requirement_id)
    current = validator.manual_inconsistencies(after, requirement_id)
    missing = original.keys() - current.keys()
    if missing:
        raise ValueError('不得无依据清除与分析不一致标注及遗留项：' + '、'.join(sorted(missing)))


def _version_key(version):
    """将已核验版本号转为数值二元组，避免误把 2.10 排在 2.2 前。"""
    return tuple(map(int, version.removesuffix('-draft').split('.')))


def _workspace_version(prd, snapshots):
    """核对版本和生命周期是否与快照谱系一致；返回最近定稿号或 None。"""
    version, status = prd['version'], prd['status']
    if not isinstance(version, str) or not _module('validate_prd').VERSION.fullmatch(version):
        raise ValueError('不支持旧版本格式，不自动迁移或覆盖')
    published = [name.removeprefix('prd/versions/prd-').removesuffix('.md') for name in snapshots if name.endswith('.md')]
    for finalized in published:
        if not all(name in snapshots for name in _release_targets(finalized)):
            raise ValueError(f'已发布版本 {finalized} 缺少快照文件')
    latest = max(published, key=_version_key, default=None)
    if version.startswith('0.'):
        valid = latest is None and status != 'released'
    elif version.endswith('-draft'):
        valid = latest is not None and status != 'released' and _version_key(version) > _version_key(latest)
    else:
        valid = status in {'released', 'deprecated'} and version == latest
    if not valid:
        raise ValueError('工作稿版本、状态与最新发布快照不一致，请先校验基线')
    return latest


def _next_version(requirement, *, operation='generate', snapshots=None, content_changed=False):
    """选工作稿号；仅显式同步或编辑可从定稿另建工作稿。"""
    prd = requirement.get('prd')
    if prd is None:
        if operation != 'generate':
            raise ValueError('尚无工作稿，请先生成首稿')
        if snapshots:
            raise ValueError('存在发布快照，首稿入口不覆盖已发布需求')
        return '0.1'
    latest = _workspace_version(prd, snapshots or {})
    if operation == 'generate':
        if latest is not None or prd['status'] != 'draft':
            raise ValueError('首稿入口不覆盖已有发布需求或非草稿状态，请使用适用操作')
    elif prd['status'] not in {'draft', 'in_review', 'released'}:
        raise ValueError('当前状态不能同步或编辑；废弃需求仅可查看')
    major, minor = _version_key(prd['version'])
    if latest is None:
        return f'0.{minor + 1}'
    if content_changed:
        return f'{major + 1}.0-draft'
    return f'{major}.{minor + 1}-draft'


def _gap_document(root, supplied, requirement_id, version, existing, sync=False):
    """保留缺口历史和扩展；显式同步仅允许以既有resolution协议关闭，不能伪造接收进度。"""
    gaps = deepcopy(supplied if supplied is not None else existing)
    if gaps is None:
        gaps = {"schema_version": "1.0", "requirement_id": requirement_id, "counters": {"GAPREQ": 0}, "requests": []}
    if not isinstance(gaps, dict):
        raise ValueError("缺口候选必须为版本化对象")
    errors = list(_module("validate_prd")._schema("gap-request").iter_errors(gaps))
    if errors:
        raise ValueError(f"缺口格式错误：{errors[0].message}")
    if gaps["requirement_id"] != requirement_id:
        raise ValueError("缺口需求编号不匹配")
    old = {item["id"]: item for item in (existing or {}).get("requests", [])}
    current = {item["id"]: item for item in gaps["requests"]}
    if len(current) != len(gaps["requests"]):
        raise ValueError("缺口编号重复")
    for key, item in old.items():
        proposed = current.get(key)
        if proposed == item:
            continue
        if not sync or proposed is None or item["status"] == "closed" or proposed["status"] != "closed":
            raise ValueError(f"不得删除、重置缺口或代替分析侧标记接收：{key}")
        # 接收问题及依据由完整候选校验核实；这里先确保关闭没有悄悄改写原问题或扩展。
        if {k: v for k, v in proposed.items() if k not in ("status", "resolution")} != {k: v for k, v in item.items() if k not in ("status", "resolution")}:
            raise ValueError(f"关闭不得改写缺口内容：{key}")
    if existing:
        if gaps["counters"]["GAPREQ"] < existing["counters"]["GAPREQ"]:
            raise ValueError("缺口计数器不得回退")
        for key, value in existing.items():
            if key not in ("requests", "counters") and gaps.get(key) != value:
                raise ValueError(f"不得覆盖缺口封装扩展：{key}")
        for key, value in existing["counters"].items():
            if key != "GAPREQ" and gaps["counters"].get(key) != value:
                raise ValueError(f"不得覆盖缺口计数器扩展：{key}")
    for item in gaps["requests"]:
        if item["id"] not in old:
            if int(item["id"].split("-")[1]) <= (existing or {}).get("counters", {}).get("GAPREQ", 0):
                raise ValueError(f"新缺口编号不得复用已有高水位：{item['id']}")
            if item["status"] != "open" or "resolution" in item:
                raise ValueError(f"新缺口只能为 open：{item['id']}")
            item["raised_in"] = version
    return gaps


def _sync_patch(patch, previous):
    """给既有映射补齐重算请求；模型只需提交新增映射，不会因漏列旧项保留过期摘要。"""
    numbering = _module("assign_ids")
    numbering._check_schema(patch, "numbering-patch")
    effective = deepcopy(patch)
    represented = set()
    by_id = {item["prd_id"]: item for item in previous["items"]}
    by_key = {item["mapping_key"]: item for item in previous["items"] if "mapping_key" in item}
    for entry in effective["items"]:
        old = by_id.get(entry.get("prd_id")) or by_key.get(entry["mapping_key"])
        if old:
            if not set(old["analysis_refs"]).issubset(entry["analysis_refs"]):
                raise ValueError(f"既有编号不得替换为其他分析身份；保留旧引用并为新身份分配新号：{old['prd_id']}")
            # 完整引用按集合判断身份，保留旧序列，避免补丁仅重排引用就制造追溯改动。
            entry['analysis_refs'] = [*old['analysis_refs'], *(ref for ref in entry['analysis_refs'] if ref not in old['analysis_refs'])]
            represented.add(old["prd_id"])
    reserved = set(by_key) | {entry["mapping_key"] for entry in patch["items"]}
    preserved = []
    for item in previous["items"]:
        if item["prd_id"] in represented:
            continue
        key = item.get("mapping_key")
        if key is None:
            base = "legacy:" + item["prd_id"]
            key, suffix = base, 1
            while key in reserved:
                key = f"{base}:{suffix}"
                suffix += 1
            reserved.add(key)
        preserved.append({"mapping_key": key, "prd_id": item["prd_id"], "kind": item["kind"], "analysis_refs": item["analysis_refs"]})
    effective["items"] = preserved + effective["items"]
    return effective


def _parsed(text):
    """复用唯一块解析器；旧稿或候选标记损坏时停止，不尝试通过重写掩盖损坏。"""
    diagnostics = []
    blocks = _module("validate_prd")._blocks(text, diagnostics)
    if diagnostics:
        raise ValueError("正文定位结构不合法：" + "; ".join(item["message"] for item in diagnostics))
    return blocks


def _raw_span(text, block):
    """把解析器内文范围扩为完整定位块范围，避免以重复的自然语言文本猜位置。"""
    markers = list(_module('validate_prd').MARKER.finditer(text))
    begin = next(match.start() for match in markers if match.end() == block['start'])
    end = next(match.end() for match in markers if match.start() == block['end'])
    return begin, end


def _raw_item(text, block):
    """取得含开闭标记的块原文；偏移是Unicode索引，切片后才编码以保留UTF-8字节。"""
    begin, end = _raw_span(text, block)
    return text[begin:end].encode('utf-8')


def _check_minimal_sync(old_text, text, comparison, previous, trace):
    """拒绝改写未变正式条目的字节、章节或身份，并防止漏掉新增分析条目。"""
    old_blocks, new_blocks = _parsed(old_text), _parsed(text)
    old_items = {item["prd_id"]: item for item in previous["items"]}
    new_items = {item["prd_id"]: item for item in trace["items"]}
    for change in comparison["items"]:
        if change["category"] != "unchanged":
            continue
        pid = change["prd_id"]
        old, new = deepcopy(old_items[pid]), deepcopy(new_items[pid])
        if "mapping_key" not in old:
            new.pop("mapping_key", None)  # 旧格式可补入稳定键，不能借此改变既有身份或来源。
        if old != new:
            raise ValueError(f"未变条目的追溯不能改写：{pid}")
        if old["status"] != "abolished":
            before, after = old_blocks["item"].get(pid), new_blocks["item"].get(pid)
            if not before or not after or before["section"] != after["section"] or _raw_item(old_text, before) != _raw_item(text, after):
                raise ValueError(f"未变条目必须保留原始字节与章节：{pid}")
    mapped = {ref for item in trace["items"] for ref in item["analysis_refs"]}
    omitted = [item["analysis_ref"] for item in comparison["added"] if item["analysis_ref"] not in mapped]
    if omitted:
        raise ValueError(f"新增分析条目缺少映射：{omitted}")
    return old_blocks, new_blocks


def _optional_manifest(path):
    """读取可用来源名称清单，辅助缺失或坏JSON降级为空，不放宽符号链接边界。"""
    _safe(path)
    try:
        return _read_json(path) if path.exists() else []
    except (OSError, ValueError, UnicodeError):
        return []


def _section_baseline(old_text, requirement, previous, existing_gaps, related, previous_analysis):
    """读取已存章节依据或匹配旧分析；缺证据返回None，不用当前分析伪造旧快照。"""
    if previous_analysis is not None:
        old = _read_json(Path(previous_analysis))
        schema, _ = _module('validate_prd')._analyst()._validators()
        errors = _module('validate_prd')._analyst()._format_errors(old, schema)
        if errors or old['requirement_id'] != requirement['common']['requirement_id'] or old['meta']['analysis_revision'] != requirement['prd']['based_on_analysis_revision']:
            raise ValueError('显式旧分析必须格式合法、需求身份及修订匹配原PRD基准')
    stored = previous['meta'].get('section_source_digests')
    if stored is not None:
        return stored
    if previous_analysis is None:
        return None
    # 旧分析有术语、旧稿没有独立术语块时，术语原来归附录，不能将新版摘要当作旧稿依据。
    legacy_layout = bool(old.get('context', {}).get('domain_terms')) and 'glossary' not in _parsed(old_text)['section']
    digests = _module('validate_prd').section_source_digests(old, existing_gaps, trace=previous,
            source_manifest=_optional_manifest(Path(previous_analysis).with_name('source-manifest.json')),
            related_analyses=related, legacy_layout=legacy_layout)
    # 没有旧关联分析快照，不能把本次传入的关联资料当作旧依据；这些章节仍须明确降级。
    for item in previous['items']:
        if any(not ref.startswith(old['requirement_id'] + '/') for ref in item['analysis_refs']):
            digests.pop(_module('validate_prd').KIND_SECTIONS[item['kind']], None)
    return digests


def _check_section_sync(old_text, text, baseline, current, diagnostics, uncovered):
    """依据未变时保护含标记的整章原字节；没有旧依据时明确降级，章节外文本仍不得夹带修改。"""
    old_blocks, blocks = _parsed(old_text), _parsed(text)
    missing = set(current) - set(baseline or {})
    if missing:
        diagnostics.append({**_diagnostic('旧稿缺少章节依据证据，未自动证明这些章节的最小同步；需补旧分析或人工逐章核对：' + '、'.join(sorted(missing)), 'prd-trace.json/meta/section_source_digests'), 'level': 'warning'})
        uncovered.append('旧稿章节依据不足（须人工逐章核对）')
    for key, digest in (baseline or {}).items():
        if digest != current[key]:
            continue
        before, after = old_blocks['section'].get(key), blocks['section'].get(key)
        if (before is None) != (after is None) or (before and _raw_item(old_text, before) != _raw_item(text, after)):
            raise ValueError(f'依据未变的章节必须保留原始字节：{key}')
    def frame(value, parsed):
        """移除已定位章节与固定提示，仅比较章节外原文，返回框架文本；定位错误原样抛出。"""
        pieces, cursor = [], 0
        for block in sorted(parsed['section'].values(), key=lambda span: span['start']):
            begin, end = _raw_span(value, block)
            pieces.append(value[cursor:begin])
            cursor = end
        pieces.append(value[cursor:])
        for prompt in _module('validate_prd').PROMPTS.values():
            if pieces[0].startswith(prompt):
                pieces[0] = pieces[0][len(prompt):]
                break
        # 新增或省略可选章会增减章间空行，不能把这些分隔符误判为未追溯正文。
        return ''.join(piece for piece in pieces if piece.strip()).strip('\r\n')
    if frame(old_text, old_blocks) != frame(text, blocks):
        raise ValueError('同步不得改写章节外的未追溯文本')


def _sync_summary(root, comparison, previous, trace, old_blocks, new_blocks, existing_gaps, gaps, diagnostics, uncovered):
    """按真实条目差异汇总事件；辅助原因缺失时明确降级，不把状态变化当内容补足。"""
    old_ids = {item["prd_id"] for item in previous["items"]}
    groups = {"新增": [item["prd_id"] for item in trace["items"] if item["prd_id"] not in old_ids],
              "修改": [], "废止": [], "待确认": []}
    labels = {"modified": "修改", "withdrawn": "废止", "to_reassess": "待确认"}
    for item in comparison["items"]:
        if item["category"] in labels:
            groups[labels[item["category"]]].append(item["prd_id"])
    parts = [label + "：" + ("、".join(ids) or "无") for label, ids in groups.items()]
    parts.append(f"就绪度：{previous['meta']['generated_under_readiness']} → {trace['meta']['generated_under_readiness']}")
    changed = old_blocks["section"]["residuals"]["text"] != new_blocks["section"]["residuals"]["text"]
    parts.append("遗留事项：" + ("已按当前分析更新" if changed else "未变"))
    closed_before = {item["id"] for item in existing_gaps["requests"] if item["status"] == "closed"}
    closed = [item["id"] for item in gaps["requests"] if item["status"] == "closed" and item["id"] not in closed_before]
    if closed:
        parts.append("核实关闭缺口：" + "、".join(closed))
    retained = [item["id"] for item in gaps["requests"] if item["status"] != "closed"]
    if retained:
        parts.append("保留缺口及占位（尚未提交经内容核实的关闭依据）：" + "、".join(retained))
    try:
        raw = _raw(root / "analysis/analysis-events.jsonl")
        if raw is None:
            raise ValueError("未提供分析事件")
        events = [json.loads(line, object_pairs_hook=_module("validate_prd")._unique,
                             parse_constant=_module("validate_prd")._constant) for line in raw.decode("utf-8").splitlines() if line.strip()]
        if any(not isinstance(event, dict) or type(event.get("revision")) is not int or not isinstance(event.get("summary"), str) for event in events):
            raise ValueError("分析事件缺少revision或summary")
        reasons = [event["summary"] for event in events if event.get("requirement_id") == trace["requirement_id"]
                   and comparison["based_on_analysis_revision"] < event["revision"] <= comparison["analysis_revision"]]
        if reasons:
            parts.append("分析事件说明：" + "；".join(reasons))
    except (OSError, ValueError, UnicodeError) as error:
        diagnostics.append({**_diagnostic(f"分析事件不可用，仅按条目生成变更摘要：{error}", "analysis/analysis-events.jsonl"), "level": "warning"})
        uncovered.append("analysis-events.jsonl（变更原因说明降级）")
    return "；".join(parts), [pid for ids in groups.values() for pid in ids]


def write_draft(requirement_dir: Path, *, patch: dict, body: str, gaps: dict | None = None,
                related_analyses: Sequence[Path] = (), allow_stale: bool = False,
                generated_at: str | None = None, candidate_dir: Path | None = None, sync: bool = False,
                previous_analysis: Path | None = None) -> dict:
    """校验并保存首稿、重复草稿或显式增量同步，返回诊断、编号、版本和实际保存位置。

    patch 仅含获认可协议的编号映射；body 为按编号候选编写的 Markdown，gaps 为可选完整缺口候选。
    sync 仅在按当前分析定向更新已有工作稿或从定稿另建工作稿时为真，关闭缺口须提交 resolution 依据。
    previous_analysis可显式提供匹配旧基准修订的分析，为缺章节摘要的旧稿建立比较证据，不修改该文件。
    related_analyses 只使用调用方显式给出的资料；allow_stale 仅可对应用户实际坚持。
    generated_at 可固定测试时间，默认取实际UTC；candidate_dir 须为需求目录外不存在的新目录。
    校验或并发失败返回 fail 并保留已构造候选；写中失败保留私有 journal，需显式恢复，不报告成功。
    不写 analysis/、其他需求、快照或 common，不执行编辑/评审/发布；安装故障原样抛出。
    """
    root = Path(os.path.abspath(requirement_dir))
    validator, renderer = _module("validate_prd"), _module("render_info")
    candidate = None
    diagnostics = []
    before, payload = {}, {}
    try:
        _safe(Path(requirement_dir))
        with _lock(root):
            if _has_journal(root):
                raise ValueError("存在未完成草稿事务，请先使用 --recover；不覆盖部分写入")
            before = {name: _raw(root / name) for name in TARGETS}
            if previous_analysis is not None and not sync:
                raise ValueError('显式旧分析只用于 --sync，不改变首稿输入')
            guards = _guards(root, related_analyses, sync=sync, previous_analysis=previous_analysis)
            snapshots = _snapshot_inputs(root, guards)
            gate = _module("check_gate").check_gate(root, allow_stale=allow_stale, related_analyses=related_analyses)
            diagnostics.extend(gate.get("diagnostics", []))
            if not gate["allowed"]:
                return {**gate, "written": [], "generated": False}
            requirement = _read_json(root / "requirement.json")
            analysis = _read_json(root / "analysis/analysis-result.json")
            candidate = _new_candidate(root, candidate_dir, (*related_analyses, *((previous_analysis,) if previous_analysis is not None else ())))
            # 先保留模型原始材料；即使编号或渲染阶段失败，也能按真实候选修正而不是丢失现场。
            inputs = candidate / "inputs"
            inputs.mkdir()
            (inputs / "body.md").write_bytes(body.encode("utf-8"))
            (inputs / "numbering-patch.json").write_bytes(_encode(patch))
            if gaps is not None:
                (inputs / "gap-requests.json").write_bytes(_encode(gaps))
            # 先用内容版分配新编号；若证明只是修订前移，就不会存在用该版引入的条目或缺口。
            version = _next_version(requirement, operation='sync' if sync else 'generate', snapshots=snapshots, content_changed=sync)
            previous = _read_json(root / "prd/prd-trace.json") if before["prd/prd-trace.json"] is not None else None
            if "prd" in requirement:
                if not sync and requirement["prd"]["based_on_analysis_revision"] != analysis["meta"]["analysis_revision"]:
                    raise ValueError("分析已变化，需使用 --sync 定向同步；首稿入口不整篇覆盖")
                if previous is None or any(before[name] is None for name in TARGETS):
                    raise ValueError("已有工作稿文件不完整，请先恢复，不覆盖已有成果")
                content_check = renderer.compare_content(before['prd/prd.md'], previous)
                if content_check['changed']:
                    raise ValueError("工作稿含尚未处理的手工修改，首稿入口不覆盖")
                if not sync:
                    existing_check = validator.validate_prd(root, related_analyses=related_analyses)
                    if existing_check["status"] == "fail":
                        return {**existing_check, "candidate_dir": str(candidate), "written": [], "generated": False}
            elif any(before[name] is not None for name in TARGETS if name not in ("requirement.json", "prd/prd-trace.json")):
                raise ValueError("无 prd 元数据但存在草稿文件，请先核对旧格式或未完成保存")
            related = [_read_json(Path(path)) for path in related_analyses]
            comparison = None
            if sync:
                comparison = _module("check_sync").compare_sources(analysis, requirement, previous, related_analyses=related)
                if not comparison["pending"]:
                    raise ValueError("分析修订未高于工作稿基准，无需同步；不借同步入口编辑正文")
            effective_patch = _sync_patch(patch, previous) if sync else patch
            trace = _module("assign_ids").allocate_ids(effective_patch, analysis, requirement, previous_trace=previous,
                        related_analyses=related, version=version, draft_kind=gate["draft_kind"])
            if sync:
                allocated = {item['prd_id']: item for item in trace['items']}
                for change in comparison['items']:
                    proposed = allocated[change['prd_id']]
                    if set(proposed['analysis_refs']) != set(change['analysis_refs']):
                        # 新来源并入旧映射也是依据变化；不能仅比较旧引用后误判为未变或漏记事件。
                        category = {'abolished': 'withdrawn', 'to_confirm': 'to_reassess', 'active': 'modified'}[proposed['status']]
                        change.update(category=category, analysis_refs=proposed['analysis_refs'], source_digest=proposed['source_digest'])
            existing_gaps = _read_json(root / "prd/gap-requests.json") if before["prd/gap-requests.json"] is not None else None
            gap_document = _gap_document(root, gaps, analysis["requirement_id"], version, existing_gaps, sync=sync)
            # 重复生成要求正文不变，不能给仍在附录中的旧术语保存新版章节依据。
            legacy_layout = previous is not None and not sync and (
                'glossary' not in previous['meta'].get('section_source_digests', {})
                and 'glossary' not in _parsed(before['prd/prd.md'].decode('utf-8'))['section']
            )
            trace['meta']['section_source_digests'] = validator.section_source_digests(analysis, gap_document, trace=trace,
                    source_manifest=_optional_manifest(root / 'analysis/source-manifest.json'), related_analyses=related,
                    legacy_layout=legacy_layout)
            uncovered = list(gate.get("uncovered_analysis", ()))
            if sync and any("source-manifest" in str(issue["path"]) and issue["level"] == "warning" for issue in diagnostics):
                uncovered.append("source-manifest.json（来源名称降级为source_id）")
            summary, affected = None, None
            if sync:
                old_text = before['prd/prd.md'].decode('utf-8')
                baseline_sections = _section_baseline(old_text, requirement, previous, existing_gaps, related, previous_analysis)
                _check_section_sync(old_text, body, baseline_sections, trace['meta']['section_source_digests'], diagnostics, uncovered)
                old_blocks, new_blocks = _check_minimal_sync(old_text, body, comparison, previous, trace)
                summary, affected = _sync_summary(root, comparison, previous, trace, old_blocks, new_blocks,
                                                 existing_gaps, gap_document, diagnostics, uncovered)
                if snapshots and baseline_sections == trace['meta']['section_source_digests'] and previous['items'] == trace['items'] and existing_gaps == gap_document and all(previous['meta'][key] == trace['meta'][key] for key in ('draft_kind', 'generated_under_readiness')):
                    # 最小同步已核对全部业务章节和章节外原文；只前移基准是次版本维护。
                    version = _next_version(requirement, operation='sync', snapshots=snapshots)
                if not any(item['status'] != 'abolished' for item in trace['items']) and any(item['status'] == 'abolished' for item in trace['items']):
                    diagnostics.append({**_diagnostic('全部已映射条目均已撤销；请由产品经理决定是否废弃，未自动废弃'), 'level': 'warning'})
            next_requirement = deepcopy(requirement)
            next_requirement["prd"] = {**requirement.get("prd", {}), "based_on_analysis_revision": analysis["meta"]["analysis_revision"], "status": "draft", "version": version}
            timestamp = generated_at or datetime.now(timezone.utc).isoformat()
            events_raw = before["prd/prd-events.jsonl"] or b""
            if events_raw and not events_raw.endswith(b"\n"):
                events_raw += b"\n"
            event = {"time": timestamp, "prd_version": version, "change_type": "sync" if sync else "initial_generation",
                     "summary": summary if sync else "首次生成工作稿" if "prd" not in requirement else "基于同一分析输入重复生成工作稿",
                     "affected_prd_ids": affected if sync else [item["prd_id"] for item in trace["items"]],
                     "based_on_analysis_revision": analysis["meta"]["analysis_revision"], "actor": "prd_generator"}
            new_events = [event]
            if any(item["id"] not in {old["id"] for old in (existing_gaps or {}).get("requests", [])} for item in gap_document["requests"]):
                new_events.append({**event, "change_type": "gap_request", "summary": "登记生成中发现的分析缺口，保留占位并建议交回需求分析"})
            events_raw += b"".join(_encode(item).replace(b"\n", b" ").rstrip() + b"\n" for item in new_events)
            events = [json.loads(line) for line in events_raw.decode("utf-8").splitlines() if line.strip()]
            changes = renderer.render_changes(events)
            text = renderer.render_info(body, next_requirement, trace, generated_at=timestamp,
                        uncovered_analysis=uncovered, changes=changes)
            trace["meta"]["content_hash"] = renderer.content_hash(text.encode("utf-8"))
            trace['meta']['content_baseline'] = text
            if previous:
                _preserve_manual_marks(before['prd/prd.md'].decode('utf-8'), text, trace['requirement_id'])
            payload = {"prd/prd.md": text.encode("utf-8"), "prd/prd-trace.json": _encode(trace),
                       "prd/gap-requests.json": _encode(gap_document), "requirement.json": _encode(next_requirement), "prd/prd-events.jsonl": events_raw}
            if not _stage_payload(root, candidate, payload, related_analyses, previous, diagnostics, snapshots=snapshots):
                return {"status": "fail", "diagnostics": diagnostics, "candidate_dir": str(candidate), "written": [], "generated": False}
            if "prd" in requirement and not sync:
                # 只排除脚本负责更新的两个块；章节外文本同样可能承载需求，不能漏比较。
                old_stable = renderer._take_section(renderer._take_section(before["prd/prd.md"].decode("utf-8"), "info"), "changes").strip("\r\n")
                new_stable = renderer._take_section(renderer._take_section(text, "info"), "changes").strip("\r\n")
                if old_stable != new_stable:
                    raise ValueError("同一分析输入重复生成不得改写需求正文；保留候选，需求修改须交回分析")
            result = {"status": "warning" if diagnostics else "pass", "diagnostics": diagnostics, "version": version,
                      "draft_kind": gate["draft_kind"], "candidate_dir": str(candidate), "generated": True, "synced": sync,
                      **({"comparison": comparison, "change_summary": summary} if sync else {}),
                      "mapping": [{"mapping_key": item.get("mapping_key"), "prd_id": item["prd_id"], "analysis_refs": item["analysis_refs"]} for item in trace["items"]]}
            return _commit_payload(root, before, payload, guards, result)
    except (OSError, ValueError, KeyError, TypeError) as error:
        written = []
        if _has_journal(root):
            for name, raw in payload.items():
                try:
                    if raw != before.get(name) and _raw(root / name) == raw:
                        written.append(name)
                except (OSError, ValueError):
                    pass
        return {"status": "fail", "diagnostics": diagnostics + [_diagnostic(error)], "candidate_dir": str(candidate) if candidate else None,
                "written": written, "generated": False, "transaction_complete": False, "recovery_required": _has_journal(root)}


def _without_empty_residual_notice(text):
    """移除遗留章中独立的空集合提示；新增实际遗留项后该提示已不再为真，不是需求规则。"""
    residual = _parsed(text)['section']['residuals']
    # 只处理完整独立行，不触碰业务句子或“无遗留项”作为引用说明的片段。
    value = re.sub(r'(?m)^[ \t]*(?:[-*][ \t]+)?(?:暂无|无)(?:适用)?遗留(?:事)?项[。.]?[ \t]*(?:\r?\n|$)', '', residual['text'])
    return text[:residual['start']] + value + text[residual['end']:]


def _stable_body(text):
    """排除脚本渲染块，保留需求正文和章节外文本以检查编辑范围。"""
    renderer = _module('render_info')
    return renderer._take_section(renderer._take_section(text, 'info'), 'changes').strip('\r\n')


def _section_without_items(text, key, blocks):
    """以条目身份替代其原文，隔离同章的非编号内容变化，避免父章重复计为手改目标。"""
    section = blocks['section'].get(key)
    if section is None:
        return None
    value = text[section['start']:section['end']]
    spans = [(pid, block) for pid, block in blocks['item'].items() if block['section'] == key]
    for pid, block in sorted(spans, key=lambda pair: pair[1]['start'], reverse=True):
        start, end = _raw_span(text, block)
        value = value[:start-section['start']] + '<item:' + pid + '>' + value[end-section['start']:]
    return value


def _required_manual_refs(baseline, current, rid):
    """返回旧稿到手改正文的所有条目及非编号内容目标；无法定位的变化抛出 ValueError。"""
    old, new = _parsed(baseline), _parsed(current)
    if old['item'].keys() != new['item'].keys() or old['section'].keys() != new['section'].keys():
        raise ValueError('手改破坏条目或稳定章节身份，须回交分析，不能以保留标注掩盖')
    refs = {rid + '/' + pid for pid in old['item'] if old['item'][pid]['text'] != new['item'][pid]['text']}
    validator = _module('validate_prd')
    for key in validator.CONTENT_SECTIONS:
        if _section_without_items(baseline, key, old) != _section_without_items(current, key, new):
            refs.add(rid + '/prd/sections/' + key)
    def frame(text, blocks):
        """排除全部已定位章节及固定提示，返回不能归属目标的正文框架。"""
        for block in sorted(blocks['section'].values(), key=lambda value: value['start'], reverse=True):
            start, end = _raw_span(text, block)
            text = text[:start] + text[end:]
        for prompt in validator.PROMPTS.values():
            if text.startswith(prompt):
                text = text[len(prompt):]
                break
        return text.strip('\r\n')
    if frame(baseline, old) != frame(current, new):
        raise ValueError('章节外内容性改动无法稳定定位，须回交分析，不直接保留为有效需求')
    return refs


def _check_edit_identity(current, candidate, *, keep=False, rid=None):
    """保护正式身份、章节和引用；坚持保留仅允许增加对应标注及遗留项，不夹带新内容。"""
    old, new = _parsed(current), _parsed(candidate)
    for kind in ('item', 'gap', 'section'):
        if old[kind].keys() != new[kind].keys():
            raise ValueError(f'编辑不得增删 {kind} 定位身份；需求变化须回交分析')
    for pid, block in old['item'].items():
        if new['item'][pid]['section'] != block['section']:
            raise ValueError(f'编辑不能改变条目的内容归属：{pid}')
    validator = _module('validate_prd')
    manual_old = validator.manual_inconsistencies(current, rid)
    manual_new = validator.manual_inconsistencies(candidate, rid)
    if not keep:
        if old['residual'].keys() != new['residual'].keys() or manual_old.keys() != manual_new.keys():
            raise ValueError('排版编辑不能增删遗留项或不一致状态')
        pattern = r'[A-Za-z0-9_-]+/(?:GOAL|SCN|FR|BR|CON|NFR|AC|FLOW|STATE|BND|EXC|Q|ASM|DEC|CNF|GAP)-[0-9]+'
        if Counter(re.findall(pattern, _stable_body(current))) != Counter(re.findall(pattern, _stable_body(candidate))):
            raise ValueError('排版编辑不得改变完整分析引用')
        for pid in old['gap']:
            if old['gap'][pid]['text'] != new['gap'][pid]['text']:
                raise ValueError('排版编辑不能改写缺口占位内容')
        return
    def normalized(text, blocks):
        """移除手工不一致说明和标签，比较剩余全文；不允许借坚持保留改写其他业务事实。"""
        for ref, block in sorted(blocks['residual'].items(), key=lambda pair: pair[1]['start'], reverse=True):
            if ref.startswith(rid + '/PRD-') or ref.startswith(rid + '/prd/sections/'):
                start, end = _raw_span(text, block)
                text = text[:start] + text[end:]
        return ' '.join(_stable_body(_without_empty_residual_notice(text)).replace(validator.INCONSISTENCY, '').split())
    if normalized(current, old) != normalized(candidate, new):
        raise ValueError('坚持保留候选只能增加不一致标注及遗留说明，不能再改写手工内容或其他正文')
    if not old['residual'].keys() <= new['residual'].keys():
        raise ValueError('坚持保留不得移除既有遗留事项')


def inspect_edits(requirement_dir: Path, *, previous_body: Path | None = None,
                  related_analyses: Sequence[Path] = (), allow_stale: bool = False) -> dict:
    """只读检查工作稿并返回实际摘要、旧稿可用性、完整差异和读时版本，不记录事件。

    requirement_dir 为已有需求；previous_body 可提供 hash 匹配的旧正文，related_analyses 仅显式资料。
    allow_stale 仅对应真实用户坚持。用户文件或协议异常转为 fail 诊断，不创建候选或业务文件。
    """
    root = Path(os.path.abspath(requirement_dir))
    try:
        _safe(Path(requirement_dir))
        with _lock(root):
            if _has_journal(root):
                raise ValueError('存在未完成事务，请先 --recover，再检查实际正文')
            before = {name: _raw(root / name) for name in TARGETS}
            guards = _guards(root, related_analyses)
            if previous_body is not None:
                guards.append({'path': str(Path(previous_body).absolute()), 'sha256': _guard_hash(Path(previous_body))})
            comparison = _module('check_sync').check_sync(root, related_analyses=related_analyses, allow_stale=allow_stale)
            requirement = _read_json(root / 'requirement.json')
            trace = _read_json(root / 'prd/prd-trace.json')
            change = _module('render_info').compare_content(before['prd/prd.md'], trace,
                         previous_content=_raw(Path(previous_body)) if previous_body else None)
            _check_guards(guards)
            if any(_raw(root / name) != before[name] for name in TARGETS):
                raise ValueError('检查期间工作稿已变化，请重新读取')
            if previous_body is not None and change['baseline_available']:
                for issue in comparison['diagnostics']:
                    if '旧稿缺少可核验正文基准' in issue['message']:
                        issue['message'] = '正文摘要变化；已用显式旧正文核验比较基准，仍须按实际差异判断含义。'
            return {**comparison, **change, 'manual_edits': change, 'base_prd_version': requirement['prd']['version'],
                    'base_analysis_revision': comparison['analysis_revision'], 'written': []}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {'status': 'fail', 'diagnostics': [_diagnostic(error)], 'written': []}


def edit_draft(requirement_dir: Path, *, mode: str, base_prd_version: str, base_analysis_revision: int,
               base_content_hash: str, summary: str, body: str | None = None,
               meaning_reviewed: bool = False, keep_confirmed: bool = False, previous_body: Path | None = None,
               related_analyses: Sequence[Path] = (), allow_stale: bool = False,
               generated_at: str | None = None, candidate_dir: Path | None = None) -> dict:
    """处理当前稿的排版、显式手改检测或用户坚持保留，返回实际保存及诊断。

    mode 为 layout/detect/keep；base_* 绑定读时 PRD 版本、当前分析修订及当前正文实际摘要。
    summary 描述已核对的差异；body 是编辑候选，detect 时为空。meaning_reviewed 表示模型已逐差异
    判断排版不改含义，keep_confirmed 仅对应真实用户坚持；两者都不是脚本的语义证明。
    previous_body 为缺基准旧稿的显式证据；related_analyses 和 allow_stale 语义同生成门禁。
    generated_at 可固定测试时间；candidate_dir 必须为正式需求外的新目录。输入、校验及并发错误
    返回 fail 并保留候选，中断保留既有 journal 以显式恢复；不写分析或发布快照。
    """
    root = Path(os.path.abspath(requirement_dir))
    candidate, before, payload, diagnostics = None, {}, {}, []
    validator, renderer = _module('validate_prd'), _module('render_info')
    try:
        _safe(Path(requirement_dir))
        if mode not in {'layout', 'detect', 'keep'} or not isinstance(summary, str) or not summary.strip():
            raise ValueError('编辑模式无效或缺少实际差异说明')
        if (mode == 'detect' and (body is not None or meaning_reviewed or keep_confirmed)) or (mode != 'detect' and body is None):
            raise ValueError('detect 仅记录检测，不接收正文或确认；layout/keep 必须提供候选正文')
        if mode == 'layout' and (not meaning_reviewed or keep_confirmed):
            raise ValueError('排版须先逐差异核对含义，不能以用户坚持代替语义核对')
        if mode == 'keep' and (not keep_confirmed or meaning_reviewed):
            raise ValueError('坚持保留须有用户实际确认，不能冒充语义未变')
        with _lock(root):
            if _has_journal(root):
                raise ValueError('存在未完成草稿事务，请先 --recover')
            before = {name: _raw(root / name) for name in TARGETS}
            if any(raw is None for raw in before.values()):
                raise ValueError('已有工作稿文件不完整，不能编辑；先生成或恢复')
            guards = _guards(root, related_analyses)
            if previous_body:
                guards.append({'path': str(Path(previous_body).absolute()), 'sha256': _guard_hash(Path(previous_body))})
            requirement = _read_json(root / 'requirement.json')
            analysis = _read_json(root / 'analysis/analysis-result.json')
            trace = _read_json(root / 'prd/prd-trace.json')
            gate = _module('check_gate').check_gate(root, related_analyses=related_analyses, allow_stale=allow_stale)
            diagnostics.extend(gate['diagnostics'])
            if not gate['allowed']:
                return {**gate, 'written': [], 'edited': False}
            snapshots = _snapshot_inputs(root, guards)
            next_version = _next_version(requirement, operation='edit', snapshots=snapshots)
            if base_prd_version != requirement['prd']['version'] or type(base_analysis_revision) is not int or base_analysis_revision != analysis['meta']['analysis_revision']:
                raise ValueError('编辑读时 PRD 版本或分析修订已变化，须重新读取差异')
            current_raw = before['prd/prd.md']
            if base_content_hash != renderer.content_hash(current_raw):
                raise ValueError('编辑读时正文已变化，不能只改基准数字重试')
            pending = requirement['prd']['based_on_analysis_revision'] < analysis['meta']['analysis_revision']
            if pending and mode == 'layout':
                raise ValueError('PRD 待同步；排版不代替分析同步或前移分析基准')
            comparison = renderer.compare_content(current_raw, trace,
                        previous_content=_raw(Path(previous_body)) if previous_body else None)
            current = current_raw.decode('utf-8')
            current_blocks = _parsed(current)
            if mode in {'detect', 'keep'} and not comparison['changed']:
                raise ValueError('当前正文摘要未变，没有尚未处理的手工修改')
            if mode in {'layout', 'keep'} and not comparison['baseline_available']:
                raise ValueError('缺少可核验旧正文，不能认定排版无害或定位全部不一致；请补 --previous-body')
            candidate = _new_candidate(root, candidate_dir, related_analyses)
            inputs = candidate / 'inputs'
            inputs.mkdir()
            (inputs / 'observed.md').write_bytes(current_raw)
            review = {'mode': mode, 'base_prd_version': base_prd_version, 'base_analysis_revision': base_analysis_revision,
                      'base_content_hash': base_content_hash, 'summary': summary, 'meaning_reviewed': meaning_reviewed,
                      'keep_confirmed': keep_confirmed, 'comparison': comparison}
            (inputs / 'edit-review.json').write_bytes(_encode(review))
            if body is not None:
                (inputs / 'body.md').write_bytes(body.encode('utf-8'))
            old_text = trace['meta'].get('content_baseline')
            if previous_body:
                old_text = _raw(Path(previous_body)).decode('utf-8')
            if old_text is None and not comparison['changed']:
                old_text = current
            if old_text is not None:
                (inputs / 'baseline.md').write_bytes(old_text.encode('utf-8'))
            events = [json.loads(line, object_pairs_hook=validator._unique, parse_constant=validator._constant)
                      for line in before['prd/prd-events.jsonl'].decode('utf-8').splitlines() if line.strip()]
            timestamp = generated_at or datetime.now(timezone.utc).isoformat()
            rid = trace['requirement_id']
            actual_targets = comparison['affected_prd_ids']
            new_requirement, new_trace = deepcopy(requirement), deepcopy(trace)
            if mode != 'detect':
                _check_edit_identity(current, body, keep=mode == 'keep', rid=rid)
                candidate_blocks = _parsed(body)
                if old_text is not None:
                    _preserve_manual_marks(old_text, body, rid)
                if mode == 'keep':
                    required = _required_manual_refs(old_text, current, rid)
                    marked = validator.manual_inconsistencies(body, rid)
                    previous_marks = validator.manual_inconsistencies(old_text, rid)
                    if not required or not required <= marked.keys() or marked.keys() - previous_marks.keys() - required:
                        raise ValueError('坚持保留须逐一标注全部实际变化目标，不得漏标或标注无关目标')
                    body = _without_empty_residual_notice(body)
                new_requirement['prd'] = {**requirement['prd'], 'version': next_version, 'status': 'draft'}
            version = new_requirement['prd']['version']
            event = {'time': timestamp, 'prd_version': version, 'change_type': 'layout_edit' if mode == 'layout' else 'manual_edit_detected',
                     'summary': summary.strip(), 'affected_prd_ids': actual_targets if mode != 'layout' else sorted(
                         pid for pid in current_blocks['item'] if current_blocks['item'][pid]['text'] != candidate_blocks['item'][pid]['text']),
                     'based_on_analysis_revision': requirement['prd']['based_on_analysis_revision'], 'actor': 'prd_generator',
                     'handling': mode, 'observed_content_hash': comparison['content_hash'],
                     'expected_content_hash': comparison['expected_content_hash']}
            if mode == 'detect' and any(item.get('change_type') == 'manual_edit_detected' and item.get('handling') == 'detect'
                    and item.get('prd_version') == version and item.get('observed_content_hash') == comparison['content_hash']
                    and item.get('expected_content_hash') == comparison['expected_content_hash'] for item in events):
                _check_guards(guards)
                if any(_raw(root / name) != before[name] for name in TARGETS):
                    raise ValueError('检测记录重试期间文件已变化，须重新读取')
                return {'status': 'warning', 'diagnostics': [{**_diagnostic('同一手改已记录，仍须回交分析或等待用户决定'), 'level': 'warning'}],
                        'detected': True, 'already_recorded': True, 'edited': False, 'version': version,
                        'manual_edits': comparison, 'candidate_dir': str(candidate), 'written': []}
            events_raw = before['prd/prd-events.jsonl']
            if events_raw and not events_raw.endswith(b'\n'):
                events_raw += b'\n'
            events_raw += _encode(event).replace(b'\n', b' ').rstrip() + b'\n'
            payload = dict(before)
            payload['prd/prd-events.jsonl'] = events_raw
            if mode != 'detect':
                changes = renderer.render_changes([*events, event])
                text = renderer.render_info(body, new_requirement, new_trace, generated_at=timestamp,
                            uncovered_analysis=gate.get('uncovered_analysis', ()), changes=changes)
                new_trace['meta']['content_hash'] = renderer.content_hash(text.encode('utf-8'))
                new_trace['meta']['content_baseline'] = text
                payload.update({'prd/prd.md': text.encode('utf-8'), 'prd/prd-trace.json': _encode(new_trace),
                                'requirement.json': _encode(new_requirement)})
            if not _stage_payload(root, candidate, payload, related_analyses, True, diagnostics, snapshots=snapshots):
                return {'status': 'fail', 'diagnostics': diagnostics, 'candidate_dir': str(candidate), 'written': [], 'edited': False}
            result = {'status': 'warning' if diagnostics else 'pass', 'diagnostics': diagnostics, 'version': version,
                      'edited': mode != 'detect', 'detected': mode != 'layout', 'generated': False,
                      'manual_edits': comparison, 'candidate_dir': str(candidate)}
            return _commit_payload(root, before, payload, guards, result)
    except (OSError, ValueError, KeyError, TypeError) as error:
        written = [name for name, raw in payload.items() if before.get(name) != raw and _raw(root / name) == raw] if _has_journal(root) else []
        return {'status': 'fail', 'diagnostics': diagnostics + [_diagnostic(error)], 'candidate_dir': str(candidate) if candidate else None,
                'written': written, 'edited': False, 'transaction_complete': False, 'recovery_required': _has_journal(root)}


def main(argv=None) -> int:
    """执行首稿、显式同步/编辑、只读比较或恢复；argv 为命令参数，返回 pass0/warning1/fail2。

    单个 JSON 输出真实结果；参数缺失由 argparse 报错，安装故障原样抛出，不自动承认过期分析。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirement_dir", type=Path)
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--body", type=Path)
    parser.add_argument("--gaps", type=Path)
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--related-analysis", action="append", type=Path, default=[])
    parser.add_argument("--allow-stale", action="store_true")
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--sync", action="store_true", help="按当前分析同步已有 PRD；已发布需求另建工作稿")
    parser.add_argument('--previous-analysis', type=Path, help='缺章节依据的旧稿可显式提供匹配原基准修订的旧分析')
    parser.add_argument('--inspect-edits', action='store_true', help='只读比较正文摘要及实际手改差异')
    parser.add_argument('--edit', choices=('layout', 'detect', 'keep'), help='显式处理排版、手改检测或用户坚持保留')
    parser.add_argument('--previous-body', type=Path, help='缺正文基准旧稿的 hash 匹配旧正文')
    parser.add_argument('--base-prd-version')
    parser.add_argument('--base-analysis-revision', type=int)
    parser.add_argument('--base-content-hash', help='读取时当前正文实际摘要，不是追溯中的旧摘要')
    parser.add_argument('--edit-summary')
    parser.add_argument('--meaning-reviewed', action='store_true', help='模型已逐差异核对排版候选不改变含义')
    parser.add_argument('--keep-confirmed', action='store_true', help='仅对应用户实际坚持保留内容性手改的回答')
    args = parser.parse_args(argv)
    if sum(bool(value) for value in (args.recover, args.sync, args.inspect_edits, args.edit)) > 1:
        parser.error('恢复、同步、只读编辑比较和编辑处理模式互斥')
    editing_inputs = any((args.base_prd_version is not None, args.base_analysis_revision is not None,
                          args.base_content_hash is not None, args.edit_summary is not None, args.meaning_reviewed, args.keep_confirmed))
    if not args.edit and editing_inputs:
        parser.error('编辑读时依据和确认仅用于 --edit')
    if args.previous_body and not (args.edit or args.inspect_edits):
        parser.error('--previous-body 仅用于编辑比较或处理')
    if args.recover:
        if args.patch or args.body or args.gaps or args.previous_analysis or args.candidate_dir:
            parser.error('--recover 不接受新的候选材料')
        result = recover_draft(args.requirement_dir)
    elif args.inspect_edits:
        if args.patch or args.body or args.gaps or args.previous_analysis or args.candidate_dir:
            parser.error('--inspect-edits 是只读操作，不接收候选材料')
        result = inspect_edits(args.requirement_dir, previous_body=args.previous_body,
                              related_analyses=args.related_analysis, allow_stale=args.allow_stale)
    elif args.edit:
        if args.patch or args.gaps or args.previous_analysis:
            parser.error('编辑不接收编号补丁、缺口候选或旧分析')
        if any(value is None for value in (args.base_prd_version, args.base_analysis_revision, args.base_content_hash, args.edit_summary)):
            parser.error('编辑必须提供 --base-prd-version、--base-analysis-revision、--base-content-hash 和 --edit-summary')
        try:
            result = edit_draft(args.requirement_dir, mode=args.edit, base_prd_version=args.base_prd_version,
                    base_analysis_revision=args.base_analysis_revision, base_content_hash=args.base_content_hash,
                    summary=args.edit_summary, body=_module('validate_prd')._read_bytes(args.body).decode('utf-8') if args.body else None,
                    meaning_reviewed=args.meaning_reviewed, keep_confirmed=args.keep_confirmed,
                    previous_body=args.previous_body, related_analyses=args.related_analysis,
                    allow_stale=args.allow_stale, candidate_dir=args.candidate_dir)
        except (OSError, ValueError, KeyError, TypeError) as error:
            result = {'status': 'fail', 'diagnostics': [_diagnostic(error)], 'written': [], 'edited': False}
    else:
        if not args.patch or not args.body:
            parser.error('保存草稿需要 --patch 和 --body')
        try:
            result = write_draft(args.requirement_dir, patch=_read_json(args.patch), body=_module('validate_prd')._read_bytes(args.body).decode('utf-8'),
                                gaps=_read_json(args.gaps) if args.gaps else None, candidate_dir=args.candidate_dir,
                                related_analyses=args.related_analysis, allow_stale=args.allow_stale, sync=args.sync, previous_analysis=args.previous_analysis)
        except (OSError, ValueError, KeyError, TypeError) as error:
            result = {'status': 'fail', 'diagnostics': [_diagnostic(error)], 'written': [], 'generated': False}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return EXIT_CODES[result["status"]]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    raise SystemExit(main())

"""根据权威元数据渲染草稿提示、文档信息和生成记录，并计算正文原始字节摘要。"""

import argparse
import difflib
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re


# 固定使用北京时间（UTC+8），使显示结果不受运行机器的时区影响。
BEIJING_TIMEZONE = timezone(timedelta(hours=8))


@lru_cache(maxsize=1)
def _validator():
    """从本 Skill 加载既有格式定义，避免渲染与校验各自维护提示和版本规则。"""
    spec = importlib.util.spec_from_file_location("prd_render_validator", Path(__file__).with_name("validate_prd.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def content_hash(content: bytes) -> str:
    """返回正文原始 content 字节的 SHA-256 摘要；不归一化换行，无预期业务异常。"""
    return "sha256:" + hashlib.sha256(content).hexdigest()


def compare_content(content: bytes, trace: dict, *, previous_content: bytes | None = None) -> dict:
    """比较实际正文与追溯基准，返回原始摘要、完整差异和受影响定位；不判断含义或写文件。

    content 为当前 Markdown 原始字节；trace 提供 content_hash 和兼容选填的 content_baseline。
    previous_content 可显式补充 hash 匹配的旧稿；旧稿不足时返回 baseline_available=False，
    不猜测旧正文。非法 UTF-8、基准类型或摘要不匹配抛出 ValueError/UnicodeError/KeyError。
    """
    expected = trace['meta']['content_hash']
    actual = content_hash(content)
    baseline = trace['meta'].get('content_baseline')
    if baseline is not None:
        if not isinstance(baseline, str) or content_hash(baseline.encode('utf-8')) != expected:
            raise ValueError('正文比较基准与 content_hash 不符，不能用于判断手工修改')
    if previous_content is not None:
        if content_hash(previous_content) != expected:
            raise ValueError('显式旧正文摘要不匹配 content_hash，不猜测或替换比较基准')
        baseline = previous_content.decode('utf-8')
    if baseline is None and actual == expected:
        baseline = content.decode('utf-8')
    current = content.decode('utf-8')
    result = {'changed': actual != expected, 'content_hash': actual, 'expected_content_hash': expected,
              'baseline_available': baseline is not None, 'diff': None, 'affected_prd_ids': [], 'affected_sections': []}
    if baseline is not None:
        result['diff'] = ''.join(difflib.unified_diff(baseline.splitlines(keepends=True), current.splitlines(keepends=True),
                                                   fromfile='last-saved/prd.md', tofile='current/prd.md'))
        old, new = _validator()._blocks(baseline, []), _validator()._blocks(current, [])
        for kind, target in (('item', 'affected_prd_ids'), ('section', 'affected_sections')):
            result[target] = sorted(key for key in old[kind].keys() | new[kind].keys()
                                    if old[kind].get(key, {}).get('text') != new[kind].get(key, {}).get('text'))
    return result


def _cell(value):
    """转义表格分隔符和换行，防止标题等展示数据破坏文档信息表。"""
    return html.escape(str(value), quote=False).replace("|", "&#124;").replace("\r\n", "<br>").replace("\r", "<br>").replace("\n", "<br>")


def _take_section(body, key):
    """取出并移除唯一的信息或记录块；重复或不完整标记抛出 ValueError。"""
    opening = re.compile(r"<!--\s*prd:section\s+" + re.escape(key) + r"\s*-->")
    matches = list(opening.finditer(body))
    if len(matches) > 1:
        raise ValueError(f"重复章节：{key}")
    if not matches:
        return body
    begin = matches[0]
    ending = re.search(r"<!--\s*/prd:section\s*-->", body[begin.end():])
    if ending is None:
        raise ValueError(f"章节未闭合：{key}")
    end = begin.end() + ending.end()
    # 不吞掉交叉章节；否则渲染可能把模型的非法结构变成看似合法的候选。
    if re.search(r"<!--\s*prd:section\b", body[begin.end():begin.end() + ending.start()]):
        raise ValueError(f"章节交叉：{key}")
    return body[:begin.start()] + body[end:]


def format_display_time(value: str) -> str:
    """将 PRD 中的 value 时间显示为北京时间的年月日和时分秒，不改动日志。

    支持 ISO 8601 时间戳及已渲染的时间；无法解析的历史文本原样返回，不抛出解析异常。
    """
    try:
        stamp = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return value
    # 评审和发布会重读生成时间；已渲染的无偏移时间是北京时间，不能再加八小时。
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(BEIJING_TIMEZONE)
    return stamp.replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")


def render_info(body: str, requirement: dict, trace: dict, *, generated_at: str, uncovered_analysis=(), changes: str | None = None) -> str:
    """返回带权威文档信息的 Markdown，不写文件。

    body 为模型候选正文；requirement 提供 common/prd，trace 提供草稿类型快照。
    generated_at 为本次实际生成时间，uncovered_analysis 为明确的降级项；changes 非空时替换生成记录。
    缺元数据、非法版本/草稿类型、空时间或信息块重复/交叉时抛出 KeyError/ValueError。
    其他正文原文保留，不改写业务内容，也不把渲染成功当作完整校验。
    """
    validator = _validator()
    common, prd = requirement["common"], requirement["prd"]
    kind = trace["meta"]["draft_kind"]
    if kind not in validator.PROMPTS or not validator.VERSION.fullmatch(str(prd["version"])):
        raise ValueError("非法草稿类型或 PRD 版本")
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("生成时间不能为空")
    value = body
    for prompt in validator.PROMPTS.values():
        if value.startswith(prompt):
            value = value[len(prompt):].lstrip("\r\n")
            break
    value = _take_section(value, "info")
    if changes is not None:
        value = _take_section(value, "changes")
    pairs = [("需求编号", common["requirement_id"]), ("标题", common["title"]), ("PRD 版本", prd["version"]),
             ("状态", prd["status"]), ("草稿类型", kind), ("基于的分析修订号", prd["based_on_analysis_revision"]),
             ("生成时间", format_display_time(generated_at)), ("未覆盖的分析项", "、".join(uncovered_analysis) if uncovered_analysis else "无")]
    table = "\n".join(["| 字段 | 值 |", "| --- | --- |", *(f"| {name} | {_cell(item)} |" for name, item in pairs)])
    info = "<!-- prd:section info -->\n# 文档信息\n\n" + table + "\n<!-- /prd:section -->"
    record = "" if changes is None else "\n\n<!-- prd:section changes -->\n# 变更记录\n\n" + changes + "\n<!-- /prd:section -->"
    prompt = "" if prd["status"] in {"released", "deprecated"} else validator.PROMPTS[kind] + "\n\n"
    return prompt + info + record + "\n\n" + value.strip("\r\n") + "\n"


def main(argv=None) -> int:
    """读取候选和权威元数据，向 stdout 输出渲染结果；argv 为 CLI 参数。

    成功返回 0，输入错误返回 2 并输出 JSON；不保存正式正文或元数据，安装损坏原样抛出。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirement_dir", type=Path)
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--generated-at")
    parser.add_argument("--uncovered", action="append", default=[])
    args = parser.parse_args(argv)
    validator = _validator()
    try:
        text = render_info(args.body.read_text(encoding="utf-8"), validator._json(args.requirement_dir / "requirement.json"),
                           validator._json(args.trace), generated_at=args.generated_at or datetime.now(timezone.utc).isoformat(),
                           uncovered_analysis=args.uncovered)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "fail", "message": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "pass", "markdown": text, "content_hash": content_hash(text.encode("utf-8"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

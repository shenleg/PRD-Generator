"""在显式索引范围内有限读取资料，返回可追溯的关键词命中。"""

from datetime import date
import importlib.util
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location("project_sources", Path(__file__).with_name("project_sources.py"))
_p = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p)


def main(argv=None):
    """执行资料检索；argv 为参数列表或默认进程参数，返回退出码，预期错误转为 JSON。"""
    try:
        parser = _p.Parser()
        parser.add_argument("--project-root", required=True)
        parser.add_argument("--query", required=True)
        for option in ("requirement", "module", "tag", "term"):
            parser.add_argument("--" + option)
        parser.add_argument("--limit", type=int, default=5)
        parser.add_argument("--max-chars", type=int, default=2000)
        parser.add_argument("--as-of")
        parser.add_argument("--max-age-days", type=int, default=365)
        args = parser.parse_args(argv)
        words = args.query.casefold().split()
        if not words or not 1 <= args.limit <= 20 or not 1 <= args.max_chars <= 20000 or args.max_age_days <= 0:
            raise _p.InputError("query、limit、max-chars 或 max-age-days 非法")
        if any(v is not None and not v.strip() for v in (args.requirement, args.module, args.tag, args.term)):
            raise _p.InputError("筛选条件不能为空")
        today = _p.parse_date(args.as_of) if args.as_of else date.today()
        root = _p.root_path(args.project_root)
        diagnostics, results, stale = [], [], []
        with _p.locked(root):
            project_path = _p.safe_path(root, "index/project-index.json")
            source_path = _p.safe_path(root, "index/source-index.json")
            if not project_path.exists() and not source_path.exists():
                return _p.output({"status": "warning", "diagnostics": [{"level": "warning", "message": "缺少索引，请先重新索引；未找到不代表无冲突。"}], "results": [], "stale_sources": []})
            if not project_path.exists() or not source_path.exists():
                raise _p.InputError("索引不一致，请重新索引")
            project, index = _p.strict_json(project_path), _p.strict_json(source_path)
            if not isinstance(project, dict) or not isinstance(index, dict) or not isinstance(index.get("sources"), list):
                raise _p.InputError("索引结构非法，请重新索引")
            sources = index["sources"]
            fingerprint = _p.digest(_p.encoded(sources))
            if (project.get("version") != 1 or index.get("version") != 1 or
                project.get("fingerprint") != fingerprint or index.get("fingerprint") != fingerprint or
                project.get("source_count") != len(sources)):
                raise _p.InputError("索引不一致，请重新索引")
            catalog = [{k: v for k, v in source.items() if k not in ("sha256", "size_bytes")} for source in sources]
            _p.validate_catalog(catalog)
            remaining = _p.MAX_TOTAL
            read_count = 0
            truncated = False
            for source in sources:
                def matches(value, expected):
                    return expected is None or (isinstance(value, str) and value.casefold() == expected.casefold())
                if not matches(source.get("requirement_id"), args.requirement) or not matches(source.get("module"), args.module):
                    continue
                if args.tag and not any(matches(x, args.tag) for x in source.get("tags", [])):
                    continue
                if args.term and not any(matches(x, args.term) for x in source.get("terms", [])):
                    continue
                if read_count >= _p.MAX_FILES or remaining <= 0:
                    truncated = True
                    break
                size = source.get("size_bytes")
                if not isinstance(size, int) or size < 0 or size > _p.MAX_FILE or not isinstance(source.get("sha256"), str):
                    raise _p.InputError("来源索引元数据非法，请重新索引")
                if size > remaining:
                    truncated = True
                    continue
                read_count += 1
                try:
                    data, text = _p.read_source(root, source["path"], min(_p.MAX_FILE, remaining))
                except (OSError, UnicodeError, _p.InputError):
                    stale.append({"source_id": source["source_id"], "path": source["path"], "reason": "资料缺失或不可读取，请重新索引"})
                    continue
                remaining -= len(data)
                if _p.digest(data) != source["sha256"]:
                    stale.append({"source_id": source["source_id"], "path": source["path"], "reason": "资料指纹已变化，请重新索引"})
                    continue
                updated = source["last_updated"]
                if updated is None:
                    diagnostics.append({"level": "warning", "source_id": source["source_id"], "message": "业务更新时间未知，请复核。"})
                else:
                    age = (today - _p.parse_date(updated)).days
                    if age < 0:
                        diagnostics.append({"level": "warning", "source_id": source["source_id"], "message": "业务更新时间在参考日期之后，不可信，请复核。"})
                    elif age > args.max_age_days:
                        diagnostics.append({"level": "warning", "source_id": source["source_id"], "message": "资料可能过期，请复核。"})
                folded = text.casefold()
                found = [word for word in words if word in folded]
                if not found:
                    continue
                # 使用行内匹配构造定位，避免摘要偏离证据位置。
                lines = text.splitlines()
                line_number, line = next(((i, line) for i, line in enumerate(lines, 1) if any(w in line.casefold() for w in found)), (1, text))
                position = min((line.casefold().find(w) for w in found if w in line.casefold()), default=0)
                start = max(0, position - 100)
                if start > 0 or len(line) > start + 400:
                    truncated = True
                result = {k: source.get(k) for k in ("source_id", "path", "requirement_id", "authority", "credibility", "revision", "sha256")}
                result.update({"location": f"line {line_number}", "excerpt": line[start:start + 400], "fingerprint": fingerprint, "score": len(found)})
                results.append(result)
        results.sort(key=lambda r: (-r["score"], r["source_id"], r["path"]))
        if len(results) > args.limit:
            truncated = True
        results = results[:args.limit]
        remaining_chars = args.max_chars
        for result in results:
            if len(result["excerpt"]) > remaining_chars:
                result["excerpt"] = result["excerpt"][:remaining_chars]
                truncated = True
            remaining_chars -= len(result["excerpt"])
        if stale:
            diagnostics.append({"level": "warning", "message": "部分资料已变化或丢失，已排除正文；请重新索引。"})
        if truncated:
            diagnostics.append({"level": "warning", "message": "检索结果或读取预算已截断，请缩小筛选范围。"})
        if not results:
            diagnostics.append({"level": "warning", "message": "未找到不代表无冲突，请复核资料范围。"})
        return _p.output({"status": "warning" if diagnostics else "pass", "diagnostics": diagnostics, "results": results, "stale_sources": stale, "fingerprint": fingerprint, "truncated": truncated})
    except (OSError, ValueError, UnicodeError, TypeError, KeyError, _p.InputError) as error:
        result = _p.failure(error)
        result.update({"results": [], "stale_sources": []})
        return _p.output(result)


if __name__ == "__main__":
    sys.exit(main())

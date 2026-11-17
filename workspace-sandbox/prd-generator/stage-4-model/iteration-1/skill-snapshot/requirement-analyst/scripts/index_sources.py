"""根据显式清单创建项目资料元数据索引，不修改资料正文。"""

import importlib.util
import os
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location("project_sources", Path(__file__).with_name("project_sources.py"))
_p = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p)


def main(argv=None):
    """执行索引命令；argv 为参数列表或默认进程参数，返回退出码，预期输入错误转为 JSON。"""
    try:
        parser = _p.Parser()
        parser.add_argument("--project-root", required=True)
        parser.add_argument("--catalog", required=True)
        args = parser.parse_args(argv)
        root = _p.root_path(args.project_root)
        catalog_path = Path(args.catalog)
        outputs = {_p.safe_path(root, "index/" + name).resolve() for name in ("source-index.json", "project-index.json")}
        if catalog_path.resolve() in outputs:
            raise _p.InputError("显式catalog不能同时作为索引输出目标；输入清单保持只读")
        catalog = _p.strict_json(catalog_path)
        _p.validate_catalog(catalog)
        with _p.locked(root):
            sources = []
            for item in catalog:
                if item["path"] in {"index/source-index.json", "index/project-index.json", ".analysis.lock"}:
                    raise _p.InputError("索引目标或分析锁不能作为原始资料")
                data, _ = _p.read_source(root, item["path"])
                source = dict(item)
                source.setdefault("authority", "unconfirmed")
                source["sha256"] = _p.digest(data)
                source["size_bytes"] = len(data)
                sources.append(source)
            sources.sort(key=lambda x: x["source_id"])
            fingerprint = _p.digest(_p.encoded(sources))
            source_index = {"version": 1, "fingerprint": fingerprint, "sources": sources}
            project_index = {"version": 1, "fingerprint": fingerprint, "source_count": len(sources)}
            directory = _p.safe_path(root, "index")
            directory.mkdir(exist_ok=True)
            root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(root_fd)
            finally:
                os.close(root_fd)
            for name, content in (("source-index.json", source_index), ("project-index.json", project_index)):
                target = _p.safe_path(root, "index/" + name)
                _p.atomic_write(target, _p.encoded(content) + b"\n")
        diagnostics = [] if sources else [{"level": "warning", "message": "资料清单为空，请补充资料后重新索引。"}]
        return _p.output({"status": "warning" if diagnostics else "pass", "diagnostics": diagnostics, "fingerprint": fingerprint, "source_count": len(sources)})
    except (OSError, ValueError, UnicodeError, TypeError, _p.InputError) as error:
        return _p.output(_p.failure(error))


if __name__ == "__main__":
    sys.exit(main())

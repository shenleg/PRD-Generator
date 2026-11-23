"""知识建议经具体批准后写入项目；确认记录是声明，不是身份认证。"""

from datetime import datetime, timezone
import importlib.util
import os
from pathlib import Path
import re
import sys
import unicodedata


_spec = importlib.util.spec_from_file_location("project_sources", Path(__file__).with_name("project_sources.py"))
_p = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p)


def _validate_proposal(proposal, root):
    """核对建议资格与项目范围；无返回值，不合格声明抛InputError。"""
    fields = {"proposal_version", "project_id", "knowledge_id", "category", "kind", "content",
              "scope", "simulation", "basis", "sources"}
    if not isinstance(proposal, dict) or set(proposal) != fields or proposal["proposal_version"] != "1.0":
        raise _p.InputError("建议字段或proposal_version非法")
    for key in ("project_id", "knowledge_id", "category", "kind", "content", "scope"):
        if not isinstance(proposal[key], str) or not proposal[key].strip():
            raise _p.InputError(f"{key}须为非空文本")
    # 目录名在 macOS 可能以分解形式存储；项目编号仍区分大小写。
    if unicodedata.normalize("NFC", proposal["project_id"]) != unicodedata.normalize("NFC", root.name):
        raise _p.InputError("project_id与指定项目目录不一致")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", proposal["knowledge_id"]):
        raise _p.InputError("knowledge_id须为不超过80字符的单一路径标识")
    categories = {"term": "domain", "business_rule": "product", "technical_constraint": "technical"}
    if categories.get(proposal["kind"]) != proposal["category"]:
        raise _p.InputError("仅支持术语/domain、业务规则/product、技术限制/technical")
    if type(proposal["simulation"]) is not bool:
        raise _p.InputError("simulation必须明确为true或false")
    basis = proposal["basis"]
    if (not isinstance(basis, dict) or set(basis) != {"status", "confirmed_by", "statement"}
            or basis.get("status") != "confirmed"
            or any(not isinstance(basis.get(key), str) or not basis[key].strip()
                   for key in ("confirmed_by", "statement"))):
        raise _p.InputError("推断和未确认事项不得沉淀；须先有明确的事实确认依据")


def _check_sources(proposal, root):
    """在锁内限量核对实际来源指纹；无返回值，缺失或变化抛异常。"""
    sources = proposal["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= _p.MAX_FILES:
        raise _p.InputError("须有1至64项明确来源")
    remaining = _p.MAX_TOTAL
    for source in sources:
        if (not isinstance(source, dict) or set(source) != {"path", "location", "sha256"}
                or any(not isinstance(source[key], str) or not source[key].strip() for key in source)
                or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"])):
            raise _p.InputError("来源须有相对路径、章节定位和SHA-256")
        data, _ = _p.read_source(root, source["path"], budget=remaining)
        remaining -= len(data)
        if _p.digest(data) != source["sha256"]:
            raise _p.InputError("来源已变化；重新核对依据并提交新建议及批准")


def main(argv=None):
    """解析公开CLI并返回退出码；输入错误输出单一JSON，内部编程错误传播。"""
    created = False
    relative = None
    try:
        parser = _p.Parser(description="将明确批准的知识建议写入项目，不自动确认业务事实")
        parser.add_argument("--project-root", required=True)
        parser.add_argument("--proposal", required=True)
        parser.add_argument("--approval", required=True)
        args = parser.parse_args(argv)
        root = _p.root_path(args.project_root)
        proposal = _p.strict_json(Path(args.proposal))
        approval = _p.strict_json(Path(args.approval))
        _validate_proposal(proposal, root)
        fingerprint = _p.digest(_p.encoded(proposal))
        if not isinstance(approval, dict) or approval.get("proposal_sha256") != fingerprint:
            raise _p.InputError("批准指纹与完整建议不一致，须重新展示并确认")
        if (set(approval) != {"proposal_sha256", "decision", "actor", "user_statement"}
                or approval.get("decision") != "approve"
                or any(not isinstance(approval.get(key), str) or not approval[key].strip()
                       for key in ("actor", "user_statement"))):
            raise _p.InputError("须有明确approve决定、确认者和实际用户原话；脚本不验证身份或代替人工审批")
        relative = f"knowledge/{proposal['category']}/{proposal['knowledge_id']}.json"
        record = {"entry_version": "1.0", "proposal": proposal, "proposal_sha256": fingerprint,
                  "approval": approval, "saved_at": datetime.now(timezone.utc).isoformat()}
        data = _p.encoded(record) + b"\n"
        with _p.locked(root):
            _check_sources(proposal, root)
            target = _p.safe_path(root, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            # 排他新建，失败保留现场；未经成功响应的文件不得纳入正式索引。
            descriptor = _p.fs.open_exclusive(target)
            created = True
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            for directory in (target.parent, target.parent.parent, root):
                _p.fs.sync_directory(directory)
        return _p.output({"status": "pass", "written": True, "file_created": True, "path": relative,
                          "proposal_sha256": fingerprint, "diagnostics": []})
    except (OSError, ValueError, UnicodeError, TypeError, _p.InputError) as error:
        return _p.output({**_p.failure(error), "written": False, "file_created": created, "path": relative})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.exit(main())

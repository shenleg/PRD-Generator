"""项目资料索引与检索共用的严格输入、锁和文件操作。"""

import argparse
from contextlib import contextmanager
from datetime import date
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from jsonschema import Draft202012Validator

# 单份资料上限和单次检索预算，防止误读大型或过多文件。
MAX_FILE = 1024 * 1024
MAX_TOTAL = 2 * 1024 * 1024
MAX_FILES = 64
AUTHORITY = {"current_published", "current_spec", "historical_published", "draft", "unconfirmed"}


class InputError(Exception):
    """表示可向调用者报告的输入或工作区错误。"""


class Parser(argparse.ArgumentParser):
    """将参数解析错误转换成统一 JSON 诊断。"""

    def error(self, message):
        """报告解析错误；message 为原因，无返回值，抛出 InputError。"""
        raise InputError(message)


def strict_json(path):
    """读取严格 JSON；path 为文件，返回对象，非法内容或读取失败时抛异常。"""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InputError(f"JSON 重复字段：{key}")
            result[key] = value
        return result

    def invalid(value):
        raise InputError(f"JSON 非法数值：{value}")

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=invalid)


def safe_path(root, value):
    """验证项目内相对路径并拒绝符号链接；失败时抛 InputError。"""
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        raise InputError("路径必须是项目内相对路径")
    parts = value.split("/")
    if any(not p or p in (".", "..") or any(ord(c) < 32 for c in p) for p in parts):
        raise InputError("路径含非法路径段")
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise InputError(f"路径不能包含符号链接：{value}")
    if not current.resolve().is_relative_to(root):
        raise InputError("路径越过项目根")
    return current


def read_source(root, value, budget=MAX_FILE):
    """读取受限普通 UTF-8 文本；value 为相对路径，返回字节和文本，非法时抛异常。"""
    path = safe_path(root, value)
    # O_NOFOLLOW 防止最后路径段在检查后被替换为符号链接。
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > min(MAX_FILE, budget):
            raise InputError("资料不是普通文件或超过读取预算")
        data = stream.read(min(MAX_FILE, budget) + 1)
    if len(data) > min(MAX_FILE, budget) or b"\0" in data:
        raise InputError("资料不是有效文本或超过读取预算")
    return data, data.decode("utf-8")


def digest(data):
    """计算 data 的 SHA-256 十六进制值；不改变数据，不主动抛异常。"""
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    """将 JSON 对象规范编码为字节；不支持的值或非有限数字抛异常。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def atomic_write(path, data):
    """原子替换文件并同步文件和目录；path 为目标、data 为内容，失败抛异常。"""
    fd, temporary = tempfile.mkstemp(prefix=".index-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(root):
    """取得工作区分析锁并拒绝未完成事务；root 为项目根，失败抛异常。"""
    workspace = next((p for p in (root, *root.parents) if (p / "workspace.json").is_file()), root)
    lock = workspace / ".analysis.lock"
    if lock.is_symlink():
        raise InputError("分析锁不能是符号链接")
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        for journal in {workspace / ".analysis-transaction.json", root / ".analysis-transaction.json"}:
            if journal.is_symlink():
                raise InputError("事务日志不能是符号链接")
            if journal.exists() and strict_json(journal) is not None:
                raise InputError("存在未完成 analysis 事务，请先恢复")
        yield


def root_path(value):
    """检查项目根目录，返回规范绝对路径；不存在或为符号链接时抛异常。"""
    path = Path(value).expanduser().absolute()
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_dir():
        raise InputError("project-root 必须是实际目录")
    return path.resolve()


def validate_catalog(catalog):
    """按来源 schema 和索引元数据约束校验 catalog；无返回值，非法时抛 InputError。"""
    schema = strict_json(Path(__file__).resolve().parent.parent / "schemas/source.schema.json")
    validator = Draft202012Validator({"$ref": "#/$defs/manifest", "$defs": schema["$defs"]})
    errors = list(validator.iter_errors(catalog))
    if errors:
        raise InputError(f"资料清单不符合来源 schema：{errors[0].message}")
    allowed = {"source_id", "name", "path", "type", "credibility", "last_updated", "revision", "requirement_id", "module", "tags", "terms", "authority", "publication_basis"}
    ids = set()
    for item in catalog:
        if set(item) - allowed:
            raise InputError("资料清单包含未知字段")
        if item["source_id"] in ids:
            raise InputError("source_id 重复")
        ids.add(item["source_id"])
        if item.get("authority", "unconfirmed") not in AUTHORITY:
            raise InputError("authority 非法")
        if item.get("authority") in {"current_published", "current_spec"} and not (isinstance(item.get("publication_basis"), str) and item["publication_basis"].strip()):
            raise InputError("当前发布/正式规范须显式publication_basis；不能由文件名推断")
        for key in ("requirement_id", "module"):
            if key in item and (not isinstance(item[key], str) or not item[key].strip()):
                raise InputError(f"{key} 必须是非空字符串")
        for key in ("tags", "terms"):
            if key in item and (not isinstance(item[key], list) or any(not isinstance(x, str) or not x.strip() for x in item[key])):
                raise InputError(f"{key} 必须是非空字符串数组")
        if item["last_updated"] is not None:
            parse_date(item["last_updated"])


def parse_date(value):
    """严格解析 ISO 日期 value；返回日期，格式非法时抛 InputError。"""
    try:
        result = date.fromisoformat(value)
        if result.isoformat() != value:
            raise ValueError()
        return result
    except (TypeError, ValueError):
        raise InputError("日期必须为 YYYY-MM-DD") from None


def output(result):
    """输出单个 JSON 结果并返回对应退出码；result 为结果，编码错误会传播。"""
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return {"pass": 0, "warning": 1, "fail": 2}[result["status"]]


def failure(error):
    """将异常转换为失败结果；error 为错误，返回 JSON 对象，不主动抛异常。"""
    return {"status": "fail", "diagnostics": [{"level": "fail", "message": str(error)}]}

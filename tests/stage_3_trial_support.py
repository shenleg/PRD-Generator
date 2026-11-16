"""阶段 3 试跑记录工具：原样接收模型补丁、调用真实写入器并保存证据，不调用模型或补业务答案。"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "workspace-sandbox/stage-3"
WORKSPACE = RUNS / "workspace"


def load_module(path: Path, name: str):
    """按 path 加载工具模块并返回；导入、文件或安装错误直接抛出。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_trial(patch_path: Path, project: str, record: str) -> dict:
    """原样保存 patch_path 并应用到试跑 project，返回真实响应。

    record 为本次唯一证据目录名；已存在则拒绝覆盖。保存候选、脚本响应和当前
    分析目录快照，不编辑模型补丁。文件、JSON、重复证据或内部安装错误直接抛出。
    """
    for name, value in (("record", record), ("project", project)):
        if not value or Path(value).name != value or value in (".", "..") or "\\" in value:
            raise ValueError(f"{name} 必须是单一路径段")
    destination = RUNS / "evidence" / project / record
    if destination.exists():
        raise FileExistsError(f"保留旧证据，拒绝覆盖：{destination}")
    raw = patch_path.read_bytes()
    patch = json.loads(raw)
    destination.mkdir(parents=True)
    (destination / "patch.json").write_bytes(raw)
    updater = load_module(ROOT / "skill/requirement-analyst/scripts/update_analysis.py", "trial_updater")
    result = updater.update_analysis(WORKSPACE, project, patch)
    (destination / "response.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destination / "provenance.json").write_text(json.dumps({"patch_sha256": hashlib.sha256(raw).hexdigest(), "origin": str(patch_path), "mode": "actual_patch_application"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    requirement_id = result.get("requirement_id") or patch.get("requirement_id")
    if requirement_id and Path(requirement_id).name == requirement_id:
        directory = WORKSPACE / "projects" / project / "requirements" / requirement_id / "analysis"
        if directory.is_dir():
            shutil.copytree(directory, destination / "analysis")
    return result


def main() -> None:
    """读取进程命令行，记录一次补丁应用并退出，无返回值。

    文件、JSON 或重复证据错误直接抛出；合法响应按 pass/warning/fail 以
    SystemExit 返回退出码，不静默替换已有证据。
    """
    parser = argparse.ArgumentParser(description="应用一次模型补丁并保存当前结果快照，不运行模型")
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--record", required=True)
    args = parser.parse_args()
    result = apply_trial(args.patch, args.project, args.record)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit({"pass": 0, "warning": 1, "fail": 2}[result["status"]])


if __name__ == "__main__":
    main()

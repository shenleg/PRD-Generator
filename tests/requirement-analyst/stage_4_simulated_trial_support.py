"""阶段 4 模拟业务试用：原样应用候选补丁、调用消费者并留存 CLI 及工作区快照。"""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
TRIAL = ROOT / "workspace-sandbox/stage-4/simulated-trial-01"
WORKSPACE = TRIAL / "workspace"
PROJECT = "office-procurement"
REQUIREMENT = "SIM-PROCUREMENT-001"
DIRECTORY = WORKSPACE / "projects" / PROJECT / "requirements" / REQUIREMENT


def _record(name):
    if not name or Path(name).name != name or name in {".", ".."} or "\\" in name:
        raise ValueError("record 必须是单一路径段")
    path = TRIAL / "evidence" / name
    path.mkdir(parents=True, exist_ok=False)
    return path


def _save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _execute(destination, command):
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
    _save(destination / "process.json", {"argv": command, "returncode": process.returncode, "stderr": process.stderr, "stdout": process.stdout})
    result = json.loads(process.stdout)
    _save(destination / "response.json", result)
    if DIRECTORY.exists():
        shutil.copytree(DIRECTORY, destination / "requirement")
    if process.returncode != {"pass": 0, "warning": 1, "fail": 2}[result["status"]]:
        raise RuntimeError("CLI 状态与退出码不一致；保留实际响应")
    return result


def apply_patch(patch_path: Path, record: str) -> dict:
    """原样保存 patch_path 后通过真实更新器 CLI 提交，返回实际结果。

    record 为新的证据目录名，存在时拒绝覆盖；快照包含当时的结果、来源、事件及 PRD。
    文件、JSON、超时和执行错误直接抛出，业务 fail 则原样返回并保留证据。
    """
    destination = _record(record)
    raw = Path(patch_path).read_bytes()
    (destination / "patch.json").write_bytes(raw)
    _save(destination / "provenance.json", {"mode": "actual_cli_patch_application", "patch_sha256": hashlib.sha256(raw).hexdigest(), "origin": str(patch_path), "business_input": "simulated_not_real_user_decision"})
    command = [sys.executable, "-I", "-B", str(ROOT / "skill/requirement-analyst/scripts/update_analysis.py"),
               "--workspace", str(WORKSPACE), "--project", PROJECT, "--patch", str(destination / "patch.json")]
    return _execute(destination, command)


def consume_trial(record: str, *, revision: int, inspect_only: bool = False) -> dict:
    """通过真实消费者 CLI 消费已读取的 revision，返回实际响应并保存快照。

    record 必须是新证据目录，inspect_only 仅检查同步。生成时要求存在有效验收条目；
    不存在则保留缺口回交响应，不补答案。文件、JSON、超时和执行错误直接抛出。
    """
    destination = _record(record)
    command = [sys.executable, "-I", "-B", str(ROOT / "tools/minimal_prd_consumer.py"), "--workspace", str(WORKSPACE),
               "--project", PROJECT, "--requirement", REQUIREMENT, "--expected-revision", str(revision),
               "--require-section", "requirements.acceptance_criteria"]
    if inspect_only:
        command.append("--inspect-only")
    return _execute(destination, command)

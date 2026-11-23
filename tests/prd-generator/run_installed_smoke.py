"""从无关目录通过项目解释器验证双 Skill 安装、分析保存、草稿恢复和并发；不进入默认测试发现。"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


_ROOT = Path(__file__).resolve().parents[2]
_PYTHON_FLAGS = ("-I", "-B", "-X", "utf8")
_EXIT_CODES = {"pass": 0, "warning": 1, "fail": 2}
_PROJECT_ID = "smoke"
_FEATURE = "支持检索合成记录"
_EVENTS = "prd/prd-events.jsonl"
_FAILURE_MARKER = "installed-smoke: interrupted PRD event publication"

# 在该子进程模拟业务事件写入中断，保留生产 CLI 自己写出的可恢复事务。
_INTERRUPT_EVENT_REPLACE = f"""
import os
from pathlib import Path
import runpy
import sys

_, target, script, *args = sys.argv
real_replace = os.replace

def replace(source, destination, *args, **kwargs):
    \"\"\"仅中断合成工作区的事件发布；其他路径透传替换结果和异常。\"\"\"
    if Path(destination) == Path(target):
        raise OSError({_FAILURE_MARKER!r})
    return real_replace(source, destination, *args, **kwargs)

os.replace = replace
sys.argv = [script, *args]
runpy.run_path(script, run_name='__main__')
"""


def _check(condition: bool, message: str) -> None:
    """要求 condition 成立，无返回；否则以 message 抛出 AssertionError。"""
    if not condition:
        raise AssertionError(message)


def _run(python: Path, cwd: Path, *args: str | Path) -> subprocess.CompletedProcess:
    """从 cwd 执行指定 python 的 args，返回过程输出；启动或超时异常原样抛出。"""
    # 已安装命令不应等待网络；一分钟用于给慢磁盘和进程调度留余量。
    return subprocess.run([str(python), *_PYTHON_FLAGS, *map(str, args)], cwd=cwd,
                          capture_output=True, encoding="utf-8", timeout=60)


def _cli(python: Path, cwd: Path, script: Path, *args: str | Path,
         interrupt_event: Path | None = None) -> dict:
    """执行安装态 script 及 args，返回符合退出码约定的 JSON；协议不符时附进程诊断。"""
    bootstrap = ("-c", _INTERRUPT_EVENT_REPLACE, interrupt_event) if interrupt_event is not None else ()
    process = _run(python, cwd, *bootstrap, script, *args)
    detail = f"{script.name}（退出码 {process.returncode}）\n{process.stdout}\n{process.stderr}"
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(f"未返回 JSON：{detail}") from error
    _check(isinstance(result, dict) and _EXIT_CODES.get(result.get("status")) == process.returncode,
           f"CLI 状态与退出码不一致：{detail}")
    return result


def _analysis_patch() -> dict:
    """返回可直接保存的合成首次分析，不模拟用户授权；无预期异常。"""
    return {
        "patch_version": "1.0", "requirement_id": None, "title": "安装检验，不是真实需求",
        "base_revision": 0, "change_type": "initial_analysis", "actor": "analyst", "summary": "保存合成分析",
        "operations": [{"op": "add", "collection": "requirements.functional_requirements", "ref": "$feature",
                        "value": {"content": _FEATURE, "tag": "confirmed", "status": "active",
                                  "sources": [{"type": "user_answer", "location": "合成测试输入"}]}}],
        "set": {"meta.input_type": "existing_document", "meta.analysis_status": "completed",
                "meta.readiness": "ready_for_document", "ux_assessment.ui_dependent": False},
        "completion_checks": [{"item": item, "satisfied": True, "question_refs": [], "reason": "仅验证合成流程"}
                              for item in range(1, 12)],
    }


def _body(source_ref: str) -> str:
    """以实际分析来源 source_ref 返回合成草稿正文，文档信息和变更记录由 CLI 生成；无预期异常。"""
    empty = "分析结果中无此项"
    sections = {
        "scope": empty, "scenarios": empty,
        "functional_requirements": ("<!-- prd:item PRD-FR-001 -->\n"
                                    f"PRD-FR-001：{_FEATURE}；分析来源 {source_ref}\n"
                                    "<!-- /prd:item -->"),
        "business_rules": empty, "boundaries_exceptions": empty, "acceptance_criteria": empty,
        "residuals": "无适用遗留项", "appendix": "合成输入，仅验证安装态程序链。",
    }
    return "\n\n".join(f"<!-- prd:section {key} -->\n{value}\n<!-- /prd:section -->"
                       for key, value in sections.items()) + "\n"


def _smoke(project: Path, temp: Path, cwd: Path) -> None:
    """用 project 的安装解释器从 cwd 运行 smoke，业务写入仅在 temp；失败抛出诊断。"""
    claude = project / ".claude"
    venv = claude / ".prd-skills-venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    _check(python.is_file(), f"未找到项目解释器：{python}。请先执行 install.py 或使用 --install。")
    probe = _run(python, cwd, "-c", "import sys, jsonschema, referencing; print(sys.prefix)")
    _check(probe.returncode == 0 and Path(probe.stdout.strip()).resolve() == venv.resolve(),
           f"项目解释器未加载独立依赖：{python}\n{probe.stdout}\n{probe.stderr}")

    analyst = claude / "skills/requirement-analyst/scripts/update_analysis.py"
    prd_scripts = claude / "skills/prd-generator/scripts"
    writer = prd_scripts / "write_draft.py"
    analysis_patch = temp / "分析 patch.json"
    analysis_patch.write_text(json.dumps(_analysis_patch(), ensure_ascii=False), encoding="utf-8")
    workspace = temp / "业务 workspace"
    analysis = _cli(python, cwd, analyst, "--workspace", workspace, "--project", _PROJECT_ID,
                    "--patch", analysis_patch)
    _check(analysis.get("written") is True and analysis.get("revision") == 1
           and analysis.get("id_map", {}).get("$feature") == "FR-1", f"未保存首次分析：{analysis}")
    rid = analysis["requirement_id"]
    requirement = workspace / "projects" / _PROJECT_ID / "requirements" / rid
    saved_analysis = requirement / "analysis/analysis-result.json"
    analysis_bytes = saved_analysis.read_bytes()
    items = json.loads(analysis_bytes)["requirements"]["functional_requirements"]
    _check([(item["id"], item["content"]) for item in items] == [("FR-1", _FEATURE)], "分析正文未写入工作区")

    source_ref = f"{rid}/FR-1"
    numbering = {"patch_version": "1.0", "requirement_id": rid, "base_analysis_revision": 1,
                 "items": [{"mapping_key": "smoke-search", "kind": "functional_requirement",
                            "analysis_refs": [source_ref]}]}
    patch = temp / "编号 patch.json"
    body = temp / "正文 body.md"
    patch.write_text(json.dumps({**numbering, "base_prd_version": None}), encoding="utf-8")
    body.write_bytes(_body(source_ref).encode("utf-8"))
    events = requirement / _EVENTS
    interrupted = _cli(python, cwd, writer, requirement, "--patch", patch, "--body", body,
                       "--candidate-dir", temp / "中断 candidate", interrupt_event=events)
    _check(interrupted.get("status") == "fail" and interrupted.get("generated") is False
           and interrupted.get("recovery_required") is True and not events.exists()
           and any(_FAILURE_MARKER in item["message"] for item in interrupted["diagnostics"]),
           f"注入的写入故障未留下待恢复事务，或提前发布了事件：{interrupted}")
    recovered = _cli(python, cwd, writer, requirement, "--recover")
    _check(recovered.get("generated") is True and recovered.get("recovered") is True
           and recovered.get("version") == "0.1", f"首稿恢复失败：{recovered}")
    first_event = events.read_bytes()

    # 两位写者复用同一个读时版本和正式正文，只将候选输出目录隔离；不假定谁先获得锁。
    body.write_bytes((requirement / "prd/prd.md").read_bytes())
    patch.write_text(json.dumps({**numbering, "base_prd_version": "0.1"}), encoding="utf-8")
    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = [pool.submit(_cli, python, cwd, writer, requirement, "--patch", patch,
                                "--body", body, "--candidate-dir", temp / f"写者 {label}") for label in ("A", "B")]
        results = [attempt.result() for attempt in attempts]
    winners = [result for result in results if result.get("generated") is True and result.get("version") == "0.2"]
    losers = [result for result in results if result.get("status") == "fail" and result.get("written") == []
              and any("读取时版本或分析修订冲突" in item["message"] for item in result["diagnostics"])]
    _check(len(winners) == len(losers) == 1, f"并发写入应仅有一个提交成功，另一个因读时版本过旧被拒绝：{results}")
    final = _cli(python, cwd, prd_scripts / "validate_prd.py", requirement)
    _check(final["status"] == "pass", f"干净夹具的正式草稿不应有校验警告或失败：{final}")
    metadata = json.loads((requirement / 'requirement.json').read_bytes())
    _check(metadata['prd']['version'] == '0.2', '落盘的 PRD 版本与胜出写者不一致')
    final_events = events.read_bytes()
    _check(final_events.startswith(first_event) and
           [json.loads(line)["prd_version"] for line in final_events.splitlines()] == ["0.1", "0.2"],
           "恢复或并发提交重复追加、覆盖或遗漏 PRD 事件")
    _check(saved_analysis.read_bytes() == analysis_bytes, "生成、恢复或并发写稿覆盖了正式分析")


def main(argv: list[str] | None = None) -> int:
    """按 argv 选择真实安装或复用已有安装，返回成功 0/失败 1；参数错误由 argparse 处理。"""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--install", action="store_true", help="用 install.py 和随包 wheel 离线安装到临时项目")
    mode.add_argument("--installed-project", type=Path, help="使用已有项目安装；仅在临时工作区写入，不安装依赖")
    args = parser.parse_args(argv)
    try:
        with tempfile.TemporaryDirectory(prefix="prd-smoke-") as directory:
            temp = Path(directory).resolve()
            cwd = temp / "无关 cwd"
            cwd.mkdir()
            if args.install:
                project = temp / "安装 project"
                project.mkdir()
                # 安装包括创建 venv 和解包多个 wheel，超时预算与单次业务 CLI 分开。
                subprocess.run([sys.executable, *_PYTHON_FLAGS, str(_ROOT / "install.py"), str(project)],
                               cwd=cwd, check=True, timeout=300)
            else:
                project = args.installed_project.resolve(strict=True)
            _smoke(project, temp, cwd)
    except (AssertionError, OSError, subprocess.SubprocessError) as error:
        print(f"安装态 smoke 失败：{error}", file=sys.stderr)
        return 1
    print("安装态 smoke 通过：项目解释器、分析保存、PRD 恢复和并发写入。")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())

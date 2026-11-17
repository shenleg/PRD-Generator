"""通过真实公开 CLI 留存阶段 2 合成接收证据；故障子进程单独标识，不冒充模型交接。"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill/requirement-analyst/scripts/update_analysis.py"


def _support():
    """返回仓库测试支持模块；仅从固定仓库路径加载，文件或导入异常原样抛出。"""
    path = ROOT / "tests/prd-generator/test_gap_handoff.py"
    spec = importlib.util.spec_from_file_location("gap_handoff_cli_support", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require(condition, message):
    """condition 不满足时以 message 抛出 AssertionError；满足时无返回值。"""
    if not condition:
        raise AssertionError(message)


class EvidenceSession:
    """在新 case 目录执行公开更新接口，逐次保存真实输入、进程输出及前后文件快照。"""

    def __init__(self, directory, support):
        """创建 directory 内的隔离案例并保存 support；无返回值，已存在或文件错误直接抛出。"""
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.workspace = self.directory / "workspace"
        self.support = support
        self.requirement = support.requirement_dir(self.workspace)
        self.calls = []

    def snapshot(self, output):
        """将当前业务文件复制到新 output 并返回摘要映射；文件异常原样抛出。"""
        output.mkdir(parents=True, exist_ok=False)
        data = self.support.business_bytes(self.workspace)
        for name, content in data.items():
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return {name: self.support.PRD.digest(content) for name, content in data.items()}

    def call(self, label, patch, *, expected="pass", related=(), dry_run=False, fault=None):
        """执行 label 对应 patch，返回真实 JSON 响应，并记录全部进程证据。

        related 为显式外部分析路径，dry_run 只预检；fault 为单独 API 故障子进程模式，
        普通调用一律经过产品公开 CLI。响应/退出码不符抛出 AssertionError；进程、文件
        异常原样抛出。失败前也先保存 stdout、stderr、退出码和前后指纹，避免丢失现场。
        """
        helper = self.support
        step = self.directory / "calls" / f"{len(self.calls) + 1:02d}-{label}"
        step.mkdir(parents=True, exist_ok=False)
        patch_path = helper.PRD.write_json(step / "patch.json", patch)
        before = self.snapshot(step / "before")
        if fault:
            command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--fault-worker", fault,
                       "--workspace", str(self.workspace), "--patch", str(patch_path),
                       "--requirement-dir", str(self.requirement), "--injection-log", str(step / "injection.json")]
            interface = "public_api_fault_subprocess"
        else:
            command = [sys.executable, "-I", "-B", str(SCRIPT), "--workspace", str(self.workspace),
                       "--project", helper.PROJECT, "--patch", str(patch_path)]
            interface = "public_cli"
        for path in related:
            command.extend(["--related-analysis", str(path)])
        if dry_run:
            command.append("--dry-run")
        process = subprocess.run(command, cwd=self.directory, capture_output=True, text=True, check=False, timeout=120)
        (step / "stdout.txt").write_text(process.stdout, encoding="utf-8")
        (step / "stderr.txt").write_text(process.stderr, encoding="utf-8")
        after = self.snapshot(step / "after")
        try:
            response = json.loads(process.stdout)
        except json.JSONDecodeError:
            response = {"status": "invalid_stdout", "message": "真实 stdout 不是单个 JSON 响应，见 stdout.txt"}
        record = {"label": label, "interface": interface, "model_called": False, "command": command,
                  "returncode": process.returncode, "expected_status": expected, "response": response,
                  "fingerprints_before": before, "fingerprints_after": after,
                  "changed_files": sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))}
        helper.PRD.write_json(step / "process.json", record)
        self.calls.append({"label": label, "interface": interface, "expected_status": expected,
                           "actual_status": response.get("status"), "returncode": process.returncode,
                           "process": str((step / "process.json").relative_to(self.directory))})
        _require(response.get("status") == expected, f"{self.directory.name}/{label}: {response}")
        _require(process.returncode == {"pass": 0, "warning": 1, "fail": 2}[expected], f"{label}: 退出码 {process.returncode} 与响应不符")
        if fault:
            injection = helper.PRD.read_json(step / "injection.json")
            _require(injection["triggered"], f"{label}: 故障钩子未实际触发")
        return response

    def seed(self, refs=None):
        """经真实 CLI 首次创建分析，再安装 refs 的明确合成缺口，返回缺口对象。

        refs=None 使用本需求 FR-1，空列表保持为空；保存原始夹具快照，文件或断言错误原样抛出。
        """
        helper = self.support
        self.call("initial-old-format", helper.initial_patch())
        gaps = helper.install_gap_fixture(self.requirement, refs)
        self.snapshot(self.directory / "fixture-original")
        return gaps

    def context(self):
        """重读当前分析返回编号/修订；无参数，文件或结构错误原样抛出。"""
        return self.support.current_result(self.requirement)

    def patch(self, related_ids=None):
        """以当前修订和 related_ids 返回新接收补丁；文件或结构错误原样抛出。"""
        return self.support.handoff_patch(self.context(), related_ids)

    def analysis(self):
        """返回已保存分析；无参数，文件或 JSON 错误原样抛出。"""
        return self.support.PRD.read_json(self.requirement / "analysis/analysis-result.json")

    def gaps(self):
        """返回已保存缺口封装；无参数，文件或 JSON 错误原样抛出。"""
        return self.support.PRD.read_json(self.requirement / "prd/gap-requests.json")

    def received(self):
        """返回唯一 GAPREQ-1 问题；无参数，缺失或重复抛出 AssertionError。"""
        questions = [q for q in self.analysis()["questions"] if q.get("gap_request_ref") == "GAPREQ-1"]
        _require(len(questions) == 1, "同一缺口未对应唯一接收问题")
        return questions[0]

    def assert_ownership(self, before, gaps_before):
        """核对 before 指纹与 gaps_before 只发生授权变化；无返回值，越界抛出断言异常。"""
        helper = self.support
        after = helper.fingerprints(self.workspace)
        base = self.requirement.relative_to(self.workspace).as_posix()
        allowed = {f"{base}/analysis/analysis-result.json", f"{base}/analysis/source-manifest.json",
                   f"{base}/analysis/analysis-events.jsonl", f"{base}/prd/gap-requests.json",
                   "workspace.json", ".analysis-transaction.json"}
        changed = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
        _require(changed <= allowed, f"越界写入：{changed - allowed}")
        _require(helper.gap_status_only(gaps_before, self.gaps()), "接收修改了目标状态以外的缺口数据")


def _exercise(output, helper, sessions):
    """在 output 执行真实 CLI 案例并向 sessions 追加现场；无返回值，断言和 I/O 错误原样抛出。"""
    def case(name):
        """创建 name 案例并登记，返回会话；目录已存在或 I/O 错误原样抛出。"""
        session = EvidenceSession(output / name, helper)
        sessions.append(session)
        return session

    local = case("local-duplicate-ownership")
    original_gaps = local.seed()
    before = helper.fingerprints(local.workspace)
    preview = local.call("dry-run-full-local", local.patch([f"{helper.REQUIREMENT}/FR-1"]), dry_run=True)
    _require(not preview["written"] and before == helper.fingerprints(local.workspace), "dry-run 修改了业务文件")
    stale = local.patch([f"{helper.REQUIREMENT}/FR-1"])
    response = local.call("accept-full-local", stale)
    _require(response["written"] and response["id_map"]["$gap"] == "Q-2", "首次接收未正式保存问题")
    _require(local.received()["related_ids"] == ["FR-1"], "本需求引用未规范化")
    local.assert_ownership(before, original_gaps)
    before = helper.fingerprints(local.workspace)
    local.call("reject-stale-duplicate", stale, expected="fail")
    _require(before == helper.fingerprints(local.workspace), "旧修订被接受")
    duplicate = local.call("repeat-short-local", local.patch())
    _require(duplicate["revision"] == 2 and not duplicate["written"], "重复接收推进修订")
    _require(before == helper.fingerprints(local.workspace), "重复接收改变业务字节或事件")
    progress = helper.ANALYST.followup(local.context())
    progress["operations"] = [{"op": "update", "target": "Q-2", "changes": {"priority": "P1", "status": "answered", "answer": "CLI 实际保存的答复"}}]
    local.call("save-progress", progress)
    saved = deepcopy(local.received())
    before = helper.fingerprints(local.workspace)
    candidate = local.patch()
    candidate["operations"][0]["value"].update(priority="P2", status="dropped", answer="不得覆盖", question="候选新措辞")
    local.call("repeat-preserve-progress", candidate)
    _require(local.received() == saved and before == helper.fingerprints(local.workspace), "重复候选覆盖了进度")
    move = helper.ANALYST.followup(local.context())
    move["operations"] = [{"op": "update", "target": "Q-2", "changes": {"gap_request_ref": "GAPREQ-2"}}]
    local.call("reject-reference-transfer", move, expected="fail")
    _require(before == helper.fingerprints(local.workspace), "update 转移了接收引用")
    old = helper.ANALYST.followup(local.context())
    old["operations"] = [{"op": "update", "target": "Q-1", "changes": {"status": "answered", "answer": "旧问题仍可正常更新"}}]
    local.call("update-old-question", old)
    _require("gap_request_ref" not in local.analysis()["questions"][0], "旧问题被强制添加接收引用")
    closed = local.gaps()
    closed["requests"][0].update(status="closed", resolution={"kind": "supplied", "analysis_refs": [f"{helper.REQUIREMENT}/FR-1"], "reason": "合成生成侧依据，不是真实关闭链路"})
    helper.PRD.write_json(local.requirement / "prd/gap-requests.json", closed)
    before = helper.fingerprints(local.workspace)
    local.call("repeat-closed", local.patch())
    _require(before == helper.fingerprints(local.workspace), "closed 缺口被重开或改写")

    cross = case("cross-explicit-analysis")
    refs = [f"{helper.REQUIREMENT}/FR-1", "EXTERNAL/FR-1"]
    gaps = cross.seed(refs)
    cross.call("initial-external", helper.initial_patch("EXTERNAL"))
    external = helper.requirement_dir(cross.workspace, "EXTERNAL") / "analysis/analysis-result.json"
    before = helper.fingerprints(cross.workspace)
    cross.call("reject-implicit-workspace-scan", cross.patch(refs), expected="fail")
    _require(before == helper.fingerprints(cross.workspace), "未显式外部资料时仍发生写入")
    cross.call("accept-explicit-external", cross.patch(refs), related=[external])
    _require(cross.received()["related_ids"] == ["FR-1", "EXTERNAL/FR-1"], "跨需求引用未保留完整格式")
    cross.assert_ownership(before, gaps)

    empty = case("empty-refs")
    gaps = empty.seed([])
    before = helper.fingerprints(empty.workspace)
    empty.call("accept-empty", empty.patch([]))
    _require(empty.received()["related_ids"] == [], "空引用被臆造关联")
    empty.assert_ownership(before, gaps)

    invalid_inputs = [
        ("malformed-full-ref", ["FR-1"], ["FR-1"]),
        ("unknown-analysis-item", [f"{helper.REQUIREMENT}/FR-999"], [f"{helper.REQUIREMENT}/FR-999"]),
        ("candidate-omits-ref", [f"{helper.REQUIREMENT}/FR-1"], []),
        ("candidate-substitutes-ref", [f"{helper.REQUIREMENT}/FR-1"], ["GOAL-1"]),
        ("candidate-extra-ref", [f"{helper.REQUIREMENT}/FR-1"], ["FR-1", "GOAL-1"]),
        ("candidate-reorders-ref", [f"{helper.REQUIREMENT}/FR-1", f"{helper.REQUIREMENT}/GOAL-1"], ["GOAL-1", "FR-1"]),
    ]
    for name, gap_refs, candidate_refs in invalid_inputs:
        session = case(name)
        session.seed(gap_refs)
        before = helper.fingerprints(session.workspace)
        response = session.call("reject-invalid", session.patch(candidate_refs), expected="fail")
        _require(not response["written"] and before == helper.fingerprints(session.workspace), f"{name}: 无效输入发生写入")

    save = case("analysis-save-failure-recovery")
    original = save.seed()
    patch = save.patch()
    response = save.call("interrupt-analysis-replace", patch, expected="fail", fault="analysis-save")
    _require(not response["written"] and save.gaps() == original, "保存失败提前标记了缺口")
    _require(len(save.analysis()["questions"]) == 1, "替换故障未阻止新分析保存")
    _require(helper.PRD.read_json(save.workspace / ".analysis-transaction.json") is not None, "未保留待恢复事务")
    save.call("recover-pending-via-dry-run", patch, expected="fail", dry_run=True)
    _require(save.context()["revision"] == 2 and save.received()["id"] == "Q-2", "原 journal 未恢复接收问题")
    _require(save.gaps() == original, "dry-run 恢复越过分析事务标记了缺口")
    _require(helper.PRD.read_json(save.workspace / ".analysis-transaction.json") is None, "恢复后 journal 未清空")
    analysis_before = helper.business_bytes(save.requirement / "analysis")
    response = save.call("reread-and-finish-marker", save.patch())
    _require(response["revision"] == 2 and not response["written"], "恢复补标记不应再保存分析")
    _require(analysis_before == helper.business_bytes(save.requirement / "analysis"), "恢复重试追加事件或覆盖分析")
    _require(helper.gap_status_only(original, save.gaps()), "恢复标记改变了其他缺口内容")

    marker = case("gap-marker-failure-retry")
    original = marker.seed()
    response = marker.call("interrupt-marker-replace", marker.patch(), expected="fail", fault="gap-mark")
    _require(response["written"] and response["revision"] == 2, "标记失败未报告已保存的分析修订")
    _require(marker.gaps() == original and marker.received()["id"] == "Q-2", "中断保存顺序不正确")
    progress = helper.ANALYST.followup(marker.context())
    progress["operations"] = [{"op": "update", "target": "Q-2", "changes": {"priority": "P1", "status": "answered", "answer": "中断后继续处理的答复"}}]
    marker.call("save-progress-before-retry", progress)
    saved = deepcopy(marker.received())
    analysis_before = helper.business_bytes(marker.requirement / "analysis")
    candidate = marker.patch()
    candidate["operations"][0]["value"].update(priority="P2", status="dropped", answer="候选答复不得覆盖")
    response = marker.call("reread-retry-marker-only", candidate)
    _require(response["revision"] == 3 and not response["written"], "补标记推进了分析修订")
    _require(saved == marker.received() and analysis_before == helper.business_bytes(marker.requirement / "analysis"), "补标记破坏了处理进度或重复追加事件")
    _require(helper.gap_status_only(original, marker.gaps()), "补标记修改了缺口状态以外的内容")

    concurrent = case("concurrent-gap-rewrite")
    concurrent.seed()
    response = concurrent.call("rewrite-gap-after-analysis-save", concurrent.patch(), expected="fail", fault="concurrent-gap")
    _require(response["written"] and response["revision"] == 2, "并发拒绝未报告已保存分析")
    injection_path = concurrent.directory / concurrent.calls[-1]["process"]
    injection = helper.PRD.read_json(injection_path.with_name("injection.json"))
    actual_gap = (concurrent.requirement / "prd/gap-requests.json").read_bytes()
    _require(helper.PRD.digest(actual_gap) == injection["concurrent_gap_sha256"], "覆盖了并发生成侧写入")
    generated = concurrent.gaps()
    _require(generated["requests"][0]["status"] == "open" and generated["requests"][-1]["id"] == "GAPREQ-3", "并发新增缺口或原状态丢失")
    analysis_before = helper.business_bytes(concurrent.requirement / "analysis")
    concurrent.call("reread-new-gap-and-retry", concurrent.patch())
    _require(helper.gap_status_only(generated, concurrent.gaps()), "重读重试未保留并发内容")
    _require(analysis_before == helper.business_bytes(concurrent.requirement / "analysis"), "并发后重试重复保存分析")

    whitespace = case("concurrent-gap-byte-only-change")
    original = whitespace.seed()
    response = whitespace.call("rewrite-only-gap-whitespace", whitespace.patch(), expected="fail", fault="concurrent-gap-bytes")
    _require(response["written"] and response["revision"] == 2, "字节冲突未报告已保存分析")
    injection_path = whitespace.directory / whitespace.calls[-1]["process"]
    injection = helper.PRD.read_json(injection_path.with_name("injection.json"))
    actual_gap = (whitespace.requirement / "prd/gap-requests.json").read_bytes()
    _require(whitespace.gaps() == original, "空白故障注入意外改变了业务语义")
    _require(helper.PRD.digest(actual_gap) == injection["concurrent_gap_sha256"], "只比较JSON语义而覆盖了并发字节")
    analysis_before = helper.business_bytes(whitespace.requirement / "analysis")
    whitespace.call("reread-byte-only-change-and-retry", whitespace.patch())
    _require(helper.gap_status_only(original, whitespace.gaps()), "字节冲突重试未仅补标记")
    _require(analysis_before == helper.business_bytes(whitespace.requirement / "analysis"), "字节冲突后重试重复保存分析")


def run(output):
    """在不存在的 output 执行留证并返回清单；新目录之外不写业务文件。

    既有目录抛出 FileExistsError，绝不清空或覆盖。产品响应与证据断言失败写入 fail 清单，
    保留全部现场；文件、参数或子进程超时异常亦记录为 fail，不伪称测试或模型行为通过。
    """
    output = Path(output).expanduser().absolute()
    output.mkdir(parents=True, exist_ok=False)
    helper = _support()
    sessions = []
    error = None
    try:
        _exercise(output, helper, sessions)
    except (AssertionError, OSError, ValueError, subprocess.TimeoutExpired) as failure:
        error = f"{type(failure).__name__}: {failure}"
    calls = [call for session in sessions for call in session.calls]
    sources = [p for parent in (ROOT / "skill/requirement-analyst", ROOT / "tests/prd-generator")
               for p in sorted(parent.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
    sources.extend([ROOT / "tests/requirement-analyst/test_update_analysis.py", ROOT / "tests/requirements.txt"])
    source_fingerprints = {}
    for source in sources:
        relative = source.relative_to(ROOT)
        raw = source.read_bytes()
        snapshot = output / "source-snapshot" / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(raw)
        source_fingerprints[relative.as_posix()] = helper.PRD.digest(raw)
    manifest = {"executed_at": datetime.now(timezone.utc).isoformat(), "status": "fail" if error else "pass",
                "scope": "PG-29 合成缺口的脚本/API 协议证据；不是模型自主交接，也不是正式生成器联调或发布",
                "model_called": False, "formal_generator_called": False, "release_executed": False,
                "output": str(output), "cli_calls": sum(c["interface"] == "public_cli" for c in calls),
                "fault_api_calls": sum(c["interface"] == "public_api_fault_subprocess" for c in calls),
                "cases": [{"name": s.directory.name, "workspace": str(s.workspace.relative_to(output)), "calls": s.calls} for s in sessions],
                "source_snapshot": "source-snapshot",
                "source_fingerprints": source_fingerprints}
    if error:
        manifest["error"] = error
    helper.PRD.write_json(output / "run-manifest.json", manifest)
    return manifest


def fault_worker(args):
    """按 args 在独立子进程加载公开 API 注入真实 I/O 故障，返回对应退出码。

    args 包含工作区、补丁、故障类型、目标需求和注入日志路径；打印真实 API JSON，
    注入状态保存到业务目录外。文件或内部程序异常原样抛出，不把故障脚本称为模型。
    """
    helper = _support()
    updater = helper.load_updater()
    patch = helper.PRD.read_json(args.patch)
    with helper.inject_io_fault(updater, args.fault_worker, args.requirement_dir) as state:
        try:
            response = updater.update_analysis(args.workspace, helper.PROJECT, patch,
                                               related_analyses=args.related_analysis, dry_run=args.dry_run)
        finally:
            log = {name: value for name, value in state.items() if name != "concurrent_gap_bytes"}
            if "concurrent_gap_bytes" in state:
                log["concurrent_gap_sha256"] = helper.PRD.digest(state["concurrent_gap_bytes"])
            helper.PRD.write_json(args.injection_log, log)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return {"pass": 0, "warning": 1, "fail": 2}[response["status"]]


def main(argv=None):
    """解析 argv 执行留证或单独故障 worker，打印摘要并返回 pass=0/fail=2。

    默认输出使用带时间和随机后缀的新目录；显式既有目录返回 2，不覆盖证据。
    参数错误由 argparse 报告；安装错误及未预期程序异常原样抛出。
    """
    parser = argparse.ArgumentParser(description="留存阶段2真实CLI接收协议证据；合成输入，不调用模型")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fault-worker", choices=["analysis-save", "gap-mark", "concurrent-gap", "concurrent-gap-bytes"], help=argparse.SUPPRESS)
    parser.add_argument("--workspace", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--patch", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--requirement-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--injection-log", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--related-analysis", action="append", default=[], type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.fault_worker:
        if not all((args.workspace, args.patch, args.requirement_dir, args.injection_log)):
            parser.error("故障 worker 必须提供 workspace、patch、requirement-dir 和 injection-log")
        return fault_worker(args)
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output = args.output or ROOT / "workspace-sandbox/prd-generator" / f"stage-2-cli-{suffix}"
    try:
        result = run(output)
    except FileExistsError:
        print(json.dumps({"status": "fail", "message": "输出目录已存在，拒绝覆盖", "output": str(output)}, ensure_ascii=False))
        return 2
    print(json.dumps({name: result[name] for name in ("status", "output", "cli_calls", "fault_api_calls")}, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())

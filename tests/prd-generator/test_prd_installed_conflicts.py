"""从独立目录验证双 Skill 安装态 CLI：缺口回交与文件归属（PG-27）、交错写入（PG-28）。"""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from prd_fixture_support import block, read_json, write_json
from prd_sync_support import mapping_patch, replace_section, row, section_text
from run_prd_generation import make_input
from test_gap_handoff import ANALYST, business_bytes, current_result, gap_status_only, handoff_patch


SKILL_SOURCE = Path(__file__).resolve().parents[2] / "skill"
PROJECT = "synthetic"
REQUIREMENT = "SYNTHETIC-PRD"
ANALYSIS = "analysis/analysis-result.json"
BODY = "prd/prd.md"
EVENTS = "prd/prd-events.jsonl"
GAPS = "prd/gap-requests.json"

# 在公开 CLI 子进程只使最后的缺口替换失败，留下真实可恢复的标记；不阻塞分析提交锁。
GAP_REPLACE_FAULT = """
import os
from pathlib import Path
import runpy
import sys

_, target, script, *args = sys.argv
real_replace = os.replace

def replace(source, destination, *args, **kwargs):
    \"\"\"仅对已安装 CLI 的目标缺口抛出 OSError；其余替换原样返回。\"\"\"
    if Path(destination) == Path(target):
        raise OSError('PG-28: injected gap replace failure')
    return real_replace(source, destination, *args, **kwargs)

os.replace = replace
sys.argv = [script, *args]
runpy.run_path(script, run_name='__main__')
"""


class InstalledConflictTests(unittest.TestCase):
    """通过已安装的写入入口覆盖 PG-28；所有赢家状态均由正式命令写入。"""

    def setUp(self):
        """安装两个完整生产 Skill 并准备 r1 合成输入；文件或安装异常使测试失败。"""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.cwd = self.base / "unrelated"
        self.cwd.mkdir()
        project = self.base / "installed-project"
        self.skills = project / ".claude/skills"
        for skill in ("prd-generator", "requirement-analyst"):
            shutil.copytree(SKILL_SOURCE / skill, self.skills / skill,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.workspace = project / "workspace"
        self.root = self.workspace / "projects" / PROJECT / "requirements" / REQUIREMENT
        _, body = make_input(self.base, missing=True)
        self.initial_body = replace_section(body, "appendix", "合成测试输入，仅用于并发验证。")
        initial = ANALYST.initial(REQUIREMENT)
        initial["operations"] = [{"op": "add", "collection": "requirements.functional_requirements", "ref": "$query",
                                  "value": ANALYST.common("合成查询功能，不代表真实业务", tag="confirmed")}]
        initial["set"].update({"meta.analysis_status": "completed", "meta.readiness": "ready_for_document"})
        initial["completion_checks"] = [{"item": i, "satisfied": True, "question_refs": [], "reason": "合成并发输入"}
                                        for i in range(1, 12)]
        saved = self.analyst("first-analysis", initial)
        self.assertEqual(saved["status"], "pass", saved)
        self.assertTrue(saved["written"], saved)
        self.assertEqual(saved["revision"], 1)
        self.assertEqual(saved["id_map"]["$query"], "FR-1")

    def cli(self, skill, script, args, *, fail_gap_replace=False):
        """从无关目录调用 skill 的绝对 script 路径和 args；可仅注入缺口替换故障。

        返回真实 CLI JSON；退出码、超时或解析异常使测试失败。
        """
        installed = self.skills / skill / "scripts" / script
        bootstrap = ["-c", GAP_REPLACE_FAULT, str(self.root / GAPS)] if fail_gap_replace else []
        process = subprocess.run([sys.executable, "-I", "-B", *bootstrap, str(installed), *map(str, args)],
                                 cwd=self.cwd, capture_output=True, text=True, timeout=30)
        self.assertIn(process.returncode, (0, 1, 2), f"{process.stdout}\n{process.stderr}")
        self.assertTrue(process.stdout, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(process.returncode, {"pass": 0, "warning": 1, "fail": 2}[result["status"]], result)
        return result

    def analyst(self, name, patch, *, fail_gap_replace=False):
        """提交名为 name 的 patch，返回分析 CLI 响应；可注入缺口替换故障，其他异常使测试失败。"""
        path = write_json(self.base / f"{name}.json", patch)
        return self.cli("requirement-analyst", "update_analysis.py",
                        ["--workspace", self.workspace, "--project", PROJECT, "--patch", path],
                        fail_gap_replace=fail_gap_replace)

    def candidate(self, name, *, initial=False, sync=False, body=None, gaps=None, additions=()):
        """用当前磁盘版本组装 name 候选并返回 CLI 参数；initial 走首稿，sync 指向定向同步。

        body 可覆盖默认正文，gaps 为可选的显式缺口快照，additions 为同步新增映射；读取或格式错误使测试失败。
        """
        mapping = {"mapping_key": "synthetic-query", "kind": "functional_requirement",
                   "analysis_refs": [f"{REQUIREMENT}/FR-1"]}
        if initial:
            patch = {"patch_version": "1.0", "requirement_id": REQUIREMENT, "base_prd_version": None,
                     "base_analysis_revision": current_result(self.root)["revision"], "items": [mapping]}
        else:
            patch = mapping_patch(self.root, additions if sync else (mapping,))
        if body is None:
            body = self.initial_body if initial else (self.root / BODY).read_text(encoding="utf-8")
        patch_path = write_json(self.base / f"{name}.json", patch)
        body_path = self.base / f"{name}.md"
        body_path.write_text(body, encoding="utf-8")
        args = [self.root, "--patch", patch_path, "--body", body_path,
                "--candidate-dir", self.base / f"{name}-candidate"]
        if sync:
            args.append("--sync")
        if gaps is not None:
            args += ["--gaps", write_json(self.base / f"{name}-gaps.json", gaps)]
        return args

    def save(self, args, *, version=None, conflict=None):
        """用 args 调用 PRD CLI；验证 version 实际提交或 conflict 拒写，返回响应；异常使测试失败。"""
        result = self.cli("prd-generator", "write_draft.py", args)
        if conflict:
            self.assertEqual(result["status"], "fail", result)
            self.assertFalse(result["generated"], result)
            self.assertEqual(result["written"], [], result)
            self.assertTrue(any(conflict in item["message"] for item in result["diagnostics"]), result)
        else:
            self.assertIn(result["status"], ("pass", "warning"), result)
            self.assertTrue(result["generated"], result)
            self.assertIn(EVENTS, result["written"], result)
            self.assertEqual(result["version"], version, result)
            self.assertEqual(read_json(self.root / "requirement.json")["prd"]["version"], version)
        return result

    def events(self):
        """从正式 PRD 日志读取事件；返回解析后的列表，读取和 JSON 错误原样抛出。"""
        return [json.loads(line) for line in (self.root / EVENTS).read_text(encoding="utf-8").splitlines()]

    def test_stale_analysis_revision_requires_rereading(self):
        """分析员提交 r2 后拒绝 r1 首稿，重读 r2 正式生成且包含新增内容。"""
        stale = self.candidate("stale-r1", initial=True)
        r1 = read_json(self.root / ANALYSIS)
        question = "是否要单独展示合成查询的空结果？"
        patch = ANALYST.followup(current_result(self.root))
        patch["completion_checks"] = r1["completion_checks"]
        addition = ANALYST.initial()["operations"][1]
        addition["value"].update(question=question, priority="P3", related_ids=["FR-1"])
        patch["operations"] = [addition]
        winner = self.analyst("ordinary-supplement", patch)
        self.assertEqual(winner["status"], "pass", winner)
        self.assertTrue(winner["written"], winner)
        self.assertEqual(winner["revision"], 2)
        winner_bytes = business_bytes(self.workspace)

        self.save(stale, conflict="读取时版本或分析修订冲突")
        self.assertEqual(business_bytes(self.workspace), winner_bytes)

        r2 = read_json(self.root / ANALYSIS)
        self.assertEqual(r2["meta"]["analysis_revision"], 2)
        saved_question, = r2["questions"]
        self.assertEqual(saved_question["question"], question)
        body = replace_section(self.initial_body, "residuals", saved_question["question"])
        self.save(self.candidate("fresh-r2", initial=True, body=body), version="0.1")
        self.assertIn(question, (self.root / BODY).read_text(encoding="utf-8"))
        self.assertEqual([event["based_on_analysis_revision"] for event in self.events()], [2])
        self.assertEqual((self.root / ANALYSIS).read_bytes(), winner_bytes[str((self.root / ANALYSIS).relative_to(self.workspace))])

    def test_stale_prd_version_requires_rereading(self):
        """两个作者读取 0.1：B 正式提交 0.2，A 的旧稿拒写，重读后才能提交 0.3。"""
        self.save(self.candidate("first", initial=True), version="0.1")
        stale = self.candidate("writer-a")
        self.save(self.candidate("writer-b"), version="0.2")
        winner_bytes = business_bytes(self.workspace)
        winner_events = self.events()
        self.assertEqual([event["prd_version"] for event in winner_events], ["0.1", "0.2"])

        self.save(stale, conflict="读取时版本或分析修订冲突")
        self.assertEqual(business_bytes(self.workspace), winner_bytes)

        self.save(self.candidate("writer-a-reread"), version="0.3")
        self.assertEqual(self.events()[:2], winner_events)
        self.assertEqual([event["prd_version"] for event in self.events()], ["0.1", "0.2", "0.3"])

    def generate_gap(self):
        """通过已安装生成 CLI 正式保存带验收缺口的首稿；失败使测试失败。"""
        gaps = {"schema_version": "1.0", "requirement_id": REQUIREMENT, "counters": {"GAPREQ": 1},
                "requests": [{"id": "GAPREQ-1", "needed_for": "acceptance_criteria", "description": "查询验收信息待补",
                              "related_analysis_refs": [f"{REQUIREMENT}/FR-1"], "raised_in": "0.1", "status": "open"}]}
        body = replace_section(self.initial_body, "acceptance_criteria",
                               block("gap", "GAPREQ-1", "待分析补充：查询验收信息"))
        self.save(self.candidate("initial-gap", initial=True, body=body, gaps=gaps), version="0.1")

    def test_installed_generator_and_sync_preserve_all_analysis_files(self):
        """PG-27 程序链：正式登记、分析接收和实际补足、生成核实关闭，分段比较文件归属。"""
        analysis_dir = self.root / "analysis"
        common = read_json(self.root / "requirement.json")["common"]
        before_generation = business_bytes(analysis_dir)
        self.generate_gap()
        self.assertEqual(business_bytes(analysis_dir), before_generation)
        self.assertEqual(read_json(self.root / "requirement.json")["common"], common)
        before_handoff = business_bytes(self.root / "prd")
        gap_path = self.root / GAPS
        registered_gaps = read_json(gap_path)
        receive = handoff_patch(current_result(self.root))
        receive["operations"][0]["value"]["priority"] = "P3"
        receive["completion_checks"] = read_json(self.root / ANALYSIS)["completion_checks"]
        received = self.analyst("receive", receive)
        self.assertTrue(received["written"] and received["gap_status_written"], received)
        self.assertTrue(gap_status_only(registered_gaps, read_json(gap_path), ("GAPREQ-1",)))
        self.assertEqual(business_bytes(self.root / "prd"), {**before_handoff, "gap-requests.json": gap_path.read_bytes()})
        handed_over = business_bytes(self.root / "prd")
        receiver = received["id_map"]["$gap"]
        answer = "查询无匹配记录时显示‘未找到匹配记录’。"
        supplement = ANALYST.followup(received)
        supplement.update(actor="user", user_statement=answer, completion_checks=receive["completion_checks"], operations=[
            {"op": "update", "target": receiver, "changes": {"status": "answered", "answer": answer}},
            {"op": "add", "collection": "requirements.acceptance_criteria", "ref": "$acceptance",
             "value": ANALYST.common(answer, tag="confirmed", refs=["FR-1"])},
        ])
        supplied = self.analyst("answer-and-supply", supplement)
        self.assertTrue(supplied["written"], supplied)
        self.assertEqual(supplied["revision"], 3)
        self.assertEqual(business_bytes(self.root / "prd"), handed_over)
        before_sync = business_bytes(analysis_dir)
        base = (self.root / BODY).read_text(encoding="utf-8")
        basis = f'{REQUIREMENT}/{supplied["id_map"]["$acceptance"]}'
        gaps = read_json(gap_path)
        gaps["requests"][0].update(status="closed", resolution={"kind": "supplied", "analysis_refs": [basis], "reason": "答案已落实为有效验收条件"})
        body = replace_section(base, "acceptance_criteria", row("PRD-AC-001", answer, basis))
        body = replace_section(body, "residuals", "无适用遗留项")
        self.save(self.candidate("sync-close", sync=True, body=body, gaps=gaps,
                                additions=[{"mapping_key": "empty-result", "kind": "acceptance_criterion", "analysis_refs": [basis]}]), version="0.2")
        self.assertEqual(business_bytes(analysis_dir), before_sync)
        self.assertEqual(read_json(self.root / "requirement.json")["common"], common)
        final_body = (self.root / BODY).read_text(encoding="utf-8")
        self.assertEqual(section_text(final_body, "functional_requirements"), section_text(base, "functional_requirements"))
        self.assertNotIn("待分析补充", final_body)
        self.assertEqual(read_json(gap_path)["requests"][0]["status"], "closed")
        trace = read_json(self.root / "prd/prd-trace.json")
        self.assertEqual({item["prd_id"]: item["analysis_refs"] for item in trace["items"]},
                         {"PRD-FR-001": [f"{REQUIREMENT}/FR-1"], "PRD-AC-001": [basis]})

    def test_stale_gap_candidate_requires_rereading_after_handoff(self):
        """分析员重试只补交接标记；同修订、同 PRD 版本的旧缺口候选仍拒写。"""
        gap_id = "GAPREQ-1"
        gap_path = self.root / GAPS
        self.generate_gap()
        self.assertIn("gap_request", [event["change_type"] for event in self.events()])
        self.assertEqual(read_json(gap_path)["requests"][0]["status"], "open")
        initial_gap_bytes = gap_path.read_bytes()

        patch = handoff_patch(current_result(self.root), gap_id=gap_id)
        patch["operations"][0]["value"]["priority"] = "P3"
        patch["completion_checks"] = read_json(self.root / ANALYSIS)["completion_checks"]
        partial = self.analyst("handoff-interrupted", patch, fail_gap_replace=True)
        self.assertEqual(partial["status"], "fail", partial)
        self.assertTrue(partial["written"], partial)
        self.assertFalse(partial["gap_status_written"], partial)
        self.assertEqual(partial["revision"], 2, partial)
        self.assertTrue(any("PG-28: injected gap replace failure" in item["message"]
                            for item in partial["diagnostics"]), partial)
        question, = read_json(self.root / ANALYSIS)["questions"]
        self.assertEqual(question["gap_request_ref"], gap_id)
        self.assertEqual(gap_path.read_bytes(), initial_gap_bytes)

        # 候选在 r2 已落盘、标记尚未补写时读取；之后只让正式重试改变缺口字节。
        open_gaps = read_json(gap_path)
        stale = self.candidate("before-gap-mark", sync=True, gaps=open_gaps)
        before_marker = business_bytes(self.workspace)
        retry = handoff_patch(current_result(self.root), gap_id=gap_id)
        retry["completion_checks"] = read_json(self.root / ANALYSIS)["completion_checks"]
        winner = self.analyst("handoff-marker-retry", retry)
        self.assertEqual(winner["status"], "pass", winner)
        self.assertFalse(winner["written"], winner)
        self.assertTrue(winner["gap_status_written"], winner)
        self.assertEqual(winner["revision"], 2, winner)
        marked = read_json(gap_path)
        self.assertTrue(gap_status_only(open_gaps, marked, (gap_id,)), marked)
        winner_bytes = business_bytes(self.workspace)
        gap_key = str(gap_path.relative_to(self.workspace))
        self.assertEqual(winner_bytes, {**before_marker, gap_key: gap_path.read_bytes()})

        self.save(stale, conflict=f"不得删除、重置缺口或代替分析侧标记接收：{gap_id}")
        self.assertEqual(business_bytes(self.workspace), winner_bytes)

        fresh = self.candidate("after-gap-mark", sync=True, gaps=read_json(gap_path))
        self.save(fresh, version="0.2")
        event = self.events()[-1]
        self.assertEqual(event["change_type"], "sync")
        self.assertEqual(event["prd_version"], "0.2")
        self.assertEqual(event["based_on_analysis_revision"], 2)
        self.assertEqual(gap_path.read_bytes(), winner_bytes[gap_key])
        self.assertEqual(read_json(self.root / ANALYSIS)["questions"], [question])

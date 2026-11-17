"""验证保存的阶段 2 模型试跑产物；不调用模型，不以静态文档存在冒充行为通过。"""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
RUN_BASE = ROOT / "workspace-sandbox/stage-2"
RUN_MANIFEST = json.loads((RUN_BASE / "run-manifest.json").read_text(encoding="utf-8"))
RUNS = RUN_BASE / f"attempt-{RUN_MANIFEST['attempt']:02d}"
SPEC = importlib.util.spec_from_file_location("stage_2_validator", ROOT / "skill/requirement-analyst/scripts/validate_analysis.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
GROUPS = ("high-low-voltage", "task-management", "probes/idea")
TEXT_PROBES = ("backend", "defect", "notification", "notification-with-reason")
SECTIONS = ("理解摘要", "已确认事项", "业务价值分析", "缺口与矛盾", "待回答问题", "暂定假设", "研发确认项", "边界与异常", "验收条件", "历史需求关联", "技术可行性及风险", "用户体验和设计建议", "结论与就绪度")


def load(path: Path):
    """读取 path 的 JSON 值；文件和格式错误直接抛出，不静默跳过未运行的场景。"""
    return json.loads(path.read_text(encoding="utf-8"))


def documents(directory: Path) -> dict:
    """返回 directory 下按需求编号索引的正式结果及来源；缺文件或错误 JSON 直接抛出。"""
    return {
        result["requirement_id"]: (result, load(path.with_name("source-manifest.json")), path)
        for path in sorted(directory.glob("requirements/*/analysis/analysis-result.json"))
        for result in (load(path),)
    }


def asked_questions(directory: Path, turn: int = 1) -> list[dict]:
    """按 turn 的实际提问引用查找问题，返回问题列表；悬空引用或记录缺失直接报错。"""
    transcript = load(directory / f"turn-{turn:02d}.json")
    docs = documents(directory)
    questions = []
    for reference in transcript["asked_question_refs"]:
        requirement_id, question_id = reference.split("/", 1)
        questions.append(next(q for q in docs[requirement_id][0]["questions"] if q["id"] == question_id))
    return questions


class SavedModelRunTests(unittest.TestCase):
    """对真实保存的模型输出执行结构、引用、状态和可观测行为检查。"""

    def test_saved_runs_match_stage_two_tag_and_inputs(self) -> None:
        """历史证据绑定 stage-2-complete；当前补丁机制另由阶段 3 实跑回归验证。"""
        manifest = load(RUN_BASE / "run-manifest.json")
        self.assertEqual(manifest["stage"], 2)
        self.assertGreaterEqual(len(manifest["files"]), 18)
        rechecks = {entry["file"]: entry for entry in manifest.get("scoped_rechecks", [])}
        for relative, expected_hash in manifest["files"].items():
            with self.subTest(file=relative):
                current = subprocess.run(
                    ["git", "show", f"stage-2-complete:{relative}"], cwd=ROOT,
                    check=True, capture_output=True,
                ).stdout
                actual_hash = hashlib.sha256(current).hexdigest()
                if actual_hash == expected_hash:
                    continue
                recheck = rechecks[relative]
                self.assertEqual(recheck["before_sha256"], expected_hash)
                self.assertEqual(recheck["after_sha256"], actual_hash)
                text = current.decode("utf-8")
                self.assertEqual(text.count(recheck["added_text"]), 1)
                original = text.replace(recheck["added_text"], "", 1).encode("utf-8")
                self.assertEqual(hashlib.sha256(original).hexdigest(), expected_hash)
                self.assertEqual(recheck["affected_requirement"], "REQ-2026-005")
                response = load(ROOT / recheck["actual_response"])
                self.assertEqual(response["user_input_source"], "内部完整性复核；无新用户输入")
                self.assertEqual(response["asked_question_refs"], [])
                self.assertEqual(response["control_questions"], [])
                self.assertEqual(load(ROOT / recheck["actual_validation"])["status"], "pass")

    def test_all_runs_have_valid_results_and_reports(self) -> None:
        """全部预定试跑必须实际存在，每个正式结果通过统一校验且报告有 13 章。"""
        for group in GROUPS:
            with self.subTest(group=group):
                docs = documents(RUNS / group)
                self.assertTrue(docs, f"尚无实际运行产物：{group}")
                for requirement_id, (analysis, manifest, path) in docs.items():
                    related = [(a, m) for key, (a, m, _) in docs.items() if key != requirement_id]
                    result = VALIDATOR.validate_analysis(analysis, manifest, related_analyses=related)
                    self.assertEqual(result, {"status": "pass", "diagnostics": []}, (path, result))
                    report = path.with_name("analysis-report.md").read_text(encoding="utf-8")
                    for section in SECTIONS:
                        self.assertIn(section, report, path)
                    self.assertTrue(analysis["ux_assessment"]["ui_dependent"] in (True, False))
                    technical = analysis.get("technical_feasibility")
                    if technical is not None:
                        self.assertEqual(technical["conclusion"], "unknown")

    def test_each_recorded_question_was_concrete_and_prioritized(self) -> None:
        """记录与实际问题对应，每轮不超过三个业务问题，不问 P2 或 P3。"""
        for group in GROUPS:
            directory = RUNS / group
            turns = sorted(directory.glob("turn-*.json"))
            self.assertTrue(turns, f"尚无对话记录：{group}")
            for path in turns:
                with self.subTest(group=group, turn=path.name):
                    record = load(path)
                    self.assertIsInstance(record["assistant_message"], str)
                    self.assertTrue(record["assistant_message"].strip())
                    self.assertLessEqual(len(record["asked_question_refs"]), 3)
                    docs = documents(directory)
                    for reference in record["asked_question_refs"]:
                        requirement_id, question_id = reference.split("/", 1)
                        question = next(q for q in docs[requirement_id][0]["questions"] if q["id"] == question_id)
                        self.assertIn(question["priority"], ("P0", "P1"))
                        self.assertGreaterEqual(len(question["options"]), 4)
                        self.assertLessEqual(len(question["options"]), 6)
                        self.assertTrue(any("其他" in option for option in question["options"]))
                        self.assertTrue(any("不确定" in option for option in question["options"]))
                        self.assertTrue(question["recommendation"].strip())

    def test_second_sample_is_split_and_initial_conflicts_are_open(self) -> None:
        """第二样例真实拆成五个需求，初始矛盾未被预设回答提前解决。"""
        directory = RUNS / "task-management/snapshots/turn-01"
        docs = documents(directory)
        self.assertEqual(len(docs), 5)
        conflicts = [(analysis, conflict) for analysis, _, _ in docs.values() for conflict in analysis["business_assessment"]["conflicts"]]
        self.assertGreaterEqual(len(conflicts), 2)
        for analysis, conflict in conflicts:
            question = next(q for q in analysis["questions"] if q["id"] == conflict["related_question"])
            self.assertEqual(question["status"], "open")
            self.assertEqual(question["priority"], "P0")
            self.assertEqual(analysis["meta"]["readiness"], "not_ready")
        record = load(RUNS / "task-management/turn-01.json")
        self.assertEqual(len(record["asked_question_refs"]), 3)

    def test_first_sample_records_conditional_scale_growth(self) -> None:
        """实际漏项回归：不因原文没有性能指标而跳过组合规模增长边界。"""
        docs = documents(RUNS / "high-low-voltage")
        self.assertEqual(len(docs), 1)
        analysis = next(iter(docs.values()))[0]
        boundaries = analysis["business_assessment"]["boundaries"]
        matches = [b for b in boundaries if re.search(r"规模|数量", b["content"]) and re.search(r"增长|增加|扩大|爆炸", b["content"])]
        self.assertTrue(matches, "首轮曾只说没有规模指标，却未登记条件性组合增长边界。")
        self.assertTrue(all(b["tag"] == "inferred" for b in matches))

    def test_second_sample_prioritizes_operational_rules(self) -> None:
        """实际偏离回归：术语登记不挤掉权限、旧删除规则和导出上限三个操作决策。"""
        questions = asked_questions(RUNS / "task-management/snapshots/turn-01")
        self.assertEqual(len(questions), 3)
        for pattern in (r"权限|角色|允许.*(?:用户|人|创建者)|谁.*删|哪些.*(?:用户|删)", r"旧.*规则|之前.*逻辑|删除.*规则|运行中", r"1000|上限|超.*条|导出.*数量"):
            with self.subTest(pattern=pattern):
                self.assertTrue(any(re.search(pattern, question["question"]) for question in questions), questions)

    def test_export_records_lifecycle_access_and_waiting_boundaries(self) -> None:
        """人工发现漏项的回归：导出不能只有数量和字段，还应检查生命周期、权限及等待失败。"""
        docs = documents(RUNS / "task-management")
        analysis = docs["REQ-2026-005"][0]
        candidates = analysis["business_assessment"]["boundaries"] + analysis["business_assessment"]["exceptions"]
        for pattern in (r"未完成|运行中|完成前", r"权限|授权|访问范围", r"超时|等待|耗时"):
            with self.subTest(pattern=pattern):
                matches = [item for item in candidates if re.search(pattern, item["content"])]
                self.assertTrue(matches, pattern)
                self.assertTrue(all(item["tag"] == "inferred" for item in matches))

    def test_uncertain_answer_produces_traceable_assumption(self) -> None:
        """不确定产生有效假设，不是假装用户回答了推荐值。"""
        docs = documents(RUNS / "task-management")
        provisional = [(analysis, question) for analysis, _, _ in docs.values() for question in analysis["questions"] if question["status"] == "provisional"]
        self.assertTrue(provisional)
        for analysis, question in provisional:
            assumptions = [a for a in analysis["assumptions"] if a["related_question"] == question["id"] and a["status"] == "active"]
            self.assertTrue(assumptions)
            for assumption in assumptions:
                self.assertEqual(assumption["tag"], "assumption")
                self.assertTrue(assumption["basis"].strip())
                self.assertTrue(assumption["verification"].strip())

    def test_answered_and_provisional_questions_are_not_reasked(self) -> None:
        """第二轮不重复问上一轮已经回答或暂定的问题。"""
        directory = RUNS / "task-management"
        first = set(load(directory / "turn-01.json")["asked_question_refs"])
        second = set(load(directory / "turn-02.json")["asked_question_refs"])
        self.assertTrue(first)
        self.assertTrue(second)
        self.assertFalse(first & second)

    def test_stop_preserves_open_p0_and_ends_questioning(self) -> None:
        """结束后没有新业务或控制问题，未解决核心缺口仍 not_ready。"""
        for group in ("high-low-voltage", "task-management"):
            with self.subTest(group=group):
                directory = RUNS / group
                record = load(sorted(directory.glob("turn-*.json"))[-1])
                self.assertEqual(record["asked_question_refs"], [])
                self.assertEqual(record["control_questions"], [])
                open_p0 = []
                for analysis, _, _ in documents(directory).values():
                    self.assertEqual(analysis["meta"]["analysis_status"], "completed")
                    blockers = [q for q in analysis["questions"] if q["priority"] == "P0" and q["status"] == "open"]
                    if blockers:
                        self.assertEqual(analysis["meta"]["readiness"], "not_ready")
                    open_p0.extend(blockers)
                self.assertTrue(open_p0)

    def test_text_probes_are_recorded_as_read_only_responses(self) -> None:
        """权限受限的探针只证明实际提问行为，不冒充独立分析文件已通过校验。"""
        responses = load(ROOT / "tests/results/stage-2-text-probes.json")
        for group in TEXT_PROBES:
            with self.subTest(group=group):
                response = responses[group]
                self.assertEqual(response["execution_mode"], "read_only_conversation")
                self.assertTrue(response["assistant_message"].strip())
                self.assertLessEqual(len(response["questions_asked"]), 3)
                for question in response["questions_asked"]:
                    self.assertIn(question["priority"], ("P0", "P1"))
                    self.assertTrue(question["recommendation"].strip())

    def test_round_limit_preserves_p0_until_explicit_stop(self) -> None:
        """达到一轮业务上限后只请求控制确认，不把未回答 P0 自动解决。"""
        directory = RUNS / "high-low-voltage"
        first = load(directory / "turn-01.json")
        second = load(directory / "turn-02.json")
        final = load(directory / "turn-03.json")
        self.assertEqual(len(first["asked_question_refs"]), 3)
        self.assertEqual(second["asked_question_refs"], [])
        self.assertEqual(len(second["control_questions"]), 1)
        self.assertEqual(final["asked_question_refs"], [])
        self.assertEqual(final["control_questions"], [])
        for analysis, _, _ in documents(directory).values():
            self.assertEqual(analysis["meta"]["analysis_status"], "completed")
            self.assertTrue(any(q["priority"] == "P0" and q["status"] == "open" for q in analysis["questions"]))

    def test_backend_has_no_visual_or_common_sense_questions(self) -> None:
        """后端探针不问视觉、登录、语言等无关细节。"""
        response = load(ROOT / "tests/results/stage-2-text-probes.json")["backend"]
        for question in response["questions_asked"]:
            self.assertNotRegex(question["question"], r"视觉稿|设计稿|按钮位置|是否需要登录|是否支持中文")
        self.assertFalse(response["ui_dependent"])

    def test_value_questions_are_lightweight(self) -> None:
        """仅缺原因的新增功能问一次原因，缺陷和原因已知时不索要价值论证。"""
        value_pattern = r"为什么要|为什么做|为何需要|原因|业务价值|收益|节省|ROI|解决什么|解决哪|目的"
        for group, expected in (("defect", 0), ("notification", 1), ("notification-with-reason", 0)):
            with self.subTest(group=group):
                questions = load(ROOT / "tests/results/stage-2-text-probes.json")[group]["questions_asked"]
                matches = [q for q in questions if re.search(value_pattern, q["question"], re.IGNORECASE)]
                self.assertEqual(len(matches), expected, questions)
                for question in questions:
                    self.assertNotRegex(question["question"], r"收益数字|节省多少|ROI|投入产出比")


if __name__ == "__main__":
    unittest.main(verbosity=2)

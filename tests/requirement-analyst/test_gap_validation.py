"""验证分析侧缺口封装、唯一接收关联及 CLI 读取边界，并覆盖生成侧上游调用回归。"""

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill/requirement-analyst/scripts/validate_analysis.py"
FIXTURE = ROOT / "tests/fixtures/requirement-analyst/high-low-voltage"


def load_module(name: str, path: Path):
    """从 path 加载独立 name 的测试目标并返回模块；文件、导入异常原样抛出。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module("gap_analysis_validator", SCRIPT)


def sample() -> tuple[dict, list, dict]:
    """返回新鲜分析、来源和一个未接收缺口；无参数，文件或解析异常原样抛出。"""
    analysis, manifest = (
        json.loads((FIXTURE / name).read_text(encoding="utf-8"))
        for name in ("analysis-result.json", "source-manifest.json")
    )
    gap = {
        "schema_version": "1.0", "requirement_id": analysis["requirement_id"],
        "counters": {"GAPREQ": 1},
        "requests": [{
            "id": "GAPREQ-1", "needed_for": "验收标准", "description": "合成缺口，仅供校验",
            "related_analysis_refs": [analysis["requirement_id"] + "/FR-1"],
            "raised_in": "0.1", "status": "open",
        }],
    }
    return analysis, manifest, gap


def write_json(path: Path, value: object) -> Path:
    """把 value 写入临时 path 并返回路径，自动建父目录；文件及序列化异常原样抛出。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


class GapValidationTests(unittest.TestCase):
    """覆盖规则 12、旧数据兼容与只读边界；断言不满足时由 unittest 报告失败。"""

    def assert_gap_failure(self, analysis, manifest, gap, **kwargs):
        """校验给定分析与 gap，kwargs 传外部资料，返回规则12失败结果；不符时抛断言异常。"""
        result = MODULE.validate_analysis(analysis, manifest, gap_requests=gap, **kwargs)
        self.assertEqual(result["status"], "fail", result)
        self.assertTrue(any(d["rule"] == 12 and d["level"] == "fail" for d in result["diagnostics"]), result)
        return result

    def test_legacy_without_gap_or_refs_keeps_behavior(self):
        """没有缺口引用的旧问题可省略 gap；显式空封装也不改变原有通过结果。"""
        analysis, manifest, gap = sample()
        expected = {"status": "pass", "diagnostics": []}
        self.assertEqual(MODULE.validate_analysis(analysis, manifest), expected)
        self.assertEqual(MODULE.validate_analysis(analysis, manifest, gap_requests=None), expected)
        gap.update(counters={"GAPREQ": 0}, requests=[])
        self.assertEqual(MODULE.validate_analysis(analysis, manifest, gap_requests=gap), expected)

    def test_gap_reference_requires_explicit_memory_object(self):
        """内存 API 不找文件，已有 gap_request_ref 而未提供 gap 时按规则12失败并定位问题。"""
        analysis, manifest, _ = sample()
        analysis["questions"][0]["gap_request_ref"] = "GAPREQ-1"
        result = self.assert_gap_failure(analysis, manifest, None)
        self.assertTrue(any(d["item_id"] == "Q-1" and d["path"] == "/questions/0/gap_request_ref" for d in result["diagnostics"]))

    def test_question_reference_pattern(self):
        """选填扩展一旦出现就须为正整数 GAPREQ 编号，不能接受跨需求或前导零。"""
        for reference in (None, 1, [], "", "GAPREQ-0", "GAPREQ-01", "GAPREQ--1", "REQ-X/GAPREQ-1", "GAPREQ-1-extra"):
            with self.subTest(reference=reference):
                analysis, manifest, gap = sample()
                analysis["questions"][0]["gap_request_ref"] = reference
                self.assert_gap_failure(analysis, manifest, gap)

    def test_versioned_envelope_required_fields_and_types(self):
        """缺口必须是完整版本化对象；错封装不能崩溃或被当作未提供。"""
        analysis, manifest, gap = sample()
        cases = [[], "invalid", False, {}, {**gap, "schema_version": "2.0"},
                 {**gap, "requirement_id": "WRONG"}, {**gap, "requirement_id": "bad/id"},
                 {**gap, "counters": None}, {**gap, "counters": {}},
                 {**gap, "requests": None}, {**gap, "requests": {}}]
        for field in gap:
            cases.append({key: value for key, value in gap.items() if key != field})
        for case in cases:
            with self.subTest(case=case):
                self.assert_gap_failure(analysis, manifest, case)

    def test_gap_counter_type_and_high_water(self):
        """计数器必须为非负整数且不能低于已分配编号；允许保留高于当前最大值的高水位。"""
        analysis, manifest, gap = sample()
        for counter in (-1, True, 1.5, "1", None):
            with self.subTest(counter=counter):
                gap["counters"]["GAPREQ"] = counter
                self.assert_gap_failure(analysis, manifest, gap)
        gap["requests"][0]["id"] = "GAPREQ-9"
        gap["counters"]["GAPREQ"] = 8
        self.assert_gap_failure(analysis, manifest, gap)
        for counter in (9, 12):
            gap["counters"]["GAPREQ"] = counter
            self.assertEqual(MODULE.validate_analysis(analysis, manifest, gap_requests=gap)["status"], "pass")

    def test_request_required_fields_and_types(self):
        """交接所需请求字段完整且有合法类型、枚举和版本，扩展不会掩盖缺字段。"""
        analysis, manifest, gap = sample()
        original = copy.deepcopy(gap["requests"][0])
        for field in original:
            with self.subTest(missing=field):
                gap["requests"] = [{key: value for key, value in original.items() if key != field}]
                self.assert_gap_failure(analysis, manifest, gap)
        cases = [("id", "GAPREQ-0"), ("id", "GAPREQ-01"), ("needed_for", " "),
                 ("description", ""), ("description", []), ("related_analysis_refs", {}),
                 ("raised_in", "0.0"), ("raised_in", "v1"), ("status", "received")]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                gap["requests"] = [{**original, field: value}]
                self.assert_gap_failure(analysis, manifest, gap)
        gap["requests"] = [None]
        self.assert_gap_failure(analysis, manifest, gap)

    def test_duplicate_gap_ids_are_rejected(self):
        """同需求缺口编号唯一，重复请求即使均未接收也失败。"""
        analysis, manifest, gap = sample()
        gap["requests"].append(copy.deepcopy(gap["requests"][0]))
        result = self.assert_gap_failure(analysis, manifest, gap)
        self.assertTrue(any(d["item_id"] == "GAPREQ-1" and d["path"].endswith("/id") for d in result["diagnostics"]))

    def test_question_reference_must_resolve_in_current_requirement(self):
        """格式合法但不存在的缺口引用仍失败，不能借用其他需求同名缺口。"""
        analysis, manifest, gap = sample()
        analysis["questions"][0]["gap_request_ref"] = "GAPREQ-2"
        self.assert_gap_failure(analysis, manifest, gap)
        gap["requirement_id"] = "OTHER"
        analysis["questions"][0]["gap_request_ref"] = "GAPREQ-1"
        self.assert_gap_failure(analysis, manifest, gap)

    def test_receivers_are_unique_for_all_statuses(self):
        """同一缺口最多一个问题；open 中断状态也不能重复，旧 dropped 接收记录不能被覆盖。"""
        for status in ("open", "handed_over", "closed"):
            with self.subTest(status=status):
                analysis, manifest, gap = sample()
                gap["requests"][0]["status"] = status
                for question in analysis["questions"][:2]:
                    question["gap_request_ref"] = "GAPREQ-1"
                analysis["questions"][0]["status"] = "dropped"
                result = self.assert_gap_failure(analysis, manifest, gap)
                self.assertTrue(any(d["item_id"] == "Q-2" for d in result["diagnostics"]))

    def test_handed_over_and_closed_require_receiver(self):
        """已交接或关闭不能没有接收问题；生成侧关闭充分性不在这里重复实现。"""
        for status in ("handed_over", "closed"):
            with self.subTest(status=status):
                analysis, manifest, gap = sample()
                request = gap["requests"][0]
                request["status"] = status
                if status == "closed":
                    request["resolution"] = {"kind": "supplied", "analysis_refs": request["related_analysis_refs"], "reason": "合成依据"}
                self.assert_gap_failure(analysis, manifest, gap)
                analysis["questions"][0]["gap_request_ref"] = "GAPREQ-1"
                # 问题仍 open 不违反接收协议；能否关闭须由 PRD Generator 另行判断。
                self.assertEqual(MODULE.validate_analysis(analysis, manifest, gap_requests=gap)["status"], "pass")

    def test_open_allows_no_receiver_or_saved_receiver(self):
        """open 的未交接及保存成功后状态标记中断均合法，不输出额外分析警告。"""
        analysis, manifest, gap = sample()
        self.assertEqual(MODULE.validate_analysis(analysis, manifest, gap_requests=gap), {"status": "pass", "diagnostics": []})
        analysis["questions"][0]["gap_request_ref"] = "GAPREQ-1"
        self.assertEqual(MODULE.validate_analysis(analysis, manifest, gap_requests=gap), {"status": "pass", "diagnostics": []})

    def test_full_analysis_references_are_valid_and_exist(self):
        """缺口引用必须完整、属于分析条目且目标存在，不能使用局部编号或来源编号。"""
        analysis, manifest, gap = sample()
        rid = analysis["requirement_id"]
        for references in (["FR-1"], [rid + "/FR-0"], [rid + "/FR-01"], [rid + "/SRC-1"],
                           [rid + "/FR-999"], [rid + "/FR-1/extra"], ["bad id/FR-1"],
                           [rid + "/FR-1", rid + "/FR-1"], [None]):
            with self.subTest(references=references):
                gap["requests"][0]["related_analysis_refs"] = references
                self.assert_gap_failure(analysis, manifest, gap)
        gap["requests"][0]["related_analysis_refs"] = []
        self.assertEqual(MODULE.validate_analysis(analysis, manifest, gap_requests=gap)["status"], "pass")

    def test_external_references_require_explicit_documents(self):
        """跨需求资料仅显式提供；完整编号本身不能证明外部条目存在。"""
        analysis, manifest, gap = sample()
        other, other_manifest, _ = sample()
        other["requirement_id"] = "CUSTOM-42"
        # 外部问题的缺口不归当前需求校验，避免把本需求 gap 错用到相关资料。
        other["questions"][0]["gap_request_ref"] = "GAPREQ-99"
        gap["requests"][0]["related_analysis_refs"] = ["CUSTOM-42/FR-1"]
        self.assert_gap_failure(analysis, manifest, gap)
        self.assertEqual(MODULE.validate_analysis(analysis, manifest, gap_requests=gap, related_analyses=[(other, other_manifest)])["status"], "pass")
        gap["requests"][0]["related_analysis_refs"] = ["CUSTOM-42/FR-999"]
        self.assert_gap_failure(analysis, manifest, gap, related_analyses=[(other, other_manifest)])

    def test_receiver_related_ids_keep_existing_reference_checks(self):
        """接收问题的本需求局部引用和外部完整引用仍沿用既有格式与存在性检查。"""
        analysis, manifest, gap = sample()
        other, other_manifest, _ = sample()
        other["requirement_id"] = "CUSTOM-42"
        question = analysis["questions"][0]
        question.update(gap_request_ref="GAPREQ-1", related_ids=["FR-1", "CUSTOM-42/FR-1"])
        self.assertEqual(MODULE.validate_analysis(analysis, manifest, gap_requests=gap, related_analyses=[(other, other_manifest)])["status"], "pass")
        for reference in ("FR-0", "CUSTOM-42/FR-999"):
            question["related_ids"] = [reference]
            result = MODULE.validate_analysis(analysis, manifest, gap_requests=gap, related_analyses=[(other, other_manifest)])
            self.assertEqual(result["status"], "fail", result)

    def test_extensions_and_inputs_are_read_only_on_pass_and_fail(self):
        """未知扩展、关闭依据和输入对象在成功、失败时都原样保留。"""
        analysis, manifest, gap = sample()
        gap["extension"] = {"owned_by": "generator", "data": [1, 2]}
        gap["counters"]["EXTRA"] = 7
        gap["requests"][0]["resolution"] = {"future_extension": ["unchanged"]}
        for fail in (False, True):
            if fail:
                analysis["questions"][0]["gap_request_ref"] = "GAPREQ-999"
            before = copy.deepcopy((analysis, manifest, gap))
            result = MODULE.validate_analysis(analysis, manifest, gap_requests=gap)
            self.assertEqual(result["status"], "fail" if fail else "pass", result)
            self.assertEqual((analysis, manifest, gap), before)

    def test_stale_warning_survives_gap_failure(self):
        """规则12失败不吞掉 stale 警告，合法缺口也不改变三态优先级。"""
        analysis, manifest, gap = sample()
        analysis["meta"]["analysis_status"] = "stale"
        self.assertEqual(MODULE.validate_analysis(analysis, manifest, gap_requests=gap)["status"], "warning")
        analysis["questions"][0]["gap_request_ref"] = "GAPREQ-999"
        result = self.assert_gap_failure(analysis, manifest, gap)
        self.assertTrue(any(d["rule"] == 11 and d["level"] == "warning" for d in result["diagnostics"]))


class GapCliTests(unittest.TestCase):
    """从真实 CLI 校验当前需求读取、显式覆盖及独立安装；不访问生产工作区。"""

    def setUp(self):
        """准备临时当前需求和已保存接收问题；返回 None，文件错误原样抛出。"""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.analysis, self.manifest, self.gap = sample()
        self.analysis["questions"][0]["gap_request_ref"] = "GAPREQ-1"
        self.path = write_json(self.directory / "current/analysis/analysis-result.json", self.analysis)
        write_json(self.path.with_name("source-manifest.json"), self.manifest)
        self.gap_path = self.path.parent.parent / "prd/gap-requests.json"

    def run_cli(self, *args, script=SCRIPT):
        """从无关 cwd 运行 script 及 args，返回进程和解析结果；子进程或解析错误由测试报告。"""
        before = {path: path.read_bytes() for path in self.directory.rglob("*") if path.is_file()}
        process = subprocess.run([sys.executable, "-I", "-B", str(script), str(self.path), *map(str, args)], cwd=self.directory, capture_output=True, text=True, check=False)
        self.assertEqual(process.stderr, "")
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        return process, json.loads(process.stdout)

    def test_auto_loads_only_current_requirement(self):
        """默认路径基于传入 analysis 而非 cwd，其他需求同名缺口不能补齐当前需求。"""
        write_json(self.directory / "other/prd/gap-requests.json", self.gap)
        process, result = self.run_cli()
        self.assertEqual(process.returncode, 2, result)
        write_json(self.gap_path, self.gap)
        process, result = self.run_cli()
        self.assertEqual(process.returncode, 0, result)

    def test_explicit_gap_path_overrides_automatic_path(self):
        """显式文件支持独立夹具并覆盖默认位置，不从默认坏文件降级。"""
        explicit = write_json(self.directory / "fixture-gap.json", self.gap)
        write_json(self.gap_path, {"invalid": "automatic"})
        process, result = self.run_cli("--gap-requests", explicit)
        self.assertEqual(process.returncode, 0, result)
        process, result = self.run_cli("--gap-requests", self.directory / "missing.json")
        self.assertEqual(process.returncode, 2, result)
        self.assertTrue(any(d["rule"] == 12 for d in result["diagnostics"]))

    def test_invalid_gap_files_report_rule_12(self):
        """存在的坏 JSON、重复键、非法常量、null 与错误编码不能静默当作没有缺口。"""
        self.gap_path.parent.mkdir(parents=True)
        for content in (b"{", b'{"requests":[],"requests":[]}', b'{"x":NaN}', b"null", b"\xff"):
            with self.subTest(content=content):
                self.gap_path.write_bytes(content)
                process, result = self.run_cli()
                self.assertEqual(process.returncode, 2, result)
                self.assertTrue(any(d["rule"] == 12 for d in result["diagnostics"]))

    def test_legacy_cli_without_gap_is_unchanged(self):
        """CLI 没缺口且没扩展引用时继续通过，但存在非法缺口封装仍须失败。"""
        del self.analysis["questions"][0]["gap_request_ref"]
        write_json(self.path, self.analysis)
        process, result = self.run_cli()
        self.assertEqual(process.returncode, 0, result)
        write_json(self.gap_path, [])
        process, result = self.run_cli()
        self.assertEqual(process.returncode, 2, result)

    def test_cross_requirement_documents_are_explicit_only(self):
        """磁盘上存在关联资料仍不能隐式使用，只有 --related-analysis 能满足引用。"""
        other, manifest, _ = sample()
        other["requirement_id"] = "OTHER"
        other_path = write_json(self.directory / "other/analysis/analysis-result.json", other)
        write_json(other_path.with_name("source-manifest.json"), manifest)
        # 关联需求缺口即使损坏也不能被自动读取。
        write_json(other_path.parent.parent / "prd/gap-requests.json", [])
        self.gap["requests"][0]["related_analysis_refs"] = ["OTHER/FR-1"]
        write_json(self.gap_path, self.gap)
        process, result = self.run_cli()
        self.assertEqual(process.returncode, 2, result)
        process, result = self.run_cli("--related-analysis", other_path)
        self.assertEqual(process.returncode, 0, result)

    def test_analyst_installation_does_not_need_generator(self):
        """仅复制分析 Skill 的独立安装也能校验缺口，不读取生成器安装目录的 Schema。"""
        installed = self.directory / "installed/requirement-analyst"
        shutil.copytree(ROOT / "skill/requirement-analyst", installed)
        write_json(self.gap_path, self.gap)
        process, result = self.run_cli(script=installed / "scripts/validate_analysis.py")
        self.assertEqual(process.returncode, 0, result)
        self.assertFalse((installed.parent / "prd-generator").exists())


class PrdUpstreamGapTests(unittest.TestCase):
    """验证阶段1生成校验器向唯一上游实现传递缺口，包括辅助来源缺失的降级路径。"""

    def test_bad_gap_structure_with_missing_sources_is_diagnostic(self):
        """来源降级时遇到非法缺口容器也返回规则12，不进入无结构前提的索引。"""
        module = load_module("bad_gap_prd_validator", ROOT / "skill/prd-generator/scripts/validate_prd.py")
        support = load_module("bad_gap_prd_fixture_support", ROOT / "tests/prd-generator/prd_fixture_support.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = support.make_workspace(Path(temporary) / "requirement")
            (root / "analysis/source-manifest.json").rename(root / "analysis/unused-sources.json")
            for malformed in ([], {"schema_version": "1.0", "requests": None}):
                with self.subTest(malformed=malformed):
                    support.write_json(root / "prd/gap-requests.json", malformed)
                    result = module.validate_prd(root)
                    self.assertEqual(result["status"], "fail", result)
                    self.assertTrue(any(d["rule"] == 12 for d in result["diagnostics"]), result)

    def test_stage_one_gap_fixtures_keep_expected_results(self):
        """阶段1合法缺口夹具仍只警告，不能因上游未收到 gap 变成失败。"""
        module = load_module("gap_prd_validator", ROOT / "skill/prd-generator/scripts/validate_prd.py")
        support = load_module("gap_prd_fixture_support", ROOT / "tests/prd-generator/prd_fixture_support.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = support.make_workspace(Path(temporary) / "requirement")
            analysis_path = root / "analysis/analysis-result.json"
            analysis = support.read_json(analysis_path)
            analysis["questions"] = [{
                "id": "Q-1", "question": "合成缺口？", "priority": "P3", "resolution": "ask_product",
                "reason": "测试", "impact": "测试", "options": ["补充", "其他"], "recommendation": "补充",
                "status": "open", "related_ids": ["FR-1"], "gap_request_ref": "GAPREQ-1",
            }]
            support.write_json(analysis_path, analysis)
            gap = {"schema_version": "1.0", "requirement_id": analysis["requirement_id"], "counters": {"GAPREQ": 1},
                   "requests": [{"id": "GAPREQ-1", "needed_for": "验收", "description": "合成缺口",
                                 "related_analysis_refs": [analysis["requirement_id"] + "/FR-1"], "raised_in": "0.1", "status": "open"}]}
            support.write_json(root / "prd/gap-requests.json", gap)
            path = root / "prd/prd.md"
            path.write_text(path.read_text(encoding="utf-8").replace("无适用遗留项", support.block("gap", "GAPREQ-1", "待分析补充：合成缺口")), encoding="utf-8")
            support.refresh_hash(root)
            for missing_sources in (False, True):
                with self.subTest(missing_sources=missing_sources):
                    if missing_sources:
                        (root / "analysis/source-manifest.json").rename(root / "analysis/unused-sources.json")
                    result = module.validate_prd(root)
                    self.assertEqual(result["status"], "warning", result)
                    self.assertFalse(any(d["level"] == "fail" for d in result["diagnostics"]), result)
                    if missing_sources:
                        # 降级路径也必须真正执行规则12，不能仅漏检而恰好通过。
                        gap["counters"]["GAPREQ"] = 0
                        support.write_json(root / "prd/gap-requests.json", gap)
                        result = module.validate_prd(root)
                        self.assertEqual(result["status"], "fail", result)
                        self.assertTrue(any(d["rule"] == 12 and "上游校验失败" in d["message"] for d in result["diagnostics"]), result)


if __name__ == "__main__":
    unittest.main()

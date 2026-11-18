"""验证统一首稿写入、元数据渲染、重复生成及失败恢复；合成输入不代表业务批准。"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch as mock_patch

from prd_fixture_support import block, digest, make_workspace, read_json, write_json


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skill/prd-generator/scripts"


def load(name):
    """加载生产 name 脚本并返回模块；路径或导入错误直接使测试失败。"""
    spec = importlib.util.spec_from_file_location("draft_test_" + name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrdDraftTests(unittest.TestCase):
    """覆盖真实生产保存边界，不让候选成功冒充正式保存成功。"""

    @classmethod
    def setUpClass(cls):
        """加载统一写入与渲染入口，导入失败不跳过。"""
        cls.writer = load("write_draft")
        cls.renderer = load("render_info")

    def setUp(self):
        """新建独立分析工作区；只复制所需分析及common，不预填生成侧产物。"""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        fixture = make_workspace(self.base / "format-fixture")
        self.body = (fixture / "prd/prd.md").read_text(encoding="utf-8")
        self.root = self.base / "requirement"
        for relative in ("analysis/analysis-result.json", "analysis/source-manifest.json"):
            write_json(self.root / relative, read_json(fixture / relative))
        metadata = read_json(fixture / "requirement.json")
        metadata.pop("prd")
        metadata["foreign_extension"] = {"keep": "其他维护者的字段"}
        write_json(self.root / "requirement.json", metadata)
        self.patch = {"patch_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "base_prd_version": None,
                      "base_analysis_revision": 1, "items": [{"mapping_key": "synthetic-query", "kind": "functional_requirement", "analysis_refs": ["SYNTHETIC-PRD/FR-1"]}]}
        self.counter = 0

    def save(self, **kwargs):
        """用固定测试时间保存候选，返回真实生产响应；默认候选位于独立新目录。"""
        self.counter += 1
        return self.writer.write_draft(self.root, patch=kwargs.pop("patch", self.patch), body=kwargs.pop("body", self.body),
                    generated_at=kwargs.pop("generated_at", "2026-11-17T00:00:00Z"),
                    candidate_dir=self.base / f"candidate-{self.counter}", **kwargs)

    def fingerprint(self):
        """返回当前业务字节映射，验证拒绝和生成侧文件归属；读取错误使测试失败。"""
        return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}

    def test_first_generation_and_repeat_preserve_identity(self):
        """首次0.1、重复0.2；分析与其他块不变，编号和需求正文稳定。"""
        before = self.fingerprint()
        result = self.save()
        self.assertNotEqual(result["status"], "fail", result)
        self.assertEqual(result["version"], "0.1")
        first = read_json(self.root / "prd/prd-trace.json")
        first_text = (self.root / "prd/prd.md").read_text()
        metadata = read_json(self.root / "requirement.json")
        self.assertEqual(metadata["foreign_extension"], {"keep": "其他维护者的字段"})
        self.assertEqual(metadata["common"], read_json(self.base / "format-fixture/requirement.json")["common"])
        for name in ("analysis/analysis-result.json", "analysis/source-manifest.json"):
            self.assertEqual((self.root / name).read_bytes(), before[name])
        repeated = deepcopy(self.patch)
        repeated["base_prd_version"] = "0.1"
        result = self.save(patch=repeated, body=first_text)
        self.assertNotEqual(result["status"], "fail", result)
        self.assertEqual(result["version"], "0.2")
        second = read_json(self.root / "prd/prd-trace.json")
        self.assertEqual(first["items"], second["items"])
        parsed = self.writer._module("validate_prd")
        one = parsed._blocks(first_text, [])
        two = parsed._blocks((self.root / "prd/prd.md").read_text(), [])
        self.assertEqual({key: value["text"] for key, value in one["item"].items()},
                         {key: value["text"] for key, value in two["item"].items()})
        self.assertEqual(len((self.root / "prd/prd-events.jsonl").read_text().splitlines()), 2)

    def test_candidate_failure_preserves_business_files(self):
        """缺少需求块的失败候选保留供修正，正式目录原始字节不变。"""
        before = self.fingerprint()
        result = self.save(body=block("section", "scope", "分析结果中无此项"))
        self.assertEqual(result["status"], "fail", result)
        self.assertEqual(self.fingerprint(), before)
        self.assertTrue(Path(result["candidate_dir"]).is_dir())
        self.assertFalse((self.root / "prd").exists())

    def test_dotdot_candidate_cannot_enter_analysis(self):
        """带..的候选路径先规范化，不能绕过生成侧禁止写analysis的边界。"""
        (self.base / "alias").mkdir()
        candidate = self.base / "alias/../requirement/analysis/candidate"
        before = self.fingerprint()
        result = self.writer.write_draft(self.root, patch=self.patch, body=self.body, candidate_dir=candidate)
        self.assertEqual(result["status"], "fail", result)
        self.assertEqual(before, self.fingerprint())
        self.assertFalse((self.root / "analysis/candidate").exists())

    def test_same_input_cannot_rewrite_requirement_content(self):
        """重复生成不能借合法结构把查询偷换成删除，拒绝后正式草稿字节不变。"""
        first = self.save()
        self.assertNotEqual(first["status"], "fail", first)
        repeated = deepcopy(self.patch)
        repeated["base_prd_version"] = "0.1"
        before = self.fingerprint()
        result = self.save(patch=repeated, body=(self.root / "prd/prd.md").read_text().replace("合成查询", "彻底删除"))
        self.assertEqual(result["status"], "fail", result)
        self.assertEqual(before, self.fingerprint())
        self.assertTrue(Path(result["candidate_dir"]).is_dir())

    def test_repeat_cannot_add_business_rules_outside_sections(self):
        """完整正文比较覆盖章节外文本，不能借未标记的附加段落偷加新规则。"""
        first = self.save()
        self.assertNotEqual(first['status'], 'fail', first)
        repeated = deepcopy(self.patch)
        repeated['base_prd_version'] = '0.1'
        before = self.fingerprint()
        body = (self.root / 'prd/prd.md').read_text() + '\n## 新业务规定\n允许删除全部记录。\n'
        result = self.save(patch=repeated, body=body)
        self.assertEqual(result['status'], 'fail', result)
        self.assertEqual(before, self.fingerprint())
        self.assertTrue(Path(result['candidate_dir']).exists())

    def test_render_failure_preserves_raw_candidate(self):
        """编号或信息渲染失败也保留模型原文和补丁供三次修正，不只保留后置校验失败。"""
        before = self.fingerprint()
        body = self.body + block("section", "info", "duplicate")
        result = self.save(body=body)
        self.assertEqual(result["status"], "fail", result)
        self.assertEqual((Path(result["candidate_dir"]) / "inputs/body.md").read_text(), body)
        self.assertEqual(before, self.fingerprint())

    def test_version_conflict_rejected(self):
        """补丁读时版本不符时拒写，而不是盲改版本自动重试。"""
        invalid = deepcopy(self.patch)
        invalid["base_prd_version"] = "0.1"
        before = self.fingerprint()
        result = self.save(patch=invalid)
        self.assertEqual(result["status"], "fail", result)
        self.assertEqual(before, self.fingerprint())

    def test_analysis_change_after_validation_rejected(self):
        """候选校验完成后分析被并发修改，正式PRD不得落盘。"""
        validator = self.writer._module("validate_prd")
        actual = validator.validate_prd
        def concurrent(*args, **kwargs):
            """执行真实候选校验再模拟外部修订，返回原校验响应；写入错误原样抛出。"""
            response = actual(*args, **kwargs)
            path = self.root / "analysis/analysis-result.json"
            value = read_json(path)
            value["meta"]["analysis_revision"] += 1
            write_json(path, value)
            return response
        with mock_patch.object(validator, "validate_prd", side_effect=concurrent):
            result = self.save()
        self.assertEqual(result["status"], "fail", result)
        self.assertFalse((self.root / "prd").exists())

    def test_metadata_change_after_validation_preserved(self):
        """即使PRD版本未变，common或其他块的并发修改也不得被旧副本覆盖。"""
        validator = self.writer._module("validate_prd")
        actual = validator.validate_prd
        def concurrent(*args, **kwargs):
            """在真实校验后更改标题，返回校验结果；只修改当前测试副本。"""
            response = actual(*args, **kwargs)
            metadata = read_json(self.root / "requirement.json")
            metadata["common"]["title"] = "并发标题"
            write_json(self.root / "requirement.json", metadata)
            return response
        with mock_patch.object(validator, "validate_prd", side_effect=concurrent):
            result = self.save()
        self.assertEqual(result["status"], "fail", result)
        self.assertEqual(read_json(self.root / "requirement.json")["common"]["title"], "并发标题")
        self.assertFalse((self.root / "prd").exists())

    def test_interruption_recovery_is_idempotent(self):
        """多文件写入中断保留journal，显式恢复不重复事件也不改分析。"""
        actual = self.writer._atomic_write
        def interrupted(path, raw):
            """模拟正式追溯替换失败；其他单文件使用真实写入，返回None或抛OSError。"""
            if path == self.root / "prd/prd-trace.json":
                raise OSError("synthetic interrupted trace write")
            return actual(path, raw)
        with mock_patch.object(self.writer, "_atomic_write", side_effect=interrupted):
            result = self.save()
        self.assertEqual(result["status"], "fail", result)
        self.assertTrue(result["recovery_required"])
        self.assertEqual(result["written"], ["prd/prd.md"])
        self.assertFalse(result["transaction_complete"])
        self.assertTrue((self.root / "prd/prd.md").exists())
        self.assertFalse((self.root / "prd/prd-events.jsonl").exists())
        retry = self.save()
        self.assertEqual(retry["status"], "fail")
        recovered = self.writer.recover_draft(self.root)
        self.assertNotEqual(recovered["status"], "fail", recovered)
        self.assertTrue(recovered["recovered"])
        self.assertEqual(len((self.root / "prd/prd-events.jsonl").read_text().splitlines()), 1)
        self.assertFalse((self.root / self.writer.JOURNAL).exists())

    def test_recovery_refuses_concurrent_content(self):
        """恢复期间遇到他人改写正文时保留双方候选，不覆盖新字节。"""
        actual = self.writer._atomic_write
        def interrupted(path, raw):
            """在trace替换点注入故障，其他写入照常，无返回值。"""
            if path == self.root / "prd/prd-trace.json":
                raise OSError("synthetic interruption")
            return actual(path, raw)
        with mock_patch.object(self.writer, "_atomic_write", side_effect=interrupted):
            self.save()
        path = self.root / "prd/prd.md"
        path.write_text("other person's content")
        result = self.writer.recover_draft(self.root)
        self.assertEqual(result["status"], "fail", result)
        self.assertEqual(path.read_text(), "other person's content")
        self.assertTrue((self.root / self.writer.JOURNAL).exists())

    def test_new_gap_warns_and_has_single_placeholder(self):
        """模板确缺内容时保存open缺口与唯一占位，warning不是结构失败或发布批准。"""
        gaps = {"schema_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "counters": {"GAPREQ": 1}, "requests": [
            {"id": "GAPREQ-1", "needed_for": "acceptance_criteria", "description": "模板要求的业务验收条件尚未分析", "related_analysis_refs": ["SYNTHETIC-PRD/FR-1"], "raised_in": "0.1", "status": "open"}]}
        body = self.body.replace("<!-- prd:section acceptance_criteria -->\n分析结果中无此项", "<!-- prd:section acceptance_criteria -->\n" + block("gap", "GAPREQ-1", "待分析补充：业务验收条件"))
        result = self.save(body=body, gaps=gaps)
        self.assertEqual(result["status"], "warning", result)
        self.assertTrue(result["generated"])
        self.assertEqual(read_json(self.root / "prd/gap-requests.json")["requests"][0]["status"], "open")
        self.assertEqual(len((self.root / "prd/prd-events.jsonl").read_text().splitlines()), 2)

    def test_new_gap_cannot_reuse_old_counter_range(self):
        """缺口列表有历史高水位时，新请求也不能补用低编号空洞。"""
        old_request = {"id": "GAPREQ-10", "needed_for": "acceptance_criteria", "description": "历史缺口", "related_analysis_refs": [], "raised_in": "0.1", "status": "open"}
        existing = {"schema_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "counters": {"GAPREQ": 10}, "requests": [old_request]}
        supplied = deepcopy(existing)
        supplied["requests"].append({**old_request, "id": "GAPREQ-1"})
        with self.assertRaisesRegex(ValueError, "高水位"):
            self.writer._gap_document(self.root, supplied, "SYNTHETIC-PRD", "0.2", existing)

    def test_unreadable_optional_manifest_degrades_without_bypassing_checks(self):
        """可选来源清单不可读时统一保存仍可降级，保留warning而不伪造来源。"""
        manifest = self.root / 'analysis/source-manifest.json'
        manifest.rename(self.root / 'analysis/source-backup.json')
        manifest.mkdir()
        result = self.save()
        self.assertEqual(result['status'], 'warning', result)
        self.assertTrue(result['generated'])
        self.assertTrue(any('来源清单不可用' in item['message'] for item in result['diagnostics']), result)

    def test_visible_title_handles_table_characters(self):
        """标题含竖线、实体和换行时展示转义与权威元数据仍一致，不篡改common。"""
        metadata = read_json(self.root / "requirement.json")
        metadata["common"]["title"] = "查询 | A&B\n<br>第二行"
        write_json(self.root / "requirement.json", metadata)
        result = self.save()
        self.assertNotEqual(result["status"], "fail", result)
        self.assertEqual(read_json(self.root / "requirement.json")["common"], metadata["common"])
        text = (self.root / "prd/prd.md").read_text()
        self.assertIn("查询 &#124; A&amp;B<br>&lt;br&gt;第二行", text)

    def test_saved_prd_displays_beijing_seconds_without_rewriting_event_time(self):
        """生成时间和变更记录按北京时间显示到秒，事件仍保留原始 UTC 时间戳。"""
        timestamp = "2026-11-18T07:12:32.964707+00:00"
        result = self.save(generated_at=timestamp)
        self.assertTrue(result.get("generated"), result)
        text = (self.root / "prd/prd.md").read_text(encoding="utf-8")
        self.assertIn("| 生成时间 | 2026-11-18 15:12:32 |", text)
        self.assertIn("- 2026-11-18 15:12:32 ·", text)
        self.assertNotIn(timestamp, text)
        event = json.loads((self.root / "prd/prd-events.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(event["time"], timestamp)

    def test_display_time_rolls_over_and_does_not_shift_twice(self):
        """UTC 夜间正确跨到北京时间次日，评审重渲染已展示的时间不会再次加八小时。"""
        displayed = self.renderer.format_display_time("2026-11-18T20:12:32Z")
        self.assertEqual(displayed, "2026-11-19 04:12:32")
        self.assertEqual(self.renderer.format_display_time(displayed), displayed)
        self.assertEqual(self.renderer.format_display_time("2026-11-19T04:12:32+08:00"), displayed)

    def test_render_info_is_authoritative_and_readonly(self):
        """渲染使用权威信息并保持需求块原文，正文摘要包含空白差异。"""
        metadata = read_json(self.base / "format-fixture/requirement.json")
        trace = read_json(self.base / "format-fixture/prd/prd-trace.json")
        text = self.renderer.render_info(self.body, metadata, trace, generated_at="fixed", uncovered_analysis=["technical_feasibility"])
        self.assertIn("| 生成时间 | fixed |", text)
        self.assertIn("| 未覆盖的分析项 | technical_feasibility |", text)
        self.assertEqual(self.renderer.content_hash(text.encode()), digest(text.encode()))
        self.assertNotEqual(self.renderer.content_hash(text.encode()), self.renderer.content_hash((text + " ").encode()))
        with self.assertRaises(ValueError):
            self.renderer.render_info(self.body + block("section", "info", "duplicate"), metadata, trace, generated_at="fixed")

    def test_cli_works_from_unrelated_directory(self):
        """公开保存CLI在隔离模式和其他cwd运行，退出码与单JSON响应一致。"""
        patch_path = write_json(self.base / "patch.json", self.patch)
        body_path = self.base / "body.md"
        body_path.write_text(self.body, encoding="utf-8")
        response = subprocess.run([sys.executable, "-I", "-B", str(SCRIPTS / "write_draft.py"), str(self.root), "--patch", str(patch_path), "--body", str(body_path), "--candidate-dir", str(self.base / "cli-candidate")], cwd="/tmp", capture_output=True, text=True, timeout=30)
        self.assertIn(response.returncode, (0, 1), response.stdout + response.stderr)
        self.assertTrue(__import__("json").loads(response.stdout)["generated"])


if __name__ == "__main__":
    unittest.main()

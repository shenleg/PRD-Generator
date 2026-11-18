"""验证正文基准和手工不一致定位、配对及只读校验边界。"""

import importlib.util
from pathlib import Path
import tempfile
import unittest

from prd_fixture_support import block, digest, make_workspace, read_json, refresh_hash, write_json


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("edit_prd_validator", ROOT / "skill/prd-generator/scripts/validate_prd.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
RID = "SYNTHETIC-PRD"
ITEM = RID + "/PRD-FR-001"
SECTION = RID + "/prd/sections/scope"
MARK = "【与分析不一致】"


class EditValidationTests(unittest.TestCase):
    """使用合成工作稿覆盖手工编辑的校验规则。"""

    def setUp(self):
        """建立独立工作稿；夹具创建异常原样抛出。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_workspace(Path(self.temp.name) / "requirement")
        self.path = self.root / "prd/prd.md"

    def save(self, text):
        """写入测试正文并刷新摘要；text 为候选正文，返回正文，文件错误原样抛出。"""
        self.path.write_text(text, encoding="utf-8")
        refresh_hash(self.root)
        return text

    def paired(self, target=ITEM):
        """创建一对测试标注；target 为完整引用，返回正文，文件错误原样抛出。"""
        text = self.path.read_text(encoding="utf-8")
        if target == ITEM:
            text = text.replace("PRD-FR-001：合成查询", "PRD-FR-001：" + MARK + "合成查询")
        else:
            text = text.replace("<!-- prd:section scope -->\n", "<!-- prd:section scope -->\n" + MARK + "扩展范围\n")
        residual = block("residual", target, MARK + " 差异：增加查询范围；建议回交分析确认。")
        return self.save(text.replace("无适用遗留项", residual))

    def result(self):
        """只读校验夹具并返回诊断；安装异常原样抛出。"""
        return VALIDATOR.validate_prd(self.root)

    def test_item_pair_warning_and_helper_scope(self):
        """条目标注仅定位条目，不向所属章节传播，合法配对阻止发布。"""
        text = self.paired()
        targets = VALIDATOR.manual_inconsistencies(text, RID)
        self.assertEqual(set(targets), {ITEM})
        self.assertIn(MARK, targets[ITEM])
        result = self.result()
        self.assertEqual(result["status"], "warning")
        self.assertTrue(any(d["item_id"] == ITEM and "不得发布" in d["message"] for d in result["diagnostics"]))

    def test_section_pair(self):
        """非编号章节可按稳定章节引用配对。"""
        text = self.paired(SECTION)
        self.assertEqual(set(VALIDATOR.manual_inconsistencies(text, RID)), {SECTION})
        self.assertEqual(self.result()["status"], "warning")

    def test_missing_marks_or_target_fail(self):
        """正文、遗留项丢标或目标不存在均不能构成配对。"""
        text = self.paired()
        cases = [text.replace(MARK, "", 1), text.replace(MARK, "", 2).replace("合成查询", MARK + "合成查询", 1),
                 text.replace(ITEM, RID + "/PRD-FR-002"), text.replace(ITEM, RID + "/FR-1"),
                 text.replace("差异：增加查询范围；建议回交分析确认。", "差异：建议回交分析确认。"),
                 text.replace("差异：增加查询范围；建议回交分析确认。", "")]
        for candidate in cases:
            with self.subTest(candidate=candidate):
                self.save(candidate)
                self.assertEqual(self.result()["status"], "fail")

    def test_forbidden_and_unknown_targets(self):
        """禁止信息、变更、遗留章节及未知手工目标伪装合法引用。"""
        text = self.paired(SECTION)
        for suffix in ("prd/sections/info", "prd/sections/changes", "prd/sections/residuals", "prd/sections/unknown", "PRD-FR-999", "prd/typo"):
            with self.subTest(suffix=suffix):
                self.save(text.replace(SECTION, RID + "/" + suffix))
                self.assertEqual(self.result()["status"], "fail")

    def test_residual_in_wrong_section(self):
        """标注完整但遗留块位于正文其他章节仍失败。"""
        text = self.paired()
        residual = block("residual", ITEM, MARK + " 差异：增加查询范围；建议回交分析确认。")
        text = text.replace(residual, "无适用遗留项").replace("首次合成夹具", "首次合成夹具\n" + residual)
        self.save(text)
        self.assertEqual(self.result()["status"], "fail")

    def test_released_fails(self):
        """已发布状态包含不一致标注必须失败。"""
        text = self.paired().replace("| 状态 | draft |", "| 状态 | released |")
        self.save(text)
        metadata = read_json(self.root / "requirement.json")
        metadata["prd"]["status"] = "released"
        write_json(self.root / "requirement.json", metadata)
        self.assertTrue(any(d["level"] == "fail" and "不一致" in d["message"] for d in self.result()["diagnostics"]))

    def test_old_and_baseline_hash(self):
        """旧稿无基准兼容，基准按 UTF-8 原始换行计算且损坏失败。"""
        self.assertEqual(self.result()["status"], "pass")
        path = self.root / "prd/prd-trace.json"
        trace = read_json(path)
        original = self.path.read_bytes().decode("utf-8")
        trace["meta"]["content_baseline"] = original
        write_json(path, trace)
        self.assertEqual(self.result()["status"], "pass")
        trace["meta"]["content_baseline"] = original.replace("\n", "\r\n")
        write_json(path, trace)
        self.assertEqual(self.result()["status"], "fail")
        trace["meta"]["content_baseline"] = 17
        write_json(path, trace)
        self.assertEqual(self.result()["status"], "fail")

    def test_unprocessed_edit_is_warning_and_read_only(self):
        """旧稿手改只告警且不更改任何文件，也不臆造基准。"""
        self.path.write_text(self.path.read_text(encoding="utf-8") + "手改\n", encoding="utf-8")
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = self.result()
        self.assertEqual(result["status"], "warning")
        self.assertTrue(any("证据不足" in d["message"] for d in result["diagnostics"]))
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_invalid_or_unlocated_mark_raises(self):
        """非法定位块、信息章节及游离标注不能交给写入器作为合法目标。"""
        text = self.path.read_text(encoding="utf-8")
        for candidate in (text + MARK, text.replace("首次合成夹具", MARK), text.replace("<!-- /prd:item -->", "")):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                VALIDATOR.manual_inconsistencies(candidate, RID)


if __name__ == "__main__":
    unittest.main()

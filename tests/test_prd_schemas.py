"""核对三份声明式格式定义及向前兼容；不执行编号分配或分析写入。"""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator
from prd_fixture_support import make_workspace, read_json


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "skill/prd-generator/schemas"


class PrdSchemaTests(unittest.TestCase):
    """独立验证 Schema 安装、必填、枚举和扩展策略。"""

    @classmethod
    def setUpClass(cls):
        """读取三份安装 Schema 并校验自身合法性；文件或格式错误原样抛出。"""
        cls.validators = {}
        for name in ("prd-trace", "gap-request", "numbering-patch"):
            schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
            Draft202012Validator.check_schema(schema)
            cls.validators[name] = Draft202012Validator(schema)

    def setUp(self):
        """创建独立临时合法夹具；错误原样抛出，测试库负责生命周期清理。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_workspace(Path(self.temp.name) / "requirement")

    def test_trace_accepts_compatible_extensions(self):
        """旧追溯没有映射键仍可读取，未知兼容字段不被丢弃。"""
        trace = read_json(self.root / "prd/prd-trace.json")
        trace["items"][0].pop("mapping_key")
        trace["extension"] = {"retained": True}
        self.assertEqual(list(self.validators["prd-trace"].iter_errors(trace)), [])

    def test_trace_rejects_required_types_and_unknown_version(self):
        """缺必填、错误枚举、坏摘要和未知格式版本均被格式拒绝。"""
        original = read_json(self.root / "prd/prd-trace.json")
        for change in (lambda d: d.pop("items"), lambda d: d.update(schema_version="2.0"), lambda d: d["meta"].update(content_hash="bad"), lambda d: d["items"][0].update(tag="unverified")):
            with self.subTest(change=change):
                trace = copy.deepcopy(original)
                change(trace)
                self.assertTrue(list(self.validators["prd-trace"].iter_errors(trace)))

    def test_trace_reference_and_id_formats(self):
        """引用必须完整，编号至少三位且可增长，零序号非法。"""
        trace = read_json(self.root / "prd/prd-trace.json")
        for pid in ("PRD-FR-001", "PRD-FR-1000"):
            trace["items"][0]["prd_id"] = pid
            self.assertEqual(list(self.validators["prd-trace"].iter_errors(trace)), [])
        trace["items"][0]["prd_id"] = "PRD-FR-000"
        self.assertTrue(list(self.validators["prd-trace"].iter_errors(trace)))
        trace["items"][0]["prd_id"] = "PRD-FR-001"
        trace["items"][0]["analysis_refs"] = ["FR-1"]
        self.assertTrue(list(self.validators["prd-trace"].iter_errors(trace)))

    def test_gap_envelope_and_closed_resolution(self):
        """裸数组不是封装，closed 必须有非空结构化依据，扩展字段兼容。"""
        validator = self.validators["gap-request"]
        gap = read_json(self.root / "prd/gap-requests.json")
        self.assertEqual(list(validator.iter_errors(gap)), [])
        self.assertTrue(list(validator.iter_errors([])))
        request = {"id": "GAPREQ-1", "needed_for": "验收", "description": "合成缺口", "related_analysis_refs": [], "raised_in": "0.1", "status": "closed", "extension": "保留"}
        gap["requests"] = [request]
        gap["counters"]["GAPREQ"] = 1
        self.assertTrue(list(validator.iter_errors(gap)))
        request["resolution"] = {"kind": "supplied", "analysis_refs": ["SYNTHETIC-PRD/AC-1"], "reason": "合成引用，非业务确认"}
        self.assertEqual(list(validator.iter_errors(gap)), [])

    def test_patch_forbids_model_assigned_data(self):
        """编号补丁拒绝正文、摘要和计数器，不接受模型自行分配新数据。"""
        validator = self.validators["numbering-patch"]
        patch = {"patch_version": "1.0", "requirement_id": "SYNTHETIC-PRD", "base_prd_version": None, "base_analysis_revision": 1, "items": [{"mapping_key": "query", "kind": "functional_requirement", "analysis_refs": ["SYNTHETIC-PRD/FR-1"]}]}
        self.assertEqual(list(validator.iter_errors(patch)), [])
        for key, value in (("content", "不允许的正文"), ("source_digest", "sha256:" + "0" * 64), ("counters", {})):
            with self.subTest(key=key):
                candidate = copy.deepcopy(patch)
                candidate["items"][0][key] = value
                self.assertTrue(list(validator.iter_errors(candidate)))
        patch["base_analysis_revision"] = True
        self.assertTrue(list(validator.iter_errors(patch)))


if __name__ == "__main__":
    unittest.main()

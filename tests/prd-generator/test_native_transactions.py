"""在原生文件系统上回归分析事务恢复和 PRD 只读快照写入，可单独以 Python -I 运行。"""

import base64
import importlib.util
import json
from pathlib import Path, PureWindowsPath
import stat
import tempfile
import unittest
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skill"


def _load_script(relative_path):
    """从仓库内的相对脚本路径加载生产模块；路径及导入错误原样抛出。"""
    path = SKILL_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(f"native_test_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _completion_checks(question_ref):
    """返回补丁规定的十一项待确认检查，均关联指定的问题；不读取业务数据。"""
    return [
        {"item": item, "satisfied": False, "question_refs": [question_ref], "reason": "范围待确认"}
        for item in range(1, 12)
    ]


def _allow_temp_cleanup(directory):
    """只恢复测试临时目录内文件的写权限，以便 Windows 删除；权限错误原样抛出。"""
    for path in directory.rglob('*'):
        if not path.is_symlink() and path.is_file():
            mode = path.stat().st_mode
            if not mode & stat.S_IWUSR:
                _load_script('requirement-analyst/scripts/portable_fs.py').set_snapshot_readonly(path, False)


class NativeTransactionTests(unittest.TestCase):
    """覆盖真实事务日志及独占只读写入的跨平台文件系统边界。"""

    def setUp(self):
        """为当前测试分配独立临时目录并登记清理；创建失败由 unittest 报告。"""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_replays_legacy_backslash_journal_after_partial_event_append(self):
        """恢复旧 Windows 日志中的半条事件，重复重放不追加事件，也不覆盖 common。"""
        updater = _load_script("requirement-analyst/scripts/update_analysis.py")
        project = "project-a"
        requirement = "NATIVE-RECOVERY"
        initial = {
            "patch_version": "1.0", "requirement_id": requirement, "title": "事务回归",
            "base_revision": 0, "change_type": "initial_analysis", "actor": "analyst",
            "summary": "首次分析", "set": {}, "completion_checks": _completion_checks("$scope"),
            "operations": [{
                "op": "add", "collection": "questions", "ref": "$scope",
                "value": {
                    "question": "本期范围是什么？", "priority": "P0", "resolution": "ask_product",
                    "reason": "范围尚未确定", "impact": "无法验收", "status": "open",
                    "options": ["仅包含方案甲", "包含方案甲和乙", "其他", "暂不确定"],
                    "recommendation": "先确认方案甲", "related_ids": [],
                },
            }],
        }
        created = updater.update_analysis(self.root, project, initial)
        self.assertEqual(created["status"], "pass", created)
        self.assertTrue(created["written"], created)
        requirement_dir = self.root / "projects" / project / "requirements" / requirement
        analysis_path = requirement_dir / "analysis" / "analysis-result.json"
        event_path = analysis_path.with_name("analysis-events.jsonl")
        common_path = requirement_dir / "requirement.json"
        journal_path = self.root / ".analysis-transaction.json"
        prefix = event_path.read_bytes()
        supplement = {
            "patch_version": "1.0", "requirement_id": requirement, "base_revision": 1,
            "change_type": "supplement", "actor": "analyst", "summary": "补充范围信息",
            "operations": [], "set": {}, "completion_checks": _completion_checks("Q-1"),
        }

        real_open = Path.open
        interruption = "event append interrupted by test"

        def open_with_interruption(path, mode="r", *args, **kwargs):
            """返回原生文件流，仅给事件追加流注入一次部分写入错误。"""
            stream = real_open(path, mode, *args, **kwargs)
            if path == event_path and mode == "ab":
                write = stream.write

                def write_partial(raw):
                    """将待追加字节的前半写到磁盘，再抛出 OSError 模拟中断。"""
                    write(raw[:len(raw) // 2])
                    stream.flush()
                    raise OSError(interruption)

                stream.write = write_partial
            return stream

        # 在生产代码落盘待恢复日志后才打断追加，保留真实的前置状态与待写入字节。
        with patch.object(Path, "open", new=open_with_interruption):
            failed = updater.update_analysis(self.root, project, supplement)
        self.assertEqual(failed["status"], "fail", failed)
        self.assertIn(interruption, str(failed["diagnostics"]))
        journal = json.loads(journal_path.read_bytes())
        for entry in journal["writes"]:
            entry["path"] = entry["path"].replace("/", "\\")
        event_entry = next(entry for entry in journal["writes"] if PureWindowsPath(entry["path"]).name == event_path.name)
        self.assertIn("\\", event_entry["path"])
        self.assertEqual(base64.b64decode(event_entry["before"]), prefix)
        expected_events = base64.b64decode(event_entry["after"])
        partial_events = event_path.read_bytes()
        self.assertTrue(partial_events.startswith(prefix))
        self.assertTrue(expected_events.startswith(partial_events))
        self.assertLess(len(prefix), len(partial_events))
        self.assertLess(len(partial_events), len(expected_events))
        legacy_journal = json.dumps(journal, ensure_ascii=False).encode("utf-8")

        # 用户可能在中断后编辑共用记录；恢复不得以事务候选覆盖这份新内容。
        common = json.loads(common_path.read_bytes())
        common["common"]["title"] = "用户修改的标题"
        common["prd"] = {"version": "0.1", "status": "draft"}
        user_common = json.dumps(common, ensure_ascii=False, indent=3).encode("utf-8")
        common_path.write_bytes(user_common)

        for state in ("partial event", "complete event"):
            # 第二次放回同一日志，模拟事件已写完但完成标记尚未持久化。
            journal_path.write_bytes(legacy_journal)
            response = updater.update_analysis(self.root, project, supplement)
            self.assertEqual(response["status"], "fail", (state, response))
            self.assertIn("/base_revision", [item["path"] for item in response["diagnostics"]], (state, response))
            self.assertIsNone(json.loads(journal_path.read_bytes()), state)
            events = event_path.read_bytes()
            self.assertEqual(events, expected_events, state)
            self.assertEqual([json.loads(line)["revision"] for line in events.splitlines()], [1, 2], state)
            self.assertEqual(json.loads(analysis_path.read_bytes())["meta"]["analysis_revision"], 2, state)
            self.assertEqual(common_path.read_bytes(), user_common, state)

    def test_atomic_write_creates_readonly_snapshot(self):
        """真实新建的快照字节正确且无写位，成功后只保留正式文件名。"""
        writer = _load_script("prd-generator/scripts/write_draft.py")
        self.addCleanup(_allow_temp_cleanup, self.root)
        target = self.root / "prd/versions/prd-1.0.md"
        target.parent.mkdir(parents=True)
        writer._atomic_write(target, b"released PRD\n", new_readonly=True)
        self.assertEqual(target.read_bytes(), b"released PRD\n")
        # 用文件属性而非写入探测：POSIX 的特权用户能绕过写位。
        self.assertEqual(target.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH), 0)
        self.assertEqual([path for path in self.root.rglob('*') if path.is_file()], [target])

    def test_atomic_write_collision_preserves_existing_snapshot_and_cleans_temp(self):
        """同名发布失败不覆盖现有文件，也不留下任何临时名（包括只读临时名）。"""
        writer = _load_script("prd-generator/scripts/write_draft.py")
        self.addCleanup(_allow_temp_cleanup, self.root)
        target = self.root / "prd/versions/prd-1.0.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing PRD\n")
        with self.assertRaises(FileExistsError):
            writer._atomic_write(target, b"competing PRD\n", new_readonly=True)
        self.assertEqual(target.read_bytes(), b"existing PRD\n")
        self.assertEqual([path for path in self.root.rglob('*') if path.is_file()], [target])


if __name__ == "__main__":
    unittest.main()

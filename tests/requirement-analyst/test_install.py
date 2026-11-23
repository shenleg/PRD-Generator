"""验证双 Skill 安装器的目标路径、解释器选择和失败回滚；测试不联网。"""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("skill_installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    """使用独立项目验证安装行为，只替换 Python 子进程。"""

    def setUp(self) -> None:
        """创建测试项目及其目标路径；无返回，无法创建时将 OSError 交给测试框架。"""
        temporary = tempfile.TemporaryDirectory(prefix="prd-skills-")
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name).resolve() / "目标 project"
        self.project.mkdir()
        self.claude = self.project / ".claude"
        self.skills = self.claude / "skills"
        self.environment = self.claude / ".prd-skills-venv"

    def _run(self) -> tuple[int, str]:
        """调用安装入口并捕获输出；返回退出码和输出，未处理的异常使测试失败。"""
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            code = installer.main([str(self.project)])
        return code, output.getvalue()

    def test_installs_both_skills_and_dependencies_in_project(self) -> None:
        """依赖装到虚拟环境而非系统 Python，项目路径有空格也只作为一个参数。"""
        with patch.dict(os.environ, {'PIP_FIND_LINKS': 'https://example.invalid/wheels/',
                                     'PIP_REQUIREMENT': 'https://example.invalid/extra.txt',
                                     'PIP_CONFIG_FILE': 'foreign.conf'}), patch.object(installer.subprocess, "run") as run:
            code, output = self._run()

        python = self.environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        self.assertEqual(code, 0, output)
        self.assertIn(str(python), output)
        calls = [call.args[0] for call in run.call_args_list]
        self.assertEqual(calls[0], [sys.executable, "-I", "-m", "venv", str(self.environment)])
        self.assertEqual(calls[1], [str(python), '-I', '-m', 'pip', '--isolated', '--disable-pip-version-check',
                                    '--no-cache-dir', '--require-virtualenv', 'install', '--no-index',
                                    '--only-binary=:all:', '--require-hashes', '--find-links',
                                    (ROOT / 'offline/wheels').as_uri(), '-r', str(ROOT / 'offline/requirements.lock')])
        env = run.call_args_list[1].kwargs['env']
        self.assertEqual({k: v for k, v in env.items() if k.upper().startswith('PIP_')}, {'PIP_CONFIG_FILE': os.devnull})
        self.assertEqual(calls[2][:3], [str(python), "-I", "-c"])
        self.assertEqual(calls[3:], [[str(python), "-I", "-B", str(self.skills / skill / "scripts" / entry), "--help"]
                                     for skill, entry in (("requirement-analyst", "update_analysis.py"),
                                                          ("prd-generator", "write_draft.py"))])
        self.assertEqual({path.name for path in self.skills.iterdir()}, {"requirement-analyst", "prd-generator"})
        self.assertTrue((self.skills / "requirement-analyst/scripts/update_analysis.py").is_file())
        self.assertTrue((self.skills / "prd-generator/scripts/check_gate.py").is_file())
        self.assertIn("*", (self.environment / ".gitignore").read_text(encoding="utf-8").splitlines())

    def test_offline_payload_is_complete(self) -> None:
        """仓库里每个实际 wheel 与锁的 SHA-256 一一对应，各目标 Python/架构均有可选原生包。"""
        offline = ROOT / 'offline'
        wheels = list((offline / 'wheels').glob('*.whl'))
        lock = (offline / 'requirements.lock').read_text(encoding='utf-8')
        direct = (ROOT / 'skill/requirement-analyst/scripts/requirements.txt').read_text(encoding='utf-8').splitlines()
        pins = {line.split()[0] for line in lock.splitlines() if line and line[0].isalnum()}
        self.assertTrue({line for line in direct if line and not line.startswith('#')} <= pins)
        hashes = re.findall(r'--hash=sha256:([a-f0-9]{64})', lock)
        self.assertCountEqual(hashes, [hashlib.sha256(w.read_bytes()).hexdigest() for w in wheels])
        self.assertFalse(any('musllinux' in w.name for w in wheels), '公开包不得含附带独立 libgcc_s 的 musllinux wheel')
        platforms = ('win32', 'win_amd64', 'win_arm64', 'macosx_10_12_x86_64', 'macosx_11_0_arm64',
                     'manylinux_2_17_aarch64.manylinux2014_aarch64', 'manylinux_2_17_x86_64.manylinux2014_x86_64')
        for m in range(10, 16):
            for platform in platforms:
                if m == 10 and platform == 'win_arm64':
                    continue  # 上游未发布该组合，不在离线支持范围内。
                tag = f'-cp3{m}-cp3{m}-{platform}.whl'
                self.assertTrue(any(w.name.startswith('rpds_py-') and w.name.endswith(tag) for w in wheels), tag)

    def test_missing_bundle_fails_before_venv_creation(self) -> None:
        """只复制 Skill 而漏带 offline/ 时给出离线提示，不调用 pip，也不创建半成品。"""
        with patch.object(installer, '_OFFLINE', self.project / 'missing'), patch.object(installer.subprocess, 'run') as run:
            code, output = self._run()
        self.assertEqual(code, 1)
        self.assertIn('缺少离线依赖', output)
        run.assert_not_called()
        self.assertFalse(self.claude.exists())

    def test_does_not_overwrite_an_existing_skill(self) -> None:
        """任何同名目标都在准备依赖前拒绝，保留现有 Skill 并避免只安装一半。"""
        original = self.skills / "prd-generator/SKILL.md"
        original.parent.mkdir(parents=True)
        original.write_text("existing", encoding="utf-8")
        with patch.object(installer.subprocess, "run") as run:
            code, output = self._run()

        self.assertEqual(code, 1)
        self.assertIn("未覆盖", output)
        run.assert_not_called()
        self.assertEqual(original.read_text(encoding="utf-8"), "existing")
        self.assertFalse(self.environment.exists())
        self.assertFalse((self.skills / "requirement-analyst").exists())

    def test_pip_failure_leaves_no_partial_install(self) -> None:
        """pip 失败后不发布 Skill，并清理仅由本次创建的虚拟环境。"""
        failure = subprocess.CalledProcessError(1, ["pip"])
        with patch.object(installer.subprocess, "run", side_effect=[None, failure]):
            code, output = self._run()

        self.assertEqual(code, 1)
        self.assertIn("无法在虚拟环境安装或加载依赖", output)
        self.assertFalse(self.environment.exists())
        self.assertEqual(list(self.skills.iterdir()), [])

    def test_copy_failure_rolls_back_only_new_targets(self) -> None:
        """第二个 Skill 复制失败时，原有的其他 Skill 不受回滚影响。"""
        existing = self.skills / "other-skill"
        existing.mkdir(parents=True)
        copytree = shutil.copytree

        def fail_prd_copy(source: Path, target: Path, *args, **kwargs) -> Path:
            """复制指定目录并返回目标；测试主入口复制 PRD 时模拟 OSError。"""
            if Path(source) == ROOT / "skill/prd-generator":
                raise OSError("复制失败")
            return copytree(source, target, *args, **kwargs)

        with patch.object(installer.subprocess, "run"), patch.object(installer.shutil, "copytree", side_effect=fail_prd_copy):
            code, output = self._run()

        self.assertEqual(code, 1)
        self.assertIn("复制失败", output)
        self.assertFalse(self.environment.exists())
        self.assertEqual(list(self.skills.iterdir()), [existing])

    def test_python_version_is_checked_before_installing(self) -> None:
        """低于 3.10 的解释器提示版本要求且不写入目标。"""
        output = io.StringIO()
        with patch.object(installer.sys, "version_info", (3, 9)), redirect_stderr(output):
            with self.assertRaises(SystemExit) as error:
                installer.main([str(self.project)])

        self.assertEqual(error.exception.code, 2)
        self.assertIn("Python 3.10", output.getvalue())
        self.assertFalse(self.claude.exists())


if __name__ == "__main__":
    unittest.main()

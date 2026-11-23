"""将两个需求协作 Skill 和共用 Python 依赖安装到指定项目。"""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import shutil
import subprocess
import sys


_SKILL_NAMES = ("requirement-analyst", "prd-generator")
_ENV_NAME = ".prd-skills-venv"
_ROOT = Path(__file__).resolve().parent
_SOURCE = _ROOT / "skill"
_OFFLINE = _ROOT / "offline"


def _prepare_environment(environment: Path) -> Path:
    try:
        subprocess.run([sys.executable, "-I", "-m", "venv", str(environment)], check=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError("无法创建虚拟环境。请确认当前 Python 支持 venv 和 ensurepip；部分 Linux 发行版需安装对应的 venv 系统包。") from error

    # Python 3.13 之前的 venv 不会生成 .gitignore，依赖不应被目标项目提交。
    ignore = environment / ".gitignore"
    if not ignore.exists():
        ignore.write_text("# Python 虚拟环境，在各机器上分别安装。\n*\n", encoding="utf-8")

    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    # --no-index 不会屏蔽用户配置的远程 find-links；同时忽略 pip 配置、环境覆盖和缓存。
    pip_env = {key: value for key, value in os.environ.items() if not key.upper().startswith('PIP_')}
    pip_env['PIP_CONFIG_FILE'] = os.devnull
    try:
        subprocess.run(
            [str(python), '-I', '-m', 'pip', '--isolated', '--disable-pip-version-check', '--no-cache-dir',
             '--require-virtualenv', 'install', '--no-index', '--only-binary=:all:', '--require-hashes',
             '--find-links', (_OFFLINE / 'wheels').as_uri(), '-r', str(_OFFLINE / 'requirements.lock')],
            env=pip_env, check=True,
        )
        subprocess.run([str(python), '-I', '-c',
                        'from jsonschema import FormatChecker; import referencing; FormatChecker(formats=["date-time"])'],
                       check=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError('无法在虚拟环境安装或加载依赖：请核对 offline/ 文件完整性及当前 Python 版本和架构。不会回退到联网安装。') from error
    return python


def _install(project: Path) -> Path:
    project = project.resolve(strict=True)
    if not project.is_dir():
        raise ValueError(f"目标项目必须是已存在的目录：{project}")

    claude = project / ".claude"
    skills = claude / "skills"
    environment = claude / _ENV_NAME
    targets = [skills / name for name in _SKILL_NAMES]
    occupied = [str(path) for path in (*targets, environment) if path.exists() or path.is_symlink()]
    if occupied:
        raise FileExistsError("目标已存在，未覆盖：" + "、".join(occupied))

    sources = [_SOURCE / name for name in _SKILL_NAMES]
    if any(not (source / "SKILL.md").is_file() for source in sources):
        raise FileNotFoundError("安装载荷不完整，请从完整仓库运行 install.py。")
    if not (_OFFLINE / 'requirements.lock').is_file() or not any((_OFFLINE / 'wheels').glob('*.whl')):
        raise FileNotFoundError('缺少离线依赖，请将完整 offline/ 目录与 install.py 一起复制，不会从公网下载。')

    skills.mkdir(parents=True, exist_ok=True)
    with ExitStack() as rollback:
        # 只回滚此次成功新建的目录；已存在或被先行创建的同名目录不归本次安装。
        environment.mkdir()
        rollback.callback(shutil.rmtree, environment)
        python = _prepare_environment(environment)
        ignore = shutil.ignore_patterns("__pycache__", "*.py[co]")
        for source, target in zip(sources, targets):
            target.mkdir()
            rollback.callback(shutil.rmtree, target)
            shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore)
        # 从复制后的目录检查业务入口，而不是仅确认 pip 成功；--help 不读写业务数据。
        try:
            for target, entry in zip(targets, ("update_analysis.py", "write_draft.py")):
                subprocess.run([str(python), "-I", "-B", str(target / "scripts" / entry), "--help"],
                               stdout=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError as error:
            raise RuntimeError("已安装的 Skill 脚本无法启动，请查看上方 Python 错误。") from error
        rollback.pop_all()
    return python


def main(argv: list[str] | None = None) -> int:
    """安装双 Skill。argv 为命令行参数；返回 0 表示成功，1 表示安装失败。

    参数或 Python 版本不符合要求时，argparse 以 SystemExit(2) 结束。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", metavar="PROJECT", type=Path, help="已有的目标项目目录")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 10):
        parser.error("需要 Python 3.10 或更新版本。")
    try:
        python = _install(args.project)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"安装失败：{error}", file=sys.stderr)
        return 1

    print(f"两个 Skill 已安装。脚本解释器：{python}")
    print("请在目标项目目录开启新的 Claude Code 会话。")
    return 0


if __name__ == "__main__":
    # Windows 重定向到日志时可能使用非 Unicode 代码页，中文项目路径仍需可读。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())

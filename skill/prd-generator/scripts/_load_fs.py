"""从并列安装的分析 Skill 加载同一个文件系统接口，确保两侧对需求互斥规则理解一致。"""

import importlib.util
from pathlib import Path

_source = Path(__file__).resolve().parents[2] / "requirement-analyst/scripts/portable_fs.py"
_spec = importlib.util.spec_from_file_location("skill_portable_fs", _source)
fs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fs)

"""按安装位置加载共享文件系统接口，不要求调用者将 Skill 加入 Python 搜索路径。"""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("skill_portable_fs", Path(__file__).with_name("portable_fs.py"))
fs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fs)

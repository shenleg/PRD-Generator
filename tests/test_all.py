"""统一发现按 Skill 分组的测试，兼容原来的 unittest discover 命令。"""

from pathlib import Path
import unittest


GROUPS = ("requirement-analyst", "prd-generator")


def load_tests(loader, standard_tests, pattern):
    """汇总各 Skill 的测试并返回完整套件，不复用 discovery 的目录状态。

    loader 和 standard_tests 来自 unittest；pattern 是调用方的文件模式。
    每组用独立发现器，让同组辅助模块正常导入；导入失败保留为失败测试，不静默跳过。
    """
    suite = unittest.TestSuite()
    base = Path(__file__).resolve().parent
    for name in GROUPS:
        suite.addTests(unittest.TestLoader().discover(str(base / name), pattern=pattern or "test_*.py"))
    return suite

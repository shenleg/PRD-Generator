"""将历史清单中的已迁移资料定位到当前文件，不改证据标识或回退历史副本。"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
# 使用逐文件迁移表而非通配重定位，避免误改生成侧资料或未知历史路径。
MATERIAL_PATHS = {
    entry["from"]: entry["to"]
    for entry in json.loads(
        (ROOT / "tests/results/repository-layout/test-materials/migration.json").read_text(encoding="utf-8")
    )["materials"]
}


def current_material_path(relative: str) -> Path:
    """返回仓库相对路径 relative 对应的当前位置；未迁移路径保持原义。

    只解析位置，不检查或修复内容；调用方必须读取当前字节并核对原哈希。
    绝对路径或父目录越界抛 ValueError，目标缺失由调用方读取时抛出文件异常，
    不尝试旧路径或 Git 历史副本。
    """
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("资料必须是仓库内相对路径")
    return ROOT / MATERIAL_PATHS.get(relative, relative)

"""读取历史试跑实际使用的源码；旧指纹绑定历史版本，不用修改哈希伪装新行为通过。"""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def recorded_bytes(relative: str, stage: int) -> bytes:
    """返回 relative 在指定 stage 试跑时的原字节，不读取当前生产副本。

    阶段2/3使用已提交完成标签；阶段4使用收口前逐份核对原指纹后保存的快照。
    路径须为仓库相对路径；未知阶段、越界路径或缺证据直接抛出，不回退当前源码。
    """
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("历史源码必须是仓库内相对路径")
    if stage in (2, 3):
        return subprocess.run(["git", "show", f"stage-{stage}-complete:{relative}"], cwd=ROOT, check=True, capture_output=True).stdout
    if stage == 4:
        return (ROOT / "workspace-sandbox/stage-4/source-snapshots/pre-install" / path).read_bytes()
    raise ValueError(f"没有阶段{stage}的历史源码约定")

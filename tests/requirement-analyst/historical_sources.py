"""读取历史试跑实际使用的源码；旧指纹绑定历史版本，不用修改哈希伪装新行为通过。"""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def recorded_bytes(relative: str, stage: int | str, *, installed: bool = False) -> bytes:
    """返回 relative 在指定 stage 试跑时的原字节，不读取当前生产副本。

    阶段2/3使用已提交验收版本1d20342/cb28316，不依赖克隆时未携带的本地标签；
    阶段4默认使用收口前逐份核对原指纹后保存的快照。
    installed=True仅用于阶段4实际安装烟测，读取其已提交收口版本3ddb876，而非更早快照。
    阶段5/6/7分别绑定已提交验收版本cbb2938/6fcf4bb/6325078；阶段8绑定be0f8ba，
    final绑定adb9706。封存证据的源码均绑定当时提交，现行生产源码由公开驱动的新重放验证。
    后续新能力另有实际证据，不改旧哈希冒充重跑。
    路径须为仓库相对路径；未知阶段、越界路径或缺证据直接抛出，不回退当前源码。
    """
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("历史源码必须是仓库内相对路径")
    if stage in (2, 3):
        commit = "1d20342" if stage == 2 else "cb28316"
        return subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=ROOT, check=True, capture_output=True).stdout
    if stage in (8, "final"):
        commit = "be0f8ba" if stage == 8 else "adb9706"
        return subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=ROOT, check=True, capture_output=True).stdout
    if stage == 7:
        return subprocess.run(["git", "show", f"632507840e6d187148c0ef1c260675201de994ee:{relative}"], cwd=ROOT, check=True, capture_output=True).stdout
    if stage == 6:
        return subprocess.run(["git", "show", f"6fcf4bbecb5332f699689fd3884b9d0c4176bad6:{relative}"], cwd=ROOT, check=True, capture_output=True).stdout
    if stage == 5:
        return subprocess.run(["git", "show", f"cbb293833a0a0f53fd50c1dc11c82e0d2e493cd3:{relative}"], cwd=ROOT, check=True, capture_output=True).stdout
    if stage == 4 and installed:
        return subprocess.run(["git", "show", f"3ddb8760110953a84b03590e138aa960c1af10ef:{relative}"], cwd=ROOT, check=True, capture_output=True).stdout
    if stage == 4:
        return (ROOT / "workspace-sandbox/stage-4/source-snapshots/pre-install" / path).read_bytes()
    raise ValueError(f"没有阶段{stage}的历史源码约定")

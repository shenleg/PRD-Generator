"""维护者在联网机器上重建离线 wheel 包和 pip 哈希锁；不会安装或执行下载的包。"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from urllib.request import urlopen


# 每个条目对应一条完整锁定的 pip requirement。3.10 需保留仍支持它的 rpds-py。
_RELEASES = (
    ('attrs', '26.1.0', ''), ('jsonschema', '4.26.0', ''),
    ('jsonschema-specifications', '2025.9.1', ''), ('referencing', '0.37.0', ''),
    ('rfc3339-validator', '0.1.4', ''), ('six', '1.17.0', ''),
    ('typing-extensions', '4.16.0', 'python_version < "3.13"'),
    ('rpds-py', '0.30.0', 'python_version == "3.10"'),
    ('rpds-py', '2026.9.1', 'python_version >= "3.11"'),
)
_PLATFORMS = ('win32', 'win_amd64', 'win_arm64', 'macosx_10_12_x86_64', 'macosx_11_0_arm64',
              'manylinux_2_17_x86_64.manylinux2014_x86_64', 'manylinux_2_17_aarch64.manylinux2014_aarch64')
# 公开仓库不收录附带独立 libgcc_s 的 musllinux wheel，避免分发尚未配齐对应源码的运行库。
_TIMEOUT = 45  # 外部下载超时应中止构建，不发布缺少 wheel 的锁文件。


def _release_files(name, version):
    with urlopen(f'https://pypi.org/pypi/{name}/{version}/json', timeout=_TIMEOUT) as stream:
        release = json.load(stream)
    files = [f for f in release['urls'] if f['packagetype'] == 'bdist_wheel' and not f['yanked']]
    if name == 'rpds-py':
        # 显式枚举目标，不能因 PyPI 少一个平台而静默生成不完整的离线包。
        minors = (10,) if version == '0.30.0' else range(11, 16)
        names = {f'rpds_py-{version}-cp3{m}-cp3{m}-{p}.whl' for m in minors for p in _PLATFORMS
                 if (m, p) != (10, 'win_arm64')}
        files = [f for f in files if f['filename'] in names]
        if names != {f['filename'] for f in files}:
            raise ValueError(f'{name} {version} 缺少预期的目标平台 wheel')
    elif len(files) != 1 or not files[0]['filename'].endswith('-none-any.whl'):
        raise ValueError(f'{name} {version} 不再是单一的通用 wheel，请重新评估平台列表')
    return sorted(files, key=lambda f: f['filename'])


def _download(file, wheels):
    name, url = file['filename'], file['url']
    if not url.startswith('https://files.pythonhosted.org/') or Path(name).name != name:
        raise ValueError(f'不是 PyPI 发布的普通 wheel 文件：{name}')
    # 每个下载在独立空目录暂存；未经校验的文件不进入分发目录。
    with tempfile.TemporaryDirectory(dir=wheels.parent) as temporary:
        stage = Path(temporary) / name
        with urlopen(url, timeout=_TIMEOUT) as response:
            data = response.read()
        if len(data) != file['size'] or sha256(data).hexdigest() != file['digests']['sha256']:
            raise ValueError(f'上游 SHA-256 或大小不符：{name}')
        stage.write_bytes(data)
        stage.rename(wheels / name)


def main(argv=None):
    """按 argv 指定的新目录准备分发文件，成功返回 0；参数错误退出，网络、校验及文件错误透传。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='用于生成 wheels/ 和 requirements.lock 的新目录，不覆盖旧包')
    destination = parser.parse_args(argv).output
    destination.mkdir(parents=True, exist_ok=False)
    wheels = destination / 'wheels'
    wheels.mkdir()
    lines = ['# pip 哈希锁，由 tools/prepare_offline_wheels.py 从固定版本的 PyPI 元数据生成。']
    with ThreadPoolExecutor(max_workers=6) as pool:
        for name, version, marker in _RELEASES:
            files = _release_files(name, version)
            list(pool.map(lambda file: _download(file, wheels), files))
            requirement = f'{name}=={version}' + (f' ; {marker}' if marker else '')
            lines.append(' \\\n    '.join([requirement, *('--hash=sha256:' + f['digests']['sha256'] for f in files)]))
    (destination / 'requirements.lock').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    print(f'已准备 {len(list(wheels.glob("*.whl")))} 个 wheel：{destination}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

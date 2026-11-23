"""跨平台验证本地锁的进程语义、受管路径和二进制文件访问。"""

from contextlib import ExitStack, contextmanager
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]


def _load(skill):
    """从 skill 的生产入口加载文件接口并返回；载荷缺失或损坏时传播导入错误。"""
    source = ROOT / 'skill' / skill / 'scripts/_load_fs.py'
    spec = importlib.util.spec_from_file_location('lock_test_' + skill, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fs


FS = _load('requirement-analyst')


def _worker(root, kind, hold):
    """在 root 申请 kind 对应的锁；hold 为真时持锁直到被终止。失败传播异常。"""
    fs = _load('prd-generator')
    (root / 'started').touch()
    lock = fs.requirement_lock(root) if kind == 'requirement' else fs.workspace_lock(root / '.analysis.lock')
    with lock:
        (root / 'acquired').touch()
        if hold:
            sys.stdin.buffer.read(1)


@contextmanager
def _child(root, kind, hold=False):
    """以另一解释器进程在 root 独立获取 kind 锁；返回进程对象；不可启动时抛 OSError。"""
    with subprocess.Popen([sys.executable, '-I', '-B', __file__, '--worker', str(root), kind, str(int(hold))],
                          stdin=subprocess.PIPE) as process:
        try:
            yield process
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=15)


def _wait_for(path, process):
    """等待子进程生成 path 同步两侧，不依赖启动速度；进程提前退出或超时抛异常。"""
    deadline = time.monotonic() + 15
    while not path.exists():
        if process.poll() is not None or time.monotonic() >= deadline:
            raise AssertionError(f'子进程未完成同步：{path.name}')
        time.sleep(0.01)


class PortableFilesystemTests(unittest.TestCase):
    """通过真实文件描述符及子进程验证三平台共用的文件协议。"""

    def test_skills_wait_on_the_same_lock_and_abandoned_lock_is_released(self):
        """两端争用同一需求/工作区锁；持锁进程被杀后无需清理锁文件即可继续。"""
        for kind in ('requirement', 'workspace'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                lock = FS.requirement_lock(root) if kind == 'requirement' else FS.workspace_lock(root / '.analysis.lock')
                # 先锁后启动竞争者，避免子进程恰好先持锁并等待输入，使测试自身死锁。
                with ExitStack() as children:
                    with lock:
                        process = children.enter_context(_child(root, kind, hold=True))
                        _wait_for(root / 'started', process)
                        with self.assertRaises(subprocess.TimeoutExpired):
                            process.wait(timeout=0.15)
                        self.assertFalse((root / 'acquired').exists())
                    _wait_for(root / 'acquired', process)
                with _child(root, kind) as successor:
                    self.assertEqual(successor.wait(timeout=15), 0)

    def test_byte_reads_and_exclusive_create(self):
        """二进制访问逐字节保留 CRLF、0x1A，独占创建不会截断原文件。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / '中文 文档'
            with self.assertRaises(FileNotFoundError):
                FS.open_readonly(path)
            data = b'\r\n\x1a\xfe\n'
            with os.fdopen(FS.open_exclusive(path), 'wb') as stream:
                stream.write(data)
            with self.assertRaises(FileExistsError):
                FS.open_exclusive(path)
            with os.fdopen(FS.open_readonly(path), 'rb') as stream:
                self.assertEqual(stream.read(), data)
            FS.sync_directory(root)

    def test_names_and_collisions(self):
        """设备名和数据流不可作普通文件；跨平台比较保守识别等价 Unicode 及大小写。"""
        for name in ('..', 'AUX.md', 'com¹', 'w:stream', 'a/b', 'a\\b', 'ending. ', 'nul .md'):
            self.assertFalse(FS.is_portable_segment(name), name)
        self.assertTrue(FS.is_portable_segment('需求 10.2.md'))
        self.assertEqual(FS.path_key(Path('é') / 'Doc'), FS.path_key(Path('é') / 'doc'))

    @unittest.skipUnless(sys.platform == 'darwin', '使用 macOS 自带的 /tmp 和 /var 别名')
    def test_macos_tmp_alias_attaches_to_the_same_lock(self):
        """系统临时目录别名可使用；普通用户链接不会被当作系统别名放行。"""
        for base in (Path('/tmp'), Path('/var')):
            self.assertFalse(FS.is_link(base))
        with tempfile.TemporaryDirectory(dir='/tmp') as directory:
            root = Path(directory)
            alias = root / 'alias'
            alias.symlink_to(root, target_is_directory=True)
            self.assertTrue(FS.is_link(alias))
            with FS.requirement_lock(root):
                with _child(root.resolve(), 'requirement') as process:
                    _wait_for(root / 'started', process)
                    with self.assertRaises(subprocess.TimeoutExpired):
                        process.wait(timeout=0.15)
                    self.assertFalse((root / 'acquired').exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows junction 不需要创建符号链接特权')
    def test_windows_junction_is_a_link_not_a_requirement_directory(self):
        """拒绝把指向其他目录的 junction 作为需求锁目标。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'real').mkdir()
            subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', 'alias', 'real'], cwd=root,
                           stdout=subprocess.DEVNULL, check=True)
            self.assertTrue(FS.is_link(root / 'alias'))
            with self.assertRaises(OSError), FS.requirement_lock(root / 'alias'):
                self.fail('不应进入重解析点')
            self.assertEqual(list((root / 'real').iterdir()), [])


if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']:
        _worker(Path(sys.argv[2]), sys.argv[3], bool(int(sys.argv[4])))
    else:
        unittest.main()

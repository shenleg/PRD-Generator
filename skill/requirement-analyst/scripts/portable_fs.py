"""两个 Skill 共用的本地文件访问、进程互斥及目录同步；不改变业务事务协议。"""

from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat
import sys
import unicodedata

if os.name == "nt":
    import ctypes
    from ctypes import wintypes
    import msvcrt
    import time
else:
    import fcntl


def is_link(path: Path) -> bool:
    """判断 path 是否为应拒绝的链接或 Windows 重解析点；缺失返回 False，其他 I/O 错误透传。"""
    if os.name == "nt":
        # GetFileAttributesW 查询链接本身；Python lstat 对部分非名称替代型重解析点会继续解析。
        attributes = _get_attributes(str(path))
        if attributes == _INVALID_FILE_ATTRIBUTES:
            error = ctypes.WinError(ctypes.get_last_error())
            if isinstance(error, FileNotFoundError):
                return False
            raise error
        return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    # macOS 的系统临时目录和 TMPDIR 通常分别以 /tmp、/var 开头。仅放行已知根别名。
    if sys.platform == "darwin" and path in (Path("/tmp"), Path("/var")) and stat.S_ISLNK(info.st_mode):
        if path.parent / os.readlink(path) == Path("/private") / path.name:
            return False
    return stat.S_ISLNK(info.st_mode)


def path_key(path: Path) -> str:
    """返回 path 用于发现可能别名的保守比较键，不需要文件存在；不是打开文件或展示的路径。"""
    return unicodedata.normalize("NFC", os.path.abspath(path)).casefold()


def is_portable_segment(name: str) -> bool:
    """判断 name 是否可用作三平台通用的单一文件名；不读磁盘，无预期异常。"""
    if not name or name.endswith((".", " ")) or any(ord(c) < 32 or c in '<>:"/\\|?*' for c in name):
        return False
    # Win32 连带扩展名、上标串口号也识别为设备，而非项目内普通文件。
    stem = name.partition(".")[0].rstrip(" ").upper()
    return not (stem in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
                or (len(stem) == 4 and stem[:3] in {"COM", "LPT"} and stem[3] in "0123456789¹²³"))


if os.name == "nt":
    _kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    _get_attributes = _kernel.GetFileAttributesW
    _get_attributes.argtypes = (wintypes.LPCWSTR,)
    _get_attributes.restype = wintypes.DWORD
    _set_attributes = _kernel.SetFileAttributesW
    _set_attributes.argtypes = (wintypes.LPCWSTR, wintypes.DWORD)
    _set_attributes.restype = wintypes.BOOL
    _INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
    _lock_region = _kernel.LockFile
    _lock_region.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD)
    _lock_region.restype = wintypes.BOOL
    _LOCK_VIOLATION = 33  # ERROR_LOCK_VIOLATION；权限等其他错误不能无限重试。
    _create_file = _kernel.CreateFileW
    _create_file.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                             wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    _create_file.restype = wintypes.HANDLE
    _close = _kernel.CloseHandle
    _close.argtypes = (wintypes.HANDLE,)
    _close.restype = wintypes.BOOL

    class _AttributeTag(ctypes.Structure):
        """Win32 FILE_ATTRIBUTE_TAG_INFO，用已打开的句柄检查文件本身而非重新解析其名字。"""

        _fields_ = [("attributes", wintypes.DWORD), ("tag", wintypes.DWORD)]

    _file_info = _kernel.GetFileInformationByHandleEx
    _file_info.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    _file_info.restype = wintypes.BOOL
    _READ, _WRITE = 0x80000000, 0x40000000  # GENERIC_READ / GENERIC_WRITE
    _SHARE_READ_WRITE, _SHARE_DELETE = 3, 4  # FILE_SHARE_*；持锁期间禁止替换锁文件
    _OPEN_EXISTING, _OPEN_ALWAYS = 3, 4
    _OPEN_REPARSE_POINT = 0x00200000  # 打开最终路径段本身，不跟随链接
    _ATTRIBUTE_TAG_INFO_CLASS = 9  # FILE_INFO_BY_HANDLE_CLASS.FileAttributeTagInfo
    _LOCK_RETRY_SECONDS = 0.05  # 仅在其他进程持有相同字节区间时重试，退出即由内核释锁。

    def _windows_fd(path: Path, *, lock: bool) -> int:
        handle = _create_file(str(path), _READ | _WRITE if lock else _READ,
                              _SHARE_READ_WRITE if lock else _SHARE_READ_WRITE | _SHARE_DELETE, None,
                              _OPEN_ALWAYS if lock else _OPEN_EXISTING, _OPEN_REPARSE_POINT, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            info = _AttributeTag()
            if not _file_info(handle, _ATTRIBUTE_TAG_INFO_CLASS, ctypes.byref(info), ctypes.sizeof(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            if info.attributes & (stat.FILE_ATTRIBUTE_DIRECTORY | stat.FILE_ATTRIBUTE_REPARSE_POINT):
                raise OSError(errno.EINVAL, "需要非重解析点的普通文件", str(path))
            # 描述符接管句柄的所有权；传给 Python 二进制流时禁止 CRT 转换换行。
            return msvcrt.open_osfhandle(handle, os.O_BINARY | (os.O_RDWR if lock else os.O_RDONLY))
        except BaseException:
            _close(handle)
            raise


def open_readonly(path: Path) -> int:
    """不跟随最终路径的链接，返回普通文件的读描述符，由调用者关闭；缺失或类型不符抛 OSError。"""
    if os.name == "nt":
        fd = _windows_fd(path, lock=False)
    else:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, "需要普通文件", str(path))
        return fd
    except BaseException:
        os.close(fd)
        raise


def open_exclusive(path: Path, mode: int = 0o600) -> int:
    """按 mode 独占新建 path，返回需关闭的二进制写描述符；存在或无法创建时抛 OSError。"""
    return os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                   | getattr(os, "O_BINARY", 0), mode)


def set_snapshot_readonly(path: Path, readonly: bool) -> None:
    """对本次创建的快照临时文件 path 设置或清除只读属性；无返回值，权限或 I/O 错误透传。"""
    if os.name != "nt":
        path.chmod(0o444 if readonly else 0o600)
        return
    # 直接修改 DOS 属性，不以数据写权限打开已经只读的文件；保留其余属性。
    attributes = _get_attributes(str(path))
    if attributes == _INVALID_FILE_ATTRIBUTES:
        raise ctypes.WinError(ctypes.get_last_error())
    attributes = attributes | stat.FILE_ATTRIBUTE_READONLY if readonly else attributes & ~stat.FILE_ATTRIBUTE_READONLY
    if not _set_attributes(str(path), attributes or stat.FILE_ATTRIBUTE_NORMAL):
        raise ctypes.WinError(ctypes.get_last_error())


def sync_directory(directory: Path) -> None:
    """同步 directory 的目录项；Windows 和不支持目录刷盘的 Darwin 卷跳过，其余失败抛 OSError。"""
    if os.name == "nt":
        # Windows 的普通用户没有可移植的目录 fsync；文件已刷盘，进程中断仍由事务日志恢复。
        return
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    except OSError as error:
        # Darwin 的部分本地卷不提供目录刷盘；同 Windows，仅保留进程中断恢复语义。
        # EIO 等真正的介质故障仍须中止事务，不能一概当作不支持。
        if sys.platform != 'darwin' or error.errno not in (errno.EINVAL, errno.ENOTSUP):
            raise
    finally:
        os.close(fd)


@contextmanager
def workspace_lock(lock_path: Path):
    """在 lock_path 上取得独占锁，持有至上下文结束；无返回值，打开或锁定失败抛 OSError。"""
    if os.name == "nt":
        fd = _windows_fd(lock_path, lock=True)
    else:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, "锁路径必须是普通文件", str(lock_path))
        if os.name == "nt":
            # 固定锁第 0 字节；区域可越过 EOF，无需写入或截断锁文件。不要删除锁文件，
            # 否则后到者可能打开新文件，和仍持有旧文件句柄的进程错用两把锁。
            handle = msvcrt.get_osfhandle(fd)
            while not _lock_region(handle, 0, 0, 1, 0):
                error = ctypes.get_last_error()
                if error != _LOCK_VIOLATION:
                    raise ctypes.WinError(error)
                time.sleep(_LOCK_RETRY_SECONDS)
        else:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


@contextmanager
def requirement_lock(directory: Path):
    """独占已有需求目录，供两个 Skill 的提交和恢复共用；无返回值，路径或锁不可用抛 OSError。"""
    if is_link(directory):
        raise OSError(errno.EINVAL, "需求目录不能是链接", str(directory))
    if os.name == "nt":
        with workspace_lock(directory / ".requirement.lock"):
            yield
        return
    # 保留 Unix 旧版本对目录本身的锁；滚动更新两侧时仍使用同一把锁。
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)

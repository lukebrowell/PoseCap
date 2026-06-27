"""Parent-process liveness checks for engine shutdown."""

import ctypes
import os
from collections.abc import Callable

ProcessProbe = Callable[[int], bool]


class ParentWatchdog:
    """Reports whether the parent process is still alive."""

    def __init__(self, parent_pid: int | None, *, probe: ProcessProbe | None = None) -> None:
        self._parent_pid = parent_pid
        self._probe = probe or _is_process_alive

    def alive(self) -> bool:
        if self._parent_pid is None:
            return True
        return self._probe(self._parent_pid)


def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        return _is_process_alive_windows(pid)
    return _is_process_alive_posix(pid)


def _is_process_alive_posix(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _is_process_alive_windows(pid: int) -> bool:
    synchronize = 0x00100000
    wait_timeout = 0x00000102
    handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
    if not handle:
        return False
    try:
        return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) == wait_timeout
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)

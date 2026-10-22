"""Find the user's Downloads folder on Windows, macOS, and Linux."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def default_downloads_dir() -> Path:
    """Return the Downloads directory without requiring that it exists.

    Windows uses the Known Folder API when it is available, so a redirected
    Downloads folder is honored. Linux and macOS honor ``XDG_DOWNLOAD_DIR``
    from ``user-dirs.dirs`` and otherwise use ``~/Downloads``.
    """
    windows = _windows_downloads()
    if windows is not None:
        return windows
    xdg = _xdg_downloads()
    if xdg is not None:
        return xdg
    return Path.home() / "Downloads"


def _xdg_downloads() -> Path | None:
    path = _user_dirs_file()
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("XDG_DOWNLOAD_DIR"):
            continue
        key, separator, value = line.partition("=")
        if separator != "=" or key.strip() != "XDG_DOWNLOAD_DIR":
            continue
        return _expand_xdg_value(value.strip())
    return None


def _user_dirs_file() -> Path:
    if os.environ.get("XDG_CONFIG_HOME"):
        base = Path(os.environ["XDG_CONFIG_HOME"]).expanduser()
    else:
        base = Path.home() / ".config"
    return base / "user-dirs.dirs"


def _expand_xdg_value(value: str) -> Path:
    value = value.strip()
    if value[:1] in "\"'":
        quote = value[0]
        end = value.find(quote, 1)
        if end != -1:
            value = value[1:end]
        else:
            value = value[1:]
    else:
        value = value.split("#", 1)[0].strip()
    home = str(Path.home())
    value = value.replace("${HOME}", home).replace("$HOME", home)
    return Path(value).expanduser()


def _windows_downloads() -> Path | None:
    """Return the Windows Downloads Known Folder, or None off Windows."""
    if os.name != "nt" or sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:  # pragma: no cover - Windows stdlib always has ctypes
        return None

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    # FOLDERID_Downloads {374DE290-123F-4565-9164-39C4925E467B}
    folder_id = GUID(
        0x374DE290,
        0x123F,
        0x4565,
        (wintypes.BYTE * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B),
    )
    try:
        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32
        output = ctypes.c_wchar_p()
        result = shell32.SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(output))
    except (AttributeError, OSError, ValueError):  # pragma: no cover - Windows only
        return None
    if result != 0 or not output.value:  # pragma: no cover - Windows only
        return None
    path = Path(output.value)
    try:
        ole32.CoTaskMemFree(output)
    except (AttributeError, OSError):  # pragma: no cover - best effort
        pass
    return path

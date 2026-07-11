"""Single source of PEAR Root resolution, shared across the addon.

The panel's model-detection, the engine launcher, and the model-setup
operators each resolved the PEAR checkout their own way — and the model-setup
copy lacked the installer-default fallback, so the setup wizard failed
"Set the PEAR Root first" on a clean install even though the engine could find
it. One resolver owns the order now; there is no second place for it to drift.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

# Mirrors engine POSECAP_PEAR_ROOT_ENV; the addon must not import posecap_engine.
POSECAP_PEAR_ROOT_ENV = "POSECAP_PEAR_ROOT"
# Default install layout (Inno {localappdata}\PoseCap): a fresh install works
# with nothing typed, and this even repairs installs made before this fallback.
INSTALLER_PEAR_SUBPATH = ("PoseCap", "pear")

PathExists = Callable[[Path], bool]


def resolve_pear_root(
    settings: Any,
    preferences: Any,
    env: dict[str, str],
    exists: PathExists,
) -> str:
    """Resolve the PEAR checkout, falling back so the user need not type a path.

    Order: explicit panel/preferences value, then the POSECAP_PEAR_ROOT env
    var, then the installer's default location. Empty only when none resolve.
    """
    explicit = first_nonempty(
        getattr(settings, "pear_root", ""),
        getattr(preferences, "pear_root", ""),
    )
    if explicit != "":
        return explicit
    env_root = env.get(POSECAP_PEAR_ROOT_ENV, "").strip()
    if env_root != "" and exists(Path(env_root)):
        return env_root
    installer_root = installer_path(env, INSTALLER_PEAR_SUBPATH)
    if installer_root is not None and exists(installer_root):
        return str(installer_root)
    return ""


def installer_path(env: dict[str, str], subpath: tuple[str, ...]) -> Path | None:
    """The default install location for a subpath under %LOCALAPPDATA%."""
    local_app_data = env.get("LOCALAPPDATA", "").strip()
    if local_app_data == "":
        return None
    return Path(local_app_data, *subpath)


def first_nonempty(*values: object) -> str:
    """The first value that is non-empty once stringified and stripped."""
    for value in values:
        text = str(value).strip()
        if text != "":
            return text
    return ""

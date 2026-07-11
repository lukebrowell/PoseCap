"""Behavior tests for the single shared PEAR Root resolver.

Three call sites resolved PEAR Root three different ways; the model-setup copy
lacked the installer-default fallback, so the wizard failed "Set the PEAR Root
first" on a clean install even though the engine could find it. One resolver
now owns the order: explicit value -> env var -> installer default -> empty.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from posecap_addon.pear_root import POSECAP_PEAR_ROOT_ENV, resolve_pear_root


def _settings(pear_root: str = "") -> SimpleNamespace:
    return SimpleNamespace(pear_root=pear_root)


def _preferences(pear_root: str = "") -> SimpleNamespace:
    return SimpleNamespace(pear_root=pear_root)


def test_explicit_scene_value_wins_over_every_fallback() -> None:
    resolved = resolve_pear_root(
        _settings("E:/typed/pear"),
        _preferences(""),
        {POSECAP_PEAR_ROOT_ENV: "D:/env", "LOCALAPPDATA": "C:/Users/x/AppData/Local"},
        lambda _path: True,
    )

    assert resolved == "E:/typed/pear"


def test_preferences_value_used_when_scene_is_empty() -> None:
    resolved = resolve_pear_root(
        _settings(""),
        _preferences("F:/pref/pear"),
        {},
        lambda _path: False,
    )

    assert resolved == "F:/pref/pear"


def test_env_var_used_when_nothing_typed_and_it_exists() -> None:
    env_root = "D:/pear-checkout"
    resolved = resolve_pear_root(
        _settings(""),
        _preferences(""),
        {POSECAP_PEAR_ROOT_ENV: env_root},
        {Path(env_root)}.__contains__,
    )

    assert resolved == env_root


def test_installer_default_used_on_a_fresh_install_with_nothing_typed() -> None:
    local = "C:/Users/Corridor/AppData/Local"
    installer_pear = Path(local, "PoseCap", "pear")

    resolved = resolve_pear_root(
        _settings(""),
        _preferences(""),
        {"LOCALAPPDATA": local},
        {installer_pear}.__contains__,
    )

    assert resolved == str(installer_pear)


def test_empty_when_nothing_resolves() -> None:
    resolved = resolve_pear_root(
        _settings(""),
        _preferences(""),
        {},
        lambda _path: False,
    )

    assert resolved == ""

"""Behavior tests for the shared Blender-version-compatible fcurve accessor.

Blender 5.x removed `action.fcurves` in favor of per-slot channelbags; 4.2 keeps
the flat collection. The POC duplicated this branch verbatim in two operators
(operators/keyframes.py:84-97 and 174-185). One helper owns it now. The 5.x
channelbag resolver is injected so both branches test without a live Blender;
both are also HITL-verified on 4.2 and 5.0.
"""

from __future__ import annotations

from types import SimpleNamespace

from posecap_addon.keyframe_io import fcurves_for


class _FCurve:
    def __init__(self, name: str) -> None:
        self.name = name


def _obj(action: object, *, action_slot: object = None) -> SimpleNamespace:
    return SimpleNamespace(animation_data=SimpleNamespace(action=action, action_slot=action_slot))


def test_fcurves_for_returns_flat_collection_on_legacy_4x_actions() -> None:
    curves = [_FCurve("a"), _FCurve("b")]
    obj = _obj(SimpleNamespace(fcurves=curves))

    assert list(fcurves_for(obj)) == curves


def test_fcurves_for_resolves_slot_channelbag_on_5x_actions() -> None:
    curves = [_FCurve("q")]
    slotted_action = SimpleNamespace()  # no `fcurves` attribute, like Blender 5.x
    slot = object()
    obj = _obj(slotted_action, action_slot=slot)
    seen: list[tuple[object, object]] = []

    def resolve(action: object, action_slot: object) -> object:
        seen.append((action, action_slot))
        return SimpleNamespace(fcurves=curves)

    assert list(fcurves_for(obj, resolve_channelbag=resolve)) == curves
    assert seen == [(slotted_action, slot)]


def test_fcurves_for_is_empty_without_animation_data() -> None:
    assert list(fcurves_for(SimpleNamespace(animation_data=None))) == []


def test_fcurves_for_is_empty_without_an_action() -> None:
    assert list(fcurves_for(_obj(None))) == []


def test_fcurves_for_is_empty_when_slot_has_no_channelbag() -> None:
    obj = _obj(SimpleNamespace(), action_slot=object())

    assert list(fcurves_for(obj, resolve_channelbag=lambda _a, _s: None)) == []

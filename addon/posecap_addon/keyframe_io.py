"""One Blender-version-compatible way to reach an object's F-curves.

Blender 5.x replaced the flat `action.fcurves` collection with per-slot
channelbags reached through `bpy_extras.anim_utils.action_get_channelbag_for_slot`
(confirmed absent on 5.0.1: `action.fcurves` raises AttributeError). 4.2 keeps
the flat collection. The POC duplicated this branch in two operators; every
keyframe-manager operator now shares this single accessor.

`bpy_extras` only exists inside Blender, so the 5.x resolver is imported lazily
and is injectable for tests.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

ChannelbagResolver = Callable[[Any, Any], Any]


def fcurves_for(obj: Any, *, resolve_channelbag: ChannelbagResolver | None = None) -> Iterable[Any]:
    """Return the F-curves of `obj`'s active action, or an empty tuple.

    Handles the missing-animation, missing-action, legacy-4.x, and slotted-5.x
    cases uniformly so callers iterate one shape regardless of Blender version.
    """
    animation_data = getattr(obj, "animation_data", None)
    if animation_data is None:
        return ()
    action = getattr(animation_data, "action", None)
    if action is None:
        return ()
    legacy_fcurves = getattr(action, "fcurves", None)
    if legacy_fcurves is not None:
        return legacy_fcurves
    resolver = resolve_channelbag or _resolve_channelbag_via_anim_utils
    slot = getattr(animation_data, "action_slot", None)
    channelbag = resolver(action, slot)
    if channelbag is None:
        return ()
    return channelbag.fcurves


def _resolve_channelbag_via_anim_utils(action: Any, slot: Any) -> Any:
    from bpy_extras import anim_utils  # type: ignore  # Blender-bundled module, lazy

    return anim_utils.action_get_channelbag_for_slot(action, slot)

"""Body Models panel section: guided setup UI for the licensed SMPL-X files.

The section only appears while models are missing (CK2P: the happy path
stays clean once setup is done). Credentials live on WindowManager
properties — Blender never saves those into .blend files — and the password
field is cleared the moment the download starts.
"""

from __future__ import annotations

import time
from functools import partial
from pathlib import Path
from typing import Any

from .model_setup import (
    ModelSetupSession,
    MpiCredentials,
    missing_model_assets,
    verify_models_with_doctor,
)

MODEL_SIGNUP_URLS = {
    "SMPL": "https://smpl.is.tue.mpg.de/register.php",
    "SMPL-X": "https://smpl-x.is.tue.mpg.de/register.php",
    "FLAME": "https://flame.is.tue.mpg.de/register.php",
}

_POLL_INTERVAL_SECONDS = 0.5
_MISSING_CACHE_TTL_SECONDS = 2.0

_ACTIVE_SESSION: ModelSetupSession | None = None
_MISSING_CACHE: dict[str, tuple[float, bool]] = {}


def active_model_setup_session() -> ModelSetupSession | None:
    """The setup session the panel is currently showing, if any."""
    return _ACTIVE_SESSION


def models_missing(pear_root: str) -> bool:
    """Cheap draw-time check whether required models are absent (2s cache)."""
    if pear_root == "":
        return False
    now = time.monotonic()
    cached = _MISSING_CACHE.get(pear_root)
    if cached is not None and now - cached[0] < _MISSING_CACHE_TTL_SECONDS:
        return cached[1]
    result = len(missing_model_assets(Path(pear_root))) > 0
    _MISSING_CACHE[pear_root] = (now, result)
    return result


def draw_body_models_section(
    layout: Any,
    wm_group: Any,
    *,
    models_missing: bool,
    session: Any | None,
) -> None:
    """Draw the one-time body-model setup UI when it is needed."""
    if session is not None and session.state in ("RUNNING", "WATCHING"):
        box = layout.box()
        box.label(text="Body Models", icon="ARMATURE_DATA")
        box.label(text=session.status_message, icon="TIME")
        return
    if not models_missing:
        if session is not None and session.state in ("DONE", "FAILED"):
            layout.box().label(text=session.status_message, icon="INFO")
        return

    box = layout.box()
    box.label(text="Body Models — one-time setup", icon="ARMATURE_DATA")
    if wm_group.status != "":
        box.label(text=wm_group.status, icon="INFO")
    column = box.column()
    column.label(text="1. Create free accounts (use the same email + password):")
    signup_row = column.row(align=True)
    for site_name, url in MODEL_SIGNUP_URLS.items():
        signup_row.operator("wm.url_open", text=site_name, icon="URL").url = url
    column.label(text="Signing up on the official sites is the license step.")
    column.label(text="2. Enter that email and password (never saved):")
    column.prop(wm_group, "mpi_email")
    column.prop(wm_group, "mpi_password")
    column.operator("posecap.setup_body_models", text="Download & Install Models", icon="IMPORT")
    column.label(text="Prefer the browser? Download the files yourself and")
    column.operator(
        "posecap.watch_model_downloads",
        text="Watch my Downloads Folder",
        icon="VIEWZOOM",
    )


def build_model_setup_classes(bpy_module: Any) -> tuple[type[Any], ...]:
    """Build the model-setup operator classes against a bpy-like module."""

    class POSECAP_OT_SetupBodyModels(bpy_module.types.Operator):
        bl_idname = "posecap.setup_body_models"
        bl_label = "Download & Install Models"
        bl_description = (
            "Download the licensed body models from the official MPI sites "
            "with your own account (credentials are used in memory only)"
        )
        bl_options = {"REGISTER"}

        def execute(self, context: Any) -> set[str]:
            wm_group = context.window_manager.posecap_model_setup
            pear_root = _resolve_pear_root(context)
            if pear_root == "":
                wm_group.status = "Set the PEAR Root first (in the panel or preferences)."
                return {"CANCELLED"}
            email = str(wm_group.mpi_email).strip()
            password = str(wm_group.mpi_password)
            if email == "" or password == "":
                wm_group.status = "Enter the email and password of your model account first."
                return {"CANCELLED"}
            credentials = MpiCredentials(email=email, password=password)
            wm_group.mpi_password = ""
            wm_group.status = ""
            session = _new_session(context)
            session.start_credential_install(Path(pear_root), credentials)
            _start_session_poll(bpy_module)
            return {"FINISHED"}

    class POSECAP_OT_WatchModelDownloads(bpy_module.types.Operator):
        bl_idname = "posecap.watch_model_downloads"
        bl_label = "Watch my Downloads Folder"
        bl_description = (
            "Download the model files manually from the official sites; "
            "PoseCap detects, checks, and installs them automatically"
        )
        bl_options = {"REGISTER"}

        def execute(self, context: Any) -> set[str]:
            wm_group = context.window_manager.posecap_model_setup
            pear_root = _resolve_pear_root(context)
            if pear_root == "":
                wm_group.status = "Set the PEAR Root first (in the panel or preferences)."
                return {"CANCELLED"}
            wm_group.status = ""
            session = _new_session(context)
            session.start_watching(Path(pear_root), Path.home() / "Downloads")
            _start_session_poll(bpy_module)
            return {"FINISHED"}

    return (POSECAP_OT_SetupBodyModels, POSECAP_OT_WatchModelDownloads)


def _new_session(context: Any) -> ModelSetupSession:
    global _ACTIVE_SESSION
    engine_executable = _resolve_engine_executable(context)
    _ACTIVE_SESSION = ModelSetupSession(
        verify=partial(verify_models_with_doctor, engine_executable=engine_executable)
        if engine_executable != ""
        else None,
    )
    return _ACTIVE_SESSION


def _start_session_poll(bpy_module: Any) -> None:
    def poll() -> float | None:
        session = _ACTIVE_SESSION
        if session is None:
            return None
        session.tick()
        _publish_status(bpy_module, session)
        if session.state in ("DONE", "FAILED"):
            _MISSING_CACHE.clear()
            return None
        return _POLL_INTERVAL_SECONDS

    timers = bpy_module.app.timers
    timers.register(poll, first_interval=_POLL_INTERVAL_SECONDS)


def _publish_status(bpy_module: Any, session: ModelSetupSession) -> None:
    context = getattr(bpy_module, "context", None)
    window_manager = getattr(context, "window_manager", None)
    wm_group = getattr(window_manager, "posecap_model_setup", None)
    if wm_group is not None:
        wm_group.status = session.status_message
    _tag_panel_redraw(window_manager)


def _tag_panel_redraw(window_manager: Any) -> None:
    for window in getattr(window_manager, "windows", []):
        for area in getattr(window.screen, "areas", []):
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _resolve_pear_root(context: Any) -> str:
    settings = getattr(context.scene, "posecap", None)
    scene_root = str(getattr(settings, "pear_root", "")).strip()
    if scene_root != "":
        return scene_root
    preferences = _addon_preferences(context)
    return str(getattr(preferences, "pear_root", "")).strip()


def _resolve_engine_executable(context: Any) -> str:
    preferences = _addon_preferences(context)
    return str(getattr(preferences, "engine_executable", "")).strip()


def _addon_preferences(context: Any) -> Any | None:
    from .panels import ADDON_ID

    preferences = getattr(context, "preferences", None)
    addons = getattr(preferences, "addons", None)
    if addons is None:
        return None
    addon = addons.get(ADDON_ID) if hasattr(addons, "get") else None
    return getattr(addon, "preferences", None)

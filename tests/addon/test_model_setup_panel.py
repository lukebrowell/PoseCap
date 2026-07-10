"""Behavior tests for the Body Models panel section and its operators."""

from types import SimpleNamespace

import posecap_addon.model_setup_panel as model_setup_panel
from posecap_addon.model_setup_panel import (
    MODEL_SIGNUP_URLS,
    build_model_setup_classes,
    draw_body_models_section,
)


class _FakeOperatorProps:
    def __init__(self) -> None:
        self.url = ""


class _FakeLayout:
    def __init__(self, sink: "dict[str, list] | None" = None) -> None:
        self._sink = sink if sink is not None else {"operators": [], "props": [], "labels": []}

    def row(self, **_kwargs: object) -> "_FakeLayout":
        return _FakeLayout(self._sink)

    def column(self, **_kwargs: object) -> "_FakeLayout":
        return _FakeLayout(self._sink)

    def box(self) -> "_FakeLayout":
        return _FakeLayout(self._sink)

    def label(self, *, text: str, icon: str = "NONE") -> None:
        self._sink["labels"].append(text)

    def prop(self, _data: object, name: str, **_kwargs: object) -> None:
        self._sink["props"].append(name)

    def operator(self, operator_id: str, **_kwargs: object) -> _FakeOperatorProps:
        props = _FakeOperatorProps()
        self._sink["operators"].append((operator_id, props))
        return props

    @property
    def operator_ids(self) -> list[str]:
        return [operator_id for operator_id, _props in self._sink["operators"]]

    @property
    def urls(self) -> list[str]:
        return [props.url for _id, props in self._sink["operators"] if props.url]

    @property
    def props_drawn(self) -> list[str]:
        return self._sink["props"]

    @property
    def labels(self) -> list[str]:
        return self._sink["labels"]


def _wm_group(email: str = "", password: str = "") -> SimpleNamespace:
    return SimpleNamespace(mpi_email=email, mpi_password=password, status="")


def test_missing_models_offer_signup_credentials_and_both_setup_paths() -> None:
    layout = _FakeLayout()

    draw_body_models_section(
        layout,
        _wm_group(),
        models_missing=True,
        session=None,
    )

    assert "posecap.setup_body_models" in layout.operator_ids
    assert "posecap.watch_model_downloads" in layout.operator_ids
    signup_buttons = [url for url in layout.urls if url in set(MODEL_SIGNUP_URLS.values())]
    assert len(signup_buttons) == 3, "one sign-up button per MPI site"
    assert "mpi_email" in layout.props_drawn
    assert "mpi_password" in layout.props_drawn


def test_section_is_empty_when_models_are_installed_and_idle() -> None:
    layout = _FakeLayout()

    draw_body_models_section(
        layout,
        _wm_group(),
        models_missing=False,
        session=None,
    )

    assert layout.operator_ids == []
    assert layout.props_drawn == []


def test_running_session_shows_status_instead_of_credential_fields() -> None:
    layout = _FakeLayout()
    session = SimpleNamespace(state="RUNNING", status_message="Downloading FLAME2020.zip…")

    draw_body_models_section(
        layout,
        _wm_group(),
        models_missing=True,
        session=session,
    )

    assert "Downloading FLAME2020.zip…" in layout.labels
    assert "mpi_password" not in layout.props_drawn


class _FakeSession:
    def __init__(self, **_kwargs: object) -> None:
        self.state = "IDLE"
        self.status_message = ""
        self.credential_calls: list[tuple[object, object]] = []
        self.watch_calls: list[tuple[object, object]] = []

    def start_credential_install(self, pear_root, credentials) -> None:
        self.state = "RUNNING"
        self.credential_calls.append((pear_root, credentials))

    def start_watching(self, pear_root, downloads_dir) -> None:
        self.state = "WATCHING"
        self.watch_calls.append((pear_root, downloads_dir))

    def tick(self) -> None:
        return None


class _FakeTimers:
    def __init__(self) -> None:
        self.registered = []

    def register(self, function, *, first_interval: float = 0.0, persistent: bool = False):
        self.registered.append(function)

    def unregister(self, function) -> None:
        self.registered.remove(function)

    def is_registered(self, function) -> bool:
        return function in self.registered


def _fake_bpy_module(wm_group: SimpleNamespace) -> SimpleNamespace:
    context = SimpleNamespace(
        window_manager=SimpleNamespace(posecap_model_setup=wm_group, windows=[]),
    )
    return SimpleNamespace(
        app=SimpleNamespace(timers=_FakeTimers()),
        context=context,
        types=SimpleNamespace(Operator=object),
    )


def _operator_context(wm_group: SimpleNamespace, *, pear_root: str = "C:/PEAR"):
    settings = SimpleNamespace(pear_root=pear_root)
    return SimpleNamespace(
        scene=SimpleNamespace(posecap=settings),
        window_manager=SimpleNamespace(posecap_model_setup=wm_group, windows=[]),
        preferences=SimpleNamespace(addons={}),
    )


def test_setup_operator_starts_a_session_and_clears_the_password(monkeypatch) -> None:
    wm_group = _wm_group(email="emmet@corridor.example", password="pw")
    bpy_module = _fake_bpy_module(wm_group)
    monkeypatch.setattr(model_setup_panel, "ModelSetupSession", _FakeSession)
    setup_cls, _watch_cls = build_model_setup_classes(bpy_module)

    result = setup_cls().execute(_operator_context(wm_group))

    assert result == {"FINISHED"}
    session = model_setup_panel.active_model_setup_session()
    assert session is not None and session.credential_calls
    credentials = session.credential_calls[0][1]
    assert credentials.email == "emmet@corridor.example"
    assert credentials.password == "pw"
    assert wm_group.mpi_password == "", "password must not linger in the UI field"
    assert len(bpy_module.app.timers.registered) == 1


def test_setup_operator_asks_for_credentials_when_fields_are_empty(monkeypatch) -> None:
    wm_group = _wm_group()
    bpy_module = _fake_bpy_module(wm_group)
    monkeypatch.setattr(model_setup_panel, "ModelSetupSession", _FakeSession)
    setup_cls, _watch_cls = build_model_setup_classes(bpy_module)

    result = setup_cls().execute(_operator_context(wm_group))

    assert result == {"CANCELLED"}
    assert "email" in wm_group.status.lower() or "password" in wm_group.status.lower()


def test_setup_operator_asks_for_pear_root_when_unset(monkeypatch) -> None:
    wm_group = _wm_group(email="a@b.c", password="pw")
    bpy_module = _fake_bpy_module(wm_group)
    monkeypatch.setattr(model_setup_panel, "ModelSetupSession", _FakeSession)
    setup_cls, _watch_cls = build_model_setup_classes(bpy_module)

    result = setup_cls().execute(_operator_context(wm_group, pear_root=""))

    assert result == {"CANCELLED"}
    assert "pear root" in wm_group.status.lower()


def test_watch_operator_starts_the_downloads_watcher(monkeypatch) -> None:
    wm_group = _wm_group()
    bpy_module = _fake_bpy_module(wm_group)
    monkeypatch.setattr(model_setup_panel, "ModelSetupSession", _FakeSession)
    _setup_cls, watch_cls = build_model_setup_classes(bpy_module)

    result = watch_cls().execute(_operator_context(wm_group))

    assert result == {"FINISHED"}
    session = model_setup_panel.active_model_setup_session()
    assert session is not None and session.watch_calls
    assert len(bpy_module.app.timers.registered) == 1


def test_poll_timer_stops_after_the_session_finishes(monkeypatch) -> None:
    wm_group = _wm_group(email="a@b.c", password="pw")
    bpy_module = _fake_bpy_module(wm_group)
    monkeypatch.setattr(model_setup_panel, "ModelSetupSession", _FakeSession)
    setup_cls, _watch_cls = build_model_setup_classes(bpy_module)
    setup_cls().execute(_operator_context(wm_group))
    session = model_setup_panel.active_model_setup_session()
    poll = bpy_module.app.timers.registered[0]

    session.status_message = "Downloading…"
    assert poll() is not None
    assert wm_group.status == "Downloading…"

    session.state = "DONE"
    session.status_message = "Models installed."
    assert poll() is None
    assert wm_group.status == "Models installed."

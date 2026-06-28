from pathlib import Path
from typing import Any, cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return cast(dict[str, Any], loaded)


def _local_hooks() -> list[dict[str, Any]]:
    config = _load_yaml(REPO_ROOT / ".pre-commit-config.yaml")
    hooks: list[dict[str, Any]] = []
    for repo in config["repos"]:
        assert isinstance(repo, dict)
        for hook in repo.get("hooks", []):
            assert isinstance(hook, dict)
            hooks.append(cast(dict[str, Any], hook))
    return hooks


def test_pre_push_pyright_checks_windows_and_linux_platforms() -> None:
    pyright_entries = {
        str(hook["entry"])
        for hook in _local_hooks()
        if str(hook.get("id", "")).startswith("pyright") and hook.get("stages") == ["pre-push"]
    }

    assert "uv run pyright --pythonplatform Windows" in pyright_entries
    assert "uv run pyright --pythonplatform Linux" in pyright_entries


def test_pre_commit_install_defaults_include_pre_push() -> None:
    config = _load_yaml(REPO_ROOT / ".pre-commit-config.yaml")

    assert set(config["default_install_hook_types"]) == {"pre-commit", "pre-push"}


def test_ci_type_gate_checks_windows_and_linux_platforms() -> None:
    workflow = _load_yaml(REPO_ROOT / ".github" / "workflows" / "ci.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    quality = jobs["quality"]
    assert isinstance(quality, dict)
    steps = quality["steps"]
    assert isinstance(steps, list)

    commands = {
        str(step["run"])
        for step in steps
        if isinstance(step, dict) and step.get("name", "").startswith("Types")
    }

    assert "uv run pyright --pythonplatform Windows" in commands
    assert "uv run pyright --pythonplatform Linux" in commands

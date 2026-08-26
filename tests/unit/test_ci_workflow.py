"""Regression coverage for the protected CI workflow contract."""

from pathlib import Path


WORKFLOW_PATH = Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_covers_protected_pull_request_events() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "pull_request:\n    branches: [main]\n    types: [opened, reopened, synchronize]" in workflow
    assert "workflow_dispatch:" in workflow


def test_ci_workflow_keeps_required_test_job_and_commands() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "jobs:\n  test:" in workflow
    for command in ("uv sync --all-extras --locked", "uv run ruff check .", "uv run pytest tests/unit -q"):
        assert command in workflow

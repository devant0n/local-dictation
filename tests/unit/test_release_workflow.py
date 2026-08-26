"""Regression coverage for the release workflow contract."""

from pathlib import Path


WORKFLOW_PATH = Path(__file__).parents[2] / ".github" / "workflows" / "release.yml"


def test_release_workflow_preserves_automatic_release_gate() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "push:\n    branches: [main]" in workflow
    assert "startsWith(github.event.head_commit.message, 'feat')" in workflow
    assert "startsWith(github.event.head_commit.message, 'fix')" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow


def test_release_workflow_uses_locked_cli_and_safe_dispatch() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "default: true" in workflow
    assert "uv sync --extra dev --locked" in workflow
    assert "uv run semantic-release version" in workflow
    assert "GH_TOKEN: ${{ secrets.RELEASE_PAT }}" in workflow
    assert "uv run semantic-release --noop version --no-push --no-vcs-release" in workflow
    assert "python-semantic-release/python-semantic-release@" not in workflow

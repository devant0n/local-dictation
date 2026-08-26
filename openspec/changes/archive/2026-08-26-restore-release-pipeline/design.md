## Context

The current release workflow uses `python-semantic-release/python-semantic-release@v10.6.1`, whose container resolves GitPython `3.1.60` and fails during configuration loading. The repository lockfile resolves Semantic Release `10.6.1` with GitPython `3.1.59`, and the same CLI succeeds locally in no-op mode.

## Goals / Non-Goals

**Goals:**
- Use the reproducible locked environment for both automatic and dry-run release execution.
- Preserve PAT-backed checkout, permissions, commit gating, version configuration, and source-only publication scope.
- Make dry-run verification safe and repeatable.

**Non-Goals:**
- Waiting for or depending on a future upstream action release.
- Changing release versioning rules, PyPI publication policy, or application packaging.
- Publishing a release during validation.

## Decisions

### Replace the Docker action with the locked CLI

Set up Python 3.13 and uv, install the `dev` extra from `uv.lock`, and invoke `uv run semantic-release version` with `GH_TOKEN` mapped to `RELEASE_PAT`. This keeps the known-compatible GitPython version and removes the action container's unconstrained dependency resolution.

Alternative: pin or override GitPython inside the third-party Docker action. Rejected because the action does not provide a supported dependency override and would remain fragile.

### Add a default-safe manual dry run

Add `workflow_dispatch` with a boolean dry-run input defaulting to true. Manual runs use `--noop --no-push --no-vcs-release`; automatic qualifying pushes retain the existing mutating command. The workflow-contract test verifies the default-safe branch.

Alternative: manually run the mutating release command for validation. Rejected because it could create an unintended version/tag/release.

### Keep the existing GitHub security model

Retain the PAT-backed checkout and `GH_TOKEN` secret mapping, with existing write permissions. No new credentials or external services are introduced.

## Risks / Trade-offs

- The next real release still mutates `main` and creates a release → preserve the existing commit gate and validate first with dry-run.
- Lockfile updates can change the compatible runtime later → require locked installs and keep the dependency versions under repository review.
- A dry-run does not prove remote write permissions → the first subsequent qualifying merge is the controlled production confirmation.

## Migration Plan

1. Replace the action step and add the dry-run dispatch branch and workflow-contract tests.
2. Run unit tests, Ruff, build, strict OpenSpec validation, and local no-op Semantic Release.
3. Merge the reviewed repair.
4. Dispatch the Release workflow with default dry-run and verify success plus no tag/release/file changes.
5. Confirm the next qualifying merge creates the expected release.

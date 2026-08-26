## Why

The Release workflow fails before version calculation because the pinned Docker action resolves a GitPython version that removed `Actor.name_email_regex`. This blocks every qualifying release and has reproduced on consecutive merges.

## What Changes

- Run Semantic Release from the project's lockfile-pinned development environment instead of the incompatible Docker action.
- Preserve automatic releases for qualifying `fix:` and `feat:` merges to `main`.
- Add a safe manual dry-run workflow path that cannot publish or modify repository state.
- Add workflow-contract coverage and a documented end-to-end verification procedure.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `release-management`: Replace the broken runtime while preserving automatic release behavior and add a maintainer-safe dry-run path.

## Impact

- `.github/workflows/release.yml`, release workflow tests, and OpenSpec release documentation.
- Uses the existing locked Python Semantic Release and GitPython versions.
- No application behavior, PyPI publication, or release-policy change.

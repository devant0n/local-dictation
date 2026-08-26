## Why

The active CI workflow is not producing a required `test` check for current pull-request heads, blocking protected merges including PR #25. Maintainers also lack a supported way to request a recovery run when GitHub does not deliver a pull-request event.

## What Changes

- Define continuous-integration behavior for same-repository pull requests and head updates.
- Add a manual workflow-dispatch recovery path to CI.
- Preserve the existing macOS test job and the strict `test` branch-protection requirement.
- Record reproducible verification of automatic and manual CI dispatch on the repair PR.

## Capabilities

### New Capabilities

- `continuous-integration`: Defines required CI triggers, check identity, and manual recovery dispatch behavior.

### Modified Capabilities

- None.

## Impact

- `.github/workflows/ci.yml` and workflow/configuration regression coverage.
- GitHub Actions dispatch behavior and the protected-branch `test` status check.
- No application, privacy, release-policy, or dependency changes.

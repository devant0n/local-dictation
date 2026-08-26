## 1. Release workflow runtime

- [x] 1.1 Replace the Python Semantic Release Docker action with Python 3.13, uv, locked `dev` dependencies, and the CLI invocation using `GH_TOKEN` from `RELEASE_PAT`.
- [x] 1.2 Add a default-safe manual `workflow_dispatch` dry-run path while preserving automatic `fix:`/`feat:` release gating and existing permissions.

## 2. Regression coverage

- [x] 2.1 Add a fast workflow-contract test for release triggers, lockfile installation, CLI invocation, token wiring, and dry-run safeguards.
- [x] 2.2 Run unit tests, Ruff, package build, strict OpenSpec validation, and local no-op Semantic Release.

## 3. End-to-end verification

- [ ] 3.1 After integration, dispatch the Release workflow in default dry-run mode and verify a successful run with no repository/tag/release changes.
- [ ] 3.2 Record the final test procedure and evidence on issue #31; confirm the next qualifying merge uses the repaired automatic release path.

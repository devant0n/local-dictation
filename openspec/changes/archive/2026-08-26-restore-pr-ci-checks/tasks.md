## 1. CI workflow contract

- [x] 1.1 Update `.github/workflows/ci.yml` with explicit `pull_request` activity types and `workflow_dispatch`, preserving the macOS `test` job and its commands.
- [x] 1.2 Add a fast repository test that asserts the CI workflow declares the required automatic and manual triggers and retains the `test` job identity.

## 2. Verification and recovery

- [x] 2.1 Run the affected unit/configuration tests, linting, and strict OpenSpec validation.
- [x] 2.2 Manually validate the repair revision before the authorized one-time exception merge.
- [ ] 2.3 After integration, dispatch CI for a selected pull-request ref and verify an opened or synchronized pull request receives an event-driven `test` check before resuming issue #23.

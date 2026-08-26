## Purpose

Ensures protected pull requests receive the required CI check and provides a controlled recovery path when GitHub does not schedule an event-driven run.

## ADDED Requirements

### Requirement: Pull-request CI coverage
The CI workflow SHALL run its `test` job when a same-repository pull request targeting `main` is opened, reopened, or synchronized, and the resulting check SHALL be associated with that pull request's current head.

#### Scenario: New pull request
- **WHEN** a same-repository pull request targeting `main` is opened
- **THEN** GitHub Actions creates a CI run with a `test` check for its current head

#### Scenario: Updated pull-request head
- **WHEN** a commit is pushed to an open same-repository pull request targeting `main`
- **THEN** GitHub Actions creates a CI run with a `test` check for the updated head

### Requirement: Manual CI recovery
The CI workflow SHALL support maintainer-triggered manual dispatch for a selected repository ref and SHALL run the same `test` job against that ref.

#### Scenario: Maintainer dispatches recovery run
- **WHEN** a maintainer manually dispatches CI for a branch containing a pull-request head
- **THEN** GitHub Actions runs the `test` job for the selected ref and reports its result as a `test` check

### Requirement: Protected-check compatibility
The CI workflow SHALL preserve the `test` check identity required by the protected `main` ruleset and SHALL not require a ruleset bypass during normal pull-request delivery.

#### Scenario: Normal protected pull request
- **WHEN** an event-triggered CI run completes successfully for a mergeable pull request
- **THEN** its `test` check satisfies the matching required-status-check rule without changing the ruleset

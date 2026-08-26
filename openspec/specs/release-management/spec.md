# release-management Specification

## Purpose

Provides a repeatable, automated release process that derives semantic versions from Conventional
Commits on every qualifying merge to the protected `main` branch, while keeping publication scope
(source-only, no PyPI, no app bundle) under explicit maintainer control.
## Requirements
### Requirement: Semantic version derivation
The project SHALL derive its next semantic version from Conventional Commit messages and stamp the selected version into package metadata.

#### Scenario: Dry-run release
- **WHEN** a developer or maintainer runs the documented release dry-run command on a clean checkout
- **THEN** the command reports the version it would produce without changing repository files, tags, or releases

### Requirement: Intentional local release

The project SHALL run its release process automatically in CI, gated by Conventional Commit type prefix on merge to the protected `main` branch, and that automated CI process SHALL NOT publish a distribution package (e.g. to PyPI) or produce an application bundle. A maintainer SHALL also be able to dispatch a dry-run release workflow that performs no repository mutation. A developer MAY build a macOS `.app` bundle locally, on demand, outside of CI; doing so is not publication and is not restricted by this requirement.

#### Scenario: Local release execution

- **WHEN** a pull request whose merge commit message starts with `fix` or `feat` passes required checks and merges to `main`
- **THEN** the release workflow versions package metadata and the changelog and creates a matching `v{version}` Git tag and GitHub release, without publishing to PyPI or producing an app bundle

#### Scenario: Non-qualifying merge does not release

- **WHEN** a merge commit message does not start with `fix` or `feat` (e.g. a `docs:` or `chore:` commit)
- **THEN** no release is created

#### Scenario: Maintainer dry-run dispatch

- **WHEN** a maintainer dispatches the release workflow in its default dry-run mode
- **THEN** Semantic Release reports the next version and creates no commit, tag, GitHub release, distribution publication, or app bundle

#### Scenario: Developer builds a local app bundle

- **WHEN** a developer runs the project's local `.app` bundle build script on their own machine
- **THEN** this is permitted and outside the scope of this requirement, since the automated release process in CI neither performs nor is affected by that local build


## Context

The existing CI workflow is active, uses the required `test` job name, and already declares `pull_request`, but GitHub created no run or check suite for PR #25's mergeable current head. The workflow has no manual-dispatch trigger. See proposal.md and the continuous-integration delta spec.

## Goals / Non-Goals

**Goals:**
- Make the intended pull-request activity types explicit and provide a maintainer recovery path.
- Keep the existing macOS validation commands and `test` check identity.
- Verify the normal event path and the manual recovery path with GitHub evidence.

**Non-Goals:**
- Changing application code, dependencies, release behavior, or the `Protect main` ruleset.
- Replacing `pull_request` with `pull_request_target`, which would change the security model for pull-request code.
- Guaranteeing third-party event delivery beyond GitHub Actions' documented behavior.

## Decisions

### Explicit pull-request activity types plus manual dispatch

Declare `opened`, `reopened`, and `synchronize` explicitly and add `workflow_dispatch`. Explicit types document the protected-merge contract; `workflow_dispatch` provides a supported recovery run on the selected ref. The same `test` job remains the only validation job.

Alternative: retain the implicit pull-request defaults and only add manual dispatch. Rejected because it leaves the required automatic activities less visible and less straightforward to verify as a contract.

### Preserve the untrusted-code execution model

Continue using `pull_request` and the existing checkout behavior. Do not use `pull_request_target` or a check-triggered recursive workflow.

Alternative: use `pull_request_target` to avoid merge-conflict restrictions. Rejected because it would run under the base repository security context and is unnecessary for this same-repository, mergeable PR.

### One-time administrator exception only for bootstrap

Use the maintainer-authorized exception only to merge the manually validated repair that cannot receive its own required check. Leave the ruleset untouched and verify normal enforcement immediately afterward.

## Risks / Trade-offs

- GitHub may continue not to deliver an eligible pull-request event → retain the manual recovery path and record the provider-side evidence for support escalation.
- The first manual-dispatch trigger cannot be used until it is on `main` → limit the authorized exception to this repair and perform local validation before that merge.
- A manually dispatched check can mask an event-delivery regression → verify a newly opened or synchronized PR produces an event-driven run after the repair.

## Migration Plan

1. Update the CI workflow and add workflow/configuration regression coverage.
2. Validate the workflow locally and manually validate the repair revision.
3. Merge only this repair through the authorized exception.
4. Dispatch CI against a selected pull-request ref, then verify a newly opened or synchronized pull request receives an event-driven `test` check.
5. Resume issue #23 only after normal required-check behavior is observed.

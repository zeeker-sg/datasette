# TEST-INFRASTRUCTURE GATE — read before any dependency change

## Status (2026-10-13)

The upgrade PR (#20) and Dependabot PR (#21) are MERGED. Production still
deploys the pinned images `sha-b2c15805…` (Datasette 0.65.2) — deployment was
out of scope and has NOT happened. The smoke-stack gate (branch
`test/smoke-stack-gate`) was validated against both:

- **baseline** `sha-b2c15805…` (deployed 0.65.2 images): 24/24 checks green
- **candidate** worktree-built images carrying the merged 0.65.5 pins: 24/24 green
- **negative control** (protection deliberately disabled): smoke correctly
  FAILED with the two expected check failures (REGRESSIONS-PASSED)

## The gate rule (user-mandated, 2026-10-13)

> Before any further dependency changes or production rollout of the PR-#20
> upgrade, the smoke stack must pass — baseline + candidate + negative
> control.

Operationally: run the two `run_smoke_stack.sh` invocations from
`tests/smoke-stack/README.md` before approving any compose pin-bump PR or
further dependency PR. Exit 0 on both = go.

## Production rollout state of the 0.65.5 upgrade

The 0.65.5 images are published by CI on master (sha `3d641f3…`) but the
compose pin-bump has NOT been merged/deployed — prod still runs
`sha-b2c15805…`. When the user approves rollout, the pin-bump PR is the next
step, gated on the smoke runs above.

## Health monitoring: PAUSED — do not resume

The user paused Zeeker health monitoring; no watchdogs, health-check resumes,
or monitoring changes are authorized by any of these tasks.
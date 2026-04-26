# Phase 7 deferred items

Items found during Phase 7 plan execution that are out-of-scope for the current
plan and DO NOT block ship. Tracked here for triage at HUMAN-UAT close-out.

---

## Plan 07-02 (Wave-1)

### 1. verify_phase_03.sh §F.1 uppercase-.JSON case-insensitivity test fails

- **Found during:** Plan 07-02 Task 3 smoke pass (`bash scripts/verify_phase_06.sh`).
- **Symptom:** Section F.1 of verify_phase_03.sh (chained from verify_phase_06)
  reports `FAIL  uppercase .JSON may have fallen through (body: <!DOCTYPE html>...)`.
- **Root cause:** Caddyfile uses `path *.json` matcher which is case-sensitive
  by default; `/SGLAWWATCH.JSON` falls through to the frontend's 404 page
  (which renders as HTML, not JSON-with-`tables`-key). The verifier comment
  on line 237 of verify_phase_03.sh asserts "Caddy path matcher is
  case-insensitive" — this is **incorrect** per the Caddy docs (matchers are
  case-sensitive unless `path_regexp` with `(?i)` is used).
- **Pre-existing:** YES — not introduced by this plan. Plan 07-01's smoke
  pass was opt-skipped because the local stack was not running. The Phase-6
  SUMMARY reports "all 11 sections green" but that run may have used
  different baseline conditions or the test was tolerated upstream.
- **Why deferred:** Plan 07-02's scope is metadata.json edit + baseline
  re-capture + cascade prepend. Fixing the Caddy case-matcher (or adjusting
  the verifier's assertion to accept a 404 from the frontend on uppercase
  .JSON) is a Caddy-config / verifier-fingerprint concern outside this
  plan's frontmatter (`files_modified` lists metadata.json + baselines +
  3 verifier-cascade lines, NOT verify_phase_03.sh §F).
- **Triage path:** Either (a) add `(?i)` case-insensitive matching to the
  Caddy path matcher (architectural decision — affects every path), OR
  (b) update verify_phase_03.sh §F.1 to accept a 404-from-frontend body as
  valid (acknowledges the production semantic: uppercase data-API URLs
  are not supported). Recommend (b) as the minimum-surface fix.
- **Owner:** Phase 7 HUMAN-UAT close-out OR Plan 07-05 deploy gate.

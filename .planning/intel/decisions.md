# Synthesized Decisions

> All decisions below originate from `prd-zeeker-frontend-split.md` Appendix A. Status is **Draft** (not LOCKED) — these are PRD-level proposals, not ratified ADRs. Promote to ADRs (`Status: Accepted`) before treating any as locked.

## DEC-1 — Keep Datasette as API backend, not rewrite
**Source:** prd-zeeker-frontend-split.md Appendix A #1
**Locked:** false (PRD draft)
**Rationale:** Re-implementing `.json`/`.csv`/`-/sql` is high-risk, low-value; the API surface is what works.
**Scope:** Architectural backbone.

## DEC-2 — Suffix-based routing over path-based
**Source:** prd-zeeker-frontend-split.md Appendix A #2, §6
**Locked:** false (PRD draft)
**Rationale:** Preserves API URLs byte-for-byte without per-database config.
**Scope:** Reverse-proxy routing strategy.

## DEC-3 — FastAPI + Jinja for frontend stack
**Source:** prd-zeeker-frontend-split.md Appendix A #3, §7.2
**Locked:** false (PRD draft)
**Rationale:** Minimal stack, Python-native, reuses Jinja knowledge from existing Datasette templates.
**Scope:** Frontend tech stack.

## DEC-4 — Caddy over nginx/Traefik
**Source:** prd-zeeker-frontend-split.md Appendix A #4, §7.3
**Locked:** false (PRD draft)
**Rationale:** Simplest config for this scale; auto-TLS.
**Scope:** Reverse-proxy software choice.

## DEC-5 — Frontend accesses data via HTTP, not direct SQLite
**Source:** prd-zeeker-frontend-split.md Appendix A #5, §7.2
**Locked:** false (PRD draft)
**Rationale:** Maintains "Datasette owns the database" discipline; keeps frontend stateless.
**Scope:** Data-access discipline.

## DEC-6 — Incremental migration with fallback
**Source:** prd-zeeker-frontend-split.md Appendix A #6, §10
**Locked:** false (PRD draft)
**Rationale:** De-risks a project where continuation itself is in question (per author's R7 risk note).
**Scope:** Rollout strategy.

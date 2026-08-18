# Phoenix Agent Operating Contract

This file is the operating manual for any agent (Claude Code, Codex, or otherwise) working in this repository. Read it first, every session, before touching anything.

---

## Source of truth

- **The Git repository is the source of truth for Phoenix.** Code, tests, and the four documents below — not chat memory, not a prior conversation, not anything you "remember" about this project.
- **Conversation/chat memory is NOT a source of truth.** A new session has no access to prior conversations and must not assume it does. Never assert a component's state, a decision, or a test count from memory — verify it against the repo.
- Before modifying anything, reconstruct current state from the repo (git log/status, the four documents, the actual code). Do not skip this because "it was already established" in an earlier turn you cannot prove exists in this session.
- If documentation and code contradict each other, do not silently pick one. Stop and report the contradiction.

---

## Required reading order

A new session should read, in this order, before doing any work:

1. `AGENTS.md` (this file)
2. `docs/architecture.md` — map of the system as it exists today
3. `docs/handoff.md` — where the project stands, what to read next
4. `docs/decisions.md` — binding architectural decisions (ADRs / `D-XXX`)
5. `docs/progress.md` — historical ledger of every hito (milestone)

Then inspect the actual code of whatever component you're about to touch. Documents describe intent; code is ground truth for behavior.

---

## Change discipline

**Before modifying anything:**
- `git status`, current branch, `HEAD` vs `origin/main` — confirm clean and synced (or explain why not).
- Run the relevant tests, then the full suite, to get a real baseline.
- Read the existing contracts/Ports/tests for the area you're about to touch.
- Read the ADRs relevant to that area in `docs/decisions.md`.

**After modifying anything:**
- Run the specific tests, then the full suite.
- Review your own diff (`git status`, `git diff --stat`, `git diff`) before committing.
- Update documentation (`progress.md`/`handoff.md`/`decisions.md`) if the change is hito-sized.
- Commit. Do not push if there is unresolved operational risk (e.g. a Railway service that could autodeploy from `main`).

---

## Architectural discipline

Stable rules, not point-in-time details:

- Separate domain from infrastructure. Domain contracts (`positions_contracts.py`, `contracts.py`, etc.) never import a `Bybit*` type, `urllib`, or any transport-level name — enforced by dedicated purity tests (AST-based) throughout the test suite.
- Ports/Adapters: a domain/application Port is a `Protocol` (`@runtime_checkable`); an Adapter implements it. `ExecutionGateway` (write) and the five read-side Ports (`PositionsReader`, `OpenOrdersReader`, `WalletBalanceReader`, `InstrumentMetadataReader`, `ExchangeStateReader`) are the currently implemented domain/application Ports — see `docs/architecture.md` §5–6. Note: several lower-level infrastructure Protocols also exist and are also `@runtime_checkable` (`HttpTransport`, `HttpGetTransport`, `MessageSigner`, `MillisecondClock`, `JsonSerializer`, `BybitAuthenticator`) — these are transport/signing/serialization seams, not domain Ports; don't conflate the two when reasoning about the domain/infrastructure boundary.
- Read-side is separate from write-side. No read method was ever added to `ExecutionGateway`; no write method exists on any reader.
- Never let exchange-specific types cross a Port boundary. Every `Bybit*` adapter translates to/from a domain contract at its own edge.
- Do not build abstractions "just in case." Three similar lines beat a premature abstraction — this repo's history shows several explicit decisions to *not* generalize a shared primitive when the need wasn't demonstrated (see ADR-002, Decisión 2).
- Do not modify a component marked `CONGELADO` (frozen, e.g. `phoenix_core`) without documenting the decision in `docs/decisions.md` first.
- Prefer small, individually auditable changes over large ones. This project's entire history is one hito at a time, each with its own tests and documentation update.
- Fail closed when remote completeness can't be guaranteed (pagination not confirmed empty, cardinality not exactly 1, symbol identity not confirmed) — never silently proceed with partial or ambiguous remote data.
- Distinguish observation from action. Everything under the read-side (`*Reader`, `ExchangeStateSnapshot`) is **observational only** — it never creates, cancels, or modifies anything. Only `ExecutionGateway.execute()` writes.
- Tests do not substitute for evidence of production behavior. A component fully covered by tests is *tested*, not *validated against real Bybit* — these are different claims and must be labeled differently (see `docs/architecture.md` §10).
- Never infer real production behavior from mocks. If a claim needs a real Bybit/Railway execution to be true, say explicitly that it hasn't been made, rather than implying it from test coverage.

---

## Environment discipline

Only what is currently confirmed true — verify against `docs/decisions.md` before relying on any of this, since it can change:

- **Bybit Demo is the only supported environment** (`D-011`). `Testnet` is excluded and rejected outright. `Mainnet` is not part of the current goal and must not be assumed or implemented by default — but this is not an eternal prohibition: `D-011` explicitly allows it *given a future explicit decision*. Do not build Mainnet support preemptively; do not treat it as permanently off the table either.
- **Railway** is the deploy target for services (`D-008`), but as of the last recorded state **no Railway service is currently connected to `main`** — `phoenix-smoke-demo` was manually deleted after Hito 3.68's validation (see `docs/handoff.md`). Confirm this hasn't changed before assuming push-to-`main` is risk-free from an autodeploy standpoint.
- Any Railway service that talks to Bybit must default to **EU West (Amsterdam, `europe-west4`)** — US regions are confirmed to fail (`D-014`, Decisión 1). The evidence only rules out US, it does not prove EU West is the *only* valid region.
- **`PYTHONPATH=/app/platform` is an active, unresolved packaging workaround, not a solution** (`D-014`, Decisión 2). If a Railway service is ever recreated from `railway.toml` alone, it will very likely reproduce the original `ModuleNotFoundError` unless `PYTHONPATH` is added manually again. Do not treat `railway.toml` as the complete source of truth for a live service's runtime config.
- Never invent credentials. Never write secrets into code, docs, or commit messages. All tests that touch credential-shaped data use synthetic, clearly-fake values.

---

## Testing / audit discipline

- This project uses adversarial/mutation testing on every hito of consequence: apply a mutation to the real production file, run the suite, confirm `DETECTADA` (caught) or `SOBREVIVE` (survived), then restore and verify byte-identity (`git diff --quiet` or tree-hash comparison) before continuing. Never leave a mutation applied.
- Distinguish a **coverage gap** (production is already correct; no test proves it) from a **production defect** (production is wrong). Most "IMPORTANTE" findings in this project's history have been the former — say which one you found.
- **Do not declare a hito accepted unless the workflow says you may.** Several hitos in this project require an independent adversarial audit (performed by stopping and reconstructing the pipeline from code, not trusting the implementer's report) before acceptance. If that's the workflow in use, the implementing session ends with "listo para auditoría adversarial independiente," never "ACEPTAR."
- When a required decision cannot be derived unambiguously from code, tests, or ADRs, and it would affect a public contract: **stop and ask**, following the STOP protocol already used in this project (see ADR-002, Hito 3.74 — Instrument Metadata scope decision was resolved this way). Do not resolve architectural ambiguity by guessing.

---

## Component completion

When a large component reaches a milestone, its closure should leave behind (per `docs/handoff.md`'s existing protocol):

- Current state and what changed
- Decisions made (in `docs/decisions.md`)
- Public interfaces / contracts exposed
- Key files
- Tests (count, what they cover)
- Commit hash / tag if applicable
- Known debts, explicitly
- What component/hito comes next

Large components additionally get a dedicated closure document under `docs/components/<name>.md` once finished and frozen (see `docs/components/phoenix-core.md` for the existing template).

---

## Agent behavior

**If a necessary decision cannot be derived unambiguously from the code, tests, or ADRs — stop and ask.** Do not silently resolve architectural ambiguity, do not guess at scope, do not assume a prior conversation's intent. This repository's own history (the Hito 3.74 Instrument Metadata scope decision, resolved by presenting options A/B/C rather than picking one) is the reference example of the expected behavior.

Do not declare more than the evidence supports. "Tested" is not "validated against real Bybit." "Production is byte-identical" is a claim that should be verified against a tree hash, not asserted from a diff summary. When in doubt about how strong a claim you're entitled to make, make the weaker one and say what's missing.

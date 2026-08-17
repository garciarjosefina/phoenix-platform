# Phoenix Architecture

This is a map of Phoenix **as it exists right now** — not a history (see `docs/progress.md` for that) and not a decision log (see `docs/decisions.md`). If this document and the code disagree, the code wins; report the discrepancy rather than trusting either blindly.

---

## 1. Purpose

Phoenix is infrastructure for building and operating a controlled, quantitative trading ecosystem — not a single bot, and not (yet) a bot itself. It is being built as a set of small, independently-testable components: a frozen domain-contract core, an execution/read-side gateway to Bybit, and a documented set of not-yet-built future components (Reconciliation Engine, Market Regime Engine, Portfolio Orchestrator, Bot SDK, Dashboard).

This document makes no claim about the profitability or trading performance of any bot — that is out of scope for Phoenix's own architecture.

---

## 2. Architectural principles

Confirmed by code, tests, and `docs/decisions.md`:

- **Domain isolation** — domain contracts never import exchange-specific types. Verified by dedicated `TestPurityByAst`-style tests across the read-side (AST-walks the module's imports, asserts no `Bybit*`/`urllib`/`http`/`socket` names).
- **Ports/Adapters** — every capability is exposed as a `Protocol` (`@runtime_checkable`) Port, implemented by a Bybit-specific Adapter. See §4–6.
- **Explicit composition roots** — no component reads environment variables or constructs its own dependencies implicitly. Each capability has a `create_*` factory (pure construction), a `create_configured_*` factory (from a typed config object), and a `bootstrap_*_from_env` function (loads env → builds). Public one-call entry points (`query_bybit_demo_*`) sit on top.
- **Fail-closed** — when the read-side cannot confirm completeness of a remote answer (pagination cursor present, cardinality ≠ 1, symbol mismatch), it raises rather than returning a partial or best-guess result.
- **Observational vs actionable state** — the entire read-side only observes; it cannot create, cancel, or modify anything. Only `ExecutionGateway.execute()` writes.
- **Reproducibility of tests** — the full suite runs offline, no network access, using monkeypatched `urllib.request.urlopen` / dependency injection. No test hits real Bybit.
- **Deterministic testing + mutation testing** — every hito of consequence includes a manual mutation-testing pass against the real production file (mutate → run suite → confirm caught → restore → verify byte-identity).
- **Exchange boundary isolation** — the only place that constructs Bybit request bodies, parses Bybit response envelopes, or signs requests is within `execution_gateway`'s Bybit-specific adapters; nothing above that boundary knows Bybit's vocabulary (`retCode`, `Buy`/`Sell`, `orderLinkId`, etc.).

---

## 3. High-level component map

```
Phoenix
│
├── phoenix_core                         [IMPLEMENTED, FROZEN — v0.1.0]
│   Immutable domain contracts (Config, Event, Signal, Order, Trade, Portfolio) +
│   ID generation/validation. Zero external dependencies. No trading logic.
│
├── execution_gateway                    [IMPLEMENTED, OPEN — not frozen]
│   │
│   ├── Write side                       [IMPLEMENTED — tested only, not real-validated]
│   │   ExecutionGateway Port (execute) + BybitExecutionGateway Adapter.
│   │   Creates/would-create real orders. See §4.
│   │
│   └── Read side                        [IMPLEMENTED — tested + partially real-validated]
│       ├── Positions                    (Hito 3.70 — ACCEPTED)
│       ├── Open Orders                  (Hito 3.71 — ACCEPTED)
│       ├── Wallet Balance               (Hito 3.72 — ACCEPTED)
│       ├── Instrument Metadata          (Hito 3.73 — ACCEPTED)
│       └── Exchange State Snapshot      (Hito 3.74 — ACCEPTED)
│           Aggregates the four account-wide reads above. See §6.
│
├── Future: Reconciliation Engine        [NOT YET IMPLEMENTED — no code, no Port]
├── Future: Market Regime Engine         [NOT YET IMPLEMENTED]
├── Future: Portfolio Orchestrator       [NOT YET IMPLEMENTED]
├── Future: Bot SDK                      [NOT YET IMPLEMENTED]
└── Future: Dashboard                    [NOT YET IMPLEMENTED]
```

`bots/` and `scripts/` exist as empty placeholder directories (`.gitkeep` only) — no bot code lives in this repository yet.

---

## 4. Execution write-side

**Port:** `ExecutionGateway` (`gateway.py`) — one method, `execute(request: ExecutionRequest) -> ExecutionResult`.
**Domain contracts:** `ExecutionRequest`/`ExecutionResult` (`contracts.py`) — `float`-based (not `Decimal`), frozen dataclasses, no Bybit vocabulary.
**Adapters (three, all implementing the same Port, interchangeable):**
- `BybitExecutionGateway` — translates to/from `BybitCreateOrderRequest`/`BybitCreateOrderResult` via `BybitDemoClient.place_order`, signs with HMAC, calls the private POST stack (`BybitRequestBuilder → HttpRequestExecutor → UrllibHttpTransport`, hardcoded to `POST`).
- `FakeExecutionGateway`, `DryRunExecutionGateway` — non-Bybit implementations for testing/dry runs.

**Error model:** business rejections (`BybitApiError`) translate to `ExecutionResult(status="rejected", ...)`. Infrastructure failures translate to `ExecutionInfrastructureError`, with the original exception preserved as `__cause__`. No `Bybit*` type crosses `execute()` (ADR-001/ADR-001A).

**Validated only by tests, never against real Bybit:** `UrllibHttpTransport.post()`, `BybitCreateOrderOperation`/`BybitCreateOrderPayloadBuilder`, real order-response interpretation, the full POST trading flow, cancellation. **No order has ever been created, filled, or cancelled against a real Bybit environment in this project's history.** Do not infer otherwise from the volume of test coverage.

---

## 5. Execution read-side

Five Ports, all `@runtime_checkable` `Protocol`s, all translating every failure to the same `ExecutionInfrastructureError` (no per-Port error hierarchy). Each has the same three-tier composition: `create_bybit_demo_*_reader` (pure) → `create_configured_bybit_demo_*_reader` (from `BybitDemoExecutionConfig`) → `bootstrap_*_reader_from_env` (loads env) → `query_bybit_demo_*` (one-call public function).

| Primitive | Port | Endpoint | Scope | Auth | Notes |
|---|---|---|---|---|---|
| Positions | `PositionsReader` | `GET /v5/position/list` | account-wide, `category=linear&settleCoin=USDT&limit=200` | private (HMAC) | No pagination — debt, capped at 200 positions. Hedge mode preserved via `(symbol, side)`, not `positionIdx`. Zero-size positions excluded. |
| Open Orders | `OpenOrdersReader` | `GET /v5/order/realtime` | account-wide, same scope, `limit=50` | private | Dual identity preserved (`exchange_order_id`/`order_id`). States: `new`/`partially_filled`/`untriggered`/`triggered`. |
| Wallet Balance | `WalletBalanceReader` | `GET /v5/account/wallet-balance` | account-wide, `accountType=UNIFIED` | private | No pagination (endpoint doesn't document any). Five account totals + per-currency balances in one snapshot. |
| Instrument Metadata | `InstrumentMetadataReader` | `GET /v5/market/instruments-info` | **per-symbol** (`symbol: str` param) | **public, unauthenticated** | Only primitive that isn't account-wide; only one using the public GET stack. Fail-closed on cardinality ≠ 1 and on symbol mismatch. |
| Exchange State Snapshot | `ExchangeStateReader` | *(aggregates the three account-wide above)* | account-wide | private (×3, independent) | See §6. |

Every primitive carries a remote `server_time_ms: int` sourced from Bybit's response envelope (`time` field), never a local clock. Every read is **exactly-once per call, no caching across calls on the same instance** — a behavioral guarantee, verified with spy-based tests, not just a design intent.

---

## 6. ExchangeStateSnapshot

`ExchangeStateSnapshot` (`exchange_state_contracts.py`), produced by `CompositeExchangeStateReader` through the `ExchangeStateReader` Port.

**What it aggregates:** exactly `positions` + `open_orders` + `wallet_balance` — the three account-wide, parameterless read-side primitives (Hitos 3.70–3.72).

**What it deliberately does NOT include:** Instrument Metadata (Hito 3.73). This was a decided architectural boundary, not an oversight — see §7.

**Non-atomicity, modeled explicitly, not hidden:** the three sub-reads are three independent HTTP GETs. `ExchangeStateSnapshot` has **no top-level `server_time_ms`** — a single "summary" timestamp would falsely imply one atomic instant. Instead:

- **`ObservationWindow`** (`earliest_remote_time_ms`, `latest_remote_time_ms`, `remote_time_span_ms`, all stored explicitly) is computed via `min()`/`max()` over the three sub-snapshots' remote `server_time_ms` — never `time.time()`, never a local clock.
- There is **no drift-tolerance field or policy**, deliberately. The snapshot *measures and exposes* drift; deciding what tolerance is acceptable is left to a future consumer (the not-yet-built Reconciliation Engine).
- `ExchangeStateSnapshot.__post_init__` cross-validates that its `observation_window` actually matches a fresh `min()`/`max()` recomputed from its own three sub-snapshots — rejects a window mixed in from a different round.

**Read order:** fixed, sequential — Positions → Open Orders → Wallet Balance. Documented as arbitrary-but-fixed, not a claim about temporal proximity. No concurrency (not demonstrated as necessary).

**Fail-closed on partial failure:** `query_exchange_state()` contains no `try`/`except` at all. Any sub-reader exception propagates unwrapped; readers after the failing one are never called. There is no partial-snapshot code path — either all three succeed and the snapshot is built complete, or nothing is returned.

**No-cache, exactly-once:** two calls to `query_exchange_state()` on the same `CompositeExchangeStateReader` instance issue six real HTTP calls (three per round), never reuse a prior result — verified with a two-round test using *smaller* timestamps in round 2, specifically to catch a "keep the historical max" bug.

**Configuration coherence:** the three sub-readers are built from the same `BybitDemoExecutionConfig` object (loaded once from environment), so they always authenticate with the same `api_key`/`api_secret`/`recv_window_ms`/`timeout_seconds`/base URL. This is now a behaviorally-tested property (`TestConfigCoherenceAcrossSubReaders`), not just an implementation detail.

**What this is:** a **base observational primitive** — the coherent set of remote facts Phoenix observed during one reading round, with enough temporal information for a future consumer to judge how close together those observations were.

**What this is NOT:** a Reconciliation Engine, a Risk Engine, a Repair Engine, or any trading policy. It does not compare observed state against expected/desired state, does not classify mismatches, does not decide what to do about drift, and cannot create, cancel, or modify anything.

---

## 7. Instrument Metadata boundary

Instrument Metadata is per-symbol (`query_instrument_metadata(*, symbol: str)`), while the other three read-side primitives are account-wide with no parameters. Combining a per-symbol primitive into an account-wide aggregate has no single obviously-correct answer — it requires a product decision about scope (all symbols? only symbols already seen in positions/orders? explicit symbol list?).

This was recognized as exactly this kind of ambiguity during Hito 3.74 and resolved by presenting three options to the user rather than choosing arbitrarily:
- **A** (chosen): `ExchangeStateSnapshot` excludes metadata entirely; it remains a fully independent primitive a caller invokes by symbol when needed.
- B (not chosen): an explicit `symbols` parameter on the aggregate.
- C (not chosen): automatic symbol derivation from observed positions/orders.

This is a decided boundary (ADR-002, Hito 3.74 update), not an open question — do not silently revisit it without a new explicit decision.

---

## 8. Error boundaries

```
Remote / transport / response-parsing failure (any kind)
        │
        ▼
ExecutionInfrastructureError  (one shared domain exception, all Ports)
        │
        ▼
Domain-facing Port method (execute() / query_*())
```

- No per-Port exception hierarchy exists — `execute()` and all five `query_*` methods share the same `ExecutionInfrastructureError` for infrastructure failures.
- Business rejections are Port-specific: only the write-side has a concept of "rejected" (`ExecutionResult(status="rejected", ...)`) — a read has no equivalent, since there's no business decision to reject.
- Internal bugs (`TypeError`, `ValueError`, `AssertionError`, `RuntimeError`, `AttributeError`, `KeyError`) are never caught by a generic `except Exception` anywhere in the read-side or in `CompositeExchangeStateReader` — they propagate by identity, distinguishable from `ExecutionInfrastructureError`. This is a tested property (spy-based identity checks), not just an intent.
- The original exception is preserved as `__cause__` when Bybit-specific exceptions are translated to `ExecutionInfrastructureError` — never silently dropped.

---

## 9. Configuration and runtime

- **Environment:** Bybit Demo only (`D-011`). Mainnet/Testnet are explicitly rejected, not just unimplemented.
- **Deployment target:** Railway (`D-008`). As of the last recorded state, **no Railway service is connected to `main`** — `phoenix-smoke-demo` (the only service ever created) was manually deleted after Hito 3.68's real-world validation. `railway.toml` remains in the repo as reference config for a future manual redeploy, not an active service.
- **Region:** any future Bybit-connected Railway service must default to EU West / Amsterdam (`europe-west4`) — US regions are confirmed to fail, evidenced by one A/B test (not an exhaustive region survey).
- **`PYTHONPATH=/app/platform`** is a live, unresolved packaging debt (`D-014`, Decisión 2) — required as a manual Railway environment variable because `railway.toml`'s `buildCommand`/`pip install .` alone reproducibly fails to make `execution_gateway` importable at runtime on Railway's build image, for a cause that is suspected (Railpack layer assembly) but not confirmed. Do not assume this is resolved without checking `docs/decisions.md` D-014 again.
- No component reads environment variables at import time (`D-010`) — configuration is always injected explicitly at construction.

---

## 10. Validation status

| Component | Unit/Integration Tests | Mutation/Adversarial | Real Bybit Validation | Status |
|---|---|---|---|---|
| `phoenix_core` | 142 tests | — | N/A (no external calls) | FROZEN, v0.1.0 |
| Write-side (`ExecutionGateway`/`BybitExecutionGateway`) | Extensive (core hardening + ADR-001/1A) | Yes (historical audits) | **NOT REAL-VALIDATED** — no order ever created against real Bybit | TESTED, AUDITED |
| Authenticated GET connectivity (`smoke_test_bybit_demo_connection`, `/v5/user/query-api`) | Yes | Yes | **REAL-DEMO-VALIDATED** — Hito 3.68, Railway EU West, real `server_time` verified | ACCEPTED |
| Positions Read | 321+ tests | 12/12 detected | NOT REAL-VALIDATED | ACCEPTED (Hito 3.70) |
| Open Orders Read | 280+19 tests | 20/20 (8/8 correction) | NOT REAL-VALIDATED | ACCEPTED (Hito 3.71) |
| Wallet Balance Read | 291+30 tests | 15/16 (13/14 correction) | NOT REAL-VALIDATED | ACCEPTED (Hito 3.72) |
| Instrument Metadata Read | 347+5 tests | 19/20 (5/5 correction) | NOT REAL-VALIDATED | ACCEPTED (Hito 3.73) |
| Exchange State Snapshot | 173+9 tests | 14/16 aggregate + 8/8 config-coherence | NOT REAL-VALIDATED | ACCEPTED (Hito 3.74) |

**The single most important line in this table:** the only real-Bybit validation ever performed in this project's history is the authenticated GET connectivity smoke test (Hito 3.68). Every read-side primitive built since — including `ExchangeStateSnapshot` — is validated exclusively by offline tests against mocked HTTP responses. Do not describe any of them as "validated against Bybit" without qualifying "in tests, not in production."

---

## 11. Known architectural debts

Active as of this document's last update — verify each against `docs/decisions.md` before relying on it, since debts get closed over time:

- **`PYTHONPATH=/app/platform` packaging workaround** (`D-014`, Decisión 2) — unresolved. `railway.toml` is not the complete source of truth for a live service's runtime.
- **Three independent private GET stacks per `ExchangeStateSnapshot` round** — each of Positions/Open Orders/Wallet Balance builds its own transport/sender/api instance from the same config, rather than sharing one. Confirmed (by adversarial audit, Hito 3.74 correction) to be a **performance/object-identity debt only** — configuration values are coherent across the three, this is not a correctness or coherence defect.
- **No pagination on Positions (`limit=200`) or Open Orders (`limit=50`)** — would silently lose data only above those thresholds in a single account; out of scope for current Demo usage.
- **`leverageFilter` non-`Mapping` tolerated as absence** in Instrument Metadata (accepted deuda MENOR, Hito 3.73) — a malformed-but-present block is treated the same as an absent one; only an individual malformed value *inside* a present block fails closed.
- **Env-loader raw `ValueError`** on structurally invalid timeout values, present since Hito 3.65 and replicated (not introduced) by Instrument Metadata's minimal loader (accepted deuda MENOR, Hito 3.73).
- **No Reconciliation Engine, no drift-tolerance policy, no expected-vs-actual comparison exists anywhere in this codebase.** `ExchangeStateSnapshot` measures and exposes observation drift; nothing in Phoenix currently decides what to do about it.

---

## 12. Next architectural boundary

**A Reconciliation Engine** is the direction implied by `ExchangeStateSnapshot`'s design (observation without action, drift measured but not judged) and by the explicit "future Reconciliation Engine" references throughout `docs/decisions.md` (ADR-002 and its Hito 3.72/3.74 updates, and the "Advertencia de no-atomicidad" note under the post-3.72 correction). It has **not been designed or started** — no Port, no contract, no code exists for it, and **its scope has not been decided**. In particular, `docs/decisions.md` does not establish whether it is detection-only or whether it may also take repair actions — do not assume either. Before it can be built, at minimum the following are undecided and must be resolved as their own hito(s), not assumed:

- What "expected/desired state" means and where it comes from
- Identity matching between observed and expected entities
- A drift-tolerance policy (deliberately not decided by `ExchangeStateSnapshot`)
- Mismatch classification
- Stale-round rejection rules
- Whether the engine is detection-only or may also take repair actions — undecided, not to be assumed either way

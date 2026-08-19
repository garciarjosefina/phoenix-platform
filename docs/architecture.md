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
├── Expected Execution State             [IMPLEMENTED, ACCEPTED — domain contracts only, no Port]
│   (Hito 3.76 — accepted after correction + final independent adversarial audit)
│   Pure immutable vocabulary for "what execution state Phoenix
│   asserts should exist" within an explicit scope. NOT a Reconciliation
│   Engine, not wired to ExchangeStateSnapshot. See §13.
│
├── Reconciliation Engine V1             [IMPLEMENTED — pending independent adversarial audit]
│   (Hito 3.77 — Detection & Classification only, explicitly NO repair)
│   Pure function reconcile_execution_state(expected, observed) ->
│   ReconciliationResult. No Port, no I/O, no persistence. See §14.
│
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

**What Instrument Metadata's fields represent (ADR-002, Decisión 6):** exchange-side constraints and capabilities for a symbol — price/quantity/leverage filters (`min_leverage`/`max_leverage`/`leverage_step`, min/max order quantity, tick size, min notional, etc.) describe what Bybit technically permits for that instrument. **They are not** recommended leverage, recommended position sizing, a risk policy, or capital allocation guidance — no code anywhere in this project treats them as such, and none should. A future Risk Engine or Order Validation layer may *consult* these as hard constraints; it must not be built on the assumption that they represent a recommendation.

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

- **Environment:** Bybit Demo only (`D-011`). `Testnet` is excluded and rejected outright. `Mainnet` is not part of the current goal and must not be assumed or implemented by default — but `D-011` does not make this an eternal prohibition: it explicitly allows Mainnet *given a future explicit decision*. Do not build Mainnet support preemptively; do not treat the door as permanently closed either.
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
| Expected Execution State (contracts only) | 137 tests | 24/24 + 13/13 re-verified independently | N/A — pure domain contracts, no I/O | ACCEPTED (Hito 3.76) |
| Reconciliation Engine V1 (Detection & Classification) | 102 tests | 23/24 detected, 1 confirmed equivalent | N/A — pure function, no I/O | PENDING AUDIT (Hito 3.77, not yet accepted) |

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
- **`BybitEndpoint.method` does not govern the HTTP verb on the main production path** (debt since the retrospective Auditoría C, recited in ADR-002 Decisión 2) — `bybit_url_builder.py`/`bybit_endpoint_executor.py`/`urllib_http_transport.py` (the productive POST stack) never read `.method`; the POST stack is hardcoded to POST and the GET stack is a separate, parallel primitive rather than a generalization that honors this field. The one place that *does* read `.method` is the standalone connectivity smoke test (`bybit_demo_connectivity_smoke_test.py`, see below) — a narrow, historical exception, not evidence the field is used productively. Not a bug — a known, accepted, unresolved debt.
- **The authenticated connectivity smoke test (built Hito 3.67, real-validated Hito 3.68) was never migrated to the reusable GET stack** built afterward (Hito 3.70's `HttpGetTransport`/`UrllibGetHttpTransport`) — `bybit_demo_connectivity_smoke_test.py` still uses its own original inline `urllib.request.Request(method="GET")`, documented from the start as an accepted one-off bypass. ADR-002, Decisión 2 records this as explicitly out of scope, not forgotten.

---

## 12. Next architectural boundary

A **Reconciliation Engine V1** now exists (Hito 3.77, pending independent adversarial audit — see §14) as the direction implied by `ExchangeStateSnapshot`'s design (observation without action, drift measured but not judged) and the explicit "future Reconciliation Engine" references throughout `docs/decisions.md`. V1 is deliberately narrow — **Detection & Classification only, explicitly no repair**. Of the items previously listed here as undecided:

- ~~What "expected/desired state" means and where it comes from~~ — **resolved by Hito 3.76**: see §13, `ExpectedExecutionState`. Still undecided: how a real `ExpectedExecutionState` gets *populated* for a live account (a future projection engine).
- ~~Identity matching between observed and expected entities~~ — **resolved by Hito 3.77**: see §14. Positions by `(symbol, side)`; orders by Phoenix `order_id` only, identity-first/scope-second.
- ~~Mismatch classification~~ — **resolved by Hito 3.77**: eleven closed `Divergence` types, see §14.
- **A drift-tolerance policy** — still not decided. `ObservationWindow` is preserved in `ReconciliationResult` (§14) but V1 does not judge it.
- **Stale-round rejection rules** — still not decided; same reason.
- **Whether the engine (beyond V1) may also take repair actions** — still undecided. V1 itself contains zero repair-shaped code (verified by AST — no `cancel`/`repair`/`remediate`/`create_order`/`close_position`/`resize` as real identifiers), but that doesn't settle whether a future version will add it.
- **Account identity** — new item, carried over from ADR-004's MENOR-3: neither `ExpectedExecutionState` nor `ExchangeStateSnapshot` carries account identity; `reconcile_execution_state` presupposes (does not validate) that both inputs belong to the same account/configuration. Any fix must be symmetric and additive to both sides, not patched onto one.

---

## 13. Expected Execution State (Hito 3.76 — ACCEPTED)

Four immutable domain contracts in `expected_execution_state_contracts.py` — pure vocabulary, no Port, no HTTP, no I/O, no Reconciliation Engine, no wiring to `ExchangeStateSnapshot`.

**Exact string identity, no silent normalization — behaviorally tested.** `symbol` and `order_id` are never `strip()`/`upper()`/`lower()`'d anywhere in this module, consistent with the observed read-side (`bybit_positions_response_interpreter.py`/`bybit_open_orders_response_interpreter.py` don't normalize either). `"BTCUSDT"`, `"btcusdt"`, `" BTCUSDT "` are distinct values, preserved exactly, and scope containment/deduplication are case- and whitespace-sensitive (`TestExactStringIdentityNoNormalization`, added in the post-3.76 correction after an audit found this property held in production but was uncovered by tests).

**`ExpectedExecutionScope`** — `symbols: tuple[str, ...]`, no duplicates. Defines *where* the state is authoritative. A symbol outside `scope` is **unknown** (Phoenix asserts nothing) — never "expected flat." An empty scope (`symbols=()`) is valid, by the same precedent as every other collection field in the read-side (empty = legitimate, never an error).

**`ExpectedPosition`** — identity `(symbol, side)`. Fields: `symbol`, `side` (same `"buy"`/`"sell"` vocabulary as `ExecutionPosition`), `quantity` (`Decimal`, finite, `> 0`). Represents the *aggregated* position Phoenix expects for that instrument/side — deliberately without `entry_price`/`leverage`/`unrealized_pnl`/`liquidation_price`/`margin`/`positionIdx`/`bot_id`/`strategy_id`. A zero-quantity expected position is never represented: "flat" is authoritative scope + absence of the corresponding `ExpectedPosition`.

**`ExpectedOpenOrder`** — identity `order_id`, which is **Phoenix's own identity** (conceptually `orderLinkId`), never `exchange_order_id` — Phoenix cannot assert in advance what id the exchange will assign to an order that doesn't exist remotely yet. Fields: `order_id`, `symbol`, `side`, `order_type` (`"market"`/`"limit"`), `quantity` (`Decimal`, finite, `> 0`), `price` (`Decimal | None`, finite, `> 0` when present — **not** coupled to `order_type`, following `ExecutionOpenOrder`'s Hito 3.71 observational precedent rather than the write-side `ExecutionRequest`'s stricter coupling), `reduce_only` (strict `bool`). Deliberately without `exchange_order_id`/`filled_quantity`/`status`/`server_time`/`bot_id`/`strategy_id` — dynamic execution-progress fields are excluded so a future Reconciliation Engine can't confuse legitimate fill progress with divergence; their semantics are for that future hito, not this one.

**`ExpectedExecutionState`** — `scope` + `positions: tuple[ExpectedPosition, ...]` + `open_orders: tuple[ExpectedOpenOrder, ...]`. Invariants enforced in `__post_init__`: every position/order symbol must belong to `scope` (fail-closed — an out-of-scope expectation invalidates construction, never silently dropped); no duplicate `(symbol, side)` among positions; no duplicate `order_id` among orders (two economically-identical orders with different `order_id` **survive** — identity is `order_id` alone); `BUY`/`SELL` of the same symbol coexist (hedge, same principle as Positions Read). Empty `positions`/`open_orders` within a non-empty `scope` is valid and means *expected absence* — not "no opinion."

**Not implemented, on purpose:** no `ExpectedExecutionState.reconcile(snapshot)`, no `ExchangeStateSnapshot.compare(expected)` — verified by AST that the module doesn't import `ExchangeStateSnapshot` and contains no reconciliation vocabulary (`reconcile`/`MATCH`/`MISSING`/`UNEXPECTED`/`MISMATCH`/`repair`) as real code (only legitimate explanatory prose). No persistence, no Canonical Execution Ledger, no projection engine that populates a real `ExpectedExecutionState` from bots/intents — this hito defines the vocabulary only. See ADR-004 for the full architectural reasoning, including why the scope-empty and `price` decisions were resolved from precedent rather than by intuition.

**Two debts registered explicitly for the Reconciliation Engine hito, deliberately not resolved here:**
- **`price` semantics are under-specified.** `ExpectedOpenOrder` currently allows `order_type="limit"` with `price=None` and `order_type="market"` with `price>0` — deliberately, not by oversight (see ADR-004). This does **not** mean either combination is operationally meaningful. Before comparing `price` against `ExecutionOpenOrder`, the Reconciliation Engine must explicitly define the semantics of: `expected.price is None`, `observed.price is None`, a market order with an observed/expected price, and a limit order expected without a price.
- **No timestamp/freshness on `ExpectedExecutionState`, and no account identity on either `ExpectedExecutionState` or `ExchangeStateSnapshot`.** Both are acceptable today (no ledger/projection engine exists to populate a real timestamp; nothing yet compares two accounts against each other), but both need a decision before/during the Reconciliation Engine hito — the account-identity gap in particular must be closed **symmetrically and additively on both sides**, not patched onto `ExpectedExecutionState` alone.

---

## 14. Reconciliation Engine V1 (Hito 3.77 — pending independent adversarial audit)

`reconcile_execution_state(*, expected: ExpectedExecutionState, observed: ExchangeStateSnapshot) -> ReconciliationResult` — a pure module function in `reconciliation_engine.py`, not a Port, no I/O. Not yet accepted; do not treat as a stable public contract until an independent audit closes it (see `docs/progress.md`).

**Scope: Detection & Classification only.** No repair, no cancellation, no order creation, no position closing, no SL/TP/leverage/margin changes, no sizing, no capital allocation, no persistence, no ledger. Verified by AST that the module contains none of `cancel`/`repair`/`remediate`/`create_order`/`close_position`/`resize` as real code (class/function/attribute names) — only as legitimate explanatory prose is any of that vocabulary permitted.

**Purity.** Same style as the rest of `execution_gateway`: `reconciliation_engine.py` imports only `exchange_state_contracts`, `expected_execution_state_contracts`, `reconciliation_contracts`, `reconciliation_precondition_error` — zero Bybit/HTTP/urllib/os/Railway. Same inputs always produce the same `ReconciliationResult`, including divergence order — no local clock, no network, no environment reads, no mutable global state.

**Position identity: `(symbol, side)`, matched only within `expected.scope`.** Same principle as `ExpectedPosition`/`ExecutionPosition`. A position observed outside `expected.scope.symbols` is never classified `UnexpectedExchangePosition` — Phoenix has no authority to assert anything about it. String identity is exact — no `strip()`/`upper()`/`lower()` anywhere in matching.

**Order identity: Phoenix `order_id` only — `exchange_order_id` never participates in matching, not even as a fallback.** `ExpectedOpenOrder.order_id` matches exclusively against `ExecutionOpenOrder.order_id`. An orphan order (`order_id is None`) whose `exchange_order_id` happens to coincide with some expected order's Phoenix `order_id` must never be treated as matched — verified with a dedicated mutation and test.

**Identity-first, scope-second — the central rule for orders.** Order matching runs in two strictly sequential phases:
1. Walk `expected.open_orders`, look up each `order_id` among observed orders — **scope does not participate here**. A matched order can produce multiple field-level divergences (including `OrderSymbolMismatch` if the observed symbol falls outside `expected.scope`) without ever being reclassified as missing/unexpected — identity matching already established it's the same entity.
2. Walk the observed orders **not** matched in phase 1 — only here does scope decide whether to report as unexpected/unattributed or ignore.

Four required scenarios, each with a dedicated test and independent mutation coverage: a matched order whose observed symbol falls outside scope still produces `OrderSymbolMismatch` (never ignored, never split into missing+unexpected); an unmatched order outside scope is ignored; an orphan outside scope is ignored; an orphan inside scope becomes `UnattributedExchangeOpenOrder`.

**Orphan orders (`order_id is None`).** An observed order without Phoenix identity (`exchange_order_id` always present) is classified `UnattributedExchangeOpenOrder` if its symbol is within `expected.scope`, or ignored otherwise. No `order_id` is ever invented; `exchange_order_id` is never substituted as Phoenix identity.

**Eleven divergence types, no free strings.** `Divergence` is a non-instantiable marker base class; eleven concrete `frozen` dataclasses subclass it — three for positions (`MissingExpectedPosition`, `UnexpectedExchangePosition`, `PositionQuantityMismatch`), eight for orders (`MissingExpectedOpenOrder`, `UnexpectedExchangeOpenOrder`, `UnattributedExchangeOpenOrder`, `OrderSymbolMismatch`, `OrderSideMismatch`, `OrderQuantityMismatch`, `OrderTypeMismatch`, `OrderPriceMismatch`). Classification is the Python type itself (`isinstance`), never a free string or generic `Literal` tag. There is no `PositionSymbolMismatch`/`PositionSideMismatch` — a position's identity **is** `(symbol, side)`, so once matched it can only diverge on `quantity`.

**`ReconciliationResult`: `is_in_sync` is a `@property`, never a second field.** `divergences: tuple[Divergence, ...]` is the sole source of truth; `is_in_sync` is derived on every access (`len(divergences) == 0`) — no stored boolean that could, through a construction bug, contradict the actual divergence list. `observation_window` is preserved verbatim from the observed `ExchangeStateSnapshot` — the caller knows which window produced these divergences, but V1 makes no freshness/staleness judgment.

**`price` semantics V1 — closes ADR-004's MENOR-1.** A `ReconciliationPreconditionError` (pure domain exception, not infrastructure — this component does no I/O) aborts, before any matching, if any expected `order_type="limit"` has `price=None` — fail-closed, `None` is never interpreted as "no opinion" or zero. For an expected `market` order, price is **not** part of the V1-reconcilable expectation — `OrderPriceMismatch` is never emitted for a `market`-expected order on price grounds alone, even if `expected.price` happens to be populated (permissive semantics inherited from 3.76, left untouched) or the observed price differs. For a matched `limit` order, comparison against `observed.price` is exact (including `observed.price is None` → `OrderPriceMismatch`). The gate is always `expected.order_type`, never `observed.order_type` — a type mismatch between the two is already reported separately as `OrderTypeMismatch`.

**Partial fills: `expected.quantity` vs `observed.quantity`, never `remaining`.** A legitimate partial fill (`observed.filled_quantity > 0`) is never, by itself, a divergence — `OrderQuantityMismatch` always compares `expected.quantity` against `observed.quantity` (the order's original size), never `observed.quantity - observed.filled_quantity`. Observed `status` never produces a divergence on its own in V1.

**No freshness policy, no account identity — both explicitly presupposed, not validated.** `reconcile_execution_state` assumes `expected` and `observed` belong to the same account/configuration; it cannot validate this (neither contract carries account identity yet — ADR-004's MENOR-3, still open). `ObservationWindow` is carried through for the caller's benefit, but V1 does not decide what counts as "too old."

**Determinism.** `set`/`dict` are used exclusively as internal lookup structures (scope membership, identity indexing) — never as a source of output ordering. Divergence order: (1) `expected.positions` in contractual order, (2) `observed.positions.positions` in contractual order for the unmatched remainder, (3) `expected.open_orders` in contractual order (missing, or matched with mismatches in the fixed field order symbol→side→quantity→order_type→price), (4) `observed.open_orders.orders` in contractual order for the unmatched remainder.

**Mutation battery: 24 specified, 23 detected, 1 confirmed equivalent.** M9 ("a matched order with symbol outside scope is ignored") is equivalent: `ExpectedExecutionState.__post_init__` (Hito 3.76's own invariant) already structurally rejects any `ExpectedOpenOrder.symbol` outside its own `scope` — verified by directly constructing that invalid state and confirming the `ValueError`. The mutated branch is unreachable dead code given that precondition.

# Phoenix Platform — Estado del Proyecto

## Estado actual

**Versión:** `v0.1.0` (tag en `main`)
**Tests:** 471 passing
**Rama activa:** `main`
**Última actualización:** 2026-07-25

---

## Hitos completados

### Fase 1 — Infraestructura base

| Hito | Descripción | Commit |
|------|-------------|--------|
| 1.0 | Repositorio GitHub creado (`garciarjosefina/phoenix-platform`) | `8dbf2ca` |
| 1.1 | Proyecto Railway creado y vinculado al repo | — |
| 1.2 | Estructura de carpetas mínima (`docs/`, `platform/`, `bots/`, `tests/`, `scripts/`) | `0ccd494` |

### Fase 2 — Phoenix Core

| Hito | Descripción | Commit |
|------|-------------|--------|
| 2.1 | Paquete Python inicializado (`pyproject.toml`, `phoenix_core/__init__.py`) | `ebfefa0` |
| 2.2 | Contratos de identidad (`ids.py`) — 5 tipos de ID + `is_valid` | `7c9e0b1` |
| 2.3 | Contrato de eventos (`events.py`) — clase `Event` inmutable | `3b0f36a` |
| 2.4 | Contrato de configuración (`config.py`) — clase `Config` + `get_config()` | `2357492` |
| 2.5 | Contrato de señales (`signals.py`) — clase `Signal` inmutable | `9f468ea` |
| 2.6 | Contrato de órdenes (`orders.py`) — clase `Order` inmutable | `29dad69` |
| 2.7 | Contrato de operaciones (`trades.py`) — clase `Trade` inmutable | `5d66868` |
| 2.8 | Contrato de portfolio (`portfolio.py`) — clase `Portfolio` inmutable | `81999c2` |
| 2.9 | API pública exportada en `__init__.py` con `__all__` | `a70cd2a` |
| 2.10 | Núcleo congelado, README actualizado, tag `v0.1.0` | `9f580e2` |

---

## Cierres de componentes

| Componente | Versión | Estado | Documento |
|------------|---------|--------|-----------|
| Phoenix Core | `v0.1.0` | ✅ Completado | [`docs/components/phoenix-core.md`](components/phoenix-core.md) |

---

## Fase 3 — Execution Gateway

### Hitos planificados

| Hito | Descripción | Commit |
|------|-------------|--------|
| 3.1 | Inicializar paquete `execution_gateway` (`__init__.py` + test de importación) | `fcb8efb` |
| 3.2 | Configuración del gateway (`GatewayConfig`) — environment, dry_run, timeout | `(ver commit 3.2)` |
| 3.3 | Contratos de ejecución (`ExecutionRequest`, `ExecutionResult`) — 37 tests | `8a61025` |
| 3.4 | Interfaz pública (`ExecutionGateway` Protocol) — 11 tests | `461532b` |
| 3.5 | Implementación determinística (`FakeExecutionGateway`) — 15 tests | `748d52b` |
| 3.6 | Gateway dry-run (`DryRunExecutionGateway`) — 18 tests | `fd90fde` |
| 3.7 | Factory del gateway (`create_execution_gateway`) — 10 tests | `44c5fac` |
| 3.8 | Entorno restringido a Bybit Demo (`environment="demo"`) — 21 tests en config | `cfd64cc` |
| 3.9 | Contrato de credenciales Bybit Demo (`BybitDemoCredentials`) — 28 tests | `3ee7df4` |
| 3.10 | Contrato del cliente de órdenes Bybit Demo (`BybitDemoClient`) — 14 tests | `333096a` |
| 3.11 | Adaptador `BybitExecutionGateway` — 19 tests | `40f0c58` |
| 3.12 | Integración de `BybitExecutionGateway` en la factory — 10 tests nuevos | `282478b` |
| 3.13 | Contrato de transporte HTTP (`HttpTransport`) — 17 tests | `680280c` |
| 3.14 | Contrato de serialización JSON (`JsonSerializer`) — 16 tests | `873f1c2` |
| 3.15 | Implementación estándar (`StandardJsonSerializer`) — 32 tests | `0fde1d1` |
| 3.16 | Contrato de reloj en milisegundos (`MillisecondClock`) — 16 tests | `22a013f` |
| 3.17 | Implementación estándar (`SystemMillisecondClock`) — 20 tests | `fb4caf6` |
| 3.18 | Contrato de firma HMAC SHA-256 (`MessageSigner`) — 21 tests | `49be8e9` |
| 3.19 | Implementación estándar (`HmacSha256Signer`) — 22 tests | `(próximo commit)` |

### Próximo hito

Por definir.

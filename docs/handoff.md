# Phoenix Platform — Handoff para nueva sesión

> Leer este archivo primero al retomar el proyecto. Luego leer `progress.md` y `decisions.md`.

---

## Fuente de verdad del proyecto

Estos cuatro archivos son la fuente de verdad. Leerlos al inicio de cada sesión:

1. `docs/handoff.md` — contexto general y protocolo de trabajo
2. `docs/progress.md` — estado actual e hitos completados
3. `docs/decisions.md` — decisiones de arquitectura tomadas
4. `docs/backlog.md` — ideas registradas, pendientes de decisión

**Regla fundamental:** Si la documentación y la memoria del chat se contradicen, prevalece siempre la documentación del repositorio.

---

## Protocolo de trabajo

### Al iniciar una sesión
1. Leer `docs/handoff.md`
2. Leer `docs/progress.md`
3. Leer `docs/decisions.md`

### Al finalizar un hito
1. Actualizar la documentación únicamente si hubo cambios.
2. Hacer commit y push.

### Al completar un componente grande
Antes de comenzar el siguiente componente, crear obligatoriamente:
`docs/components/<nombre-del-componente>.md`

Componentes grandes: Phoenix Core, Execution Gateway, Auditor, Market Regime Engine, Portfolio Orchestrator, Bot SDK, Dashboard, cada bot aprobado.

El cierre debe incluir: nombre/versión, estado, objetivo, funcionalidades, interfaces, archivos, tests, decisiones, limitaciones, backlog, commit/tag y próximo componente. Actualizar también `docs/progress.md` y `docs/handoff.md`.

El documento del componente debe terminar siempre con una sección `## Estado` que lo marque como CONGELADO.

### Componentes congelados

Un componente marcado como **CONGELADO** no debe modificarse salvo para:

- Corrección de bugs.
- Problemas de seguridad.
- Refactorizaciones que no alteren el comportamiento.
- Cambios aprobados explícitamente.

Antes de modificar un componente congelado, documentar la decisión en `docs/decisions.md` y actualizar el documento del componente con el motivo del cambio. No agregar nuevas funcionalidades directamente sobre un componente congelado.

---

## ¿Qué es este proyecto?

Phoenix Platform es una plataforma modular de trading algorítmico. Está siendo construida desde cero con contratos inmutables y arquitectura por capas.

---

## Estado al 2026-07-25

- **Tag activo:** `v0.1.0`
- **Tests:** 1298 passing, 0 failing
- **Python:** 3.14 en local (requisito mínimo: 3.12)
- **Railway:** proyecto creado, sin servicios desplegados
- **GitHub:** `garciarjosefina/phoenix-platform`, rama `main`
- **Fase activa:** Fase 3 — Execution Gateway (Hito 3.34 completado)

---

## Componente en curso: `execution_gateway` (Fase 3)

**Hitos completados:**
- 3.1 — Paquete `execution_gateway` inicializado (`__version__ = "0.1.0"`)
- 3.2 — `GatewayConfig` (`environment`, `dry_run`, `timeout_seconds`), 15 tests
- 3.3 — `ExecutionRequest` y `ExecutionResult` (`contracts.py`), 37 tests
- 3.4 — `ExecutionGateway` Protocol (`gateway.py`), 11 tests
- 3.5 — `FakeExecutionGateway` (`fake_gateway.py`), 15 tests
- 3.6 — `DryRunExecutionGateway` (`dry_run_gateway.py`), 18 tests
- 3.7 — `create_execution_gateway` factory (`factory.py`), 10 tests
- 3.8 — `GatewayConfig.environment` restringido a `"demo"` (D-011), 21 tests en config
- 3.9 — `BybitDemoCredentials` (`credentials.py`), 28 tests
- 3.10 — `BybitDemoClient` Protocol (`bybit_client.py`), 14 tests
- 3.11 — `BybitExecutionGateway` adaptador (`bybit_gateway.py`), 19 tests
- 3.12 — Factory ampliada: `dry_run=False` + `BybitDemoClient` → `BybitExecutionGateway`
- 3.13 — `HttpTransport` Protocol (`http_transport.py`), 17 tests
- 3.14 — `JsonSerializer` Protocol (`json_serializer.py`), 16 tests
- 3.15 — `StandardJsonSerializer` (`standard_json_serializer.py`), 32 tests
- 3.16 — `MillisecondClock` Protocol (`millisecond_clock.py`), 16 tests
- 3.17 — `SystemMillisecondClock` (`system_millisecond_clock.py`), 20 tests
- 3.18 — `MessageSigner` Protocol (`message_signer.py`), 21 tests
- 3.19 — `HmacSha256Signer` (`hmac_sha256_signer.py`), 22 tests
- 3.20 — `BybitAuthentication` + `BybitAuthenticator` (`bybit_authenticator.py`), 38 tests
- 3.21 — `StandardBybitAuthenticator` (`standard_bybit_authenticator.py`), 40 tests
- 3.22 — `BybitHeaderBuilder` (`bybit_header_builder.py`), 31 tests
- 3.23 — `UrllibHttpTransport` (`urllib_http_transport.py`), 45 tests
- 3.24 — `HttpRequest` + `BybitRequestBuilder` (`http_request.py`, `bybit_request_builder.py`), 58 tests
- 3.25 — `HttpRequestExecutor` (`http_request_executor.py`), 47 tests
- 3.26 — `BybitPrivateRequestSender` (`bybit_private_request_sender.py`), 58 tests
- 3.27 — `BybitResponse` (`bybit_response.py`), 59 tests
- 3.28 — `BybitResponseParser` (`bybit_response_parser.py`), 63 tests
- 3.29 — `BybitPrivateApi` (`bybit_private_api.py`), 52 tests
- 3.30 — `BybitEndpoint` (`bybit_endpoint.py`), 58 tests
- 3.31 — `BybitUrlBuilder` (`bybit_url_builder.py`), 52 tests
- 3.32 — `BybitEndpointExecutor` (`bybit_endpoint_executor.py`), 67 tests
- 3.33 — `BYBIT_CREATE_ORDER_ENDPOINT` (`bybit_endpoints.py`), 40 tests — endpoint declarado, operación todavía no implementada
- 3.34 — `BybitCreateOrderRequest` (`bybit_create_order_request.py`), 119 tests — modelo definido, payload y operación todavía no implementados

**Tests totales:** 1298 passing

**Próximo hito:** por definir.

---

## Componente anterior: `phoenix_core` (CONGELADO en v0.1.0)

### Módulos existentes en `platform/phoenix_core/`

| Módulo | Clase/Función principal | Estado |
|--------|------------------------|--------|
| `__init__.py` | API pública con `__all__` | ✅ congelado |
| `ids.py` | `bot_id`, `signal_id`, `order_id`, `trade_id`, `event_id`, `portfolio_id`, `is_valid` | ✅ congelado |
| `config.py` | `Config`, `get_config()` | ✅ congelado |
| `events.py` | `Event` | ✅ congelado |
| `signals.py` | `Signal` | ✅ congelado |
| `orders.py` | `Order` | ✅ congelado |
| `trades.py` | `Trade` | ✅ congelado |
| `portfolio.py` | `Portfolio` | ✅ congelado |

### Tests en `tests/`

```
tests/test_import.py       — importación y API pública
tests/test_ids.py          — generación y validación de IDs
tests/test_config.py       — configuración por defecto
tests/test_events.py       — contrato de eventos
tests/test_signals.py      — contrato de señales
tests/test_orders.py       — contrato de órdenes (market/limit)
tests/test_trades.py       — contrato de operaciones
tests/test_portfolio.py    — contrato de portfolios
```

---

## Cómo correr los tests

```bash
cd /Users/jose/phoenix-platform
python3 -m pytest tests/ -v
```

---

## Qué falta construir

La Fase 3 no está definida todavía. Los candidatos naturales son:

1. **Cliente Bybit** — HTTP wrapper en `platform/` para enviar órdenes reales
2. **Lógica de bots** — primeros bots en `bots/` que emiten `Signal` → `Order`
3. **Servicio Railway** — desplegar el primer bot como servicio en Railway

---

## Qué NO debe modificarse

- `platform/phoenix_core/` — está congelado en `v0.1.0`. No agregar lógica de trading.
- Los tests existentes deben seguir pasando en cada hito.
- `pyproject.toml` — no cambiar `requires-python` ni la configuración de `setuptools` sin documentar en `decisions.md`.
- El tag `v0.1.0` — no mover ni eliminar.

---

## Estructura del repo

```
phoenix-platform/
├── docs/
│   ├── backlog.md      ← ideas pendientes de decisión
│   ├── decisions.md    ← decisiones de arquitectura
│   ├── handoff.md      ← este archivo
│   └── progress.md     ← estado e hitos
├── platform/
│   └── phoenix_core/   ← núcleo congelado v0.1.0
├── bots/               ← vacío (próxima fase)
├── scripts/            ← vacío
├── tests/              ← 142 tests, todos passing
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## Railway

- **Proyecto:** `phoenix-platform`
- **ID:** `07fffce4-ec38-463b-a0a0-6a15fe640134`
- **Workspace:** `garciarjosefina's Projects`
- **Estado:** sin servicios, sin deployments, sin variables
- **CLI:** `railway status` desde `/Users/jose/phoenix-platform`

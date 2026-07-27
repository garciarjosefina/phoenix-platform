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

## Estado al 2026-07-27

- **Tag activo:** `v0.1.0`
- **Tests:** 2404 passing, 0 failing
- **Python:** 3.14 en local (requisito mínimo: 3.12)
- **Railway:** proyecto creado, sin servicios desplegados
- **GitHub:** `garciarjosefina/phoenix-platform`, rama `main`
- **Fase activa:** Fase 3 — Execution Gateway (Hito 3.52 completado)

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
- 3.34 — `BybitCreateOrderRequest` (`bybit_create_order_request.py`), 119 tests
- 3.35 — `BybitCreateOrderPayloadBuilder` (`bybit_create_order_payload_builder.py`), 73 tests
- 3.36 — `BybitCreateOrderOperation` (`bybit_create_order_operation.py`), 71 tests
- 3.37 — `BybitDemoClient.create_order` (`bybit_client.py`), 59 tests — fachada sobre `BybitCreateOrderOperation`; respuesta no interpretada
- 3.38 — `BybitCreateOrderResult` (`bybit_create_order_result.py`), 62 tests — value object de salida (`order_id`, `order_link_id`)
- 3.39 — `BybitCreateOrderResponseInterpreter` (`bybit_create_order_response_interpreter.py`), 73 tests — interpreta `BybitResponse` (ret_code==0) → `BybitCreateOrderResult`; no integrado en operación ni en cliente; `BybitDemoClient.create_order()` continúa devolviendo `BybitResponse`; `ret_code != 0` lanza `ValueError` temporalmente
- 3.40 — Integración del intérprete en `BybitCreateOrderOperation` (`bybit_create_order_operation.py`), 76 tests — cadena completa: `BybitCreateOrderRequest → BybitCreateOrderPayloadBuilder → BYBIT_CREATE_ORDER_ENDPOINT → BybitEndpointExecutor → BybitResponse → BybitCreateOrderResponseInterpreter → BybitCreateOrderResult`; `BybitDemoClient` no modificado
- 3.41 — Adaptación de `BybitDemoClient.create_order` al resultado interpretado (`bybit_client.py`), 64 tests — anotación de retorno cambiada de `BybitResponse` a `BybitCreateOrderResult`; import de `BybitResponse` eliminado; cadena pública completa: `BybitCreateOrderRequest → BybitDemoClient.create_order() → BybitCreateOrderOperation.execute() → BybitCreateOrderResult`; respuestas rechazadas (`ret_code != 0`) generan `ValueError` propagado desde el intérprete a través de la operación; cancelación, consultas y posiciones todavía no implementadas
- 3.42 — Excepción mínima para errores de la API de Bybit (`bybit_api_error.py`), 61 tests — `BybitApiError(Exception)` con campos `ret_code: int` y `ret_msg: str`; keyword-only; mensaje determinista `"Bybit API error {ret_code}: {ret_msg}"`; clasificación de errores y retries pendientes
- 3.43 — Integración de `BybitApiError` en `BybitCreateOrderResponseInterpreter` (`bybit_create_order_response_interpreter.py`), 80 tests — respuestas rechazadas (`ret_code != 0`) ahora lanzan `BybitApiError(ret_code=..., ret_msg=...)` en lugar de `ValueError`; `ret_code` y `ret_msg` conservados en el error; propagación intacta a través de `BybitCreateOrderOperation` y `BybitDemoClient`; clasificación de errores y retries pendientes
- 3.44 — Composition root del flujo de creación de órdenes de Bybit Demo (`bybit_demo_client_factory.py`), 54 tests — `create_bybit_demo_client(*, endpoint_executor: BybitEndpointExecutor) -> BybitDemoClient`; ensambla `BybitCreateOrderPayloadBuilder`, `BybitCreateOrderResponseInterpreter`, `BybitCreateOrderOperation` y `BybitDemoClient`; recibe un `BybitEndpointExecutor` ya construido; no construye transporte, sender ni credenciales; el cliente queda listo para creación de órdenes; respuestas rechazadas generan `BybitApiError`; cancelación, consultas y posiciones todavía no implementadas; configuración desde entorno pendiente
- 3.45 — Prueba integrada de creación de orden desde el gateway público (`test_execution_gateway_create_order_integration.py`), 94 tests — flujo de punta a punta validado en dos secciones: (A) desde `BybitDemoClient.create_order()` con `SpyExecutor`; (B) desde `BybitExecutionGateway.execute()` con `SpyPrivateApi` en la frontera inferior (`BybitPrivateApi`), `BybitEndpointExecutor` y `BybitUrlBuilder` reales; fix de producción mínimo: `place_order()` agregado a `BybitDemoClient` para conectar `BybitExecutionGateway.execute()` → `create_order()` (el `__subclasshook__` ya anticipaba este método); gateway público concreto: `BybitExecutionGateway`; método público probado: `execute()`; frontera simulada en la sección B: `SpyPrivateApi`; recorrido probado desde el gateway, no sólo desde el cliente; no se realizó conexión real con Bybit Demo; transporte, configuración y credenciales productivas continúan pendientes; cancelación, consultas y posiciones no implementadas
- 3.46 — Composition root del gateway público de Bybit Demo (`bybit_demo_execution_gateway_factory.py`), 63 tests — `create_bybit_demo_execution_gateway(*, private_api: BybitPrivateApi) -> BybitExecutionGateway`; ensambla internamente `BybitUrlBuilder` (URL hardcoded `https://api-demo.bybit.com`), `BybitEndpointExecutor` y delega en `create_bybit_demo_client`; recibe únicamente `private_api` ya construido; no lee entorno, no construye transporte ni credenciales; exportado en `__all__`; cobertura completa: API pública, validación, grafo de dependencias, reutilización de factory, múltiples llamadas, ausencia de ejecución en construcción, flujo integrado éxito+rechazo, ausencia de responsabilidades adicionales
- 3.47 — Composition root de `BybitPrivateApi` con dependencias inyectadas (`bybit_private_api_factory.py`), 65 tests — `create_bybit_private_api(*, sender: BybitPrivateRequestSender, response_parser: BybitResponseParser) -> BybitPrivateApi`; recibe `sender` (I/O, transporte, auth, firma) y `response_parser` (puro, contiene `JsonSerializer`) ya construidos; no lee variables de entorno; no recibe API key ni API secret como strings; no construye transporte, sesiones ni credenciales; no firma ni genera headers durante construcción; conserva ambas dependencias por identidad; cada llamada devuelve instancia nueva; validado compositivamente con `create_bybit_demo_execution_gateway`; todavía no existe composition root desde configuración externa; todavía no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.48 — Composition root de `BybitResponseParser` (`bybit_response_parser_factory.py`), 66 tests — `create_bybit_response_parser(*, serializer: JsonSerializer) -> BybitResponseParser`; recibe `serializer` (Protocol `@runtime_checkable`, acepta compatibilidad estructural) ya construido; conserva dependencia por identidad; no ejecuta parsing durante construcción; no llama a `dumps` ni `loads` al construir; no lee variables de entorno; no construye transporte ni sender; composición del sender privado sigue pendiente; todavía no existe composition root desde configuración externa; todavía no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.49 — Composition root de `BybitPrivateRequestSender` (`bybit_private_request_sender_factory.py`), 78 tests — `create_bybit_private_request_sender(*, request_builder: BybitRequestBuilder, request_executor: HttpRequestExecutor) -> BybitPrivateRequestSender`; `request_builder` contiene autenticador (secretos, firma) y serializer; `request_executor` contiene transporte (I/O); ambos inyectados ya construidos; conserva ambas dependencias por identidad; no llama al builder ni executor durante construcción; sin retries; error de transporte propagado por identidad sin wrapping; validado compositivamente hasta gateway; composition root de `BybitRequestBuilder` y `HttpRequestExecutor` sigue pendiente; no existe composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.50 — Composition root de `BybitRequestBuilder` (`bybit_request_builder_factory.py`), 88 tests — `create_bybit_request_builder(*, serializer: JsonSerializer, authenticator: BybitAuthenticator, header_builder: BybitHeaderBuilder) -> BybitRequestBuilder`; `serializer` (Protocol estructural, serializa payload); `authenticator` (Protocol estructural, contiene secretos, firma, reloj); `header_builder` (clase concreta, nominal, pura — inyectada para mantener visibilidad del grafo); conserva las tres dependencias por identidad; no serializa, no autentica, no firma, no consulta reloj durante construcción; error de autenticación propagado por identidad sin retry; validado compositivamente hasta gateway; composition root de `HttpRequestExecutor` y `StandardBybitAuthenticator` sigue pendiente; no existe composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.51 — Composition root de `StandardBybitAuthenticator` (`bybit_authenticator_factory.py`), 97 tests — `create_bybit_authenticator(*, credentials: BybitDemoCredentials, clock: MillisecondClock, signer: MessageSigner, recv_window_ms: int) -> StandardBybitAuthenticator`; `credentials` nominal (`BybitDemoCredentials`); `clock` (Protocol estructural, implementación mínima: `now_ms()`); `signer` (Protocol estructural, implementación mínima: `sign(*, secret, message)`); `recv_window_ms` int > 0, bool rechazado; no llama a clock ni signer durante construcción; error de clock y signer propagado por identidad; satisface `BybitAuthenticator` Protocol; validado compositivamente con `create_bybit_request_builder` hasta gateway; composition root de `HttpRequestExecutor` sigue pendiente; no existe composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.52 — Composition root de `HttpRequestExecutor` (`http_request_executor_factory.py`), 85 tests — `create_http_request_executor(*, transport: HttpTransport, timeout_seconds: float) -> HttpRequestExecutor`; `transport` (Protocol estructural `@runtime_checkable`, acepta cualquier objeto con `post(*, url, headers, body, timeout_seconds)`); `timeout_seconds` int o float > 0, bool rechazado; conserva `transport` por identidad; conserva `timeout_seconds` exactamente; no llama al transporte durante construcción; no abre conexiones ni crea sesiones; errores del transporte propagados por identidad sin wrapping ni retry; validado compositivamente hasta gateway completo; no existe composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes

**Tests totales:** 2404 passing

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

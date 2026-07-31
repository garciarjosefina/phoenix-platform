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

## Estado al 2026-07-31

- **Tag activo:** `v0.1.0`
- **Tests:** 3372 passing, 0 failing
- **Python:** 3.14 en local (requisito mínimo: 3.12)
- **Railway:** proyecto creado, sin servicios desplegados
- **GitHub:** `garciarjosefina/phoenix-platform`, rama `main`
- **Fase activa:** Fase 3 — Execution Gateway (Hito 3.64 completado)

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
- 3.53 — Composition root del transporte HTTP productivo (`http_transport_factory.py`), 62 tests — `create_http_transport() -> UrllibHttpTransport`; sin parámetros: `UrllibHttpTransport.__init__` no recibe dependencias (usa `urllib.request.urlopen` directamente en `post()`); implementación concreta única que satisface `HttpTransport`; no llama a `urlopen` durante construcción; no abre conexiones ni resuelve DNS; no crea cliente ni sesión; errores de red propagados sin retry; validado compositivamente hasta gateway completo; no existe composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.54 — Composition root del serializer JSON productivo (`json_serializer_factory.py`), 76 tests — `create_json_serializer() -> StandardJsonSerializer`; sin parámetros: `StandardJsonSerializer.__init__` no recibe dependencias; delega `dumps` a `json.dumps` y `loads` a `json.loads` sin opciones especiales; satisface `JsonSerializer` Protocol; cada llamada crea instancia nueva (sin singleton); puede compartirse por identidad entre `create_bybit_request_builder` y `create_bybit_response_parser`; no llama a `dumps` ni `loads` durante construcción; no realiza I/O; no lee variables de entorno; no existe composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.55 — Composition root de `BybitHeaderBuilder` (`bybit_header_builder_factory.py`), 64 tests — `create_bybit_header_builder() -> BybitHeaderBuilder`; sin parámetros: `BybitHeaderBuilder.__init__` no recibe dependencias; `build(*, authentication: BybitAuthentication)` produce 5 headers (`X-BAPI-API-KEY`, `X-BAPI-TIMESTAMP`, `X-BAPI-RECV-WINDOW`, `X-BAPI-SIGN`, `Content-Type: application/json`); validación nominal de `BybitAuthentication`; cada llamada crea instancia nueva; no construye headers durante construcción; no realiza I/O; no lee variables de entorno; validado compositivamente con `create_bybit_request_builder` hasta gateway completo; no existe composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.56 — Composition root de `BybitDemoCredentials` desde secretos explícitos (`bybit_demo_credentials_factory.py`), 107 tests — `create_bybit_demo_credentials(*, api_key: str, api_secret: str) -> BybitDemoCredentials`; delega directamente al constructor del dataclass `frozen=True`; `api_key`: str no vacío ni whitespace-only → `ValueError`; tipo no-str → `TypeError` con mensaje `"api_key must be str, got: ..."`, bool rechazado como no-str; `api_secret`: misma validación con mensaje `"api_secret must not be empty or whitespace-only"`; `repr` actual: oculta secreto (`api_secret = field(repr=False)`) — solo muestra `api_key`; factory no lee variables de entorno; no registra ni imprime secretos; no valida credenciales contra Bybit; no crea authenticator, signer ni clock; no ejecuta red; cada llamada crea instancia nueva (sin singleton ni caché); valores no transformados (no strip, no normalización); integrada con `create_bybit_authenticator` y con stack completo hasta gateway; pendiente: composition root desde configuración externa (Railway vars / `.env`); no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.57 — Composition root del `MessageSigner` productivo (`message_signer_factory.py`), 85 tests — `create_message_signer() -> HmacSha256Signer`; sin parámetros; implementación concreta: `HmacSha256Signer`; satisface `MessageSigner` Protocol; algoritmo: HMAC-SHA256; biblioteca: `hmac` + `hashlib` (stdlib); encoding: UTF-8; digest: SHA-256; formato de salida: hexadecimal lowercase, 64 caracteres; acepta secret y message vacíos; no firma durante construcción; no recibe secretos; no lee variables de entorno; conservado por identidad en `StandardBybitAuthenticator._signer`; cada llamada crea instancia nueva; integrado hasta gateway completo; pendiente: composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.58 — Composition root del `MillisecondClock` productivo (`millisecond_clock_factory.py`), 86 tests — `create_millisecond_clock() -> SystemMillisecondClock`; sin parámetros; implementación: `SystemMillisecondClock`; fuente: `time.time_ns()` (ns Unix epoch); unidad: ms; tipo: `int`; truncamiento `// 1_000_000`; no consulta reloj durante construcción; conservado por identidad en `StandardBybitAuthenticator._clock`; cada llamada crea instancia nueva; integrado hasta gateway completo; pendiente: composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.59 — Composition root del recv window de Bybit desde valor explícito (`bybit_recv_window_factory.py`), 90 tests — `create_bybit_recv_window_ms(*, recv_window_ms: int) -> int`; tipo: `int`; `bool` → `TypeError("recv_window_ms must be int, got: bool")`; no-int → `TypeError`; `<= 0` → `ValueError("recv_window_ms must be > 0, got: {v}")`; int > 0 → aceptado sin transformación; subclasses de `int` (no bool): aceptadas; sin límite superior; sin default; no convierte ni normaliza; se inyecta en `StandardBybitAuthenticator._recv_window_ms`; no lee variables de entorno; pendiente: composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.60 — Composition root del timeout HTTP desde valor explícito (`http_timeout_factory.py`), 94 tests — `create_http_timeout_seconds(*, timeout_seconds: int | float) -> int | float`; tipos aceptados: `int` y `float` (no bool); `bool` → `TypeError("timeout_seconds must be int or float, got: bool")`; no-int/no-float → `TypeError("timeout_seconds must be int or float, got: {type}")`; `<= 0` → `ValueError("timeout_seconds must be > 0, got: {v}")`; NaN (float): aceptado (nan ≤ 0 evalúa False en Python); +inf: aceptado; -inf: ValueError; Decimal/Fraction: TypeError; subclasses de `int` y `float` (no bool): aceptadas; sin límite superior; sin default; no convierte (int preservado como int, float como float); se inyecta en `HttpRequestExecutor._timeout_seconds`; no ejecuta HTTP durante composición; no lee variables de entorno; pendiente: composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes
- 3.61 — Composition root de la base URL de Bybit Demo desde valor explícito (`bybit_demo_base_url_factory.py`), 82 tests — `create_bybit_demo_base_url(*, base_url: str) -> str`; tipo: `str` puro; no-str → `TypeError("base_url must be str, got: {type}")`; vacío o solo whitespace → `ValueError("base_url must not be empty or whitespace-only")`; sin `https://` → `ValueError("base_url must start with 'https://', got: ...")`; host vacío (e.g. `"https://"`) → `ValueError("base_url must have a non-empty host, got: ...")`; path presente (incl. trailing slash) → `ValueError("base_url must not contain a path, got: ...")`; query string presente → `ValueError("base_url must not contain a query string, got: ...")`; fragment presente → `ValueError("base_url must not contain a fragment, got: ...")`; subclasses de `str`: aceptadas; valor retornado sin transformación; usa `urlparse` de stdlib; validación idéntica a `BybitUrlBuilder.__init__` pero sin crear el objeto; consumidor principal: `BybitUrlBuilder(base_url=...)` → concatena `self._base_url + endpoint.path`; URL canónica de producción: `"https://api-demo.bybit.com"` (constante privada en `bybit_demo_execution_gateway_factory.py`); factory no hardcodea ninguna URL; no lee variables de entorno; no crea transporte, autenticador ni URL builder; no realiza DNS ni conexiones; integrado con stack completo hasta gateway; pendiente: composition root desde configuración externa; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes

- 3.62 — Composition root integral del Bybit Demo Execution Gateway (`configured_bybit_demo_execution_gateway_factory.py`), 74 tests — `create_configured_bybit_demo_execution_gateway(*, api_key: str, api_secret: str, recv_window_ms: int, timeout_seconds: int | float) -> BybitExecutionGateway`; único composition root de alto nivel que construye el grafo completo (credenciales → signer → clock → recv window → authenticator → serializer → header builder → request builder → response parser → transport → timeout → request executor → sender → private api → gateway) reutilizando exclusivamente las factories de los hitos 3.44–3.61, sin instanciar ninguna clase concreta directamente; **diagnóstico previo:** no existía factory integral equivalente — `create_bybit_demo_execution_gateway` (3.46) es la más cercana pero parte de un `private_api` ya construido, no de secretos crudos; el grafo del hito, tal como fue especificado, listaba `create_bybit_demo_base_url()` como paso intermedio, pero esa factory **no se invoca** en la implementación final: su único consumidor real es `BybitUrlBuilder`, y ese objeto ya se construye internamente dentro de `create_bybit_demo_execution_gateway` (3.46) a partir de la constante privada `_BYBIT_DEMO_BASE_URL`, sin aceptar `base_url` como parámetro; invocar `create_bybit_demo_base_url()` por separado habría producido un valor sin ningún destino en el grafo (llamada muerta) o habría exigido reimplementar la construcción de `BybitUrlBuilder`/`BybitEndpointExecutor`/`BybitDemoClient` en este hito, duplicando lógica ya resuelta en 3.46 — decisión: delegar el ensamblaje final directamente en `create_bybit_demo_execution_gateway(private_api=...)`, que ya reutiliza esa lógica sin modificarla; `create_bybit_demo_base_url` sigue disponible como composition root independiente para cualquier consumidor futuro que sí necesite inyectar una URL explícita; `recv_window_ms` y `timeout_seconds` se validan explícitamente vía `create_bybit_recv_window_ms` y `create_http_timeout_seconds` antes de inyectarse (validación redundante con la interna de `create_bybit_authenticator`/`create_http_request_executor` es preexistente de hitos anteriores, no introducida aquí); `serializer` se construye una sola vez y se comparte por identidad entre `request_builder` y `response_parser`; todos los parámetros externos son keyword-only y sin default (no se inventa ningún valor); cada llamada crea un grafo completamente nuevo (sin singleton, sin caché, sin estado global); no ejecuta HTTP, DNS, sockets, reloj, firma ni autenticación durante la composición; no lee variables de entorno ni archivos; próximo límite arquitectónico: composition root desde configuración externa (Railway vars) todavía no existe — este hito compone el grafo desde valores explícitos, no desde el entorno; no se validó conexión real con Bybit Demo; cancelación, consultas y posiciones pendientes

- 3.62-fix — Corrección post-auditoría del Hito 3.62 (`tests/test_execution_gateway_configured_bybit_demo_execution_gateway_factory.py`, sin cambios en `platform/`), 84 tests — auditoría independiente (Opus 5) sobre el commit `823e6b8` clasificó `CORREGIR HITO 3.62`; hallazgo importante: 9 de los 10 tests de `TestIdentity` usaban `assert x is not None` o `isinstance(...)`, que no detectan sustitución ni duplicación de dependencias — confirmado empíricamente mutando la composición (serializer no compartido entre `request_builder`/`response_parser`) y observando que 9 tests seguían pasando; corrección: `TestIdentity` reescrita para espiar cada factory inferior importada dentro del módulo (vía `monkeypatch.setattr(_module, nombre, spy)`), capturar el objeto real retornado, y comparar por `is` contra el objeto efectivamente hallado en el grafo construido (`_build_with_capture`); 15 identidades/valores verificados así: credentials, signer, clock, recv_window_ms (valor+tipo), authenticator, serializer (compartido entre builder y parser), header_builder, request_builder, response_parser, transport, timeout_seconds (valor+tipo), request_executor, sender, private_api, gateway; se agregó `TestIdentityMutationSensitivity` con sustitución real de signer y transport, y un contador de invocaciones de `create_json_serializer` (debe ser exactamente 1); re-ejecutar la mutación original de la auditoría contra la suite corregida confirma que `test_serializer_identity_shared_between_builder_and_parser` ahora falla como se espera, y que la suite vuelve a pasar en verde contra la composición real sin mutar; hallazgo menor H2 (test tautológico `hasattr(factory, "send_order")`) eliminado — la ausencia de envío de órdenes ya está cubierta conductualmente por `test_no_http_post_during_construction`; hallazgo menor H3 corregido: se agregaron spies que lanzan si `StandardJsonSerializer.dumps`, `StandardJsonSerializer.loads` o `BybitHeaderBuilder.build` son invocados durante la composición, confirmando conductualmente su ausencia (antes sólo se verificaba por inspección estática del código fuente); no corregidos en este commit (fuera de alcance, deuda documentada en la auditoría): doble validación de `recv_window_ms`/`timeout_seconds` (preexistente de 3.51/3.52) y ausencia de consumidor productivo de `create_bybit_demo_base_url` (deuda de diseño de 3.61); `configured_bybit_demo_execution_gateway_factory.py` no fue modificada — la composición productiva ya era correcta, sólo faltaba la prueba

- 3.63 — Configuración tipada e inmutable de Bybit Demo (`bybit_demo_execution_config.py`), 111 tests — `BybitDemoExecutionConfig` (`@dataclass(frozen=True)`) con exactamente cuatro campos: `api_key: str`, `api_secret: str = field(repr=False)`, `recv_window_ms: int`, `timeout_seconds: int | float`; encapsula únicamente los cuatro valores externos que hoy recibe `create_configured_bybit_demo_execution_gateway`, sin agregar `base_url` ni `environment`; validación en `__post_init__` **reutilizando** las composition roots existentes (`create_bybit_demo_credentials`, `create_bybit_recv_window_ms`, `create_http_timeout_seconds`) en lugar de reescribir los checks a mano — los valores retornados por esas factories se descartan (nunca reemplazan los campos: no hay transformación, no hay strip, no hay conversión); mensajes y tipos de excepción son **byte-idénticos** a las factories inferiores, verificado con tests parametrizados de paridad directa; NaN y +inf siguen aceptados en `timeout_seconds` (mismo contrato que 3.60, sin corregirlo aquí); `repr()`/`str()` ocultan `api_secret` (heredado de `field(repr=False)`, mismo patrón que `BybitDemoCredentials`), `api_key` permanece visible (mismo contrato que el value object existente); igualdad por valor (semántica normal de dataclass, sin identidad personalizada); sin `slots` (no es convención existente en el proyecto); superficie mínima: sin `from_env`, `from_dict`, `load`, `parse`, `to_dict`, `masked`, `validate` ni ningún método público más allá de los generados por `dataclass`; construir el objeto no lee entorno, no lee archivos, no consulta reloj, no firma, no serializa, no ejecuta HTTP/DNS, no construye el gateway, transporte ni authenticator (verificado con spies); **no se modificó** `create_configured_bybit_demo_execution_gateway` — todavía recibe los cuatro valores sueltos; la adaptación de la factory integral para aceptar este config queda para el Hito 3.64; todavía no existe carga desde variables de entorno ni Railway (Hito 3.65); todavía no existe bootstrap de aplicación (Hito 3.66) ni conexión real con Bybit Demo (Hito 3.67); cancelación, consultas y posiciones siguen pendientes; `execution_gateway` permanece abierto, no congelado

- 3.64 — Composition root integral adaptado para recibir `BybitDemoExecutionConfig` (`configured_bybit_demo_execution_gateway_factory.py`), 107 tests — firma nueva: `create_configured_bybit_demo_execution_gateway(*, config: BybitDemoExecutionConfig) -> BybitExecutionGateway`; **firma anterior eliminada por completo** (`api_key`, `api_secret`, `recv_window_ms`, `timeout_seconds` sueltos) — sin wrapper legacy, sin overload, sin deprecation warning; una llamada con la firma antigua falla naturalmente con `TypeError: unexpected keyword argument`; validación nominal explícita al inicio (`isinstance(config, BybitDemoExecutionConfig)`), rechaza `None`, `dict`, `tuple`, objetos arbitrarios y objetos estructurales con los mismos cuatro atributos (duck typing rechazado — la validación es nominal, no estructural); internamente la factory lee `config.api_key`, `config.api_secret`, `config.recv_window_ms`, `config.timeout_seconds` y los pasa **sin transformación** (verificado por identidad para los strings y por valor+tipo para los numéricos) a exactamente el mismo grafo de composición aceptado en el Hito 3.62 — ninguna factory inferior fue modificada, ninguna se agregó ni se quitó; se conservan las llamadas a `create_bybit_demo_credentials`, `create_bybit_recv_window_ms` y `create_http_timeout_seconds` como composition roots productivos aunque el config ya validó esos valores en su propio `__post_init__` (no se elimina la doble validación preexistente de 3.51/3.52/3.59/3.60, sigue fuera de alcance); el config no se muta, no se reemplaza, no se serializa (`dataclasses.asdict` nunca se invoca) y no se reconstruye dentro de la factory (verificado con spy sobre `BybitDemoExecutionConfig.__init__`); reutilizar el mismo objeto `config` en dos llamadas produce dos grafos completamente independientes; excepciones de factories inferiores sustituidas por spies (`create_bybit_demo_credentials`, `create_bybit_authenticator`, `create_http_request_executor`, `create_bybit_demo_execution_gateway`) propagan por identidad exacta, sin envolver; los 15 tests de identidad, los 3 de sensibilidad a mutación y todos los spies de ausencia de ejecución (reloj, firma, authenticate, dumps, loads, header build, HTTP, DNS, socket, entorno, archivos) del Hito 3.62 se conservaron intactos, sólo adaptados a construir el `config` antes de invocar la factory; correcciones menores aplicadas al Hito 3.63 (sin tocar producción del config): se agregaron 4 tests de orden de validación (`api_key` → `api_secret` → `recv_window_ms` → `timeout_seconds`, se detiene en el primero inválido) y se reemplazó la assertion tautológica de fuga de secreto por un marcador inequívoco (`ZZTOPSECRETMARKER9999`); siguiente límite arquitectónico: carga segura de `BybitDemoExecutionConfig` desde variables de entorno / Railway (Hito 3.65) — todavía no se leen variables de entorno en ningún punto de la cadena; todavía no existe bootstrap de aplicación (3.66) ni conexión real con Bybit Demo (3.67); cancelación, consultas y posiciones siguen pendientes; `execution_gateway` permanece abierto, no congelado

**Tests totales:** 3372 passing

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

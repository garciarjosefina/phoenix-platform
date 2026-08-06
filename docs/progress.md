# Phoenix Platform — Estado del Proyecto

## Estado actual

**Versión:** `v0.1.0` (tag en `main`)
**Tests:** 3695 passing
**Rama activa:** `main`
**Última actualización:** 2026-08-03

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
| 3.19 | Implementación estándar (`HmacSha256Signer`) — 22 tests | `cb54d54` |
| 3.20 | Contrato de autenticación (`BybitAuthentication` + `BybitAuthenticator`) — 38 tests | `30f351a` |
| 3.21 | Implementación estándar de autenticación (`StandardBybitAuthenticator`) — 40 tests | `2ad9ed4` |
| 3.22 | Constructor de headers privados (`BybitHeaderBuilder`) — 31 tests | `8be2e77` |
| 3.23 | Implementación HTTP estándar (`UrllibHttpTransport`) — 45 tests | `f363f55` |
| 3.24 | Constructor de solicitud HTTP preparada (`HttpRequest` + `BybitRequestBuilder`) — 58 tests | `6eab0ab` |
| 3.25 | Ejecutor de solicitudes HTTP preparadas (`HttpRequestExecutor`) — 47 tests | `2eb8750` |
| 3.26 | Emisor de solicitudes privadas de Bybit Demo (`BybitPrivateRequestSender`) — 58 tests | `36f30be` |
| 3.27 | Resultado normalizado de respuesta privada Bybit Demo (`BybitResponse`) — 59 tests | `108772b` |
| 3.28 | Parser de respuesta privada Bybit Demo (`BybitResponseParser`) — 63 tests | `1464b56` |
| 3.29 | Servicio de solicitud privada Bybit Demo con respuesta normalizada (`BybitPrivateApi`) — 52 tests | `f54f772` |
| 3.30 | Value object de endpoint privado Bybit Demo (`BybitEndpoint`) — 58 tests | `42a58cf` |
| 3.31 | Constructor de URL para endpoints Bybit Demo (`BybitUrlBuilder`) — 52 tests | `3055157` |
| 3.32 | Ejecutor de endpoint privado Bybit Demo (`BybitEndpointExecutor`) — 67 tests | `9ba22f7` |
| 3.33 | Endpoint privado de creación de órdenes Bybit Demo (`BYBIT_CREATE_ORDER_ENDPOINT`) — 40 tests | `affd531` |
| 3.34 | Value object de solicitud de creación de orden Bybit Demo (`BybitCreateOrderRequest`) — 119 tests | `641d916` |
| 3.35 | Constructor de payload HTTP para creación de orden Bybit Demo (`BybitCreateOrderPayloadBuilder`) — 73 tests | `1ecb45b` |
| 3.36 | Operación de creación de orden Bybit Demo (`BybitCreateOrderOperation`) — 71 tests | `5e5a4e3` |
| 3.37 | Integración de creación de órdenes en `BybitDemoClient` — 59 tests | `7cc9ea5` |
| 3.38 | Value object de resultado de creación de orden (`BybitCreateOrderResult`) — 62 tests | `4485485` |
| 3.39 | Intérprete de respuesta exitosa de creación de orden (`BybitCreateOrderResponseInterpreter`) — 73 tests | pendiente |
| 3.40 | Integración del intérprete en `BybitCreateOrderOperation` — 76 tests | `cd54d06` |
| 3.41 | Adaptación de `BybitDemoClient.create_order` al resultado interpretado — 64 tests | `579cd6a` |
| 3.42 | Excepción mínima para errores de la API de Bybit (`BybitApiError`) — 61 tests | `64bd6e1` |
| 3.43 | Integración de `BybitApiError` en `BybitCreateOrderResponseInterpreter` — 80 tests | `262de33` |
| 3.44 | Composition root del flujo de creación de órdenes de Bybit Demo (`create_bybit_demo_client`) — 54 tests | `ace253b` |
| 3.45 | Prueba integrada de creación de orden desde el gateway público — 94 tests | `a82ad6a` |
| 3.46 | Composition root del gateway público de Bybit Demo (`create_bybit_demo_execution_gateway`) — 63 tests | `ff292a4` |
| 3.47 | Composition root de `BybitPrivateApi` con dependencias inyectadas (`create_bybit_private_api`) — 65 tests | `2725245` |
| 3.48 | Composition root de `BybitResponseParser` (`create_bybit_response_parser`) — 66 tests | `937bd82` |
| 3.49 | Composition root de `BybitPrivateRequestSender` (`create_bybit_private_request_sender`) — 78 tests | `96dd94b` |
| 3.50 | Composition root de `BybitRequestBuilder` (`create_bybit_request_builder`) — 88 tests | `7e2cdab` |
| 3.51 | Composition root de `StandardBybitAuthenticator` (`create_bybit_authenticator`) — 97 tests | `4201e20` |
| 3.52 | Composition root de `HttpRequestExecutor` (`create_http_request_executor`) — 85 tests | `215ea0b` |
| 3.53 | Composition root del transporte HTTP productivo (`create_http_transport`) — 62 tests | `409f6bc` |
| 3.54 | Composition root del serializer JSON productivo (`create_json_serializer`) — 76 tests | `a7a67cc` |
| 3.55 | Composition root de `BybitHeaderBuilder` (`create_bybit_header_builder`) — 64 tests | `b7c3f02` |
| 3.56 | Composition root de `BybitDemoCredentials` desde secretos explícitos (`create_bybit_demo_credentials`) — 107 tests | `713daf6` |
| 3.57 | Composition root del `MessageSigner` productivo (`create_message_signer`) — 85 tests | `1051ebe` |
| 3.58 | Composition root del `MillisecondClock` productivo (`create_millisecond_clock`) — 86 tests | `4cfb461` |
| 3.59 | Composition root del recv window de Bybit desde valor explícito (`create_bybit_recv_window_ms`) — 90 tests | `17fec78` |
| 3.60 | Composition root del timeout HTTP desde valor explícito (`create_http_timeout_seconds`) — 94 tests | `c593df9` |
| 3.61 | Composition root de la base URL de Bybit Demo desde valor explícito (`create_bybit_demo_base_url`) — 82 tests | `8c4159d` |
| 3.62 | Composition root integral del Bybit Demo Execution Gateway (`create_configured_bybit_demo_execution_gateway`) — 74 tests | `823e6b8` |
| 3.62-fix | Corrección post-auditoría (Opus): pruebas de identidad reales por `is`, sensibilidad a mutación, ausencia conductual de serialización/headers — 84 tests (solo tests, sin cambios en `platform/`) | `1844512` |
| 3.63 | Configuración tipada e inmutable de Bybit Demo (`BybitDemoExecutionConfig`) — 111 tests | `3a5e59f` |
| 3.64 | Composition root integral adaptado para recibir `BybitDemoExecutionConfig` (firma anterior eliminada) — 107 tests de la factory + 4 tests de orden de validación en el config | `857ebe4` |
| ADR-001 | `ExecutionGateway` como Port del dominio; `BybitExecutionGateway` como Adapter (traducción `ExecutionRequest`↔`BybitCreateOrderRequest`/`ExecutionResult`↔`BybitCreateOrderResult`, sin exponer tipos Bybit fuera del adaptador) — 39 tests nuevos, 4 archivos de test migrados | `2ac7678` |
| ADR-001A | Camino de error del Port desacoplado de Bybit: `BybitApiError` (rechazo de negocio) se traduce a `ExecutionResult(status="rejected")`; excepciones de infraestructura se traducen a `ExecutionInfrastructureError` (nuevo tipo de dominio, `message: str`, encadenada vía `__cause__`) — ningún tipo `Bybit*` cruza `execute()` en ningún camino | `f23374d` |
| Core Hardening Pack A | Cierre de la Auditoría Retrospectiva A: clasificación fail-closed de errores Bybit (allowlist de rechazo explícita), eliminación del catch-all genérico, mensajes de infraestructura saneados, `HttpRequest`/`BybitResponse` inmutables en profundidad, `repr` seguro (`BybitAuthentication.signature`, headers), `GatewayConfig` con validación estricta, `create_execution_gateway` desacoplado de Bybit, cantidades/precios sin notación científica, verificación de correlación `order_link_id`, incompatibilidad de longitud sin vocabulario Bybit, pureza de dominio simétrica — suite 3463→3587 (+124 tests netos) | `db0888d` |
| Corrección final Auditoría A | Respuestas remotas no interpretables (`UnicodeDecodeError`, JSON malformado, esquema inválido, claves/tipos ausentes) se normalizan a `BybitResponseProcessingError` en la frontera inferior (`bybit_private_api.py`, `bybit_response_parser.py`, `bybit_create_order_response_interpreter.py`) y el gateway las traduce a `ExecutionInfrastructureError`; sin `except Exception`; `HttpRequest` acepta cualquier `Mapping` (corrige el round-trip roto) — suite 3587→3695 (+108 tests netos) | `2d03cc2` |
| Corrección Auditoría B | Cierre de los hallazgos H1/H2 de la Auditoría Retrospectiva B: `create_http_timeout_seconds` (única fuente de verdad, sin duplicar en otras capas) ahora exige `math.isfinite(timeout_seconds)` — `NaN` y `+inf` pasaban antes toda la validación y escapaban como `ValueError`/`OverflowError` crudos dentro de `socket.settimeout()` al no ser `OSError`; `BybitDemoExecutionConfig` hereda el rechazo automáticamente por delegación existente, sin cambios propios. `BybitRequestBuilder` protegido con pruebas de comportamiento (statelessness entre llamadas `.build()` consecutivas con la misma instancia) — sin cambios de producción en el builder. 4 mutaciones verificadas y detectadas (NaN aceptado, +inf aceptado, builder cachea `body`, builder cachea `authentication`) — suite 3695→3719 (+24 tests netos) | `260a7d9` |
| Corrección Auditoría C | Cierre del hallazgo C1 de la Auditoría Retrospectiva C: el test que cubría `_BYBIT_DEMO_BASE_URL` comparaba la constante contra sí misma (`assert url_builder._base_url == _BYBIT_DEMO_BASE_URL`), por lo que un cambio accidental Demo→Mainnet en la propia constante no rompía la suite. Reemplazado por tres pruebas que fijan el literal productivo `"https://api-demo.bybit.com"` — incluida una que verifica la URL realmente alcanzada por `UrllibHttpTransport.post` en un flujo `execute()` completo, no sólo el atributo interno del url builder. Sólo tests modificados; ninguna factory ni composition root tocados (la implementación ya apuntaba correctamente a Demo). Mutación Demo→Mainnet verificada como detectada (antes: 3719/3719 passing con la mutación activa; después: 3 tests fallan) — suite 3719→3721 (+2 tests netos) | `3f3f5f5` |
| 3.65 | Carga segura de `BybitDemoExecutionConfig` desde variables de entorno (`load_bybit_demo_execution_config_from_env`) — lee `PHOENIX_BYBIT_DEMO_API_KEY`, `PHOENIX_BYBIT_DEMO_API_SECRET`, `PHOENIX_BYBIT_RECV_WINDOW_MS`, `PHOENIX_HTTP_TIMEOUT_SECONDS` con mapping inyectable (`environ=None` usa `os.environ`, releído cada llamada, sin caché); conversión mínima (`int`/`float`) delegando toda validación semántica a `BybitDemoExecutionConfig`; nueva excepción `EnvironmentConfigurationError` sólo para variable ausente o conversión estructural inválida; sin `.env`, sin dotenv, sin Railway SDK, sin defaults ocultos; no construye el gateway ni conecta con Bybit; 8 mutaciones detectadas — 109 tests nuevos, suite 3721→3830 (+109 tests netos) | `418a0ba` |
| 3.66 | Bootstrap seguro del Bybit Demo Execution Gateway desde entorno (`bootstrap_bybit_demo_execution_gateway_from_env`) — une exclusivamente `load_bybit_demo_execution_config_from_env` (3.65) → `create_configured_bybit_demo_execution_gateway` (3.64), sin llamar factories inferiores ni instanciar clases concretas; `environ` delegado por identidad (`None` o mapping explícito, sin copiar/mutar/mezclar con `os.environ`); orden fijo loader→root verificado con spies, errores de ambas capas propagados por identidad sin envolver; retorno es el gateway exacto del composition root (`is`); grafo nuevo por llamada, sin singleton/caché; sin I/O durante la construcción (red, reloj, firma, autenticación, serialización, headers, transporte, órdenes); secretos ausentes de `repr`/`str`/errores, verificado con marcador; corrección menor del Hito 3.65 incluida (sólo tests): `test_environment_configuration_error_message_never_contains_marker` era vacuo por un merge de dicts que sobrescribía el marcador, corregido invirtiendo el orden; 8 mutaciones detectadas — 96 tests nuevos, suite 3830→3926 (+96 tests netos) | `af81c1d` |
| 3.67 | Smoke test seguro de conectividad y autenticación Bybit Demo, sólo lectura (`smoke_test_bybit_demo_connection`) — flujo `environ → bootstrap (3.66) → GET autenticado → SmokeTestResult`, sin construir manualmente el grafo; endpoint `GET /v5/user/query-api` (Query API Key Information: sin parámetros, verifica credenciales/firma/timestamp/recv_window/permisos, no toca órdenes/posiciones/balances); el transporte existente está hardcodeado a POST (deuda ya documentada en Auditoría C), así que la llamada GET se implementa con un `urllib.request.Request` propio reutilizando el authenticator y el `BybitHeaderBuilder` reales del grafo — nada se reconstruye a mano; `ret_code != 0` → `BybitApiError` (sin excepción nueva); `SmokeTestResult` (frozen, `success`/`endpoint`/`environment`/`server_time`/`account_type`) nunca expone api_key/secret/firma/headers; 8 mutaciones detectadas — 88 tests nuevos, suite 3926→4014 (+88 tests netos) | `fce1a4c` |
| 3.68A | Runner one-shot seguro para el smoke test de Bybit Demo (`bybit_demo_smoke_runner.py`) — `def main() -> int` invoca `smoke_test_bybit_demo_connection(environ=None)` exactamente una vez (sin retry, sin loop, sin segunda llamada en `finally`); comando `python3 -m execution_gateway.bybit_demo_smoke_runner` (diagnosticado: `platform/` no es un paquete Python, `python -m platform.execution_gateway...` no es una ruta válida); salida saneada determinista — éxito imprime `PHOENIX_BYBIT_DEMO_SMOKE_TEST_SUCCESS` + 5 campos exactos (`NONE` literal para opcionales ausentes), fallo imprime `PHOENIX_BYBIT_DEMO_SMOKE_TEST_FAILURE` + `error_type`/`error_message`, nunca traceback ni `repr(result)`; clasificación sin excepción nueva — `EnvironmentConfigurationError`/errores de validación de config usan `str(error)` (seguro por contrato), `BybitApiError` usa mensaje genérico fijo, `OSError` (cubre `HTTPError`/`URLError`/`TimeoutError` por herencia, sin importar `urllib.error` ni `socket`) usa mensaje genérico, cualquier excepción no clasificada usa `"Unexpected smoke test failure"` sin `str(error)`; `KeyboardInterrupt`/`SystemExit` no capturados; exit codes exactamente 0/1; no conoce Railway (sin SDK, sin `RAILWAY_*`, sin `railway.json/toml`); no exportado desde `__init__.py`; 10 mutaciones detectadas (la de "ejecución durante el import" verificada inyectando la línea real en el archivo, confirmando fallo en la sola colección de tests, y restaurando sin dejar rastro) — 96 tests nuevos, suite 4014→4110 (+96 tests netos) | `1347bd5` |
| 3.69 | Preparación del despliegue one-shot en Railway (`railway.toml`, defecto real corregido en `pyproject.toml`) — diagnóstico en venv temporal fuera del repo (nunca commiteado) reveló que `pip install .` **fallaba siempre**: `build-backend = "setuptools.backends.legacy:build"` no existe en ningún `setuptools` (confirmado con 83.0.0); corregido a `setuptools.build_meta` (el estándar PEP 517), **con confirmación explícita del usuario antes de tocar el archivo**; verificado en un segundo venv temporal contra el repo real: `pip install .` instala, `import execution_gateway` funciona sin `PYTHONPATH`, y el runner corre sin red real dos veces (falla esperada sin credenciales, éxito con `urlopen` sustituido) — ambos venvs eliminados al terminar; `railway.toml` mínimo — `buildCommand = "python3 -m pip install ."`, `startCommand = "python3 -m execution_gateway.bybit_demo_smoke_runner"` — deliberadamente sin restart policy, healthcheck, dominio, cron, réplicas, IDs ni variables `PHOENIX_*` (todo eso es manual en el dashboard); `tests/test_railway_smoke_service_config.py` parsea con `tomllib` (stdlib) e incluye 2 tests de instalación real en venv temporal; 10 mutaciones detectadas sobre el archivo real (Start Command incorrecto, `python -c`, build que no instala el proyecto, dependencia de `PYTHONPATH`, servidor web, variable `PHOENIX_*`, secret, retry/loop, Mainnet, módulo inexistente); no se creó el servicio Railway, no se usó CLI/API, sin conexión real — 40 tests nuevos, suite 4110→4150 (+40 tests netos) | `bd3aff5` |

### Próximo hito

Configuración manual en el dashboard de Railway: crear el servicio `phoenix-smoke-demo`, conectar el repo, desactivar autodeploy, `Restart Policy = Never`, sin dominio, sin cron, cargar las variables `PHOENIX_BYBIT_DEMO_*`/`PHOENIX_HTTP_TIMEOUT_SECONDS` selladas, y disparar la corrida una sola vez.

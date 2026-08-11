# Phoenix Platform — Decisiones de Arquitectura

> Regla: nunca eliminar entradas. Solo agregar nuevas.

---

## D-001 — Lenguaje: Python 3.12+

**Fecha:** 2026-07-23
**Decisión:** El proyecto usa Python 3.12 como versión mínima (`requires-python = ">=3.12"`).
**Razón:** Soporte a largo plazo, `type hints` modernos (`float | None`), `dataclasses` maduras.
**Nota:** El entorno local corre Python 3.14, que satisface el requisito.

---

## D-002 — Paquete en `platform/`

**Fecha:** 2026-07-23
**Decisión:** El código fuente de `phoenix_core` vive en `platform/phoenix_core/`, no en la raíz.
**Razón:** Separar el núcleo reutilizable del código de bots (`bots/`) y scripts (`scripts/`).
**Configuración:** `pyproject.toml` con `[tool.setuptools.package-dir] "" = "platform"`.

---

## D-003 — Contratos inmutables con `dataclasses(frozen=True)`

**Fecha:** 2026-07-23
**Decisión:** Todas las clases de contrato (`Config`, `Event`, `Signal`, `Order`, `Trade`, `Portfolio`) son `frozen=True`.
**Razón:** Los contratos no deben mutar después de crearse. Facilita razonamiento y concurrencia.
**Implicación:** Los campos que requieren valores por defecto mutables (dict, list) usan `field(default_factory=...)`.

---

## D-004 — IDs con UUID4 y prefijo semántico

**Fecha:** 2026-07-23
**Decisión:** Todos los IDs siguen el formato `{prefix}_{uuid4}` (ej. `bot_<uuid>`, `signal_<uuid>`).
**Razón:** Identificación inmediata del tipo de entidad solo mirando el ID. Facilita debugging en logs.
**Función de validación:** `is_valid(value, prefix)` en `ids.py`.

---

## D-005 — Sin dependencias externas en el núcleo

**Fecha:** 2026-07-23
**Decisión:** `phoenix_core` usa únicamente librería estándar de Python.
**Razón:** El núcleo debe ser portable, instalable y testeable sin instalar nada.
**Alcance:** Esta restricción aplica solo a `phoenix_core`. Las capas superiores (bots, servicios) pueden tener dependencias.

---

## D-006 — Timestamps siempre en UTC

**Fecha:** 2026-07-23
**Decisión:** Todos los timestamps se generan con `datetime.now(timezone.utc)` y se serializa con `.isoformat()`.
**Razón:** Evitar ambigüedad de zona horaria en un sistema distribuido.
**Formato de salida:** ISO 8601 con offset `+00:00`.

---

## D-007 — `pyproject.toml` como único archivo de configuración del proyecto

**Fecha:** 2026-07-23
**Decisión:** Se usa `pyproject.toml` con `setuptools` como build backend. No hay `setup.py`, `setup.cfg`, ni `requirements.txt`.
**Razón:** Estándar moderno de Python. Unifica configuración de build y herramientas (pytest) en un solo archivo.

---

## D-008 — Railway como plataforma de despliegue

**Fecha:** 2026-07-23
**Decisión:** Los servicios de producción se despliegan en Railway.
**Estado actual:** Proyecto `phoenix-platform` creado en Railway (ID `07fffce4-ec38-463b-a0a0-6a15fe640134`), sin servicios activos todavía.

---

## D-010 — Configuración por inyección, no por lectura automática

**Fecha:** 2026-07-23
**Decisión:** Los módulos de `execution_gateway` no leen variables de entorno ni archivos en tiempo de importación. La configuración se inyecta explícitamente al construir instancias (`GatewayConfig(...)`).
**Razón:** Evitar efectos secundarios al importar. Facilita testing determinístico y despliegues en múltiples entornos sin cambiar el código.
**Alcance:** Todo componente dentro de `execution_gateway`. Las credenciales y variables de entorno se inyectarán en una capa superior cuando corresponda.

---

## D-009 — `docs/` como fuente de verdad del proyecto

**Fecha:** 2026-07-23
**Decisión:** Los archivos `docs/progress.md`, `docs/decisions.md` y `docs/handoff.md` son la fuente de verdad. Se actualizan al finalizar cada hito.
**Razón:** El contexto del chat no persiste entre sesiones. La documentación garantiza continuidad.
**Regla:** Leer estos archivos antes de comenzar cualquier trabajo nuevo.

---

## D-012 — Contratos internos antes de SDKs externos

**Fecha:** 2026-07-25
**Decisión:** Las dependencias externas de Phoenix se incorporan primero mediante contratos internos mínimos y después mediante implementaciones concretas. El dominio no debe depender directamente de SDKs o librerías de proveedores externos.

---

## D-013 — `BybitDemoClient` convertido de Protocol a clase concreta con compatibilidad estructural

**Fecha:** 2026-07-26
**Decisión:** `BybitDemoClient` fue convertido de `Protocol` (con `@runtime_checkable`) a clase concreta con `ABCMeta` y `__subclasshook__`. El `__subclasshook__` replica el comportamiento estructural del Protocol: cualquier clase que defina `place_order` pasa el `isinstance` check, preservando la compatibilidad con `BybitExecutionGateway` y los tests existentes.
**Razón:** El Hito 3.37 requería agregar un constructor con dependencias y un método concreto (`create_order`). Un Protocol con métodos concretos adicionales los habría incluido en `__protocol_attrs__`, rompiendo los `isinstance` checks existentes. La solución con `ABCMeta` + `__subclasshook__` conserva el comportamiento estructural sin necesidad de modificar archivos fuera del alcance.
**Consecuencias:**
- Los tests existentes de `BybitExecutionGateway` y `BybitDemoClient` continúan pasando sin modificación.
- `BybitDemoClient` puede ahora instanciarse directamente como cliente concreto.
- La verificación estructural de `place_order` sigue funcionando via `__subclasshook__`.

---

## D-011 — Bybit Demo como único entorno soportado

**Fecha:** 2026-07-25
**Decisión:** `GatewayConfig.environment` acepta únicamente el valor `"demo"` (Bybit Demo). El valor predeterminado es `"demo"`.
**Razón:** Phoenix opera exclusivamente en Bybit Demo. No existe necesidad actual de testnet ni mainnet.
**Consecuencias:**
- `testnet` queda excluido y rechazado explícitamente.
- `mainnet` no se implementará salvo decisión explícita futura.
- No se agrega soporte preventivo para entornos no requeridos.
- La validación es estricta y sensible a mayúsculas y minúsculas (`"DEMO"` y `"Demo"` son inválidos).

---

## ADR-001 — `ExecutionGateway` como Port del dominio; `BybitExecutionGateway` como Adapter

**Fecha:** 2026-08-01
**Decisión:** `ExecutionGateway` (Protocol) y sus contratos `ExecutionRequest`/`ExecutionResult` son el único vocabulario público del dominio para ejecutar órdenes. `BybitExecutionGateway` es un Adapter: traduce internamente `ExecutionRequest → BybitCreateOrderRequest` antes de invocar `BybitDemoClient.place_order`, y `BybitCreateOrderResult → ExecutionResult` al recibir la respuesta. Ningún tipo `Bybit*` cruza la frontera pública `execute(request: ExecutionRequest) -> ExecutionResult`.
**Razón:** Una auditoría retrospectiva del núcleo (Auditoría A) encontró que `BybitExecutionGateway.execute` delegaba directamente `self._client.place_order(request)` sin traducir, por lo que en producción sólo aceptaba `BybitCreateOrderRequest` y devolvía `BybitCreateOrderResult` — incumpliendo la anotación pública del Protocol `ExecutionGateway`. `isinstance(gw, ExecutionGateway)` daba `True` pese a que el gateway rechazaba el tipo que el Protocol declara. Las otras dos implementaciones del mismo Protocol (`DryRunExecutionGateway`, `FakeExecutionGateway`) sí respetaban el contrato, por lo que las tres no eran intercambiables.
**Mapeo de traducción (dentro de `BybitExecutionGateway`, único lugar donde ocurre):**
- `side`: `"buy"/"sell"` → `"Buy"/"Sell"`; `order_type`: `"market"/"limit"` → `"Market"/"Limit"`.
- `quantity`/`price`: `float` → `Decimal(str(valor))` (evita artefactos de precisión binaria).
- `order_link_id` (Bybit) = `order_id` (dominio) — el id de dominio se reutiliza como clave de idempotencia del exchange.
- `time_in_force="GTC"` y `reduce_only=False`: decisiones del adaptador: el dominio no modela estos conceptos.
- `ExecutionResult.order_id` conserva el id de dominio original (no el id que genera Bybit); `ExecutionResult.exchange_order_id` transporta el id que devuelve Bybit; `status="accepted"` (el endpoint de creación de orden sólo confirma aceptación, no fill).
**Consecuencias:**
- Las tres implementaciones de `ExecutionGateway` (`DryRunExecutionGateway`, `FakeExecutionGateway`, `BybitExecutionGateway`) vuelven a ser intercambiables bajo el mismo Protocol.
- Las excepciones (`BybitApiError`, errores de transporte) siguen propagándose sin envolver — el adaptador no introduce manejo de errores nuevo.
- `gateway.py` y `contracts.py` no importan ningún tipo `Bybit*` (verificado con tests dedicados de pureza de dominio).
- No se modificó ninguna factory inferior ni el Composition Root: la firma de `BybitExecutionGateway.__init__` no cambió.

---

## ADR-001A — Camino de error del Port desacoplado de Bybit

**Fecha:** 2026-08-01
**Decisión:** `BybitApiError` nunca cruza `execute()`. Los rechazos de negocio se traducen a `ExecutionResult(status="rejected", error_message=error.ret_msg)`; los errores de infraestructura se traducen a la nueva excepción de dominio `ExecutionInfrastructureError(message=...)`, con el `BybitApiError`/excepción original conservado en `__cause__`.
**Razón:** Auditoría independiente del ADR-001 encontró que, aunque el camino feliz ya traducía correctamente, `BybitApiError` seguía atravesando el Port sin traducir en el camino de rechazo, rompiendo la sustituibilidad (LSP) entre `DryRunExecutionGateway`, `FakeExecutionGateway` y `BybitExecutionGateway`.
**Limitación reconocida y corregida en el Core Hardening Pack A (ver abajo):** la primera implementación de este ADR clasificaba *todo* `BybitApiError` como rechazo de negocio (`except BybitApiError: return rejected`) y usaba `except Exception` + `message=str(error)` para el resto. Ambas decisiones fueron corregidas — ver Core Hardening Pack A, Partes A–C.

---

## Core Hardening Pack A — Cierre de la Auditoría Retrospectiva A

**Fecha:** 2026-08-03
**Contexto:** La Auditoría Retrospectiva A (auditoría independiente del núcleo `execution_gateway`, posterior al ADR-001/ADR-001A) clasificó el núcleo como no apto para congelarse, con hallazgos bloqueantes e importantes. Este paquete los resuelve en una única pasada coordinada.

**A — Clasificación explícita de errores Bybit.** `BybitExecutionGateway` mantiene un clasificador privado, `_ORDER_REJECTION_RET_CODES = frozenset({10001, 110003, 110004, 110007})`: sólo estos códigos, verificados y respaldados por caso de uso, se traducen a `ExecutionResult(status="rejected")`. Cualquier otro `ret_code` — incluidos autenticación (10003), firma (10004), rate limit (10006/429), timestamp (10002), servidor (10016) y **cualquier código desconocido** — se trata de forma conservadora (fail-closed) como `ExecutionInfrastructureError`. Nunca como rechazo normal.

**B — Ausencia de catch-all.** `except Exception` fue eliminado. El adaptador sólo captura `(OSError, json.JSONDecodeError)` — los únicos tipos concretos que la cadena real de transporte (`urllib.error.URLError`/`HTTPError`, timeouts de socket, y `json.loads` sobre un body no-JSON) puede producir. `TypeError`, `ValueError` genérico, `AttributeError`, `KeyError`, `AssertionError` y `RuntimeError` propagan sin envolver: representan defectos de programación, no fallos operacionales.

**C — Mensajes seguros.** `ExecutionInfrastructureError` nunca recibe `message=str(error)`. Usa una constante fija (`"Bybit execution infrastructure failure"`); el detalle técnico original queda exclusivamente en `__cause__`, nunca en el mensaje que cruza al dominio. No se copia `ret_msg` ni se expone `ret_code`.

**D — Inmutabilidad profunda de `HttpRequest`.** `headers` se envuelve en `MappingProxyType` tras una copia defensiva en `__post_init__`; la anotación pública pasa a `Mapping[str, str]`. Cambio imprescindible relacionado: `UrllibHttpTransport.post` valida `isinstance(headers, Mapping)` en lugar de `isinstance(headers, dict)` (un `MappingProxyType` no es `dict`).

**E — `BybitResponse` inmutable recursivamente.** `result`/`ret_ext_info` se congelan con `_deep_freeze`: `dict`→`MappingProxyType`, `list`→`tuple`, `set`→`frozenset`, recursivamente. Compatible con `BybitCreateOrderResponseInterpreter` sin cambios (`MappingProxyType` es `Mapping`).

**F — `repr` seguro.** `BybitAuthentication.signature` usa `field(repr=False)` (mismo patrón que `BybitDemoCredentials.api_secret`); `api_key` permanece visible por coherencia. `HttpRequest` reemplaza el `__repr__` autogenerado por uno que muestra la URL y **sólo los nombres** de los headers, nunca sus valores, y oculta el body por completo.

**G — `GatewayConfig` estricto.** `environment` exige `str` no vacío/whitespace (sin `strip`); `dry_run` exige `bool` exacto (rechaza `"true"`, `1`, etc.); `timeout_seconds` exige `int` con `bool` explícitamente rechazado — mismo patrón que el resto del núcleo.

**H — Factory genérica desacoplada de Bybit.** `create_execution_gateway(config: GatewayConfig) -> ExecutionGateway` — se eliminó el parámetro `client: BybitDemoClient | None`. Con `dry_run=False` lanza `ValueError("Live execution requires a dedicated composition root for the selected adapter.")`, sin nombrar ningún exchange. `create_configured_bybit_demo_execution_gateway` (Hito 3.64) sigue siendo el único composition root para ejecución real con Bybit.

**I — Cantidades y precios finitos, sin notación científica.** Nueva función privada `_to_plain_decimal` en el adaptador: rechaza `NaN`/`+inf`/`-inf` con `ExecutionRequestNotSupportedError` antes de construir el `Decimal`. Cambio imprescindible relacionado, verificado matemáticamente (no existe forma de que `Decimal.__str__` evite notación científica para magnitudes extremas sin intervenir en el punto de serialización): `BybitCreateOrderPayloadBuilder` usa `format(valor, "f")` en lugar de `str(valor)` para `qty`/`price`, garantizando representación decimal plana.

**J — Verificación de correlación `order_link_id`.** El adaptador compara `BybitCreateOrderResult.order_link_id` contra `ExecutionRequest.order_id` antes de devolver `status="accepted"`. Ante una discordancia, lanza `ExecutionInfrastructureError` (mensaje seguro, sin vocabulario Bybit) en lugar de confirmar una orden cuya identidad no puede verificarse.

**K — Incompatibilidad de longitud sin vocabulario Bybit.** El adaptador valida `len(request.order_id) <= 36` **antes** de construir `BybitCreateOrderRequest`, evitando que el mensaje `"order_link_id must be at most 36 characters"` escape al dominio. Ante incompatibilidad, lanza la nueva excepción `ExecutionRequestNotSupportedError(message="Execution request cannot be represented by the selected adapter")` — misma excepción reutilizada por la Parte I para valores no finitos: ambas son, conceptualmente, "el adaptador elegido no puede representar esta solicitud de dominio válida".

**L — Pureza de dominio simétrica.** `tests/test_execution_gateway_domain_purity.py` aplica la misma regla (sin imports, sin nombres, sin mensajes que nombren un exchange) a `gateway.py`, `contracts.py`, `execution_infrastructure_error.py`, `execution_request_not_supported_error.py` y `factory.py` por igual — la asimetría original (que dejaba pasar `BybitDemoClient` en `factory.py`) queda cerrada.

**Archivos de producción modificados:** `bybit_gateway.py`, `execution_infrastructure_error.py` (sin cambios de código, ya correcto), `http_request.py`, `bybit_response.py`, `bybit_authenticator.py`, `config.py`, `factory.py`, `__init__.py`; y, por necesidad estrictamente demostrada, `urllib_http_transport.py` (Parte D) y `bybit_create_order_payload_builder.py` (Parte I).
**Archivo nuevo:** `execution_request_not_supported_error.py`.
**No modificado:** `phoenix_core`, `BybitDemoClient`, authenticator, request builder, sender, serializer, factories inferiores, Composition Root. Sin dependencias nuevas.
**Deuda que permanece fuera de alcance (documentada, no bloqueante):** duplicación de la constante de longitud 36 entre `BybitCreateOrderRequest`/`BybitCreateOrderResult`/el adaptador; `time_in_force`/`reduce_only` fijados rígidamente por el adaptador (el dominio no modela vigencia ni reduce-only); doble validación preexistente de `recv_window_ms`/`timeout_seconds` entre composition roots y sus consumidores (hitos 3.51/3.52/3.59/3.60). No existe conexión real con Bybit Demo.

---

## Corrección final de Auditoría A — `BybitResponseProcessingError`

**Fecha:** 2026-08-03
**Decisión:** Se introduce `BybitResponseProcessingError` (`bybit_response_processing_error.py`) como excepción interna, específica de Bybit, que representa exclusivamente: *la respuesta remota fue recibida, pero no pudo decodificarse, parsearse o interpretarse*. Nunca forma parte del dominio ni cruza `execute()`. `BybitExecutionGateway` captura únicamente `(OSError, BybitResponseProcessingError)` y los traduce a `ExecutionInfrastructureError(message="Bybit execution infrastructure failure")`, con la excepción original en `__cause__`.
**Razón:** La reauditoría del Core Hardening Pack A demostró, mediante integración productiva real sustituyendo sólo `urlopen`, que 6 de 7 respuestas malformadas ya recibidas de la red (body no-UTF8, JSON inválido, esquema con claves/tipos incorrectos) escapaban como excepción cruda (`UnicodeDecodeError`, `KeyError`, `TypeError`) en lugar de clasificarse como el fallo operacional ambiguo que representan.
**Principio arquitectónico permanente establecido:** la traducción de un error concreto y conocido a un tipo normalizado ocurre siempre en el componente que sabe de dónde proviene ese error — nunca mediante un `except Exception` amplio en una capa superior. `bybit_private_api.py` traduce `UnicodeDecodeError` (frontera entre transporte genérico y procesamiento Bybit); `bybit_response_parser.py` traduce `JSONDecodeError` y los fallos de construcción de `BybitResponse`; `bybit_create_order_response_interpreter.py` traduce los fallos de construcción de `BybitCreateOrderResult`. El gateway, en el nivel más alto, sólo captura tipos ya normalizados y concretos — nunca vuelve a inspeccionar el origen técnico del error.
**Consecuencias:**
- `UrllibHttpTransport` permanece exchange-agnóstico (no se le agregó ningún tipo Bybit); la traducción vive en la capa que ya es Bybit-específica.
- `HttpRequest.headers` pasa a aceptar cualquier `Mapping[str, str]` válido (antes exigía `dict` exacto, rompiendo el round-trip con sus propios headers ya expuestos).
- Verificado con batería de mutación (8/8 detectadas), incluida una mutación que reveló un hueco real de cobertura en `bybit_private_api.py` (mensaje sin sanear), cerrado antes de commitear.

---

## D-014 — EU West (Amsterdam) como región Railway por defecto para Bybit; `PYTHONPATH` como deuda técnica de packaging

**Fecha:** 2026-08-07
**Contexto:** Cierre del Hito 3.68 — primera ejecución real del smoke test (`execution_gateway.bybit_demo_smoke_runner`) desde el servicio Railway `phoenix-smoke-demo` contra Bybit Demo.

**Decisión 1 — Región:** Todo servicio Railway que interactúe con la API de Bybit se despliega, por defecto, en **EU West (Amsterdam, Netherlands / `europe-west4`)**, salvo decisión explícita en contrario documentada.
**Razón:** A/B limpio, mismo commit y misma configuración salvo una única variable: región US West (California) → `HTTPError` (la conexión y el TLS se establecieron, el rechazo fue de la aplicación — consistente con bloqueo geográfico de Bybit); región EU West (Amsterdam) → `success=True`. Coincide con la región donde ya opera `fib-shadow-canary` contra Bybit.
**Alcance de la evidencia:** sólo se probaron dos regiones. La regla validada es "no desplegar en regiones de EE. UU.", no "EU West es la única región válida" — Southeast Asia u otras regiones no estadounidenses no fueron descartadas ni confirmadas.

**Decisión 2 — Deuda técnica registrada:** la variable de entorno `PYTHONPATH=/app/platform`, cargada manualmente en `phoenix-smoke-demo`, es un **workaround aceptado, no una solución definitiva**.
**Razón:** El primer deploy falló con `ModuleNotFoundError: No module named 'execution_gateway'` pese a que `railway.toml` ejecuta `python3 -m pip install .` sin error. Diagnóstico aislado — `git archive HEAD` (commit exacto, sin cambios sin commitear) reconstruido en un venv limpio fuera del repo, reproduciendo literalmente el `buildCommand` — confirmó con evidencia (79 entradas del wheel, `execution_gateway/` completo con sus 66 archivos, módulo importado y ejecutado con éxito desde un directorio ajeno al repo, sin `PYTHONPATH`) que `pyproject.toml`/`tool.setuptools.package-dir`/`tool.setuptools.packages.find` empaquetan e instalan correctamente el paquete. La causa más probable —no confirmada— es el ensamblado de capas de Railpack: los Build Logs muestran un paso `copy /mise/installs, ..., /app` posterior a `python3 -m pip install .`, que podría descartar el `site-packages` recién escrito.
**Consecuencia no deseada:** `railway.toml` deja de ser la fuente completa de verdad del runtime del servicio — recrear `phoenix-smoke-demo` únicamente desde el repositorio, sin agregar `PYTHONPATH` manualmente en el dashboard, reproduciría el mismo `ModuleNotFoundError`. Compromete el objetivo de reproducibilidad perseguido por los Hitos 3.69 y la corrección post-3.69.
**Pendiente (explícitamente no resuelto en el Hito 3.68):** investigar la causa exacta del ensamblado de Railpack y restaurar la reproducibilidad completa del servicio exclusivamente desde config-as-code, sin variables manuales en el dashboard.
**No existe conexión real con Bybit Mainnet en ningún momento; ambas decisiones surgen de ejecuciones reales contra Bybit Demo.**

---

## ADR-002 — `PositionsReader` como Port de lectura separado del Port de ejecución; primitiva HTTP GET nueva en vez de generalizar la existente

**Fecha:** 2026-08-07
**Contexto:** Hito 3.70 — primera capacidad productiva de lectura de estado real de Bybit (posiciones), base de la futura Reconciliation Engine/Portfolio Orchestrator/Risk Engine.

**Decisión 1 — Port nuevo, no extensión del existente.** Se introduce `PositionsReader` (`positions_reader.py`, Protocol `@runtime_checkable`, único método `query_positions(self) -> PositionsSnapshot`), implementado por `BybitPositionsReader`. **No** se agregó ningún método de lectura a `ExecutionGateway`/`BybitDemoClient`.
**Razón:** `ExecutionGateway.execute()` es, por diseño desde el ADR-001, el único Port de escritura del dominio. Mezclar una operación de lectura ahí habría acoplado dos responsabilidades con ciclos de vida, garantías de idempotencia y modelos de error distintos — una lectura no tiene noción de "rechazo de negocio" (no existe el equivalente de una orden rechazada por riesgo), a diferencia de `execute()`. Precedente directo: la separación Port/Adapter que el ADR-001 ya estableció para escritura se extiende aquí, simétricamente, a lectura.
**Traducción de errores:** `BybitPositionsReader.query_positions()` traduce **todo** fallo (`BybitApiError` para cualquier `ret_code` — no sólo un subconjunto de códigos de rechazo, porque no existe esa categoría en lectura —, `BybitResponseProcessingError`, `OSError`) a `ExecutionInfrastructureError`, la misma excepción de dominio que ya usa el Port de escritura (ADR-001A/Core Hardening Pack A) — **sin inventar una jerarquía nueva.** Ningún tipo `Bybit*` cruza `query_positions()`, verificado con tests dedicados.

**Actualización (Hito 3.71):** `OpenOrdersReader`/`BybitOpenOrdersReader` (`open_orders_reader.py`/`bybit_open_orders_reader.py`) se suman como segundo Port de lectura hermano de `PositionsReader`, bajo exactamente los mismos tres principios de esta Decisión 1 — Port separado del de escritura, mismo patrón de traducción total de errores a `ExecutionInfrastructureError`, mismo split Bybit↔dominio sin tipos `Bybit*` cruzando el Port. No se crea un ADR nuevo porque no hay ninguna decisión arquitectónica adicional que declarar: `OpenOrdersReader` es una aplicación directa de la misma decisión ya tomada aquí, no una variación de ella. Ambos Ports reutilizan, sin duplicar, exactamente la misma primitiva GET de la Decisión 2.

**Decisión 2 — Primitiva HTTP GET nueva y paralela, no generalización de la existente.** La cadena POST productiva (`BybitRequestBuilder`→`HttpRequestExecutor`→`UrllibHttpTransport`) está hardcodeada a POST; `BybitEndpoint.method` es metadata declarada pero nunca consumida por `BybitEndpointExecutor`/`BybitUrlBuilder` (deuda ya documentada desde la Auditoría C/Hito 3.67). Se evaluó generalizar esos tres componentes para honrar `endpoint.method` y se descartó explícitamente.
**Razón:** los tres componentes tienen 45-90 tests cada uno y sostienen todo el camino de creación de órdenes ya auditado y considerado correcto — tocarlos para una primera lectura habría sido una refactorización amplia sin necesidad demostrada, exactamente lo que el hito pedía evitar sin autorización explícita.
**Alternativa elegida:** una primitiva GET nueva, mínima y paralela — `HttpGetTransport` (Protocol) + `UrllibGetHttpTransport` + `HttpGetRequestExecutor` + `BybitPrivateGetRequestSender` + `BybitPrivateGetApi` —, mismo split de responsabilidades 1:1 que su equivalente POST, pero **reutilizando sin duplicar** `BybitAuthenticator`/`BybitHeaderBuilder`/`BybitResponseParser`/credenciales/`recv_window`/`timeout_seconds` ya existentes y ya auditados. `BybitAuthenticator.authenticate(body=...)` ya era genérico (firma cualquier string, no específicamente un JSON body) — reutilizado sin cambios para firmar la query string de un GET, exactamente como Bybit V5 lo especifica.
**Consecuencia explícita:** el patrón ad-hoc del Hito 3.67 (un `urllib.request.Request(method="GET")` inline dentro del propio smoke test, documentado ahí como bypass aceptado *una sola vez*) queda generalizado en un primitivo reutilizable — el smoke test 3.67 en sí **no fue tocado ni migrado** a esta primitiva; sigue con su implementación inline original. Migrar 3.67 a `HttpGetTransport` queda fuera de alcance de este hito.

**Decisión 3 — Alcance de consulta fijado a `category=linear&settleCoin=USDT&limit=200`, sin paginación.**
**Razón:** Phoenix opera únicamente derivados lineares de Bybit (mismo alcance que `BybitCreateOrderPayloadBuilder`, Hito 3.35). `settleCoin` es obligatorio en la API V5 de Bybit cuando no se filtra por `symbol`. `limit=200` es el máximo de página soportado por Bybit.
**Deuda documentada, no bloqueante:** no se implementa paginación (`nextPageCursor`) en este hito. Con el límite máximo de página ya solicitado, sólo se perdería información con más de 200 posiciones simultáneas en una única cuenta — escenario fuera de alcance para Demo. Pendiente si un consumidor real lo requiere.

**Decisión 4 — Posiciones de tamaño 0 excluidas del snapshot, hedge mode preservado sin `positionIdx`.**
**Razón:** Bybit devuelve entradas placeholder (`size="0"`, frecuentemente `side="None"`) para representar "sin posición" en ciertos escenarios de consulta. Modelarlas como `ExecutionPosition(quantity=0)` violaría el propio invariante del contrato (`quantity > 0`) y confundiría "ausencia" con "posición". En hedge mode, Bybit distingue las dos piernas de una posición por `(symbol, side)` con ambos lados no-cero — suficiente para no colapsarlas sin necesitar exponer `positionIdx` (vocabulario Bybit) en el contrato de dominio.

**Archivos nuevos:** `positions_contracts.py`, `positions_reader.py`, `bybit_positions_reader.py`, `bybit_positions_response_interpreter.py`, `bybit_private_get_api.py`, `bybit_private_get_request_sender.py`, `http_get_request_executor.py`, `http_get_transport.py`, `urllib_get_http_transport.py`, `bybit_demo_positions_reader_factory.py`, `configured_bybit_demo_positions_reader_factory.py`, `bybit_demo_positions_reader_env_bootstrap.py`, `bybit_demo_positions_query.py`.
**Archivos existentes extendidos (aditivo, sin romper contratos):** `bybit_endpoints.py` (+`BYBIT_POSITIONS_ENDPOINT`), `__init__.py` (+exports).
**No modificado:** `contracts.py`, `gateway.py`, `bybit_gateway.py`, `bybit_client.py`, `factory.py`, `bybit_request_builder.py`, `http_request_executor.py`, `urllib_http_transport.py`, `http_transport.py`, `bybit_demo_connectivity_smoke_test.py` — ningún componente del Port de escritura ni del smoke test 3.67 fue tocado.
**Sin conexión real con Bybit en este hito; sin ninguna orden creada, cancelada o modificada.**

---

## Corrección post-3.70 — Hallazgos IMPORTANTES de la auditoría independiente

**Fecha:** 2026-08-11
**Contexto:** Auditoría independiente del Hito 3.70 (modelo distinto al que implementó el hito) clasificó `CORREGIR HITO 3.70`, con tres hallazgos IMPORTANTES que bloqueaban que `PositionsReader` fuera una base segura para reconciliación futura, y uno adicional (IMPORTANT-4) resuelto documentalmente. Los hallazgos MENORES quedaron explícitamente fuera de alcance de esta corrección.

**IMPORTANT-1 — Fail-closed ante paginación (`bybit_positions_response_interpreter.py`).** La auditoría demostró empíricamente que un `nextPageCursor` no vacío se ignoraba en silencio: el interpreter devolvía un `PositionsSnapshot` "completo" que en realidad podía estar truncado, sin ninguna señal para el consumidor. Corregido: `interpret()` ahora lanza `BybitResponseProcessingError` si `result.get("nextPageCursor")` es truthy — cualquier valor no vacío, incluido whitespace-only, se trata como señal de paginación pendiente. Ausencia de la clave o cadena vacía se tratan igual (sin señal). **No se implementa el follow-up de cursor** — sigue siendo deuda documentada, ahora con la garantía de que su ausencia falla ruidosamente en vez de corromper silenciosamente el snapshot.

**IMPORTANT-2 — Campos accesorios opcionales (`positions_contracts.py`, `bybit_positions_response_interpreter.py`).** La auditoría demostró que `leverage=""` (respuesta real y válida de Bybit para cuentas Unified en portfolio margin) abortaba la consulta completa, dejando al motor sin visibilidad de *todas* las posiciones por una sola fila con un campo no esencial en blanco. Corregido: `ExecutionPosition.leverage`/`unrealized_pnl` pasan a `Decimal | None = None`; el interpreter trata `""` y ausencia de clave como `None` para ambos, pero sigue validando estrictamente cualquier valor presente y no vacío (un `leverage="abc"` sigue fallando cerrado — nunca se acepta un accesorio malformado en silencio). **`symbol`/`side`/`quantity`/`entry_price` permanecen obligatorios sin cambios.** Se evaluó explícitamente `avgPrice="0"` y se decidió **no** relajar su validación: por construcción sólo se evalúa para filas con `quantity > 0` ya confirmada, y Bybit no documenta ningún caso de una posición realmente abierta con precio promedio de entrada no positivo — mantenerlo `> 0` no es una regla económica arbitraria sino la única lectura consistente con el dato ya filtrado.

**IMPORTANT-3 — Garantía conductual de ausencia de caché (`tests/test_execution_gateway_bybit_positions_reader.py`).** La auditoría reprodujo la mutación exacta (`self._cached`) que sobrevivía a la suite anterior: ningún test invocaba `query_positions()` dos veces sobre la **misma instancia** de `BybitPositionsReader`, por lo que un caché por instancia no se detectaba. **No había caché real en producción** — el hallazgo era de cobertura, no de comportamiento. Se agregó `TestNoCacheAcrossCalls` (7 tests) que invoca la misma instancia dos veces con respuestas distintas y confirma: dos llamadas reales a `BybitPrivateGetApi`, dos llamadas reales al interpreter, snapshots distintos por identidad, el segundo snapshot refleja genuinamente la segunda respuesta (verificado de punta a punta con el interpreter real, no un spy), y la instancia no expone ningún atributo `_cached`/`_cache`/`_last_result`/`_last_snapshot`. Reinyectando la mutación original de la auditoría, la nueva suite la detecta (5/7 tests fallan).

**IMPORTANT-4 — `PositionsSnapshot` es observacional, no operativo (documental, sin cambio de código).** La auditoría confirmó que `(symbol, side)` preserva correctamente ambas piernas de una posición hedged sin colapsarlas, y que la decisión original de omitir `positionIdx` es correcta — pero señaló que el snapshot resultante **no** contiene la identidad operativa completa que Bybit exige para *actuar* sobre una posición: cerrar o modificar una posición en hedge mode requiere `positionIdx` en el payload de la orden, y `PositionsSnapshot` no lo transporta. Se declara explícitamente: **`PositionsSnapshot` es un snapshot observacional del estado remoto, no una base suficiente para emitir órdenes de cierre/modificación en hedge mode.** La futura capa de actuación (fuera de alcance de este hito y de esta corrección) deberá incorporar el slot/leg remoto necesario antes de poder cerrar o modificar una posición — no debe asumirse que `(symbol, side)` contiene toda la identidad operativa de Bybit. No se agrega `positionIdx` ni ningún campo equivalente al contrato en esta corrección: no hay consumidor real todavía que lo justifique.

**Hallazgos MENORES — explícitamente no corregidos:** tamaño 0 con campos secundarios malformados sin validar, cierre de `Response` sin test dedicado, validación de timeout duplicada en 6 archivos. Ninguno bloquea que `PositionsReader` sirva de base observacional para reconciliación.

**Archivos modificados:** `positions_contracts.py`, `bybit_positions_response_interpreter.py`, `tests/test_execution_gateway_positions_contracts.py`, `tests/test_execution_gateway_bybit_positions_response_interpreter.py`, `tests/test_execution_gateway_bybit_positions_reader.py`, `docs/decisions.md`, `docs/progress.md`, `docs/handoff.md`.
**No modificado:** todo lo demás del stack GET (`http_get_transport.py`, `urllib_get_http_transport.py`, `http_get_request_executor.py`, `bybit_private_get_request_sender.py`, `bybit_private_get_api.py`), composition roots, `authenticator`, `parser`, loader, bootstrap, `railway.toml`, `phoenix_core`, todo el Port de escritura — la decisión de mantener la cadena GET paralela sin generalizar (ADR-002, Decisión 2) permanece vigente sin cambios; se reafirma explícitamente: si aparece un tercer verbo HTTP o una segunda necesidad fuerte de generalización, revisar el contrato HTTP existente antes de duplicar otra cadena.
**8/8 mutaciones de esta corrección verificadas y detectadas manualmente** (cursor ignorado, snapshot parcial con cursor, `leverage`/`unrealisedPnl` obligatorios de nuevo, accesorio malformado aceptado en silencio, caché por instancia reinyectada, regresión de colapso de hedge legs) — cada una restaurada y verificada byte-idéntica contra el original.
**Sin conexión real con Bybit en esta corrección; sin ninguna orden creada, cancelada o modificada.**

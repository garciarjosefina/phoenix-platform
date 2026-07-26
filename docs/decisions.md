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

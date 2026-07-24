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

## D-009 — `docs/` como fuente de verdad del proyecto

**Fecha:** 2026-07-23
**Decisión:** Los archivos `docs/progress.md`, `docs/decisions.md` y `docs/handoff.md` son la fuente de verdad. Se actualizan al finalizar cada hito.
**Razón:** El contexto del chat no persiste entre sesiones. La documentación garantiza continuidad.
**Regla:** Leer estos archivos antes de comenzar cualquier trabajo nuevo.

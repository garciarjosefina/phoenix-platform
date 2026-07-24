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

## Estado al 2026-07-23

- **Tag activo:** `v0.1.0`
- **Tests:** 142 passing, 0 failing
- **Python:** 3.14 en local (requisito mínimo: 3.12)
- **Railway:** proyecto creado, sin servicios desplegados
- **GitHub:** `garciarjosefina/phoenix-platform`, rama `main`
- **Fase activa:** Fase 3 — Execution Gateway (Hito 3.1 pendiente de implementación)

---

## Componente en curso: `execution_gateway` (Fase 3)

**Hito activo:** 3.1 — Inicializar el paquete `execution_gateway`

Crear `platform/execution_gateway/__init__.py` y `tests/test_execution_gateway_import.py`. Sin Bybit, sin HTTP, sin autenticación todavía.

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

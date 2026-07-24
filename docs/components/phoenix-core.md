# Cierre de Componente — Phoenix Core

## 1. Nombre y versión

**Componente:** `phoenix_core`
**Versión:** `0.1.0`
**Tag Git:** `v0.1.0`

---

## 2. Estado final

**Completado.**

---

## 3. Objetivo del componente

Definir los contratos de datos inmutables que todos los componentes de Phoenix utilizarán para comunicarse: identidad, configuración, eventos, señales, órdenes, operaciones y portfolios. Sin lógica de trading, sin dependencias externas, sin efectos secundarios.

---

## 4. Funcionalidades implementadas

- Generación y validación de IDs con prefijo semántico y UUID4 (`bot_`, `signal_`, `order_`, `trade_`, `event_`, `portfolio_`)
- Configuración central inmutable con valores por defecto (`Config`, `get_config()`)
- Contrato de eventos internos (`Event`) con timestamp UTC y serialización ISO 8601
- Contrato de señales de bot (`Signal`) con validación de `side` y `bot_id`
- Contrato de órdenes internas (`Order`) con reglas market/limit y validación de `price`
- Contrato de operaciones abiertas (`Trade`) con validación de precios y cantidades
- Contrato de portfolio (`Portfolio`) con `bot_ids` como tupla inmutable
- API pública unificada en `phoenix_core/__init__.py` con `__all__`

---

## 5. Interfaces públicas y contratos expuestos

Importables desde `from phoenix_core import ...`:

| Símbolo | Tipo | Descripción |
|---------|------|-------------|
| `__version__` | `str` | `"0.1.0"` |
| `Config` | `dataclass(frozen=True)` | `environment`, `debug`, `version` |
| `get_config()` | `() -> Config` | Devuelve configuración por defecto |
| `Event` | `dataclass(frozen=True)` | `event_id`, `event_type`, `source`, `timestamp`, `payload` |
| `Signal` | `dataclass(frozen=True)` | `signal_id`, `bot_id`, `symbol`, `side`, `timeframe`, `timestamp`, `metadata` |
| `Order` | `dataclass(frozen=True)` | `order_id`, `signal_id`, `bot_id`, `symbol`, `side`, `order_type`, `quantity`, `price`, `status`, `timestamp`, `metadata` |
| `Trade` | `dataclass(frozen=True)` | `trade_id`, `order_id`, `signal_id`, `bot_id`, `symbol`, `side`, `quantity`, `entry_price`, `opened_at`, `metadata` |
| `Portfolio` | `dataclass(frozen=True)` | `portfolio_id`, `name`, `created_at`, `bot_ids`, `metadata` |
| `bot_id()` | `() -> str` | Genera `bot_<uuid4>` |
| `signal_id()` | `() -> str` | Genera `signal_<uuid4>` |
| `order_id()` | `() -> str` | Genera `order_<uuid4>` |
| `trade_id()` | `() -> str` | Genera `trade_<uuid4>` |
| `event_id()` | `() -> str` | Genera `event_<uuid4>` |
| `portfolio_id()` | `() -> str` | Genera `portfolio_<uuid4>` |
| `is_valid(value, prefix)` | `(str, str) -> bool` | Valida formato `{prefix}_{uuid4}` |

Todos los contratos exponen `to_dict() -> dict` con timestamps en ISO 8601.

---

## 6. Archivos principales

```
platform/phoenix_core/__init__.py   — API pública y __all__        (35 líneas)
platform/phoenix_core/ids.py        — generación y validación IDs  (42 líneas)
platform/phoenix_core/config.py     — Config y get_config()        (14 líneas)
platform/phoenix_core/events.py     — clase Event                  (30 líneas)
platform/phoenix_core/signals.py    — clase Signal                 (40 líneas)
platform/phoenix_core/orders.py     — clase Order                  (61 líneas)
platform/phoenix_core/trades.py     — clase Trade                  (52 líneas)
platform/phoenix_core/portfolio.py  — clase Portfolio              (31 líneas)
pyproject.toml                      — build config + pytest config
```

---

## 7. Tests ejecutados y resultado

**Total: 142 passed, 0 failed**

| Archivo | Tests | Resultado |
|---------|-------|-----------|
| `tests/test_import.py` | 6 | ✅ |
| `tests/test_ids.py` | 40 | ✅ |
| `tests/test_config.py` | 5 | ✅ |
| `tests/test_events.py` | 14 | ✅ |
| `tests/test_signals.py` | 15 | ✅ |
| `tests/test_orders.py` | 26 | ✅ |
| `tests/test_trades.py` | 20 | ✅ |
| `tests/test_portfolio.py` | 16 | ✅ |

Ejecutar con: `python3 -m pytest tests/ -v`

---

## 8. Decisiones relevantes

Ver `docs/decisions.md` para el detalle completo. Las que afectan directamente a este componente:

- **D-002** — Paquete en `platform/`, no en la raíz
- **D-003** — `dataclasses(frozen=True)` para todos los contratos
- **D-004** — IDs con formato `{prefix}_{uuid4}`
- **D-005** — Sin dependencias externas en `phoenix_core`
- **D-006** — Timestamps siempre en UTC, serializados en ISO 8601

---

## 9. Limitaciones conocidas

- `payload`, `metadata` y otros dicts internos son mutables en contenido (solo el atributo es inmutable por `frozen=True`). Ver backlog para posible mitigación con `MappingProxyType`.
- `Config` no lee variables de entorno ni archivos externos. Deliberado en esta versión.
- `Order.status` solo acepta `"created"`. Los estados de ciclo de vida de la orden no están modelados.

---

## 10. Elementos enviados al backlog

Ver `docs/backlog.md`. Entradas relacionadas con este componente:

- Validadores por tipo de ID (`is_bot_id()`, `is_signal_id()`, etc.)
- `MappingProxyType` para inmutabilidad profunda de dicts
- Logging estructurado en `phoenix_core`

---

## 11. Commit final y tag

| Campo | Valor |
|-------|-------|
| Commit de cierre | `9f580e2` — `docs: freeze phoenix core v0.1.0` |
| Tag | `v0.1.0` |
| Rama | `main` |

---

## 12. Qué componente comienza después

**Fase 3 — por definir.**

Candidatos documentados en `docs/progress.md`:
- Execution Gateway (cliente Bybit)
- Bot SDK (lógica de bots)
- Primer despliegue en Railway

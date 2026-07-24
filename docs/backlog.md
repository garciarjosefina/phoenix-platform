# Phoenix Platform — Backlog

## Propósito

Registrar ideas, mejoras o funcionalidades que se decidió NO implementar en el hito actual. Este archivo es únicamente un registro para no perder ideas.

## Reglas

- Nunca implementar automáticamente una idea de este backlog.
- Nunca mover una idea al proyecto sin una decisión explícita.
- Mantener el backlog ordenado cronológicamente (más reciente al final).
- Estados válidos: `Pendiente` / `Descartado` / `Implementado`

---

## Entradas

| Fecha | Título | Descripción | Estado |
|-------|--------|-------------|--------|
| 2026-07-23 | Validadores por tipo de ID | Funciones específicas `is_bot_id()`, `is_signal_id()`, etc., además de la función genérica `is_valid()`. Se optó por mantener solo `is_valid(value, prefix)` para no duplicar lógica. | Pendiente |
| 2026-07-23 | `MappingProxyType` para payload/metadata | Convertir los dicts internos a `MappingProxyType` para inmutabilidad profunda. Se descartó en v0.1.0 por complejidad innecesaria en esta fase. | Pendiente |
| 2026-07-23 | Logging estructurado en `phoenix_core` | Agregar un módulo de logging con formato JSON al núcleo. Postergado: el núcleo debe permanecer sin dependencias y sin efectos secundarios. | Pendiente |

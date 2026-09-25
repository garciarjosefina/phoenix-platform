class EconomicComparisonPreconditionError(Exception):
    """Input estructuralmente imposible de comparar -- no una divergencia
    económica (Hito 3.91, ADR-014 D9/D11/D19).

    Se levanta EXCLUSIVAMENTE cuando `attempted.execution_order_id` y
    `observed.execution_order_id` no coinciden. ADR-014 congeló que una
    identidad cruzada es un defecto de programación (el caller comparó
    la intención de X contra la observación de Y), nunca un hecho sobre
    el mundo: "identidad cruzada Attempted(X) contra observación de Y ->
    no es MISMATCH, es error" (ADR-014 D19). Fundir este caso con
    `EconomicDivergence` obligaría a toda Projection/recovery futuro a
    distinguir una excepción a "toda divergencia es un hecho económico
    real", exactamente la ambigüedad que el modelo marcador-por-tipo de
    este proyecto existe para eliminar.

    Deliberadamente NO se reutiliza `ReconciliationPreconditionError`
    (reconciliation_precondition_error.py, Hito 3.77): esa excepción
    describe un input irreconciliable dentro de la pregunta de
    Reconciliation V1 (estado esperado de cuenta contra snapshot
    completo) -- una pregunta distinta de "¿esta observación es la
    intención que Phoenix registró para esta identidad?". Mismo
    principio ya aplicado por `CrossAccountReconciliationError`
    (account_scoped_reconciliation.py, Hito 3.81): una frontera de
    identidad equivocada es un error de enrutamiento del caller, no un
    dato del dominio -- pero es una frontera de identidad DISTINTA
    (cuenta vs. orden) y por tanto un tipo propio.

    Tampoco es `ExecutionInfrastructureError`: no hay I/O involucrado."""

    def __init__(self, *, message: str) -> None:
        if not isinstance(message, str):
            raise TypeError(f"message must be str, got: {type(message).__name__}")
        if not message or message.isspace():
            raise ValueError("message must not be empty or whitespace-only")
        super().__init__(message)
        self.message = message


__all__ = ["EconomicComparisonPreconditionError"]

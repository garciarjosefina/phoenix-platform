class CrossAccountReconciliationError(Exception):
    """Se intentó reconciliar el estado esperado de una cuenta contra el
    estado observado de OTRA cuenta.

    Deliberadamente NO se reutiliza `ReconciliationPreconditionError`: esa
    excepción describe un input estructuralmente irreconciliable *dentro
    de una misma cuenta* (una orden LIMIT esperada sin precio, una
    identidad observada duplicada) y la levanta el propio reconciler
    sobre los datos que se le entregan. Esto es una frontera distinta y
    anterior: un error de enrutamiento/cableado del caller, no un defecto
    de los datos. La remediación también es distinta -- ahí se re-lee el
    snapshot, aquí se corrige quién llama con qué. Un caller que capture
    una sola excepción para ambos casos no podría distinguirlos.

    Tampoco es `ExecutionInfrastructureError`: no hay I/O involucrado.
    """

    def __init__(self, *, message: str) -> None:
        if not isinstance(message, str):
            raise TypeError(f"message must be str, got: {type(message).__name__}")
        if not message or message.isspace():
            raise ValueError("message must not be empty or whitespace-only")
        super().__init__(message)
        self.message = message

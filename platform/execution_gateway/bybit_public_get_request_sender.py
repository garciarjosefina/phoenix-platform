from execution_gateway.http_get_request_executor import HttpGetRequestExecutor

# Sin autenticación deliberadamente: /v5/market/instruments-info (y los
# endpoints públicos de Bybit V5 en general) no requieren firma HMAC ni
# headers X-BAPI-*. A diferencia de BybitPrivateGetRequestSender, esta clase
# no depende de BybitAuthenticator ni de BybitHeaderBuilder -- construirla
# con credenciales Demo sólo para satisfacer un constructor habría acoplado
# en falso una lectura pública a secretos que nunca usa. Ver ADR-002,
# Decisión de arquitectura Public/Private GET (Hito 3.73).
_EMPTY_HEADERS: dict[str, str] = {}


class BybitPublicGetRequestSender:
    def __init__(self, request_executor: HttpGetRequestExecutor) -> None:
        if not isinstance(request_executor, HttpGetRequestExecutor):
            raise TypeError(
                f"request_executor must be HttpGetRequestExecutor, "
                f"got: {type(request_executor).__name__}"
            )
        self._request_executor = request_executor

    def send(self, *, url: str, query_string: str) -> str:
        if not isinstance(url, str):
            raise TypeError(f"url must be str, got: {type(url).__name__}")
        if not url or url.isspace():
            raise ValueError("url must not be empty or whitespace-only")
        if not isinstance(query_string, str):
            raise TypeError(f"query_string must be str, got: {type(query_string).__name__}")

        full_url = f"{url}?{query_string}" if query_string else url
        return self._request_executor.execute(url=full_url, headers=_EMPTY_HEADERS)

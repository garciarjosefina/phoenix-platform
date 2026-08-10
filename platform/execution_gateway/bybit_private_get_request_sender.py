from execution_gateway.bybit_authenticator import BybitAuthenticator
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.http_get_request_executor import HttpGetRequestExecutor


class BybitPrivateGetRequestSender:
    def __init__(
        self,
        authenticator: BybitAuthenticator,
        header_builder: BybitHeaderBuilder,
        request_executor: HttpGetRequestExecutor,
    ) -> None:
        if not isinstance(authenticator, BybitAuthenticator):
            raise TypeError(
                f"authenticator must be compatible with BybitAuthenticator, "
                f"got: {type(authenticator).__name__}"
            )
        if not isinstance(header_builder, BybitHeaderBuilder):
            raise TypeError(
                f"header_builder must be BybitHeaderBuilder, got: {type(header_builder).__name__}"
            )
        if not isinstance(request_executor, HttpGetRequestExecutor):
            raise TypeError(
                f"request_executor must be HttpGetRequestExecutor, "
                f"got: {type(request_executor).__name__}"
            )
        self._authenticator = authenticator
        self._header_builder = header_builder
        self._request_executor = request_executor

    def send(self, *, url: str, query_string: str) -> str:
        if not isinstance(url, str):
            raise TypeError(f"url must be str, got: {type(url).__name__}")
        if not url or url.isspace():
            raise ValueError("url must not be empty or whitespace-only")
        if not isinstance(query_string, str):
            raise TypeError(f"query_string must be str, got: {type(query_string).__name__}")

        # Firma de Bybit V5 para GET: timestamp + api_key + recv_window +
        # queryString (sin cuerpo). Reutiliza el mismo `authenticator` que el
        # camino POST -- `authenticate(body=...)` es genérico, acepta
        # cualquier string a firmar, no sólo un JSON body.
        authentication = self._authenticator.authenticate(body=query_string)
        headers = self._header_builder.build(authentication=authentication)
        full_url = f"{url}?{query_string}" if query_string else url
        return self._request_executor.execute(url=full_url, headers=headers)

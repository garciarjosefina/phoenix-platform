from execution_gateway.bybit_authenticator import BybitAuthentication


class BybitHeaderBuilder:
    def build(self, *, authentication: BybitAuthentication) -> dict[str, str]:
        if not isinstance(authentication, BybitAuthentication):
            raise TypeError(
                f"authentication must be BybitAuthentication, got: {type(authentication).__name__}"
            )
        return {
            "X-BAPI-API-KEY": authentication.api_key,
            "X-BAPI-TIMESTAMP": str(authentication.timestamp_ms),
            "X-BAPI-RECV-WINDOW": str(authentication.recv_window_ms),
            "X-BAPI-SIGN": authentication.signature,
            "Content-Type": "application/json",
        }

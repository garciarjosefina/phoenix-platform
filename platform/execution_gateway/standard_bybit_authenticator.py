from execution_gateway.bybit_authenticator import BybitAuthentication, BybitAuthenticator
from execution_gateway.credentials import BybitDemoCredentials
from execution_gateway.message_signer import MessageSigner
from execution_gateway.millisecond_clock import MillisecondClock


class StandardBybitAuthenticator:
    def __init__(
        self,
        credentials: BybitDemoCredentials,
        clock: MillisecondClock,
        signer: MessageSigner,
        recv_window_ms: int,
    ) -> None:
        if not isinstance(credentials, BybitDemoCredentials):
            raise TypeError(
                f"credentials must be BybitDemoCredentials, got: {type(credentials).__name__}"
            )
        if not isinstance(clock, MillisecondClock):
            raise TypeError(
                f"clock must be compatible with MillisecondClock, got: {type(clock).__name__}"
            )
        if not isinstance(signer, MessageSigner):
            raise TypeError(
                f"signer must be compatible with MessageSigner, got: {type(signer).__name__}"
            )
        if isinstance(recv_window_ms, bool) or not isinstance(recv_window_ms, int):
            raise TypeError(
                f"recv_window_ms must be int, got: {type(recv_window_ms).__name__}"
            )
        if recv_window_ms <= 0:
            raise ValueError(f"recv_window_ms must be > 0, got: {recv_window_ms}")

        self._credentials = credentials
        self._clock = clock
        self._signer = signer
        self._recv_window_ms = recv_window_ms

    def authenticate(self, *, body: str) -> BybitAuthentication:
        if not isinstance(body, str):
            raise TypeError(f"body must be str, got: {type(body).__name__}")

        timestamp_ms = self._clock.now_ms()
        message = (
            str(timestamp_ms)
            + self._credentials.api_key
            + str(self._recv_window_ms)
            + body
        )
        signature = self._signer.sign(
            secret=self._credentials.api_secret,
            message=message,
        )
        return BybitAuthentication(
            timestamp_ms=timestamp_ms,
            api_key=self._credentials.api_key,
            recv_window_ms=self._recv_window_ms,
            signature=signature,
        )

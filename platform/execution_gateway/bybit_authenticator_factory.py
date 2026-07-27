from execution_gateway.credentials import BybitDemoCredentials
from execution_gateway.message_signer import MessageSigner
from execution_gateway.millisecond_clock import MillisecondClock
from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator


def create_bybit_authenticator(
    *,
    credentials: BybitDemoCredentials,
    clock: MillisecondClock,
    signer: MessageSigner,
    recv_window_ms: int,
) -> StandardBybitAuthenticator:
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
    return StandardBybitAuthenticator(
        credentials=credentials,
        clock=clock,
        signer=signer,
        recv_window_ms=recv_window_ms,
    )

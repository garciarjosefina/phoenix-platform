def create_bybit_recv_window_ms(*, recv_window_ms: int) -> int:
    if isinstance(recv_window_ms, bool) or not isinstance(recv_window_ms, int):
        raise TypeError(
            f"recv_window_ms must be int, got: {type(recv_window_ms).__name__}"
        )
    if recv_window_ms <= 0:
        raise ValueError(f"recv_window_ms must be > 0, got: {recv_window_ms}")
    return recv_window_ms

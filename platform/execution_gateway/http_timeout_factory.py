def create_http_timeout_seconds(*, timeout_seconds: int | float) -> int | float:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise TypeError(
            f"timeout_seconds must be int or float, got: {type(timeout_seconds).__name__}"
        )
    if timeout_seconds <= 0:
        raise ValueError(f"timeout_seconds must be > 0, got: {timeout_seconds}")
    return timeout_seconds

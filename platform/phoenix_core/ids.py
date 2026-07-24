import uuid


def _make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4()}"


def bot_id() -> str:
    return _make_id("bot")


def signal_id() -> str:
    return _make_id("signal")


def order_id() -> str:
    return _make_id("order")


def trade_id() -> str:
    return _make_id("trade")


def event_id() -> str:
    return _make_id("event")


def is_valid(value: str, prefix: str) -> bool:
    if not isinstance(value, str):
        return False
    parts = value.split("_", 1)
    if len(parts) != 2 or parts[0] != prefix:
        return False
    try:
        parsed = uuid.UUID(parts[1])
        return parsed.version == 4
    except ValueError:
        return False

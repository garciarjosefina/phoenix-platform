from dataclasses import dataclass, field
from datetime import datetime, timezone

from phoenix_core.ids import order_id as _make_order_id, is_valid as _is_valid

_VALID_SIDES = {"buy", "sell"}
_VALID_ORDER_TYPES = {"market", "limit"}
_VALID_STATUSES = {"created"}


@dataclass(frozen=True)
class Order:
    signal_id: str
    bot_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float | None = None
    status: str = "created"
    metadata: dict = field(default_factory=dict)
    order_id: str = field(default_factory=_make_order_id)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not _is_valid(self.signal_id, "signal"):
            raise ValueError(f"signal_id must be a valid signal_ prefixed ID, got: {self.signal_id!r}")
        if not _is_valid(self.bot_id, "bot"):
            raise ValueError(f"bot_id must be a valid bot_ prefixed ID, got: {self.bot_id!r}")
        if not self.symbol:
            raise ValueError("symbol cannot be empty")
        if self.side not in _VALID_SIDES:
            raise ValueError(f"side must be 'buy' or 'sell', got: {self.side!r}")
        if self.order_type not in _VALID_ORDER_TYPES:
            raise ValueError(f"order_type must be 'market' or 'limit', got: {self.order_type!r}")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be > 0, got: {self.quantity}")
        if self.order_type == "limit":
            if self.price is None or self.price <= 0:
                raise ValueError("limit order requires price > 0")
        if self.order_type == "market" and self.price is not None:
            raise ValueError("market order must have price=None")
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"status must be 'created', got: {self.status!r}")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict")

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "signal_id": self.signal_id,
            "bot_id": self.bot_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

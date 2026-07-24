from dataclasses import dataclass, field
from datetime import datetime, timezone

from phoenix_core.ids import trade_id as _make_trade_id, is_valid as _is_valid

_VALID_SIDES = {"long", "short"}


@dataclass(frozen=True)
class Trade:
    order_id: str
    signal_id: str
    bot_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    metadata: dict = field(default_factory=dict)
    trade_id: str = field(default_factory=_make_trade_id)
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not _is_valid(self.order_id, "order"):
            raise ValueError(f"order_id must be a valid order_ prefixed ID, got: {self.order_id!r}")
        if not _is_valid(self.signal_id, "signal"):
            raise ValueError(f"signal_id must be a valid signal_ prefixed ID, got: {self.signal_id!r}")
        if not _is_valid(self.bot_id, "bot"):
            raise ValueError(f"bot_id must be a valid bot_ prefixed ID, got: {self.bot_id!r}")
        if not self.symbol:
            raise ValueError("symbol cannot be empty")
        if self.side not in _VALID_SIDES:
            raise ValueError(f"side must be 'long' or 'short', got: {self.side!r}")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be > 0, got: {self.quantity}")
        if self.entry_price <= 0:
            raise ValueError(f"entry_price must be > 0, got: {self.entry_price}")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict")

    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "signal_id": self.signal_id,
            "bot_id": self.bot_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "opened_at": self.opened_at.isoformat(),
            "metadata": self.metadata,
        }

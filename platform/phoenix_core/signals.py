from dataclasses import dataclass, field
from datetime import datetime, timezone

from phoenix_core.ids import signal_id as _make_signal_id, is_valid as _is_valid

_VALID_SIDES = {"long", "short"}


@dataclass(frozen=True)
class Signal:
    bot_id: str
    symbol: str
    side: str
    timeframe: str
    metadata: dict = field(default_factory=dict)
    signal_id: str = field(default_factory=_make_signal_id)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not _is_valid(self.bot_id, "bot"):
            raise ValueError(f"bot_id must be a valid bot_ prefixed ID, got: {self.bot_id!r}")
        if not self.symbol:
            raise ValueError("symbol cannot be empty")
        if self.side not in _VALID_SIDES:
            raise ValueError(f"side must be 'long' or 'short', got: {self.side!r}")
        if not self.timeframe:
            raise ValueError("timeframe cannot be empty")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict")

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "bot_id": self.bot_id,
            "symbol": self.symbol,
            "side": self.side,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

from dataclasses import dataclass, field
from datetime import datetime, timezone

from phoenix_core.ids import portfolio_id as _make_portfolio_id, is_valid as _is_valid


@dataclass(frozen=True)
class Portfolio:
    name: str
    bot_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict = field(default_factory=dict)
    portfolio_id: str = field(default_factory=_make_portfolio_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name cannot be empty")
        for bid in self.bot_ids:
            if not _is_valid(bid, "bot"):
                raise ValueError(f"bot_ids contains invalid bot ID: {bid!r}")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict")

    def to_dict(self) -> dict:
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "bot_ids": list(self.bot_ids),
            "metadata": self.metadata,
        }

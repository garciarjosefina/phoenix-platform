from dataclasses import dataclass, field
from datetime import datetime, timezone

from phoenix_core.ids import event_id as _make_event_id


@dataclass(frozen=True)
class Event:
    event_type: str
    source: str
    payload: dict = field(default_factory=dict)
    event_id: str = field(default_factory=_make_event_id)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ValueError("event_type cannot be empty")
        if not self.source:
            raise ValueError("source cannot be empty")
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict")

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
        }

from dataclasses import dataclass

_ORDER_LINK_ID_MAX_LEN = 36


@dataclass(frozen=True)
class BybitCreateOrderResult:
    order_id: str
    order_link_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.order_id, str):
            raise TypeError(f"order_id must be str, got: {type(self.order_id).__name__}")
        if not self.order_id or self.order_id.isspace():
            raise ValueError("order_id must not be empty or whitespace-only")

        if not isinstance(self.order_link_id, str):
            raise TypeError(f"order_link_id must be str, got: {type(self.order_link_id).__name__}")
        if not self.order_link_id or self.order_link_id.isspace():
            raise ValueError("order_link_id must not be empty or whitespace-only")
        if len(self.order_link_id) > _ORDER_LINK_ID_MAX_LEN:
            raise ValueError(
                f"order_link_id must be at most {_ORDER_LINK_ID_MAX_LEN} characters, "
                f"got: {len(self.order_link_id)}"
            )

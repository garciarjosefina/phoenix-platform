from dataclasses import dataclass
from decimal import Decimal

_ALLOWED_SIDES = frozenset({"Buy", "Sell"})
_ALLOWED_ORDER_TYPES = frozenset({"Market", "Limit"})
_ALLOWED_TIME_IN_FORCE = frozenset({"GTC", "IOC", "FOK", "PostOnly"})
_ORDER_LINK_ID_MAX_LEN = 36


@dataclass(frozen=True)
class BybitCreateOrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None
    time_in_force: str
    reduce_only: bool
    order_link_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str):
            raise TypeError(f"symbol must be str, got: {type(self.symbol).__name__}")
        if not self.symbol or self.symbol.isspace():
            raise ValueError("symbol must not be empty or whitespace-only")

        if not isinstance(self.side, str):
            raise TypeError(f"side must be str, got: {type(self.side).__name__}")
        if self.side not in _ALLOWED_SIDES:
            raise ValueError(f"side must be Buy or Sell, got: {self.side!r}")

        if not isinstance(self.order_type, str):
            raise TypeError(f"order_type must be str, got: {type(self.order_type).__name__}")
        if self.order_type not in _ALLOWED_ORDER_TYPES:
            raise ValueError(f"order_type must be Market or Limit, got: {self.order_type!r}")

        if not isinstance(self.quantity, Decimal):
            raise TypeError(f"quantity must be Decimal, got: {type(self.quantity).__name__}")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be > 0, got: {self.quantity}")

        if self.price is not None and not isinstance(self.price, Decimal):
            raise TypeError(f"price must be Decimal or None, got: {type(self.price).__name__}")
        if self.order_type == "Market" and self.price is not None:
            raise ValueError("price must be None for Market orders")
        if self.order_type == "Limit":
            if self.price is None:
                raise ValueError("price must be Decimal for Limit orders")
            if self.price <= 0:
                raise ValueError(f"price must be > 0, got: {self.price}")

        if not isinstance(self.time_in_force, str):
            raise TypeError(f"time_in_force must be str, got: {type(self.time_in_force).__name__}")
        if self.time_in_force not in _ALLOWED_TIME_IN_FORCE:
            raise ValueError(f"time_in_force must be GTC, IOC, FOK or PostOnly, got: {self.time_in_force!r}")

        if not isinstance(self.reduce_only, bool):
            raise TypeError(f"reduce_only must be bool, got: {type(self.reduce_only).__name__}")

        if not isinstance(self.order_link_id, str):
            raise TypeError(f"order_link_id must be str, got: {type(self.order_link_id).__name__}")
        if not self.order_link_id or self.order_link_id.isspace():
            raise ValueError("order_link_id must not be empty or whitespace-only")
        if len(self.order_link_id) > _ORDER_LINK_ID_MAX_LEN:
            raise ValueError(
                f"order_link_id must be at most {_ORDER_LINK_ID_MAX_LEN} characters, "
                f"got: {len(self.order_link_id)}"
            )

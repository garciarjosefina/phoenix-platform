from dataclasses import dataclass

_VALID_SIDES = {"buy", "sell"}
_VALID_ORDER_TYPES = {"market", "limit"}
_VALID_STATUSES = {"accepted", "rejected", "partially_filled", "filled", "cancelled"}


@dataclass(frozen=True)
class ExecutionRequest:
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float | None = None

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id cannot be empty")
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


@dataclass(frozen=True)
class ExecutionResult:
    order_id: str
    status: str
    exchange_order_id: str | None = None
    filled_quantity: float = 0.0
    average_price: float | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id cannot be empty")
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(_VALID_STATUSES)}, got: {self.status!r}")
        if self.filled_quantity < 0:
            raise ValueError(f"filled_quantity cannot be negative, got: {self.filled_quantity}")
        if self.average_price is not None and self.average_price <= 0:
            raise ValueError(f"average_price must be > 0, got: {self.average_price}")
        if self.status == "rejected":
            if not self.error_message:
                raise ValueError("error_message is required when status is 'rejected'")
        else:
            if self.error_message is not None:
                raise ValueError("error_message must be None when status is not 'rejected'")
        if self.status == "filled":
            if self.filled_quantity <= 0:
                raise ValueError("filled_quantity must be > 0 when status is 'filled'")
        if self.status in {"filled", "partially_filled"}:
            if self.average_price is None:
                raise ValueError(f"average_price is required when status is '{self.status}'")

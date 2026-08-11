from dataclasses import dataclass
from decimal import Decimal

_VALID_SIDES = {"buy", "sell"}


@dataclass(frozen=True)
class ExecutionPosition:
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    # leverage/unrealized_pnl son accesorios, no identidad de la posición
    # (auditoría Hito 3.70, IMPORTANT-2): Bybit puede devolverlos vacíos en
    # respuestas válidas (p.ej. cuentas Unified en portfolio margin) -- una
    # posición real sigue siendo observable sin ellos. None cuando el
    # exchange no los reporta; si vienen presentes, se siguen validando
    # igual que antes.
    leverage: Decimal | None = None
    unrealized_pnl: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str):
            raise TypeError(f"symbol must be str, got: {type(self.symbol).__name__}")
        if not self.symbol or self.symbol.isspace():
            raise ValueError("symbol must not be empty or whitespace-only")

        if not isinstance(self.side, str):
            raise TypeError(f"side must be str, got: {type(self.side).__name__}")
        if self.side not in _VALID_SIDES:
            raise ValueError(f"side must be 'buy' or 'sell', got: {self.side!r}")

        if not isinstance(self.quantity, Decimal):
            raise TypeError(f"quantity must be Decimal, got: {type(self.quantity).__name__}")
        if not self.quantity.is_finite():
            raise ValueError("quantity must be finite")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be > 0, got: {self.quantity}")

        # entry_price sigue siendo obligatorio y > 0: por construcción sólo
        # se evalúa para posiciones con quantity > 0 ya confirmada (el
        # interpreter descarta antes las filas de tamaño 0) -- Bybit no
        # documenta ningún caso en que una posición realmente abierta tenga
        # un precio promedio de entrada no positivo (evaluado explícitamente,
        # auditoría Hito 3.70, IMPORTANT-2).
        if not isinstance(self.entry_price, Decimal):
            raise TypeError(f"entry_price must be Decimal, got: {type(self.entry_price).__name__}")
        if not self.entry_price.is_finite():
            raise ValueError("entry_price must be finite")
        if self.entry_price <= 0:
            raise ValueError(f"entry_price must be > 0, got: {self.entry_price}")

        if self.leverage is not None:
            if not isinstance(self.leverage, Decimal):
                raise TypeError(f"leverage must be Decimal or None, got: {type(self.leverage).__name__}")
            if not self.leverage.is_finite():
                raise ValueError("leverage must be finite")
            if self.leverage <= 0:
                raise ValueError(f"leverage must be > 0, got: {self.leverage}")

        if self.unrealized_pnl is not None:
            if not isinstance(self.unrealized_pnl, Decimal):
                raise TypeError(
                    f"unrealized_pnl must be Decimal or None, got: {type(self.unrealized_pnl).__name__}"
                )
            if not self.unrealized_pnl.is_finite():
                raise ValueError("unrealized_pnl must be finite")


@dataclass(frozen=True)
class PositionsSnapshot:
    positions: tuple[ExecutionPosition, ...]
    server_time_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.positions, tuple):
            raise TypeError(f"positions must be tuple, got: {type(self.positions).__name__}")
        for position in self.positions:
            if not isinstance(position, ExecutionPosition):
                raise TypeError(
                    f"positions must contain only ExecutionPosition, got: {type(position).__name__}"
                )

        if isinstance(self.server_time_ms, bool) or not isinstance(self.server_time_ms, int):
            raise TypeError(
                f"server_time_ms must be int, got: {type(self.server_time_ms).__name__}"
            )
        if self.server_time_ms < 0:
            raise ValueError(f"server_time_ms must be >= 0, got: {self.server_time_ms}")

from dataclasses import dataclass
from decimal import Decimal

_VALID_SIDES = {"buy", "sell"}
_VALID_ORDER_TYPES = {"market", "limit"}

# /v5/order/realtime sólo devuelve órdenes no terminales (a diferencia de
# /v5/order/history, que no se usa en este hito). El universo posible de
# orderStatus para ese endpoint está acotado a estos cuatro -- cualquier otro
# valor sería inesperado para este scope de lectura y se rechaza en la
# interpretación en lugar de mapearse a un estado que perdería información.
# "triggered" se agregó tras la auditoría del Hito 3.71 (IMPORTANT-2):
# es el estado transitorio legítimo de una orden condicional en la
# transición Untriggered -> Triggered -> New, observable en una carrera de
# lectura real. No se agregan estados terminales (Filled/Cancelled/
# Rejected) -- esos siguen fuera del scope de este endpoint de lectura.
_VALID_STATUSES = {"new", "partially_filled", "untriggered", "triggered"}


@dataclass(frozen=True)
class ExecutionOpenOrder:
    exchange_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    filled_quantity: Decimal
    status: str
    reduce_only: bool
    # order_id (dominio) == orderLinkId de Bybit -- puede ser None: Bybit
    # permite crear órdenes sin orderLinkId (devuelve "" ), o la orden puede
    # ser enteramente ajena a Phoenix. No se inventa un id ni se oculta la
    # orden -- queda en el snapshot con identidad de dominio ausente, para
    # que un futuro reconciliador pueda detectarla como potencialmente
    # huérfana. exchange_order_id (orderId de Bybit) siempre está presente:
    # es el identificador que el propio exchange asigna a toda orden real.
    order_id: str | None = None
    # price ausente/vacío/cero es legítimo para market orders (Bybit no
    # siempre reporta un precio preestablecido; "0" confirmado como
    # respuesta legítima real, no sólo ""  -- IMPORTANT-1, auditoría del
    # Hito 3.71) -- ver bybit_open_orders_response_interpreter.py.
    price: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.exchange_order_id, str):
            raise TypeError(
                f"exchange_order_id must be str, got: {type(self.exchange_order_id).__name__}"
            )
        if not self.exchange_order_id or self.exchange_order_id.isspace():
            raise ValueError("exchange_order_id must not be empty or whitespace-only")

        if self.order_id is not None:
            if not isinstance(self.order_id, str):
                raise TypeError(f"order_id must be str or None, got: {type(self.order_id).__name__}")
            if not self.order_id or self.order_id.isspace():
                raise ValueError("order_id must not be empty or whitespace-only when present")

        if not isinstance(self.symbol, str):
            raise TypeError(f"symbol must be str, got: {type(self.symbol).__name__}")
        if not self.symbol or self.symbol.isspace():
            raise ValueError("symbol must not be empty or whitespace-only")

        if not isinstance(self.side, str):
            raise TypeError(f"side must be str, got: {type(self.side).__name__}")
        if self.side not in _VALID_SIDES:
            raise ValueError(f"side must be 'buy' or 'sell', got: {self.side!r}")

        if not isinstance(self.order_type, str):
            raise TypeError(f"order_type must be str, got: {type(self.order_type).__name__}")
        if self.order_type not in _VALID_ORDER_TYPES:
            raise ValueError(f"order_type must be 'market' or 'limit', got: {self.order_type!r}")

        if not isinstance(self.quantity, Decimal):
            raise TypeError(f"quantity must be Decimal, got: {type(self.quantity).__name__}")
        if not self.quantity.is_finite():
            raise ValueError("quantity must be finite")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be > 0, got: {self.quantity}")

        if self.price is not None:
            if not isinstance(self.price, Decimal):
                raise TypeError(f"price must be Decimal or None, got: {type(self.price).__name__}")
            if not self.price.is_finite():
                raise ValueError("price must be finite")
            if self.price <= 0:
                raise ValueError(f"price must be > 0, got: {self.price}")

        # filled_quantity >= 0 es la única invariante exigida. 0 es el
        # estado normal de una orden recién creada sin fills. No se exige
        # filled_quantity <= quantity: no está confirmado que Bybit
        # garantice esa relación en todo momento para este endpoint, y no
        # corresponde imponer una regla de negocio no verificada (lección
        # de la auditoría del Hito 3.70 sobre avgPrice).
        if not isinstance(self.filled_quantity, Decimal):
            raise TypeError(
                f"filled_quantity must be Decimal, got: {type(self.filled_quantity).__name__}"
            )
        if not self.filled_quantity.is_finite():
            raise ValueError("filled_quantity must be finite")
        if self.filled_quantity < 0:
            raise ValueError(f"filled_quantity must be >= 0, got: {self.filled_quantity}")

        if not isinstance(self.status, str):
            raise TypeError(f"status must be str, got: {type(self.status).__name__}")
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(_VALID_STATUSES)}, got: {self.status!r}")

        if not isinstance(self.reduce_only, bool):
            raise TypeError(f"reduce_only must be bool, got: {type(self.reduce_only).__name__}")


@dataclass(frozen=True)
class OpenOrdersSnapshot:
    orders: tuple[ExecutionOpenOrder, ...]
    server_time_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.orders, tuple):
            raise TypeError(f"orders must be tuple, got: {type(self.orders).__name__}")
        for order in self.orders:
            if not isinstance(order, ExecutionOpenOrder):
                raise TypeError(
                    f"orders must contain only ExecutionOpenOrder, got: {type(order).__name__}"
                )

        if isinstance(self.server_time_ms, bool) or not isinstance(self.server_time_ms, int):
            raise TypeError(
                f"server_time_ms must be int, got: {type(self.server_time_ms).__name__}"
            )
        if self.server_time_ms < 0:
            raise ValueError(f"server_time_ms must be >= 0, got: {self.server_time_ms}")

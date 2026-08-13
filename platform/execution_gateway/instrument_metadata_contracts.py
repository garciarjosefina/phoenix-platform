from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ExecutionInstrumentMetadata:
    # Identidad y clasificación del instrumento. Los seis primeros campos
    # (symbol/base_asset/quote_asset/settlement_asset/instrument_status/
    # contract_type) son esenciales: sin ellos no hay forma de identificar
    # ni clasificar el instrumento devuelto. `settlement_asset` (settleCoin)
    # es distinto de `quote_asset` (quoteCoin) -- para un instrumento linear
    # coin-margined ambos difieren; Phoenix opera exclusivamente linear
    # USDT-margined, así que `settlement_asset` es la confirmación explícita
    # de que el instrumento realmente liquida en USDT, no una redundancia.
    symbol: str
    base_asset: str
    quote_asset: str
    settlement_asset: str
    # instrument_status/contract_type se preservan EXACTAMENTE como Bybit
    # los devuelve (sin traducir a minúsculas ni a un enum cerrado), a
    # diferencia de side/order_type/status en Positions/Open Orders Read.
    # Divergencia deliberada: aquí el universo de valores NO está
    # documentado de forma completa por Bybit (a diferencia de
    # /v5/order/realtime, que documenta explícitamente su universo acotado
    # de estados no-terminales) -- instruments-info expone el ciclo de vida
    # completo de cualquier instrumento (Trading/PreLaunch/Delivering y
    # potencialmente otros no confirmados). Tratar esto como un enum cerrado
    # sería inventar una restricción no respaldada por la documentación, y
    # bloquearía la observación de instrumentos en estados legítimos no
    # anticipados. Se conserva la información en vez de esconderla o de
    # rechazar instrumentos no operables -- este hito es observacional, no
    # un filtro de operabilidad.
    instrument_status: str
    contract_type: str
    # Price filter -- granularidad y límites de precio. tick_size > 0 es una
    # necesidad estructural del concepto "incremento de precio" (un step de
    # 0 no es un incremento), no una garantía asumida de Bybit. min_price/
    # max_price se validan sólo como Decimal finito >= 0, sin relación
    # cruzada entre sí ni con tick_size -- Bybit no documenta que
    # max_price > min_price sea una invariante garantizada, y no se inventa.
    tick_size: Decimal
    min_price: Decimal
    max_price: Decimal
    # Lot size filter -- granularidad y límites de cantidad. qty_step > 0 y
    # min_order_qty > 0 por la misma razón estructural que tick_size (un
    # step o un mínimo de cantidad igual a 0 no es un concepto coherente).
    # max_order_qty se valida sólo >= 0 (un máximo de 0 podría representar
    # legítimamente un instrumento con trading de límite suspendido, sin
    # evidencia de que eso nunca ocurra).
    qty_step: Decimal
    min_order_qty: Decimal
    max_order_qty: Decimal
    # server_time_ms: mismo patrón que PositionsSnapshot/OpenOrdersSnapshot/
    # WalletBalanceSnapshot -- proviene del envelope `time` de la respuesta
    # remota, nunca de un reloj local. Útil para detectar metadata obsoleta
    # en una futura capa de validación (esta metadata NO se cachea, pero un
    # consumidor que sí decida cachearla localmente podría usar este campo
    # para decidir cuándo refrescar).
    server_time_ms: int
    # max_market_order_qty (maxMktOrderQty) es DISTINTO de max_order_qty
    # (maxOrderQty, límite de órdenes limit) -- confirmado por el ejemplo
    # oficial de Bybit, donde ambos valores difieren para el mismo
    # instrumento. Confundirlos permitiría que una futura validación de
    # market order aceptara una cantidad que sólo es válida para limit.
    # Accesorio (Decimal | None): no hay confirmación de que este campo
    # esté siempre presente/no-vacío para todo instrumento linear (a
    # diferencia de qtyStep/minOrderQty/maxOrderQty, presentes en el
    # ejemplo base sin condición documentada).
    max_market_order_qty: Decimal | None = None
    # minNotionalValue: DISTINTO de min_order_qty -- notional es
    # price × quantity, no una cantidad de contratos. Esencial para una
    # futura validación de "orden mínima viable" que min_order_qty por sí
    # solo no puede expresar (una orden puede cumplir min_order_qty y aun
    # así no alcanzar el valor nocional mínimo si el precio es bajo). Este
    # hito NO implementa esa validación (price × qty >= min_notional_value)
    # -- sólo representa el dato. Accesorio: no confirmado que esté
    # garantizado presente para todo instrumento linear.
    min_notional_value: Decimal | None = None
    # Leverage filter -- METADATA REMOTA únicamente, nunca una recomendación
    # operativa. min_leverage/max_leverage/leverage_step describen lo que
    # Bybit permite técnicamente para este instrumento -- NO lo que Phoenix
    # debería usar. Un futuro Risk Engine NO debe interpretar max_leverage
    # como "leverage seguro" ni calcular/configurar leverage a partir de
    # estos valores en este hito ni implícitamente en el futuro sin una
    # decisión de riesgo explícita y separada. Accesorios: Bybit documenta
    # leverageFilter como ausente para category=spot: aunque Phoenix sólo
    # consulta linear, no hay confirmación de que el bloque esté siempre
    # presente y completo para todo instrumento linear (p.ej. instrumentos
    # en pre-listing con filtros aún no calibrados).
    min_leverage: Decimal | None = None
    max_leverage: Decimal | None = None
    leverage_step: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str):
            raise TypeError(f"symbol must be str, got: {type(self.symbol).__name__}")
        if not self.symbol or self.symbol.isspace():
            raise ValueError("symbol must not be empty or whitespace-only")

        if not isinstance(self.base_asset, str):
            raise TypeError(f"base_asset must be str, got: {type(self.base_asset).__name__}")
        if not self.base_asset or self.base_asset.isspace():
            raise ValueError("base_asset must not be empty or whitespace-only")

        if not isinstance(self.quote_asset, str):
            raise TypeError(f"quote_asset must be str, got: {type(self.quote_asset).__name__}")
        if not self.quote_asset or self.quote_asset.isspace():
            raise ValueError("quote_asset must not be empty or whitespace-only")

        if not isinstance(self.settlement_asset, str):
            raise TypeError(f"settlement_asset must be str, got: {type(self.settlement_asset).__name__}")
        if not self.settlement_asset or self.settlement_asset.isspace():
            raise ValueError("settlement_asset must not be empty or whitespace-only")

        if not isinstance(self.instrument_status, str):
            raise TypeError(f"instrument_status must be str, got: {type(self.instrument_status).__name__}")
        if not self.instrument_status or self.instrument_status.isspace():
            raise ValueError("instrument_status must not be empty or whitespace-only")

        if not isinstance(self.contract_type, str):
            raise TypeError(f"contract_type must be str, got: {type(self.contract_type).__name__}")
        if not self.contract_type or self.contract_type.isspace():
            raise ValueError("contract_type must not be empty or whitespace-only")

        if not isinstance(self.tick_size, Decimal):
            raise TypeError(f"tick_size must be Decimal, got: {type(self.tick_size).__name__}")
        if not self.tick_size.is_finite():
            raise ValueError("tick_size must be finite")
        if self.tick_size <= 0:
            raise ValueError(f"tick_size must be > 0, got: {self.tick_size}")

        if not isinstance(self.min_price, Decimal):
            raise TypeError(f"min_price must be Decimal, got: {type(self.min_price).__name__}")
        if not self.min_price.is_finite():
            raise ValueError("min_price must be finite")
        if self.min_price < 0:
            raise ValueError(f"min_price must be >= 0, got: {self.min_price}")

        if not isinstance(self.max_price, Decimal):
            raise TypeError(f"max_price must be Decimal, got: {type(self.max_price).__name__}")
        if not self.max_price.is_finite():
            raise ValueError("max_price must be finite")
        if self.max_price < 0:
            raise ValueError(f"max_price must be >= 0, got: {self.max_price}")

        if not isinstance(self.qty_step, Decimal):
            raise TypeError(f"qty_step must be Decimal, got: {type(self.qty_step).__name__}")
        if not self.qty_step.is_finite():
            raise ValueError("qty_step must be finite")
        if self.qty_step <= 0:
            raise ValueError(f"qty_step must be > 0, got: {self.qty_step}")

        if not isinstance(self.min_order_qty, Decimal):
            raise TypeError(f"min_order_qty must be Decimal, got: {type(self.min_order_qty).__name__}")
        if not self.min_order_qty.is_finite():
            raise ValueError("min_order_qty must be finite")
        if self.min_order_qty <= 0:
            raise ValueError(f"min_order_qty must be > 0, got: {self.min_order_qty}")

        if not isinstance(self.max_order_qty, Decimal):
            raise TypeError(f"max_order_qty must be Decimal, got: {type(self.max_order_qty).__name__}")
        if not self.max_order_qty.is_finite():
            raise ValueError("max_order_qty must be finite")
        if self.max_order_qty < 0:
            raise ValueError(f"max_order_qty must be >= 0, got: {self.max_order_qty}")

        if self.max_market_order_qty is not None:
            if not isinstance(self.max_market_order_qty, Decimal):
                raise TypeError(
                    f"max_market_order_qty must be Decimal or None, "
                    f"got: {type(self.max_market_order_qty).__name__}"
                )
            if not self.max_market_order_qty.is_finite():
                raise ValueError("max_market_order_qty must be finite")
            if self.max_market_order_qty < 0:
                raise ValueError(
                    f"max_market_order_qty must be >= 0, got: {self.max_market_order_qty}"
                )

        if self.min_notional_value is not None:
            if not isinstance(self.min_notional_value, Decimal):
                raise TypeError(
                    f"min_notional_value must be Decimal or None, "
                    f"got: {type(self.min_notional_value).__name__}"
                )
            if not self.min_notional_value.is_finite():
                raise ValueError("min_notional_value must be finite")
            if self.min_notional_value < 0:
                raise ValueError(
                    f"min_notional_value must be >= 0, got: {self.min_notional_value}"
                )

        if self.min_leverage is not None:
            if not isinstance(self.min_leverage, Decimal):
                raise TypeError(
                    f"min_leverage must be Decimal or None, got: {type(self.min_leverage).__name__}"
                )
            if not self.min_leverage.is_finite():
                raise ValueError("min_leverage must be finite")
            if self.min_leverage <= 0:
                raise ValueError(f"min_leverage must be > 0, got: {self.min_leverage}")

        if self.max_leverage is not None:
            if not isinstance(self.max_leverage, Decimal):
                raise TypeError(
                    f"max_leverage must be Decimal or None, got: {type(self.max_leverage).__name__}"
                )
            if not self.max_leverage.is_finite():
                raise ValueError("max_leverage must be finite")
            if self.max_leverage <= 0:
                raise ValueError(f"max_leverage must be > 0, got: {self.max_leverage}")

        if self.leverage_step is not None:
            if not isinstance(self.leverage_step, Decimal):
                raise TypeError(
                    f"leverage_step must be Decimal or None, got: {type(self.leverage_step).__name__}"
                )
            if not self.leverage_step.is_finite():
                raise ValueError("leverage_step must be finite")
            if self.leverage_step <= 0:
                raise ValueError(f"leverage_step must be > 0, got: {self.leverage_step}")

        if isinstance(self.server_time_ms, bool) or not isinstance(self.server_time_ms, int):
            raise TypeError(
                f"server_time_ms must be int, got: {type(self.server_time_ms).__name__}"
            )
        if self.server_time_ms < 0:
            raise ValueError(f"server_time_ms must be >= 0, got: {self.server_time_ms}")

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ExecutionCurrencyBalance:
    coin: str
    wallet_balance: Decimal
    equity: Decimal
    # unrealized_pnl/usd_value son accesorios, no identidad del balance (mismo
    # principio que leverage/unrealized_pnl en positions_contracts.py, Hito
    # 3.70): Bybit documenta que ciertos campos del objeto `coin` pueden venir
    # vacíos según el modo de margen de la cuenta. None cuando el exchange no
    # los reporta; "0" es un valor real (P&L nulo / valor USD nulo), nunca se
    # colapsa a None.
    unrealized_pnl: Decimal | None = None
    usd_value: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.coin, str):
            raise TypeError(f"coin must be str, got: {type(self.coin).__name__}")
        if not self.coin or self.coin.isspace():
            raise ValueError("coin must not be empty or whitespace-only")

        # wallet_balance/equity: sin restricción de signo. Bybit no garantiza
        # que sean siempre >= 0 -- una cuenta con pérdidas no liquidadas
        # todavía reflejadas contablemente podría, en teoría, reportar equity
        # negativo; no se asume una regla de negocio no confirmada.
        if not isinstance(self.wallet_balance, Decimal):
            raise TypeError(f"wallet_balance must be Decimal, got: {type(self.wallet_balance).__name__}")
        if not self.wallet_balance.is_finite():
            raise ValueError("wallet_balance must be finite")

        if not isinstance(self.equity, Decimal):
            raise TypeError(f"equity must be Decimal, got: {type(self.equity).__name__}")
        if not self.equity.is_finite():
            raise ValueError("equity must be finite")

        if self.unrealized_pnl is not None:
            if not isinstance(self.unrealized_pnl, Decimal):
                raise TypeError(
                    f"unrealized_pnl must be Decimal or None, got: {type(self.unrealized_pnl).__name__}"
                )
            if not self.unrealized_pnl.is_finite():
                raise ValueError("unrealized_pnl must be finite")

        if self.usd_value is not None:
            if not isinstance(self.usd_value, Decimal):
                raise TypeError(f"usd_value must be Decimal or None, got: {type(self.usd_value).__name__}")
            if not self.usd_value.is_finite():
                raise ValueError("usd_value must be finite")


@dataclass(frozen=True)
class WalletBalanceSnapshot:
    # Totales de cuenta (USD-denominados, según /v5/account/wallet-balance):
    # los cinco campos mínimos necesarios para distinguir "lo que la cuenta
    # posee" (wallet_balance) de "lo que la cuenta vale ahora mismo incluyendo
    # PnL no realizado" (equity) de total_available_balance -- ver más abajo,
    # NO es simplemente "capital disponible para operar" -- más los dos
    # agregados de margen ya comprometido/en riesgo de liquidación
    # (initial_margin/maintenance_margin), esenciales para un futuro Risk
    # Engine. Deliberadamente no se incluyen totalMarginBalance,
    # totalPerpUPL, accountIMRate/accountMMRate (ver ADR correspondiente):
    # son derivables o redundantes con los cinco campos ya presentes para el
    # alcance actual de Phoenix (linear USDT), y agregarlos "por si acaso"
    # violaría el principio de no exponer superficie no justificada.
    #
    # total_available_balance -- semántica exacta, corrección post-3.72
    # (IMPORTANTE-2): NO representa "buying power en USDT" ni "lo que
    # puede usarse directamente para abrir una posición nueva" -- esa
    # lectura fue la de la versión original de este comentario y era
    # engañosa. Según la documentación oficial de Bybit V5:
    #   - es una magnitud a nivel de CUENTA (no por moneda);
    #   - está expresada en equivalente USD, no en USDT;
    #   - agrega TODOS los activos de colateral de la cuenta, no sólo USDT;
    #   - depende del margin mode (fórmula distinta en Cross Margin:
    #     totalMarginBalance - Haircut - totalInitialMargin, vs. Portfolio
    #     Margin: totalEquity - Haircut - totalInitialMargin);
    #   - incorpora un "Haircut" que Bybit no define en esta página.
    # NO debe usarse aislado como buying power para dimensionar una orden
    # linear USDT: un Risk Engine que lo haga podría sobredimensionar
    # posiciones contra colateral no-USDT sujeto a haircut y a variación de
    # precio. El futuro Risk Engine deberá interpretar este campo en
    # conjunto con currency_balances, la moneda de settlement del
    # instrumento, el colateral relevante y el margin mode -- ninguna de
    # esas reglas se construye en este hito (ver ADR-002).
    total_equity: Decimal
    total_wallet_balance: Decimal
    total_available_balance: Decimal
    total_initial_margin: Decimal
    total_maintenance_margin: Decimal
    currency_balances: tuple[ExecutionCurrencyBalance, ...]
    server_time_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.total_equity, Decimal):
            raise TypeError(f"total_equity must be Decimal, got: {type(self.total_equity).__name__}")
        if not self.total_equity.is_finite():
            raise ValueError("total_equity must be finite")

        if not isinstance(self.total_wallet_balance, Decimal):
            raise TypeError(
                f"total_wallet_balance must be Decimal, got: {type(self.total_wallet_balance).__name__}"
            )
        if not self.total_wallet_balance.is_finite():
            raise ValueError("total_wallet_balance must be finite")

        if not isinstance(self.total_available_balance, Decimal):
            raise TypeError(
                f"total_available_balance must be Decimal, got: {type(self.total_available_balance).__name__}"
            )
        if not self.total_available_balance.is_finite():
            raise ValueError("total_available_balance must be finite")

        # initial_margin/maintenance_margin: magnitudes de margen -- a
        # diferencia de equity/available_balance, estructuralmente no pueden
        # ser negativas (no existe "margen negativo" en la semántica de
        # Bybit); "0" es el valor legítimo cuando no hay posiciones/órdenes
        # abiertas.
        if not isinstance(self.total_initial_margin, Decimal):
            raise TypeError(
                f"total_initial_margin must be Decimal, got: {type(self.total_initial_margin).__name__}"
            )
        if not self.total_initial_margin.is_finite():
            raise ValueError("total_initial_margin must be finite")
        if self.total_initial_margin < 0:
            raise ValueError(f"total_initial_margin must be >= 0, got: {self.total_initial_margin}")

        if not isinstance(self.total_maintenance_margin, Decimal):
            raise TypeError(
                f"total_maintenance_margin must be Decimal, got: {type(self.total_maintenance_margin).__name__}"
            )
        if not self.total_maintenance_margin.is_finite():
            raise ValueError("total_maintenance_margin must be finite")
        if self.total_maintenance_margin < 0:
            raise ValueError(f"total_maintenance_margin must be >= 0, got: {self.total_maintenance_margin}")

        if not isinstance(self.currency_balances, tuple):
            raise TypeError(
                f"currency_balances must be tuple, got: {type(self.currency_balances).__name__}"
            )
        for balance in self.currency_balances:
            if not isinstance(balance, ExecutionCurrencyBalance):
                raise TypeError(
                    f"currency_balances must contain only ExecutionCurrencyBalance, "
                    f"got: {type(balance).__name__}"
                )

        if isinstance(self.server_time_ms, bool) or not isinstance(self.server_time_ms, int):
            raise TypeError(
                f"server_time_ms must be int, got: {type(self.server_time_ms).__name__}"
            )
        if self.server_time_ms < 0:
            raise ValueError(f"server_time_ms must be >= 0, got: {self.server_time_ms}")

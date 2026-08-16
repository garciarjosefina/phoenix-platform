from dataclasses import dataclass

from execution_gateway.open_orders_contracts import OpenOrdersSnapshot
from execution_gateway.positions_contracts import PositionsSnapshot
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot


@dataclass(frozen=True)
class ObservationWindow:
    # Mide, no decide. earliest/latest son los extremos de los server_time_ms
    # remotos de las tres lecturas que componen la ronda -- NUNCA un reloj
    # local (`time.time()`), y nunca sustituidos si un valor remoto falta.
    # remote_time_span_ms se almacena explícitamente (no como propiedad
    # calculada) para mantener el mismo estilo de dataclass puro y
    # verificable en tests que el resto de los contratos del read-side, y
    # se valida por consistencia contra earliest/latest en __post_init__.
    #
    # Deliberadamente NO existe ningún campo ni validación de "ventana
    # máxima aceptable" -- eso es política, no medición (Hito 3.74, sección
    # 7): este objeto expone el drift observado, un futuro consumidor
    # decide qué tolerancia aplicar. Ver ADR-002.
    earliest_remote_time_ms: int
    latest_remote_time_ms: int
    remote_time_span_ms: int

    def __post_init__(self) -> None:
        if isinstance(self.earliest_remote_time_ms, bool) or not isinstance(
            self.earliest_remote_time_ms, int
        ):
            raise TypeError(
                f"earliest_remote_time_ms must be int, "
                f"got: {type(self.earliest_remote_time_ms).__name__}"
            )
        if self.earliest_remote_time_ms < 0:
            raise ValueError(
                f"earliest_remote_time_ms must be >= 0, got: {self.earliest_remote_time_ms}"
            )

        if isinstance(self.latest_remote_time_ms, bool) or not isinstance(
            self.latest_remote_time_ms, int
        ):
            raise TypeError(
                f"latest_remote_time_ms must be int, "
                f"got: {type(self.latest_remote_time_ms).__name__}"
            )
        if self.latest_remote_time_ms < 0:
            raise ValueError(
                f"latest_remote_time_ms must be >= 0, got: {self.latest_remote_time_ms}"
            )

        # Necesidad estructural, no una política de negocio: "el máximo" no
        # puede ser menor que "el mínimo" del mismo conjunto de valores.
        if self.latest_remote_time_ms < self.earliest_remote_time_ms:
            raise ValueError(
                "latest_remote_time_ms must be >= earliest_remote_time_ms, "
                f"got: latest={self.latest_remote_time_ms}, earliest={self.earliest_remote_time_ms}"
            )

        if isinstance(self.remote_time_span_ms, bool) or not isinstance(
            self.remote_time_span_ms, int
        ):
            raise TypeError(
                f"remote_time_span_ms must be int, got: {type(self.remote_time_span_ms).__name__}"
            )
        if self.remote_time_span_ms < 0:
            raise ValueError(
                f"remote_time_span_ms must be >= 0, got: {self.remote_time_span_ms}"
            )
        expected_span = self.latest_remote_time_ms - self.earliest_remote_time_ms
        if self.remote_time_span_ms != expected_span:
            raise ValueError(
                f"remote_time_span_ms must equal latest_remote_time_ms - earliest_remote_time_ms "
                f"({expected_span}), got: {self.remote_time_span_ms}"
            )


@dataclass(frozen=True)
class ExchangeStateSnapshot:
    # Agrega EXACTAMENTE las tres primitives account-wide ya aceptadas
    # (Positions/Open Orders/Wallet Balance Read, Hitos 3.70-3.72).
    # Deliberadamente NO incluye Instrument Metadata (Hito 3.73): esa
    # primitive es por-símbolo (exige `symbol` en su Port), mientras que
    # las otras tres son account-wide sin parámetros -- forzar una
    # selección de símbolos aquí habría inventado una política de
    # selección no justificada por ningún consumidor real todavía. Ver
    # ADR-002, extensión de Hito 3.74, para el razonamiento completo y las
    # alternativas descartadas.
    #
    # Este objeto es observacional y NO es una fotografía atómica: cada
    # sub-snapshot proviene de un request HTTP independiente. Nunca debe
    # tratarse como "el estado de la cuenta en un instante". Ver
    # `observation_window` para la única garantía temporal real: los
    # extremos remotos observados durante esta ronda, nunca inventados.
    positions: PositionsSnapshot
    open_orders: OpenOrdersSnapshot
    wallet_balance: WalletBalanceSnapshot
    observation_window: ObservationWindow

    def __post_init__(self) -> None:
        if not isinstance(self.positions, PositionsSnapshot):
            raise TypeError(
                f"positions must be PositionsSnapshot, got: {type(self.positions).__name__}"
            )
        if not isinstance(self.open_orders, OpenOrdersSnapshot):
            raise TypeError(
                f"open_orders must be OpenOrdersSnapshot, got: {type(self.open_orders).__name__}"
            )
        if not isinstance(self.wallet_balance, WalletBalanceSnapshot):
            raise TypeError(
                f"wallet_balance must be WalletBalanceSnapshot, "
                f"got: {type(self.wallet_balance).__name__}"
            )
        if not isinstance(self.observation_window, ObservationWindow):
            raise TypeError(
                f"observation_window must be ObservationWindow, "
                f"got: {type(self.observation_window).__name__}"
            )

        # Consistencia cruzada, defensa en profundidad (mismo principio ya
        # aplicado en el read-side: no confiar únicamente en la lógica del
        # agregador -- el propio contrato rechaza una ObservationWindow que
        # no corresponda realmente a los tres server_time_ms presentes,
        # incluso si alguien construyera este objeto a mano en el futuro).
        remote_times = (
            self.positions.server_time_ms,
            self.open_orders.server_time_ms,
            self.wallet_balance.server_time_ms,
        )
        expected_earliest = min(remote_times)
        expected_latest = max(remote_times)
        if self.observation_window.earliest_remote_time_ms != expected_earliest:
            raise ValueError(
                "observation_window.earliest_remote_time_ms does not match the earliest "
                f"server_time_ms among positions/open_orders/wallet_balance "
                f"(expected {expected_earliest}, got {self.observation_window.earliest_remote_time_ms})"
            )
        if self.observation_window.latest_remote_time_ms != expected_latest:
            raise ValueError(
                "observation_window.latest_remote_time_ms does not match the latest "
                f"server_time_ms among positions/open_orders/wallet_balance "
                f"(expected {expected_latest}, got {self.observation_window.latest_remote_time_ms})"
            )

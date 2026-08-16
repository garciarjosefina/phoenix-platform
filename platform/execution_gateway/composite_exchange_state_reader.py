from execution_gateway.exchange_state_contracts import ExchangeStateSnapshot, ObservationWindow
from execution_gateway.open_orders_reader import OpenOrdersReader
from execution_gateway.positions_reader import PositionsReader
from execution_gateway.wallet_balance_reader import WalletBalanceReader


class CompositeExchangeStateReader:
    # Deliberadamente exchange-agnostic: depende únicamente de los tres
    # Ports de lectura ya aceptados (Protocols), nunca de un tipo Bybit
    # concreto. Funcionaría igual con cualquier implementación de esos
    # tres Ports -- la composición con Bybit Demo vive exclusivamente en
    # las factories de composición (bybit_demo_exchange_state_*), no acá.
    def __init__(
        self,
        positions_reader: PositionsReader,
        open_orders_reader: OpenOrdersReader,
        wallet_balance_reader: WalletBalanceReader,
    ) -> None:
        if not isinstance(positions_reader, PositionsReader):
            raise TypeError(
                f"positions_reader must be compatible with PositionsReader, "
                f"got: {type(positions_reader).__name__}"
            )
        if not isinstance(open_orders_reader, OpenOrdersReader):
            raise TypeError(
                f"open_orders_reader must be compatible with OpenOrdersReader, "
                f"got: {type(open_orders_reader).__name__}"
            )
        if not isinstance(wallet_balance_reader, WalletBalanceReader):
            raise TypeError(
                f"wallet_balance_reader must be compatible with WalletBalanceReader, "
                f"got: {type(wallet_balance_reader).__name__}"
            )
        self._positions_reader = positions_reader
        self._open_orders_reader = open_orders_reader
        self._wallet_balance_reader = wallet_balance_reader

    def query_exchange_state(self) -> ExchangeStateSnapshot:
        # Orden fijo, determinista, secuencial -- Positions -> Open Orders
        # -> Wallet Balance, el mismo orden en que estas tres primitives
        # fueron construidas y aceptadas (Hitos 3.70/3.71/3.72). No existe
        # evidencia de que algún orden sea objetivamente superior a otro
        # (son tres GET independientes sin relación causal documentada en
        # la API de Bybit) -- se documenta explícitamente que el orden es
        # arbitrario-pero-fijo, NO una garantía de atomicidad ni de
        # cercanía temporal. Sin concurrencia (deuda futura, no
        # justificada todavía -- ver ADR-002).
        #
        # Fail-closed ante fallo parcial: si cualquiera de los tres readers
        # lanza (ExecutionInfrastructureError u otra excepción), NO se
        # atrapa acá -- se propaga sin envolver, y los readers restantes
        # NUNCA se llaman. No existe ningún snapshot parcial observable:
        # o las tres lecturas de esta ronda tienen éxito, o
        # query_exchange_state() no retorna nada.
        positions = self._positions_reader.query_positions()
        open_orders = self._open_orders_reader.query_open_orders()
        wallet_balance = self._wallet_balance_reader.query_wallet_balance()

        # earliest/latest se calculan EXCLUSIVAMENTE a partir de los
        # server_time_ms remotos ya presentes en los tres sub-snapshots --
        # nunca de time.time() ni de ningún reloj local.
        remote_times = (
            positions.server_time_ms,
            open_orders.server_time_ms,
            wallet_balance.server_time_ms,
        )
        earliest = min(remote_times)
        latest = max(remote_times)
        observation_window = ObservationWindow(
            earliest_remote_time_ms=earliest,
            latest_remote_time_ms=latest,
            remote_time_span_ms=latest - earliest,
        )

        return ExchangeStateSnapshot(
            positions=positions,
            open_orders=open_orders,
            wallet_balance=wallet_balance,
            observation_window=observation_window,
        )

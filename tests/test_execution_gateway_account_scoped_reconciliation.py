import ast
import dataclasses
import inspect
from decimal import Decimal

import pytest

from execution_gateway import account_scoped_reconciliation as _scoped
from execution_gateway import expected_execution_state_contracts as _expected_contracts
from execution_gateway.account_scoped_execution_state_contracts import (
    AccountScopedExchangeStateSnapshot,
    AccountScopedExpectedExecutionState,
)
from execution_gateway.account_scoped_reconciliation import (
    reconcile_account_scoped_execution_state,
)
from execution_gateway.cross_account_reconciliation_error import (
    CrossAccountReconciliationError,
)
from execution_gateway.exchange_state_contracts import (
    ExchangeStateSnapshot,
    ObservationWindow,
)
from execution_gateway.execution_identity_contracts import ExecutionAccountId
from execution_gateway.expected_execution_state_contracts import ExpectedExecutionState
from execution_gateway.open_orders_contracts import ExecutionOpenOrder, OpenOrdersSnapshot
from execution_gateway.positions_contracts import ExecutionPosition, PositionsSnapshot
from execution_gateway.reconciliation_contracts import (
    ReconciliationResult,
    UnexpectedExchangePosition,
)
from execution_gateway.reconciliation_precondition_error import (
    ReconciliationPreconditionError,
)
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot


# Nota de aislamiento de tests (misma razón que en los archivos de 3.76/3.77):
# test_execution_gateway_expected_execution_state_contracts.py hace
# importlib.reload() sobre el módulo de contratos esperados, lo que muta la
# identidad de clase para el resto de la sesión de pytest. Las clases "hoja"
# que ExpectedExecutionState.__post_init__ verifica dinámicamente con
# isinstance deben construirse vía atributo de módulo fresco;
# ExpectedExecutionState en sí se importa normalmente, porque el módulo de
# producción también capturó su referencia en tiempo de colección.
def _scope(**overrides):
    defaults = dict(symbols=("BTCUSDT",))
    defaults.update(overrides)
    return _expected_contracts.ExpectedExecutionScope(**defaults)


def _expected_state(scope=None, positions=(), open_orders=()):
    return ExpectedExecutionState(
        scope=scope if scope is not None else _scope(),
        positions=tuple(positions),
        open_orders=tuple(open_orders),
    )


def _snapshot(positions=(), orders=(), t=1000):
    return ExchangeStateSnapshot(
        positions=PositionsSnapshot(positions=tuple(positions), server_time_ms=t),
        open_orders=OpenOrdersSnapshot(orders=tuple(orders), server_time_ms=t),
        wallet_balance=WalletBalanceSnapshot(
            total_equity=Decimal("1"), total_wallet_balance=Decimal("1"),
            total_available_balance=Decimal("1"), total_initial_margin=Decimal("0"),
            total_maintenance_margin=Decimal("0"), currency_balances=(), server_time_ms=t,
        ),
        observation_window=ObservationWindow(
            earliest_remote_time_ms=t, latest_remote_time_ms=t, remote_time_span_ms=0
        ),
    )


def _position(**overrides):
    defaults = dict(
        symbol="BTCUSDT", side="buy", quantity=Decimal("1"), entry_price=Decimal("100")
    )
    defaults.update(overrides)
    return ExecutionPosition(**defaults)


_ACCOUNT_A = ExecutionAccountId(value="ACCOUNT-A")
_ACCOUNT_B = ExecutionAccountId(value="ACCOUNT-B")


# ---------------------------------------------------------------------------
# Wrappers: envuelven, nunca reconstruyen
# ---------------------------------------------------------------------------

class TestAccountScopedExpectedExecutionState:
    def test_is_frozen(self):
        wrapper = AccountScopedExpectedExecutionState(
            execution_account_id=_ACCOUNT_A, state=_expected_state()
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            wrapper.execution_account_id = _ACCOUNT_B

    def test_preserves_account_id_by_identity(self):
        wrapper = AccountScopedExpectedExecutionState(
            execution_account_id=_ACCOUNT_A, state=_expected_state()
        )
        assert wrapper.execution_account_id is _ACCOUNT_A

    def test_preserves_wrapped_state_by_identity_not_a_copy(self):
        state = _expected_state()
        wrapper = AccountScopedExpectedExecutionState(
            execution_account_id=_ACCOUNT_A, state=state
        )
        assert wrapper.state is state

    def test_does_not_duplicate_inner_fields(self):
        names = {f.name for f in dataclasses.fields(AccountScopedExpectedExecutionState)}
        assert names == {"execution_account_id", "state"}
        for leaked in ("scope", "positions", "open_orders"):
            assert leaked not in names

    def test_rejects_wrong_account_id_type(self):
        with pytest.raises(TypeError):
            AccountScopedExpectedExecutionState(
                execution_account_id="ACCOUNT-A", state=_expected_state()
            )

    def test_rejects_wrong_state_type(self):
        with pytest.raises(TypeError):
            AccountScopedExpectedExecutionState(
                execution_account_id=_ACCOUNT_A, state=_snapshot()
            )


class TestAccountScopedExchangeStateSnapshot:
    def test_is_frozen(self):
        wrapper = AccountScopedExchangeStateSnapshot(
            execution_account_id=_ACCOUNT_A, state=_snapshot()
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            wrapper.state = _snapshot()

    def test_preserves_wrapped_snapshot_by_identity(self):
        snapshot = _snapshot()
        wrapper = AccountScopedExchangeStateSnapshot(
            execution_account_id=_ACCOUNT_A, state=snapshot
        )
        assert wrapper.state is snapshot

    def test_observation_window_preserved_transitively_by_identity(self):
        snapshot = _snapshot(t=987654321)
        window = snapshot.observation_window
        wrapper = AccountScopedExchangeStateSnapshot(
            execution_account_id=_ACCOUNT_A, state=snapshot
        )
        assert wrapper.state.observation_window is window

    def test_does_not_duplicate_inner_fields(self):
        names = {f.name for f in dataclasses.fields(AccountScopedExchangeStateSnapshot)}
        assert names == {"execution_account_id", "state"}
        for leaked in ("positions", "open_orders", "wallet_balance", "observation_window"):
            assert leaked not in names

    def test_rejects_wrong_state_type(self):
        with pytest.raises(TypeError):
            AccountScopedExchangeStateSnapshot(
                execution_account_id=_ACCOUNT_A, state=_expected_state()
            )

    def test_carries_no_bot_identity(self):
        names = {f.name for f in dataclasses.fields(AccountScopedExchangeStateSnapshot)}
        assert not any("bot" in name for name in names)


# ---------------------------------------------------------------------------
# Reconciliación account-scoped
# ---------------------------------------------------------------------------

def _scoped_pair(expected_account, observed_account, *, positions=(), expected_state=None):
    return (
        AccountScopedExpectedExecutionState(
            execution_account_id=expected_account,
            state=expected_state if expected_state is not None else _expected_state(),
        ),
        AccountScopedExchangeStateSnapshot(
            execution_account_id=observed_account, state=_snapshot(positions=positions)
        ),
    )


class TestAccountScopedReconciliation:
    def test_same_account_delegates_and_returns_reconciliation_result(self):
        expected, observed = _scoped_pair(_ACCOUNT_A, _ACCOUNT_A)
        result = reconcile_account_scoped_execution_state(
            expected=expected, observed=observed
        )
        assert isinstance(result, ReconciliationResult)
        assert result.is_in_sync

    def test_same_account_preserves_underlying_divergences(self):
        expected, observed = _scoped_pair(_ACCOUNT_A, _ACCOUNT_A, positions=(_position(),))
        result = reconcile_account_scoped_execution_state(
            expected=expected, observed=observed
        )
        assert [type(d).__name__ for d in result.divergences] == [
            "UnexpectedExchangePosition"
        ]
        assert isinstance(result.divergences[0], UnexpectedExchangePosition)

    def test_observation_window_survives_the_scoped_layer_by_identity(self):
        snapshot = _snapshot(t=555)
        window = snapshot.observation_window
        expected = AccountScopedExpectedExecutionState(
            execution_account_id=_ACCOUNT_A, state=_expected_state()
        )
        observed = AccountScopedExchangeStateSnapshot(
            execution_account_id=_ACCOUNT_A, state=snapshot
        )
        result = reconcile_account_scoped_execution_state(
            expected=expected, observed=observed
        )
        assert result.observation_window is window

    def test_different_accounts_fail_closed(self):
        expected, observed = _scoped_pair(_ACCOUNT_A, _ACCOUNT_B)
        with pytest.raises(CrossAccountReconciliationError):
            reconcile_account_scoped_execution_state(expected=expected, observed=observed)

    def test_cross_account_error_names_both_accounts(self):
        expected, observed = _scoped_pair(_ACCOUNT_A, _ACCOUNT_B)
        with pytest.raises(CrossAccountReconciliationError) as caught:
            reconcile_account_scoped_execution_state(expected=expected, observed=observed)
        assert "ACCOUNT-A" in str(caught.value)
        assert "ACCOUNT-B" in str(caught.value)

    def test_cross_account_check_is_case_sensitive(self):
        expected, observed = _scoped_pair(
            ExecutionAccountId(value="ACCOUNT-A"), ExecutionAccountId(value="account-a")
        )
        with pytest.raises(CrossAccountReconciliationError):
            reconcile_account_scoped_execution_state(expected=expected, observed=observed)

    def test_cross_account_check_is_whitespace_sensitive(self):
        expected, observed = _scoped_pair(
            ExecutionAccountId(value="ACCOUNT-A"), ExecutionAccountId(value=" ACCOUNT-A ")
        )
        with pytest.raises(CrossAccountReconciliationError):
            reconcile_account_scoped_execution_state(expected=expected, observed=observed)

    def test_equal_but_separately_constructed_account_ids_are_accepted(self):
        expected, observed = _scoped_pair(
            ExecutionAccountId(value="ACCOUNT-A"), ExecutionAccountId(value="ACCOUNT-A")
        )
        result = reconcile_account_scoped_execution_state(
            expected=expected, observed=observed
        )
        assert result.is_in_sync

    def test_cross_account_check_runs_before_delegating(self):
        # El expected tiene una LIMIT sin precio: el reconciler subyacente
        # levantaría ReconciliationPreconditionError. Con cuentas distintas
        # debe ganar el fallo de cuenta, probando que se verifica antes.
        bad_expected = _expected_state(
            open_orders=(
                _expected_contracts.ExpectedOpenOrder(
                    order_id="PHX-1", symbol="BTCUSDT", side="buy", order_type="limit",
                    quantity=Decimal("1"), price=None, reduce_only=False,
                ),
            )
        )
        expected = AccountScopedExpectedExecutionState(
            execution_account_id=_ACCOUNT_A, state=bad_expected
        )
        observed = AccountScopedExchangeStateSnapshot(
            execution_account_id=_ACCOUNT_B, state=_snapshot()
        )
        with pytest.raises(CrossAccountReconciliationError):
            reconcile_account_scoped_execution_state(expected=expected, observed=observed)

    def test_underlying_precondition_errors_still_propagate_when_accounts_match(self):
        bad_expected = _expected_state(
            open_orders=(
                _expected_contracts.ExpectedOpenOrder(
                    order_id="PHX-1", symbol="BTCUSDT", side="buy", order_type="limit",
                    quantity=Decimal("1"), price=None, reduce_only=False,
                ),
            )
        )
        expected = AccountScopedExpectedExecutionState(
            execution_account_id=_ACCOUNT_A, state=bad_expected
        )
        observed = AccountScopedExchangeStateSnapshot(
            execution_account_id=_ACCOUNT_A, state=_snapshot()
        )
        with pytest.raises(ReconciliationPreconditionError):
            reconcile_account_scoped_execution_state(expected=expected, observed=observed)

    def test_cross_account_error_is_not_a_reconciliation_precondition_error(self):
        # Fronteras conceptualmente distintas: cableado del caller vs.
        # datos irreconciliables. Un caller debe poder distinguirlas.
        assert not issubclass(
            CrossAccountReconciliationError, ReconciliationPreconditionError
        )
        assert not issubclass(
            ReconciliationPreconditionError, CrossAccountReconciliationError
        )

    @pytest.mark.parametrize("bad", [None, "expected", 42])
    def test_rejects_unwrapped_arguments(self, bad):
        _, observed = _scoped_pair(_ACCOUNT_A, _ACCOUNT_A)
        with pytest.raises(TypeError):
            reconcile_account_scoped_execution_state(expected=bad, observed=observed)

    def test_rejects_raw_expected_state_without_wrapper(self):
        _, observed = _scoped_pair(_ACCOUNT_A, _ACCOUNT_A)
        with pytest.raises(TypeError):
            reconcile_account_scoped_execution_state(
                expected=_expected_state(), observed=observed
            )


# ---------------------------------------------------------------------------
# La capa delega: no reimplementa reconciliación
# ---------------------------------------------------------------------------

class TestDelegationNotDuplication:
    def test_result_is_the_very_object_returned_by_the_inner_reconciler(self, monkeypatch):
        sentinel = ReconciliationResult(
            divergences=(), observation_window=ObservationWindow(
                earliest_remote_time_ms=7, latest_remote_time_ms=7, remote_time_span_ms=0
            ),
        )
        calls = []

        def _spy(*, expected, observed):
            calls.append((expected, observed))
            return sentinel

        monkeypatch.setattr(_scoped, "reconcile_execution_state", _spy)
        expected, observed = _scoped_pair(_ACCOUNT_A, _ACCOUNT_A)
        result = reconcile_account_scoped_execution_state(
            expected=expected, observed=observed
        )
        # Delegó exactamente una vez, con los objetos internos desenvueltos...
        assert len(calls) == 1
        assert calls[0][0] is expected.state
        assert calls[0][1] is observed.state
        # ...y devolvió el resultado tal cual, sin reconstruirlo.
        assert result is sentinel

    def test_does_not_delegate_when_accounts_differ(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            _scoped,
            "reconcile_execution_state",
            lambda **kwargs: calls.append(kwargs),
        )
        expected, observed = _scoped_pair(_ACCOUNT_A, _ACCOUNT_B)
        with pytest.raises(CrossAccountReconciliationError):
            reconcile_account_scoped_execution_state(expected=expected, observed=observed)
        assert calls == []

    def test_module_contains_no_reconciliation_vocabulary_as_code(self):
        # Conductual arriba; esto sólo confirma que no se copió lógica de 3.77.
        tree = ast.parse(inspect.getsource(_scoped))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        for forbidden in (
            "positions", "open_orders", "scope", "symbols", "divergences", "price",
            "quantity", "order_type",
        ):
            assert forbidden not in names

    def test_imports_are_minimal_and_pure(self):
        tree = ast.parse(inspect.getsource(_scoped))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                modules.add(node.module)
        assert modules == {
            "execution_gateway.account_scoped_execution_state_contracts",
            "execution_gateway.cross_account_reconciliation_error",
            "execution_gateway.reconciliation_contracts",
            "execution_gateway.reconciliation_engine",
        }

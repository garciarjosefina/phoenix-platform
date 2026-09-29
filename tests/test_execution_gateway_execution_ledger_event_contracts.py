import ast
import dataclasses
import inspect
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway import execution_ledger_event_contracts as _events
from execution_gateway.execution_identity_contracts import ExecutionAccountId, ExecutionOrderId
from execution_gateway.execution_ledger_event_contracts import (
    ExecutionBotId,
    ExecutionLedgerEvent,
    ExecutionLedgerEventId,
    ExecutionLedgerEventPayload,
    LocalFact,
    ObservedFact,
    OrderAcceptedByExchange,
    OrderIdentityReportedDuplicateByExchange,
    OrderObservedClosed,
    OrderObservedOpen,
    OrderRejectedByExchange,
    OrderSubmissionAttempted,
    OrderSubmissionOutcomeUnknown,
    RemoteFact,
)

_HEX32 = "0123456789abcdef" * 2
_ORDER_ID = ExecutionOrderId(value="ord_" + _HEX32)
_ORDER_ID_2 = ExecutionOrderId(value="ord_" + "a" * 32)
_ACCOUNT = ExecutionAccountId(value="ACCOUNT-A")


def _attempt(**overrides):
    defaults = dict(
        execution_order_id=_ORDER_ID, symbol="BTCUSDT", side="buy", order_type="limit",
        quantity=Decimal("1"), price=Decimal("100"),
    )
    defaults.update(overrides)
    return OrderSubmissionAttempted(**defaults)


def _unknown(**overrides):
    defaults = dict(execution_order_id=_ORDER_ID, reason="transport_failure")
    defaults.update(overrides)
    return OrderSubmissionOutcomeUnknown(**defaults)


def _accepted(**overrides):
    defaults = dict(execution_order_id=_ORDER_ID, exchange_order_id="BYBIT-1", server_time_ms=1000)
    defaults.update(overrides)
    return OrderAcceptedByExchange(**defaults)


def _rejected(**overrides):
    defaults = dict(
        execution_order_id=_ORDER_ID, ret_code=10001, ret_msg="bad order", server_time_ms=1000,
    )
    defaults.update(overrides)
    return OrderRejectedByExchange(**defaults)


def _observed(**overrides):
    defaults = dict(
        execution_order_id=_ORDER_ID, exchange_order_id="BYBIT-1", symbol="BTCUSDT", side="buy",
        order_type="limit", quantity=Decimal("1"), filled_quantity=Decimal("0"), status="new",
        reduce_only=False, server_time_ms=1000, price=Decimal("100"),
    )
    defaults.update(overrides)
    return OrderObservedOpen(**defaults)


def _duplicate(**overrides):
    defaults = dict(
        execution_order_id=_ORDER_ID, ret_code=110072,
        ret_msg="OrderLinkedID is duplicate", server_time_ms=1000,
    )
    defaults.update(overrides)
    return OrderIdentityReportedDuplicateByExchange(**defaults)


def _observed_closed(**overrides):
    # Fixture "Filled" -- derivada del acceptance case principal de
    # ADR-012 D14a (MARKET, ACK perdido, llenada). Los demás casos
    # (Cancelled zero-fill, Cancelled parcial, Rejected) se construyen
    # en TestOrderObservedClosed a partir de este mismo default.
    defaults = dict(
        execution_order_id=_ORDER_ID, exchange_order_id="BYBIT-1", symbol="BTCUSDT",
        side="buy", order_type="limit", quantity=Decimal("1"), filled_quantity=Decimal("1"),
        filled_value=Decimal("100"), remote_status="filled", reduce_only=False,
        server_time_ms=1000, remote_created_time_ms=900, remote_updated_time_ms=950,
        price=Decimal("100"), average_price=Decimal("100"),
    )
    defaults.update(overrides)
    return OrderObservedClosed(**defaults)


def _envelope(*, payload, event_id="evt-1", account=_ACCOUNT, occurred_at_ms=1000):
    return ExecutionLedgerEvent(
        event_id=ExecutionLedgerEventId(value=event_id),
        execution_account_id=account, occurred_at_ms=occurred_at_ms, payload=payload,
    )


# ---------------------------------------------------------------------------
# ExecutionBotId
# ---------------------------------------------------------------------------

class TestExecutionBotId:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            ExecutionBotId(value="A").value = "B"

    def test_exact_string_preserved(self):
        assert ExecutionBotId(value="Bot-01").value == "Bot-01"

    def test_casing_is_identity(self):
        assert ExecutionBotId(value="BOT-A") != ExecutionBotId(value="bot-a")

    def test_padding_is_identity(self):
        assert ExecutionBotId(value=" BOT-A ") != ExecutionBotId(value="BOT-A")

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            ExecutionBotId(value="")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError):
            ExecutionBotId(value="   ")

    @pytest.mark.parametrize("bad", [None, 1, True, b"x"])
    def test_non_str_rejected(self, bad):
        with pytest.raises(TypeError):
            ExecutionBotId(value=bad)

    def test_no_implicit_generation(self):
        with pytest.raises(TypeError):
            ExecutionBotId()

    def test_no_format_constraint_imposed(self):
        # Deliberadamente sin formato congelado (ADR-010, Decisión 6):
        # cualquier string no vacío es válido.
        assert ExecutionBotId(value="anything-goes-123").value == "anything-goes-123"

    def test_module_does_not_import_phoenix_core(self):
        tree = ast.parse(inspect.getsource(_events))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        assert not any("phoenix_core" in (m or "") for m in imported)

    def test_hashable(self):
        assert len({ExecutionBotId(value="A"), ExecutionBotId(value="A")}) == 1


# ---------------------------------------------------------------------------
# ExecutionLedgerEventId
# ---------------------------------------------------------------------------

class TestExecutionLedgerEventId:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            ExecutionLedgerEventId(value="A").value = "B"

    def test_exact_identity(self):
        assert ExecutionLedgerEventId(value="evt-1") == ExecutionLedgerEventId(value="evt-1")
        assert ExecutionLedgerEventId(value="evt-1") != ExecutionLedgerEventId(value="EVT-1")

    def test_no_implicit_generation(self):
        with pytest.raises(TypeError):
            ExecutionLedgerEventId()

    def test_two_calls_with_same_value_are_equal_not_auto_unique(self):
        # Si hubiera generación implícita de UUID, dos instancias con el
        # mismo `value` explícito nunca podrían ser iguales por accidente
        # de un generador interno -- esto confirma que value es lo único
        # que participa.
        assert ExecutionLedgerEventId(value="fixed") == ExecutionLedgerEventId(value="fixed")

    @pytest.mark.parametrize("bad", ["", "   ", None, 1, True])
    def test_rejects_empty_whitespace_and_non_str(self, bad):
        expected = TypeError if not isinstance(bad, (str, type(None))) or isinstance(bad, bool) else ValueError
        with pytest.raises((TypeError, ValueError)):
            ExecutionLedgerEventId(value=bad)

    def test_no_normalization(self):
        assert ExecutionLedgerEventId(value=" evt ").value == " evt "

    def test_hashable(self):
        assert len({ExecutionLedgerEventId(value="A"), ExecutionLedgerEventId(value="A")}) == 1


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------

class TestExecutionLedgerEvent:
    def test_is_frozen(self):
        env = _envelope(payload=_attempt())
        with pytest.raises(dataclasses.FrozenInstanceError):
            env.occurred_at_ms = 2000

    def test_preserves_event_id(self):
        eid = ExecutionLedgerEventId(value="evt-x")
        env = ExecutionLedgerEvent(
            event_id=eid, execution_account_id=_ACCOUNT, occurred_at_ms=1, payload=_attempt(),
        )
        assert env.event_id == eid

    def test_preserves_execution_account_id(self):
        env = _envelope(payload=_attempt())
        assert env.execution_account_id == _ACCOUNT

    def test_preserves_occurred_at_ms_exact(self):
        assert _envelope(payload=_attempt(), occurred_at_ms=123456).occurred_at_ms == 123456

    def test_preserves_payload_by_identity(self):
        payload = _attempt()
        env = _envelope(payload=payload)
        assert env.payload is payload

    def test_rejects_bool_as_occurred_at_ms(self):
        with pytest.raises(TypeError):
            ExecutionLedgerEvent(
                event_id=ExecutionLedgerEventId(value="e"), execution_account_id=_ACCOUNT,
                occurred_at_ms=True, payload=_attempt(),
            )

    def test_rejects_float_as_occurred_at_ms(self):
        with pytest.raises(TypeError):
            ExecutionLedgerEvent(
                event_id=ExecutionLedgerEventId(value="e"), execution_account_id=_ACCOUNT,
                occurred_at_ms=1.5, payload=_attempt(),
            )

    def test_rejects_negative_occurred_at_ms(self):
        with pytest.raises(ValueError):
            ExecutionLedgerEvent(
                event_id=ExecutionLedgerEventId(value="e"), execution_account_id=_ACCOUNT,
                occurred_at_ms=-1, payload=_attempt(),
            )

    def test_rejects_wrong_payload_type(self):
        with pytest.raises(TypeError):
            ExecutionLedgerEvent(
                event_id=ExecutionLedgerEventId(value="e"), execution_account_id=_ACCOUNT,
                occurred_at_ms=1, payload="not a payload",
            )

    def test_rejects_wrong_account_id_type(self):
        with pytest.raises(TypeError):
            ExecutionLedgerEvent(
                event_id=ExecutionLedgerEventId(value="e"), execution_account_id="ACCOUNT-A",
                occurred_at_ms=1, payload=_attempt(),
            )

    def test_no_clock_calls_in_module(self):
        source = inspect.getsource(_events)
        for forbidden in ("time.time", "datetime.now", "clock.now", "now_ms"):
            assert forbidden not in source

    def test_two_distinct_events_can_share_occurred_at_ms(self):
        e1 = _envelope(payload=_attempt(), event_id="evt-1", occurred_at_ms=1000)
        e2 = _envelope(payload=_unknown(), event_id="evt-2", occurred_at_ms=1000)
        assert e1.occurred_at_ms == e2.occurred_at_ms
        assert e1.event_id != e2.event_id
        assert e1 != e2

    def test_independently_constructed_equal_envelopes_compare_equal(self):
        e1 = _envelope(payload=_attempt(), event_id="evt-1", occurred_at_ms=1000)
        e2 = _envelope(payload=_attempt(), event_id="evt-1", occurred_at_ms=1000)
        assert e1 == e2
        assert e1 is not e2

    def test_envelope_has_no_sequence_field(self):
        # ADR-010 Decisión 9: el mecanismo de ordering físico queda fuera
        # del envelope lógico.
        names = {f.name for f in dataclasses.fields(ExecutionLedgerEvent)}
        assert "sequence" not in names

    def test_envelope_has_no_execution_order_id_field(self):
        # No todo evento tiene orden -- vive en el payload (ADR-010 D5).
        names = {f.name for f in dataclasses.fields(ExecutionLedgerEvent)}
        assert "execution_order_id" not in names

    def test_envelope_fields_are_exactly_four(self):
        names = {f.name for f in dataclasses.fields(ExecutionLedgerEvent)}
        assert names == {"event_id", "execution_account_id", "occurred_at_ms", "payload"}


# ---------------------------------------------------------------------------
# OrderSubmissionAttempted
# ---------------------------------------------------------------------------

class TestOrderSubmissionAttempted:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _attempt().quantity = Decimal("2")

    def test_is_local_fact(self):
        assert isinstance(_attempt(), LocalFact)
        assert isinstance(_attempt(), ExecutionLedgerEventPayload)

    def test_bot_id_defaults_to_none(self):
        assert _attempt().execution_bot_id is None

    def test_bot_id_can_be_present(self):
        bot = ExecutionBotId(value="BOT-1")
        assert _attempt(execution_bot_id=bot).execution_bot_id is bot

    def test_bot_id_presence_does_not_contaminate_other_fields(self):
        # bot_id nunca se embebe en ningún otro campo del hecho (ni en el
        # texto de symbol, ni en ningún otro dominio económico).
        bot = ExecutionBotId(value="BOT-1")
        with_bot = _attempt(execution_bot_id=bot)
        without_bot = _attempt(execution_bot_id=None)
        assert with_bot.symbol == without_bot.symbol == "BTCUSDT"
        assert with_bot.side == without_bot.side
        assert with_bot.order_type == without_bot.order_type
        assert with_bot.quantity == without_bot.quantity
        assert with_bot.price == without_bot.price

    def test_independently_constructed_equal_attempts_compare_equal(self):
        # Igualdad por valor estándar del dataclass -- dos construcciones
        # independientes con exactamente los mismos campos son iguales.
        a1 = _attempt()
        a2 = _attempt()
        assert a1 == a2
        assert a1 is not a2

    def test_execution_order_id_exact(self):
        assert _attempt().execution_order_id == _ORDER_ID

    def test_symbol_exact(self):
        assert _attempt(symbol="ETHUSDT").symbol == "ETHUSDT"

    def test_side_validated(self):
        with pytest.raises(ValueError):
            _attempt(side="long")

    def test_order_type_validated(self):
        with pytest.raises(ValueError):
            _attempt(order_type="stop")

    def test_quantity_is_decimal(self):
        with pytest.raises(TypeError):
            _attempt(quantity=1.0)

    def test_limit_requires_price(self):
        with pytest.raises(ValueError):
            _attempt(order_type="limit", price=None)

    def test_market_requires_no_price(self):
        with pytest.raises(ValueError):
            _attempt(order_type="market", price=Decimal("100"))

    def test_market_without_price_is_valid(self):
        assert _attempt(order_type="market", price=None).price is None

    def test_no_remote_success_fields(self):
        names = {f.name for f in dataclasses.fields(OrderSubmissionAttempted)}
        assert "exchange_order_id" not in names
        assert "server_time_ms" not in names

    def test_rejects_wrong_bot_id_type(self):
        with pytest.raises(TypeError):
            _attempt(execution_bot_id="BOT-1")

    def test_rejects_wrong_execution_order_id_type(self):
        with pytest.raises(TypeError):
            OrderSubmissionAttempted(
                execution_order_id="ord_x", symbol="BTCUSDT", side="buy",
                order_type="market", quantity=Decimal("1"),
            )


# ---------------------------------------------------------------------------
# OrderSubmissionOutcomeUnknown
# ---------------------------------------------------------------------------

class TestOrderSubmissionOutcomeUnknown:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _unknown().reason = "malformed_response"

    def test_is_local_fact(self):
        assert isinstance(_unknown(), LocalFact)

    def test_same_execution_order_id_as_attempt(self):
        attempt = _attempt()
        unknown = _unknown(execution_order_id=attempt.execution_order_id)
        assert unknown.execution_order_id == attempt.execution_order_id

    def test_no_success_or_reject_fields(self):
        names = {f.name for f in dataclasses.fields(OrderSubmissionOutcomeUnknown)}
        assert "exchange_order_id" not in names
        assert "ret_code" not in names
        assert "status" not in names

    def test_no_exception_object_stored(self):
        names = {f.name for f in dataclasses.fields(OrderSubmissionOutcomeUnknown)}
        assert "exception" not in names
        assert "traceback" not in names

    @pytest.mark.parametrize(
        "reason",
        ["transport_failure", "malformed_response", "ambiguous_business_response", "identity_mismatch"],
    )
    def test_accepts_all_four_documented_reasons(self, reason):
        assert _unknown(reason=reason).reason == reason

    def test_rejects_arbitrary_reason(self):
        with pytest.raises(ValueError):
            _unknown(reason="server_exploded")

    def test_two_events_can_share_occurred_at_ms_via_envelope(self):
        attempt_env = _envelope(payload=_attempt(), event_id="e1", occurred_at_ms=500)
        unknown_env = _envelope(payload=_unknown(), event_id="e2", occurred_at_ms=500)
        assert attempt_env.occurred_at_ms == unknown_env.occurred_at_ms
        assert attempt_env.event_id != unknown_env.event_id


# ---------------------------------------------------------------------------
# OrderAcceptedByExchange
# ---------------------------------------------------------------------------

class TestOrderAcceptedByExchange:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _accepted().exchange_order_id = "X"

    def test_is_remote_fact(self):
        assert isinstance(_accepted(), RemoteFact)
        assert not isinstance(_accepted(), LocalFact)

    def test_execution_order_id_and_exchange_order_id_are_separate_fields(self):
        ev = _accepted(exchange_order_id="BYBIT-DIFFERENT")
        assert ev.execution_order_id == _ORDER_ID
        assert ev.exchange_order_id == "BYBIT-DIFFERENT"
        assert ev.execution_order_id.value != ev.exchange_order_id

    def test_both_ids_required_non_empty(self):
        with pytest.raises(ValueError):
            _accepted(exchange_order_id="")

    def test_no_silent_fallback_between_ids(self):
        # No debe existir ningún mecanismo que copie uno al otro.
        ev = _accepted()
        assert ev.execution_order_id.value != ev.exchange_order_id

    def test_missing_execution_order_id_is_rejected_not_backfilled(self):
        # execution_order_id=None NUNCA debe rellenarse silenciosamente
        # con exchange_order_id -- ADR-005 D4 / ADR-009: exchange_order_id
        # nunca es fallback de identidad Phoenix.
        with pytest.raises(TypeError):
            _accepted(execution_order_id=None)

    def test_server_time_ms_exact(self):
        assert _accepted(server_time_ms=999999).server_time_ms == 999999

    def test_server_time_ms_rejects_bool(self):
        with pytest.raises(TypeError):
            _accepted(server_time_ms=True)

    def test_server_time_ms_rejects_negative(self):
        with pytest.raises(ValueError):
            _accepted(server_time_ms=-1)

    def test_no_normalization_of_exchange_order_id(self):
        assert _accepted(exchange_order_id=" BYBIT-1 ").exchange_order_id == " BYBIT-1 "


# ---------------------------------------------------------------------------
# OrderRejectedByExchange
# ---------------------------------------------------------------------------

class TestOrderRejectedByExchange:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _rejected().ret_code = 1

    def test_is_remote_fact(self):
        assert isinstance(_rejected(), RemoteFact)

    def test_not_confused_with_unknown(self):
        assert not isinstance(_rejected(), LocalFact)
        assert type(_rejected()) is not OrderSubmissionOutcomeUnknown

    def test_no_exchange_order_id_field(self):
        # Un rechazo nunca produce identidad remota -- la orden nunca
        # llegó a crearse.
        names = {f.name for f in dataclasses.fields(OrderRejectedByExchange)}
        assert "exchange_order_id" not in names

    def test_ret_code_and_ret_msg_exact(self):
        ev = _rejected(ret_code=110004, ret_msg="insufficient balance")
        assert ev.ret_code == 110004
        assert ev.ret_msg == "insufficient balance"

    def test_ret_code_rejects_bool(self):
        with pytest.raises(TypeError):
            _rejected(ret_code=True)

    def test_ret_msg_rejects_empty(self):
        with pytest.raises(ValueError):
            _rejected(ret_msg="")

    def test_server_time_ms_present(self):
        assert _rejected(server_time_ms=42).server_time_ms == 42

    def test_authority_is_structural_not_configurable(self):
        # No existe ningún parámetro authority= en el constructor.
        sig = inspect.signature(OrderRejectedByExchange.__init__)
        assert "authority" not in sig.parameters

    # -----------------------------------------------------------------
    # ADR-013 D3, reforzado por la Resolución del STOP punto (5): 110072
    # NUNCA es representable como OrderRejectedByExchange -- el hecho
    # correcto es OrderIdentityReportedDuplicateByExchange (Hito 3.89).
    # -----------------------------------------------------------------

    def test_rejects_ret_code_110072(self):
        with pytest.raises(ValueError, match="110072"):
            _rejected(ret_code=110072)

    @pytest.mark.parametrize("ret_code", [10001, 110003, 110004, 110007])
    def test_other_documented_rejection_codes_still_construct(self, ret_code):
        # El conjunto de rechazo de negocio reconocido hoy en
        # bybit_gateway.py (_ORDER_REJECTION_RET_CODES) sigue funcionando
        # sin cambio -- la guarda nueva es exclusiva de 110072, no una
        # ampliación de la validación general de ret_code.
        ev = _rejected(ret_code=ret_code)
        assert ev.ret_code == ret_code


# ---------------------------------------------------------------------------
# OrderObservedOpen
# ---------------------------------------------------------------------------

class TestOrderObservedOpen:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _observed().status = "new"

    def test_is_observed_fact(self):
        ev = _observed()
        assert isinstance(ev, ObservedFact)
        assert not isinstance(ev, RemoteFact)
        assert not isinstance(ev, LocalFact)

    def test_not_convertible_to_accepted(self):
        assert type(_observed()) is not OrderAcceptedByExchange

    def test_preserves_ids(self):
        ev = _observed(exchange_order_id="BYBIT-9")
        assert ev.execution_order_id == _ORDER_ID
        assert ev.exchange_order_id == "BYBIT-9"

    def test_execution_order_id_is_mandatory(self):
        # Resolución del STOP de ADR-010 (2026-08-29): OrderObservedOpen
        # V1 representa EXCLUSIVAMENTE el caso correlacionado -- exige
        # ExecutionOrderId, nunca acepta None.
        with pytest.raises(TypeError):
            OrderObservedOpen(
                execution_order_id=None, exchange_order_id="BYBIT-9", symbol="BTCUSDT",
                side="buy", order_type="limit", quantity=Decimal("1"),
                filled_quantity=Decimal("0"), status="new", reduce_only=False,
                server_time_ms=1000, price=Decimal("100"),
            )

    def test_execution_order_id_rejects_a_bare_string_not_the_value_object(self):
        # No se acepta un string suelto en el lugar de ExecutionOrderId --
        # evita que un caller "invente" una identidad Phoenix ad-hoc en
        # vez de pasar el value object real.
        with pytest.raises(TypeError):
            OrderObservedOpen(
                execution_order_id="ord_" + "a" * 32, exchange_order_id="BYBIT-9",
                symbol="BTCUSDT", side="buy", order_type="limit", quantity=Decimal("1"),
                filled_quantity=Decimal("0"), status="new", reduce_only=False,
                server_time_ms=1000, price=Decimal("100"),
            )

    def test_exchange_order_id_never_used_as_fallback_for_execution_order_id(self):
        # Resolución del STOP: PROHIBIDO usar exchange_order_id como
        # fallback de identidad Phoenix. Omitir execution_order_id nunca
        # debe rellenarse silenciosamente con exchange_order_id -- debe
        # fallar, no inventar la identidad.
        with pytest.raises(TypeError):
            OrderObservedOpen(
                exchange_order_id="BYBIT-9", symbol="BTCUSDT", side="buy",
                order_type="limit", quantity=Decimal("1"), filled_quantity=Decimal("0"),
                status="new", reduce_only=False, server_time_ms=1000, price=Decimal("100"),
            )

    def test_orphan_open_order_case_has_no_dedicated_event_type_in_v1(self):
        # Resolución del STOP: las huérfanas (order_id is None en
        # ExecutionOpenOrder) NO generan OrderObservedOpen y NO existe
        # ningún tipo de evento dedicado (p. ej.
        # "UnattributedOrderObservedOpen") para representarlas -- siguen
        # siendo observables únicamente vía Reconciliation V1
        # (UnattributedExchangeOpenOrder). Deuda arquitectónica explícita,
        # no implementada aquí.
        import execution_gateway.execution_ledger_event_contracts as _mod
        event_type_names = {
            name for name, obj in vars(_mod).items()
            if isinstance(obj, type) and issubclass(obj, ExecutionLedgerEventPayload)
        }
        assert "UnattributedOrderObservedOpen" not in event_type_names
        # Exactamente 7 tipos concretos (5 de ADR-010/Hito 3.83 + el séptimo
        # tipo de ADR-013/Hito 3.89, OrderIdentityReportedDuplicateByExchange
        # + el octavo tipo de ADR-012/Hito 3.94, OrderObservedClosed) + el
        # marcador base + los 3 marcadores de autoridad = 11; ninguno
        # adicional para huérfanas.
        concrete_event_types = event_type_names - {
            "ExecutionLedgerEventPayload", "LocalFact", "RemoteFact", "ObservedFact",
        }
        assert len(concrete_event_types) == 7

    def test_status_validated(self):
        with pytest.raises(ValueError):
            _observed(status="filled")

    def test_filled_quantity_can_be_zero(self):
        assert _observed(filled_quantity=Decimal("0")).filled_quantity == Decimal("0")

    def test_filled_quantity_rejects_negative(self):
        with pytest.raises(ValueError):
            _observed(filled_quantity=Decimal("-1"))

    def test_price_can_be_none_for_market(self):
        assert _observed(order_type="market", price=None).price is None

    def test_server_time_ms_present(self):
        assert _observed(server_time_ms=777).server_time_ms == 777

    def test_reduce_only_rejects_non_bool(self):
        with pytest.raises(TypeError):
            _observed(reduce_only=1)


# ---------------------------------------------------------------------------
# OrderObservedClosed (Hito 3.94, ADR-012 D16 + corrección post-3.85,
# reafirmado sin cambios por ADR-015). Octavo tipo de evento, OBSERVED,
# terminal y absorbente. Mecánicamente equivalente en field set e
# invariantes a BybitOrderHistoryOrderFound (Hito 3.86) -- los nombres de
# test que siguen replican deliberadamente los de
# test_execution_gateway_order_history_lookup_contracts.py para dejar la
# correspondencia mecánica auditable, no por coincidencia.
# ---------------------------------------------------------------------------

class TestOrderObservedClosedConstruction:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _observed_closed().remote_status = "cancelled"

    def test_is_observed_fact(self):
        ev = _observed_closed()
        assert isinstance(ev, ObservedFact)
        assert not isinstance(ev, RemoteFact)
        assert not isinstance(ev, LocalFact)

    def test_not_convertible_to_accepted_or_rejected(self):
        assert type(_observed_closed()) is not OrderAcceptedByExchange
        assert type(_observed_closed()) is not OrderRejectedByExchange

    # A. valid Filled
    def test_valid_filled(self):
        ev = _observed_closed(
            remote_status="filled", quantity=Decimal("1"), filled_quantity=Decimal("1"),
            filled_value=Decimal("100"), average_price=Decimal("100"),
        )
        assert ev.remote_status == "filled"
        assert ev.filled_quantity == ev.quantity

    # B. valid Cancelled zero-fill
    def test_valid_cancelled_zero_fill(self):
        ev = _observed_closed(
            remote_status="cancelled", quantity=Decimal("1"), filled_quantity=Decimal("0"),
            filled_value=Decimal("0"), average_price=None, cancel_type="CancelByUser",
        )
        assert ev.remote_status == "cancelled"
        assert ev.filled_quantity == Decimal("0")

    # C. valid Cancelled partial-fill
    def test_valid_cancelled_partial_fill(self):
        ev = _observed_closed(
            remote_status="cancelled", quantity=Decimal("1"), filled_quantity=Decimal("0.4"),
            filled_value=Decimal("40"), average_price=Decimal("100"), cancel_type="CancelByUser",
        )
        assert ev.filled_quantity == Decimal("0.4")
        assert ev.filled_quantity < ev.quantity

    # D. valid Rejected
    def test_valid_rejected(self):
        ev = _observed_closed(
            remote_status="rejected", quantity=Decimal("1"), filled_quantity=Decimal("0"),
            filled_value=Decimal("0"), average_price=None, reject_reason="EC_InsufficientBalance",
        )
        assert ev.remote_status == "rejected"
        assert ev.filled_quantity == Decimal("0")

    # E. MARKET closed
    def test_market_closed(self):
        ev = _observed_closed(order_type="market", price=None)
        assert ev.price is None

    # F. LIMIT closed
    def test_limit_closed(self):
        ev = _observed_closed(order_type="limit", price=Decimal("100"))
        assert ev.price == Decimal("100")

    def test_preserves_ids(self):
        ev = _observed_closed(exchange_order_id="BYBIT-9")
        assert ev.execution_order_id == _ORDER_ID
        assert ev.exchange_order_id == "BYBIT-9"

    def test_execution_order_id_preserved_by_identity(self):
        marker = ExecutionOrderId(value="ord_" + "d" * 32)
        ev = _observed_closed(execution_order_id=marker)
        assert ev.execution_order_id is marker

    def test_execution_order_id_is_mandatory(self):
        with pytest.raises(TypeError):
            _observed_closed(execution_order_id=None)

    def test_execution_order_id_rejects_a_bare_string_not_the_value_object(self):
        with pytest.raises(TypeError):
            _observed_closed(execution_order_id="ord_" + "a" * 32)

    def test_exchange_order_id_never_used_as_fallback_for_execution_order_id(self):
        kwargs = dict(
            exchange_order_id="BYBIT-9", symbol="BTCUSDT", side="buy", order_type="limit",
            quantity=Decimal("1"), filled_quantity=Decimal("1"), filled_value=Decimal("100"),
            remote_status="filled", reduce_only=False, server_time_ms=1000,
            remote_created_time_ms=900, remote_updated_time_ms=950, price=Decimal("100"),
            average_price=Decimal("100"),
        )
        with pytest.raises(TypeError):
            OrderObservedClosed(**kwargs)

    def test_exchange_order_id_must_not_be_empty(self):
        with pytest.raises(ValueError):
            _observed_closed(exchange_order_id="")

    def test_exchange_order_id_must_be_str(self):
        with pytest.raises(TypeError):
            _observed_closed(exchange_order_id=123)

    def test_no_forbidden_attributes_on_real_instance(self):
        # Mismo patrón que el N21 de Hito 3.89 (hasattr sobre instancia
        # real, no dataclasses.fields sobre la clase) -- confirma que
        # ningún campo de orquestación/envelope/credenciales se cuela
        # silenciosamente en este contrato puro.
        ev = _observed_closed()
        for forbidden in (
            "bot_id", "execution_bot_id", "account_id", "execution_account_id",
            "authority", "sequence", "occurred_at_ms", "committed_at_ms", "event_id",
            "api_key", "api_secret", "credential", "headers", "raw_response",
            "terminal", "is_terminal", "leaves_qty", "cum_exec_fee",
        ):
            assert not hasattr(ev, forbidden), forbidden


class TestOrderObservedClosedTypeAttacks:
    @pytest.mark.parametrize("bad", [None, "1", True, 1.5, [], {}, b"x", object()])
    def test_execution_order_id_rejects_non_value_object(self, bad):
        with pytest.raises(TypeError):
            _observed_closed(execution_order_id=bad)

    @pytest.mark.parametrize("field", ["quantity", "filled_quantity", "filled_value"])
    @pytest.mark.parametrize("bad", [None, "1", True, 1.5, [], {}, object()])
    def test_decimal_fields_reject_non_decimal(self, field, bad):
        with pytest.raises(TypeError):
            _observed_closed(**{field: bad})

    @pytest.mark.parametrize("field", ["quantity", "filled_quantity", "filled_value"])
    def test_decimal_fields_reject_infinity(self, field):
        with pytest.raises(ValueError):
            _observed_closed(**{field: Decimal("Infinity")})

    def test_price_rejects_non_decimal_when_present(self):
        with pytest.raises(TypeError):
            _observed_closed(price=100.0)

    def test_average_price_rejects_non_decimal_when_present(self):
        with pytest.raises(TypeError):
            _observed_closed(average_price=100.0)

    @pytest.mark.parametrize("bad", [None, "false", 1, 0, 1.0, []])
    def test_reduce_only_rejects_non_bool(self, bad):
        with pytest.raises(TypeError):
            _observed_closed(reduce_only=bad)

    @pytest.mark.parametrize("field", [
        "server_time_ms", "remote_created_time_ms", "remote_updated_time_ms",
    ])
    @pytest.mark.parametrize("bad", [None, "1000", 1.5, [], {}, object()])
    def test_timestamp_fields_reject_non_int(self, field, bad):
        with pytest.raises(TypeError):
            _observed_closed(**{field: bad})

    @pytest.mark.parametrize("field", [
        "server_time_ms", "remote_created_time_ms", "remote_updated_time_ms",
    ])
    def test_timestamp_fields_reject_bool(self, field):
        # bool es subclase de int -- True/False no deben colarse como
        # timestamp válido (mismo patrón que el resto del archivo).
        with pytest.raises(TypeError):
            _observed_closed(**{field: True})

    @pytest.mark.parametrize("field", [
        "server_time_ms", "remote_created_time_ms", "remote_updated_time_ms",
    ])
    def test_timestamp_fields_reject_negative(self, field):
        with pytest.raises(ValueError):
            _observed_closed(**{field: -1})

    def test_remote_status_rejects_non_str(self):
        with pytest.raises(TypeError):
            _observed_closed(remote_status=1)

    def test_symbol_rejects_non_str(self):
        with pytest.raises(TypeError):
            _observed_closed(symbol=None)

    def test_cancel_type_rejects_non_str_when_present(self):
        with pytest.raises(TypeError):
            _observed_closed(remote_status="cancelled", cancel_type=1, filled_quantity=Decimal("0"),
                              filled_value=Decimal("0"), average_price=None)

    def test_reject_reason_rejects_non_str_when_present(self):
        with pytest.raises(TypeError):
            _observed_closed(reject_reason=1)


class TestOrderObservedClosedRemoteStatus:
    def test_rejects_open_status(self):
        with pytest.raises(ValueError):
            _observed_closed(remote_status="new")

    def test_rejects_impossible_closed_status_deactivated(self):
        with pytest.raises(ValueError):
            _observed_closed(remote_status="deactivated")

    def test_rejects_impossible_closed_status_partially_filled_cancelled(self):
        with pytest.raises(ValueError):
            _observed_closed(remote_status="partially_filled_cancelled")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError):
            _observed_closed(remote_status="")

    def test_accepts_filled(self):
        assert _observed_closed(
            remote_status="filled", filled_quantity=Decimal("1"), quantity=Decimal("1"),
            filled_value=Decimal("100"), average_price=Decimal("100"),
        ).remote_status == "filled"

    def test_accepts_cancelled(self):
        assert _observed_closed(
            remote_status="cancelled", filled_quantity=Decimal("0"), quantity=Decimal("1"),
            filled_value=Decimal("0"), average_price=None,
        ).remote_status == "cancelled"

    def test_accepts_rejected(self):
        assert _observed_closed(
            remote_status="rejected", filled_quantity=Decimal("0"), quantity=Decimal("1"),
            filled_value=Decimal("0"), average_price=None,
        ).remote_status == "rejected"


class TestOrderObservedClosedCrossFieldInvariants:
    def test_filled_requires_full_fill(self):
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="filled", quantity=Decimal("1"), filled_quantity=Decimal("0.9"),
            )

    def test_rejected_requires_zero_fill(self):
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="rejected", quantity=Decimal("1"), filled_quantity=Decimal("0.1"),
                filled_value=Decimal("10"), average_price=Decimal("100"),
            )

    def test_cancelled_requires_partial_fill_strictly_below_quantity(self):
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="cancelled", quantity=Decimal("1"), filled_quantity=Decimal("1"),
                filled_value=Decimal("100"), average_price=Decimal("100"),
            )

    def test_average_price_none_requires_zero_fill(self):
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="cancelled", quantity=Decimal("1"), filled_quantity=Decimal("0.4"),
                filled_value=Decimal("40"), average_price=None,
            )

    def test_average_price_present_requires_nonzero_fill(self):
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="cancelled", quantity=Decimal("1"), filled_quantity=Decimal("0"),
                filled_value=Decimal("0"), average_price=Decimal("100"),
            )

    def test_average_price_must_be_positive_when_present(self):
        with pytest.raises(ValueError):
            _observed_closed(average_price=Decimal("0"))

    def test_filled_value_zero_iff_filled_quantity_zero_direction_a(self):
        # filled_value > 0 con filled_quantity == 0
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="rejected", quantity=Decimal("1"), filled_quantity=Decimal("0"),
                filled_value=Decimal("10"), average_price=None,
            )

    def test_filled_value_zero_iff_filled_quantity_zero_direction_b(self):
        # filled_value == 0 con filled_quantity > 0
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="cancelled", quantity=Decimal("1"), filled_quantity=Decimal("0.4"),
                filled_value=Decimal("0"), average_price=Decimal("100"),
            )

    def test_filled_quantity_cannot_exceed_quantity(self):
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="filled", quantity=Decimal("1"), filled_quantity=Decimal("1.1"),
                filled_value=Decimal("110"), average_price=Decimal("100"),
            )


class TestOrderObservedClosedOrderTypePriceCoupling:
    def test_limit_requires_price(self):
        with pytest.raises(ValueError):
            _observed_closed(order_type="limit", price=None)

    def test_market_forbids_price(self):
        with pytest.raises(ValueError):
            _observed_closed(order_type="market", price=Decimal("100"))

    def test_limit_with_price_is_valid(self):
        assert _observed_closed(order_type="limit", price=Decimal("100")).price == Decimal("100")


class TestOrderObservedClosedCancelAndRejectReason:
    def test_cancel_type_must_be_none_unless_cancelled(self):
        with pytest.raises(ValueError):
            _observed_closed(remote_status="filled", cancel_type="CancelByUser")

    def test_cancel_type_allowed_when_cancelled(self):
        ev = _observed_closed(
            remote_status="cancelled", quantity=Decimal("1"), filled_quantity=Decimal("0"),
            filled_value=Decimal("0"), average_price=None, cancel_type="CancelByUser",
        )
        assert ev.cancel_type == "CancelByUser"

    def test_cancel_type_rejects_empty_string(self):
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="cancelled", quantity=Decimal("1"), filled_quantity=Decimal("0"),
                filled_value=Decimal("0"), average_price=None, cancel_type="",
            )

    def test_reject_reason_preserved_verbatim(self):
        ev = _observed_closed(
            remote_status="rejected", quantity=Decimal("1"), filled_quantity=Decimal("0"),
            filled_value=Decimal("0"), average_price=None, reject_reason="EC_InsufficientBalance",
        )
        assert ev.reject_reason == "EC_InsufficientBalance"

    def test_reject_reason_not_coupled_to_remote_status(self):
        # ADR-012 D8: reject_reason NO está acoplado estrictamente a
        # remote_status -- la propia taxonomía de Bybit lo usa también en
        # cancelaciones (p. ej. EC_CancelByOrderValueZero).
        ev = _observed_closed(
            remote_status="cancelled", quantity=Decimal("1"), filled_quantity=Decimal("0"),
            filled_value=Decimal("0"), average_price=None, cancel_type="CancelByUser",
            reject_reason="EC_CancelByOrderValueZero",
        )
        assert ev.reject_reason == "EC_CancelByOrderValueZero"

    def test_reject_reason_rejects_empty_string(self):
        with pytest.raises(ValueError):
            _observed_closed(reject_reason="")


class TestOrderObservedClosedTimestamps:
    def test_updated_must_not_precede_created(self):
        with pytest.raises(ValueError):
            _observed_closed(remote_created_time_ms=1000, remote_updated_time_ms=999)

    def test_equal_created_and_updated_is_valid(self):
        ev = _observed_closed(remote_created_time_ms=1000, remote_updated_time_ms=1000)
        assert ev.remote_created_time_ms == ev.remote_updated_time_ms == 1000

    def test_server_time_ms_is_independent_of_remote_timestamps(self):
        # server_time_ms describe ESTA consulta, no la orden -- puede ser
        # anterior, igual o posterior a los timestamps remotos sin que
        # ninguna invariante lo relacione con ellos.
        ev = _observed_closed(
            remote_created_time_ms=1000, remote_updated_time_ms=1000, server_time_ms=50,
        )
        assert ev.server_time_ms == 50

    def test_server_time_ms_is_not_silently_reconstructed(self):
        # Auditoría adversarial 3.94, MENOR-3: distinto de un test de tipo
        # -- prueba que el valor RECIBIDO llega intacto, no que un valor
        # inválido sea rechazado. Si el contrato alguna vez reconstruyera
        # server_time_ms (p. ej. a un valor fijo) DESPUÉS de la validación,
        # este test lo detectaría porque el valor recibido, no el
        # reconstruido, es el que se compara.
        assert _observed_closed(server_time_ms=4242).server_time_ms == 4242
        assert _observed_closed(server_time_ms=0).server_time_ms == 0


# ---------------------------------------------------------------------------
# Preservación literal de valores (Hito 3.94, corrección post-auditoría
# adversarial, IMPORTANTE-1). Los tests de construcción/tipo/invariantes de
# arriba usan fixtures uniformes (economía por defecto en todos los campos
# no atacados) -- una mutación que sobrescribiera un campo DESPUÉS de la
# validación (p. ej. `object.__setattr__(self, 'reduce_only', False)`) no
# fallaría ningún test existente porque el default YA es ese valor. Cada
# test de esta clase usa al menos un valor deliberadamente distinto del
# default en el campo que verifica, y afirma preservación literal --
# mismo patrón que `test_copies_each_field_with_a_non_default_economy` de
# Hito 3.91 y `test_symbol_with_padding_preserved_literal` de 3.91/3.92.
# ---------------------------------------------------------------------------

class TestOrderObservedClosedValuePreservation:
    def test_preserves_every_field_with_a_fully_non_default_economy(self):
        # Ninguno de estos valores coincide con el default de
        # _observed_closed() -- una mutación que sobrescriba CUALQUIER
        # campo tras la validación (con el valor por defecto u otro fijo)
        # rompe esta única aserción exhaustiva.
        marker = ExecutionOrderId(value="ord_" + "e" * 32)
        ev = OrderObservedClosed(
            execution_order_id=marker,
            exchange_order_id="BYBIT-XORDER-77",
            symbol="ethusdt",
            side="sell",
            order_type="limit",
            quantity=Decimal("1.3700"),
            filled_quantity=Decimal("0.4100"),
            filled_value=Decimal("39.73"),
            remote_status="cancelled",
            reduce_only=True,
            server_time_ms=4242,
            remote_created_time_ms=900,
            remote_updated_time_ms=1950,
            price=Decimal("1234.567"),
            average_price=Decimal("96.90"),
            cancel_type="CancelByUser",
            reject_reason="EC_CancelByOrderValueZero",
        )
        assert ev.execution_order_id is marker
        assert ev.exchange_order_id == "BYBIT-XORDER-77"
        assert ev.symbol == "ethusdt"
        assert ev.side == "sell"
        assert ev.order_type == "limit"
        assert ev.quantity == Decimal("1.3700")
        assert ev.filled_quantity == Decimal("0.4100")
        assert ev.filled_value == Decimal("39.73")
        assert ev.remote_status == "cancelled"
        assert ev.reduce_only is True
        assert ev.server_time_ms == 4242
        assert ev.remote_created_time_ms == 900
        assert ev.remote_updated_time_ms == 1950
        assert ev.price == Decimal("1234.567")
        assert ev.average_price == Decimal("96.90")
        assert ev.cancel_type == "CancelByUser"
        assert ev.reject_reason == "EC_CancelByOrderValueZero"

    def test_reduce_only_true_preserved(self):
        assert _observed_closed(reduce_only=True).reduce_only is True

    def test_reduce_only_false_preserved(self):
        assert _observed_closed(reduce_only=False).reduce_only is False

    def test_side_sell_preserved(self):
        assert _observed_closed(side="sell").side == "sell"

    def test_side_buy_preserved(self):
        assert _observed_closed(side="buy").side == "buy"

    def test_order_type_market_preserved(self):
        ev = _observed_closed(order_type="market", price=None)
        assert ev.order_type == "market"

    def test_order_type_limit_preserved(self):
        ev = _observed_closed(order_type="limit", price=Decimal("100"))
        assert ev.order_type == "limit"

    def test_symbol_lowercase_preserved_without_case_normalization(self):
        # "ethusdt" discrimina .upper()/.lower()/.casefold() -- ninguna
        # normalización de case está autorizada (symbol es literal, mismo
        # tratamiento que ADR-005 Decisión 3).
        assert _observed_closed(symbol="ethusdt").symbol == "ethusdt"

    def test_symbol_with_padding_preserved_literal(self):
        # Espacios discriminan un .strip() indebido -- "ethusdt" por sí
        # solo no lo haría al carecer de espacios.
        ev = _observed_closed(symbol=" BTCUSDT ")
        assert ev.symbol == " BTCUSDT "

    def test_exchange_order_id_with_padding_preserved_literal(self):
        ev = _observed_closed(exchange_order_id=" BYBIT-XORDER-77 ")
        assert ev.exchange_order_id == " BYBIT-XORDER-77 "

    def test_reject_reason_with_padding_preserved_verbatim(self):
        ev = _observed_closed(
            remote_status="rejected", quantity=Decimal("1"), filled_quantity=Decimal("0"),
            filled_value=Decimal("0"), average_price=None, reject_reason=" EC_InsufficientBalance ",
        )
        assert ev.reject_reason == " EC_InsufficientBalance "

    def test_filled_value_is_not_derived_from_quantity_times_price(self):
        # Precondición explícita del ataque: ni filled_quantity*price ni
        # filled_quantity*average_price coinciden con filled_value -- una
        # mutación que RECALCULARA filled_value a partir de otros campos
        # (en vez de preservar el valor recibido) produciría un valor
        # distinto del literal, detectable por esta aserción.
        quantity, price, average_price = Decimal("1"), Decimal("100"), Decimal("99.5")
        filled_quantity, filled_value = Decimal("0.4"), Decimal("39.73")
        assert filled_quantity * price != filled_value
        assert filled_quantity * average_price != filled_value
        ev = _observed_closed(
            remote_status="cancelled", quantity=quantity, filled_quantity=filled_quantity,
            filled_value=filled_value, price=price, average_price=average_price,
        )
        assert ev.filled_value == Decimal("39.73")

    def test_remote_updated_time_ms_preserved_when_different_from_created(self):
        ev = _observed_closed(remote_created_time_ms=900, remote_updated_time_ms=1950)
        assert ev.remote_updated_time_ms == 1950
        assert ev.remote_created_time_ms == 900


# ---------------------------------------------------------------------------
# Clasificación de Decimal.normalize() (Hito 3.94, corrección post-
# auditoría, respuesta a IMPORTANTE-1/§7 y §19): equivalente, no hueco de
# cobertura. ADR-012 exige preservación por VALOR de los campos Decimal
# (nunca literal de representación textual, a diferencia de symbol/side,
# que sí son literales de string -- ADR-005 Decisión 3). `Decimal.__eq__`
# compara por valor, no por representación (`Decimal("1.3700") ==
# Decimal("1.37")` es `True`), y ninguna invariante de este contrato
# compara `str()`/exponente de un campo Decimal. Por tanto una mutación
# que aplicara `.normalize()` a `quantity` (o cualquier otro campo
# Decimal) preserva el valor exacto y es EQUIVALENTE -- mismo patrón que
# N35b en el Economic Comparator de Hito 3.91. No se escribe un test
# artificial que exija representación textual específica: ADR-012 no lo
# exige y hacerlo violaría la propia guía de esta corrección (no inventar
# garantías nuevas para matar redundancia).
# ---------------------------------------------------------------------------

class TestOrderObservedClosedDecimalNormalizeIsEquivalent:
    def test_normalize_does_not_change_value_equality(self):
        assert Decimal("1.3700").normalize() == Decimal("1.3700")
        assert Decimal("1.3700").normalize() == Decimal("1.37")

    def test_contract_does_not_compare_decimal_string_representation_anywhere(self):
        # Confirma la premisa de la equivalencia: ninguna invariante de
        # OrderObservedClosed invoca str()/as_tuple() sobre un campo
        # Decimal -- las comparaciones cruzadas son aritméticas (==, <, >).
        source = inspect.getsource(OrderObservedClosed)
        for banned in ("str(self.quantity", "str(self.filled_quantity", "str(self.filled_value",
                       "str(self.price", "str(self.average_price", ".as_tuple("):
            assert banned not in source


# ---------------------------------------------------------------------------
# Sensibilidad a mayúsculas/espacios de remote_status (Hito 3.94,
# corrección post-auditoría, IMPORTANTE-2). El contrato compara contra
# `_VALID_CLOSED_ORDER_STATUSES` con `in`, sin normalización -- ninguna
# variante de casing/espaciado debe pasar.
# ---------------------------------------------------------------------------

class TestOrderObservedClosedStatusCaseSensitivity:
    @pytest.mark.parametrize("bad_status", [
        "Filled", "FILLED", " filled", "filled ",
        "Cancelled", "CANCELLED", " cancelled",
        "Rejected", "REJECTED", " rejected",
    ])
    def test_rejects_any_casing_or_spacing_variant(self, bad_status):
        with pytest.raises(ValueError):
            _observed_closed(remote_status=bad_status)

    @pytest.mark.parametrize("good_status,kwargs", [
        ("filled", dict(quantity=Decimal("1"), filled_quantity=Decimal("1"),
                        filled_value=Decimal("100"), average_price=Decimal("100"))),
        ("cancelled", dict(quantity=Decimal("1"), filled_quantity=Decimal("0"),
                            filled_value=Decimal("0"), average_price=None)),
        ("rejected", dict(quantity=Decimal("1"), filled_quantity=Decimal("0"),
                           filled_value=Decimal("0"), average_price=None)),
    ])
    def test_accepts_only_the_exact_lowercase_token(self, good_status, kwargs):
        ev = _observed_closed(remote_status=good_status, **kwargs)
        assert ev.remote_status == good_status


# ---------------------------------------------------------------------------
# Envelope real (Hito 3.94, corrección post-auditoría, IMPORTANTE-3). La
# auditoría demostró EXPRESABLE una mutación que excluye este tipo del
# envelope (el aceptado hasta ahora era un enunciado sin test que lo
# probara) -- se agrega aquí, mismo patrón que
# TestOrderIdentityReportedDuplicateByExchange.test_works_as_envelope_payload
# de Hito 3.89.
# ---------------------------------------------------------------------------

class TestOrderObservedClosedEnvelope:
    def test_works_as_envelope_payload(self):
        payload = _observed_closed()
        event = _envelope(payload=payload)
        assert isinstance(event.payload, OrderObservedClosed)
        assert event.payload is payload

    def test_envelope_still_has_exactly_four_fields_with_this_payload(self):
        event = _envelope(payload=_observed_closed())
        names = {f.name for f in dataclasses.fields(event)}
        assert names == {"event_id", "execution_account_id", "occurred_at_ms", "payload"}


# ---------------------------------------------------------------------------
# Cotas de quantity (Hito 3.94, corrección post-auditoría, MENOR-1).
# ---------------------------------------------------------------------------

class TestOrderObservedClosedQuantityBounds:
    # filled_quantity=0/remote_status="rejected" evita que la cruzada
    # `filled_quantity > quantity` dispare antes -- aísla causalmente la
    # guarda de positividad de `quantity` (mata M6: positive -> non-negative
    # sobrevive si `quantity=0` colisiona con otra invariante primero).
    def test_quantity_rejects_zero(self):
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="rejected", quantity=Decimal("0"), filled_quantity=Decimal("0"),
                filled_value=Decimal("0"), average_price=None,
            )

    def test_quantity_rejects_negative(self):
        with pytest.raises(ValueError):
            _observed_closed(
                remote_status="rejected", quantity=Decimal("-1"), filled_quantity=Decimal("0"),
                filled_value=Decimal("0"), average_price=None,
            )


# ---------------------------------------------------------------------------
# Superficie exacta de atributos públicos (Hito 3.94, corrección post-
# auditoría, MENOR-2). El test previo de atributos prohibidos
# (`test_no_forbidden_attributes_on_real_instance`) usa una lista negra
# que crecería indefinidamente; éste usa una lista blanca derivada de
# `dataclasses.fields()` y la compara contra TODO atributo público no
# invocable de una instancia real -- una `@property` nueva (calculada, no
# almacenada en `__dict__`, por lo que `vars()` no la vería) SÍ aparece en
# `dir()` y no es invocable al acceder a ella, así que queda atrapada.
# ---------------------------------------------------------------------------

class TestOrderObservedClosedPublicAttributeSurface:
    def test_public_non_callable_attributes_equal_exactly_the_declared_fields(self):
        ev = _observed_closed()
        expected = {f.name for f in dataclasses.fields(OrderObservedClosed)}
        actual = {
            name for name in dir(ev)
            if not name.startswith("_") and not callable(getattr(ev, name))
        }
        assert actual == expected


# ---------------------------------------------------------------------------
# Partición de contenido estable vs. metadato de observación (ADR-012,
# "Corrección post-reauditoría de D12"). Fija declarativamente, del lado
# del test, la partición 16+1 que el futuro Writer usará para idempotencia
# -- protege contra reabrir accidentalmente el defecto de la reauditoría
# de Hito 3.85 (D12 original no distinguía server_time_ms del resto).
# ---------------------------------------------------------------------------

_OBSERVED_CLOSED_STABLE_CONTENT_FIELDS = frozenset({
    "execution_order_id", "exchange_order_id", "symbol", "side", "order_type",
    "quantity", "filled_quantity", "filled_value", "remote_status", "reduce_only",
    "remote_created_time_ms", "remote_updated_time_ms", "price", "average_price",
    "cancel_type", "reject_reason",
})
_OBSERVED_CLOSED_OBSERVATION_METADATA_FIELDS = frozenset({"server_time_ms"})


class TestOrderObservedClosedContentPartition:
    def test_stable_content_has_exactly_sixteen_fields(self):
        assert len(_OBSERVED_CLOSED_STABLE_CONTENT_FIELDS) == 16

    def test_observation_metadata_has_exactly_one_field(self):
        assert len(_OBSERVED_CLOSED_OBSERVATION_METADATA_FIELDS) == 1

    def test_partition_covers_every_field_without_overlap_or_gap(self):
        all_fields = {f.name for f in dataclasses.fields(OrderObservedClosed)}
        union = _OBSERVED_CLOSED_STABLE_CONTENT_FIELDS | _OBSERVED_CLOSED_OBSERVATION_METADATA_FIELDS
        assert union == all_fields
        assert not (
            _OBSERVED_CLOSED_STABLE_CONTENT_FIELDS & _OBSERVED_CLOSED_OBSERVATION_METADATA_FIELDS
        )

    def test_two_observations_with_same_stable_content_differ_only_in_server_time_ms(self):
        # Simula dos observaciones legítimas del mismo hecho remoto cerrado
        # -- distintas consultas, mismo hecho. El Writer (no implementado
        # aquí) las trataría como idempotentes.
        first = _observed_closed(server_time_ms=1000)
        second = _observed_closed(server_time_ms=2000)
        assert first != second  # payload completo difiere (dataclass eq incluye todo)
        stable_first = {f: getattr(first, f) for f in _OBSERVED_CLOSED_STABLE_CONTENT_FIELDS}
        stable_second = {f: getattr(second, f) for f in _OBSERVED_CLOSED_STABLE_CONTENT_FIELDS}
        assert stable_first == stable_second

    def test_server_time_ms_is_received_never_generated(self):
        # No hay reloj, no hay default -- confirmado también por
        # TestPurity.test_no_clock_or_environment_access más abajo; aquí
        # se confirma específicamente que server_time_ms es un campo
        # posicional/keyword obligatorio, no un default_factory.
        field = next(f for f in dataclasses.fields(OrderObservedClosed) if f.name == "server_time_ms")
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING


# ---------------------------------------------------------------------------
# Export a nivel de paquete (Hito 3.89 §16/§21 M11) -- ningún tipo de
# evento anterior tenía cobertura explícita de su presencia en
# execution_gateway.__all__/namespace; se agrega aquí sólo para el tipo
# nuevo, mismo patrón `TestImport` usado en 3.86/3.88.
# ---------------------------------------------------------------------------

class TestPackageExport:
    def test_importable_from_package(self):
        assert execution_gateway.OrderIdentityReportedDuplicateByExchange is (
            OrderIdentityReportedDuplicateByExchange
        )

    def test_in_all(self):
        assert "OrderIdentityReportedDuplicateByExchange" in execution_gateway.__all__

    def test_observed_closed_importable_from_package(self):
        assert execution_gateway.OrderObservedClosed is OrderObservedClosed

    def test_observed_closed_in_all(self):
        assert "OrderObservedClosed" in execution_gateway.__all__


# ---------------------------------------------------------------------------
# OrderIdentityReportedDuplicateByExchange (Hito 3.89, ADR-013 Opción B,
# séptimo tipo de evento -- REMOTE, NO TERMINAL, representa Bybit
# retCode 110072 sobre una ExecutionOrderId reintentada).
# ---------------------------------------------------------------------------

class TestOrderIdentityReportedDuplicateByExchange:
    # A. construcción válida
    def test_constructs_validly(self):
        ev = _duplicate()
        assert ev.ret_code == 110072
        assert ev.ret_msg == "OrderLinkedID is duplicate"
        assert ev.server_time_ms == 1000

    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _duplicate().ret_code = 1

    # B. preserva ExecutionOrderId (identidad de objeto, no sólo equality)
    def test_preserves_execution_order_id_by_identity(self):
        marker = ExecutionOrderId(value="ord_" + "c" * 32)
        ev = _duplicate(execution_order_id=marker)
        assert ev.execution_order_id is marker

    # C. ret_code exactamente 110072
    def test_ret_code_must_be_exactly_110072(self):
        assert _duplicate(ret_code=110072).ret_code == 110072

    # D. rechaza otros ints
    @pytest.mark.parametrize("ret_code", [110071, 110073, 0, -1, 10001, 1])
    def test_ret_code_rejects_other_ints(self, ret_code):
        with pytest.raises(ValueError):
            _duplicate(ret_code=ret_code)

    # E. rechaza bool (True/False no deben colarse como int -- 110072 es
    # un valor concreto, no un chequeo de truthiness)
    @pytest.mark.parametrize("ret_code", [True, False])
    def test_ret_code_rejects_bool(self, ret_code):
        with pytest.raises(TypeError):
            _duplicate(ret_code=ret_code)

    # F. rechaza str "110072"
    def test_ret_code_rejects_string(self):
        with pytest.raises(TypeError):
            _duplicate(ret_code="110072")

    # G. rechaza float 110072.0
    def test_ret_code_rejects_float(self):
        with pytest.raises(TypeError):
            _duplicate(ret_code=110072.0)

    # H. ret_msg válido (preservado verbatim, sin normalizar)
    def test_ret_msg_preserved_verbatim(self):
        ev = _duplicate(ret_msg="  OrderLinkedID is duplicate  ")
        assert ev.ret_msg == "  OrderLinkedID is duplicate  "

    def test_ret_msg_not_required_to_be_the_literal_bybit_string(self):
        # El código numérico es la semántica estable congelada por
        # ADR-013 -- el texto remoto puede variar entre versiones de la
        # API de Bybit y no se exige literal.
        ev = _duplicate(ret_msg="duplicate order link id detected")
        assert ev.ret_msg == "duplicate order link id detected"

    # I. ret_msg wrong type
    @pytest.mark.parametrize("bad", [None, 1, 1.5, True, [], {}, b"x", object()])
    def test_ret_msg_rejects_non_str(self, bad):
        with pytest.raises(TypeError):
            _duplicate(ret_msg=bad)

    def test_ret_msg_rejects_empty(self):
        with pytest.raises(ValueError):
            _duplicate(ret_msg="")

    def test_ret_msg_rejects_whitespace_only(self):
        with pytest.raises(ValueError):
            _duplicate(ret_msg="   ")

    # J. server_time_ms válido
    def test_server_time_ms_preserved(self):
        assert _duplicate(server_time_ms=42).server_time_ms == 42

    def test_server_time_ms_can_be_zero(self):
        assert _duplicate(server_time_ms=0).server_time_ms == 0

    # K. server_time_ms wrong type
    @pytest.mark.parametrize("bad", [None, "1000", 1.5, [], {}, object()])
    def test_server_time_ms_rejects_non_int(self, bad):
        with pytest.raises(TypeError):
            _duplicate(server_time_ms=bad)

    # L. server_time_ms límites/invariantes -- mismo patrón que
    # OrderAcceptedByExchange/OrderRejectedByExchange/OrderObservedOpen
    # (_require_non_negative_int: bool rechazado, negativo rechazado).
    def test_server_time_ms_rejects_bool(self):
        with pytest.raises(TypeError):
            _duplicate(server_time_ms=True)

    def test_server_time_ms_rejects_negative(self):
        with pytest.raises(ValueError):
            _duplicate(server_time_ms=-1)

    # M/N/O. Authority estructural: REMOTE, nunca LOCAL ni OBSERVED
    def test_is_remote_fact(self):
        assert isinstance(_duplicate(), RemoteFact)

    def test_is_not_local_fact(self):
        assert not isinstance(_duplicate(), LocalFact)

    def test_is_not_observed_fact(self):
        assert not isinstance(_duplicate(), ObservedFact)

    def test_authority_is_structural_not_configurable(self):
        sig = inspect.signature(OrderIdentityReportedDuplicateByExchange.__init__)
        assert "authority" not in sig.parameters

    # P/Q. payload funciona en el envelope existente, sin ampliarlo
    def test_works_as_envelope_payload(self):
        event = _envelope(payload=_duplicate())
        assert isinstance(event.payload, OrderIdentityReportedDuplicateByExchange)

    def test_envelope_still_has_exactly_four_fields_with_this_payload(self):
        event = _envelope(payload=_duplicate())
        names = {f.name for f in dataclasses.fields(event)}
        assert names == {"event_id", "execution_account_id", "occurred_at_ms", "payload"}

    # R. no exchange_order_id (estructuralmente ausente, no opcional)
    def test_no_exchange_order_id_field(self):
        names = {f.name for f in dataclasses.fields(OrderIdentityReportedDuplicateByExchange)}
        assert "exchange_order_id" not in names

    def test_no_exchange_order_id_attribute_on_real_instance(self):
        # Auditoría adversarial final 3.89, hallazgo MENOR (N21):
        # `dataclasses.fields()` inspecciona sólo los campos declarados de
        # la clase -- una `@property` de sólo lectura llamada
        # `exchange_order_id` que siempre devolviera `None` pasaría
        # inadvertida por `test_no_exchange_order_id_field` de arriba,
        # aunque `hasattr(instancia, "exchange_order_id")` sea `True` para
        # ese mutante. Aquí se construye una instancia REAL y se
        # inspecciona el OBJETO, no la clase -- `hasattr` sí discrimina
        # una property. ADR-013, Resolución del STOP punto (1): "sin
        # `exchange_order_id` (Bybit no lo entrega en esta respuesta; su
        # ausencia es estructural, no opcional)". Se extiende, en el mismo
        # test y sin parametrización adicional, al resto de atributos que
        # ADR-013 prohíbe explícitamente para este tipo (bot ownership,
        # economía, autoridad configurable, vocabulario de terminalidad) --
        # ya cubiertos por separado a nivel de `dataclasses.fields()`, pero
        # nunca antes a nivel de instancia real.
        ev = _duplicate()
        for forbidden in (
            "exchange_order_id", "bot_id", "execution_bot_id", "symbol", "side",
            "order_type", "quantity", "price", "reduce_only", "authority",
            "terminal", "is_terminal", "status",
        ):
            assert not hasattr(ev, forbidden), forbidden

    # S. no economics
    def test_no_economic_fields(self):
        names = {f.name for f in dataclasses.fields(OrderIdentityReportedDuplicateByExchange)}
        for forbidden in ("symbol", "side", "order_type", "quantity", "price", "reduce_only"):
            assert forbidden not in names

    # T. no bot_id
    def test_no_bot_id_field(self):
        names = {f.name for f in dataclasses.fields(OrderIdentityReportedDuplicateByExchange)}
        assert "execution_bot_id" not in names
        assert "bot_id" not in names

    # U. no credentials/raw response
    def test_no_credential_or_raw_response_fields(self):
        names = {f.name for f in dataclasses.fields(OrderIdentityReportedDuplicateByExchange)}
        for forbidden in (
            "api_key", "api_secret", "signature", "headers", "credential",
            "raw_response", "request_body", "body",
        ):
            assert not any(forbidden in n for n in names)

    # Exact field set -- mismo patrón que TestExactFieldSets para los
    # otros seis tipos.
    def test_exact_field_set(self):
        names = {f.name for f in dataclasses.fields(OrderIdentityReportedDuplicateByExchange)}
        assert names == {"execution_order_id", "ret_code", "ret_msg", "server_time_ms"}

    def test_payload_marker_is_never_used_as_a_concrete_event_type(self):
        assert type(_duplicate()) is not ExecutionLedgerEventPayload
        assert type(_duplicate()) not in (LocalFact, RemoteFact, ObservedFact)

    # No-terminalidad estructural (ADR-013 D5): el modelo hoy no tiene
    # ningún marcador/campo de terminalidad -- auditado antes de escribir
    # este test (Accepted/Rejected son terminales sólo por convención
    # documental, nunca por un campo o clase base compartida). No se crea
    # ninguna abstracción nueva aquí; sólo se confirma que este tipo no
    # hereda de los dos tipos REMOTE terminales existentes ni introduce
    # vocabulario de cierre.
    def test_does_not_inherit_from_accepted_or_rejected(self):
        assert not issubclass(OrderIdentityReportedDuplicateByExchange, OrderAcceptedByExchange)
        assert not issubclass(OrderIdentityReportedDuplicateByExchange, OrderRejectedByExchange)
        assert not issubclass(OrderAcceptedByExchange, OrderIdentityReportedDuplicateByExchange)
        assert not issubclass(OrderRejectedByExchange, OrderIdentityReportedDuplicateByExchange)

    def test_is_a_distinct_type_from_accepted_and_rejected(self):
        assert type(_duplicate()) is not OrderAcceptedByExchange
        assert type(_duplicate()) is not OrderRejectedByExchange

    def test_no_terminality_vocabulary_in_field_names(self):
        names = {f.name for f in dataclasses.fields(OrderIdentityReportedDuplicateByExchange)}
        for forbidden in ("terminal", "is_terminal", "closed", "final", "outcome"):
            assert not any(forbidden in n for n in names)

    def test_no_terminality_or_resolution_methods(self):
        for forbidden in (
            "mutate", "correct", "replace", "mark_resolved", "resolve",
            "close", "finalize", "terminate",
        ):
            assert not hasattr(OrderIdentityReportedDuplicateByExchange, forbidden)


# ---------------------------------------------------------------------------
# Coexistencia estructural con otros hechos (Hito 3.89 §18/§10): sólo
# construcción de objetos -- sin Projection, sin state machine. Si
# OrderObservedClosed todavía no existe, no se inventa aquí.
# ---------------------------------------------------------------------------

class TestCoexistenceWithOtherFacts:
    def test_attempted_unknown_and_duplicate_construct_for_the_same_order_id(self):
        attempt = _attempt(execution_order_id=_ORDER_ID)
        unknown = _unknown(execution_order_id=_ORDER_ID)
        duplicate = _duplicate(execution_order_id=_ORDER_ID)
        assert attempt.execution_order_id == unknown.execution_order_id == duplicate.execution_order_id
        # tres hechos distintos, ninguno sustituye a otro
        assert type(attempt) is not type(unknown) is not type(duplicate)
        assert len({type(attempt), type(unknown), type(duplicate)}) == 3

    def test_duplicate_does_not_mutate_or_invalidate_prior_unknown(self):
        unknown = _unknown(execution_order_id=_ORDER_ID)
        snapshot = repr(unknown)
        _duplicate(execution_order_id=_ORDER_ID)
        assert repr(unknown) == snapshot

    def test_duplicate_and_observed_open_coexist_for_the_same_order_id(self):
        # Caso (b) de ADR-013 D13: 110072 -> realtime FOUND New ->
        # ObservedOpen. Sólo se comprueba compatibilidad ESTRUCTURAL
        # (ambos se construyen sin excepción) -- ninguna orquestación,
        # ninguna Projection.
        duplicate = _duplicate(execution_order_id=_ORDER_ID)
        observed = _observed(execution_order_id=_ORDER_ID)
        assert duplicate.execution_order_id == observed.execution_order_id
        assert type(duplicate) is not type(observed)

    def test_two_facts_for_same_order_id_can_coexist_in_the_same_envelope_account(self):
        duplicate = _duplicate(execution_order_id=_ORDER_ID)
        observed = _observed(execution_order_id=_ORDER_ID)
        ev1 = _envelope(payload=duplicate, event_id="evt-dup")
        ev2 = _envelope(payload=observed, event_id="evt-obs")
        assert ev1.execution_account_id == ev2.execution_account_id
        assert ev1.event_id != ev2.event_id
        assert ev1.payload is duplicate
        assert ev2.payload is observed

    # ADR-012 D9: [Attempted, Unknown, ObservedClosed] -- Unknown no se
    # borra ni se transforma; ambos coexisten para la misma identidad.
    def test_unknown_and_observed_closed_coexist_for_the_same_order_id(self):
        unknown = _unknown(execution_order_id=_ORDER_ID)
        closed = _observed_closed(execution_order_id=_ORDER_ID)
        assert unknown.execution_order_id == closed.execution_order_id
        assert type(unknown) is not type(closed)

    def test_observed_closed_does_not_mutate_prior_unknown(self):
        unknown = _unknown(execution_order_id=_ORDER_ID)
        snapshot = repr(unknown)
        _observed_closed(execution_order_id=_ORDER_ID)
        assert repr(unknown) == snapshot

    # ADR-012 D10: [Attempted, ObservedClosed] sin Unknown -- caso crash,
    # representable sin inventar ningún hecho intermedio.
    def test_attempt_and_observed_closed_coexist_without_any_unknown(self):
        attempt = _attempt(execution_order_id=_ORDER_ID)
        closed = _observed_closed(execution_order_id=_ORDER_ID)
        assert attempt.execution_order_id == closed.execution_order_id
        assert type(attempt) is not type(closed)

    # ADR-012 D11: [Attempted, Accepted, ObservedClosed] -- ciclo normal,
    # ObservedClosed no es un evento de error.
    def test_accepted_and_observed_closed_coexist(self):
        accepted = _accepted(execution_order_id=_ORDER_ID)
        closed = _observed_closed(execution_order_id=_ORDER_ID)
        assert accepted.execution_order_id == closed.execution_order_id
        assert type(accepted) is not type(closed)

    # ADR-013 D13(a): [Attempted, Unknown, <110072>, ObservedClosed] --
    # los cuatro hechos coexisten sin contradicción estructural.
    def test_duplicate_and_observed_closed_coexist(self):
        duplicate = _duplicate(execution_order_id=_ORDER_ID)
        closed = _observed_closed(execution_order_id=_ORDER_ID)
        assert duplicate.execution_order_id == closed.execution_order_id
        assert type(duplicate) is not type(closed)

    def test_full_market_acceptance_case_sequence_constructs_without_contradiction(self):
        # ADR-012 D14a, el acceptance case principal: MARKET, ACK perdido,
        # llenada rápido -- [Attempted, Unknown, <110072>, ObservedClosed].
        # Sólo construcción de objetos -- sin Projection, sin state machine.
        attempt = _attempt(execution_order_id=_ORDER_ID, order_type="market", price=None)
        unknown = _unknown(execution_order_id=_ORDER_ID, reason="transport_failure")
        duplicate = _duplicate(execution_order_id=_ORDER_ID)
        closed = _observed_closed(
            execution_order_id=_ORDER_ID, order_type="market", price=None,
            remote_status="filled", quantity=Decimal("1"), filled_quantity=Decimal("1"),
            filled_value=Decimal("100"), average_price=Decimal("100"),
        )
        events = [attempt, unknown, duplicate, closed]
        assert all(e.execution_order_id == _ORDER_ID for e in events)
        assert len({type(e) for e in events}) == 4


# ---------------------------------------------------------------------------
# execution_order_id: type-safety sistemática y simétrica entre los seis
# tipos de evento order-scoped (cierre del hallazgo IMPORTANTE de la
# auditoría adversarial independiente post-3.83: OrderSubmissionOutcomeUnknown
# y OrderRejectedByExchange carecían de esta cobertura conductual, pese a
# que la producción ya validaba correctamente en las cinco clases -- hueco
# de cobertura, nunca un defecto de comportamiento, confirmado
# manualmente antes de escribir cualquier test nuevo). Extendido en el
# Hito 3.89 al séptimo tipo, OrderIdentityReportedDuplicateByExchange.
#
# Parametrizado por (builder, bad_value) para que un fallo señale sin
# ambigüedad CUÁL de los tipos dejó de validar -- nunca origen por
# inspección de fuente.
# ---------------------------------------------------------------------------

_EVENT_ORDER_ID_BUILDERS = {
    "OrderSubmissionAttempted": _attempt,
    "OrderSubmissionOutcomeUnknown": _unknown,
    "OrderAcceptedByExchange": _accepted,
    "OrderRejectedByExchange": _rejected,
    "OrderIdentityReportedDuplicateByExchange": _duplicate,
    "OrderObservedOpen": _observed,
    "OrderObservedClosed": _observed_closed,
}

_BAD_EXECUTION_ORDER_IDS = [None, "ord_" + "a" * 32, 123, True, 1.5, b"x", object()]


class TestExecutionOrderIdTypeSafetyAcrossAllEventTypes:
    @pytest.mark.parametrize("event_name", list(_EVENT_ORDER_ID_BUILDERS))
    @pytest.mark.parametrize("bad_value", _BAD_EXECUTION_ORDER_IDS,
                             ids=[repr(v) for v in _BAD_EXECUTION_ORDER_IDS])
    def test_rejects_non_execution_order_id_value(self, event_name, bad_value):
        builder = _EVENT_ORDER_ID_BUILDERS[event_name]
        with pytest.raises(TypeError):
            builder(execution_order_id=bad_value)

    @pytest.mark.parametrize("event_name", list(_EVENT_ORDER_ID_BUILDERS))
    def test_accepts_valid_execution_order_id_by_identity(self, event_name):
        builder = _EVENT_ORDER_ID_BUILDERS[event_name]
        marker = ExecutionOrderId(value="ord_" + "b" * 32)
        event = builder(execution_order_id=marker)
        # Preservación por identidad de objeto (`is`), no sólo equality --
        # confirma que el contrato no reconstruye ni copia el value object.
        assert event.execution_order_id is marker


# ---------------------------------------------------------------------------
# Autoridad -- estructural, no configurable
# ---------------------------------------------------------------------------

class TestAuthority:
    def test_attempted_is_local(self):
        assert isinstance(_attempt(), LocalFact)

    def test_unknown_is_local(self):
        assert isinstance(_unknown(), LocalFact)

    def test_accepted_is_remote(self):
        assert isinstance(_accepted(), RemoteFact)

    def test_rejected_is_remote(self):
        assert isinstance(_rejected(), RemoteFact)

    def test_duplicate_is_remote(self):
        assert isinstance(_duplicate(), RemoteFact)

    def test_observed_open_is_observed(self):
        assert isinstance(_observed(), ObservedFact)

    def test_observed_closed_is_observed(self):
        assert isinstance(_observed_closed(), ObservedFact)
        assert not isinstance(_observed_closed(), RemoteFact)
        assert not isinstance(_observed_closed(), LocalFact)

    def test_authorities_are_mutually_exclusive_marker_hierarchies(self):
        events = [_attempt(), _unknown(), _accepted(), _rejected(), _duplicate(), _observed(), _observed_closed()]
        for event in events:
            markers = [isinstance(event, m) for m in (LocalFact, RemoteFact, ObservedFact)]
            assert sum(markers) == 1

    def test_no_payload_class_exposes_a_settable_authority_field(self):
        for cls in (
            OrderSubmissionAttempted, OrderSubmissionOutcomeUnknown, OrderAcceptedByExchange,
            OrderRejectedByExchange, OrderIdentityReportedDuplicateByExchange, OrderObservedOpen,
            OrderObservedClosed,
        ):
            names = {f.name for f in dataclasses.fields(cls)}
            assert "authority" not in names

    def test_payload_marker_is_never_used_as_a_concrete_event_type(self):
        # Mismo patrón que `Divergence` (ADR-005, Decisión 7): la clase
        # marcadora es documentalmente "nunca instanciada directamente",
        # no forzado en runtime -- confirmamos que ningún tipo concreto
        # ES la propia clase marcadora (isinstance exacto, no subclase).
        for event in (_attempt(), _unknown(), _accepted(), _rejected(), _duplicate(), _observed(), _observed_closed()):
            assert type(event) is not ExecutionLedgerEventPayload
            assert type(event) not in (LocalFact, RemoteFact, ObservedFact)


# ---------------------------------------------------------------------------
# Uncertainty: Attempted + Unknown coexisten como hechos distintos
# ---------------------------------------------------------------------------

class TestUncertaintyRepresentation:
    def test_attempt_and_unknown_are_two_distinct_facts_same_order(self):
        attempt = _attempt()
        unknown = _unknown(execution_order_id=attempt.execution_order_id)
        assert attempt != unknown
        assert attempt.execution_order_id == unknown.execution_order_id
        assert type(attempt) is not type(unknown)

    def test_attempt_is_not_mutated_by_constructing_unknown(self):
        attempt = _attempt()
        snapshot = repr(attempt)
        _unknown(execution_order_id=attempt.execution_order_id)
        assert repr(attempt) == snapshot

    def test_no_mutate_or_correct_or_resolve_methods_exist(self):
        for cls in (
            OrderSubmissionAttempted, OrderSubmissionOutcomeUnknown, OrderAcceptedByExchange,
            OrderRejectedByExchange, OrderIdentityReportedDuplicateByExchange, OrderObservedOpen,
            OrderObservedClosed,
            ExecutionLedgerEvent,
        ):
            for forbidden in ("mutate", "correct", "replace", "mark_resolved", "resolve"):
                assert not hasattr(cls, forbidden)


# ---------------------------------------------------------------------------
# No dedup económico
# ---------------------------------------------------------------------------

class TestNoEconomicDeduplication:
    def test_two_attempts_same_economics_different_order_id_are_distinct(self):
        a1 = _attempt(execution_order_id=_ORDER_ID)
        a2 = _attempt(execution_order_id=_ORDER_ID_2)
        assert a1 != a2
        assert a1.execution_order_id != a2.execution_order_id
        # mismos symbol/side/order_type/quantity/price
        assert a1.symbol == a2.symbol
        assert a1.side == a2.side
        assert a1.quantity == a2.quantity
        assert a1.price == a2.price


# ---------------------------------------------------------------------------
# Decimal, no float
# ---------------------------------------------------------------------------

class TestDecimalUsage:
    def test_attempt_quantity_rejects_float(self):
        with pytest.raises(TypeError):
            _attempt(quantity=1.5)

    def test_observed_quantity_rejects_float(self):
        with pytest.raises(TypeError):
            _observed(quantity=1.5)

    def test_observed_filled_quantity_rejects_float(self):
        with pytest.raises(TypeError):
            _observed(filled_quantity=0.5)

    def test_price_rejects_float_when_present(self):
        with pytest.raises(TypeError):
            _attempt(price=100.5)

    def test_observed_closed_quantity_rejects_float(self):
        with pytest.raises(TypeError):
            _observed_closed(quantity=1.5)

    def test_observed_closed_filled_quantity_rejects_float(self):
        with pytest.raises(TypeError):
            _observed_closed(filled_quantity=0.5)

    def test_observed_closed_filled_value_rejects_float(self):
        with pytest.raises(TypeError):
            _observed_closed(filled_value=50.0)


# ---------------------------------------------------------------------------
# Conjunto exacto de campos -- protege contra la adición silenciosa de un
# campo nuevo (p. ej. un campo optativo sin usar que nadie valida ni prueba
# pasaría inadvertido si sólo se comprueban campos individuales).
# ---------------------------------------------------------------------------

class TestExactFieldSets:
    def test_attempted_fields(self):
        names = {f.name for f in dataclasses.fields(OrderSubmissionAttempted)}
        assert names == {
            "execution_order_id", "symbol", "side", "order_type", "quantity",
            "price", "execution_bot_id",
        }

    def test_unknown_fields(self):
        names = {f.name for f in dataclasses.fields(OrderSubmissionOutcomeUnknown)}
        assert names == {"execution_order_id", "reason"}

    def test_accepted_fields(self):
        names = {f.name for f in dataclasses.fields(OrderAcceptedByExchange)}
        assert names == {"execution_order_id", "exchange_order_id", "server_time_ms"}

    def test_rejected_fields(self):
        names = {f.name for f in dataclasses.fields(OrderRejectedByExchange)}
        assert names == {"execution_order_id", "ret_code", "ret_msg", "server_time_ms"}

    def test_duplicate_fields(self):
        names = {f.name for f in dataclasses.fields(OrderIdentityReportedDuplicateByExchange)}
        assert names == {"execution_order_id", "ret_code", "ret_msg", "server_time_ms"}

    def test_observed_open_fields(self):
        names = {f.name for f in dataclasses.fields(OrderObservedOpen)}
        assert names == {
            "execution_order_id", "exchange_order_id", "symbol", "side", "order_type",
            "quantity", "filled_quantity", "status", "reduce_only", "server_time_ms", "price",
        }

    def test_observed_closed_fields(self):
        names = {f.name for f in dataclasses.fields(OrderObservedClosed)}
        assert names == {
            "execution_order_id", "exchange_order_id", "symbol", "side", "order_type",
            "quantity", "filled_quantity", "filled_value", "remote_status", "reduce_only",
            "server_time_ms", "remote_created_time_ms", "remote_updated_time_ms", "price",
            "average_price", "cancel_type", "reject_reason",
        }

    def test_envelope_fields(self):
        names = {f.name for f in dataclasses.fields(ExecutionLedgerEvent)}
        assert names == {"event_id", "execution_account_id", "occurred_at_ms", "payload"}

    def test_bot_id_fields(self):
        assert {f.name for f in dataclasses.fields(ExecutionBotId)} == {"value"}

    def test_event_id_fields(self):
        assert {f.name for f in dataclasses.fields(ExecutionLedgerEventId)} == {"value"}


# ---------------------------------------------------------------------------
# Pureza
# ---------------------------------------------------------------------------

class TestPurity:
    def _imports(self):
        tree = ast.parse(inspect.getsource(_events))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module)
        return names

    def test_imports_only_dataclasses_decimal_and_own_identities(self):
        assert self._imports() == {
            "dataclasses",
            "decimal",
            "execution_gateway.execution_identity_contracts",
        }

    def test_no_bybit_or_infrastructure_vocabulary(self):
        source = inspect.getsource(_events)
        tree = ast.parse(source)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        for forbidden in ("urlopen", "environ", "getenv", "urllib", "requests", "socket"):
            assert forbidden not in names

    def test_no_repair_vocabulary(self):
        source = inspect.getsource(_events)
        tree = ast.parse(source)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        for forbidden in ("should_retry", "should_cancel", "repair_action", "recommended_action"):
            assert forbidden not in names

    def test_no_credential_shaped_fields_anywhere(self):
        for cls in (
            OrderSubmissionAttempted, OrderSubmissionOutcomeUnknown, OrderAcceptedByExchange,
            OrderRejectedByExchange, OrderIdentityReportedDuplicateByExchange, OrderObservedOpen,
            OrderObservedClosed,
            ExecutionLedgerEvent,
        ):
            names = {f.name for f in dataclasses.fields(cls)}
            for forbidden in ("api_key", "api_secret", "signature", "headers", "credential"):
                assert not any(forbidden in n for n in names)

    def test_no_mutable_dict_or_list_fields(self):
        for cls in (
            OrderSubmissionAttempted, OrderSubmissionOutcomeUnknown, OrderAcceptedByExchange,
            OrderRejectedByExchange, OrderIdentityReportedDuplicateByExchange, OrderObservedOpen,
            OrderObservedClosed,
            ExecutionLedgerEvent,
        ):
            for field in dataclasses.fields(cls):
                assert field.type not in ("dict", "list")

    def test_all_payload_and_envelope_classes_are_frozen_dataclasses(self):
        for cls in (
            OrderSubmissionAttempted, OrderSubmissionOutcomeUnknown, OrderAcceptedByExchange,
            OrderRejectedByExchange, OrderIdentityReportedDuplicateByExchange, OrderObservedOpen,
            OrderObservedClosed,
            ExecutionLedgerEvent,
        ):
            assert dataclasses.is_dataclass(cls)
            assert cls.__dataclass_params__.frozen

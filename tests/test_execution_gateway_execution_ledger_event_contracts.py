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
        # Exactamente 6 tipos concretos (5 de ADR-010/Hito 3.83 + el
        # séptimo tipo de ADR-013/Hito 3.89, OrderIdentityReportedDuplicate
        # ByExchange) + el marcador base + los 3 marcadores de autoridad =
        # 10; ninguno adicional para huérfanas.
        concrete_event_types = event_type_names - {
            "ExecutionLedgerEventPayload", "LocalFact", "RemoteFact", "ObservedFact",
        }
        assert len(concrete_event_types) == 6

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

    def test_authorities_are_mutually_exclusive_marker_hierarchies(self):
        events = [_attempt(), _unknown(), _accepted(), _rejected(), _duplicate(), _observed()]
        for event in events:
            markers = [isinstance(event, m) for m in (LocalFact, RemoteFact, ObservedFact)]
            assert sum(markers) == 1

    def test_no_payload_class_exposes_a_settable_authority_field(self):
        for cls in (
            OrderSubmissionAttempted, OrderSubmissionOutcomeUnknown, OrderAcceptedByExchange,
            OrderRejectedByExchange, OrderIdentityReportedDuplicateByExchange, OrderObservedOpen,
        ):
            names = {f.name for f in dataclasses.fields(cls)}
            assert "authority" not in names

    def test_payload_marker_is_never_used_as_a_concrete_event_type(self):
        # Mismo patrón que `Divergence` (ADR-005, Decisión 7): la clase
        # marcadora es documentalmente "nunca instanciada directamente",
        # no forzado en runtime -- confirmamos que ningún tipo concreto
        # ES la propia clase marcadora (isinstance exacto, no subclase).
        for event in (_attempt(), _unknown(), _accepted(), _rejected(), _duplicate(), _observed()):
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
            ExecutionLedgerEvent,
        ):
            names = {f.name for f in dataclasses.fields(cls)}
            for forbidden in ("api_key", "api_secret", "signature", "headers", "credential"):
                assert not any(forbidden in n for n in names)

    def test_no_mutable_dict_or_list_fields(self):
        for cls in (
            OrderSubmissionAttempted, OrderSubmissionOutcomeUnknown, OrderAcceptedByExchange,
            OrderRejectedByExchange, OrderIdentityReportedDuplicateByExchange, OrderObservedOpen,
            ExecutionLedgerEvent,
        ):
            for field in dataclasses.fields(cls):
                assert field.type not in ("dict", "list")

    def test_all_payload_and_envelope_classes_are_frozen_dataclasses(self):
        for cls in (
            OrderSubmissionAttempted, OrderSubmissionOutcomeUnknown, OrderAcceptedByExchange,
            OrderRejectedByExchange, OrderIdentityReportedDuplicateByExchange, OrderObservedOpen,
            ExecutionLedgerEvent,
        ):
            assert dataclasses.is_dataclass(cls)
            assert cls.__dataclass_params__.frozen

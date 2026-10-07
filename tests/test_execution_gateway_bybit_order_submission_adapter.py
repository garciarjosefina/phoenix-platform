import ast
import http.client
import inspect
import json
import socket
import urllib.error

import pytest

import execution_gateway
import execution_gateway.bybit_order_submission_adapter as _module
from execution_gateway.bybit_authenticator_factory import create_bybit_authenticator
from execution_gateway.bybit_create_order_payload_builder import BybitCreateOrderPayloadBuilder
from execution_gateway.bybit_demo_execution_gateway_factory import create_bybit_demo_execution_gateway
from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor
from execution_gateway.bybit_endpoints import BYBIT_CREATE_ORDER_ENDPOINT
from execution_gateway.bybit_header_builder_factory import create_bybit_header_builder
from execution_gateway.bybit_order_submission_adapter import BybitOrderSubmissionAdapter
from execution_gateway.bybit_order_submission_response_interpreter import (
    BybitOrderSubmissionResponseInterpreter,
)
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import create_bybit_private_request_sender
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.contracts import ExecutionRequest
from execution_gateway.credentials import BybitDemoCredentials
from execution_gateway.execution_request_not_supported_error import ExecutionRequestNotSupportedError
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.json_serializer_factory import create_json_serializer
from execution_gateway.order_submission_outcome_contracts import (
    OrderSubmissionOutcome,
    SubmissionAccepted,
    SubmissionIdentityDuplicate,
    SubmissionOutcomeUnknown,
    SubmissionRejected,
)
from execution_gateway.order_submission_port import OrderSubmissionPort

_LINK = "ord_" + "a" * 32
_REMOTE = "bybit-remote-9f3"
_AUTH_TS = 1_111_111_111_111  # timestamp de AUTENTICACIÓN: debe ser distinto del `time` del response
_SERVER_TIME = 1_700_000_000_123


def _request(**overrides):
    kw = dict(order_id=_LINK, symbol="BTCUSDT", side="buy", order_type="market", quantity=0.001)
    kw.update(overrides)
    return ExecutionRequest(**kw)


def _wire(*, ret_code=0, ret_msg="OK", result="default", time=_SERVER_TIME, link=_LINK, remote=_REMOTE):
    if result == "default":
        result = {"orderId": remote, "orderLinkId": link}
    return json.dumps({"retCode": ret_code, "retMsg": ret_msg, "result": result, "retExtInfo": {}, "time": time})


def _response(*, ret_code=0, ret_msg="OK", result="default", time_ms=_SERVER_TIME, link=_LINK, remote=_REMOTE):
    if result == "default":
        result = {"orderId": remote, "orderLinkId": link}
    return BybitResponse(ret_code=ret_code, ret_msg=ret_msg, result=result, ret_ext_info={}, time_ms=time_ms)


# ---------------------------------------------------------------------------
# Dobles -- sólo en la frontera de infraestructura
# ---------------------------------------------------------------------------

class _SpyExecutor(BybitEndpointExecutor):
    """Sustituye al endpoint executor (frontera de red). `behaviors` es la
    lista de resultados por llamada: un `BybitResponse` se devuelve, una
    excepción se lanza. Una llamada de más es un `AssertionError`."""

    def __init__(self, *behaviors):
        self._behaviors = list(behaviors)
        self.calls = []

    def execute(self, *, endpoint, payload):
        self.calls.append({"endpoint": endpoint, "payload": dict(payload)})
        if not self._behaviors:
            raise AssertionError("unexpected extra remote call")
        behavior = self._behaviors.pop(0)
        if isinstance(behavior, BaseException):
            raise behavior
        return behavior


class _FakeClock:
    def now_ms(self):
        return _AUTH_TS


class _FakeSigner:
    def sign(self, *, secret, message):
        return "deterministic-signature"


class _ScriptedTransport:
    """Sustituye sólo `HttpTransport.post`. Cada llamada consume un
    comportamiento: un `str` es el cuerpo de la respuesta; una excepción se
    lanza."""

    def __init__(self, *behaviors):
        self._behaviors = list(behaviors)
        self.calls = []

    def post(self, *, url, headers, body, timeout_seconds):
        self.calls.append({"url": url, "headers": dict(headers), "body": body, "timeout": timeout_seconds})
        if not self._behaviors:
            raise AssertionError("unexpected extra remote call")
        behavior = self._behaviors.pop(0)
        if isinstance(behavior, BaseException):
            raise behavior
        return behavior


def _private_api(transport):
    serializer = create_json_serializer()
    authenticator = create_bybit_authenticator(
        credentials=BybitDemoCredentials(api_key="test-key", api_secret="test-secret"),
        clock=_FakeClock(), signer=_FakeSigner(), recv_window_ms=5000,
    )
    request_builder = create_bybit_request_builder(
        serializer=serializer, authenticator=authenticator, header_builder=create_bybit_header_builder(),
    )
    sender = create_bybit_private_request_sender(
        request_builder=request_builder,
        request_executor=create_http_request_executor(transport=transport, timeout_seconds=10.0),
    )
    return create_bybit_private_api(
        sender=sender, response_parser=create_bybit_response_parser(serializer=serializer),
    )


def _endpoint_executor(private_api):
    return BybitEndpointExecutor(
        url_builder=BybitUrlBuilder(base_url="https://api-demo.bybit.com"), private_api=private_api,
    )


def _adapter(executor):
    return BybitOrderSubmissionAdapter(
        payload_builder=BybitCreateOrderPayloadBuilder(),
        endpoint_executor=executor,
        response_interpreter=BybitOrderSubmissionResponseInterpreter(),
    )


def _full_stack_adapter(*behaviors):
    transport = _ScriptedTransport(*behaviors)
    return _adapter(_endpoint_executor(_private_api(transport))), transport


# ---------------------------------------------------------------------------
# Composición y estructura
# ---------------------------------------------------------------------------

class TestConstructionAndStructure:
    def test_satisfies_the_submission_port_structurally(self):
        assert isinstance(_adapter(_SpyExecutor()), OrderSubmissionPort)

    def test_submit_signature_is_exactly_the_port_signature(self):
        sig = inspect.signature(BybitOrderSubmissionAdapter.submit)
        assert list(sig.parameters) == ["self", "request"]
        assert sig.parameters["request"].annotation is ExecutionRequest
        assert sig.return_annotation is OrderSubmissionOutcome
        assert not inspect.iscoroutinefunction(BybitOrderSubmissionAdapter.submit)

    @pytest.mark.parametrize("kwargs", [
        dict(payload_builder=object()), dict(endpoint_executor=object()), dict(response_interpreter=object()),
        dict(payload_builder=None), dict(endpoint_executor=None), dict(response_interpreter=None),
    ])
    def test_constructor_rejects_wrong_collaborators(self, kwargs):
        good = dict(
            payload_builder=BybitCreateOrderPayloadBuilder(), endpoint_executor=_SpyExecutor(),
            response_interpreter=BybitOrderSubmissionResponseInterpreter(),
        )
        good.update(kwargs)
        with pytest.raises(TypeError):
            BybitOrderSubmissionAdapter(**good)

    def test_construction_performs_no_remote_call(self):
        spy = _SpyExecutor()
        _adapter(spy)
        assert spy.calls == []

    @pytest.mark.parametrize("bad", [None, "ord_x", {"order_id": _LINK}, object(), 5])
    def test_submit_rejects_a_non_execution_request_without_remote_call(self, bad):
        spy = _SpyExecutor(_response())
        with pytest.raises(TypeError):
            _adapter(spy).submit(bad)
        assert spy.calls == []

    def test_exported_from_package(self):
        assert execution_gateway.BybitOrderSubmissionAdapter is BybitOrderSubmissionAdapter
        assert "BybitOrderSubmissionAdapter" in execution_gateway.__all__

    def test_the_package_still_exports_the_unchanged_legacy_gateway(self):
        assert "BybitExecutionGateway" in execution_gateway.__all__


# ---------------------------------------------------------------------------
# Identidad: la identidad viaja en el request, el adapter no genera ninguna
# ---------------------------------------------------------------------------

class TestIdentityComesFromTheRequest:
    @pytest.mark.parametrize("order_id", [_LINK, "ord_abc", "x", "ORD_" + "F" * 32, "a" * 36])
    def test_order_link_id_is_exactly_request_order_id(self, order_id):
        spy = _SpyExecutor(_response(link=order_id))
        _adapter(spy).submit(_request(order_id=order_id))
        assert spy.calls[0]["payload"]["orderLinkId"] == order_id

    def test_adapter_generates_no_identity_between_calls(self):
        spy = _SpyExecutor(_response(), _response())
        adapter = _adapter(spy)
        adapter.submit(_request())
        adapter.submit(_request())
        assert [c["payload"]["orderLinkId"] for c in spy.calls] == [_LINK, _LINK]

    def test_the_exchange_order_id_never_replaces_the_order_link_id(self):
        spy = _SpyExecutor(_response(remote="remote-777"))
        _adapter(spy).submit(_request())
        assert spy.calls[0]["payload"]["orderLinkId"] == _LINK


# ---------------------------------------------------------------------------
# Resultados remotos conocidos -- una llamada, devueltos
# ---------------------------------------------------------------------------

class TestKnownRemoteOutcomes:
    def test_accepted(self):
        spy = _SpyExecutor(_response(ret_msg="OK", time_ms=_SERVER_TIME, remote=_REMOTE))
        outcome = _adapter(spy).submit(_request())
        assert outcome == SubmissionAccepted(exchange_order_id=_REMOTE, server_time_ms=_SERVER_TIME)
        assert len(spy.calls) == 1

    @pytest.mark.parametrize("code", [10001, 110003, 110004, 110007])
    def test_rejected(self, code):
        spy = _SpyExecutor(_response(ret_code=code, ret_msg=f" Reason {code} ", result={}, time_ms=77))
        outcome = _adapter(spy).submit(_request())
        assert outcome == SubmissionRejected(ret_code=code, ret_msg=f" Reason {code} ", server_time_ms=77)
        assert len(spy.calls) == 1

    def test_duplicate(self):
        spy = _SpyExecutor(_response(ret_code=110072, ret_msg="OrderLinkedID is duplicate", result={}, time_ms=88))
        outcome = _adapter(spy).submit(_request())
        assert outcome == SubmissionIdentityDuplicate(
            ret_code=110072, ret_msg="OrderLinkedID is duplicate", server_time_ms=88,
        )
        assert not isinstance(outcome, SubmissionRejected)
        assert len(spy.calls) == 1

    def test_unclassified_code_is_ambiguous(self):
        spy = _SpyExecutor(_response(ret_code=10006, ret_msg="Too many visits", result={}))
        assert _adapter(spy).submit(_request()) == SubmissionOutcomeUnknown(reason="ambiguous_business_response")
        assert len(spy.calls) == 1

    def test_identity_mismatch(self):
        spy = _SpyExecutor(_response(link="ord_" + "b" * 32))
        assert _adapter(spy).submit(_request()) == SubmissionOutcomeUnknown(reason="identity_mismatch")
        assert len(spy.calls) == 1

    def test_malformed_success_result(self):
        spy = _SpyExecutor(_response(result={"orderId": _REMOTE}))
        assert _adapter(spy).submit(_request()) == SubmissionOutcomeUnknown(reason="malformed_response")
        assert len(spy.calls) == 1

    def test_the_endpoint_is_the_create_order_endpoint(self):
        spy = _SpyExecutor(_response())
        _adapter(spy).submit(_request())
        assert spy.calls[0]["endpoint"] is BYBIT_CREATE_ORDER_ENDPOINT


# ---------------------------------------------------------------------------
# Taxonomía de errores de transporte
# ---------------------------------------------------------------------------

_OS_ERRORS = [
    OSError("generic"), TimeoutError("timed out"), socket.timeout("socket timeout"),
    ConnectionResetError("reset"), ConnectionRefusedError("refused"), ConnectionAbortedError("aborted"),
    BrokenPipeError("pipe"), socket.gaierror(-2, "dns"), urllib.error.URLError("no route"),
    urllib.error.HTTPError("https://x", 500, "server error", {}, None),
    urllib.error.HTTPError("https://x", 400, "bad request", {}, None),
    http.client.RemoteDisconnected("remote closed"),
]
_OS_ERROR_IDS = [type(e).__name__ + f"-{i}" for i, e in enumerate(_OS_ERRORS)]


_HTTP_CLIENT_ERRORS = [
    http.client.BadStatusLine("GARBAGE"),
    http.client.IncompleteRead(b"partial", 100),
    http.client.IncompleteRead(b""),
    http.client.LineTooLong("header line"),
    http.client.HTTPException("generic"),
    http.client.ImproperConnectionState("state"),
    http.client.CannotSendRequest("cannot send"),
    http.client.ResponseNotReady("not ready"),
    http.client.UnknownProtocol("HTTP/9"),
    http.client.NotConnected("nc"),
    http.client.InvalidURL("bad url"),
]
_HTTP_CLIENT_ERROR_IDS = [type(e).__name__ + f"-{i}" for i, e in enumerate(_HTTP_CLIENT_ERRORS)]


class TestTransportFailures:
    @pytest.mark.parametrize("error", _OS_ERRORS, ids=_OS_ERROR_IDS)
    def test_network_errors_are_transport_failure_after_exactly_one_call(self, error):
        spy = _SpyExecutor(error)
        outcome = _adapter(spy).submit(_request())
        assert outcome == SubmissionOutcomeUnknown(reason="transport_failure")
        assert len(spy.calls) == 1

    @pytest.mark.parametrize("error", _HTTP_CLIENT_ERRORS, ids=_HTTP_CLIENT_ERROR_IDS)
    def test_http_client_exceptions_are_transport_failure_after_exactly_one_call(self, error):
        # `HTTPException` NO hereda de `OSError` (salvo `RemoteDisconnected`) y puede
        # surgir DESPUÉS de que el servidor recibió la orden completa (ADR-015 D9).
        spy = _SpyExecutor(error)
        outcome = _adapter(spy).submit(_request())
        assert outcome == SubmissionOutcomeUnknown(reason="transport_failure")
        assert len(spy.calls) == 1

    @pytest.mark.parametrize("error", _HTTP_CLIENT_ERRORS, ids=_HTTP_CLIENT_ERROR_IDS)
    def test_http_client_exceptions_do_not_trigger_a_second_call(self, error):
        spy = _SpyExecutor(error, _response())
        _adapter(spy).submit(_request())
        assert len(spy.calls) == 1
        assert len(spy._behaviors) == 1

    def test_the_http_client_family_is_not_part_of_oserror_except_remote_disconnected(self):
        # Precondición real de la jerarquía: documenta por qué el catch explícito es necesario.
        assert not issubclass(http.client.HTTPException, OSError)
        for cls in (http.client.BadStatusLine, http.client.IncompleteRead, http.client.LineTooLong):
            assert not issubclass(cls, OSError)
        assert issubclass(http.client.RemoteDisconnected, OSError)

    def test_response_processing_error_is_malformed_response(self):
        spy = _SpyExecutor(BybitResponseProcessingError(message="Bybit response could not be processed"))
        assert _adapter(spy).submit(_request()) == SubmissionOutcomeUnknown(reason="malformed_response")
        assert len(spy.calls) == 1

    def test_a_timeout_does_not_trigger_a_second_call_even_if_a_second_response_is_available(self):
        spy = _SpyExecutor(TimeoutError("t"), _response())
        outcome = _adapter(spy).submit(_request())
        assert outcome == SubmissionOutcomeUnknown(reason="transport_failure")
        assert len(spy.calls) == 1
        assert len(spy._behaviors) == 1  # la respuesta disponible nunca se consumió

    def test_a_rejection_does_not_trigger_a_second_call(self):
        spy = _SpyExecutor(_response(ret_code=110004, result={}), _response())
        _adapter(spy).submit(_request())
        assert len(spy.calls) == 1

    def test_duplicate_does_not_trigger_a_second_call(self):
        spy = _SpyExecutor(_response(ret_code=110072, ret_msg="dup", result={}), _response())
        _adapter(spy).submit(_request())
        assert len(spy.calls) == 1


class TestProgrammingErrorsPropagate:
    @pytest.mark.parametrize("error", [
        TypeError("bug"), ValueError("bug"), KeyError("bug"), AttributeError("bug"), AssertionError("bug"),
        RuntimeError("bug"), ZeroDivisionError("bug"), IndexError("bug"), NotImplementedError("bug"),
        LookupError("bug"), Exception("bug"),
    ], ids=lambda e: type(e).__name__)
    def test_non_transport_exceptions_are_not_converted_to_unknown(self, error):
        spy = _SpyExecutor(error)
        with pytest.raises(type(error)) as caught:
            _adapter(spy).submit(_request())
        assert caught.value is error
        assert len(spy.calls) == 1

    def test_programming_error_before_the_call_propagates_with_zero_remote_calls(self):
        class _BrokenBuilder(BybitCreateOrderPayloadBuilder):
            def build(self, *, request):
                raise ValueError("local logic bug")

        spy = _SpyExecutor(_response())
        adapter = BybitOrderSubmissionAdapter(
            payload_builder=_BrokenBuilder(), endpoint_executor=spy,
            response_interpreter=BybitOrderSubmissionResponseInterpreter(),
        )
        with pytest.raises(ValueError):
            adapter.submit(_request())
        assert spy.calls == []

    def test_a_local_valueerror_is_not_confused_with_a_transport_failure(self):
        # `ValueError` NO es `OSError` ni `HTTPException`: aun surgiendo de la
        # llamada remota (p. ej. un bug del executor) se propaga.
        error = ValueError("local unexpected")
        with pytest.raises(ValueError) as caught:
            _adapter(_SpyExecutor(error)).submit(_request())
        assert caught.value is error

    def test_programming_error_in_the_interpreter_propagates(self):
        class _BrokenInterpreter(BybitOrderSubmissionResponseInterpreter):
            def interpret(self, *, response, expected_order_link_id):
                raise RuntimeError("interpreter bug")

        adapter = BybitOrderSubmissionAdapter(
            payload_builder=BybitCreateOrderPayloadBuilder(), endpoint_executor=_SpyExecutor(_response()),
            response_interpreter=_BrokenInterpreter(),
        )
        with pytest.raises(RuntimeError):
            adapter.submit(_request())

    def test_oserror_raised_by_the_interpreter_is_not_treated_as_a_transport_failure(self):
        # El `try` cubre SÓLO la llamada remota, no la interpretación.
        class _OsInterpreter(BybitOrderSubmissionResponseInterpreter):
            def interpret(self, *, response, expected_order_link_id):
                raise OSError("not a network failure")

        adapter = BybitOrderSubmissionAdapter(
            payload_builder=BybitCreateOrderPayloadBuilder(), endpoint_executor=_SpyExecutor(_response()),
            response_interpreter=_OsInterpreter(),
        )
        with pytest.raises(OSError):
            adapter.submit(_request())


# ---------------------------------------------------------------------------
# Request no representable: cero llamadas
# ---------------------------------------------------------------------------

class TestNotRepresentableRequestsNeverReachTheNetwork:
    @pytest.mark.parametrize("request_kwargs", [
        dict(order_id="o" * 37),
        dict(order_id="o" * 100),
        dict(quantity=float("nan")),
        dict(quantity=float("inf")),
        dict(order_type="limit", price=float("inf"), side="sell"),
        dict(order_type="limit", price=float("nan")),
    ], ids=["id-37", "id-100", "qty-nan", "qty-inf", "price-inf", "price-nan"])
    def test_raises_not_supported_with_zero_remote_calls(self, request_kwargs):
        spy = _SpyExecutor(_response())
        with pytest.raises(ExecutionRequestNotSupportedError):
            _adapter(spy).submit(_request(**request_kwargs))
        assert spy.calls == []

    def test_zero_transport_calls_through_the_full_stack(self):
        adapter, transport = _full_stack_adapter(_wire())
        with pytest.raises(ExecutionRequestNotSupportedError):
            adapter.submit(_request(order_id="o" * 37))
        assert transport.calls == []

    def test_a_36_character_order_id_is_representable(self):
        spy = _SpyExecutor(_response(link="o" * 36))
        outcome = _adapter(spy).submit(_request(order_id="o" * 36))
        assert type(outcome) is SubmissionAccepted
        assert len(spy.calls) == 1

    def test_not_supported_error_is_not_converted_into_an_outcome(self):
        with pytest.raises(ExecutionRequestNotSupportedError):
            _adapter(_SpyExecutor()).submit(_request(quantity=float("nan")))


# ---------------------------------------------------------------------------
# Paridad de payload con el camino aceptado (cable idéntico)
# ---------------------------------------------------------------------------

_PARITY_REQUESTS = [
    dict(),
    dict(side="sell", quantity=1.5),
    dict(order_type="limit", price=50000.5),
    dict(order_type="limit", price=0.1 + 0.2, side="sell", quantity=0.1 + 0.7),
    dict(quantity=1e-07),
    dict(quantity=123456789.125, order_type="limit", price=1e16),
    dict(symbol="ETHUSDT", quantity=2.0),
    dict(symbol="btcUSDT", quantity=2.0),
    dict(order_id="short", quantity=3),
    dict(order_id="o" * 36, order_type="limit", price=0.0001),
]


def _legacy_wire(request):
    transport = _ScriptedTransport(_wire(link=request.order_id))
    gateway = create_bybit_demo_execution_gateway(private_api=_private_api(transport))
    gateway.execute(request)
    assert len(transport.calls) == 1
    return transport.calls[0]


class TestPayloadParityWithTheAcceptedPath:
    @pytest.mark.parametrize("overrides", _PARITY_REQUESTS, ids=lambda o: str(sorted(o.items())))
    def test_the_wire_request_is_identical_to_the_legacy_gateway_wire_request(self, overrides):
        request = _request(**overrides)
        adapter, transport = _full_stack_adapter(_wire(link=request.order_id))
        adapter.submit(request)
        assert len(transport.calls) == 1
        assert transport.calls[0] == _legacy_wire(request)

    def test_discriminating_expected_payload_for_a_limit_order(self):
        request = _request(order_type="limit", price=50000.5, side="sell", quantity=0.25)
        adapter, transport = _full_stack_adapter(_wire())
        adapter.submit(request)
        body = json.loads(transport.calls[0]["body"])
        assert body == {
            "category": "linear", "symbol": "BTCUSDT", "side": "Sell", "orderType": "Limit",
            "qty": "0.25", "price": "50000.5", "timeInForce": "GTC", "reduceOnly": False,
            "orderLinkId": _LINK,
        }
        assert transport.calls[0]["url"] == "https://api-demo.bybit.com/v5/order/create"

    @pytest.mark.parametrize("symbol", ["btcusdt", "BtcUsdt", "ETHUSDT", "1000PEPEUSDT"])
    def test_symbol_is_forwarded_literally_without_case_normalization(self, symbol):
        adapter, transport = _full_stack_adapter(_wire())
        adapter.submit(_request(symbol=symbol))
        assert json.loads(transport.calls[0]["body"])["symbol"] == symbol

    def test_market_order_payload_has_no_price(self):
        adapter, transport = _full_stack_adapter(_wire())
        adapter.submit(_request())
        body = json.loads(transport.calls[0]["body"])
        assert "price" not in body
        assert body["orderType"] == "Market"

    def test_reduce_only_is_always_false_and_time_in_force_gtc(self):
        for request in (_request(), _request(side="sell", order_type="limit", price=3.0)):
            adapter, transport = _full_stack_adapter(_wire())
            adapter.submit(request)
            body = json.loads(transport.calls[0]["body"])
            assert body["reduceOnly"] is False
            assert body["timeInForce"] == "GTC"

    def test_quantity_uses_the_canonical_decimal_string_not_the_binary_float(self):
        adapter, transport = _full_stack_adapter(_wire())
        adapter.submit(_request(quantity=0.1 + 0.2))
        assert json.loads(transport.calls[0]["body"])["qty"] == "0.30000000000000004"


# ---------------------------------------------------------------------------
# Extremo a extremo con el stack real (sólo el transporte es un doble)
# ---------------------------------------------------------------------------

class TestEndToEndThroughTheRealStack:
    def test_accepted_preserves_remote_id_and_response_time_not_the_auth_timestamp(self):
        adapter, transport = _full_stack_adapter(_wire(time=_SERVER_TIME, remote="REMOTE-id-5", link=_LINK))
        outcome = adapter.submit(_request())
        assert outcome == SubmissionAccepted(exchange_order_id="REMOTE-id-5", server_time_ms=_SERVER_TIME)
        assert outcome.server_time_ms != _AUTH_TS
        assert outcome.exchange_order_id != _LINK
        assert len(transport.calls) == 1

    def test_the_auth_timestamp_is_really_distinct_and_really_sent(self):
        adapter, transport = _full_stack_adapter(_wire())
        adapter.submit(_request())
        assert str(_AUTH_TS) in json.dumps(transport.calls[0]["headers"])
        assert _SERVER_TIME != _AUTH_TS

    def test_rejected_preserves_literal_ret_msg_and_response_time(self):
        adapter, transport = _full_stack_adapter(
            _wire(ret_code=110007, ret_msg="  Insufficient AVAILABLE balance  ", result={}, time=424242),
        )
        outcome = adapter.submit(_request())
        assert outcome == SubmissionRejected(
            ret_code=110007, ret_msg="  Insufficient AVAILABLE balance  ", server_time_ms=424242,
        )
        assert outcome.server_time_ms != _AUTH_TS
        assert len(transport.calls) == 1

    def test_duplicate_preserves_literal_ret_msg_and_response_time(self):
        adapter, transport = _full_stack_adapter(
            _wire(ret_code=110072, ret_msg=" OrderLinkedID is DUPLICATE ", result={}, time=515151),
        )
        outcome = adapter.submit(_request())
        assert outcome == SubmissionIdentityDuplicate(
            ret_code=110072, ret_msg=" OrderLinkedID is DUPLICATE ", server_time_ms=515151,
        )
        assert not isinstance(outcome, SubmissionRejected)
        assert len(transport.calls) == 1

    def test_unclassified_code_through_the_stack(self):
        adapter, transport = _full_stack_adapter(_wire(ret_code=10006, ret_msg="rate", result={}))
        assert adapter.submit(_request()) == SubmissionOutcomeUnknown(reason="ambiguous_business_response")
        assert len(transport.calls) == 1

    @pytest.mark.parametrize("raw", [
        "not json", "", "[]", "null", "42", '"text"', "{",
        json.dumps({"retCode": 0}),
        json.dumps({"retMsg": "OK", "result": {}, "retExtInfo": {}, "time": 1}),
        json.dumps({"retCode": 0, "retMsg": "OK", "result": {}, "retExtInfo": {}}),
        json.dumps({"retCode": 0, "retMsg": 5, "result": {}, "retExtInfo": {}, "time": 1}),
        json.dumps({"retCode": 0, "retMsg": "OK", "result": {}, "retExtInfo": {}, "time": "1"}),
        json.dumps({"retCode": 0, "retMsg": "OK", "result": {}, "retExtInfo": {}, "time": -1}),
        json.dumps({"retCode": 0, "retMsg": "OK", "result": {}, "retExtInfo": {}, "time": True}),
    ], ids=lambda r: r[:40] or "empty")
    def test_unparseable_or_incomplete_response_is_malformed_never_accepted(self, raw):
        adapter, transport = _full_stack_adapter(raw)
        assert adapter.submit(_request()) == SubmissionOutcomeUnknown(reason="malformed_response")
        assert len(transport.calls) == 1

    @pytest.mark.parametrize("ret_code", [True, False, 0.0, 10001.0, "0", "10001", None])
    def test_ret_code_from_the_wire_is_never_coerced(self, ret_code):
        raw = json.dumps({"retCode": ret_code, "retMsg": "OK", "result": {"orderId": _REMOTE, "orderLinkId": _LINK},
                          "retExtInfo": {}, "time": _SERVER_TIME})
        adapter, transport = _full_stack_adapter(raw)
        outcome = adapter.submit(_request())
        assert outcome == SubmissionOutcomeUnknown(reason="malformed_response")
        assert not isinstance(outcome, (SubmissionAccepted, SubmissionRejected))

    def test_invalid_utf8_response_is_malformed(self):
        adapter, transport = _full_stack_adapter(UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"))
        assert adapter.submit(_request()) == SubmissionOutcomeUnknown(reason="malformed_response")
        assert len(transport.calls) == 1

    @pytest.mark.parametrize("error", _OS_ERRORS, ids=_OS_ERROR_IDS)
    def test_transport_exceptions_through_the_stack_are_transport_failure_with_one_call(self, error):
        adapter, transport = _full_stack_adapter(error)
        assert adapter.submit(_request()) == SubmissionOutcomeUnknown(reason="transport_failure")
        assert len(transport.calls) == 1

    @pytest.mark.parametrize("error", _HTTP_CLIENT_ERRORS, ids=_HTTP_CLIENT_ERROR_IDS)
    def test_http_client_exceptions_through_the_stack_are_transport_failure_with_one_call(self, error):
        adapter, transport = _full_stack_adapter(error)
        assert adapter.submit(_request()) == SubmissionOutcomeUnknown(reason="transport_failure")
        assert len(transport.calls) == 1

    @pytest.mark.parametrize("error", [ValueError("bug"), AssertionError("bug"), KeyError("bug"), RuntimeError("bug")],
                             ids=lambda e: type(e).__name__)
    def test_programming_errors_from_the_transport_propagate_through_the_stack(self, error):
        adapter, transport = _full_stack_adapter(error)
        with pytest.raises(type(error)):
            adapter.submit(_request())
        assert len(transport.calls) == 1

    def test_programming_error_from_the_transport_propagates_with_one_call(self):
        adapter, transport = _full_stack_adapter(TypeError("transport bug"))
        with pytest.raises(TypeError):
            adapter.submit(_request())
        assert len(transport.calls) == 1

    def test_identity_mismatch_through_the_stack(self):
        adapter, transport = _full_stack_adapter(_wire(link="ord_" + "b" * 32))
        assert adapter.submit(_request()) == SubmissionOutcomeUnknown(reason="identity_mismatch")
        assert len(transport.calls) == 1

    def test_all_four_unknown_reasons_are_producible(self):
        produced = set()
        scenarios = [
            [OSError("x")],
            ["not json"],
            [_wire(ret_code=10006, result={})],
            [_wire(link="ord_" + "b" * 32)],
        ]
        for behaviors in scenarios:
            adapter, _ = _full_stack_adapter(*behaviors)
            outcome = adapter.submit(_request())
            produced.add(outcome.reason)
        assert produced == {
            "transport_failure", "malformed_response", "ambiguous_business_response", "identity_mismatch",
        }

    def test_two_submits_make_exactly_two_independent_remote_calls(self):
        adapter, transport = _full_stack_adapter(_wire(), _wire(ret_code=110072, ret_msg="dup", result={}))
        first = adapter.submit(_request())
        second = adapter.submit(_request())
        assert type(first) is SubmissionAccepted
        assert type(second) is SubmissionIdentityDuplicate
        assert len(transport.calls) == 2


# ---------------------------------------------------------------------------
# Sin Ledger, sin reintentos, sin amplitud de captura (AST)
# ---------------------------------------------------------------------------

def _tree():
    return ast.parse(inspect.getsource(_module))


def _imports():
    names = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module)
    return names


class TestStructuralGuarantees:
    def test_does_not_import_the_ledger_or_identity_modules(self):
        assert not any("ledger" in name or "identity" in name for name in _imports())

    def test_does_not_import_clock_uuid_sleep_or_retry_machinery(self):
        for forbidden in ("time", "uuid", "datetime", "random", "asyncio", "threading", "tenacity", "functools"):
            assert forbidden not in _imports()

    def test_names_no_ledger_event_or_identity_symbol(self):
        names = {n.id for n in ast.walk(_tree()) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(_tree()) if isinstance(n, ast.Attribute)}
        for forbidden in ("ExecutionLedgerEvent", "ExecutionOrderId", "ExecutionAccountId",
                          "OrderAcceptedByExchange", "OrderRejectedByExchange",
                          "OrderIdentityReportedDuplicateByExchange", "OrderSubmissionOutcomeUnknown",
                          "OrderSubmissionAttempted", "sleep", "now", "time", "uuid4"):
            assert forbidden not in names

    def test_no_loop_construct_exists_so_a_retry_is_structurally_impossible(self):
        assert not [n for n in ast.walk(_tree()) if isinstance(n, (ast.For, ast.While, ast.AsyncFor))]

    def test_exactly_one_remote_call_site(self):
        calls = [n for n in ast.walk(_tree()) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "execute"]
        assert len(calls) == 1

    def test_only_the_known_transport_failure_types_are_caught(self):
        handlers = [n for n in ast.walk(_tree()) if isinstance(n, ast.ExceptHandler)]
        assert sorted(ast.unparse(h.type) for h in handlers) == [
            "(OSError, http.client.HTTPException)", "BybitResponseProcessingError",
        ]

    def test_no_bare_or_broad_except(self):
        for h in (n for n in ast.walk(_tree()) if isinstance(n, ast.ExceptHandler)):
            assert h.type is not None
            assert ast.unparse(h.type) not in ("Exception", "BaseException")

    def test_the_remote_call_is_the_only_statement_inside_the_try(self):
        tries = [n for n in ast.walk(_tree()) if isinstance(n, ast.Try)]
        assert len(tries) == 1
        assert len(tries[0].body) == 1

    def test_adapter_holds_no_mutable_attribute_beyond_its_three_collaborators(self):
        adapter = _adapter(_SpyExecutor())
        assert sorted(vars(adapter)) == ["_endpoint_executor", "_payload_builder", "_response_interpreter"]

    def test_legacy_gateway_is_not_used_by_the_adapter(self):
        assert "execution_gateway.bybit_gateway" not in _imports()
        assert "execution_gateway.bybit_client" not in _imports()
        assert "execution_gateway.bybit_create_order_operation" not in _imports()

    def test_canonical_decimal_authority_is_the_only_float_conversion(self):
        src = inspect.getsource(_module)
        assert "canonical_execution_decimal" in src
        assert "Decimal(" not in src
        assert "from_float" not in src

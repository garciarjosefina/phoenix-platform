import hashlib
import hmac
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_authenticator import BybitAuthentication
from execution_gateway.bybit_endpoint import BybitEndpoint
from execution_gateway.bybit_endpoints import BYBIT_WALLET_BALANCE_ENDPOINT
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_private_get_request_sender import BybitPrivateGetRequestSender
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.bybit_wallet_balance_reader import BybitWalletBalanceReader
from execution_gateway.bybit_wallet_balance_response_interpreter import (
    BybitWalletBalanceResponseInterpreter,
)
from execution_gateway.credentials import BybitDemoCredentials
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.hmac_sha256_signer import HmacSha256Signer
from execution_gateway.http_get_request_executor import HttpGetRequestExecutor
from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot

_SENTINEL_URL = "https://api-demo.bybit.com/v5/account/wallet-balance"
_SENTINEL_ACCOUNT_ITEM = {
    "accountType": "UNIFIED",
    "totalEquity": "1000",
    "totalWalletBalance": "1000",
    "totalAvailableBalance": "1000",
    "totalInitialMargin": "0",
    "totalMaintenanceMargin": "0",
    "coin": (),
}
_SENTINEL_RESPONSE = BybitResponse(
    ret_code=0, ret_msg="OK", result={"list": (_SENTINEL_ACCOUNT_ITEM,)}, ret_ext_info={}, time_ms=1_000,
)
_SENTINEL_SNAPSHOT = WalletBalanceSnapshot(
    total_equity=Decimal("1000"), total_wallet_balance=Decimal("1000"),
    total_available_balance=Decimal("1000"), total_initial_margin=Decimal("0"),
    total_maintenance_margin=Decimal("0"), currency_balances=(), server_time_ms=1_000,
)


class _SpyUrlBuilder(BybitUrlBuilder):
    def __init__(self, result: str = _SENTINEL_URL) -> None:
        self.calls: list[dict] = []
        self._result = result

    def build(self, *, endpoint: BybitEndpoint) -> str:
        self.calls.append({"endpoint": endpoint})
        return self._result


class _SpyPrivateGetApi(BybitPrivateGetApi):
    def __init__(
        self,
        *,
        result: BybitResponse | None = None,
        results: list[BybitResponse] | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.calls: list[dict] = []
        self._results = list(results) if results is not None else None
        self._result = result if result is not None else _SENTINEL_RESPONSE
        self._exc = exc

    def request(self, *, url: str, query_string: str) -> BybitResponse:
        self.calls.append({"url": url, "query_string": query_string})
        if self._exc is not None:
            raise self._exc
        if self._results is not None:
            return self._results.pop(0)
        return self._result


class _SpyInterpreter(BybitWalletBalanceResponseInterpreter):
    def __init__(
        self,
        *,
        result: WalletBalanceSnapshot | None = None,
        results: list[WalletBalanceSnapshot] | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.calls: list[dict] = []
        self._results = list(results) if results is not None else None
        self._result = result if result is not None else _SENTINEL_SNAPSHOT
        self._exc = exc

    def interpret(self, *, response: BybitResponse) -> WalletBalanceSnapshot:
        self.calls.append({"response": response})
        if self._exc is not None:
            raise self._exc
        if self._results is not None:
            return self._results.pop(0)
        return self._result


def _reader(*, url_builder=None, private_get_api=None, response_interpreter=None):
    return BybitWalletBalanceReader(
        private_get_api=private_get_api or _SpyPrivateGetApi(),
        url_builder=url_builder or _SpyUrlBuilder(),
        response_interpreter=response_interpreter or _SpyInterpreter(),
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitWalletBalanceReader")
        assert execution_gateway.BybitWalletBalanceReader is BybitWalletBalanceReader

    def test_in_all(self):
        assert "BybitWalletBalanceReader" in execution_gateway.__all__

    def test_satisfies_wallet_balance_reader_protocol(self):
        from execution_gateway.wallet_balance_reader import WalletBalanceReader
        assert isinstance(_reader(), WalletBalanceReader)


class TestConstruction:
    def test_private_get_api_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitPrivateGetApi"):
            BybitWalletBalanceReader(
                private_get_api=object(),
                url_builder=_SpyUrlBuilder(),
                response_interpreter=_SpyInterpreter(),
            )

    def test_url_builder_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitUrlBuilder"):
            BybitWalletBalanceReader(
                private_get_api=_SpyPrivateGetApi(),
                url_builder=object(),
                response_interpreter=_SpyInterpreter(),
            )

    def test_response_interpreter_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitWalletBalanceResponseInterpreter"):
            BybitWalletBalanceReader(
                private_get_api=_SpyPrivateGetApi(),
                url_builder=_SpyUrlBuilder(),
                response_interpreter=object(),
            )


class TestQueryWalletBalance:
    def test_returns_wallet_balance_snapshot(self):
        snapshot = _reader().query_wallet_balance()
        assert isinstance(snapshot, WalletBalanceSnapshot)

    def test_returns_interpreter_result_by_identity(self):
        interpreter = _SpyInterpreter(result=_SENTINEL_SNAPSHOT)
        reader = _reader(response_interpreter=interpreter)
        assert reader.query_wallet_balance() is _SENTINEL_SNAPSHOT

    def test_url_built_from_wallet_balance_endpoint(self):
        url_builder = _SpyUrlBuilder()
        reader = _reader(url_builder=url_builder)
        reader.query_wallet_balance()
        assert url_builder.calls[0]["endpoint"] is BYBIT_WALLET_BALANCE_ENDPOINT

    def test_uses_url_from_builder(self):
        api = _SpyPrivateGetApi()
        reader = _reader(url_builder=_SpyUrlBuilder(result="https://custom/x"), private_get_api=api)
        reader.query_wallet_balance()
        assert api.calls[0]["url"] == "https://custom/x"

    def test_query_string_is_account_type_unified(self):
        api = _SpyPrivateGetApi()
        reader = _reader(private_get_api=api)
        reader.query_wallet_balance()
        assert api.calls[0]["query_string"] == "accountType=UNIFIED"

    def test_query_string_does_not_pin_a_specific_coin(self):
        # Omitir `coin` es deliberado -- fijarlo ocultaría en silencio
        # cualquier otra moneda con saldo presente en la cuenta.
        api = _SpyPrivateGetApi()
        reader = _reader(private_get_api=api)
        reader.query_wallet_balance()
        assert "coin=" not in api.calls[0]["query_string"]

    def test_response_passed_to_interpreter_by_identity(self):
        response = BybitResponse(
            ret_code=0, ret_msg="OK", result={"list": (_SENTINEL_ACCOUNT_ITEM,)}, ret_ext_info={}, time_ms=1,
        )
        interpreter = _SpyInterpreter()
        reader = _reader(
            private_get_api=_SpyPrivateGetApi(result=response),
            response_interpreter=interpreter,
        )
        reader.query_wallet_balance()
        assert interpreter.calls[0]["response"] is response

    def test_exactly_one_api_request_call(self):
        api = _SpyPrivateGetApi()
        reader = _reader(private_get_api=api)
        reader.query_wallet_balance()
        assert len(api.calls) == 1

    def test_exactly_one_interpret_call(self):
        interpreter = _SpyInterpreter()
        reader = _reader(response_interpreter=interpreter)
        reader.query_wallet_balance()
        assert len(interpreter.calls) == 1


class TestErrorTranslation:
    """Ningún tipo Bybit cruza query_wallet_balance() -- mismo principio que
    BybitPositionsReader/BybitOpenOrdersReader: todo se traduce a
    ExecutionInfrastructureError ya existente, sin inventar jerarquía nueva."""

    def test_api_error_translated_to_infrastructure_error(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="invalid key"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_wallet_balance()

    def test_bybit_api_error_does_not_cross_the_port(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="invalid key"))
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_wallet_balance()
            assert False, "expected ExecutionInfrastructureError"
        except BybitApiError:
            assert False, "BybitApiError must not cross the read Port"
        except ExecutionInfrastructureError:
            pass

    def test_response_processing_error_from_interpreter_translated(self):
        interpreter = _SpyInterpreter(exc=BybitResponseProcessingError(message="bad schema"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_wallet_balance()

    def test_response_processing_error_from_transport_layer_translated(self):
        api = _SpyPrivateGetApi(exc=BybitResponseProcessingError(message="bad utf-8"))
        reader = _reader(private_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_wallet_balance()

    def test_os_error_from_transport_translated(self):
        api = _SpyPrivateGetApi(exc=OSError("connection refused"))
        reader = _reader(private_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_wallet_balance()

    def test_original_error_preserved_as_cause(self):
        original = BybitApiError(ret_code=10003, ret_msg="invalid key")
        interpreter = _SpyInterpreter(exc=original)
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_wallet_balance()
        except ExecutionInfrastructureError as error:
            assert error.__cause__ is original

    def test_infrastructure_error_message_does_not_leak_ret_msg(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="SUPER_SECRET_DETAIL"))
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_wallet_balance()
            assert False
        except ExecutionInfrastructureError as error:
            assert "SUPER_SECRET_DETAIL" not in str(error)

    def test_type_error_from_interpreter_propagates_unwrapped(self):
        interpreter = _SpyInterpreter(exc=TypeError("programming bug"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(TypeError, match="programming bug"):
            reader.query_wallet_balance()


class TestNoTrading:
    def test_no_create_order_reference_in_source(self):
        import inspect
        import execution_gateway.bybit_wallet_balance_reader as module
        src = inspect.getsource(module)
        assert "create_order" not in src
        assert "place_order" not in src
        assert "BybitCreateOrderOperation" not in src
        assert "/v5/order/create" not in src

    def test_does_not_import_execution_gateway_write_types(self):
        import execution_gateway.bybit_wallet_balance_reader as module
        assert not hasattr(module, "ExecutionGateway")
        assert not hasattr(module, "BybitExecutionGateway")
        assert not hasattr(module, "BybitDemoClient")


class TestNoCacheAcrossCalls:
    """Lección directa del Hito 3.70 (IMPORTANT-3), aplicada desde el primer
    commit de este hito: un futuro Reconciliation/Risk Engine mantendrá vivo
    un mismo BybitWalletBalanceReader y lo consultará repetidas veces."""

    def test_api_called_exactly_twice_on_two_queries(self):
        api = _SpyPrivateGetApi(results=[_SENTINEL_RESPONSE, _SENTINEL_RESPONSE])
        reader = _reader(private_get_api=api)
        reader.query_wallet_balance()
        reader.query_wallet_balance()
        assert len(api.calls) == 2

    def test_interpreter_called_exactly_twice_on_two_queries(self):
        snap_a = WalletBalanceSnapshot(
            total_equity=Decimal("1"), total_wallet_balance=Decimal("1"),
            total_available_balance=Decimal("1"), total_initial_margin=Decimal("0"),
            total_maintenance_margin=Decimal("0"), currency_balances=(), server_time_ms=1,
        )
        snap_b = WalletBalanceSnapshot(
            total_equity=Decimal("2"), total_wallet_balance=Decimal("2"),
            total_available_balance=Decimal("2"), total_initial_margin=Decimal("0"),
            total_maintenance_margin=Decimal("0"), currency_balances=(), server_time_ms=2,
        )
        interpreter = _SpyInterpreter(results=[snap_a, snap_b])
        reader = _reader(response_interpreter=interpreter)
        reader.query_wallet_balance()
        reader.query_wallet_balance()
        assert len(interpreter.calls) == 2

    def test_two_calls_on_same_instance_return_distinct_snapshots_by_identity(self):
        snap_a = WalletBalanceSnapshot(
            total_equity=Decimal("1"), total_wallet_balance=Decimal("1"),
            total_available_balance=Decimal("1"), total_initial_margin=Decimal("0"),
            total_maintenance_margin=Decimal("0"), currency_balances=(), server_time_ms=1,
        )
        snap_b = WalletBalanceSnapshot(
            total_equity=Decimal("2"), total_wallet_balance=Decimal("2"),
            total_available_balance=Decimal("2"), total_initial_margin=Decimal("0"),
            total_maintenance_margin=Decimal("0"), currency_balances=(), server_time_ms=2,
        )
        interpreter = _SpyInterpreter(results=[snap_a, snap_b])
        reader = _reader(response_interpreter=interpreter)
        first = reader.query_wallet_balance()
        second = reader.query_wallet_balance()
        assert first is snap_a
        assert second is snap_b
        assert first is not second

    def test_second_snapshot_reflects_second_api_response_end_to_end(self):
        resp1 = BybitResponse(
            ret_code=0, ret_msg="OK", result={"list": (_SENTINEL_ACCOUNT_ITEM,)}, ret_ext_info={}, time_ms=111,
        )
        resp2 = BybitResponse(
            ret_code=0, ret_msg="OK", result={"list": (_SENTINEL_ACCOUNT_ITEM,)}, ret_ext_info={}, time_ms=222,
        )
        api = _SpyPrivateGetApi(results=[resp1, resp2])
        reader = _reader(private_get_api=api, response_interpreter=BybitWalletBalanceResponseInterpreter())
        first = reader.query_wallet_balance()
        second = reader.query_wallet_balance()
        assert first.server_time_ms == 111
        assert second.server_time_ms == 222

    def test_reader_instance_has_no_cache_attribute_after_query(self):
        reader = _reader()
        reader.query_wallet_balance()
        assert not hasattr(reader, "_cached")
        assert not hasattr(reader, "_cache")
        assert not hasattr(reader, "_last_result")
        assert not hasattr(reader, "_last_snapshot")

    def test_two_independent_reader_instances_do_not_share_state(self):
        reader_a = _reader()
        reader_b = _reader()
        assert reader_a is not reader_b
        assert vars(reader_a).keys() == {"_private_get_api", "_url_builder", "_response_interpreter"}

    def test_second_query_after_first_failure_still_calls_api_again(self):
        api = _SpyPrivateGetApi(exc=OSError("down"))
        reader = _reader(private_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_wallet_balance()
        api._exc = None
        api._result = _SENTINEL_RESPONSE
        reader.query_wallet_balance()
        assert len(api.calls) == 2


class TestQueryCanonicalization:
    """La query firmada para HMAC debe ser byte-idéntica a la enviada en la
    URL -- verificado con el pipeline productivo real de autenticación
    (StandardBybitAuthenticator + HmacSha256Signer + BybitHeaderBuilder),
    recalculando el HMAC de forma independiente en el test."""

    def _real_reader(self, *, transport, recv_window_ms=5000, now_ms=1_700_000_000_000):
        class _FixedClock:
            def now_ms(self_inner):
                return now_ms

        credentials = BybitDemoCredentials(api_key="demo-key", api_secret="demo-secret")
        authenticator = StandardBybitAuthenticator(
            credentials=credentials,
            clock=_FixedClock(),
            signer=HmacSha256Signer(),
            recv_window_ms=recv_window_ms,
        )
        executor = HttpGetRequestExecutor(transport=transport, timeout_seconds=10)
        sender = BybitPrivateGetRequestSender(
            authenticator=authenticator,
            header_builder=BybitHeaderBuilder(),
            request_executor=executor,
        )
        from execution_gateway.bybit_response_parser import BybitResponseParser
        from execution_gateway.standard_json_serializer import StandardJsonSerializer

        private_get_api = BybitPrivateGetApi(
            sender=sender, response_parser=BybitResponseParser(serializer=StandardJsonSerializer()),
        )
        return BybitWalletBalanceReader(
            private_get_api=private_get_api,
            url_builder=BybitUrlBuilder(base_url="https://api-demo.bybit.com"),
            response_interpreter=BybitWalletBalanceResponseInterpreter(),
        )

    def test_signature_matches_independently_computed_hmac_for_query_string(self):
        import json

        class _SpyTransport:
            def __init__(self):
                self.calls = []

            def get(self, *, url, headers, timeout_seconds):
                self.calls.append(dict(url=url, headers=headers, timeout_seconds=timeout_seconds))
                return json.dumps({
                    "retCode": 0, "retMsg": "OK",
                    "result": {"list": [_SENTINEL_ACCOUNT_ITEM]},
                    "retExtInfo": {}, "time": 1_000,
                })

        transport = _SpyTransport()
        reader = self._real_reader(transport=transport)
        reader.query_wallet_balance()

        headers = transport.calls[0]["headers"]
        query_string = "accountType=UNIFIED"
        message = (
            headers["X-BAPI-TIMESTAMP"] + headers["X-BAPI-API-KEY"]
            + headers["X-BAPI-RECV-WINDOW"] + query_string
        )
        expected = hmac.new(b"demo-secret", message.encode("utf-8"), hashlib.sha256).hexdigest()
        assert headers["X-BAPI-SIGN"] == expected

        assert transport.calls[0]["url"] == (
            "https://api-demo.bybit.com/v5/account/wallet-balance?accountType=UNIFIED"
        )

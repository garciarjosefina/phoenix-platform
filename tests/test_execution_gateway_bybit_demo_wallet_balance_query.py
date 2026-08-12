import inspect
import json
import urllib.error
import urllib.request
from decimal import Decimal

import pytest

import execution_gateway
import execution_gateway.bybit_demo_wallet_balance_query as _module
from execution_gateway import (
    EnvironmentConfigurationError,
    WalletBalanceSnapshot,
    query_bybit_demo_wallet_balance,
)
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError

_VALID_ENV = {
    "PHOENIX_BYBIT_DEMO_API_KEY": "demo-key",
    "PHOENIX_BYBIT_DEMO_API_SECRET": "demo-secret",
    "PHOENIX_BYBIT_RECV_WINDOW_MS": "5000",
    "PHOENIX_HTTP_TIMEOUT_SECONDS": "10",
}


def _env(**overrides):
    d = dict(_VALID_ENV)
    d.update(overrides)
    return d


def _coin_item(**overrides):
    defaults = dict(
        coin="USDT", walletBalance="1000.5", equity="1005.25",
        unrealisedPnl="4.75", usdValue="1005.25",
    )
    defaults.update(overrides)
    return defaults


def _account_item(**overrides):
    defaults = dict(
        accountType="UNIFIED", totalEquity="1005.25", totalWalletBalance="1000.5",
        totalAvailableBalance="800.0", totalInitialMargin="200.5",
        totalMaintenanceMargin="50.25", coin=[_coin_item()],
    )
    defaults.update(overrides)
    return defaults


def _ok_body(ret_code=0, ret_msg="OK", accounts=None, time_ms=1_700_000_000_000):
    result = {"list": accounts if accounts is not None else [_account_item()]}
    return json.dumps({
        "retCode": ret_code, "retMsg": ret_msg,
        "result": result, "retExtInfo": {}, "time": time_ms,
    }).encode()


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _install_fake_urlopen(monkeypatch, *, body=None, exc=None, capture=None):
    def fake(req, timeout=None):
        if capture is not None:
            capture.append(dict(
                method=req.get_method(), url=req.full_url,
                headers={k: v for k, v in req.header_items()},
                data=req.data, timeout=timeout,
            ))
        if exc is not None:
            raise exc
        return _FakeResponse(body if body is not None else _ok_body())

    monkeypatch.setattr(urllib.request, "urlopen", fake)


def _raised(fn):
    try:
        fn()
        return None
    except Exception as e:
        return e


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_demo_wallet_balance_query import (
            query_bybit_demo_wallet_balance as f,
        )
        assert f is query_bybit_demo_wallet_balance

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "query_bybit_demo_wallet_balance")
        assert execution_gateway.query_bybit_demo_wallet_balance is query_bybit_demo_wallet_balance

    def test_in_all(self):
        assert "query_bybit_demo_wallet_balance" in execution_gateway.__all__

    def test_callable(self):
        assert callable(query_bybit_demo_wallet_balance)


class TestSignature:
    def test_exactly_one_parameter(self):
        sig = inspect.signature(query_bybit_demo_wallet_balance)
        assert len(sig.parameters) == 1

    def test_parameter_named_environ(self):
        sig = inspect.signature(query_bybit_demo_wallet_balance)
        assert "environ" in sig.parameters

    def test_parameter_is_keyword_only(self):
        sig = inspect.signature(query_bybit_demo_wallet_balance)
        assert sig.parameters["environ"].kind == inspect.Parameter.KEYWORD_ONLY

    def test_parameter_defaults_to_none(self):
        sig = inspect.signature(query_bybit_demo_wallet_balance)
        assert sig.parameters["environ"].default is None

    def test_return_annotation_is_wallet_balance_snapshot(self):
        hints = inspect.get_annotations(query_bybit_demo_wallet_balance, eval_str=True)
        assert hints.get("return") is WalletBalanceSnapshot

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            query_bybit_demo_wallet_balance(_VALID_ENV)


# ---------------------------------------------------------------------------
# 2. Éxito
# ---------------------------------------------------------------------------

class TestSuccess:
    def test_returns_wallet_balance_snapshot(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert isinstance(result, WalletBalanceSnapshot)

    def test_totals_mapped(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(accounts=[_account_item(totalEquity="42.5")]))
        result = query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert result.total_equity == Decimal("42.5")

    def test_server_time_populated_from_response(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(time_ms=1_712_345_678_901))
        result = query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert result.server_time_ms == 1_712_345_678_901

    def test_currency_balances_mapped(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(
            accounts=[_account_item(coin=[_coin_item(coin="USDT")])]
        ))
        result = query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert len(result.currency_balances) == 1
        assert result.currency_balances[0].coin == "USDT"

    def test_wallet_balance_is_decimal_not_float(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(
            accounts=[_account_item(coin=[_coin_item(walletBalance="0.015")])]
        ))
        result = query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert result.currency_balances[0].wallet_balance == Decimal("0.015")

    def test_empty_currency_list_is_success(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(accounts=[_account_item(coin=[])]))
        result = query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert result.currency_balances == ()


# ---------------------------------------------------------------------------
# 3. Credenciales inválidas / entorno inválido
# ---------------------------------------------------------------------------

class TestInvalidCredentialsAndEnvironment:
    def test_missing_api_key(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        env = {k: v for k, v in _VALID_ENV.items() if k != "PHOENIX_BYBIT_DEMO_API_KEY"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_KEY"):
            query_bybit_demo_wallet_balance(environ=env)
        assert called == []

    def test_missing_api_secret(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        env = {k: v for k, v in _VALID_ENV.items() if k != "PHOENIX_BYBIT_DEMO_API_SECRET"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_SECRET"):
            query_bybit_demo_wallet_balance(environ=env)
        assert called == []

    def test_invalid_recv_window(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_RECV_WINDOW_MS"):
            query_bybit_demo_wallet_balance(environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="abc"))
        assert called == []

    def test_invalid_timeout(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_HTTP_TIMEOUT_SECONDS"):
            query_bybit_demo_wallet_balance(environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="abc"))
        assert called == []


# ---------------------------------------------------------------------------
# 4. Fallos de red / HTTP / respuesta malformada -- todos traducidos
# ---------------------------------------------------------------------------

class TestFailuresTranslatedToInfrastructureError:
    def test_socket_timeout_translated(self, monkeypatch):
        import socket
        _install_fake_urlopen(monkeypatch, exc=socket.timeout("timed out"))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_wallet_balance(environ=_VALID_ENV)

    def test_connection_error_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, exc=urllib.error.URLError("connection refused"))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_wallet_balance(environ=_VALID_ENV)

    def test_http_error_translated(self, monkeypatch):
        http_error = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        _install_fake_urlopen(monkeypatch, exc=http_error)
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_wallet_balance(environ=_VALID_ENV)

    def test_malformed_json_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=b"{not json")
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_wallet_balance(environ=_VALID_ENV)

    def test_invalid_utf8_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=b"\xff\xfe\x00")
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_wallet_balance(environ=_VALID_ENV)

    def test_auth_error_ret_code_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_code=10003, ret_msg="API key is invalid"))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_wallet_balance(environ=_VALID_ENV)

    def test_malformed_account_item_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(accounts=[_account_item(totalEquity="abc")]))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_wallet_balance(environ=_VALID_ENV)

    def test_multiple_accounts_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(accounts=[_account_item(), _account_item()]))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_wallet_balance(environ=_VALID_ENV)

    def test_bybit_processing_error_never_crosses_public_function(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=b"{not json")
        error = _raised(lambda: query_bybit_demo_wallet_balance(environ=_VALID_ENV))
        assert not isinstance(error, BybitResponseProcessingError)
        assert isinstance(error, ExecutionInfrastructureError)


# ---------------------------------------------------------------------------
# 5. Exactamente una llamada HTTP / sin I/O adicional
# ---------------------------------------------------------------------------

class TestSingleCallAndNoExtraIO:
    def test_exactly_one_http_call(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert len(calls) == 1

    def test_no_print(self, monkeypatch, capsys):
        _install_fake_urlopen(monkeypatch)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


# ---------------------------------------------------------------------------
# 6. Endpoint correcto / método GET / cero POST / cero trading
# ---------------------------------------------------------------------------

class TestEndpointAndMethod:
    def test_url_is_wallet_balance_endpoint(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert calls[0]["url"].startswith("https://api-demo.bybit.com/v5/account/wallet-balance?")

    def test_method_is_get(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert calls[0]["method"] == "GET"

    def test_no_body_sent(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert calls[0]["data"] is None

    def test_not_the_create_order_endpoint(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert "/v5/order/create" not in calls[0]["url"]

    def test_not_the_positions_endpoint(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert "/v5/position/list" not in calls[0]["url"]

    def test_not_the_open_orders_endpoint(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert "/v5/order/realtime" not in calls[0]["url"]

    def test_query_string_is_exactly_account_type_unified(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert calls[0]["url"].endswith("?accountType=UNIFIED")

    def test_does_not_import_create_order_types(self):
        src = inspect.getsource(_module)
        assert "BybitCreateOrderOperation" not in src
        assert "BybitCreateOrderRequest" not in src
        assert "BybitCreateOrderPayloadBuilder" not in src
        assert "BybitCreateOrderResponseInterpreter" not in src

    def test_does_not_call_gateway_execute(self):
        src = inspect.getsource(_module)
        assert ".execute(" not in src
        assert "ExecutionRequest" not in src
        assert "ExecutionResult" not in src

    def test_does_not_use_bybit_execution_gateway(self):
        src = inspect.getsource(_module)
        assert "BybitExecutionGateway" not in src
        assert "BybitDemoClient" not in src

    def test_never_calls_create_order_module_functions(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        for call in calls:
            assert "order/create" not in call["url"]


# ---------------------------------------------------------------------------
# 7. Integración: transporte real, urlopen espiado
# ---------------------------------------------------------------------------

class TestRealTransportIntegration:
    """Ejercita el pipeline productivo real (bootstrap -> authenticator real
    -> BybitHeaderBuilder real -> urllib.request.Request real), espiando
    únicamente urlopen -- ningún componente intermedio se sustituye."""

    def test_get_with_authenticated_headers_and_no_post(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)

        call = calls[0]
        assert call["method"] == "GET"
        assert call["data"] is None

        headers_lower = {k.lower(): v for k, v in call["headers"].items()}
        assert set(headers_lower) == {
            "x-bapi-api-key", "x-bapi-timestamp", "x-bapi-recv-window",
            "x-bapi-sign", "content-type",
        }
        assert headers_lower["x-bapi-api-key"] == "demo-key"

    def test_signature_matches_independently_computed_hmac_over_query_string(self, monkeypatch):
        import hmac
        import hashlib
        from urllib.parse import urlsplit

        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)

        headers_lower = {k.lower(): v for k, v in calls[0]["headers"].items()}
        query_string = urlsplit(calls[0]["url"]).query
        message = (
            headers_lower["x-bapi-timestamp"]
            + headers_lower["x-bapi-api-key"]
            + headers_lower["x-bapi-recv-window"]
            + query_string
        )
        expected = hmac.new(b"demo-secret", message.encode("utf-8"), hashlib.sha256).hexdigest()
        assert headers_lower["x-bapi-sign"] == expected

    def test_recv_window_header_matches_config(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="7500"))
        headers_lower = {k.lower(): v for k, v in calls[0]["headers"].items()}
        assert headers_lower["x-bapi-recv-window"] == "7500"

    def test_timeout_passed_to_urlopen_matches_config(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="12.5"))
        assert calls[0]["timeout"] == 12.5


# ---------------------------------------------------------------------------
# 8. Seguridad -- secretos ausentes de repr/mensajes
# ---------------------------------------------------------------------------

class TestSecurity:
    _MARKER = "ZZSUPERSECRETWALLETBALANCE9999"

    def test_marker_absent_from_result_repr(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = query_bybit_demo_wallet_balance(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        )
        assert self._MARKER not in repr(result)

    def test_marker_absent_from_missing_variable_error(self):
        env = {"PHOENIX_BYBIT_DEMO_API_SECRET": self._MARKER}
        error = _raised(lambda: query_bybit_demo_wallet_balance(environ=env))
        assert error is not None
        assert self._MARKER not in str(error)

    def test_marker_absent_from_infrastructure_error_message(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_code=10003, ret_msg="invalid"))
        error = _raised(lambda: query_bybit_demo_wallet_balance(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        ))
        assert error is not None
        assert self._MARKER not in str(error)

    def test_marker_absent_from_module_source(self):
        src = inspect.getsource(_module)
        assert self._MARKER not in src

    def test_result_does_not_expose_credentials_attributes(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert not hasattr(result, "api_key")
        assert not hasattr(result, "api_secret")
        assert not hasattr(result, "signature")
        assert not hasattr(result, "headers")

    def test_no_print_in_source(self):
        src = inspect.getsource(_module)
        assert "print(" not in src

    def test_no_logging_in_source(self):
        src = inspect.getsource(_module)
        assert "logging" not in src


# ---------------------------------------------------------------------------
# 9. Dos llamadas independientes / sin cache / sin singleton
# ---------------------------------------------------------------------------

class TestTwoCallsIndependence:
    def test_two_calls_produce_distinct_results(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(accounts=[_account_item(totalEquity="1")]))
        r1 = query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        _install_fake_urlopen(monkeypatch, body=_ok_body(accounts=[_account_item(totalEquity="2")]))
        r2 = query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert r1 is not r2
        assert r1.total_equity == Decimal("1")
        assert r2.total_equity == Decimal("2")

    def test_two_calls_each_issue_their_own_http_request(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert len(calls) == 2

    def test_no_module_level_mutable_state(self):
        mutable = [
            n for n, o in vars(_module).items()
            if not n.startswith("__") and isinstance(o, (list, dict, set))
        ]
        assert mutable == []

    def test_no_cache_or_memoization_in_source(self):
        src = inspect.getsource(_module)
        assert "cache" not in src.lower()
        assert "memo" not in src.lower()

    def test_second_call_after_first_failure_still_works(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, exc=urllib.error.URLError("down"))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        _install_fake_urlopen(monkeypatch, body=_ok_body())
        result = query_bybit_demo_wallet_balance(environ=_VALID_ENV)
        assert isinstance(result, WalletBalanceSnapshot)


# ---------------------------------------------------------------------------
# 10. Superficie mínima
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_no_mainnet_reference(self):
        src = inspect.getsource(_module)
        assert "mainnet" not in src.lower()

    def test_no_testnet_reference(self):
        src = inspect.getsource(_module)
        assert "testnet" not in src.lower()

    def test_no_railway_reference(self):
        src = inspect.getsource(_module)
        assert "railway" not in src.lower()

    def test_no_cancel_order_reference(self):
        src = inspect.getsource(_module)
        assert "cancel" not in src.lower()

    def test_module_only_calls_bootstrap_not_lower_factories(self):
        src = inspect.getsource(_module)
        forbidden = [
            "create_bybit_demo_credentials(", "create_message_signer(", "create_millisecond_clock(",
            "create_bybit_recv_window_ms(", "create_bybit_authenticator(", "create_json_serializer(",
            "create_http_timeout_seconds(", "create_bybit_header_builder(",
            "create_configured_bybit_demo_wallet_balance_reader(",
        ]
        for f in forbidden:
            assert f not in src, f"{f} debe reutilizarse desde el grafo, no reconstruirse"

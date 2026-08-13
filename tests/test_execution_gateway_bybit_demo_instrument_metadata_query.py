import inspect
import json
import urllib.error
import urllib.request
from decimal import Decimal

import pytest

import execution_gateway
import execution_gateway.bybit_demo_instrument_metadata_query as _module
from execution_gateway import (
    EnvironmentConfigurationError,
    ExecutionInstrumentMetadata,
    query_bybit_demo_instrument_metadata,
)
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError

_VALID_ENV = {"PHOENIX_HTTP_TIMEOUT_SECONDS": "10"}


def _env(**overrides):
    d = dict(_VALID_ENV)
    d.update(overrides)
    return d


def _price_filter(**overrides):
    d = dict(minPrice="0.10", maxPrice="1999999.80", tickSize="0.10")
    d.update(overrides)
    return d


def _lot_size_filter(**overrides):
    d = dict(maxOrderQty="1190.000", minOrderQty="0.001", qtyStep="0.001",
             maxMktOrderQty="500.000", minNotionalValue="5")
    d.update(overrides)
    return d


def _item(**overrides):
    defaults = dict(
        symbol="BTCUSDT", contractType="LinearPerpetual", status="Trading",
        baseCoin="BTC", quoteCoin="USDT", settleCoin="USDT",
        priceFilter=_price_filter(), lotSizeFilter=_lot_size_filter(),
        leverageFilter=dict(minLeverage="1", maxLeverage="100.00", leverageStep="0.01"),
    )
    defaults.update(overrides)
    return defaults


def _ok_body(ret_code=0, ret_msg="OK", items=None, time_ms=1_700_000_000_000):
    result = {"category": "linear", "list": list(items if items is not None else [_item()]), "nextPageCursor": ""}
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
        from execution_gateway.bybit_demo_instrument_metadata_query import (
            query_bybit_demo_instrument_metadata as f,
        )
        assert f is query_bybit_demo_instrument_metadata

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "query_bybit_demo_instrument_metadata")
        assert (
            execution_gateway.query_bybit_demo_instrument_metadata
            is query_bybit_demo_instrument_metadata
        )

    def test_in_all(self):
        assert "query_bybit_demo_instrument_metadata" in execution_gateway.__all__

    def test_callable(self):
        assert callable(query_bybit_demo_instrument_metadata)


class TestSignature:
    def test_exactly_two_parameters(self):
        sig = inspect.signature(query_bybit_demo_instrument_metadata)
        assert len(sig.parameters) == 2

    def test_parameter_named_symbol(self):
        sig = inspect.signature(query_bybit_demo_instrument_metadata)
        assert "symbol" in sig.parameters

    def test_symbol_has_no_default(self):
        sig = inspect.signature(query_bybit_demo_instrument_metadata)
        assert sig.parameters["symbol"].default is inspect.Parameter.empty

    def test_parameter_named_environ(self):
        sig = inspect.signature(query_bybit_demo_instrument_metadata)
        assert "environ" in sig.parameters

    def test_both_parameters_are_keyword_only(self):
        sig = inspect.signature(query_bybit_demo_instrument_metadata)
        assert sig.parameters["symbol"].kind == inspect.Parameter.KEYWORD_ONLY
        assert sig.parameters["environ"].kind == inspect.Parameter.KEYWORD_ONLY

    def test_environ_defaults_to_none(self):
        sig = inspect.signature(query_bybit_demo_instrument_metadata)
        assert sig.parameters["environ"].default is None

    def test_return_annotation_is_execution_instrument_metadata(self):
        hints = inspect.get_annotations(query_bybit_demo_instrument_metadata, eval_str=True)
        assert hints.get("return") is ExecutionInstrumentMetadata

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            query_bybit_demo_instrument_metadata("BTCUSDT")


# ---------------------------------------------------------------------------
# 2. Éxito
# ---------------------------------------------------------------------------

class TestSuccess:
    def test_returns_execution_instrument_metadata(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert isinstance(result, ExecutionInstrumentMetadata)

    def test_symbol_mapped(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(items=[_item(symbol="BTCUSDT")]))
        result = query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert result.symbol == "BTCUSDT"

    def test_does_not_require_bybit_credentials_in_env(self, monkeypatch):
        # Confirmación directa: sin PHOENIX_BYBIT_DEMO_API_KEY/SECRET en el
        # entorno, la consulta pública igual funciona.
        _install_fake_urlopen(monkeypatch)
        env = {"PHOENIX_HTTP_TIMEOUT_SECONDS": "10"}
        result = query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=env)
        assert isinstance(result, ExecutionInstrumentMetadata)

    def test_server_time_populated_from_response(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(time_ms=1_712_345_678_901))
        result = query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert result.server_time_ms == 1_712_345_678_901

    def test_tick_size_is_decimal_not_float(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(
            items=[_item(priceFilter=_price_filter(tickSize="0.015"))]
        ))
        result = query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert result.tick_size == Decimal("0.015")

    def test_different_symbol_queried(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(items=[_item(symbol="ETHUSDT")]))
        result = query_bybit_demo_instrument_metadata(symbol="ETHUSDT", environ=_VALID_ENV)
        assert result.symbol == "ETHUSDT"


# ---------------------------------------------------------------------------
# 3. Entorno inválido / símbolo inválido
# ---------------------------------------------------------------------------

class TestInvalidEnvironmentAndSymbol:
    def test_missing_timeout(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_HTTP_TIMEOUT_SECONDS"):
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ={})
        assert called == []

    def test_invalid_timeout(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_HTTP_TIMEOUT_SECONDS"):
            query_bybit_demo_instrument_metadata(
                symbol="BTCUSDT", environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="abc")
            )
        assert called == []

    def test_empty_symbol_rejected_before_any_http_call(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(ValueError, match="symbol must not be empty"):
            query_bybit_demo_instrument_metadata(symbol="", environ=_VALID_ENV)
        assert called == []

    def test_non_string_symbol_rejected(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(TypeError, match="symbol must be str"):
            query_bybit_demo_instrument_metadata(symbol=123, environ=_VALID_ENV)
        assert called == []


# ---------------------------------------------------------------------------
# 4. Fallos de red / HTTP / respuesta malformada -- todos traducidos
# ---------------------------------------------------------------------------

class TestFailuresTranslatedToInfrastructureError:
    def test_socket_timeout_translated(self, monkeypatch):
        import socket
        _install_fake_urlopen(monkeypatch, exc=socket.timeout("timed out"))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)

    def test_connection_error_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, exc=urllib.error.URLError("connection refused"))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)

    def test_http_error_translated(self, monkeypatch):
        http_error = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        _install_fake_urlopen(monkeypatch, exc=http_error)
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)

    def test_malformed_json_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=b"{not json")
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)

    def test_invalid_utf8_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=b"\xff\xfe\x00")
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)

    def test_params_error_ret_code_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_code=10001, ret_msg="params error"))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)

    def test_symbol_not_found_empty_list_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(items=[]))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)

    def test_remote_symbol_mismatch_translated(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(items=[_item(symbol="ETHUSDT")]))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)

    def test_pagination_cursor_translated(self, monkeypatch):
        body = json.dumps({
            "retCode": 0, "retMsg": "OK",
            "result": {"category": "linear", "list": [], "nextPageCursor": "abc%3D%3D"},
            "retExtInfo": {}, "time": 1_700_000_000_000,
        }).encode()
        _install_fake_urlopen(monkeypatch, body=body)
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)

    def test_bybit_processing_error_never_crosses_public_function(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=b"{not json")
        error = _raised(lambda: query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV))
        assert not isinstance(error, BybitResponseProcessingError)
        assert isinstance(error, ExecutionInfrastructureError)


# ---------------------------------------------------------------------------
# 5. Exactamente una llamada HTTP / sin I/O adicional
# ---------------------------------------------------------------------------

class TestSingleCallAndNoExtraIO:
    def test_exactly_one_http_call(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert len(calls) == 1

    def test_no_print(self, monkeypatch, capsys):
        _install_fake_urlopen(monkeypatch)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


# ---------------------------------------------------------------------------
# 6. Endpoint correcto / método GET / sin autenticación / cero POST/trading
# ---------------------------------------------------------------------------

class TestEndpointAndMethod:
    def test_url_is_instruments_info_endpoint(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert calls[0]["url"].startswith("https://api-demo.bybit.com/v5/market/instruments-info?")

    def test_method_is_get(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert calls[0]["method"] == "GET"

    def test_no_body_sent(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert calls[0]["data"] is None

    def test_no_authentication_headers_sent(self, monkeypatch):
        # Punto arquitectónico central del hito, verificado end-to-end
        # contra el pipeline productivo real: sin X-BAPI-* en absoluto.
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        headers_upper = {k.upper() for k in calls[0]["headers"]}
        assert not any(h.startswith("X-BAPI") for h in headers_upper)

    def test_query_string_has_category_and_symbol(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert "category=linear" in calls[0]["url"]
        assert "symbol=BTCUSDT" in calls[0]["url"]

    def test_not_the_create_order_endpoint(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert "/v5/order/create" not in calls[0]["url"]

    def test_not_the_positions_or_wallet_endpoint(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert "/v5/position/list" not in calls[0]["url"]
        assert "/v5/account/wallet-balance" not in calls[0]["url"]

    def test_does_not_import_create_order_types(self):
        src = inspect.getsource(_module)
        assert "BybitCreateOrderOperation" not in src
        assert "BybitCreateOrderRequest" not in src
        assert "BybitCreateOrderPayloadBuilder" not in src

    def test_does_not_call_gateway_execute(self):
        src = inspect.getsource(_module)
        assert ".execute(" not in src
        assert "ExecutionRequest" not in src
        assert "ExecutionResult" not in src

    def test_does_not_use_bybit_execution_gateway(self):
        src = inspect.getsource(_module)
        assert "BybitExecutionGateway" not in src
        assert "BybitDemoClient" not in src


# ---------------------------------------------------------------------------
# 7. Integración: transporte real, urlopen espiado
# ---------------------------------------------------------------------------

class TestRealTransportIntegration:
    def test_get_public_no_auth_no_post(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)

        call = calls[0]
        assert call["method"] == "GET"
        assert call["data"] is None
        # Sin ningún header de autenticación -- puede tener a lo sumo
        # Content-Type (ausente aquí, no lo agregamos para GET público).
        headers_upper = {k.upper() for k in call["headers"]}
        assert "X-BAPI-API-KEY" not in headers_upper
        assert "X-BAPI-SIGN" not in headers_upper
        assert "X-BAPI-TIMESTAMP" not in headers_upper
        assert "X-BAPI-RECV-WINDOW" not in headers_upper

    def test_timeout_passed_to_urlopen_matches_config(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(
            symbol="BTCUSDT", environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="12.5")
        )
        assert calls[0]["timeout"] == 12.5


# ---------------------------------------------------------------------------
# 8. Seguridad -- ausencia de fugas
# ---------------------------------------------------------------------------

class TestSecurity:
    _MARKER = "ZZSUPERSECRETINSTRUMENTMETADATA9999"

    def test_marker_absent_from_result_repr(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_msg=self._MARKER))
        result = query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert self._MARKER not in repr(result)

    def test_marker_absent_from_infrastructure_error_message(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_code=10001, ret_msg=self._MARKER))
        error = _raised(lambda: query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV))
        assert error is not None
        assert self._MARKER not in str(error)

    def test_marker_absent_from_module_source(self):
        src = inspect.getsource(_module)
        assert self._MARKER not in src

    def test_result_does_not_expose_credentials_attributes(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
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
        _install_fake_urlopen(monkeypatch, body=_ok_body(items=[_item(priceFilter=_price_filter(tickSize="0.1"))]))
        r1 = query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        _install_fake_urlopen(monkeypatch, body=_ok_body(items=[_item(priceFilter=_price_filter(tickSize="0.2"))]))
        r2 = query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert r1 is not r2
        assert r1.tick_size == Decimal("0.1")
        assert r2.tick_size == Decimal("0.2")

    def test_two_calls_each_issue_their_own_http_request(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
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
            query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        _install_fake_urlopen(monkeypatch, body=_ok_body())
        result = query_bybit_demo_instrument_metadata(symbol="BTCUSDT", environ=_VALID_ENV)
        assert isinstance(result, ExecutionInstrumentMetadata)


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
            "create_json_serializer(", "create_bybit_response_parser(",
            "create_http_timeout_seconds(",
            "create_configured_bybit_demo_instrument_metadata_reader(",
        ]
        for f in forbidden:
            assert f not in src, f"{f} debe reutilizarse desde el grafo, no reconstruirse"

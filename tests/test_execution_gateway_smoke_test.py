import inspect
import json
import urllib.error
import urllib.request

import pytest

import execution_gateway
import execution_gateway.bybit_demo_connectivity_smoke_test as _module
from execution_gateway import (
    EnvironmentConfigurationError,
    SmokeTestResult,
    smoke_test_bybit_demo_connection,
)
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError

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


def _ok_body(ret_code=0, ret_msg="OK", result=None, time_ms=1_700_000_000_000):
    return json.dumps({
        "retCode": ret_code, "retMsg": ret_msg,
        "result": result if result is not None else {},
        "retExtInfo": {}, "time": time_ms,
    }).encode()


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body
        self.closed = False

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.closed = True
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
        from execution_gateway.bybit_demo_connectivity_smoke_test import (
            smoke_test_bybit_demo_connection as f,
        )
        assert f is smoke_test_bybit_demo_connection

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "smoke_test_bybit_demo_connection")
        assert execution_gateway.smoke_test_bybit_demo_connection is smoke_test_bybit_demo_connection

    def test_included_in_all(self):
        assert "smoke_test_bybit_demo_connection" in execution_gateway.__all__

    def test_result_importable_directly(self):
        from execution_gateway.smoke_test_result import SmokeTestResult as R
        assert R is SmokeTestResult

    def test_result_importable_from_package(self):
        assert hasattr(execution_gateway, "SmokeTestResult")
        assert execution_gateway.SmokeTestResult is SmokeTestResult

    def test_result_included_in_all(self):
        assert "SmokeTestResult" in execution_gateway.__all__

    def test_callable(self):
        assert callable(smoke_test_bybit_demo_connection)


class TestSignature:
    def test_exactly_one_parameter(self):
        sig = inspect.signature(smoke_test_bybit_demo_connection)
        assert len(sig.parameters) == 1

    def test_parameter_named_environ(self):
        sig = inspect.signature(smoke_test_bybit_demo_connection)
        assert "environ" in sig.parameters

    def test_parameter_is_keyword_only(self):
        sig = inspect.signature(smoke_test_bybit_demo_connection)
        assert sig.parameters["environ"].kind == inspect.Parameter.KEYWORD_ONLY

    def test_parameter_defaults_to_none(self):
        sig = inspect.signature(smoke_test_bybit_demo_connection)
        assert sig.parameters["environ"].default is None

    def test_return_annotation_is_smoke_test_result(self):
        hints = inspect.get_annotations(smoke_test_bybit_demo_connection, eval_str=True)
        assert hints.get("return") is SmokeTestResult

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            smoke_test_bybit_demo_connection(_VALID_ENV)

    def test_no_unknown_kwargs_accepted(self):
        with pytest.raises(TypeError):
            smoke_test_bybit_demo_connection(environ=_VALID_ENV, extra=True)


class TestSmokeTestResultContract:
    def test_is_frozen_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(SmokeTestResult)
        assert SmokeTestResult.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        import dataclasses
        names = [f.name for f in dataclasses.fields(SmokeTestResult)]
        assert names == ["success", "endpoint", "environment", "server_time", "account_type"]

    def test_only_safe_public_attributes(self):
        result = SmokeTestResult(success=True, endpoint="/v5/user/query-api", environment="demo")
        public = {k for k in vars(result) if not k.startswith("_")}
        assert public == {"success", "endpoint", "environment", "server_time", "account_type"}

    def test_rejects_api_key_like_extra_field(self):
        with pytest.raises(TypeError):
            SmokeTestResult(
                success=True, endpoint="/x", environment="demo", api_key="leak",
            )

    def test_success_must_be_bool(self):
        with pytest.raises(TypeError, match="success must be bool"):
            SmokeTestResult(success=1, endpoint="/x", environment="demo")

    def test_endpoint_must_be_non_empty(self):
        with pytest.raises(ValueError, match="endpoint must not be empty"):
            SmokeTestResult(success=True, endpoint="", environment="demo")

    def test_environment_must_be_non_empty(self):
        with pytest.raises(ValueError, match="environment must not be empty"):
            SmokeTestResult(success=True, endpoint="/x", environment="")

    def test_server_time_optional(self):
        result = SmokeTestResult(success=True, endpoint="/x", environment="demo")
        assert result.server_time is None

    def test_account_type_optional(self):
        result = SmokeTestResult(success=True, endpoint="/x", environment="demo")
        assert result.account_type is None

    def test_server_time_rejects_bool(self):
        with pytest.raises(TypeError, match="server_time must be int or None"):
            SmokeTestResult(success=True, endpoint="/x", environment="demo", server_time=True)

    def test_server_time_rejects_negative(self):
        with pytest.raises(ValueError, match="server_time must be >= 0"):
            SmokeTestResult(success=True, endpoint="/x", environment="demo", server_time=-1)


# ---------------------------------------------------------------------------
# 2. Éxito
# ---------------------------------------------------------------------------

class TestSuccess:
    def test_returns_smoke_test_result(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert isinstance(result, SmokeTestResult)

    def test_success_true(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert result.success is True

    def test_environment_is_demo(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert result.environment == "demo"

    def test_endpoint_matches_query_api(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert result.endpoint == "/v5/user/query-api"

    def test_server_time_populated_from_response(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(time_ms=1_712_345_678_901))
        result = smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert result.server_time == 1_712_345_678_901


# ---------------------------------------------------------------------------
# 3. Credenciales inválidas / entorno inválido
# ---------------------------------------------------------------------------

class TestInvalidCredentialsAndEnvironment:
    def test_missing_api_key(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        env = {k: v for k, v in _VALID_ENV.items() if k != "PHOENIX_BYBIT_DEMO_API_KEY"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_KEY"):
            smoke_test_bybit_demo_connection(environ=env)
        assert called == []

    def test_missing_api_secret(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        env = {k: v for k, v in _VALID_ENV.items() if k != "PHOENIX_BYBIT_DEMO_API_SECRET"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_SECRET"):
            smoke_test_bybit_demo_connection(environ=env)
        assert called == []

    def test_empty_api_key_rejected_by_config(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(ValueError, match="api_key must not be empty"):
            smoke_test_bybit_demo_connection(environ=_env(PHOENIX_BYBIT_DEMO_API_KEY=""))
        assert called == []

    def test_invalid_recv_window(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_RECV_WINDOW_MS"):
            smoke_test_bybit_demo_connection(environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="abc"))
        assert called == []

    def test_invalid_timeout(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_HTTP_TIMEOUT_SECONDS"):
            smoke_test_bybit_demo_connection(environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="abc"))
        assert called == []

    def test_timeout_nan(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(ValueError, match="finite"):
            smoke_test_bybit_demo_connection(environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="nan"))
        assert called == []


# ---------------------------------------------------------------------------
# 4. Timeout / error de red / error HTTP
# ---------------------------------------------------------------------------

class TestNetworkFailures:
    def test_socket_timeout_propagates(self, monkeypatch):
        import socket
        _install_fake_urlopen(monkeypatch, exc=socket.timeout("timed out"))
        with pytest.raises(socket.timeout):
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)

    def test_connection_error_propagates(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, exc=urllib.error.URLError("connection refused"))
        with pytest.raises(urllib.error.URLError):
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)

    def test_http_error_propagates(self, monkeypatch):
        http_error = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        _install_fake_urlopen(monkeypatch, exc=http_error)
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert exc_info.value.code == 403

    def test_malformed_json_translated_to_processing_error(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=b"{not json")
        with pytest.raises(BybitResponseProcessingError):
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)

    def test_invalid_utf8_translated_to_processing_error(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=b"\xff\xfe\x00")
        with pytest.raises(BybitResponseProcessingError):
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)

    def test_missing_schema_fields_translated_to_processing_error(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=json.dumps({"retCode": 0}).encode())
        with pytest.raises(BybitResponseProcessingError):
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)


# ---------------------------------------------------------------------------
# 5. Error de autenticación (ret_code != 0)
# ---------------------------------------------------------------------------

class TestAuthenticationError:
    def test_invalid_api_key_ret_code(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_code=10003, ret_msg="API key is invalid"))
        with pytest.raises(BybitApiError) as exc_info:
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert exc_info.value.ret_code == 10003

    def test_invalid_signature_ret_code(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_code=10004, ret_msg="error sign"))
        with pytest.raises(BybitApiError) as exc_info:
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert exc_info.value.ret_code == 10004

    def test_expired_timestamp_ret_code(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_code=10002, ret_msg="invalid timestamp"))
        with pytest.raises(BybitApiError) as exc_info:
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert exc_info.value.ret_code == 10002

    def test_ret_msg_preserved(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_code=10003, ret_msg="API key is invalid."))
        with pytest.raises(BybitApiError) as exc_info:
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert exc_info.value.ret_msg == "API key is invalid."

    def test_does_not_return_result_on_api_error(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_code=10003, ret_msg="x"))
        result = _raised(lambda: smoke_test_bybit_demo_connection(environ=_VALID_ENV))
        assert isinstance(result, BybitApiError)


# ---------------------------------------------------------------------------
# 6. Ausencia de I/O adicional / exactamente una llamada HTTP
# ---------------------------------------------------------------------------

class TestSingleCallAndNoExtraIO:
    def test_exactly_one_http_call(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert len(calls) == 1

    def test_no_file_reads(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        calls = []
        original_open = open

        def spy_open(*args, **kwargs):
            calls.append(args)
            return original_open(*args, **kwargs)

        import builtins
        monkeypatch.setattr(builtins, "open", spy_open)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert calls == []

    def test_no_print(self, monkeypatch, capsys):
        _install_fake_urlopen(monkeypatch)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_no_dns_resolution_beyond_urlopen(self, monkeypatch):
        # urlopen ya está reemplazado; ninguna otra ruta de red debe activarse.
        import socket
        calls = []
        original = socket.getaddrinfo

        def patched(*args, **kwargs):
            calls.append(args)
            return original(*args, **kwargs)

        monkeypatch.setattr(socket, "getaddrinfo", patched)
        _install_fake_urlopen(monkeypatch)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert calls == []


# ---------------------------------------------------------------------------
# 7. Endpoint correcto / método GET / cero POST / cero trading
# ---------------------------------------------------------------------------

class TestEndpointAndMethod:
    def test_url_is_exact(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert calls[0]["url"] == "https://api-demo.bybit.com/v5/user/query-api"

    def test_method_is_get(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert calls[0]["method"] == "GET"

    def test_no_body_sent(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert calls[0]["data"] is None

    def test_not_the_create_order_endpoint(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert "/v5/order/create" not in calls[0]["url"]

    def test_does_not_import_create_order_types(self):
        # `_create_order_operation` aparece sólo como travesía de atributos
        # privados del grafo ya construido (nombre heredado del gateway,
        # que hoy sólo soporta creación de órdenes) -- el módulo no importa
        # ni construye ningún tipo de creación de órdenes.
        src = inspect.getsource(_module)
        assert "BybitCreateOrderOperation" not in src
        assert "BybitCreateOrderRequest" not in src
        assert "BybitCreateOrderPayloadBuilder" not in src
        assert "BybitCreateOrderResponseInterpreter" not in src

    def test_does_not_import_from_create_order_modules(self):
        imported_modules = {getattr(v, "__module__", None) for v in vars(_module).values()}
        assert not any(m and "bybit_create_order" in m for m in imported_modules if m)

    def test_does_not_call_gateway_execute(self):
        src = inspect.getsource(_module)
        assert ".execute(" not in src
        assert "ExecutionRequest" not in src
        assert "ExecutionResult" not in src

    def test_does_not_reference_dummy_order(self):
        src = inspect.getsource(_module)
        assert "dummy" not in src.lower()

    def test_endpoint_constant_method_is_get(self):
        assert _module._SMOKE_TEST_ENDPOINT.method == "GET"

    def test_endpoint_constant_path(self):
        assert _module._SMOKE_TEST_ENDPOINT.path == "/v5/user/query-api"


# ---------------------------------------------------------------------------
# 8. Integración: transporte real, urlopen espiado
# ---------------------------------------------------------------------------

class TestRealTransportIntegration:
    """Ejercita el pipeline productivo real (bootstrap -> authenticator real
    -> BybitHeaderBuilder real -> urllib.request.Request real), espiando
    únicamente urlopen -- ningún componente intermedio se sustituye."""

    def test_get_with_authenticated_headers_and_no_post(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)

        call = calls[0]
        assert call["method"] == "GET"
        assert call["url"] == "https://api-demo.bybit.com/v5/user/query-api"
        assert call["data"] is None

        headers_lower = {k.lower(): v for k, v in call["headers"].items()}
        assert set(headers_lower) == {
            "x-bapi-api-key", "x-bapi-timestamp", "x-bapi-recv-window",
            "x-bapi-sign", "content-type",
        }
        assert headers_lower["x-bapi-api-key"] == "demo-key"

    def test_signature_matches_independently_computed_hmac(self, monkeypatch):
        import hmac
        import hashlib

        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)

        headers_lower = {k.lower(): v for k, v in calls[0]["headers"].items()}
        message = (
            headers_lower["x-bapi-timestamp"]
            + headers_lower["x-bapi-api-key"]
            + headers_lower["x-bapi-recv-window"]
        )
        expected = hmac.new(b"demo-secret", message.encode("utf-8"), hashlib.sha256).hexdigest()
        assert headers_lower["x-bapi-sign"] == expected

    def test_recv_window_header_matches_config(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="7500"))
        headers_lower = {k.lower(): v for k, v in calls[0]["headers"].items()}
        assert headers_lower["x-bapi-recv-window"] == "7500"

    def test_timeout_passed_to_urlopen_matches_config(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="12.5"))
        assert calls[0]["timeout"] == 12.5


# ---------------------------------------------------------------------------
# 9. Seguridad — secretos ausentes de repr/mensajes
# ---------------------------------------------------------------------------

class TestSecurity:
    _MARKER = "ZZSUPERSECRETSMOKE9999"

    def test_marker_absent_from_result_repr(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = smoke_test_bybit_demo_connection(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        )
        assert self._MARKER not in repr(result)

    def test_marker_absent_from_result_str(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = smoke_test_bybit_demo_connection(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        )
        assert self._MARKER not in str(result)

    def test_marker_absent_from_missing_variable_error(self):
        env = {"PHOENIX_BYBIT_DEMO_API_SECRET": self._MARKER}
        error = _raised(lambda: smoke_test_bybit_demo_connection(environ=env))
        assert error is not None
        assert self._MARKER not in str(error)

    def test_marker_absent_from_numeric_conversion_error(self):
        env = _env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER, PHOENIX_BYBIT_RECV_WINDOW_MS="abc")
        error = _raised(lambda: smoke_test_bybit_demo_connection(environ=env))
        assert error is not None
        assert self._MARKER not in str(error)

    def test_marker_absent_from_api_error_message(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(ret_code=10003, ret_msg="invalid"))
        error = _raised(lambda: smoke_test_bybit_demo_connection(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        ))
        assert error is not None
        assert self._MARKER not in str(error)

    def test_marker_absent_from_module_source(self):
        src = inspect.getsource(_module)
        assert self._MARKER not in src

    def test_result_does_not_expose_credentials_attributes(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        result = smoke_test_bybit_demo_connection(environ=_VALID_ENV)
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
# 10. Dos llamadas independientes / sin cache / sin singleton
# ---------------------------------------------------------------------------

class TestTwoCallsIndependence:
    def test_two_calls_produce_distinct_results(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=_ok_body(time_ms=1_000))
        r1 = smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        _install_fake_urlopen(monkeypatch, body=_ok_body(time_ms=2_000))
        r2 = smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert r1 is not r2
        assert r1.server_time == 1_000
        assert r2.server_time == 2_000

    def test_two_calls_each_issue_their_own_http_request(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert len(calls) == 2

    def test_different_environs_produce_different_signatures(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        smoke_test_bybit_demo_connection(environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET="secret-one"))
        smoke_test_bybit_demo_connection(environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET="secret-two"))
        sig1 = {k.lower(): v for k, v in calls[0]["headers"].items()}["x-bapi-sign"]
        sig2 = {k.lower(): v for k, v in calls[1]["headers"].items()}["x-bapi-sign"]
        assert sig1 != sig2

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

    def test_no_singleton_in_source(self):
        src = inspect.getsource(_module)
        assert "singleton" not in src.lower()
        assert "instance" not in src.lower()

    def test_second_call_after_first_failure_still_works(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, exc=urllib.error.URLError("down"))
        with pytest.raises(urllib.error.URLError):
            smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        _install_fake_urlopen(monkeypatch, body=_ok_body())
        result = smoke_test_bybit_demo_connection(environ=_VALID_ENV)
        assert result.success is True


# ---------------------------------------------------------------------------
# 11. Superficie mínima
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_no_mainnet_reference(self):
        src = inspect.getsource(_module)
        assert "mainnet" not in src.lower()

    def test_no_testnet_reference(self):
        src = inspect.getsource(_module)
        assert "testnet" not in src.lower()

    def test_no_dotenv_reference(self):
        src = inspect.getsource(_module)
        assert "dotenv" not in src.lower()

    def test_no_railway_reference(self):
        src = inspect.getsource(_module)
        assert "railway" not in src.lower()

    def test_no_cancel_order_reference(self):
        src = inspect.getsource(_module)
        assert "cancel" not in src.lower()

    def test_no_position_modification_reference(self):
        src = inspect.getsource(_module)
        assert "position" not in src.lower()

    def test_module_only_calls_bootstrap_not_lower_factories(self):
        src = inspect.getsource(_module)
        forbidden = [
            "create_bybit_demo_credentials(", "create_message_signer(", "create_millisecond_clock(",
            "create_bybit_recv_window_ms(", "create_bybit_authenticator(", "create_json_serializer(",
            "create_http_transport(", "create_http_timeout_seconds(", "create_http_request_executor(",
            "create_bybit_private_request_sender(", "create_bybit_private_api(",
            "create_configured_bybit_demo_execution_gateway(",
        ]
        for f in forbidden:
            assert f not in src, f"{f} debe reutilizarse desde el grafo, no reconstruirse"

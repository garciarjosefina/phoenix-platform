import inspect
import math

import pytest

import execution_gateway
import execution_gateway.bybit_demo_execution_config_env_loader as _module
from execution_gateway import (
    BybitDemoExecutionConfig,
    EnvironmentConfigurationError,
    load_bybit_demo_execution_config_from_env,
)
from execution_gateway.bybit_demo_execution_config_env_loader import (
    _API_KEY_VAR,
    _API_SECRET_VAR,
    _RECV_WINDOW_MS_VAR,
    _TIMEOUT_SECONDS_VAR,
)

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


def _without(*names):
    return {k: v for k, v in _VALID_ENV.items() if k not in names}


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
        from execution_gateway.bybit_demo_execution_config_env_loader import (
            load_bybit_demo_execution_config_from_env as f,
        )
        assert f is load_bybit_demo_execution_config_from_env

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "load_bybit_demo_execution_config_from_env")
        assert (
            execution_gateway.load_bybit_demo_execution_config_from_env
            is load_bybit_demo_execution_config_from_env
        )

    def test_included_in_all(self):
        assert "load_bybit_demo_execution_config_from_env" in execution_gateway.__all__

    def test_exception_importable_directly(self):
        from execution_gateway.environment_configuration_error import (
            EnvironmentConfigurationError as E,
        )
        assert E is EnvironmentConfigurationError

    def test_exception_importable_from_package(self):
        assert hasattr(execution_gateway, "EnvironmentConfigurationError")
        assert execution_gateway.EnvironmentConfigurationError is EnvironmentConfigurationError

    def test_exception_included_in_all(self):
        assert "EnvironmentConfigurationError" in execution_gateway.__all__

    def test_callable(self):
        assert callable(load_bybit_demo_execution_config_from_env)

    def test_no_private_helpers_exported(self):
        assert "_read_required" not in execution_gateway.__all__
        assert "_read_int" not in execution_gateway.__all__
        assert "_read_float" not in execution_gateway.__all__


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_exactly_one_parameter(self):
        sig = inspect.signature(load_bybit_demo_execution_config_from_env)
        assert len(sig.parameters) == 1

    def test_parameter_named_environ(self):
        sig = inspect.signature(load_bybit_demo_execution_config_from_env)
        assert "environ" in sig.parameters

    def test_parameter_is_keyword_only(self):
        sig = inspect.signature(load_bybit_demo_execution_config_from_env)
        assert sig.parameters["environ"].kind == inspect.Parameter.KEYWORD_ONLY

    def test_parameter_defaults_to_none(self):
        sig = inspect.signature(load_bybit_demo_execution_config_from_env)
        assert sig.parameters["environ"].default is None

    def test_return_annotation_is_config_type(self):
        hints = inspect.get_annotations(load_bybit_demo_execution_config_from_env, eval_str=True)
        assert hints.get("return") is BybitDemoExecutionConfig

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            load_bybit_demo_execution_config_from_env(_VALID_ENV)

    def test_no_unknown_kwargs_accepted(self):
        with pytest.raises(TypeError):
            load_bybit_demo_execution_config_from_env(environ=_VALID_ENV, extra=True)

    def test_environ_wrong_type_raises_type_error(self):
        with pytest.raises(TypeError, match="environ must be a Mapping"):
            load_bybit_demo_execution_config_from_env(environ=["not", "a", "mapping"])

    def test_environ_string_raises_type_error(self):
        with pytest.raises(TypeError, match="environ must be a Mapping"):
            load_bybit_demo_execution_config_from_env(environ="not-a-mapping")


# ---------------------------------------------------------------------------
# 3. Caso válido — mapping explícito
# ---------------------------------------------------------------------------

class TestValidConstruction:
    def test_returns_bybit_demo_execution_config(self):
        config = load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert isinstance(config, BybitDemoExecutionConfig)

    def test_api_key_exact(self):
        config = load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert config.api_key == "demo-key"

    def test_api_secret_exact(self):
        config = load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert config.api_secret == "demo-secret"

    def test_recv_window_ms_converted_to_int(self):
        config = load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert config.recv_window_ms == 5000
        assert type(config.recv_window_ms) is int

    def test_timeout_seconds_is_float_ten(self):
        config = load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert config.timeout_seconds == 10.0
        assert type(config.timeout_seconds) is float

    def test_secret_hidden_in_repr(self):
        config = load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert "demo-secret" not in repr(config)

    def test_secret_hidden_in_str(self):
        config = load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert "demo-secret" not in str(config)

    def test_mapping_not_mutated(self):
        snapshot = dict(_VALID_ENV)
        load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert _VALID_ENV == snapshot


# ---------------------------------------------------------------------------
# 4. Timeout decimal
# ---------------------------------------------------------------------------

class TestDecimalTimeout:
    def test_decimal_timeout_value(self):
        config = load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="7.5")
        )
        assert config.timeout_seconds == 7.5

    def test_decimal_timeout_type(self):
        config = load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="7.5")
        )
        assert type(config.timeout_seconds) is float

    def test_decimal_timeout_no_rounding(self):
        config = load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="7.53219")
        )
        assert config.timeout_seconds == pytest.approx(7.53219)


# ---------------------------------------------------------------------------
# 5. Variables ausentes — individualmente
# ---------------------------------------------------------------------------

class TestMissingVariables:
    def test_missing_api_key(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(environ=_without(_API_KEY_VAR))
        assert str(exc_info.value) == "Missing required environment variable: PHOENIX_BYBIT_DEMO_API_KEY"

    def test_missing_api_secret(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(environ=_without(_API_SECRET_VAR))
        assert str(exc_info.value) == "Missing required environment variable: PHOENIX_BYBIT_DEMO_API_SECRET"

    def test_missing_recv_window(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(environ=_without(_RECV_WINDOW_MS_VAR))
        assert str(exc_info.value) == "Missing required environment variable: PHOENIX_BYBIT_RECV_WINDOW_MS"

    def test_missing_timeout(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(environ=_without(_TIMEOUT_SECONDS_VAR))
        assert str(exc_info.value) == "Missing required environment variable: PHOENIX_HTTP_TIMEOUT_SECONDS"

    def test_missing_message_names_only_that_variable(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(environ=_without(_API_SECRET_VAR))
        msg = str(exc_info.value)
        assert "PHOENIX_BYBIT_DEMO_API_SECRET" in msg
        assert "PHOENIX_BYBIT_DEMO_API_KEY" not in msg
        assert "PHOENIX_BYBIT_RECV_WINDOW_MS" not in msg
        assert "PHOENIX_HTTP_TIMEOUT_SECONDS" not in msg

    def test_missing_error_never_contains_secret_value(self):
        env = _without(_TIMEOUT_SECONDS_VAR)
        env["PHOENIX_BYBIT_DEMO_API_SECRET"] = "ZZSUPERSECRET9999"
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(environ=env)
        assert "ZZSUPERSECRET9999" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# 6. Conversión inválida
# ---------------------------------------------------------------------------

class TestInvalidConversion:
    def test_recv_window_non_numeric(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(
                environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="abc")
            )
        assert str(exc_info.value) == "Invalid integer environment variable: PHOENIX_BYBIT_RECV_WINDOW_MS"

    def test_recv_window_float_text_rejected(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(
                environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="5000.0")
            )
        assert str(exc_info.value) == "Invalid integer environment variable: PHOENIX_BYBIT_RECV_WINDOW_MS"

    def test_recv_window_conversion_error_has_cause(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(
                environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="abc")
            )
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_timeout_non_numeric(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(
                environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="abc")
            )
        assert str(exc_info.value) == "Invalid numeric environment variable: PHOENIX_HTTP_TIMEOUT_SECONDS"

    def test_timeout_empty_string(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(
                environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="")
            )
        assert str(exc_info.value) == "Invalid numeric environment variable: PHOENIX_HTTP_TIMEOUT_SECONDS"

    def test_timeout_conversion_error_has_cause(self):
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(
                environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="abc")
            )
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_timeout_nan_is_a_successful_conversion_rejected_by_config(self):
        # float("nan") no lanza ValueError: la conversión mínima tiene éxito.
        # El rechazo ocurre después, en BybitDemoExecutionConfig.
        with pytest.raises(ValueError, match="timeout_seconds must be finite") as exc_info:
            load_bybit_demo_execution_config_from_env(
                environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="nan")
            )
        assert not isinstance(exc_info.value, EnvironmentConfigurationError)

    def test_timeout_positive_infinity_rejected_by_config(self):
        with pytest.raises(ValueError, match="timeout_seconds must be finite") as exc_info:
            load_bybit_demo_execution_config_from_env(
                environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="inf")
            )
        assert not isinstance(exc_info.value, EnvironmentConfigurationError)

    def test_timeout_negative_infinity_rejected_by_config(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0") as exc_info:
            load_bybit_demo_execution_config_from_env(
                environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="-inf")
            )
        assert not isinstance(exc_info.value, EnvironmentConfigurationError)


# ---------------------------------------------------------------------------
# 7. Paridad con BybitDemoExecutionConfig
# ---------------------------------------------------------------------------

class TestParityWithConfig:
    def test_valid_input_parity(self):
        loaded = load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        direct = BybitDemoExecutionConfig(
            api_key="demo-key", api_secret="demo-secret",
            recv_window_ms=5000, timeout_seconds=10.0,
        )
        assert loaded == direct

    def test_zero_recv_window_rejected_same_as_config(self):
        loader_error = _raised(lambda: load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="0")
        ))
        config_error = _raised(lambda: BybitDemoExecutionConfig(
            api_key="demo-key", api_secret="demo-secret",
            recv_window_ms=0, timeout_seconds=10.0,
        ))
        assert type(loader_error) is type(config_error)
        assert str(loader_error) == str(config_error)

    def test_negative_timeout_rejected_same_as_config(self):
        loader_error = _raised(lambda: load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="-5")
        ))
        config_error = _raised(lambda: BybitDemoExecutionConfig(
            api_key="demo-key", api_secret="demo-secret",
            recv_window_ms=5000, timeout_seconds=-5.0,
        ))
        assert type(loader_error) is type(config_error)
        assert str(loader_error) == str(config_error)

    def test_empty_api_key_rejected_same_as_config(self):
        loader_error = _raised(lambda: load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_BYBIT_DEMO_API_KEY="")
        ))
        config_error = _raised(lambda: BybitDemoExecutionConfig(
            api_key="", api_secret="demo-secret",
            recv_window_ms=5000, timeout_seconds=10.0,
        ))
        assert type(loader_error) is type(config_error)
        assert str(loader_error) == str(config_error)

    def test_whitespace_api_secret_rejected_same_as_config(self):
        loader_error = _raised(lambda: load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET="   ")
        ))
        config_error = _raised(lambda: BybitDemoExecutionConfig(
            api_key="demo-key", api_secret="   ",
            recv_window_ms=5000, timeout_seconds=10.0,
        ))
        assert type(loader_error) is type(config_error)
        assert str(loader_error) == str(config_error)


# ---------------------------------------------------------------------------
# 8. Orden de lectura
# ---------------------------------------------------------------------------

class TestReadOrder:
    def test_all_missing_raises_api_key_error_first(self):
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_KEY"):
            load_bybit_demo_execution_config_from_env(environ={})

    def test_key_present_secret_missing_raises_secret_error(self):
        env = {"PHOENIX_BYBIT_DEMO_API_KEY": "k"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_SECRET"):
            load_bybit_demo_execution_config_from_env(environ=env)

    def test_credentials_present_recv_missing_raises_recv_error(self):
        env = {"PHOENIX_BYBIT_DEMO_API_KEY": "k", "PHOENIX_BYBIT_DEMO_API_SECRET": "s"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_RECV_WINDOW_MS"):
            load_bybit_demo_execution_config_from_env(environ=env)

    def test_credentials_and_recv_present_timeout_missing_raises_timeout_error(self):
        env = {
            "PHOENIX_BYBIT_DEMO_API_KEY": "k",
            "PHOENIX_BYBIT_DEMO_API_SECRET": "s",
            "PHOENIX_BYBIT_RECV_WINDOW_MS": "5000",
        }
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_HTTP_TIMEOUT_SECONDS"):
            load_bybit_demo_execution_config_from_env(environ=env)

    def test_all_structurally_convertible_but_semantically_invalid_raises_api_key_error_first(self):
        # Las cuatro variables están presentes y son estructuralmente
        # convertibles (el loader no falla en ninguna conversión), por lo
        # que las cuatro llegan a BybitDemoExecutionConfig, cuyo propio
        # __post_init__ valida en orden api_key -> api_secret -> recv -> timeout.
        env = {
            "PHOENIX_BYBIT_DEMO_API_KEY": "",
            "PHOENIX_BYBIT_DEMO_API_SECRET": "",
            "PHOENIX_BYBIT_RECV_WINDOW_MS": "0",
            "PHOENIX_HTTP_TIMEOUT_SECONDS": "0",
        }
        with pytest.raises(ValueError, match="api_key must not be empty") as exc_info:
            load_bybit_demo_execution_config_from_env(environ=env)
        assert not isinstance(exc_info.value, EnvironmentConfigurationError)

    def test_recv_invalid_takes_precedence_over_timeout_missing(self):
        env = {
            "PHOENIX_BYBIT_DEMO_API_KEY": "k",
            "PHOENIX_BYBIT_DEMO_API_SECRET": "s",
            "PHOENIX_BYBIT_RECV_WINDOW_MS": "abc",
        }
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_RECV_WINDOW_MS"):
            load_bybit_demo_execution_config_from_env(environ=env)


# ---------------------------------------------------------------------------
# 9. Semántica del mapping explícito
# ---------------------------------------------------------------------------

class TestExplicitMappingSemantics:
    def test_does_not_consult_os_environ(self, monkeypatch):
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "env-key")
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_SECRET", "env-secret")
        monkeypatch.setenv("PHOENIX_BYBIT_RECV_WINDOW_MS", "9999")
        monkeypatch.setenv("PHOENIX_HTTP_TIMEOUT_SECONDS", "99")
        config = load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert config.api_key == "demo-key"
        assert config.recv_window_ms == 5000
        assert config.timeout_seconds == 10.0

    def test_does_not_mix_explicit_mapping_with_os_environ(self, monkeypatch):
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "env-key")
        partial = {
            "PHOENIX_BYBIT_DEMO_API_SECRET": "s",
            "PHOENIX_BYBIT_RECV_WINDOW_MS": "5000",
            "PHOENIX_HTTP_TIMEOUT_SECONDS": "10",
        }
        # Debe fallar por api_key ausente en el mapping explícito, no
        # completarlo con el valor presente en os.environ.
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_KEY"):
            load_bybit_demo_execution_config_from_env(environ=partial)

    def test_does_not_mutate_the_mapping(self):
        env = dict(_VALID_ENV)
        before = dict(env)
        load_bybit_demo_execution_config_from_env(environ=env)
        assert env == before

    def test_does_not_retain_reference_to_the_mapping(self):
        env = dict(_VALID_ENV)
        config = load_bybit_demo_execution_config_from_env(environ=env)
        env["PHOENIX_BYBIT_DEMO_API_KEY"] = "mutated-after-call"
        assert config.api_key == "demo-key"

    def test_two_calls_read_fresh_values(self):
        env = dict(_VALID_ENV)
        config1 = load_bybit_demo_execution_config_from_env(environ=env)
        env["PHOENIX_BYBIT_DEMO_API_KEY"] = "second-key"
        config2 = load_bybit_demo_execution_config_from_env(environ=env)
        assert config1.api_key == "demo-key"
        assert config2.api_key == "second-key"

    def test_two_independent_mappings_produce_independent_results(self):
        config1 = load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="1000")
        )
        config2 = load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="2000")
        )
        assert config1.recv_window_ms == 1000
        assert config2.recv_window_ms == 2000


# ---------------------------------------------------------------------------
# 10. Entorno real parcheado (environ=None)
# ---------------------------------------------------------------------------

class TestRealEnvironment:
    def test_reads_from_os_environ_when_environ_is_none(self, monkeypatch):
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "real-key")
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_SECRET", "real-secret")
        monkeypatch.setenv("PHOENIX_BYBIT_RECV_WINDOW_MS", "6000")
        monkeypatch.setenv("PHOENIX_HTTP_TIMEOUT_SECONDS", "12.5")
        config = load_bybit_demo_execution_config_from_env()
        assert config.api_key == "real-key"
        assert config.api_secret == "real-secret"
        assert config.recv_window_ms == 6000
        assert config.timeout_seconds == 12.5

    def test_missing_from_real_environment_raises(self, monkeypatch):
        monkeypatch.delenv("PHOENIX_BYBIT_DEMO_API_KEY", raising=False)
        monkeypatch.delenv("PHOENIX_BYBIT_DEMO_API_SECRET", raising=False)
        monkeypatch.delenv("PHOENIX_BYBIT_RECV_WINDOW_MS", raising=False)
        monkeypatch.delenv("PHOENIX_HTTP_TIMEOUT_SECONDS", raising=False)
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_KEY"):
            load_bybit_demo_execution_config_from_env()

    def test_each_call_rereads_os_environ(self, monkeypatch):
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "first-key")
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_SECRET", "s")
        monkeypatch.setenv("PHOENIX_BYBIT_RECV_WINDOW_MS", "5000")
        monkeypatch.setenv("PHOENIX_HTTP_TIMEOUT_SECONDS", "10")
        first = load_bybit_demo_execution_config_from_env()
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "second-key")
        second = load_bybit_demo_execution_config_from_env()
        assert first.api_key == "first-key"
        assert second.api_key == "second-key"

    def test_no_caching_of_missing_variable_error(self, monkeypatch):
        monkeypatch.delenv("PHOENIX_BYBIT_DEMO_API_KEY", raising=False)
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_SECRET", "s")
        monkeypatch.setenv("PHOENIX_BYBIT_RECV_WINDOW_MS", "5000")
        monkeypatch.setenv("PHOENIX_HTTP_TIMEOUT_SECONDS", "10")
        with pytest.raises(EnvironmentConfigurationError):
            load_bybit_demo_execution_config_from_env()
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "now-present")
        config = load_bybit_demo_execution_config_from_env()
        assert config.api_key == "now-present"


# ---------------------------------------------------------------------------
# 11. Ausencia de efectos
# ---------------------------------------------------------------------------

class TestNoSideEffects:
    def test_no_file_reads(self, monkeypatch):
        calls = []
        original_open = open

        def spy_open(*args, **kwargs):
            calls.append(args)
            return original_open(*args, **kwargs)

        import builtins
        monkeypatch.setattr(builtins, "open", spy_open)
        load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert calls == []

    def test_no_socket_connections(self):
        import socket
        calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        finally:
            socket.socket.connect = original
        assert calls == []

    def test_no_urlopen(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert called == []

    def test_no_clock_read(self, monkeypatch):
        import time
        calls = []
        original_ns = time.time_ns

        def spy_ns():
            calls.append(True)
            return original_ns()

        monkeypatch.setattr(time, "time_ns", spy_ns)
        load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert calls == []

    def test_no_signing(self, monkeypatch):
        from execution_gateway.hmac_sha256_signer import HmacSha256Signer
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert calls == []

    def test_no_gateway_construction(self):
        src = inspect.getsource(_module)
        assert "BybitExecutionGateway" not in src
        assert "create_configured_bybit_demo_execution_gateway" not in src
        assert "create_bybit_demo_execution_gateway" not in src

    def test_no_print(self, capsys):
        load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_no_logging_import(self):
        assert "logging" not in vars(_module)

    def test_source_does_not_use_print(self):
        src = inspect.getsource(_module)
        assert "print(" not in src


# ---------------------------------------------------------------------------
# 12. Seguridad
# ---------------------------------------------------------------------------

class TestSecurity:
    _MARKER = "ZZSUPERSECRET9999"

    def test_marker_absent_from_repr(self):
        config = load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        )
        assert self._MARKER not in repr(config)

    def test_marker_absent_from_str(self):
        config = load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        )
        assert self._MARKER not in str(config)

    def test_marker_absent_when_other_field_fails(self):
        env = _env(
            PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER,
            PHOENIX_BYBIT_RECV_WINDOW_MS="abc",
        )
        with pytest.raises(EnvironmentConfigurationError) as exc_info:
            load_bybit_demo_execution_config_from_env(environ=env)
        assert self._MARKER not in str(exc_info.value)

    def test_marker_absent_when_secret_itself_is_rejected_by_config(self):
        env = _env(PHOENIX_BYBIT_DEMO_API_SECRET="   ")
        with pytest.raises(ValueError) as exc_info:
            load_bybit_demo_execution_config_from_env(environ=env)
        assert "   " not in str(exc_info.value)

    def test_environment_configuration_error_message_never_contains_marker(self):
        for env in [
            _without(_API_KEY_VAR),
            _env(**{_API_SECRET_VAR: self._MARKER}) | _without(_TIMEOUT_SECONDS_VAR),
        ]:
            error = _raised(lambda e=env: load_bybit_demo_execution_config_from_env(environ=e))
            if error is not None:
                assert self._MARKER not in str(error)

    def test_does_not_import_dotenv(self):
        assert "dotenv" not in vars(_module)

    def test_source_has_no_dotenv_reference(self):
        src = inspect.getsource(_module)
        assert "dotenv" not in src.lower()


# ---------------------------------------------------------------------------
# 13. Superficie mínima
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_config_has_no_from_env_classmethod(self):
        assert not hasattr(BybitDemoExecutionConfig, "from_env")

    def test_loader_has_no_default_environment_values(self):
        src = inspect.getsource(_module)
        assert "demo-key" not in src
        assert "5000" not in src
        assert "10.0" not in src

    def test_no_mainnet_reference(self):
        src = inspect.getsource(_module)
        assert "mainnet" not in src.lower()

    def test_no_testnet_reference(self):
        src = inspect.getsource(_module)
        assert "testnet" not in src.lower()

    def test_no_exchange_selection(self):
        src = inspect.getsource(_module)
        assert "Binance" not in src
        assert "OKX" not in src

    def test_no_file_read_source(self):
        src = inspect.getsource(_module)
        assert "open(" not in src

    def test_no_railway_reference(self):
        src = inspect.getsource(_module)
        assert "railway" not in src.lower()

    def test_no_retry_logic(self):
        src = inspect.getsource(_module)
        assert "retry" not in src.lower()
        assert "retries" not in src.lower()

    def test_no_logging_reference(self):
        src = inspect.getsource(_module)
        assert "logging" not in src

    def test_single_public_function_in_module(self):
        public = [n for n in vars(_module) if not n.startswith("_") and inspect.isfunction(getattr(_module, n))]
        assert public == ["load_bybit_demo_execution_config_from_env"]

    def test_only_four_variable_name_constants(self):
        names = {n for n in vars(_module) if n.isupper() or (n.startswith("_") and n.endswith("_VAR"))}
        assert names == {"_API_KEY_VAR", "_API_SECRET_VAR", "_RECV_WINDOW_MS_VAR", "_TIMEOUT_SECONDS_VAR"}

    def test_variable_names_are_exact(self):
        assert _API_KEY_VAR == "PHOENIX_BYBIT_DEMO_API_KEY"
        assert _API_SECRET_VAR == "PHOENIX_BYBIT_DEMO_API_SECRET"
        assert _RECV_WINDOW_MS_VAR == "PHOENIX_BYBIT_RECV_WINDOW_MS"
        assert _TIMEOUT_SECONDS_VAR == "PHOENIX_HTTP_TIMEOUT_SECONDS"

    def test_no_alias_variable_names_accepted(self, monkeypatch):
        monkeypatch.delenv("BYBIT_API_KEY", raising=False)
        env = dict(_VALID_ENV)
        env["BYBIT_API_KEY"] = "alias-should-be-ignored"
        config = load_bybit_demo_execution_config_from_env(environ=env)
        assert config.api_key == "demo-key"


# ---------------------------------------------------------------------------
# 14. Excepción — EnvironmentConfigurationError
# ---------------------------------------------------------------------------

class TestEnvironmentConfigurationError:
    def test_inherits_directly_from_exception(self):
        assert Exception in EnvironmentConfigurationError.__bases__

    def test_valid_construction(self):
        err = EnvironmentConfigurationError(message="missing variable")
        assert err.message == "missing variable"

    def test_message_is_keyword_only(self):
        with pytest.raises(TypeError):
            EnvironmentConfigurationError("missing variable")

    def test_rejects_non_string_message(self):
        with pytest.raises(TypeError, match="message must be str"):
            EnvironmentConfigurationError(message=None)

    def test_rejects_empty_message(self):
        with pytest.raises(ValueError, match="message must not be empty or whitespace-only"):
            EnvironmentConfigurationError(message="")

    def test_rejects_whitespace_only_message(self):
        with pytest.raises(ValueError, match="message must not be empty or whitespace-only"):
            EnvironmentConfigurationError(message="   ")

    def test_str_is_message_verbatim(self):
        err = EnvironmentConfigurationError(message="Missing required environment variable: X")
        assert str(err) == "Missing required environment variable: X"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(EnvironmentConfigurationError):
            raise EnvironmentConfigurationError(message="boom")

    def test_distinguishes_missing_from_invalid_conversion(self):
        missing = _raised(lambda: load_bybit_demo_execution_config_from_env(
            environ=_without(_RECV_WINDOW_MS_VAR)
        ))
        invalid = _raised(lambda: load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="abc")
        ))
        assert type(missing) is EnvironmentConfigurationError
        assert type(invalid) is EnvironmentConfigurationError
        assert "Missing required" in str(missing)
        assert "Invalid integer" in str(invalid)
        assert str(missing) != str(invalid)


# ---------------------------------------------------------------------------
# 15. Mutaciones — comportamientos que la suite debe detectar
# ---------------------------------------------------------------------------

class TestMutationDetection:
    def test_explicit_mapping_wins_over_os_environ_completely(self, monkeypatch):
        # Si el loader usara os.environ aun con mapping explícito, esta
        # variable "envenenada" contaminaría el resultado.
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "POISONED")
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_SECRET", "POISONED")
        monkeypatch.setenv("PHOENIX_BYBIT_RECV_WINDOW_MS", "1")
        monkeypatch.setenv("PHOENIX_HTTP_TIMEOUT_SECONDS", "1")
        config = load_bybit_demo_execution_config_from_env(environ=_VALID_ENV)
        assert config.api_key != "POISONED"
        assert config.recv_window_ms != 1

    def test_credentials_are_not_stripped(self):
        env = _env(
            PHOENIX_BYBIT_DEMO_API_KEY="  padded-key  ",
            PHOENIX_BYBIT_DEMO_API_SECRET="  padded-secret  ",
        )
        config = load_bybit_demo_execution_config_from_env(environ=env)
        assert config.api_key == "  padded-key  "
        assert config.api_secret == "  padded-secret  "

    def test_no_hidden_default_for_recv_window(self):
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_RECV_WINDOW_MS"):
            load_bybit_demo_execution_config_from_env(environ=_without(_RECV_WINDOW_MS_VAR))

    def test_no_hidden_default_for_timeout(self):
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_HTTP_TIMEOUT_SECONDS"):
            load_bybit_demo_execution_config_from_env(environ=_without(_TIMEOUT_SECONDS_VAR))

    def test_timeout_nan_is_never_silently_accepted(self):
        with pytest.raises(ValueError, match="finite"):
            load_bybit_demo_execution_config_from_env(
                environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="nan")
            )

    def test_results_are_not_cached_between_calls(self):
        first = load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="1111")
        )
        second = load_bybit_demo_execution_config_from_env(
            environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="2222")
        )
        assert first.recv_window_ms == 1111
        assert second.recv_window_ms == 2222
        assert first != second

    def test_read_order_is_key_then_secret_then_recv_then_timeout(self):
        # Cada variable, tomada de a una, debe producir el error
        # correspondiente a su propia posición en el orden documentado.
        assert "PHOENIX_BYBIT_DEMO_API_KEY" in str(_raised(
            lambda: load_bybit_demo_execution_config_from_env(environ={})
        ))
        assert "PHOENIX_BYBIT_DEMO_API_SECRET" in str(_raised(
            lambda: load_bybit_demo_execution_config_from_env(
                environ={"PHOENIX_BYBIT_DEMO_API_KEY": "k"}
            )
        ))
        assert "PHOENIX_BYBIT_RECV_WINDOW_MS" in str(_raised(
            lambda: load_bybit_demo_execution_config_from_env(
                environ={"PHOENIX_BYBIT_DEMO_API_KEY": "k", "PHOENIX_BYBIT_DEMO_API_SECRET": "s"}
            )
        ))
        assert "PHOENIX_HTTP_TIMEOUT_SECONDS" in str(_raised(
            lambda: load_bybit_demo_execution_config_from_env(environ={
                "PHOENIX_BYBIT_DEMO_API_KEY": "k",
                "PHOENIX_BYBIT_DEMO_API_SECRET": "s",
                "PHOENIX_BYBIT_RECV_WINDOW_MS": "5000",
            })
        ))

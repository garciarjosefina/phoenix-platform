import dataclasses
import inspect
import math
from decimal import Decimal
from fractions import Fraction

import pytest

import execution_gateway
import execution_gateway.bybit_demo_execution_config as _module
from execution_gateway.bybit_demo_credentials_factory import create_bybit_demo_credentials
from execution_gateway.bybit_demo_execution_config import BybitDemoExecutionConfig
from execution_gateway.bybit_recv_window_factory import create_bybit_recv_window_ms
from execution_gateway.http_timeout_factory import create_http_timeout_seconds


_VALID_KEY = "demo-key"
_VALID_SECRET = "demo-secret"
_VALID_RECV_WINDOW_MS = 5_000
_VALID_TIMEOUT_SECONDS = 5.0


def _build(**overrides):
    kwargs = dict(
        api_key=_VALID_KEY,
        api_secret=_VALID_SECRET,
        recv_window_ms=_VALID_RECV_WINDOW_MS,
        timeout_seconds=_VALID_TIMEOUT_SECONDS,
    )
    kwargs.update(overrides)
    return BybitDemoExecutionConfig(**kwargs)


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
        from execution_gateway.bybit_demo_execution_config import BybitDemoExecutionConfig as C
        assert C is BybitDemoExecutionConfig

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitDemoExecutionConfig")
        assert execution_gateway.BybitDemoExecutionConfig is BybitDemoExecutionConfig

    def test_included_in_all(self):
        assert "BybitDemoExecutionConfig" in execution_gateway.__all__

    def test_single_public_class_in_module(self):
        class_names = [
            name for name in vars(_module)
            if inspect.isclass(getattr(_module, name))
            and getattr(_module, name).__module__ == _module.__name__
        ]
        assert class_names == ["BybitDemoExecutionConfig"]

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(BybitDemoExecutionConfig)

    def test_is_frozen(self):
        assert BybitDemoExecutionConfig.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(BybitDemoExecutionConfig)]
        assert names == ["api_key", "api_secret", "recv_window_ms", "timeout_seconds"]

    def test_exactly_four_fields(self):
        assert len(dataclasses.fields(BybitDemoExecutionConfig)) == 4

    def test_field_annotations_exact(self):
        hints = inspect.get_annotations(BybitDemoExecutionConfig, eval_str=True)
        assert hints["api_key"] is str
        assert hints["api_secret"] is str
        assert hints["recv_window_ms"] is int
        assert hints["timeout_seconds"] == (int | float)


# ---------------------------------------------------------------------------
# 2. Construcción válida
# ---------------------------------------------------------------------------

class TestValidConstruction:
    def test_builds_with_valid_values(self):
        config = _build()
        assert isinstance(config, BybitDemoExecutionConfig)

    def test_values_preserved_exactly(self):
        config = _build(api_key="my-key", api_secret="my-secret", recv_window_ms=7_500, timeout_seconds=12.5)
        assert config.api_key == "my-key"
        assert config.api_secret == "my-secret"
        assert config.recv_window_ms == 7_500
        assert config.timeout_seconds == 12.5

    def test_timeout_accepts_int(self):
        config = _build(timeout_seconds=5)
        assert config.timeout_seconds == 5
        assert type(config.timeout_seconds) is int

    def test_timeout_accepts_float(self):
        config = _build(timeout_seconds=5.5)
        assert config.timeout_seconds == 5.5
        assert type(config.timeout_seconds) is float

    def test_recv_window_type_preserved(self):
        config = _build(recv_window_ms=5_000)
        assert type(config.recv_window_ms) is int

    def test_equality_by_value(self):
        c1 = _build()
        c2 = _build()
        assert c1 == c2
        assert c1 is not c2

    def test_inequality_on_different_api_key(self):
        c1 = _build(api_key="key-a")
        c2 = _build(api_key="key-b")
        assert c1 != c2

    def test_inequality_on_different_recv_window(self):
        c1 = _build(recv_window_ms=1_000)
        c2 = _build(recv_window_ms=2_000)
        assert c1 != c2

    def test_inequality_on_different_timeout(self):
        c1 = _build(timeout_seconds=1.0)
        c2 = _build(timeout_seconds=2.0)
        assert c1 != c2


# ---------------------------------------------------------------------------
# 3. Validación de credenciales — paridad exacta con create_bybit_demo_credentials
# ---------------------------------------------------------------------------

class TestCredentialsValidation:
    def test_valid_api_key_accepted(self):
        config = _build(api_key="any-nonempty-key")
        assert config.api_key == "any-nonempty-key"

    def test_empty_api_key_raises_value_error(self):
        with pytest.raises(ValueError, match="api_key must not be empty or whitespace-only"):
            _build(api_key="")

    def test_whitespace_api_key_raises_value_error(self):
        with pytest.raises(ValueError, match="api_key must not be empty or whitespace-only"):
            _build(api_key="   ")

    def test_non_string_api_key_raises_type_error(self):
        with pytest.raises(TypeError, match="api_key must be str, got: int"):
            _build(api_key=123)

    def test_none_api_key_raises_type_error(self):
        with pytest.raises(TypeError, match="api_key must be str, got: NoneType"):
            _build(api_key=None)

    def test_valid_api_secret_accepted(self):
        config = _build(api_secret="any-nonempty-secret")
        assert config.api_secret == "any-nonempty-secret"

    def test_empty_api_secret_raises_value_error(self):
        with pytest.raises(ValueError, match="api_secret must not be empty or whitespace-only"):
            _build(api_secret="")

    def test_whitespace_api_secret_raises_value_error(self):
        with pytest.raises(ValueError, match="api_secret must not be empty or whitespace-only"):
            _build(api_secret="\t")

    def test_non_string_api_secret_raises_type_error(self):
        with pytest.raises(TypeError, match="api_secret must be str, got: bytes"):
            _build(api_secret=b"secret")

    def test_peripheral_spaces_preserved_no_strip(self):
        config = _build(api_key="  padded-key  ")
        assert config.api_key == "  padded-key  "

    @pytest.mark.parametrize("bad_api_key", [None, 1, 1.0, [], {}, object()])
    def test_credentials_parity_type_errors(self, bad_api_key):
        integral_error = _raised(lambda: _build(api_key=bad_api_key))
        direct_error = _raised(lambda: create_bybit_demo_credentials(api_key=bad_api_key, api_secret=_VALID_SECRET))
        assert type(integral_error) is type(direct_error)
        assert str(integral_error) == str(direct_error)

    @pytest.mark.parametrize("bad_value", ["", "   ", "\t\t"])
    def test_credentials_parity_value_errors(self, bad_value):
        integral_error = _raised(lambda: _build(api_key=bad_value))
        direct_error = _raised(lambda: create_bybit_demo_credentials(api_key=bad_value, api_secret=_VALID_SECRET))
        assert type(integral_error) is type(direct_error)
        assert str(integral_error) == str(direct_error)


# ---------------------------------------------------------------------------
# 4. Validación de recv_window_ms — paridad exacta con create_bybit_recv_window_ms
# ---------------------------------------------------------------------------

class TestRecvWindowValidation:
    def test_valid_recv_window_accepted(self):
        config = _build(recv_window_ms=5_000)
        assert config.recv_window_ms == 5_000

    def test_minimum_valid_recv_window(self):
        config = _build(recv_window_ms=1)
        assert config.recv_window_ms == 1

    def test_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="recv_window_ms must be > 0, got: 0"):
            _build(recv_window_ms=0)

    def test_negative_raises_value_error(self):
        with pytest.raises(ValueError, match="recv_window_ms must be > 0, got: -1"):
            _build(recv_window_ms=-1)

    def test_bool_raises_type_error(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: bool"):
            _build(recv_window_ms=True)

    def test_float_raises_type_error(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: float"):
            _build(recv_window_ms=5_000.0)

    def test_string_raises_type_error(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: str"):
            _build(recv_window_ms="5000")

    def test_int_subclass_accepted(self):
        class MyInt(int):
            pass
        config = _build(recv_window_ms=MyInt(5_000))
        assert config.recv_window_ms == 5_000

    def test_no_upper_bound(self):
        config = _build(recv_window_ms=10_000_000)
        assert config.recv_window_ms == 10_000_000

    @pytest.mark.parametrize("bad_value", [0, -1, -100, True, 5_000.0, "5000", None, []])
    def test_recv_window_parity(self, bad_value):
        integral_error = _raised(lambda: _build(recv_window_ms=bad_value))
        direct_error = _raised(lambda: create_bybit_recv_window_ms(recv_window_ms=bad_value))
        assert type(integral_error) is type(direct_error)
        assert str(integral_error) == str(direct_error)


# ---------------------------------------------------------------------------
# 5. Validación de timeout_seconds — paridad exacta con create_http_timeout_seconds
# ---------------------------------------------------------------------------

class TestTimeoutValidation:
    def test_valid_int_accepted(self):
        config = _build(timeout_seconds=5)
        assert config.timeout_seconds == 5

    def test_valid_float_accepted(self):
        config = _build(timeout_seconds=5.5)
        assert config.timeout_seconds == 5.5

    def test_fractional_value_accepted(self):
        config = _build(timeout_seconds=0.001)
        assert config.timeout_seconds == 0.001

    def test_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0, got: 0"):
            _build(timeout_seconds=0)

    def test_negative_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            _build(timeout_seconds=-5.0)

    def test_bool_raises_type_error(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: bool"):
            _build(timeout_seconds=True)

    def test_string_raises_type_error(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: str"):
            _build(timeout_seconds="5")

    def test_decimal_raises_type_error(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: Decimal"):
            _build(timeout_seconds=Decimal("5.0"))

    def test_fraction_raises_type_error(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: Fraction"):
            _build(timeout_seconds=Fraction(5, 1))

    def test_int_subclass_accepted(self):
        class MyInt(int):
            pass
        config = _build(timeout_seconds=MyInt(5))
        assert config.timeout_seconds == 5

    def test_float_subclass_accepted(self):
        class MyFloat(float):
            pass
        config = _build(timeout_seconds=MyFloat(5.0))
        assert config.timeout_seconds == 5.0

    def test_nan_accepted_matching_current_contract(self):
        config = _build(timeout_seconds=math.nan)
        assert math.isnan(config.timeout_seconds)

    def test_positive_infinity_accepted_matching_current_contract(self):
        config = _build(timeout_seconds=math.inf)
        assert config.timeout_seconds == math.inf

    def test_negative_infinity_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            _build(timeout_seconds=-math.inf)

    @pytest.mark.parametrize(
        "bad_value",
        [0, -5.0, True, "5", Decimal("5.0"), Fraction(5, 1), None, -math.inf],
    )
    def test_timeout_parity(self, bad_value):
        integral_error = _raised(lambda: _build(timeout_seconds=bad_value))
        direct_error = _raised(lambda: create_http_timeout_seconds(timeout_seconds=bad_value))
        assert type(integral_error) is type(direct_error)
        assert str(integral_error) == str(direct_error)


# ---------------------------------------------------------------------------
# 6. Inmutabilidad
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_cannot_reassign_api_key(self):
        config = _build()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.api_key = "other"

    def test_cannot_reassign_api_secret(self):
        config = _build()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.api_secret = "other"

    def test_cannot_reassign_recv_window_ms(self):
        config = _build()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.recv_window_ms = 9_999

    def test_cannot_reassign_timeout_seconds(self):
        config = _build()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.timeout_seconds = 9.9

    def test_original_values_survive_failed_mutation(self):
        config = _build(api_key="unchanged")
        try:
            config.api_key = "mutated"
        except dataclasses.FrozenInstanceError:
            pass
        assert config.api_key == "unchanged"


# ---------------------------------------------------------------------------
# 7. Seguridad
# ---------------------------------------------------------------------------

class TestSecurity:
    def test_repr_hides_api_secret(self):
        config = _build(api_secret="super-secret-value")
        assert "super-secret-value" not in repr(config)

    def test_str_hides_api_secret(self):
        config = _build(api_secret="super-secret-value")
        assert "super-secret-value" not in str(config)

    def test_repr_still_shows_api_key(self):
        config = _build(api_key="visible-key")
        assert "visible-key" in repr(config)

    def test_exception_messages_do_not_leak_secret(self):
        try:
            _build(api_secret=123)
            assert False, "expected TypeError"
        except TypeError as e:
            assert "123" not in str(e) or "api_secret must be str" in str(e)

    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_import_dotenv(self):
        assert "dotenv" not in vars(_module)

    def test_does_not_import_logging(self):
        assert "logging" not in vars(_module)

    def test_source_does_not_use_print(self):
        src = inspect.getsource(_module)
        assert "print(" not in src

    def test_source_does_not_use_open(self):
        src = inspect.getsource(_module)
        assert "open(" not in src

    def test_source_does_not_reference_env(self):
        src = inspect.getsource(_module)
        assert "os.environ" not in src
        assert "os.getenv" not in src

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "env-key")
        monkeypatch.setenv("BYBIT_API_SECRET", "env-secret")
        config = _build()
        assert config.api_key == _VALID_KEY
        assert config.api_secret == _VALID_SECRET

    def test_no_file_reads_during_construction(self, monkeypatch):
        calls = []
        original_open = open

        def spy_open(*args, **kwargs):
            calls.append(args)
            return original_open(*args, **kwargs)

        import builtins
        monkeypatch.setattr(builtins, "open", spy_open)
        _build()
        assert calls == []


# ---------------------------------------------------------------------------
# 8. Superficie mínima
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_no_from_env(self):
        assert not hasattr(BybitDemoExecutionConfig, "from_env")

    def test_no_from_dict(self):
        assert not hasattr(BybitDemoExecutionConfig, "from_dict")

    def test_no_load(self):
        assert not hasattr(BybitDemoExecutionConfig, "load")

    def test_no_parse(self):
        assert not hasattr(BybitDemoExecutionConfig, "parse")

    def test_no_to_dict(self):
        assert not hasattr(BybitDemoExecutionConfig, "to_dict")

    def test_no_masked(self):
        assert not hasattr(BybitDemoExecutionConfig, "masked")

    def test_no_validate_method(self):
        assert not hasattr(BybitDemoExecutionConfig, "validate")

    def test_no_base_url_field(self):
        names = [f.name for f in dataclasses.fields(BybitDemoExecutionConfig)]
        assert "base_url" not in names

    def test_no_environment_field(self):
        names = [f.name for f in dataclasses.fields(BybitDemoExecutionConfig)]
        assert "environment" not in names

    def test_only_public_members_are_the_four_fields(self):
        public_attrs = {
            name for name in vars(BybitDemoExecutionConfig)
            if not name.startswith("_")
        }
        assert public_attrs == set()


# ---------------------------------------------------------------------------
# 9. Ausencia de efectos durante la construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_no_clock_read(self, monkeypatch):
        import time
        calls = []
        original_ns = time.time_ns

        def spy_ns():
            calls.append(True)
            return original_ns()

        monkeypatch.setattr(time, "time_ns", spy_ns)
        _build()
        assert calls == []

    def test_no_signing(self, monkeypatch):
        from execution_gateway.hmac_sha256_signer import HmacSha256Signer
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        _build()
        assert calls == []

    def test_no_serialization(self, monkeypatch):
        from execution_gateway.standard_json_serializer import StandardJsonSerializer

        def explode(self, value):
            raise AssertionError("dumps must not be called")

        monkeypatch.setattr(StandardJsonSerializer, "dumps", explode)
        _build()

    def test_no_http(self, monkeypatch):
        from execution_gateway.urllib_http_transport import UrllibHttpTransport
        calls = []
        original_post = UrllibHttpTransport.post

        def spy_post(self, *, url, headers, body, timeout_seconds):
            calls.append(url)
            return original_post(self, url=url, headers=headers, body=body, timeout_seconds=timeout_seconds)

        monkeypatch.setattr(UrllibHttpTransport, "post", spy_post)
        _build()
        assert calls == []

    def test_no_dns_resolution(self, monkeypatch):
        import socket
        calls = []
        original = socket.getaddrinfo

        def patched(*args, **kwargs):
            calls.append(args)
            return original(*args, **kwargs)

        monkeypatch.setattr(socket, "getaddrinfo", patched)
        _build()
        assert calls == []

    def test_does_not_construct_gateway(self):
        src = inspect.getsource(_module)
        assert "create_configured_bybit_demo_execution_gateway" not in src
        assert "BybitExecutionGateway" not in src

    def test_does_not_construct_transport(self):
        src = inspect.getsource(_module)
        assert "HttpTransport" not in src
        assert "UrllibHttpTransport" not in src

    def test_does_not_construct_authenticator(self):
        src = inspect.getsource(_module)
        assert "Authenticator" not in src

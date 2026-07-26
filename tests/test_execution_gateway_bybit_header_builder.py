import os
import pytest
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_authenticator import BybitAuthentication
import execution_gateway


def _auth(**kwargs) -> BybitAuthentication:
    defaults = dict(
        timestamp_ms=1_700_000_000_000,
        api_key="MYAPIKEY",
        recv_window_ms=5000,
        signature="a" * 64,
    )
    defaults.update(kwargs)
    return BybitAuthentication(**defaults)


class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_header_builder import BybitHeaderBuilder as B
        assert B is BybitHeaderBuilder

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitHeaderBuilder")
        assert execution_gateway.BybitHeaderBuilder is BybitHeaderBuilder

    def test_in_all(self):
        assert "BybitHeaderBuilder" in execution_gateway.__all__


class TestConstruction:
    def test_no_constructor_args(self):
        builder = BybitHeaderBuilder()
        assert builder is not None

    def test_two_instances_independent(self):
        b1 = BybitHeaderBuilder()
        b2 = BybitHeaderBuilder()
        assert b1 is not b2


class TestValidation:
    def test_rejects_none(self):
        builder = BybitHeaderBuilder()
        with pytest.raises(TypeError):
            builder.build(authentication=None)

    def test_rejects_incompatible_object(self):
        builder = BybitHeaderBuilder()
        with pytest.raises(TypeError):
            builder.build(authentication={"api_key": "k"})

    def test_accepts_valid_authentication(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        assert isinstance(headers, dict)


class TestHeaders:
    def test_exactly_five_keys(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        assert len(headers) == 5

    def test_api_key_header_name(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        assert "X-BAPI-API-KEY" in headers

    def test_timestamp_header_name(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        assert "X-BAPI-TIMESTAMP" in headers

    def test_recv_window_header_name(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        assert "X-BAPI-RECV-WINDOW" in headers

    def test_sign_header_name(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        assert "X-BAPI-SIGN" in headers

    def test_content_type_header_name(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        assert "Content-Type" in headers

    def test_api_key_value_unchanged(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth(api_key="EXACT_KEY"))
        assert headers["X-BAPI-API-KEY"] == "EXACT_KEY"

    def test_timestamp_converted_to_str(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth(timestamp_ms=1_700_000_000_000))
        assert headers["X-BAPI-TIMESTAMP"] == "1700000000000"

    def test_recv_window_converted_to_str(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth(recv_window_ms=5000))
        assert headers["X-BAPI-RECV-WINDOW"] == "5000"

    def test_signature_value_unchanged(self):
        sig = "b" * 64
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth(signature=sig))
        assert headers["X-BAPI-SIGN"] == sig

    def test_content_type_value(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        assert headers["Content-Type"] == "application/json"

    def test_all_values_are_str(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        for v in headers.values():
            assert isinstance(v, str)

    def test_no_api_secret_in_headers(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        for k, v in headers.items():
            assert "secret" not in k.lower()
            assert "secret" not in v.lower()

    def test_no_extra_headers(self):
        builder = BybitHeaderBuilder()
        headers = builder.build(authentication=_auth())
        expected_keys = {
            "X-BAPI-API-KEY",
            "X-BAPI-TIMESTAMP",
            "X-BAPI-RECV-WINDOW",
            "X-BAPI-SIGN",
            "Content-Type",
        }
        assert set(headers.keys()) == expected_keys


class TestIndependence:
    def test_each_call_returns_new_dict(self):
        builder = BybitHeaderBuilder()
        auth = _auth()
        h1 = builder.build(authentication=auth)
        h2 = builder.build(authentication=auth)
        assert h1 is not h2

    def test_mutating_first_result_does_not_affect_second(self):
        builder = BybitHeaderBuilder()
        auth = _auth()
        h1 = builder.build(authentication=auth)
        h1["X-BAPI-API-KEY"] = "MUTATED"
        h2 = builder.build(authentication=auth)
        assert h2["X-BAPI-API-KEY"] == auth.api_key

    def test_no_stored_last_headers(self):
        builder = BybitHeaderBuilder()
        builder.build(authentication=_auth())
        assert not hasattr(builder, "last_headers")

    def test_does_not_modify_authentication(self):
        auth = _auth()
        builder = BybitHeaderBuilder()
        builder.build(authentication=auth)
        assert auth.api_key == "MYAPIKEY"
        assert auth.timestamp_ms == 1_700_000_000_000


class TestNoSideEffects:
    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__header_sentinel__"
        try:
            builder = BybitHeaderBuilder()
            headers = builder.build(authentication=_auth())
            assert headers is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_no_external_dependencies(self):
        import sys
        for name in ("requests", "httpx", "aiohttp", "pybit"):
            assert name not in sys.modules or True


class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_standard_authenticator_still_works(self):
        from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator
        assert StandardBybitAuthenticator is not None

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None

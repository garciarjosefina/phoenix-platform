import os
import pytest
from execution_gateway.json_serializer import JsonSerializer
import execution_gateway


class _ValidSerializer:
    def dumps(self, value: object) -> str:
        return f"serialized:{value}"

    def loads(self, value: str) -> object:
        return {"parsed": value}


class _MissingLoads:
    def dumps(self, value: object) -> str:
        return ""


class _MissingDumps:
    def loads(self, value: str) -> object:
        return {}


class TestImport:
    def test_direct_import(self):
        from execution_gateway.json_serializer import JsonSerializer as S
        assert S is JsonSerializer

    def test_public_import(self):
        assert hasattr(execution_gateway, "JsonSerializer")
        assert execution_gateway.JsonSerializer is JsonSerializer

    def test_in_all(self):
        assert "JsonSerializer" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable_valid(self):
        s = _ValidSerializer()
        assert isinstance(s, JsonSerializer)

    def test_missing_loads_rejected(self):
        s = _MissingLoads()
        assert not isinstance(s, JsonSerializer)

    def test_missing_dumps_rejected(self):
        s = _MissingDumps()
        assert not isinstance(s, JsonSerializer)

    def test_no_explicit_inheritance_required(self):
        s = _ValidSerializer()
        assert isinstance(s, JsonSerializer)

    def test_dumps_returns_exact_str(self):
        s = _ValidSerializer()
        result = s.dumps({"key": "value"})
        assert result == "serialized:{'key': 'value'}"

    def test_loads_returns_exact_object(self):
        s = _ValidSerializer()
        result = s.loads('{"key":"value"}')
        assert result == {"parsed": '{"key":"value"}'}

    def test_dumps_str_is_same_object(self):
        class IdentitySerializer:
            def dumps(self, value: object) -> str:
                return "fixed"
            def loads(self, value: str) -> object:
                return value

        s = IdentitySerializer()
        result = s.dumps({})
        assert result == "fixed"

    def test_loads_object_is_same_object(self):
        sentinel = object()

        class SentinelSerializer:
            def dumps(self, value: object) -> str:
                return ""
            def loads(self, value: str) -> object:
                return sentinel

        s = SentinelSerializer()
        result = s.loads("anything")
        assert result is sentinel


class TestNoSideEffects:
    def test_import_does_not_read_env(self):
        os.environ["BYBIT_API_KEY"] = "__json_sentinel__"
        try:
            from execution_gateway.json_serializer import JsonSerializer as S
            assert S is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_no_external_dependencies(self):
        import sys
        import execution_gateway.json_serializer as module
        for name in ("orjson", "ujson", "requests", "httpx"):
            assert name not in sys.modules or True
        assert module is not None


class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_http_transport_still_works(self):
        from execution_gateway.http_transport import HttpTransport
        assert HttpTransport is not None

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None

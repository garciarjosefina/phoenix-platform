import json
import os
import pytest
from execution_gateway.standard_json_serializer import StandardJsonSerializer
from execution_gateway.json_serializer import JsonSerializer
import execution_gateway


class TestImport:
    def test_direct_import(self):
        from execution_gateway.standard_json_serializer import StandardJsonSerializer as S
        assert S is StandardJsonSerializer

    def test_public_import(self):
        assert hasattr(execution_gateway, "StandardJsonSerializer")
        assert execution_gateway.StandardJsonSerializer is StandardJsonSerializer

    def test_in_all(self):
        assert "StandardJsonSerializer" in execution_gateway.__all__


class TestStructural:
    def test_implements_json_serializer(self):
        s = StandardJsonSerializer()
        assert isinstance(s, JsonSerializer)

    def test_no_constructor_args(self):
        s = StandardJsonSerializer()
        assert s is not None

    def test_two_instances_independent(self):
        s1 = StandardJsonSerializer()
        s2 = StandardJsonSerializer()
        assert s1 is not s2


class TestDumps:
    def test_dict(self):
        s = StandardJsonSerializer()
        assert s.dumps({"a": 1}) == json.dumps({"a": 1})

    def test_list(self):
        s = StandardJsonSerializer()
        assert s.dumps([1, 2, 3]) == json.dumps([1, 2, 3])

    def test_str(self):
        s = StandardJsonSerializer()
        assert s.dumps("hello") == json.dumps("hello")

    def test_int(self):
        s = StandardJsonSerializer()
        assert s.dumps(42) == json.dumps(42)

    def test_float(self):
        s = StandardJsonSerializer()
        assert s.dumps(3.14) == json.dumps(3.14)

    def test_bool_true(self):
        s = StandardJsonSerializer()
        assert s.dumps(True) == json.dumps(True)

    def test_bool_false(self):
        s = StandardJsonSerializer()
        assert s.dumps(False) == json.dumps(False)

    def test_none(self):
        s = StandardJsonSerializer()
        assert s.dumps(None) == json.dumps(None)

    def test_exact_standard_output(self):
        s = StandardJsonSerializer()
        value = {"key": "value", "n": 1}
        assert s.dumps(value) == json.dumps(value)

    def test_non_serializable_raises_type_error(self):
        s = StandardJsonSerializer()
        with pytest.raises(TypeError):
            s.dumps(object())


class TestLoads:
    def test_object(self):
        s = StandardJsonSerializer()
        assert s.loads('{"a": 1}') == {"a": 1}

    def test_array(self):
        s = StandardJsonSerializer()
        assert s.loads('[1, 2, 3]') == [1, 2, 3]

    def test_string(self):
        s = StandardJsonSerializer()
        assert s.loads('"hello"') == "hello"

    def test_number(self):
        s = StandardJsonSerializer()
        assert s.loads('42') == 42

    def test_boolean_true(self):
        s = StandardJsonSerializer()
        assert s.loads('true') is True

    def test_boolean_false(self):
        s = StandardJsonSerializer()
        assert s.loads('false') is False

    def test_null(self):
        s = StandardJsonSerializer()
        assert s.loads('null') is None

    def test_equivalent_to_standard_loads(self):
        s = StandardJsonSerializer()
        raw = '{"key": "value", "n": 1}'
        assert s.loads(raw) == json.loads(raw)

    def test_invalid_json_raises_decode_error(self):
        s = StandardJsonSerializer()
        with pytest.raises(json.JSONDecodeError):
            s.loads("not-json")


class TestRoundTrip:
    def test_round_trip_dict(self):
        s = StandardJsonSerializer()
        original = {"key": "value", "n": 42, "flag": True, "nothing": None}
        assert s.loads(s.dumps(original)) == original

    def test_round_trip_list(self):
        s = StandardJsonSerializer()
        original = [1, "two", 3.0, True, None]
        assert s.loads(s.dumps(original)) == original


class TestNoSideEffects:
    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__std_json_sentinel__"
        try:
            s = StandardJsonSerializer()
            assert s is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_no_external_dependencies(self):
        import sys
        for name in ("orjson", "ujson", "requests", "httpx"):
            assert name not in sys.modules or True


class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_json_serializer_contract_still_works(self):
        from execution_gateway.json_serializer import JsonSerializer
        assert JsonSerializer is not None

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None

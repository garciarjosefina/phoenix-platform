import inspect

import pytest

import execution_gateway
import execution_gateway.bybit_response_parser_factory as _module
from execution_gateway.bybit_demo_execution_gateway_factory import (
    create_bybit_demo_execution_gateway,
)
from execution_gateway.bybit_private_api import BybitPrivateApi
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender import BybitPrivateRequestSender
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_parser import BybitResponseParser
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.json_serializer import JsonSerializer


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

class SpySerializer:
    """Structural JsonSerializer spy — has dumps and loads, records calls."""

    def __init__(self):
        self.dumps_calls: list = []
        self.loads_calls: list = []

    def dumps(self, value: object) -> str:
        self.dumps_calls.append(value)
        return "{}"

    def loads(self, value: str) -> object:
        self.loads_calls.append(value)
        return {
            "retCode": 0,
            "retMsg": "OK",
            "result": {},
            "retExtInfo": {},
            "time": 1000,
        }


class RejectingSerializer:
    """Returns non-dict to trigger parser error."""

    def dumps(self, value: object) -> str:
        return "[]"

    def loads(self, value: str) -> object:
        return []


class SpySender(BybitPrivateRequestSender):
    def __init__(self):
        self.calls: list[dict] = []

    def send(self, *, url: str, payload: object) -> str:
        self.calls.append({"url": url, "payload": payload})
        return '{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}'


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_response_parser_factory import (
            create_bybit_response_parser as f,
        )
        assert f is create_bybit_response_parser

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_response_parser")
        assert execution_gateway.create_bybit_response_parser is create_bybit_response_parser

    def test_included_in_all(self):
        assert "create_bybit_response_parser" in execution_gateway.__all__

    def test_single_factory_for_bybit_response_parser(self):
        factory_names = [
            name for name in vars(_module)
            if callable(getattr(_module, name))
            and "response_parser" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_response_parser"

    def test_serializer_param_is_keyword_only(self):
        sig = inspect.signature(create_bybit_response_parser)
        param = sig.parameters["serializer"]
        assert param.kind == inspect.Parameter.KEYWORD_ONLY

    def test_all_params_keyword_only(self):
        sig = inspect.signature(create_bybit_response_parser)
        for name, param in sig.parameters.items():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY, (
                f"param {name!r} must be keyword-only"
            )

    def test_return_annotation_is_bybit_response_parser(self):
        hints = inspect.get_annotations(create_bybit_response_parser, eval_str=True)
        assert hints.get("return") is BybitResponseParser

    def test_positional_call_rejected(self):
        with pytest.raises(TypeError):
            create_bybit_response_parser(SpySerializer())


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_has_serializer_param(self):
        sig = inspect.signature(create_bybit_response_parser)
        assert "serializer" in sig.parameters

    def test_exactly_one_param(self):
        sig = inspect.signature(create_bybit_response_parser)
        assert len(sig.parameters) == 1

    def test_no_default_for_serializer(self):
        sig = inspect.signature(create_bybit_response_parser)
        assert sig.parameters["serializer"].default is inspect.Parameter.empty

    def test_does_not_receive_api_key(self):
        sig = inspect.signature(create_bybit_response_parser)
        assert "api_key" not in sig.parameters

    def test_does_not_receive_api_secret(self):
        sig = inspect.signature(create_bybit_response_parser)
        assert "api_secret" not in sig.parameters

    def test_does_not_receive_base_url(self):
        sig = inspect.signature(create_bybit_response_parser)
        assert "base_url" not in sig.parameters


# ---------------------------------------------------------------------------
# 3. Validación
# ---------------------------------------------------------------------------

class TestValidation:
    def test_accepts_valid_serializer(self):
        parser = create_bybit_response_parser(serializer=SpySerializer())
        assert parser is not None

    def test_accepts_structural_serializer(self):
        class AnonSerializer:
            def dumps(self, value: object) -> str:
                return "{}"
            def loads(self, value: str) -> object:
                return {}
        parser = create_bybit_response_parser(serializer=AnonSerializer())
        assert isinstance(parser, BybitResponseParser)

    def test_rejects_none(self):
        with pytest.raises(TypeError, match="JsonSerializer"):
            create_bybit_response_parser(serializer=None)

    def test_rejects_dict(self):
        with pytest.raises(TypeError, match="JsonSerializer"):
            create_bybit_response_parser(serializer={"dumps": None, "loads": None})

    def test_rejects_string(self):
        with pytest.raises(TypeError, match="JsonSerializer"):
            create_bybit_response_parser(serializer="json")

    def test_rejects_int(self):
        with pytest.raises(TypeError, match="JsonSerializer"):
            create_bybit_response_parser(serializer=42)

    def test_rejects_object_without_loads(self):
        class NoDumps:
            def loads(self, v: str) -> object:
                return {}
        with pytest.raises(TypeError, match="JsonSerializer"):
            create_bybit_response_parser(serializer=NoDumps())

    def test_rejects_object_without_dumps(self):
        class NoLoads:
            def dumps(self, v: object) -> str:
                return "{}"
        with pytest.raises(TypeError, match="JsonSerializer"):
            create_bybit_response_parser(serializer=NoLoads())

    def test_does_not_convert_value(self):
        with pytest.raises(TypeError):
            create_bybit_response_parser(serializer=None)

    def test_error_is_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_response_parser(serializer=object())

    def test_accepts_subclass_of_spy(self):
        class SubSpy(SpySerializer):
            pass
        parser = create_bybit_response_parser(serializer=SubSpy())
        assert isinstance(parser, BybitResponseParser)


# ---------------------------------------------------------------------------
# 4. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_returns_bybit_response_parser(self):
        parser = create_bybit_response_parser(serializer=SpySerializer())
        assert isinstance(parser, BybitResponseParser)

    def test_returns_exact_type(self):
        parser = create_bybit_response_parser(serializer=SpySerializer())
        assert type(parser) is BybitResponseParser

    def test_two_calls_return_different_parsers(self):
        s = SpySerializer()
        p1 = create_bybit_response_parser(serializer=s)
        p2 = create_bybit_response_parser(serializer=s)
        assert p1 is not p2

    def test_does_not_return_serializer(self):
        parser = create_bybit_response_parser(serializer=SpySerializer())
        assert not isinstance(parser, type(SpySerializer()))

    def test_does_not_return_tuple(self):
        parser = create_bybit_response_parser(serializer=SpySerializer())
        assert not isinstance(parser, tuple)

    def test_does_not_return_dict(self):
        parser = create_bybit_response_parser(serializer=SpySerializer())
        assert not isinstance(parser, dict)


# ---------------------------------------------------------------------------
# 5. Identidad
# ---------------------------------------------------------------------------

class TestIdentity:
    def test_serializer_stored_by_identity(self):
        spy = SpySerializer()
        parser = create_bybit_response_parser(serializer=spy)
        assert parser._serializer is spy

    def test_does_not_wrap_serializer(self):
        spy = SpySerializer()
        parser = create_bybit_response_parser(serializer=spy)
        assert type(parser._serializer) is SpySerializer

    def test_does_not_copy_serializer(self):
        spy = SpySerializer()
        parser = create_bybit_response_parser(serializer=spy)
        assert parser._serializer is spy

    def test_two_parsers_share_same_serializer(self):
        spy = SpySerializer()
        p1 = create_bybit_response_parser(serializer=spy)
        p2 = create_bybit_response_parser(serializer=spy)
        assert p1._serializer is spy
        assert p2._serializer is spy


# ---------------------------------------------------------------------------
# 6. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_calls_produce_distinct_parsers(self):
        s = SpySerializer()
        p1 = create_bybit_response_parser(serializer=s)
        p2 = create_bybit_response_parser(serializer=s)
        assert p1 is not p2

    def test_serializer_identity_preserved_across_calls(self):
        s = SpySerializer()
        p1 = create_bybit_response_parser(serializer=s)
        p2 = create_bybit_response_parser(serializer=s)
        assert p1._serializer is s
        assert p2._serializer is s

    def test_no_global_state_between_calls(self):
        s1 = SpySerializer()
        s2 = SpySerializer()
        p1 = create_bybit_response_parser(serializer=s1)
        p2 = create_bybit_response_parser(serializer=s2)
        assert p1._serializer is s1
        assert p2._serializer is s2

    def test_no_singleton_behavior(self):
        s = SpySerializer()
        parsers = [create_bybit_response_parser(serializer=s) for _ in range(5)]
        ids = [id(p) for p in parsers]
        assert len(set(ids)) == 5


# ---------------------------------------------------------------------------
# 7. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_serializer_dumps_not_called_during_construction(self):
        spy = SpySerializer()
        create_bybit_response_parser(serializer=spy)
        assert spy.dumps_calls == []

    def test_serializer_loads_not_called_during_construction(self):
        spy = SpySerializer()
        create_bybit_response_parser(serializer=spy)
        assert spy.loads_calls == []

    def test_no_serialization_at_all_during_construction(self):
        spy = SpySerializer()
        create_bybit_response_parser(serializer=spy)
        assert spy.dumps_calls == [] and spy.loads_calls == []

    def test_no_network_calls_during_construction(self):
        import socket
        network_calls = []
        original_connect = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original_connect(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_response_parser(serializer=SpySerializer())
        finally:
            socket.socket.connect = original_connect

        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        parser = create_bybit_response_parser(serializer=SpySerializer())
        assert isinstance(parser, BybitResponseParser)


# ---------------------------------------------------------------------------
# 8. Comportamiento integrado mínimo
# ---------------------------------------------------------------------------

class TestIntegratedBehavior:
    def test_parse_returns_bybit_response(self):
        spy = SpySerializer()
        parser = create_bybit_response_parser(serializer=spy)
        result = parser.parse(response_text='{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}')
        assert isinstance(result, BybitResponse)

    def test_parse_conserves_ret_code(self):
        class RetCodeSerializer:
            def dumps(self, v):
                return "{}"
            def loads(self, v):
                return {"retCode": 42, "retMsg": "X", "result": {}, "retExtInfo": {}, "time": 1}
        parser = create_bybit_response_parser(serializer=RetCodeSerializer())
        result = parser.parse(response_text="irrelevant")
        assert result.ret_code == 42

    def test_parse_conserves_ret_msg(self):
        class RetMsgSerializer:
            def dumps(self, v):
                return "{}"
            def loads(self, v):
                return {"retCode": 0, "retMsg": "Custom message", "result": {}, "retExtInfo": {}, "time": 1}
        parser = create_bybit_response_parser(serializer=RetMsgSerializer())
        result = parser.parse(response_text="irrelevant")
        assert result.ret_msg == "Custom message"

    def test_parse_conserves_result(self):
        payload = {"orderId": "abc123"}
        class ResultSerializer:
            def dumps(self, v):
                return "{}"
            def loads(self, v):
                return {"retCode": 0, "retMsg": "OK", "result": payload, "retExtInfo": {}, "time": 1}
        parser = create_bybit_response_parser(serializer=ResultSerializer())
        result = parser.parse(response_text="irrelevant")
        assert result.result == payload

    def test_serializer_loads_called_exactly_once(self):
        spy = SpySerializer()
        parser = create_bybit_response_parser(serializer=spy)
        parser.parse(response_text='{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}')
        assert len(spy.loads_calls) == 1

    def test_invalid_response_structure_raises_type_error(self):
        parser = create_bybit_response_parser(serializer=RejectingSerializer())
        with pytest.raises(TypeError):
            parser.parse(response_text="[]")

    def test_parse_does_not_call_dumps(self):
        spy = SpySerializer()
        parser = create_bybit_response_parser(serializer=spy)
        parser.parse(response_text='{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}')
        assert spy.dumps_calls == []


# ---------------------------------------------------------------------------
# 9. Integración compositiva con create_bybit_private_api y gateway
# ---------------------------------------------------------------------------

class TestCompositiveIntegration:
    def test_composition_builds_correctly(self):
        from execution_gateway.bybit_gateway import BybitExecutionGateway
        spy_serializer = SpySerializer()
        parser = create_bybit_response_parser(serializer=spy_serializer)
        spy_sender = SpySender()
        api = create_bybit_private_api(sender=spy_sender, response_parser=parser)
        gw = create_bybit_demo_execution_gateway(private_api=api)
        assert isinstance(gw, BybitExecutionGateway)

    def test_parser_identity_in_private_api(self):
        spy_serializer = SpySerializer()
        parser = create_bybit_response_parser(serializer=spy_serializer)
        api = create_bybit_private_api(sender=SpySender(), response_parser=parser)
        assert api._response_parser is parser

    def test_serializer_identity_reachable_through_api(self):
        spy_serializer = SpySerializer()
        parser = create_bybit_response_parser(serializer=spy_serializer)
        api = create_bybit_private_api(sender=SpySender(), response_parser=parser)
        assert api._response_parser._serializer is spy_serializer

    def test_sender_identity_in_private_api(self):
        spy_sender = SpySender()
        parser = create_bybit_response_parser(serializer=SpySerializer())
        api = create_bybit_private_api(sender=spy_sender, response_parser=parser)
        assert api._sender is spy_sender

    def test_no_execution_during_full_composition(self):
        spy_serializer = SpySerializer()
        spy_sender = SpySender()
        parser = create_bybit_response_parser(serializer=spy_serializer)
        api = create_bybit_private_api(sender=spy_sender, response_parser=parser)
        create_bybit_demo_execution_gateway(private_api=api)
        assert spy_serializer.dumps_calls == []
        assert spy_serializer.loads_calls == []
        assert spy_sender.calls == []

    def test_serializer_identity_reachable_through_gateway(self):
        spy_serializer = SpySerializer()
        parser = create_bybit_response_parser(serializer=spy_serializer)
        api = create_bybit_private_api(sender=SpySender(), response_parser=parser)
        gw = create_bybit_demo_execution_gateway(private_api=api)
        executor = gw._client._create_order_operation._endpoint_executor
        assert executor._private_api._response_parser._serializer is spy_serializer


# ---------------------------------------------------------------------------
# 10. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_know_api_key(self):
        src = inspect.getsource(create_bybit_response_parser)
        assert "api_key" not in src
        assert "API_KEY" not in src

    def test_does_not_know_api_secret(self):
        src = inspect.getsource(create_bybit_response_parser)
        assert "api_secret" not in src

    def test_does_not_import_transport(self):
        assert "UrllibHttpTransport" not in vars(_module)
        assert "HttpTransport" not in vars(_module)

    def test_does_not_import_sender(self):
        assert "BybitPrivateRequestSender" not in vars(_module)

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_signer(self):
        assert "HmacSha256Signer" not in vars(_module)

    def test_does_not_import_authenticator(self):
        assert "BybitAuthenticator" not in vars(_module)

    def test_does_not_import_clock(self):
        assert "MillisecondClock" not in vars(_module)
        assert "SystemMillisecondClock" not in vars(_module)

import inspect

import pytest

import execution_gateway
import execution_gateway.bybit_private_api_factory as _module
from execution_gateway.bybit_demo_execution_gateway_factory import (
    create_bybit_demo_execution_gateway,
)
from execution_gateway.bybit_private_api import BybitPrivateApi
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender import BybitPrivateRequestSender
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_parser import BybitResponseParser


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

class SpySender(BybitPrivateRequestSender):
    def __init__(self):
        self.calls: list[dict] = []

    def send(self, *, url: str, payload: object) -> str:
        self.calls.append({"url": url, "payload": payload})
        return '{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}'


class SpyParser(BybitResponseParser):
    def __init__(self):
        self.calls: list[dict] = []
        self._result: BybitResponse = BybitResponse(
            ret_code=0,
            ret_msg="OK",
            result={},
            ret_ext_info={},
            time_ms=1000,
        )

    def parse(self, *, response_text: str) -> BybitResponse:
        self.calls.append({"response_text": response_text})
        return self._result


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_private_api_factory import (
            create_bybit_private_api as f,
        )
        assert f is create_bybit_private_api

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_private_api")
        assert execution_gateway.create_bybit_private_api is create_bybit_private_api

    def test_included_in_all(self):
        assert "create_bybit_private_api" in execution_gateway.__all__

    def test_single_factory_for_bybit_private_api(self):
        factory_names = [
            name for name in vars(_module)
            if callable(getattr(_module, name))
            and "bybit_private_api" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_private_api"

    def test_sender_kwarg_required(self):
        with pytest.raises(TypeError):
            create_bybit_private_api(SpySender(), SpyParser())

    def test_all_params_keyword_only(self):
        sig = inspect.signature(create_bybit_private_api)
        for name, param in sig.parameters.items():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY, (
                f"param {name!r} must be keyword-only"
            )

    def test_return_annotation_is_bybit_private_api(self):
        hints = inspect.get_annotations(create_bybit_private_api, eval_str=True)
        assert hints.get("return") is BybitPrivateApi


# ---------------------------------------------------------------------------
# 2. Firma real
# ---------------------------------------------------------------------------

class TestSignature:
    def test_has_sender_param(self):
        sig = inspect.signature(create_bybit_private_api)
        assert "sender" in sig.parameters

    def test_has_response_parser_param(self):
        sig = inspect.signature(create_bybit_private_api)
        assert "response_parser" in sig.parameters

    def test_exactly_two_params(self):
        sig = inspect.signature(create_bybit_private_api)
        assert len(sig.parameters) == 2

    def test_does_not_receive_api_key(self):
        sig = inspect.signature(create_bybit_private_api)
        assert "api_key" not in sig.parameters

    def test_does_not_receive_api_secret(self):
        sig = inspect.signature(create_bybit_private_api)
        assert "api_secret" not in sig.parameters

    def test_does_not_receive_base_url(self):
        sig = inspect.signature(create_bybit_private_api)
        assert "base_url" not in sig.parameters

    def test_does_not_receive_environment_flag(self):
        sig = inspect.signature(create_bybit_private_api)
        assert "environment" not in sig.parameters
        assert "testnet" not in sig.parameters
        assert "mainnet" not in sig.parameters

    def test_no_default_for_sender(self):
        sig = inspect.signature(create_bybit_private_api)
        assert sig.parameters["sender"].default is inspect.Parameter.empty

    def test_no_default_for_response_parser(self):
        sig = inspect.signature(create_bybit_private_api)
        assert sig.parameters["response_parser"].default is inspect.Parameter.empty


# ---------------------------------------------------------------------------
# 3. Validación — sender
# ---------------------------------------------------------------------------

class TestValidationSender:
    def test_accepts_valid_sender(self):
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        assert api is not None

    def test_rejects_none_sender(self):
        with pytest.raises(TypeError, match="sender must be BybitPrivateRequestSender"):
            create_bybit_private_api(sender=None, response_parser=SpyParser())

    def test_rejects_dict_sender(self):
        with pytest.raises(TypeError, match="sender must be BybitPrivateRequestSender"):
            create_bybit_private_api(sender={"send": lambda: None}, response_parser=SpyParser())

    def test_rejects_string_sender(self):
        with pytest.raises(TypeError, match="sender must be BybitPrivateRequestSender"):
            create_bybit_private_api(sender="sender", response_parser=SpyParser())

    def test_rejects_arbitrary_object_sender(self):
        with pytest.raises(TypeError, match="sender must be BybitPrivateRequestSender"):
            create_bybit_private_api(sender=object(), response_parser=SpyParser())

    def test_rejects_int_sender(self):
        with pytest.raises(TypeError, match="sender must be BybitPrivateRequestSender"):
            create_bybit_private_api(sender=42, response_parser=SpyParser())

    def test_does_not_convert_sender(self):
        with pytest.raises(TypeError):
            create_bybit_private_api(sender=None, response_parser=SpyParser())

    def test_accepts_subclass_sender(self):
        class SubSender(SpySender):
            pass
        api = create_bybit_private_api(sender=SubSender(), response_parser=SpyParser())
        assert isinstance(api, BybitPrivateApi)


# ---------------------------------------------------------------------------
# 4. Validación — response_parser
# ---------------------------------------------------------------------------

class TestValidationResponseParser:
    def test_accepts_valid_parser(self):
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        assert api is not None

    def test_rejects_none_parser(self):
        with pytest.raises(TypeError, match="response_parser must be BybitResponseParser"):
            create_bybit_private_api(sender=SpySender(), response_parser=None)

    def test_rejects_dict_parser(self):
        with pytest.raises(TypeError, match="response_parser must be BybitResponseParser"):
            create_bybit_private_api(sender=SpySender(), response_parser={"parse": lambda: None})

    def test_rejects_string_parser(self):
        with pytest.raises(TypeError, match="response_parser must be BybitResponseParser"):
            create_bybit_private_api(sender=SpySender(), response_parser="parser")

    def test_rejects_arbitrary_object_parser(self):
        with pytest.raises(TypeError, match="response_parser must be BybitResponseParser"):
            create_bybit_private_api(sender=SpySender(), response_parser=object())

    def test_rejects_int_parser(self):
        with pytest.raises(TypeError, match="response_parser must be BybitResponseParser"):
            create_bybit_private_api(sender=SpySender(), response_parser=0)

    def test_does_not_convert_parser(self):
        with pytest.raises(TypeError):
            create_bybit_private_api(sender=SpySender(), response_parser=None)

    def test_accepts_subclass_parser(self):
        class SubParser(SpyParser):
            pass
        api = create_bybit_private_api(sender=SpySender(), response_parser=SubParser())
        assert isinstance(api, BybitPrivateApi)


# ---------------------------------------------------------------------------
# 5. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_returns_bybit_private_api(self):
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        assert isinstance(api, BybitPrivateApi)

    def test_returns_exact_type(self):
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        assert type(api) is BybitPrivateApi

    def test_two_calls_return_different_instances(self):
        s = SpySender()
        p = SpyParser()
        api1 = create_bybit_private_api(sender=s, response_parser=p)
        api2 = create_bybit_private_api(sender=s, response_parser=p)
        assert api1 is not api2

    def test_does_not_return_tuple(self):
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        assert not isinstance(api, tuple)

    def test_does_not_return_dict(self):
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        assert not isinstance(api, dict)

    def test_does_not_return_sender(self):
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        assert not isinstance(api, BybitPrivateRequestSender)

    def test_does_not_return_parser(self):
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        assert not isinstance(api, BybitResponseParser)


# ---------------------------------------------------------------------------
# 6. Grafo de dependencias
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def test_sender_stored_by_identity(self):
        spy_sender = SpySender()
        api = create_bybit_private_api(sender=spy_sender, response_parser=SpyParser())
        assert api._sender is spy_sender

    def test_response_parser_stored_by_identity(self):
        spy_parser = SpyParser()
        api = create_bybit_private_api(sender=SpySender(), response_parser=spy_parser)
        assert api._response_parser is spy_parser

    def test_both_dependencies_stored(self):
        spy_sender = SpySender()
        spy_parser = SpyParser()
        api = create_bybit_private_api(sender=spy_sender, response_parser=spy_parser)
        assert api._sender is spy_sender
        assert api._response_parser is spy_parser

    def test_does_not_wrap_sender(self):
        spy_sender = SpySender()
        api = create_bybit_private_api(sender=spy_sender, response_parser=SpyParser())
        assert type(api._sender) is SpySender

    def test_does_not_wrap_parser(self):
        spy_parser = SpyParser()
        api = create_bybit_private_api(sender=SpySender(), response_parser=spy_parser)
        assert type(api._response_parser) is SpyParser


# ---------------------------------------------------------------------------
# 7. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_calls_produce_distinct_instances(self):
        s = SpySender()
        p = SpyParser()
        api1 = create_bybit_private_api(sender=s, response_parser=p)
        api2 = create_bybit_private_api(sender=s, response_parser=p)
        assert api1 is not api2

    def test_sender_identity_preserved_across_calls(self):
        s = SpySender()
        p = SpyParser()
        api1 = create_bybit_private_api(sender=s, response_parser=p)
        api2 = create_bybit_private_api(sender=s, response_parser=p)
        assert api1._sender is s
        assert api2._sender is s

    def test_parser_identity_preserved_across_calls(self):
        s = SpySender()
        p = SpyParser()
        api1 = create_bybit_private_api(sender=s, response_parser=p)
        api2 = create_bybit_private_api(sender=s, response_parser=p)
        assert api1._response_parser is p
        assert api2._response_parser is p

    def test_no_global_state_between_calls(self):
        s1, p1 = SpySender(), SpyParser()
        s2, p2 = SpySender(), SpyParser()
        api1 = create_bybit_private_api(sender=s1, response_parser=p1)
        api2 = create_bybit_private_api(sender=s2, response_parser=p2)
        assert api1._sender is s1
        assert api2._sender is s2
        assert api1._response_parser is p1
        assert api2._response_parser is p2


# ---------------------------------------------------------------------------
# 8. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_sender_not_called_during_construction(self):
        spy = SpySender()
        create_bybit_private_api(sender=spy, response_parser=SpyParser())
        assert spy.calls == []

    def test_parser_not_called_during_construction(self):
        spy = SpyParser()
        create_bybit_private_api(sender=SpySender(), response_parser=spy)
        assert spy.calls == []

    def test_no_network_calls_during_construction(self):
        import socket
        network_calls = []
        original_connect = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original_connect(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        finally:
            socket.socket.connect = original_connect

        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel-key")
        monkeypatch.setenv("BYBIT_API_SECRET", "sentinel-secret")
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        assert isinstance(api, BybitPrivateApi)


# ---------------------------------------------------------------------------
# 9. Integración mínima con el gateway
# ---------------------------------------------------------------------------

class TestGatewayComposition:
    def test_gateway_builds_correctly(self):
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        gw = create_bybit_demo_execution_gateway(private_api=api)
        from execution_gateway.bybit_gateway import BybitExecutionGateway
        assert isinstance(gw, BybitExecutionGateway)

    def test_private_api_identity_in_executor(self):
        api = create_bybit_private_api(sender=SpySender(), response_parser=SpyParser())
        gw = create_bybit_demo_execution_gateway(private_api=api)
        executor = gw._client._create_order_operation._endpoint_executor
        assert executor._private_api is api

    def test_no_execution_during_composition(self):
        spy_sender = SpySender()
        spy_parser = SpyParser()
        api = create_bybit_private_api(sender=spy_sender, response_parser=spy_parser)
        create_bybit_demo_execution_gateway(private_api=api)
        assert spy_sender.calls == []
        assert spy_parser.calls == []

    def test_sender_identity_reachable_through_gateway(self):
        spy_sender = SpySender()
        api = create_bybit_private_api(sender=spy_sender, response_parser=SpyParser())
        gw = create_bybit_demo_execution_gateway(private_api=api)
        executor = gw._client._create_order_operation._endpoint_executor
        assert executor._private_api._sender is spy_sender

    def test_parser_identity_reachable_through_gateway(self):
        spy_parser = SpyParser()
        api = create_bybit_private_api(sender=SpySender(), response_parser=spy_parser)
        gw = create_bybit_demo_execution_gateway(private_api=api)
        executor = gw._client._create_order_operation._endpoint_executor
        assert executor._private_api._response_parser is spy_parser


# ---------------------------------------------------------------------------
# 10. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_know_api_key(self):
        src = inspect.getsource(create_bybit_private_api)
        assert "api_key" not in src
        assert "API_KEY" not in src

    def test_does_not_know_api_secret(self):
        src = inspect.getsource(create_bybit_private_api)
        assert "api_secret" not in src
        assert "API_SECRET" not in src

    def test_does_not_import_transport(self):
        assert "UrllibHttpTransport" not in vars(_module)
        assert "HttpTransport" not in vars(_module)

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_signer(self):
        assert "HmacSha256Signer" not in vars(_module)
        assert "MessageSigner" not in vars(_module)

    def test_does_not_import_authenticator(self):
        assert "BybitAuthenticator" not in vars(_module)
        assert "StandardBybitAuthenticator" not in vars(_module)

    def test_does_not_import_clock(self):
        assert "MillisecondClock" not in vars(_module)
        assert "SystemMillisecondClock" not in vars(_module)

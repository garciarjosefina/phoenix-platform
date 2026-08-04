import inspect

import pytest

import execution_gateway
import execution_gateway.bybit_demo_execution_gateway_env_bootstrap as _module
from execution_gateway import (
    BybitDemoExecutionConfig,
    EnvironmentConfigurationError,
    bootstrap_bybit_demo_execution_gateway_from_env,
)
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.urllib_http_transport import UrllibHttpTransport

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
        from execution_gateway.bybit_demo_execution_gateway_env_bootstrap import (
            bootstrap_bybit_demo_execution_gateway_from_env as f,
        )
        assert f is bootstrap_bybit_demo_execution_gateway_from_env

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "bootstrap_bybit_demo_execution_gateway_from_env")
        assert (
            execution_gateway.bootstrap_bybit_demo_execution_gateway_from_env
            is bootstrap_bybit_demo_execution_gateway_from_env
        )

    def test_included_in_all(self):
        assert "bootstrap_bybit_demo_execution_gateway_from_env" in execution_gateway.__all__

    def test_callable(self):
        assert callable(bootstrap_bybit_demo_execution_gateway_from_env)

    def test_single_public_function_in_module(self):
        public = [
            n for n in vars(_module)
            if not n.startswith("_") and inspect.isfunction(getattr(_module, n))
            and getattr(_module, n).__module__ == _module.__name__
        ]
        assert public == ["bootstrap_bybit_demo_execution_gateway_from_env"]

    def test_no_alternative_names_exist(self):
        for alias in (
            "create_gateway_from_env", "load_gateway", "from_env",
            "bootstrap_gateway", "create_bybit_gateway_from_environment",
        ):
            assert not hasattr(execution_gateway, alias)
            assert alias not in execution_gateway.__all__


class TestSignature:
    def test_exactly_one_parameter(self):
        sig = inspect.signature(bootstrap_bybit_demo_execution_gateway_from_env)
        assert len(sig.parameters) == 1

    def test_parameter_named_environ(self):
        sig = inspect.signature(bootstrap_bybit_demo_execution_gateway_from_env)
        assert "environ" in sig.parameters

    def test_parameter_is_keyword_only(self):
        sig = inspect.signature(bootstrap_bybit_demo_execution_gateway_from_env)
        assert sig.parameters["environ"].kind == inspect.Parameter.KEYWORD_ONLY

    def test_parameter_defaults_to_none(self):
        sig = inspect.signature(bootstrap_bybit_demo_execution_gateway_from_env)
        assert sig.parameters["environ"].default is None

    def test_return_annotation_is_bybit_execution_gateway(self):
        hints = inspect.get_annotations(bootstrap_bybit_demo_execution_gateway_from_env, eval_str=True)
        assert hints.get("return") is BybitExecutionGateway

    def test_environ_annotation(self):
        hints = inspect.get_annotations(bootstrap_bybit_demo_execution_gateway_from_env, eval_str=True)
        assert str(hints.get("environ")).replace("collections.abc.", "") == "Mapping[str, str] | None"

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            bootstrap_bybit_demo_execution_gateway_from_env(_VALID_ENV)

    def test_no_unknown_kwargs_accepted(self):
        with pytest.raises(TypeError):
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV, extra=True)


# ---------------------------------------------------------------------------
# 2. Composición exacta
# ---------------------------------------------------------------------------

class TestExactComposition:
    def test_loader_called_exactly_once(self, monkeypatch):
        calls = []
        original = _module.load_bybit_demo_execution_config_from_env

        def spy(*, environ=None):
            calls.append(environ)
            return original(environ=environ)

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", spy)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert len(calls) == 1

    def test_composition_root_called_exactly_once(self, monkeypatch):
        calls = []
        original = _module.create_configured_bybit_demo_execution_gateway

        def spy(*, config):
            calls.append(config)
            return original(config=config)

        monkeypatch.setattr(_module, "create_configured_bybit_demo_execution_gateway", spy)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert len(calls) == 1

    def test_order_loader_before_composition_root(self, monkeypatch):
        log = []
        original_loader = _module.load_bybit_demo_execution_config_from_env
        original_root = _module.create_configured_bybit_demo_execution_gateway

        def spy_loader(*, environ=None):
            log.append("loader")
            return original_loader(environ=environ)

        def spy_root(*, config):
            log.append("root")
            return original_root(config=config)

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", spy_loader)
        monkeypatch.setattr(_module, "create_configured_bybit_demo_execution_gateway", spy_root)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert log == ["loader", "root"]

    def test_config_passed_to_composition_root_by_identity(self, monkeypatch):
        captured_config = {}
        original_loader = _module.load_bybit_demo_execution_config_from_env
        original_root = _module.create_configured_bybit_demo_execution_gateway

        def spy_loader(*, environ=None):
            cfg = original_loader(environ=environ)
            captured_config["value"] = cfg
            return cfg

        def spy_root(*, config):
            assert config is captured_config["value"]
            return original_root(config=config)

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", spy_loader)
        monkeypatch.setattr(_module, "create_configured_bybit_demo_execution_gateway", spy_root)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)

    def test_result_is_composition_root_result_by_identity(self, monkeypatch):
        produced = {}
        original_root = _module.create_configured_bybit_demo_execution_gateway

        def spy_root(*, config):
            gw = original_root(config=config)
            produced["value"] = gw
            return gw

        monkeypatch.setattr(_module, "create_configured_bybit_demo_execution_gateway", spy_root)
        result = bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert result is produced["value"]

    def test_does_not_call_lower_factories_directly(self):
        src = inspect.getsource(_module)
        forbidden = [
            "create_bybit_demo_credentials(", "create_message_signer(", "create_millisecond_clock(",
            "create_bybit_recv_window_ms(", "create_bybit_authenticator(", "create_json_serializer(",
            "create_bybit_header_builder(", "create_bybit_request_builder(", "create_bybit_response_parser(",
            "create_http_transport(", "create_http_timeout_seconds(", "create_http_request_executor(",
            "create_bybit_private_request_sender(", "create_bybit_private_api(",
            "create_bybit_demo_execution_gateway(", "create_bybit_demo_client(",
            "BybitExecutionGateway(", "BybitDemoClient(",
        ]
        for f in forbidden:
            assert f not in src, f"{f} debe delegarse, no llamarse directamente"

    def test_source_only_calls_the_two_authorized_functions(self):
        src = inspect.getsource(_module.bootstrap_bybit_demo_execution_gateway_from_env)
        assert "load_bybit_demo_execution_config_from_env(" in src
        assert "create_configured_bybit_demo_execution_gateway(" in src


# ---------------------------------------------------------------------------
# 3. Mapping explícito
# ---------------------------------------------------------------------------

class TestExplicitMapping:
    def test_reaches_loader_by_identity(self, monkeypatch):
        marker = dict(_VALID_ENV)
        received = {}
        original = _module.load_bybit_demo_execution_config_from_env

        def spy(*, environ=None):
            received["value"] = environ
            return original(environ=environ)

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", spy)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=marker)
        assert received["value"] is marker

    def test_does_not_consult_os_environ(self, monkeypatch):
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "POISONED")
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_SECRET", "POISONED")
        monkeypatch.setenv("PHOENIX_BYBIT_RECV_WINDOW_MS", "1")
        monkeypatch.setenv("PHOENIX_HTTP_TIMEOUT_SECONDS", "1")
        gateway = bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        credentials = (
            gateway._client._create_order_operation._endpoint_executor
            ._private_api._sender._request_builder._authenticator._credentials
        )
        assert credentials.api_key == "demo-key"

    def test_does_not_convert_to_dict(self, monkeypatch):
        received = {}
        original = _module.load_bybit_demo_execution_config_from_env

        def spy(*, environ=None):
            received["type"] = type(environ)
            return original(environ=environ)

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", spy)

        class _CustomMapping(dict):
            pass

        m = _CustomMapping(_VALID_ENV)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=m)
        assert received["type"] is _CustomMapping

    def test_does_not_mutate_the_mapping(self):
        m = dict(_VALID_ENV)
        before = dict(m)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=m)
        assert m == before

    def test_does_not_retain_reference_after_returning(self):
        m = dict(_VALID_ENV)
        gateway = bootstrap_bybit_demo_execution_gateway_from_env(environ=m)
        m["PHOENIX_BYBIT_DEMO_API_KEY"] = "mutated-after-call"
        credentials = (
            gateway._client._create_order_operation._endpoint_executor
            ._private_api._sender._request_builder._authenticator._credentials
        )
        assert credentials.api_key == "demo-key"

    def test_changes_between_calls_are_observed(self):
        m = dict(_VALID_ENV)
        g1 = bootstrap_bybit_demo_execution_gateway_from_env(environ=m)
        m["PHOENIX_BYBIT_RECV_WINDOW_MS"] = "9999"
        g2 = bootstrap_bybit_demo_execution_gateway_from_env(environ=m)
        a1 = g1._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator
        a2 = g2._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator
        assert a1._recv_window_ms == 5000
        assert a2._recv_window_ms == 9999


# ---------------------------------------------------------------------------
# 4. environ=None
# ---------------------------------------------------------------------------

class TestEnvironNone:
    def test_passes_none_to_loader(self, monkeypatch):
        received = {}
        original = _module.load_bybit_demo_execution_config_from_env

        def spy(*, environ=None):
            received["value"] = environ
            return original(environ=environ)

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", spy)
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "real-key")
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_SECRET", "real-secret")
        monkeypatch.setenv("PHOENIX_BYBIT_RECV_WINDOW_MS", "5000")
        monkeypatch.setenv("PHOENIX_HTTP_TIMEOUT_SECONDS", "10")
        bootstrap_bybit_demo_execution_gateway_from_env()
        assert received["value"] is None

    def test_does_not_access_os_environ_directly(self):
        src = inspect.getsource(_module)
        assert "os.environ" not in src
        assert "os.getenv" not in src
        assert "import os" not in src

    def test_reads_real_environment_via_loader(self, monkeypatch):
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "real-key")
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_SECRET", "real-secret")
        monkeypatch.setenv("PHOENIX_BYBIT_RECV_WINDOW_MS", "6000")
        monkeypatch.setenv("PHOENIX_HTTP_TIMEOUT_SECONDS", "12.5")
        gateway = bootstrap_bybit_demo_execution_gateway_from_env()
        credentials = (
            gateway._client._create_order_operation._endpoint_executor
            ._private_api._sender._request_builder._authenticator._credentials
        )
        assert credentials.api_key == "real-key"
        assert credentials.api_secret == "real-secret"


# ---------------------------------------------------------------------------
# 5. Error del loader
# ---------------------------------------------------------------------------

class _LoaderMarkerError(Exception):
    pass


class TestLoaderErrorPropagation:
    def test_propagates_by_identity(self, monkeypatch):
        original = _LoaderMarkerError("loader exploded")

        def broken(*, environ=None):
            raise original

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", broken)
        with pytest.raises(_LoaderMarkerError) as exc_info:
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert exc_info.value is original

    def test_composition_root_not_called(self, monkeypatch):
        calls = []

        def broken(*, environ=None):
            raise _LoaderMarkerError("boom")

        def spy_root(*, config):
            calls.append(config)
            raise AssertionError("composition root must not be called")

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", broken)
        monkeypatch.setattr(_module, "create_configured_bybit_demo_execution_gateway", spy_root)
        with pytest.raises(_LoaderMarkerError):
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert calls == []

    def test_not_wrapped(self, monkeypatch):
        def broken(*, environ=None):
            raise _LoaderMarkerError("boom")

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", broken)
        with pytest.raises(_LoaderMarkerError) as exc_info:
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert exc_info.value.__cause__ is None

    def test_loader_called_only_once_on_failure(self, monkeypatch):
        calls = []

        def broken(*, environ=None):
            calls.append(1)
            raise _LoaderMarkerError("boom")

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", broken)
        with pytest.raises(_LoaderMarkerError):
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert calls == [1]

    def test_real_environment_configuration_error_propagates(self):
        with pytest.raises(EnvironmentConfigurationError):
            bootstrap_bybit_demo_execution_gateway_from_env(environ={})


# ---------------------------------------------------------------------------
# 6. Error del composition root
# ---------------------------------------------------------------------------

class _RootMarkerError(Exception):
    pass


class TestCompositionRootErrorPropagation:
    def test_propagates_by_identity(self, monkeypatch):
        original = _RootMarkerError("root exploded")

        def broken(*, config):
            raise original

        monkeypatch.setattr(_module, "create_configured_bybit_demo_execution_gateway", broken)
        with pytest.raises(_RootMarkerError) as exc_info:
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert exc_info.value is original

    def test_loader_called_exactly_once(self, monkeypatch):
        calls = []
        original_loader = _module.load_bybit_demo_execution_config_from_env

        def spy_loader(*, environ=None):
            calls.append(1)
            return original_loader(environ=environ)

        def broken_root(*, config):
            raise _RootMarkerError("boom")

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", spy_loader)
        monkeypatch.setattr(_module, "create_configured_bybit_demo_execution_gateway", broken_root)
        with pytest.raises(_RootMarkerError):
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert calls == [1]

    def test_composition_root_called_exactly_once(self, monkeypatch):
        calls = []

        def broken_root(*, config):
            calls.append(config)
            raise _RootMarkerError("boom")

        monkeypatch.setattr(_module, "create_configured_bybit_demo_execution_gateway", broken_root)
        with pytest.raises(_RootMarkerError):
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert len(calls) == 1

    def test_not_wrapped(self, monkeypatch):
        def broken_root(*, config):
            raise _RootMarkerError("boom")

        monkeypatch.setattr(_module, "create_configured_bybit_demo_execution_gateway", broken_root)
        with pytest.raises(_RootMarkerError) as exc_info:
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert exc_info.value.__cause__ is None

    def test_no_partial_result_returned(self, monkeypatch):
        def broken_root(*, config):
            raise _RootMarkerError("boom")

        monkeypatch.setattr(_module, "create_configured_bybit_demo_execution_gateway", broken_root)
        result = None
        try:
            result = bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
            pytest.fail("expected _RootMarkerError")
        except _RootMarkerError:
            pass
        assert result is None


# ---------------------------------------------------------------------------
# 7. Integración productiva válida
# ---------------------------------------------------------------------------

class TestValidProductionIntegration:
    def _gateway(self):
        return bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)

    def test_returns_bybit_execution_gateway(self):
        assert isinstance(self._gateway(), BybitExecutionGateway)

    def test_credentials_applied_exactly(self):
        gw = self._gateway()
        credentials = (
            gw._client._create_order_operation._endpoint_executor
            ._private_api._sender._request_builder._authenticator._credentials
        )
        assert credentials.api_key == "demo-key"
        assert credentials.api_secret == "demo-secret"

    def test_recv_window_applied_exactly(self):
        gw = self._gateway()
        authenticator = (
            gw._client._create_order_operation._endpoint_executor
            ._private_api._sender._request_builder._authenticator
        )
        assert authenticator._recv_window_ms == 5000

    def test_timeout_applied_as_float_ten(self):
        gw = self._gateway()
        executor = gw._client._create_order_operation._endpoint_executor._private_api._sender._request_executor
        assert executor._timeout_seconds == 10.0
        assert type(executor._timeout_seconds) is float

    def test_base_url_is_bybit_demo(self):
        gw = self._gateway()
        url_builder = gw._client._create_order_operation._endpoint_executor._url_builder
        assert url_builder._base_url == "https://api-demo.bybit.com"

    def test_transport_is_urllib_http_transport(self):
        gw = self._gateway()
        transport = gw._client._create_order_operation._endpoint_executor._private_api._sender._request_executor._transport
        assert isinstance(transport, UrllibHttpTransport)

    def test_no_network_executed(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        self._gateway()
        assert called == []


# ---------------------------------------------------------------------------
# 8. Dos llamadas — independencia
# ---------------------------------------------------------------------------

class TestTwoCallsIndependence:
    def _envs(self):
        env1 = _env(
            PHOENIX_BYBIT_DEMO_API_KEY="key-one", PHOENIX_BYBIT_DEMO_API_SECRET="secret-one",
            PHOENIX_BYBIT_RECV_WINDOW_MS="1000", PHOENIX_HTTP_TIMEOUT_SECONDS="1.0",
        )
        env2 = _env(
            PHOENIX_BYBIT_DEMO_API_KEY="key-two", PHOENIX_BYBIT_DEMO_API_SECRET="secret-two",
            PHOENIX_BYBIT_RECV_WINDOW_MS="2000", PHOENIX_HTTP_TIMEOUT_SECONDS="2.0",
        )
        return env1, env2

    def _chain(self, gw):
        auth = (
            gw._client._create_order_operation._endpoint_executor
            ._private_api._sender._request_builder._authenticator
        )
        return dict(
            gateway=gw, client=gw._client, operation=gw._client._create_order_operation,
            endpoint_executor=gw._client._create_order_operation._endpoint_executor,
            private_api=gw._client._create_order_operation._endpoint_executor._private_api,
            sender=gw._client._create_order_operation._endpoint_executor._private_api._sender,
            request_builder=gw._client._create_order_operation._endpoint_executor._private_api._sender._request_builder,
            executor=gw._client._create_order_operation._endpoint_executor._private_api._sender._request_executor,
            transport=gw._client._create_order_operation._endpoint_executor._private_api._sender._request_executor._transport,
            authenticator=auth, credentials=auth._credentials,
        )

    def test_two_gateways_distinct(self):
        env1, env2 = self._envs()
        g1 = bootstrap_bybit_demo_execution_gateway_from_env(environ=env1)
        g2 = bootstrap_bybit_demo_execution_gateway_from_env(environ=env2)
        c1, c2 = self._chain(g1), self._chain(g2)
        for key in c1:
            assert c1[key] is not c2[key], f"{key} debe ser un objeto distinto en cada grafo"

    def test_credentials_values_correct_in_each_graph(self):
        env1, env2 = self._envs()
        g1 = bootstrap_bybit_demo_execution_gateway_from_env(environ=env1)
        g2 = bootstrap_bybit_demo_execution_gateway_from_env(environ=env2)
        c1, c2 = self._chain(g1)["credentials"], self._chain(g2)["credentials"]
        assert c1.api_key == "key-one" and c1.api_secret == "secret-one"
        assert c2.api_key == "key-two" and c2.api_secret == "secret-two"

    def test_recv_window_and_timeout_correct_in_each_graph(self):
        env1, env2 = self._envs()
        g1 = bootstrap_bybit_demo_execution_gateway_from_env(environ=env1)
        g2 = bootstrap_bybit_demo_execution_gateway_from_env(environ=env2)
        a1, a2 = self._chain(g1)["authenticator"], self._chain(g2)["authenticator"]
        e1, e2 = self._chain(g1)["executor"], self._chain(g2)["executor"]
        assert a1._recv_window_ms == 1000 and a2._recv_window_ms == 2000
        assert e1._timeout_seconds == 1.0 and e2._timeout_seconds == 2.0

    def test_configs_distinct(self, monkeypatch):
        env1, env2 = self._envs()
        configs = []
        original = _module.load_bybit_demo_execution_config_from_env

        def spy(*, environ=None):
            cfg = original(environ=environ)
            configs.append(cfg)
            return cfg

        monkeypatch.setattr(_module, "load_bybit_demo_execution_config_from_env", spy)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=env1)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=env2)
        assert configs[0] is not configs[1]
        assert configs[0] != configs[1]


# ---------------------------------------------------------------------------
# 9. Ausencia de ejecución
# ---------------------------------------------------------------------------

class TestNoExecutionDuringBootstrap:
    def test_no_urlopen(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert called == []

    def test_no_socket_connect(self):
        import socket
        calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        finally:
            socket.socket.connect = original
        assert calls == []

    def test_no_dns_resolution(self, monkeypatch):
        import socket
        calls = []
        original = socket.getaddrinfo

        def patched(*args, **kwargs):
            calls.append(args)
            return original(*args, **kwargs)

        monkeypatch.setattr(socket, "getaddrinfo", patched)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert calls == []

    def test_no_clock_read(self, monkeypatch):
        import time
        calls = []
        original_ns = time.time_ns

        def spy_ns():
            calls.append(True)
            return original_ns()

        monkeypatch.setattr(time, "time_ns", spy_ns)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert calls == []

    def test_no_signing(self, monkeypatch):
        from execution_gateway.hmac_sha256_signer import HmacSha256Signer
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert calls == []

    def test_no_authentication_call(self, monkeypatch):
        from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator
        calls = []
        original = StandardBybitAuthenticator.authenticate

        def spy(self, *, body):
            calls.append(True)
            return original(self, body=body)

        monkeypatch.setattr(StandardBybitAuthenticator, "authenticate", spy)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert calls == []

    def test_no_serializer_dumps(self, monkeypatch):
        from execution_gateway.standard_json_serializer import StandardJsonSerializer

        def explode(self, value):
            raise AssertionError("dumps must not be called during bootstrap")

        monkeypatch.setattr(StandardJsonSerializer, "dumps", explode)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)

    def test_no_serializer_loads(self, monkeypatch):
        from execution_gateway.standard_json_serializer import StandardJsonSerializer

        def explode(self, value):
            raise AssertionError("loads must not be called during bootstrap")

        monkeypatch.setattr(StandardJsonSerializer, "loads", explode)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)

    def test_no_header_building(self, monkeypatch):
        from execution_gateway.bybit_header_builder import BybitHeaderBuilder

        def explode(self, *, authentication):
            raise AssertionError("header builder must not be called during bootstrap")

        monkeypatch.setattr(BybitHeaderBuilder, "build", explode)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)

    def test_no_transport_post(self, monkeypatch):
        calls = []
        original_post = UrllibHttpTransport.post

        def spy_post(self, *, url, headers, body, timeout_seconds):
            calls.append(url)
            return original_post(self, url=url, headers=headers, body=body, timeout_seconds=timeout_seconds)

        monkeypatch.setattr(UrllibHttpTransport, "post", spy_post)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert calls == []

    def test_no_order_creation(self, monkeypatch):
        from execution_gateway.bybit_create_order_operation import BybitCreateOrderOperation

        def explode(self, *, request):
            raise AssertionError("no order must be created during bootstrap")

        monkeypatch.setattr(BybitCreateOrderOperation, "execute", explode)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)

    def test_no_print(self, capsys):
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_no_file_reads(self, monkeypatch):
        calls = []
        original_open = open

        def spy_open(*args, **kwargs):
            calls.append(args)
            return original_open(*args, **kwargs)

        import builtins
        monkeypatch.setattr(builtins, "open", spy_open)
        bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert calls == []


# ---------------------------------------------------------------------------
# 10. Seguridad
# ---------------------------------------------------------------------------

class TestSecurity:
    _MARKER = "ZZSUPERSECRETBOOTSTRAP9999"

    def test_marker_absent_from_gateway_repr(self):
        gw = bootstrap_bybit_demo_execution_gateway_from_env(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        )
        assert self._MARKER not in repr(gw)

    def test_marker_absent_from_gateway_str(self):
        gw = bootstrap_bybit_demo_execution_gateway_from_env(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        )
        assert self._MARKER not in str(gw)

    def test_marker_absent_from_missing_variable_error(self):
        env = {"PHOENIX_BYBIT_DEMO_API_SECRET": self._MARKER}
        error = _raised(lambda: bootstrap_bybit_demo_execution_gateway_from_env(environ=env))
        assert error is not None
        assert self._MARKER not in str(error)

    def test_marker_absent_from_numeric_conversion_error(self):
        env = _env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER, PHOENIX_BYBIT_RECV_WINDOW_MS="abc")
        error = _raised(lambda: bootstrap_bybit_demo_execution_gateway_from_env(environ=env))
        assert error is not None
        assert self._MARKER not in str(error)

    def test_marker_absent_from_module_source(self):
        src = inspect.getsource(_module)
        assert self._MARKER not in src

    def test_secret_still_present_internally_for_authentication(self):
        gw = bootstrap_bybit_demo_execution_gateway_from_env(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        )
        credentials = (
            gw._client._create_order_operation._endpoint_executor
            ._private_api._sender._request_builder._authenticator._credentials
        )
        assert credentials.api_secret == self._MARKER

    def test_does_not_expose_repr_of_config(self):
        src = inspect.getsource(_module)
        assert "repr(config)" not in src

    def test_does_not_return_config(self):
        gw = bootstrap_bybit_demo_execution_gateway_from_env(environ=_VALID_ENV)
        assert not isinstance(gw, BybitDemoExecutionConfig)
        assert not hasattr(gw, "api_key")
        assert not hasattr(gw, "api_secret")


# ---------------------------------------------------------------------------
# 11. Superficie mínima
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_no_os_environ_reference(self):
        src = inspect.getsource(_module)
        assert "os.environ" not in src

    def test_no_os_getenv_reference(self):
        src = inspect.getsource(_module)
        assert "os.getenv" not in src

    def test_no_dotenv_reference(self):
        src = inspect.getsource(_module)
        assert "dotenv" not in src.lower()

    def test_no_railway_reference(self):
        src = inspect.getsource(_module)
        assert "railway" not in src.lower()

    def test_no_socket_reference(self):
        src = inspect.getsource(_module)
        assert "socket" not in src

    def test_no_urllib_reference(self):
        src = inspect.getsource(_module)
        assert "urllib" not in src

    def test_no_time_reference(self):
        src = inspect.getsource(_module)
        assert "import time" not in src
        assert "time.time" not in src

    def test_no_signer_reference(self):
        src = inspect.getsource(_module)
        assert "Signer" not in src

    def test_no_transport_reference(self):
        src = inspect.getsource(_module)
        assert "Transport" not in src

    def test_no_retry_logic(self):
        src = inspect.getsource(_module)
        assert "retry" not in src.lower()
        assert "retries" not in src.lower()

    def test_no_logging_reference(self):
        src = inspect.getsource(_module)
        assert "logging" not in src

    def test_no_print_in_source(self):
        src = inspect.getsource(_module)
        assert "print(" not in src

    def test_no_mutable_globals(self):
        mutable = [
            n for n, o in vars(_module).items()
            if not n.startswith("__") and isinstance(o, (list, dict, set))
        ]
        assert mutable == []

    def test_no_cache_or_memoization(self):
        src = inspect.getsource(_module)
        assert "cache" not in src.lower()
        assert "memo" not in src.lower()

    def test_no_mainnet_testnet_selection(self):
        src = inspect.getsource(_module)
        assert "mainnet" not in src.lower()
        assert "testnet" not in src.lower()

    def test_no_order_execution_reference(self):
        src = inspect.getsource(_module)
        assert "execute(" not in src
        assert "place_order" not in src

    def test_module_imports_are_minimal(self):
        expected = {
            "BybitExecutionGateway",
            "Mapping",
            "bootstrap_bybit_demo_execution_gateway_from_env",
            "create_configured_bybit_demo_execution_gateway",
            "load_bybit_demo_execution_config_from_env",
        }
        actual = {
            n for n in vars(_module)
            if not n.startswith("_") and (inspect.isclass(getattr(_module, n)) or inspect.isfunction(getattr(_module, n)))
        }
        assert actual == expected


# ---------------------------------------------------------------------------
# 12. Integración negativa
# ---------------------------------------------------------------------------

class TestNegativeIntegration:
    def test_missing_api_key(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        env = {k: v for k, v in _VALID_ENV.items() if k != "PHOENIX_BYBIT_DEMO_API_KEY"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_KEY"):
            bootstrap_bybit_demo_execution_gateway_from_env(environ=env)
        assert called == []

    def test_missing_api_secret(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        env = {k: v for k, v in _VALID_ENV.items() if k != "PHOENIX_BYBIT_DEMO_API_SECRET"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_SECRET"):
            bootstrap_bybit_demo_execution_gateway_from_env(environ=env)
        assert called == []

    def test_invalid_recv_window(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_RECV_WINDOW_MS"):
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_env(PHOENIX_BYBIT_RECV_WINDOW_MS="abc"))
        assert called == []

    def test_invalid_timeout(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_HTTP_TIMEOUT_SECONDS"):
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="abc"))
        assert called == []

    def test_timeout_nan(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        with pytest.raises(ValueError, match="finite") as exc_info:
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="nan"))
        assert not isinstance(exc_info.value, EnvironmentConfigurationError)
        assert called == []

    def test_timeout_infinite(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        with pytest.raises(ValueError, match="finite") as exc_info:
            bootstrap_bybit_demo_execution_gateway_from_env(environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="inf"))
        assert not isinstance(exc_info.value, EnvironmentConfigurationError)
        assert called == []

    def test_no_secret_leaked_across_negative_cases(self):
        marker = "ZZSUPERSECRETBOOTSTRAP9999"
        cases = [
            {k: v for k, v in _env(PHOENIX_BYBIT_DEMO_API_SECRET=marker).items() if k != "PHOENIX_BYBIT_DEMO_API_KEY"},
            _env(PHOENIX_BYBIT_DEMO_API_SECRET=marker, PHOENIX_BYBIT_RECV_WINDOW_MS="abc"),
            _env(PHOENIX_BYBIT_DEMO_API_SECRET=marker, PHOENIX_HTTP_TIMEOUT_SECONDS="nan"),
        ]
        for env in cases:
            error = _raised(lambda e=env: bootstrap_bybit_demo_execution_gateway_from_env(environ=e))
            assert error is not None
            assert marker not in str(error)

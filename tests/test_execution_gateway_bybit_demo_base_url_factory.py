import inspect

import pytest

import execution_gateway
import execution_gateway.bybit_demo_base_url_factory as _module
from execution_gateway.bybit_authenticator_factory import create_bybit_authenticator
from execution_gateway.bybit_demo_base_url_factory import create_bybit_demo_base_url
from execution_gateway.bybit_demo_client_factory import create_bybit_demo_client
from execution_gateway.bybit_demo_credentials_factory import create_bybit_demo_credentials
from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder_factory import create_bybit_header_builder
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import create_bybit_private_request_sender
from execution_gateway.bybit_recv_window_factory import create_bybit_recv_window_ms
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.hmac_sha256_signer import HmacSha256Signer
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.http_timeout_factory import create_http_timeout_seconds
from execution_gateway.http_transport_factory import create_http_transport
from execution_gateway.json_serializer_factory import create_json_serializer
from execution_gateway.message_signer_factory import create_message_signer
from execution_gateway.millisecond_clock_factory import create_millisecond_clock
from execution_gateway.system_millisecond_clock import SystemMillisecondClock
from execution_gateway.urllib_http_transport import UrllibHttpTransport


_VALID_KEY = "demo-key"
_VALID_SECRET = "demo-secret"
_VALID_URL = "https://api-demo.bybit.com"


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_demo_base_url_factory import create_bybit_demo_base_url as f
        assert f is create_bybit_demo_base_url

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_demo_base_url")
        assert execution_gateway.create_bybit_demo_base_url is create_bybit_demo_base_url

    def test_included_in_all(self):
        assert "create_bybit_demo_base_url" in execution_gateway.__all__

    def test_single_factory_for_base_url(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "base_url" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_demo_base_url"

    def test_callable(self):
        assert callable(create_bybit_demo_base_url)

    def test_return_annotation_is_str(self):
        hints = inspect.get_annotations(create_bybit_demo_base_url, eval_str=True)
        assert hints.get("return") is str


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_exactly_one_parameter(self):
        sig = inspect.signature(create_bybit_demo_base_url)
        assert len(sig.parameters) == 1

    def test_parameter_is_keyword_only(self):
        sig = inspect.signature(create_bybit_demo_base_url)
        param = sig.parameters["base_url"]
        assert param.kind == inspect.Parameter.KEYWORD_ONLY

    def test_parameter_named_base_url(self):
        sig = inspect.signature(create_bybit_demo_base_url)
        assert "base_url" in sig.parameters

    def test_no_credentials_parameter(self):
        sig = inspect.signature(create_bybit_demo_base_url)
        assert "credentials" not in sig.parameters

    def test_no_transport_parameter(self):
        sig = inspect.signature(create_bybit_demo_base_url)
        assert "transport" not in sig.parameters

    def test_no_timeout_parameter(self):
        sig = inspect.signature(create_bybit_demo_base_url)
        assert "timeout_seconds" not in sig.parameters

    def test_no_environment_parameter(self):
        sig = inspect.signature(create_bybit_demo_base_url)
        assert "environment" not in sig.parameters

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            create_bybit_demo_base_url(_VALID_URL)

    def test_no_unknown_kwargs_accepted(self):
        with pytest.raises(TypeError):
            create_bybit_demo_base_url(base_url=_VALID_URL, extra=True)


# ---------------------------------------------------------------------------
# 3. Valores válidos
# ---------------------------------------------------------------------------

class TestValidValues:
    def test_canonical_demo_url_accepted(self):
        result = create_bybit_demo_base_url(base_url=_VALID_URL)
        assert result == _VALID_URL

    def test_other_valid_https_host_accepted(self):
        url = "https://example.com"
        result = create_bybit_demo_base_url(base_url=url)
        assert result == url

    def test_https_host_with_port_accepted(self):
        url = "https://example.com:8080"
        result = create_bybit_demo_base_url(base_url=url)
        assert result == url

    def test_returns_str(self):
        result = create_bybit_demo_base_url(base_url=_VALID_URL)
        assert isinstance(result, str)

    def test_returns_exact_type_str(self):
        result = create_bybit_demo_base_url(base_url=_VALID_URL)
        assert type(result) is str


# ---------------------------------------------------------------------------
# 4. Validación — tipo
# ---------------------------------------------------------------------------

class TestTypeValidation:
    def test_none_raises_type_error(self):
        with pytest.raises(TypeError, match="base_url must be str, got: NoneType"):
            create_bybit_demo_base_url(base_url=None)

    def test_int_raises_type_error(self):
        with pytest.raises(TypeError, match="base_url must be str, got: int"):
            create_bybit_demo_base_url(base_url=443)

    def test_bool_raises_type_error(self):
        with pytest.raises(TypeError, match="base_url must be str, got: bool"):
            create_bybit_demo_base_url(base_url=True)

    def test_bytes_raises_type_error(self):
        with pytest.raises(TypeError, match="base_url must be str, got: bytes"):
            create_bybit_demo_base_url(base_url=b"https://example.com")

    def test_list_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_base_url(base_url=["https://example.com"])

    def test_dict_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_base_url(base_url={"url": "https://example.com"})

    def test_object_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_base_url(base_url=object())


# ---------------------------------------------------------------------------
# 5. Validación — contenido
# ---------------------------------------------------------------------------

class TestContentValidation:
    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError, match="base_url must not be empty or whitespace-only"):
            create_bybit_demo_base_url(base_url="")

    def test_whitespace_only_raises_value_error(self):
        with pytest.raises(ValueError, match="base_url must not be empty or whitespace-only"):
            create_bybit_demo_base_url(base_url="   ")

    def test_tab_only_raises_value_error(self):
        with pytest.raises(ValueError, match="base_url must not be empty or whitespace-only"):
            create_bybit_demo_base_url(base_url="\t")

    def test_http_scheme_raises_value_error(self):
        with pytest.raises(ValueError, match="base_url must start with 'https://'"):
            create_bybit_demo_base_url(base_url="http://api-demo.bybit.com")

    def test_no_scheme_raises_value_error(self):
        with pytest.raises(ValueError, match="base_url must start with 'https://'"):
            create_bybit_demo_base_url(base_url="api-demo.bybit.com")

    def test_ftp_scheme_raises_value_error(self):
        with pytest.raises(ValueError, match="base_url must start with 'https://'"):
            create_bybit_demo_base_url(base_url="ftp://api-demo.bybit.com")

    def test_trailing_slash_raises_value_error(self):
        with pytest.raises(ValueError, match="base_url must not contain a path"):
            create_bybit_demo_base_url(base_url="https://api-demo.bybit.com/")

    def test_path_raises_value_error(self):
        with pytest.raises(ValueError, match="base_url must not contain a path"):
            create_bybit_demo_base_url(base_url="https://api-demo.bybit.com/v5")

    def test_query_string_raises_value_error(self):
        with pytest.raises(ValueError, match="base_url must not contain a query string"):
            create_bybit_demo_base_url(base_url="https://api-demo.bybit.com?foo=bar")

    def test_fragment_raises_value_error(self):
        with pytest.raises(ValueError, match="base_url must not contain a fragment"):
            create_bybit_demo_base_url(base_url="https://api-demo.bybit.com#section")

    def test_leading_space_raises_value_error(self):
        with pytest.raises(ValueError):
            create_bybit_demo_base_url(base_url=" https://api-demo.bybit.com")

    def test_https_only_no_host_raises_value_error(self):
        with pytest.raises(ValueError):
            create_bybit_demo_base_url(base_url="https://")


# ---------------------------------------------------------------------------
# 6. Subclasses de str
# ---------------------------------------------------------------------------

class TestStrSubclass:
    def test_str_subclass_accepted(self):
        class MyStr(str):
            pass
        result = create_bybit_demo_base_url(base_url=MyStr(_VALID_URL))
        assert result == _VALID_URL


# ---------------------------------------------------------------------------
# 7. Ausencia de transformación
# ---------------------------------------------------------------------------

class TestNoTransformation:
    def test_value_preserved_exactly(self):
        assert create_bybit_demo_base_url(base_url=_VALID_URL) == _VALID_URL

    def test_no_strip_applied(self):
        url = "https://example.com"
        result = create_bybit_demo_base_url(base_url=url)
        assert result == url

    def test_no_scheme_change(self):
        url = "https://example.com"
        result = create_bybit_demo_base_url(base_url=url)
        assert result.startswith("https://")

    def test_does_not_add_trailing_slash(self):
        url = "https://example.com"
        result = create_bybit_demo_base_url(base_url=url)
        assert not result.endswith("/")

    def test_does_not_add_path(self):
        url = "https://example.com"
        result = create_bybit_demo_base_url(base_url=url)
        assert result == "https://example.com"

    def test_does_not_return_bytes(self):
        result = create_bybit_demo_base_url(base_url=_VALID_URL)
        assert not isinstance(result, bytes)

    def test_does_not_return_none(self):
        result = create_bybit_demo_base_url(base_url=_VALID_URL)
        assert result is not None

    def test_does_not_return_tuple(self):
        result = create_bybit_demo_base_url(base_url=_VALID_URL)
        assert not isinstance(result, tuple)

    def test_does_not_return_dict(self):
        result = create_bybit_demo_base_url(base_url=_VALID_URL)
        assert not isinstance(result, dict)


# ---------------------------------------------------------------------------
# 8. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_same_value_each_call(self):
        r1 = create_bybit_demo_base_url(base_url=_VALID_URL)
        r2 = create_bybit_demo_base_url(base_url=_VALID_URL)
        assert r1 == r2

    def test_no_state_accumulation(self):
        for _ in range(5):
            result = create_bybit_demo_base_url(base_url=_VALID_URL)
            assert result == _VALID_URL


# ---------------------------------------------------------------------------
# 9. Ausencia de ejecución
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_no_network_during_construction(self):
        import socket
        calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_demo_base_url(base_url=_VALID_URL)
        finally:
            socket.socket.connect = original
        assert calls == []

    def test_no_env_vars_read(self, monkeypatch):
        monkeypatch.setenv("BYBIT_BASE_URL", "https://other.example.com")
        result = create_bybit_demo_base_url(base_url=_VALID_URL)
        assert result == _VALID_URL


# ---------------------------------------------------------------------------
# 10. Seguridad estática
# ---------------------------------------------------------------------------

class TestStaticSecurity:
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

    def test_source_does_not_contain_env_var_names(self):
        src = inspect.getsource(_module)
        assert "BYBIT_API_KEY" not in src
        assert "BYBIT_BASE_URL" not in src

    def test_does_not_import_transport(self):
        assert "UrllibHttpTransport" not in vars(_module)

    def test_does_not_import_executor(self):
        assert "HttpRequestExecutor" not in vars(_module)

    def test_does_not_import_authenticator(self):
        assert "StandardBybitAuthenticator" not in vars(_module)


# ---------------------------------------------------------------------------
# 11. Integración con BybitUrlBuilder (consumidor real)
# ---------------------------------------------------------------------------

class TestIntegrationWithUrlBuilder:
    def test_result_accepted_by_bybit_url_builder(self):
        url = create_bybit_demo_base_url(base_url=_VALID_URL)
        builder = BybitUrlBuilder(base_url=url)
        assert isinstance(builder, BybitUrlBuilder)

    def test_url_preserved_in_url_builder(self):
        url = create_bybit_demo_base_url(base_url=_VALID_URL)
        builder = BybitUrlBuilder(base_url=url)
        assert builder._base_url == _VALID_URL

    def test_url_builder_not_created_during_factory_call(self, monkeypatch):
        calls = []
        original_init = BybitUrlBuilder.__init__

        def spy_init(self, base_url):
            calls.append(base_url)
            return original_init(self, base_url)

        monkeypatch.setattr(BybitUrlBuilder, "__init__", spy_init)
        create_bybit_demo_base_url(base_url=_VALID_URL)
        assert calls == []

    def test_url_builder_endpoint_executor_compose(self):
        url = create_bybit_demo_base_url(base_url=_VALID_URL)
        serializer = create_json_serializer()
        signer = create_message_signer()
        clock = create_millisecond_clock()
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        authenticator = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=create_bybit_recv_window_ms(recv_window_ms=5_000),
        )
        header_builder = create_bybit_header_builder()
        request_builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=authenticator,
            header_builder=header_builder,
        )
        parser = create_bybit_response_parser(serializer=serializer)
        transport = create_http_transport()
        timeout = create_http_timeout_seconds(timeout_seconds=5.0)
        executor = create_http_request_executor(transport=transport, timeout_seconds=timeout)
        sender = create_bybit_private_request_sender(
            request_builder=request_builder,
            request_executor=executor,
        )
        private_api = create_bybit_private_api(sender=sender, response_parser=parser)

        url_builder = BybitUrlBuilder(base_url=url)
        endpoint_executor = BybitEndpointExecutor(
            url_builder=url_builder,
            private_api=private_api,
        )
        client = create_bybit_demo_client(endpoint_executor=endpoint_executor)
        gateway = BybitExecutionGateway(client=client)
        assert isinstance(gateway, BybitExecutionGateway)

    def test_no_http_during_url_builder_composition(self, monkeypatch):
        calls = []
        original_post = UrllibHttpTransport.post

        def spy_post(self, *, url, headers, body, timeout_seconds):
            calls.append(url)
            return original_post(self, url=url, headers=headers, body=body, timeout_seconds=timeout_seconds)

        monkeypatch.setattr(UrllibHttpTransport, "post", spy_post)
        url = create_bybit_demo_base_url(base_url=_VALID_URL)
        BybitUrlBuilder(base_url=url)
        assert calls == []


# ---------------------------------------------------------------------------
# 12. Integración completa sin ejecución
# ---------------------------------------------------------------------------

class TestFullIntegrationNoExecution:
    def _build_full_stack(self, url: str = _VALID_URL):
        base_url = create_bybit_demo_base_url(base_url=url)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        recv = create_bybit_recv_window_ms(recv_window_ms=5_000)
        authenticator = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=recv,
        )
        serializer = create_json_serializer()
        header_builder = create_bybit_header_builder()
        request_builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=authenticator,
            header_builder=header_builder,
        )
        parser = create_bybit_response_parser(serializer=serializer)
        transport = create_http_transport()
        timeout = create_http_timeout_seconds(timeout_seconds=5.0)
        executor = create_http_request_executor(transport=transport, timeout_seconds=timeout)
        sender = create_bybit_private_request_sender(
            request_builder=request_builder,
            request_executor=executor,
        )
        private_api = create_bybit_private_api(sender=sender, response_parser=parser)

        url_builder = BybitUrlBuilder(base_url=base_url)
        endpoint_executor = BybitEndpointExecutor(
            url_builder=url_builder,
            private_api=private_api,
        )
        client = create_bybit_demo_client(endpoint_executor=endpoint_executor)
        gateway = BybitExecutionGateway(client=client)

        return dict(
            base_url=base_url,
            credentials=credentials,
            signer=signer,
            clock=clock,
            authenticator=authenticator,
            serializer=serializer,
            header_builder=header_builder,
            request_builder=request_builder,
            parser=parser,
            transport=transport,
            timeout=timeout,
            executor=executor,
            sender=sender,
            private_api=private_api,
            url_builder=url_builder,
            endpoint_executor=endpoint_executor,
            gateway=gateway,
        )

    def test_full_stack_builds_successfully(self):
        stack = self._build_full_stack()
        assert isinstance(stack["gateway"], BybitExecutionGateway)

    def test_base_url_preserved_in_url_builder(self):
        stack = self._build_full_stack()
        assert stack["url_builder"]._base_url == _VALID_URL

    def test_transport_identity_in_executor(self):
        stack = self._build_full_stack()
        assert stack["executor"]._transport is stack["transport"]

    def test_executor_identity_in_sender(self):
        stack = self._build_full_stack()
        assert stack["sender"]._request_executor is stack["executor"]

    def test_credentials_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._credentials is stack["credentials"]

    def test_signer_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._signer is stack["signer"]

    def test_clock_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._clock is stack["clock"]

    def test_serializer_shared_in_builder_and_parser(self):
        stack = self._build_full_stack()
        assert stack["request_builder"]._serializer is stack["serializer"]
        assert stack["parser"]._serializer is stack["serializer"]

    def test_no_network_during_full_composition(self):
        import socket
        calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            self._build_full_stack()
        finally:
            socket.socket.connect = original
        assert calls == []

    def test_no_clock_during_full_composition(self, monkeypatch):
        import time
        calls = []
        original_ns = time.time_ns

        def spy_ns():
            calls.append(True)
            return original_ns()

        monkeypatch.setattr(time, "time_ns", spy_ns)
        self._build_full_stack()
        assert calls == []

    def test_no_sign_during_full_composition(self, monkeypatch):
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        self._build_full_stack()
        assert calls == []

    def test_no_http_during_full_composition(self, monkeypatch):
        calls = []
        original_post = UrllibHttpTransport.post

        def spy_post(self, *, url, headers, body, timeout_seconds):
            calls.append(url)
            return original_post(self, url=url, headers=headers, body=body, timeout_seconds=timeout_seconds)

        monkeypatch.setattr(UrllibHttpTransport, "post", spy_post)
        self._build_full_stack()
        assert calls == []


# ---------------------------------------------------------------------------
# 13. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_full_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_does_not_create_url_builder(self):
        src = inspect.getsource(create_bybit_demo_base_url)
        assert "BybitUrlBuilder" not in src

    def test_does_not_create_transport(self):
        src = inspect.getsource(create_bybit_demo_base_url)
        assert "HttpTransport" not in src
        assert "UrllibHttpTransport" not in src

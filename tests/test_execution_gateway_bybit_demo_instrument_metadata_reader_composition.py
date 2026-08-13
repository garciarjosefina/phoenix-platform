import pytest

import execution_gateway
from execution_gateway.bybit_demo_instrument_metadata_reader_env_bootstrap import (
    bootstrap_bybit_demo_instrument_metadata_reader_from_env,
)
from execution_gateway.bybit_demo_instrument_metadata_reader_factory import (
    create_bybit_demo_instrument_metadata_reader,
)
from execution_gateway.bybit_instrument_metadata_reader import BybitInstrumentMetadataReader
from execution_gateway.bybit_public_get_api import BybitPublicGetApi
from execution_gateway.configured_bybit_demo_instrument_metadata_reader_factory import (
    create_configured_bybit_demo_instrument_metadata_reader,
)
from execution_gateway.environment_configuration_error import EnvironmentConfigurationError

_VALID_ENV = {"PHOENIX_HTTP_TIMEOUT_SECONDS": "10"}


class _FakePublicGetApi(BybitPublicGetApi):
    def __init__(self) -> None:
        pass


class TestCreateBybitDemoInstrumentMetadataReader:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_demo_instrument_metadata_reader")
        assert (
            execution_gateway.create_bybit_demo_instrument_metadata_reader
            is create_bybit_demo_instrument_metadata_reader
        )

    def test_in_all(self):
        assert "create_bybit_demo_instrument_metadata_reader" in execution_gateway.__all__

    def test_public_get_api_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitPublicGetApi"):
            create_bybit_demo_instrument_metadata_reader(public_get_api=object())

    def test_returns_bybit_instrument_metadata_reader(self):
        reader = create_bybit_demo_instrument_metadata_reader(public_get_api=_FakePublicGetApi())
        assert isinstance(reader, BybitInstrumentMetadataReader)

    def test_preserves_public_get_api_by_identity(self):
        api = _FakePublicGetApi()
        reader = create_bybit_demo_instrument_metadata_reader(public_get_api=api)
        assert reader._public_get_api is api

    def test_uses_demo_base_url(self):
        reader = create_bybit_demo_instrument_metadata_reader(public_get_api=_FakePublicGetApi())
        assert reader._url_builder._base_url == "https://api-demo.bybit.com"

    def test_keyword_only(self):
        with pytest.raises(TypeError):
            create_bybit_demo_instrument_metadata_reader(_FakePublicGetApi())

    def test_two_calls_return_distinct_instances(self):
        api = _FakePublicGetApi()
        r1 = create_bybit_demo_instrument_metadata_reader(public_get_api=api)
        r2 = create_bybit_demo_instrument_metadata_reader(public_get_api=api)
        assert r1 is not r2


class TestCreateConfiguredBybitDemoInstrumentMetadataReader:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_configured_bybit_demo_instrument_metadata_reader")
        assert (
            execution_gateway.create_configured_bybit_demo_instrument_metadata_reader
            is create_configured_bybit_demo_instrument_metadata_reader
        )

    def test_in_all(self):
        assert "create_configured_bybit_demo_instrument_metadata_reader" in execution_gateway.__all__

    def test_returns_bybit_instrument_metadata_reader(self):
        reader = create_configured_bybit_demo_instrument_metadata_reader(timeout_seconds=10)
        assert isinstance(reader, BybitInstrumentMetadataReader)

    def test_does_not_require_credentials_config(self):
        # Punto arquitectónico central del Hito 3.73: la factory configurada
        # NO acepta ni requiere BybitDemoExecutionConfig -- sólo
        # timeout_seconds, la única dependencia operativa real del endpoint
        # público. Verificado por firma.
        import inspect
        params = inspect.signature(create_configured_bybit_demo_instrument_metadata_reader).parameters
        assert set(params.keys()) == {"timeout_seconds"}
        assert "config" not in params

    def test_invalid_timeout_rejected(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            create_configured_bybit_demo_instrument_metadata_reader(timeout_seconds=0)

    def test_nan_timeout_rejected(self):
        with pytest.raises(ValueError, match="timeout_seconds must be finite"):
            create_configured_bybit_demo_instrument_metadata_reader(timeout_seconds=float("nan"))

    def test_keyword_only(self):
        with pytest.raises(TypeError):
            create_configured_bybit_demo_instrument_metadata_reader(10)

    def test_does_not_construct_execution_gateway(self):
        import inspect
        import execution_gateway.configured_bybit_demo_instrument_metadata_reader_factory as module
        src = inspect.getsource(module)
        assert "BybitExecutionGateway" not in src
        assert "BybitDemoClient" not in src
        assert "create_order" not in src

    def test_does_not_reference_authenticator_or_credentials(self):
        import inspect
        import execution_gateway.configured_bybit_demo_instrument_metadata_reader_factory as module
        code_lines = [
            line for line in inspect.getsource(module).splitlines()
            if not line.strip().startswith("#")
        ]
        code = "\n".join(code_lines).lower()
        assert "credentials" not in code
        assert "authenticat" not in code
        assert "header_builder" not in code
        assert "recv_window" not in code

    def test_two_calls_return_distinct_instances(self):
        r1 = create_configured_bybit_demo_instrument_metadata_reader(timeout_seconds=10)
        r2 = create_configured_bybit_demo_instrument_metadata_reader(timeout_seconds=10)
        assert r1 is not r2


class TestBootstrap:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "bootstrap_bybit_demo_instrument_metadata_reader_from_env")
        assert (
            execution_gateway.bootstrap_bybit_demo_instrument_metadata_reader_from_env
            is bootstrap_bybit_demo_instrument_metadata_reader_from_env
        )

    def test_in_all(self):
        assert "bootstrap_bybit_demo_instrument_metadata_reader_from_env" in execution_gateway.__all__

    def test_keyword_only_environ(self):
        with pytest.raises(TypeError):
            bootstrap_bybit_demo_instrument_metadata_reader_from_env(_VALID_ENV)

    def test_environ_defaults_to_none(self):
        import inspect
        sig = inspect.signature(bootstrap_bybit_demo_instrument_metadata_reader_from_env)
        assert sig.parameters["environ"].default is None

    def test_returns_bybit_instrument_metadata_reader(self):
        reader = bootstrap_bybit_demo_instrument_metadata_reader_from_env(environ=_VALID_ENV)
        assert isinstance(reader, BybitInstrumentMetadataReader)

    def test_does_not_require_api_key_env_var(self):
        # Confirmación conductual directa del punto arquitectónico: una
        # cuenta sin ninguna credencial Bybit Demo configurada puede seguir
        # consultando metadata de instrumentos.
        env = {"PHOENIX_HTTP_TIMEOUT_SECONDS": "10"}
        reader = bootstrap_bybit_demo_instrument_metadata_reader_from_env(environ=env)
        assert isinstance(reader, BybitInstrumentMetadataReader)

    def test_missing_timeout_raises_environment_configuration_error(self):
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_HTTP_TIMEOUT_SECONDS"):
            bootstrap_bybit_demo_instrument_metadata_reader_from_env(environ={})

    def test_invalid_timeout_raises_environment_configuration_error(self):
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_HTTP_TIMEOUT_SECONDS"):
            bootstrap_bybit_demo_instrument_metadata_reader_from_env(
                environ={"PHOENIX_HTTP_TIMEOUT_SECONDS": "abc"}
            )

    def test_environ_must_be_mapping(self):
        with pytest.raises(TypeError, match="environ must be a Mapping"):
            bootstrap_bybit_demo_instrument_metadata_reader_from_env(environ=["not", "a", "mapping"])

    def test_two_calls_build_distinct_graphs(self):
        r1 = bootstrap_bybit_demo_instrument_metadata_reader_from_env(environ=_VALID_ENV)
        r2 = bootstrap_bybit_demo_instrument_metadata_reader_from_env(environ=_VALID_ENV)
        assert r1 is not r2

    def test_no_new_environment_variables_introduced(self):
        # Reutiliza exactamente PHOENIX_HTTP_TIMEOUT_SECONDS, ya existente
        # desde BybitDemoExecutionConfig -- cero variables PHOENIX_* nuevas.
        # Sólo código real (sin comentarios), que sí mencionan las otras
        # tres variables en prosa para explicar por qué no se requieren.
        import inspect
        import execution_gateway.bybit_demo_instrument_metadata_reader_env_bootstrap as module
        code_lines = [
            line for line in inspect.getsource(module).splitlines()
            if not line.strip().startswith("#")
        ]
        code = "\n".join(code_lines)
        assert "PHOENIX_BYBIT_DEMO_API_KEY" not in code
        assert "PHOENIX_BYBIT_DEMO_API_SECRET" not in code
        assert "PHOENIX_BYBIT_RECV_WINDOW_MS" not in code
        assert "PHOENIX_HTTP_TIMEOUT_SECONDS" in code

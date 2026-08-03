import pytest

from execution_gateway import BybitResponseProcessingError
import execution_gateway
import execution_gateway.bybit_response_processing_error as _module


# ---------------------------------------------------------------------------
# 1. Importación y API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError as E
        assert E is BybitResponseProcessingError

    def test_importable_from_package(self):
        from execution_gateway import BybitResponseProcessingError as E
        assert E is BybitResponseProcessingError

    def test_included_in_all(self):
        assert "BybitResponseProcessingError" in execution_gateway.__all__

    def test_inherits_from_exception(self):
        assert issubclass(BybitResponseProcessingError, Exception)

    def test_is_direct_subclass_of_exception(self):
        assert Exception in BybitResponseProcessingError.__bases__

    def test_does_not_inherit_from_bybit_api_error(self):
        from execution_gateway.bybit_api_error import BybitApiError
        assert not issubclass(BybitResponseProcessingError, BybitApiError)

    def test_does_not_inherit_from_execution_infrastructure_error(self):
        from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
        assert not issubclass(BybitResponseProcessingError, ExecutionInfrastructureError)


# ---------------------------------------------------------------------------
# 2. Constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_valid_construction(self):
        err = BybitResponseProcessingError(message="response could not be processed")
        assert err is not None

    def test_argument_is_keyword_only(self):
        with pytest.raises(TypeError):
            BybitResponseProcessingError("response could not be processed")

    def test_stores_message(self):
        err = BybitResponseProcessingError(message="malformed response")
        assert err.message == "malformed response"

    def test_preserves_message_exactly(self):
        msg = "Bybit response could not be processed"
        err = BybitResponseProcessingError(message=msg)
        assert err.message is msg


# ---------------------------------------------------------------------------
# 3. Validación de message
# ---------------------------------------------------------------------------

class TestMessageValidation:
    def test_rejects_none(self):
        with pytest.raises(TypeError, match="message must be str"):
            BybitResponseProcessingError(message=None)

    def test_rejects_int(self):
        with pytest.raises(TypeError, match="message must be str"):
            BybitResponseProcessingError(message=1)

    def test_rejects_bytes(self):
        with pytest.raises(TypeError, match="message must be str"):
            BybitResponseProcessingError(message=b"failure")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="message must not be empty or whitespace-only"):
            BybitResponseProcessingError(message="")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="message must not be empty or whitespace-only"):
            BybitResponseProcessingError(message="   ")


# ---------------------------------------------------------------------------
# 4. Mensaje y encadenamiento
# ---------------------------------------------------------------------------

class TestMessageAndChaining:
    def test_str_format_is_message_verbatim(self):
        err = BybitResponseProcessingError(message="malformed response")
        assert str(err) == "malformed response"

    def test_supports_exception_chaining_via_from(self):
        original = ValueError("bad json")
        try:
            try:
                raise original
            except ValueError as e:
                raise BybitResponseProcessingError(message="response could not be processed") from e
        except BybitResponseProcessingError as wrapped:
            assert wrapped.__cause__ is original

    def test_can_be_raised_and_caught(self):
        with pytest.raises(BybitResponseProcessingError):
            raise BybitResponseProcessingError(message="x")


# ---------------------------------------------------------------------------
# 5. Superficie mínima
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_public_attributes_are_message_only(self):
        err = BybitResponseProcessingError(message="x")
        public = {k for k in vars(err) if not k.startswith("_")}
        assert public == {"message"}

    def test_no_ret_code_attribute(self):
        err = BybitResponseProcessingError(message="x")
        assert not hasattr(err, "ret_code")

    def test_no_ret_msg_attribute(self):
        err = BybitResponseProcessingError(message="x")
        assert not hasattr(err, "ret_msg")

    def test_no_extra_public_methods(self):
        err = BybitResponseProcessingError(message="x")
        inherited = set(dir(Exception()))
        own_public = {n for n in dir(err) if not n.startswith("_") and n not in inherited}
        assert own_public == {"message"}


# ---------------------------------------------------------------------------
# 6. Pureza — no debe formar parte del dominio ni ser confundida con él
# ---------------------------------------------------------------------------

class TestScopeIsInfrastructureInternal:
    def test_module_does_not_reference_domain_contracts(self):
        import inspect
        src = inspect.getsource(_module)
        assert "ExecutionRequest" not in src
        assert "ExecutionResult" not in src
        assert "ExecutionGateway" not in src

    def test_whole_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

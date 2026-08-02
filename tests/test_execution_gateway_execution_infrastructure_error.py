import pytest

from execution_gateway import ExecutionInfrastructureError
import execution_gateway
import execution_gateway.execution_infrastructure_error as _module


# ---------------------------------------------------------------------------
# 1. Importación y API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError as E
        assert E is ExecutionInfrastructureError

    def test_importable_from_package(self):
        from execution_gateway import ExecutionInfrastructureError as E
        assert E is ExecutionInfrastructureError

    def test_included_in_all(self):
        assert "ExecutionInfrastructureError" in execution_gateway.__all__

    def test_inherits_from_exception(self):
        assert issubclass(ExecutionInfrastructureError, Exception)

    def test_is_direct_subclass_of_exception(self):
        assert Exception in ExecutionInfrastructureError.__bases__

    def test_does_not_inherit_from_bybit_api_error(self):
        from execution_gateway.bybit_api_error import BybitApiError
        assert not issubclass(ExecutionInfrastructureError, BybitApiError)


# ---------------------------------------------------------------------------
# 2. Constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_valid_construction(self):
        err = ExecutionInfrastructureError(message="network failure")
        assert err is not None

    def test_argument_is_keyword_only(self):
        with pytest.raises(TypeError):
            ExecutionInfrastructureError("network failure")

    def test_stores_message(self):
        err = ExecutionInfrastructureError(message="network failure")
        assert err.message == "network failure"

    def test_preserves_message_exactly(self):
        msg = "connection refused: 10.0.0.1:443"
        err = ExecutionInfrastructureError(message=msg)
        assert err.message is msg


# ---------------------------------------------------------------------------
# 3. Validación de message
# ---------------------------------------------------------------------------

class TestMessageValidation:
    def test_rejects_none(self):
        with pytest.raises(TypeError, match="message must be str"):
            ExecutionInfrastructureError(message=None)

    def test_rejects_int(self):
        with pytest.raises(TypeError, match="message must be str"):
            ExecutionInfrastructureError(message=1)

    def test_rejects_bytes(self):
        with pytest.raises(TypeError, match="message must be str"):
            ExecutionInfrastructureError(message=b"failure")

    def test_rejects_list(self):
        with pytest.raises(TypeError, match="message must be str"):
            ExecutionInfrastructureError(message=["failure"])

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="message must not be empty or whitespace-only"):
            ExecutionInfrastructureError(message="")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="message must not be empty or whitespace-only"):
            ExecutionInfrastructureError(message="   ")

    def test_does_not_convert_via_str(self):
        with pytest.raises(TypeError):
            ExecutionInfrastructureError(message=12345)


# ---------------------------------------------------------------------------
# 4. Mensaje
# ---------------------------------------------------------------------------

class TestMessage:
    def test_str_format_is_message_verbatim(self):
        err = ExecutionInfrastructureError(message="network failure")
        assert str(err) == "network failure"

    def test_no_prefix_added(self):
        err = ExecutionInfrastructureError(message="raw error")
        assert str(err) == "raw error"

    def test_args_contains_only_message(self):
        err = ExecutionInfrastructureError(message="msg")
        assert len(err.args) == 1
        assert err.args[0] == "msg"


# ---------------------------------------------------------------------------
# 5. Excepción real y encadenamiento
# ---------------------------------------------------------------------------

class TestAsException:
    def test_can_be_raised(self):
        with pytest.raises(ExecutionInfrastructureError):
            raise ExecutionInfrastructureError(message="error")

    def test_caught_as_execution_infrastructure_error(self):
        try:
            raise ExecutionInfrastructureError(message="caught")
        except ExecutionInfrastructureError as e:
            assert e.message == "caught"

    def test_caught_as_exception(self):
        try:
            raise ExecutionInfrastructureError(message="caught")
        except Exception as e:
            assert isinstance(e, ExecutionInfrastructureError)

    def test_supports_exception_chaining_via_from(self):
        original = RuntimeError("transport down")
        try:
            try:
                raise original
            except RuntimeError as e:
                raise ExecutionInfrastructureError(message=str(e)) from e
        except ExecutionInfrastructureError as wrapped:
            assert wrapped.__cause__ is original

    def test_not_caught_as_bybit_api_error(self):
        from execution_gateway.bybit_api_error import BybitApiError
        with pytest.raises(ExecutionInfrastructureError):
            try:
                raise ExecutionInfrastructureError(message="not a bybit error")
            except BybitApiError:
                pytest.fail("ExecutionInfrastructureError must not be caught as BybitApiError")


# ---------------------------------------------------------------------------
# 6. Superficie mínima
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_public_attributes_are_message_only(self):
        err = ExecutionInfrastructureError(message="msg")
        public = {k for k in vars(err) if not k.startswith("_")}
        assert public == {"message"}

    def test_no_ret_code_attribute(self):
        err = ExecutionInfrastructureError(message="msg")
        assert not hasattr(err, "ret_code")

    def test_no_ret_msg_attribute(self):
        err = ExecutionInfrastructureError(message="msg")
        assert not hasattr(err, "ret_msg")

    def test_no_retryable_attribute(self):
        err = ExecutionInfrastructureError(message="msg")
        assert not hasattr(err, "retryable")

    def test_no_original_error_attribute(self):
        err = ExecutionInfrastructureError(message="msg")
        assert not hasattr(err, "original_error")

    def test_no_extra_public_methods(self):
        err = ExecutionInfrastructureError(message="msg")
        inherited = set(dir(Exception()))
        own_public = {
            n for n in dir(err)
            if not n.startswith("_") and n not in inherited
        }
        assert own_public == {"message"}


# ---------------------------------------------------------------------------
# 7. Pureza de dominio — ausencia de responsabilidades y tipos Bybit
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_module_source_has_no_bybit_reference(self):
        import inspect
        src = inspect.getsource(_module)
        assert "Bybit" not in src

    def test_does_not_import_bybit_api_error(self):
        assert "BybitApiError" not in vars(_module)

    def test_does_not_import_bybit_response(self):
        assert "BybitResponse" not in vars(_module)

    def test_does_not_import_bybit_client(self):
        assert "BybitDemoClient" not in vars(_module)

    def test_whole_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

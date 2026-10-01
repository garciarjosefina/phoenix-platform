import ast
import inspect
import typing

import pytest

import execution_gateway
import execution_gateway.order_submission_port as _module
from execution_gateway.contracts import ExecutionRequest
from execution_gateway.execution_request_not_supported_error import ExecutionRequestNotSupportedError
from execution_gateway.order_submission_outcome_contracts import (
    OrderSubmissionOutcome,
    SubmissionAccepted,
    SubmissionIdentityDuplicate,
    SubmissionOutcomeUnknown,
    SubmissionRejected,
)
from execution_gateway.order_submission_port import OrderSubmissionPort


def _request():
    return ExecutionRequest(
        order_id="ord_" + "a" * 32, symbol="BTCUSDT", side="buy", order_type="market", quantity=0.001,
    )


class _CompatibleFake:
    """Doble estructuralmente compatible -- vive sólo en tests, nunca en
    producción (no existe ninguna implementación concreta del puerto en 3.95)."""

    def __init__(self, outcome):
        self._outcome = outcome
        self.received = []

    def submit(self, request):
        self.received.append(request)
        return self._outcome


class _NoSubmit:
    def execute(self, request):
        ...


class _WrongName:
    def send(self, request):
        ...


# ---------------------------------------------------------------------------
# Protocol -- runtime_checkable estructural
# ---------------------------------------------------------------------------

class TestRuntimeCheckableProtocol:
    def test_compatible_fake_is_an_instance(self):
        assert isinstance(_CompatibleFake(None), OrderSubmissionPort)

    def test_object_without_submit_is_not_an_instance(self):
        assert not isinstance(_NoSubmit(), OrderSubmissionPort)

    def test_object_with_differently_named_method_is_not_an_instance(self):
        assert not isinstance(_WrongName(), OrderSubmissionPort)

    def test_plain_object_is_not_an_instance(self):
        assert not isinstance(object(), OrderSubmissionPort)

    def test_isinstance_does_not_raise_which_requires_runtime_checkable(self):
        # Sin @runtime_checkable, isinstance contra un Protocol lanza TypeError.
        try:
            isinstance(object(), OrderSubmissionPort)
        except TypeError:  # pragma: no cover -- sólo si falta el decorador
            pytest.fail("OrderSubmissionPort must be @runtime_checkable")

    def test_is_a_protocol_and_cannot_be_instantiated(self):
        assert getattr(OrderSubmissionPort, "_is_protocol", False) is True
        with pytest.raises(TypeError):
            OrderSubmissionPort()

    def test_structural_check_does_not_validate_the_return_type(self):
        # runtime_checkable sólo verifica la presencia de `submit`.
        class _ReturnsGarbage:
            def submit(self, request):
                return 42

        assert isinstance(_ReturnsGarbage(), OrderSubmissionPort)


# ---------------------------------------------------------------------------
# Firma exacta -- ADR-016 D2: sólo `request`, sin cuenta ni identidad extra
# ---------------------------------------------------------------------------

class TestSignature:
    def test_single_public_member_is_submit(self):
        members = [n for n, v in vars(OrderSubmissionPort).items() if not n.startswith("_") and callable(v)]
        assert members == ["submit"]

    def test_parameters_are_exactly_self_and_request(self):
        sig = inspect.signature(OrderSubmissionPort.submit)
        assert list(sig.parameters) == ["self", "request"]

    def test_request_is_annotated_execution_request_and_return_is_outcome_family_root(self):
        hints = typing.get_type_hints(OrderSubmissionPort.submit)
        assert hints["request"] is ExecutionRequest
        assert hints["return"] is OrderSubmissionOutcome

    def test_is_synchronous(self):
        assert not inspect.iscoroutinefunction(OrderSubmissionPort.submit)

    def test_no_account_or_identity_parameter_in_the_signature(self):
        params = set(inspect.signature(OrderSubmissionPort.submit).parameters)
        for forbidden in ("account_id", "execution_account_id", "execution_order_id", "order_id", "bot_id"):
            assert forbidden not in params


# ---------------------------------------------------------------------------
# Uso: el puerto devuelve (no lanza) cada outcome conocido o ambiguo
# ---------------------------------------------------------------------------

class TestUsageThroughTheStructuralContract:
    # Los outcomes se construyen DENTRO del test (factories perezosas): si el
    # contrato se rompiera, falla este test -- no la colección entera del
    # archivo, que enmascararía el resto de la suite (lección de 3.94, MENOR-3).
    @pytest.mark.parametrize("make_outcome", [
        lambda: SubmissionAccepted(exchange_order_id="B-1", server_time_ms=1),
        lambda: SubmissionRejected(ret_code=10001, ret_msg="bad", server_time_ms=1),
        lambda: SubmissionIdentityDuplicate(ret_code=110072, ret_msg="dup", server_time_ms=1),
        lambda: SubmissionOutcomeUnknown(reason="transport_failure"),
    ], ids=["accepted", "rejected", "duplicate", "unknown"])
    def test_each_outcome_is_returned_not_raised(self, make_outcome):
        outcome = make_outcome()
        port = _CompatibleFake(outcome)
        request = _request()
        result = port.submit(request)
        assert result is outcome
        assert isinstance(result, OrderSubmissionOutcome)
        assert port.received == [request]


# ---------------------------------------------------------------------------
# Contrato de excepciones documentado (ADR-016 D2) -- documental: lo
# implementa cada adapter, este puerto sólo lo fija.
# ---------------------------------------------------------------------------

class TestDocumentedExceptionContract:
    def test_docstring_fixes_the_four_clauses(self):
        doc = inspect.getdoc(OrderSubmissionPort)
        assert "ExecutionRequestNotSupportedError" in doc
        for name in ("SubmissionAccepted", "SubmissionRejected", "SubmissionIdentityDuplicate",
                     "SubmissionOutcomeUnknown"):
            assert name in doc
        assert "errores de programación" in doc

    def test_referenced_error_type_exists(self):
        assert issubclass(ExecutionRequestNotSupportedError, Exception)


# ---------------------------------------------------------------------------
# Export y pureza
# ---------------------------------------------------------------------------

class TestPackageExport:
    def test_importable_from_package_and_in_all(self):
        assert execution_gateway.OrderSubmissionPort is OrderSubmissionPort
        assert "OrderSubmissionPort" in execution_gateway.__all__


class TestPurity:
    def _imports(self):
        names = set()
        for node in ast.walk(ast.parse(inspect.getsource(_module))):
            if isinstance(node, ast.Import):
                names |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module)
        return names

    def test_imports_are_exactly_typing_request_and_outcome_contracts(self):
        assert self._imports() == {
            "typing",
            "execution_gateway.contracts",
            "execution_gateway.order_submission_outcome_contracts",
        }

    def test_no_concrete_implementation_lives_in_the_module(self):
        classes = [
            n for n, o in vars(_module).items()
            if isinstance(o, type) and o.__module__ == _module.__name__
        ]
        assert classes == ["OrderSubmissionPort"]

    def test_no_clock_uuid_network_or_environment_names(self):
        names = set()
        for node in ast.walk(ast.parse(inspect.getsource(_module))):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        for forbidden in ("time", "uuid", "urlopen", "environ", "getenv", "socket", "datetime"):
            assert forbidden not in names

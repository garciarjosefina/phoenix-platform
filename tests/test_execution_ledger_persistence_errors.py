import ast
import inspect

import pytest

import execution_gateway
import execution_gateway.execution_ledger_persistence_errors as _module
from execution_gateway.execution_ledger_persistence_errors import (
    ExecutionLedgerPersistenceError,
    LeaseLostError,
    LeaseNotAcquiredError,
    LedgerAppendError,
    LedgerIntegrityError,
    LedgerReadError,
)

_CONCRETE = (LedgerAppendError, LedgerReadError, LedgerIntegrityError, LeaseNotAcquiredError, LeaseLostError)


class _Obj:
    pass


class TestHierarchy:
    def test_exactly_five_concrete_errors_under_one_base(self):
        found = sorted(
            n for n, o in vars(_module).items()
            if isinstance(o, type) and issubclass(o, ExecutionLedgerPersistenceError) and o is not ExecutionLedgerPersistenceError
        )
        assert found == sorted(c.__name__ for c in _CONCRETE)

    @pytest.mark.parametrize("cls", _CONCRETE)
    def test_each_is_a_direct_child_of_the_base_and_an_exception(self, cls):
        assert cls.__mro__[1] is ExecutionLedgerPersistenceError
        assert issubclass(cls, Exception)

    def test_no_concrete_error_inherits_from_another(self):
        for a in _CONCRETE:
            for b in _CONCRETE:
                if a is not b:
                    assert not issubclass(a, b), (a.__name__, b.__name__)

    @pytest.mark.parametrize("cls", [ExecutionLedgerPersistenceError, *_CONCRETE])
    def test_none_inherits_from_an_os_or_vendor_error(self, cls):
        assert not issubclass(cls, (OSError, ValueError, TypeError, KeyError))

    def test_other_execution_errors_are_not_related(self):
        from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
        from execution_gateway.execution_request_not_supported_error import ExecutionRequestNotSupportedError

        for cls in _CONCRETE:
            assert not issubclass(cls, (ExecutionInfrastructureError, ExecutionRequestNotSupportedError))
            assert not issubclass(ExecutionInfrastructureError, cls)


class TestMessageContract:
    @pytest.mark.parametrize("cls", [ExecutionLedgerPersistenceError, *_CONCRETE])
    def test_message_is_preserved_and_keyword_only(self, cls):
        error = cls(message=" a message ")
        assert error.message == " a message " and str(error) == " a message "
        with pytest.raises(TypeError):
            cls(" positional ")

    @pytest.mark.parametrize("cls", [ExecutionLedgerPersistenceError, *_CONCRETE])
    @pytest.mark.parametrize("bad", [None, 1, b"x", _Obj(), ["m"]])
    def test_message_must_be_str(self, cls, bad):
        with pytest.raises(TypeError):
            cls(message=bad)

    @pytest.mark.parametrize("cls", [ExecutionLedgerPersistenceError, *_CONCRETE])
    @pytest.mark.parametrize("bad", ["", "   ", "\t\n"])
    def test_message_must_not_be_blank(self, cls, bad):
        with pytest.raises(ValueError):
            cls(message=bad)

    @pytest.mark.parametrize("cls", _CONCRETE)
    def test_cause_chaining_is_preserved(self, cls):
        cause = RuntimeError("driver failure")
        try:
            try:
                raise cause
            except RuntimeError as error:
                raise cls(message="translated") from error
        except cls as caught:
            assert caught.__cause__ is cause

    @pytest.mark.parametrize("cls", _CONCRETE)
    def test_each_error_can_be_caught_distinctly(self, cls):
        others = [c for c in _CONCRETE if c is not cls]
        with pytest.raises(cls):
            try:
                raise cls(message="m")
            except tuple(others):  # pragma: no cover -- no debe capturarse
                pytest.fail("caught by a sibling error type")


class TestPurityAndExports:
    def test_module_imports_nothing(self):
        tree = ast.parse(inspect.getsource(_module))
        assert not [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]

    def test_no_vendor_names(self):
        src = inspect.getsource(_module)
        for forbidden in ("psycopg", "OperationalError", "UniqueViolation", "sqlalchemy"):
            assert forbidden not in src, forbidden

    @pytest.mark.parametrize("name", ["ExecutionLedgerPersistenceError", *[c.__name__ for c in _CONCRETE]])
    def test_exported_from_package(self, name):
        assert getattr(execution_gateway, name) is getattr(_module, name)
        assert name in execution_gateway.__all__

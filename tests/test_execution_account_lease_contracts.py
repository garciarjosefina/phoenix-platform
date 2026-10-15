import ast
import inspect
import typing

import pytest

import execution_gateway
import execution_gateway.execution_account_lease_contracts as _module
from execution_gateway.execution_account_lease_contracts import AccountExecutionLease, AccountLeaseHandle
from execution_gateway.execution_identity_contracts import ExecutionAccountId
from execution_gateway.execution_ledger_persistence_contracts import ExecutionLedgerReader, ExecutionLedgerWriter

_ACCOUNT = ExecutionAccountId(value="acct-1")
_HANDLE_MEMBERS = ("execution_account_id", "writer", "reader", "release")


class _FakeWriter:
    def append(self, *, execution_account_id, occurred_at_ms, payload):
        return None


class _FakeReader:
    def read_account_events(self, *, execution_account_id):
        return ()

    def read_order_events(self, *, execution_account_id, execution_order_id):
        return ()

    def read_last_order_event(self, *, execution_account_id, execution_order_id, payload_type):
        return None

    def read_order_ids_with_event_type(self, *, execution_account_id, payload_type):
        return ()


class _FakeHandle:
    def __init__(self, account):
        self._account = account
        self._writer = _FakeWriter()
        self._reader = _FakeReader()
        self.released = 0

    @property
    def execution_account_id(self):
        return self._account

    @property
    def writer(self):
        return self._writer

    @property
    def reader(self):
        return self._reader

    def release(self):
        self.released += 1


class _FakeLease:
    def acquire(self, *, execution_account_id):
        return _FakeHandle(execution_account_id)


def _public_members(proto):
    return sorted(n for n in vars(proto) if not n.startswith("_"))


class TestAccountLeaseHandle:
    def test_compatible_fake_is_an_instance(self):
        assert isinstance(_FakeHandle(_ACCOUNT), AccountLeaseHandle)

    @pytest.mark.parametrize("missing", _HANDLE_MEMBERS)
    def test_object_missing_any_single_member_is_not_an_instance(self, missing):
        class Stripped:
            pass

        for name in _HANDLE_MEMBERS:
            if name != missing:
                setattr(Stripped, name, vars(_FakeHandle)[name])
        assert not isinstance(Stripped(), AccountLeaseHandle)

    def test_plain_object_is_not_an_instance(self):
        assert not isinstance(object(), AccountLeaseHandle)

    def test_is_a_protocol_and_not_instantiable(self):
        assert getattr(AccountLeaseHandle, "_is_protocol", False) is True
        with pytest.raises(TypeError):
            AccountLeaseHandle()

    def test_exact_public_surface(self):
        assert _public_members(AccountLeaseHandle) == sorted(_HANDLE_MEMBERS)

    def test_property_types(self):
        expected = {
            "execution_account_id": ExecutionAccountId,
            "writer": ExecutionLedgerWriter,
            "reader": ExecutionLedgerReader,
        }
        for name, cls in expected.items():
            fget = vars(AccountLeaseHandle)[name].fget
            assert typing.get_type_hints(fget)["return"] is cls, name

    def test_release_takes_no_arguments_and_returns_none(self):
        assert list(inspect.signature(AccountLeaseHandle.release).parameters) == ["self"]
        assert typing.get_type_hints(AccountLeaseHandle.release)["return"] is type(None)

    def test_has_no_validity_flag_reconnect_or_timeout_surface(self):
        for forbidden in ("is_active", "is_valid", "reconnect", "renew", "refresh", "timeout",
                          "connection", "cursor", "execute", "commit", "rollback", "transaction"):
            assert not hasattr(AccountLeaseHandle, forbidden), forbidden

    def test_writer_and_reader_exposed_by_the_handle_satisfy_their_ports(self):
        handle = _FakeHandle(_ACCOUNT)
        assert isinstance(handle.writer, ExecutionLedgerWriter)
        assert isinstance(handle.reader, ExecutionLedgerReader)


class TestAccountExecutionLease:
    def test_compatible_fake_is_an_instance(self):
        assert isinstance(_FakeLease(), AccountExecutionLease)

    def test_object_without_acquire_is_not_an_instance(self):
        class Other:
            def take(self, *, execution_account_id):
                ...

        assert not isinstance(Other(), AccountExecutionLease)
        assert not isinstance(object(), AccountExecutionLease)

    def test_exact_public_surface(self):
        assert _public_members(AccountExecutionLease) == ["acquire"]

    def test_acquire_signature_is_keyword_only_account_without_timeout(self):
        sig = inspect.signature(AccountExecutionLease.acquire)
        assert list(sig.parameters) == ["self", "execution_account_id"]
        assert sig.parameters["execution_account_id"].kind is inspect.Parameter.KEYWORD_ONLY
        for forbidden in ("timeout", "timeout_ms", "timeout_seconds", "wait", "blocking", "retries"):
            assert forbidden not in sig.parameters

    def test_acquire_types(self):
        hints = typing.get_type_hints(AccountExecutionLease.acquire)
        assert hints["execution_account_id"] is ExecutionAccountId
        assert hints["return"] is AccountLeaseHandle

    def test_acquire_is_synchronous(self):
        assert not inspect.iscoroutinefunction(AccountExecutionLease.acquire)

    def test_is_a_protocol_and_not_instantiable(self):
        assert getattr(AccountExecutionLease, "_is_protocol", False) is True
        with pytest.raises(TypeError):
            AccountExecutionLease()

    def test_usage_acquire_returns_a_handle_for_that_account(self):
        handle = _FakeLease().acquire(execution_account_id=_ACCOUNT)
        assert isinstance(handle, AccountLeaseHandle)
        assert handle.execution_account_id is _ACCOUNT
        handle.release()
        assert handle.released == 1


class TestPurityAndExports:
    def _tree(self):
        return ast.parse(inspect.getsource(_module))

    def test_imports_are_exactly_typing_identity_and_persistence_contracts(self):
        names = set()
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Import):
                names |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module)
        assert names == {
            "typing",
            "execution_gateway.execution_identity_contracts",
            "execution_gateway.execution_ledger_persistence_contracts",
        }

    def test_no_vendor_clock_environment_or_network_names(self):
        tree = self._tree()
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for forbidden in ("psycopg", "Connection", "time", "uuid", "environ", "socket", "urlopen"):
            assert forbidden not in names, forbidden

    def test_only_the_two_protocols_are_defined(self):
        classes = sorted(
            n for n, o in vars(_module).items() if isinstance(o, type) and o.__module__ == _module.__name__
        )
        assert classes == ["AccountExecutionLease", "AccountLeaseHandle"]

    @pytest.mark.parametrize("name", ["AccountLeaseHandle", "AccountExecutionLease"])
    def test_exported_from_package(self, name):
        assert getattr(execution_gateway, name) is getattr(_module, name)
        assert name in execution_gateway.__all__

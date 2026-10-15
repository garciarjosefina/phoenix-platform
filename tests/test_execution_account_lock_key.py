import ast
import hashlib
import inspect
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest

import execution_gateway
import execution_gateway.execution_account_lock_key as _module
from execution_gateway.execution_account_lock_key import account_lock_key
from execution_gateway.execution_identity_contracts import ExecutionAccountId, ExecutionOrderId

_PLATFORM_DIR = str(Path(execution_gateway.__file__).resolve().parent.parent)
_NAMESPACE = b"phoenix:execution-account-lease:v1:"

# Vectores calculados INDEPENDIENTEMENTE del código bajo prueba
# (hashlib.sha256 + struct.unpack(">q"), ADR-017 D5).
_KNOWN_VECTORS = [
    ("acct-1", 8598282589666693132),
    ("PHX-ACCOUNT-001", -7268620538417556245),
    ("a", -3592965045856389752),
    ("ACCOUNT", -771965778036882398),
    ("acct-1 ", -4497813911984194540),
    (" acct-1", -4181999884342021649),
    ("ñandú-001", -1356934374678581340),
    ("日本語-口座", -2063576300182782365),
    ("acct\x00x", -7833364394859967262),
    ("x" * 500, 2066879582222228401),
]


def _key(value):
    return account_lock_key(ExecutionAccountId(value=value))


def _head(value):
    return hashlib.sha256(_NAMESPACE + value.encode("utf-8")).digest()[:8]


class _Obj:
    pass


class TestKnownVectors:
    @pytest.mark.parametrize("value,expected", _KNOWN_VECTORS)
    def test_known_vector(self, value, expected):
        assert _key(value) == expected

    def test_independent_reference_implementation_agrees(self):
        for i in range(500):
            value = f"acct-{i}"
            assert _key(value) == struct.unpack(">q", _head(value))[0]

    def test_namespace_and_version_prefix_matter(self):
        value = "acct-1"
        without_prefix = struct.unpack(">q", hashlib.sha256(value.encode()).digest()[:8])[0]
        v2 = struct.unpack(
            ">q", hashlib.sha256(b"phoenix:execution-account-lease:v2:" + value.encode()).digest()[:8]
        )[0]
        assert _key(value) not in (without_prefix, v2)

    def test_it_is_not_python_hash(self):
        assert _key("acct-1") != hash("acct-1")


class TestProperties:
    def test_deterministic_within_a_process(self):
        assert [_key("acct-1") for _ in range(5)] == [8598282589666693132] * 5

    def test_returns_exactly_int(self):
        assert type(_key("acct-1")) is int

    def test_signed_bigint_range(self):
        keys = [_key(f"acct-{i}") for i in range(5000)]
        assert all(-(2**63) <= k < 2**63 for k in keys)
        assert any(k < 0 for k in keys) and any(k > 0 for k in keys)

    def test_distinct_accounts_get_distinct_keys(self):
        assert len({_key(f"acct-{i}") for i in range(20000)}) == 20000

    def test_value_is_literal_no_normalization(self):
        keys = {_key("acct-1"), _key("acct-1 "), _key(" acct-1"), _key("ACCT-1"), _key("Acct-1")}
        assert len(keys) == 5

    def test_unicode_is_encoded_as_utf8(self):
        value = "ñandú-001"
        assert _key(value) == int.from_bytes(_head(value), "big", signed=True)
        latin1 = hashlib.sha256(_NAMESPACE + value.encode("latin-1")).digest()[:8]
        assert _key(value) != int.from_bytes(latin1, "big", signed=True)

    def test_uses_big_endian_and_signed_interpretation(self):
        head = _head("a")
        assert _key("a") == int.from_bytes(head, "big", signed=True)
        assert _key("a") != int.from_bytes(head, "little", signed=True)
        assert _key("a") != int.from_bytes(head, "big", signed=False)
        assert _key("a") < 0 < int.from_bytes(head, "big", signed=False)

    def test_uses_exactly_the_first_64_bits(self):
        digest = hashlib.sha256(_NAMESPACE + b"a").digest()
        assert _key("a") != int.from_bytes(digest[:4], "big", signed=True)
        assert _key("a") != int.from_bytes(digest[:16], "big", signed=True)
        assert _key("a") != int.from_bytes(digest[-8:], "big", signed=True)

    def test_uses_sha256_not_another_hash(self):
        for algo in ("sha1", "sha512", "sha3_256", "blake2b", "md5"):
            digest = hashlib.new(algo, _NAMESPACE + b"a").digest()
            assert _key("a") != int.from_bytes(digest[:8], "big", signed=True), algo

    def test_lone_surrogate_fails_closed_instead_of_being_replaced(self):
        with pytest.raises(UnicodeEncodeError):
            _key("acct-\ud800")


class TestTypeAttacks:
    @pytest.mark.parametrize("bad", [
        "acct-1", None, 1, True, b"acct-1", _Obj(), ExecutionOrderId(value="ord_" + "a" * 32),
    ], ids=["str", "none", "int", "bool", "bytes", "obj", "order-id"])
    def test_requires_an_execution_account_id(self, bad):
        with pytest.raises(TypeError):
            account_lock_key(bad)

    def test_no_coercion_of_a_look_alike(self):
        class Fake:
            value = "acct-1"

        with pytest.raises(TypeError):
            account_lock_key(Fake())


class TestCrossProcessStability:
    # El mismo id debe dar la misma clave en procesos distintos, aun con
    # aleatorización de hash() distinta (PYTHONHASHSEED).
    _SCRIPT = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "from execution_gateway.execution_account_lock_key import account_lock_key;"
        "from execution_gateway.execution_identity_contracts import ExecutionAccountId;"
        "print(','.join(str(account_lock_key(ExecutionAccountId(value=f'acct-{i}'))) for i in range(300)))"
    )

    @pytest.mark.parametrize("hash_seed", ["0", "1", "12345", "random"])
    def test_same_keys_in_a_separate_process(self, hash_seed):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed, PYTHONDONTWRITEBYTECODE="1")
        out = subprocess.run(
            [sys.executable, "-c", self._SCRIPT, _PLATFORM_DIR],
            capture_output=True, text=True, env=env, timeout=60, check=True,
        ).stdout.strip()
        assert [int(x) for x in out.split(",")] == [_key(f"acct-{i}") for i in range(300)]

    def test_python_builtin_hash_does_differ_across_processes_which_is_why_it_is_not_used(self):
        def run(seed):
            return subprocess.run(
                [sys.executable, "-c", "print(hash('acct-1'))"],
                capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=seed), check=True,
            ).stdout

        assert run("1") != run("2")


class TestPurity:
    def _tree(self):
        return ast.parse(inspect.getsource(_module))

    def test_imports_are_exactly_hashlib_and_the_identity_contract(self):
        names = set()
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Import):
                names |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module)
        assert names == {"hashlib", "execution_gateway.execution_identity_contracts"}

    def test_no_builtin_hash_random_clock_environment_or_vendor_names(self):
        tree = self._tree()
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for forbidden in ("hash", "random", "uuid", "time", "environ", "getenv", "psycopg", "os", "secrets"):
            assert forbidden not in names, forbidden

    def test_exported_from_package(self):
        assert execution_gateway.account_lock_key is account_lock_key
        assert "account_lock_key" in execution_gateway.__all__

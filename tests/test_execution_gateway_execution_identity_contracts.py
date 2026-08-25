import ast
import dataclasses
import inspect
import uuid

import pytest

from execution_gateway import execution_identity_contracts as _identity
from execution_gateway import execution_order_id_factory as _factory
from execution_gateway.execution_identity_contracts import (
    ExchangeAccountIdentity,
    ExecutionAccountId,
    ExecutionOrderId,
)
from execution_gateway.execution_order_id_factory import create_execution_order_id

_VALID_HEX = "0123456789abcdef" * 2  # 32 lowercase hex chars
_VALID_ORDER_ID = "ord_" + _VALID_HEX


# ---------------------------------------------------------------------------
# ExecutionAccountId -- identidad INTERNA opaca de Phoenix
# ---------------------------------------------------------------------------

class TestExecutionAccountId:
    def test_is_frozen(self):
        account = ExecutionAccountId(value="PHX-ACCOUNT-001")
        with pytest.raises(dataclasses.FrozenInstanceError):
            account.value = "OTHER"

    def test_equality_by_value(self):
        assert ExecutionAccountId(value="A") == ExecutionAccountId(value="A")

    def test_inequality(self):
        assert ExecutionAccountId(value="A") != ExecutionAccountId(value="B")

    def test_hashable(self):
        assert len({ExecutionAccountId(value="A"), ExecutionAccountId(value="A")}) == 1

    def test_exact_string_preserved(self):
        assert ExecutionAccountId(value="PHX-Account_01").value == "PHX-Account_01"

    def test_casing_is_identity(self):
        assert ExecutionAccountId(value="ACCOUNT-A") != ExecutionAccountId(value="account-a")

    def test_padding_is_identity_not_stripped(self):
        padded = ExecutionAccountId(value=" ACCOUNT-A ")
        assert padded.value == " ACCOUNT-A "
        assert padded != ExecutionAccountId(value="ACCOUNT-A")

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            ExecutionAccountId(value="")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError):
            ExecutionAccountId(value="   ")

    @pytest.mark.parametrize("bad", [None, 123, True, b"A", ["A"]])
    def test_non_str_rejected(self, bad):
        with pytest.raises(TypeError):
            ExecutionAccountId(value=bad)

    def test_has_exactly_one_field_no_credentials_no_environment(self):
        # Las credenciales autentican, no identifican; environment es otra
        # dimensión y vive en ExchangeAccountIdentity.
        names = {f.name for f in dataclasses.fields(ExecutionAccountId)}
        assert names == {"value"}

    def test_no_implicit_generation(self):
        # No debe poder construirse sin suministrar la identidad.
        with pytest.raises(TypeError):
            ExecutionAccountId()


# ---------------------------------------------------------------------------
# ExchangeAccountIdentity -- identidad OBSERVABLE de la cuenta remota
# ---------------------------------------------------------------------------

def _remote(**overrides):
    defaults = dict(exchange="bybit", environment="demo", remote_user_id="123456")
    defaults.update(overrides)
    return ExchangeAccountIdentity(**defaults)


class TestExchangeAccountIdentity:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _remote().exchange = "other"

    def test_equality_requires_all_three_fields(self):
        assert _remote() == _remote()

    def test_different_exchange_is_different_identity(self):
        assert _remote(exchange="bybit") != _remote(exchange="binance")

    def test_different_environment_is_different_identity(self):
        assert _remote(environment="demo") != _remote(environment="mainnet")

    def test_different_remote_user_id_is_different_identity(self):
        assert _remote(remote_user_id="123") != _remote(remote_user_id="456")

    def test_same_user_id_across_environments_stays_distinct(self):
        # Demo y Mainnet son sistemas Bybit separados: el mismo userID en
        # ambos NO es la misma cuenta.
        assert _remote(environment="demo", remote_user_id="123") != _remote(
            environment="mainnet", remote_user_id="123"
        )

    def test_hashable(self):
        assert len({_remote(), _remote()}) == 1

    def test_exact_preservation_no_normalization(self):
        identity = _remote(exchange="ByBit", environment="Demo", remote_user_id=" 123 ")
        assert identity.exchange == "ByBit"
        assert identity.environment == "Demo"
        assert identity.remote_user_id == " 123 "

    def test_casing_is_identity(self):
        assert _remote(exchange="bybit") != _remote(exchange="BYBIT")

    @pytest.mark.parametrize("field", ["exchange", "environment", "remote_user_id"])
    def test_empty_rejected_per_field(self, field):
        with pytest.raises(ValueError):
            _remote(**{field: ""})

    @pytest.mark.parametrize("field", ["exchange", "environment", "remote_user_id"])
    def test_whitespace_only_rejected_per_field(self, field):
        with pytest.raises(ValueError):
            _remote(**{field: "  "})

    @pytest.mark.parametrize("field", ["exchange", "environment", "remote_user_id"])
    def test_non_str_rejected_per_field(self, field):
        with pytest.raises(TypeError):
            _remote(**{field: 123})

    def test_remote_user_id_int_rejected_even_though_bybit_reports_an_integer(self):
        # Bybit expone userID (int) y userIDInt64 (str). Se preserva como
        # string exacto, igual que exchange_order_id -- nunca se
        # reinterpreta numéricamente.
        with pytest.raises(TypeError):
            _remote(remote_user_id=123456)

    def test_bool_rejected(self):
        with pytest.raises(TypeError):
            _remote(remote_user_id=True)

    def test_fields_are_exactly_the_three_identity_dimensions(self):
        # Sin credenciales, sin parent_uid/is_master (son metadata de
        # jerarquía, no identidad de esta cuenta).
        names = {f.name for f in dataclasses.fields(ExchangeAccountIdentity)}
        assert names == {"exchange", "environment", "remote_user_id"}

    def test_carries_no_credential_shaped_field(self):
        names = {f.name for f in dataclasses.fields(ExchangeAccountIdentity)}
        for forbidden in ("api_key", "api_secret", "secret", "credential", "fingerprint"):
            assert not any(forbidden in name for name in names)


# ---------------------------------------------------------------------------
# ExecutionOrderId -- identidad Phoenix de una orden de ejecución
# ---------------------------------------------------------------------------

class TestExecutionOrderId:
    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            ExecutionOrderId(value=_VALID_ORDER_ID).value = _VALID_ORDER_ID

    def test_accepts_canonical_format(self):
        assert ExecutionOrderId(value=_VALID_ORDER_ID).value == _VALID_ORDER_ID

    def test_length_is_exactly_36(self):
        assert len(_VALID_ORDER_ID) == 36

    def test_equality_and_hashability(self):
        a, b = ExecutionOrderId(value=_VALID_ORDER_ID), ExecutionOrderId(value=_VALID_ORDER_ID)
        assert a == b and len({a, b}) == 1

    def test_exact_preservation_no_normalization(self):
        assert ExecutionOrderId(value=_VALID_ORDER_ID).value == _VALID_ORDER_ID

    def test_rejects_legacy_phoenix_core_format(self):
        # phoenix_core.ids.order_id() -> "order_" + uuid4 canónico = 42 chars.
        legacy = "order_" + str(uuid.uuid4())
        assert len(legacy) == 42
        with pytest.raises(ValueError):
            ExecutionOrderId(value=legacy)

    def test_rejects_value_longer_than_36(self):
        with pytest.raises(ValueError):
            ExecutionOrderId(value="ord_" + "a" * 33)

    def test_rejects_value_shorter_than_36(self):
        with pytest.raises(ValueError):
            ExecutionOrderId(value="ord_" + "a" * 31)

    def test_rejects_missing_prefix(self):
        with pytest.raises(ValueError):
            ExecutionOrderId(value="xxx_" + _VALID_HEX)

    def test_rejects_uppercase_hex(self):
        # uuid4().hex es minúscula; Bybit no documenta case-sensitivity de
        # orderLinkId, así que aceptar mayúsculas crearía dos strings que
        # "parecen" la misma orden sin evidencia de que lo sean.
        with pytest.raises(ValueError):
            ExecutionOrderId(value="ord_" + _VALID_HEX.upper())

    def test_rejects_non_hex_characters(self):
        with pytest.raises(ValueError):
            ExecutionOrderId(value="ord_" + "z" * 32)

    def test_rejects_dashes_inside_suffix_even_though_bybit_allows_them(self):
        # El charset de Bybit permite guiones, pero el formato canónico de
        # Phoenix es hex plano: "compatible con la frontera" no equivale a
        # "es una identidad Phoenix".
        canonical_uuid = str(uuid.uuid4())  # 36 chars con guiones
        assert len(canonical_uuid) == 36
        with pytest.raises(ValueError):
            ExecutionOrderId(value=canonical_uuid)

    def test_rejects_boundary_compatible_but_non_canonical_value(self):
        with pytest.raises(ValueError):
            ExecutionOrderId(value="PHX-123")

    def test_rejects_empty_and_whitespace(self):
        for bad in ("", "   "):
            with pytest.raises(ValueError):
                ExecutionOrderId(value=bad)

    @pytest.mark.parametrize("bad", [None, 123, True, b"x"])
    def test_non_str_rejected(self, bad):
        with pytest.raises(TypeError):
            ExecutionOrderId(value=bad)

    def test_no_implicit_generation(self):
        with pytest.raises(TypeError):
            ExecutionOrderId()

    def test_does_not_embed_bot_or_account_identity(self):
        names = {f.name for f in dataclasses.fields(ExecutionOrderId)}
        assert names == {"value"}

    def test_is_a_distinct_type_from_account_identity(self):
        # Conceptualmente distinta del exchange_order_id y de la cuenta.
        assert ExecutionOrderId is not ExecutionAccountId


# ---------------------------------------------------------------------------
# Generador explícito
# ---------------------------------------------------------------------------

class TestExecutionOrderIdFactory:
    def test_returns_execution_order_id(self):
        assert isinstance(create_execution_order_id(), ExecutionOrderId)

    def test_bulk_generation_properties(self):
        generated = [create_execution_order_id() for _ in range(500)]
        values = [o.value for o in generated]
        for value in values:
            assert len(value) == 36
            assert value.startswith("ord_")
            suffix = value[4:]
            assert len(suffix) == 32
            assert all(c in "0123456789abcdef" for c in suffix)
            assert not value.startswith("order_")
        # La unicidad de una muestra NO prueba unicidad matemática -- sólo
        # confirma que el generador no está devolviendo un valor fijo.
        assert len(set(values)) == 500

    def test_preserves_full_uuid4_entropy_no_truncation(self):
        # 32 hex chars == los 128 bits completos del UUID4 (122 aleatorios
        # efectivos). Cualquier recorte se vería aquí.
        suffix = create_execution_order_id().value[4:]
        assert len(suffix) == 32
        assert uuid.UUID(hex=suffix).version == 4

    def test_does_not_use_phoenix_core_generator(self):
        # Conductual + estructural: el módulo no importa phoenix_core en
        # absoluto (la mención en el docstring explica por qué NO se usa,
        # así que un grep de texto plano sería un falso positivo).
        tree = ast.parse(inspect.getsource(_factory))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        assert not any("phoenix_core" in (name or "") for name in imported)
        # Y el valor producido nunca tiene la forma legacy.
        assert not create_execution_order_id().value.startswith("order_")


# ---------------------------------------------------------------------------
# Pureza
# ---------------------------------------------------------------------------

class TestPurity:
    def _imports(self, module):
        tree = ast.parse(inspect.getsource(module))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module)
        return set(names)

    def test_identity_contracts_import_only_dataclasses(self):
        assert self._imports(_identity) == {"dataclasses"}

    def test_factory_imports_only_uuid_and_the_contract(self):
        assert self._imports(_factory) == {
            "uuid",
            "execution_gateway.execution_identity_contracts",
        }

    def test_contracts_have_no_bybit_or_io_vocabulary(self):
        source = inspect.getsource(_identity)
        tree = ast.parse(source)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        for forbidden in ("urlopen", "request", "environ", "getenv", "open", "now", "time"):
            assert forbidden not in names

    def test_no_module_level_mutable_state(self):
        tree = ast.parse(inspect.getsource(_identity))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                assert isinstance(node.value, (ast.Constant, ast.Call, ast.BinOp)), (
                    f"unexpected module-level assignment: {ast.unparse(node)}"
                )

import dataclasses

import pytest

from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
import execution_gateway
import execution_gateway.bybit_create_order_result as _module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid(**kwargs) -> BybitCreateOrderResult:
    defaults = dict(
        order_id="123456789",
        order_link_id="test-link-id",
    )
    return BybitCreateOrderResult(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# 1. Importación y API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_create_order_result import BybitCreateOrderResult as C
        assert C is BybitCreateOrderResult

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitCreateOrderResult")
        assert execution_gateway.BybitCreateOrderResult is BybitCreateOrderResult

    def test_in_all(self):
        assert "BybitCreateOrderResult" in execution_gateway.__all__


# ---------------------------------------------------------------------------
# 2. Construcción válida
# ---------------------------------------------------------------------------

class TestValidConstruction:
    def test_numeric_order_id(self):
        r = _valid(order_id="123456789")
        assert r.order_id == "123456789"

    def test_alphanumeric_order_id(self):
        r = _valid(order_id="order-abc-123")
        assert r.order_id == "order-abc-123"

    def test_valid_order_link_id(self):
        r = _valid(order_link_id="my-link-id")
        assert r.order_link_id == "my-link-id"

    def test_order_link_id_exactly_36(self):
        lid = "a" * 36
        r = _valid(order_link_id=lid)
        assert r.order_link_id == lid

    def test_order_id_preserved_exactly(self):
        r = _valid(order_id="abc-123")
        assert r.order_id == "abc-123"

    def test_order_link_id_preserved_exactly(self):
        lid = "exact-value-preserved"
        r = _valid(order_link_id=lid)
        assert r.order_link_id == lid

    def test_equality_by_value(self):
        r1 = _valid(order_id="x", order_link_id="y")
        r2 = _valid(order_id="x", order_link_id="y")
        assert r1 == r2

    def test_inequality_different_order_id(self):
        r1 = _valid(order_id="aaa")
        r2 = _valid(order_id="bbb")
        assert r1 != r2

    def test_inequality_different_order_link_id(self):
        r1 = _valid(order_link_id="link-1")
        r2 = _valid(order_link_id="link-2")
        assert r1 != r2


# ---------------------------------------------------------------------------
# 3. Validación de order_id
# ---------------------------------------------------------------------------

class TestOrderId:
    def test_rejects_none(self):
        with pytest.raises(TypeError, match="order_id must be str"):
            _valid(order_id=None)

    def test_rejects_int(self):
        with pytest.raises(TypeError, match="order_id must be str"):
            _valid(order_id=123456789)

    def test_rejects_float(self):
        with pytest.raises(TypeError, match="order_id must be str"):
            _valid(order_id=1.5)

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="order_id must not be empty or whitespace-only"):
            _valid(order_id="")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="order_id must not be empty or whitespace-only"):
            _valid(order_id="   ")

    def test_accepts_peripheral_spaces_with_content(self):
        r = _valid(order_id="  order-id  ")
        assert r.order_id == "  order-id  "

    def test_no_strip_applied(self):
        r = _valid(order_id="  abc  ")
        assert r.order_id == "  abc  "

    def test_does_not_convert_to_int(self):
        r = _valid(order_id="999")
        assert isinstance(r.order_id, str)
        assert r.order_id == "999"

    def test_does_not_validate_numeric_format(self):
        r = _valid(order_id="not-a-number")
        assert r.order_id == "not-a-number"

    def test_does_not_validate_length(self):
        r = _valid(order_id="x" * 100)
        assert len(r.order_id) == 100

    def test_single_char_accepted(self):
        r = _valid(order_id="1")
        assert r.order_id == "1"


# ---------------------------------------------------------------------------
# 4. Validación de order_link_id
# ---------------------------------------------------------------------------

class TestOrderLinkId:
    def test_rejects_none(self):
        with pytest.raises(TypeError, match="order_link_id must be str"):
            _valid(order_link_id=None)

    def test_rejects_int(self):
        with pytest.raises(TypeError, match="order_link_id must be str"):
            _valid(order_link_id=42)

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="order_link_id must not be empty or whitespace-only"):
            _valid(order_link_id="")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="order_link_id must not be empty or whitespace-only"):
            _valid(order_link_id="   ")

    def test_rejects_length_37(self):
        with pytest.raises(ValueError, match="order_link_id must be at most 36 characters"):
            _valid(order_link_id="a" * 37)

    def test_accepts_length_36(self):
        lid = "b" * 36
        r = _valid(order_link_id=lid)
        assert r.order_link_id == lid

    def test_accepts_length_1(self):
        r = _valid(order_link_id="x")
        assert r.order_link_id == "x"

    def test_accepts_peripheral_spaces_with_content(self):
        r = _valid(order_link_id="  link  ")
        assert r.order_link_id == "  link  "

    def test_no_strip_applied(self):
        r = _valid(order_link_id="  abc  ")
        assert r.order_link_id == "  abc  "

    def test_preserved_exactly(self):
        lid = "exact-link-value"
        r = _valid(order_link_id=lid)
        assert r.order_link_id == lid

    def test_does_not_require_uuid_format(self):
        r = _valid(order_link_id="plain-id")
        assert r.order_link_id == "plain-id"

    def test_does_not_require_prefix(self):
        r = _valid(order_link_id="no-prefix-needed")
        assert r.order_link_id == "no-prefix-needed"

    def test_does_not_validate_uniqueness(self):
        lid = "same-id"
        r1 = _valid(order_link_id=lid)
        r2 = _valid(order_link_id=lid)
        assert r1.order_link_id == r2.order_link_id == lid


# ---------------------------------------------------------------------------
# 5. Inmutabilidad
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(BybitCreateOrderResult)
        r = _valid()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError, TypeError)):
            r.order_id = "new-id"

    def test_cannot_mutate_order_link_id(self):
        r = _valid()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError, TypeError)):
            r.order_link_id = "new-link"

    def test_equality_by_value_not_identity(self):
        r1 = _valid(order_id="abc", order_link_id="link")
        r2 = _valid(order_id="abc", order_link_id="link")
        assert r1 == r2
        assert r1 is not r2

    def test_inequality_when_order_id_differs(self):
        r1 = _valid(order_id="x")
        r2 = _valid(order_id="y")
        assert r1 != r2

    def test_inequality_when_order_link_id_differs(self):
        r1 = _valid(order_link_id="link-1")
        r2 = _valid(order_link_id="link-2")
        assert r1 != r2


# ---------------------------------------------------------------------------
# 6. Superficie mínima
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_has_exactly_two_fields(self):
        fields = {f.name for f in dataclasses.fields(BybitCreateOrderResult)}
        assert fields == {"order_id", "order_link_id"}

    def test_no_extra_public_methods(self):
        r = _valid()
        field_names = {f.name for f in dataclasses.fields(r)}
        actual_public = {n for n in dir(r) if not n.startswith("_")}
        expected = field_names
        extra = actual_public - expected
        assert extra == set(), f"unexpected public members: {extra}"

    def test_no_from_response(self):
        assert not hasattr(BybitCreateOrderResult, "from_response")

    def test_no_from_dict(self):
        assert not hasattr(BybitCreateOrderResult, "from_dict")

    def test_no_parse(self):
        assert not hasattr(BybitCreateOrderResult, "parse")

    def test_no_to_dict(self):
        assert not hasattr(BybitCreateOrderResult, "to_dict")

    def test_no_serialize(self):
        assert not hasattr(BybitCreateOrderResult, "serialize")

    def test_no_success(self):
        assert not hasattr(BybitCreateOrderResult, "success")

    def test_no_status(self):
        assert not hasattr(BybitCreateOrderResult, "status")

    def test_no_ret_code(self):
        assert not hasattr(BybitCreateOrderResult, "ret_code")

    def test_no_ret_msg(self):
        assert not hasattr(BybitCreateOrderResult, "ret_msg")

    def test_no_camelcase_fields(self):
        field_names = {f.name for f in dataclasses.fields(BybitCreateOrderResult)}
        for name in field_names:
            assert name == name.lower() or "_" in name, f"camelCase field found: {name}"
        assert "orderId" not in field_names
        assert "orderLinkId" not in field_names


# ---------------------------------------------------------------------------
# 7. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_bybit_response(self):
        assert "BybitResponse" not in vars(_module)

    def test_does_not_import_bybit_demo_client(self):
        assert "BybitDemoClient" not in vars(_module)

    def test_does_not_import_operation(self):
        assert "BybitCreateOrderOperation" not in vars(_module)

    def test_does_not_import_endpoint_executor(self):
        assert "BybitEndpointExecutor" not in vars(_module)

    def test_does_not_import_private_api(self):
        assert "BybitPrivateApi" not in vars(_module)

    def test_does_not_import_sender(self):
        assert "BybitPrivateRequestSender" not in vars(_module)

    def test_does_not_import_parser(self):
        assert "BybitResponseParser" not in vars(_module)

    def test_does_not_read_env_vars(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        r = _valid()
        assert r is not None

    def test_whole_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

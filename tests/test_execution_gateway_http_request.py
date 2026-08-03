import pytest
import execution_gateway
from execution_gateway.http_request import HttpRequest


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.http_request import HttpRequest as R
        assert R is HttpRequest

    def test_public_import(self):
        assert hasattr(execution_gateway, "HttpRequest")
        assert execution_gateway.HttpRequest is HttpRequest

    def test_in_all(self):
        assert "HttpRequest" in execution_gateway.__all__


# ── construction & frozen ──────────────────────────────────────────────────

class TestConstruction:
    def test_valid_construction(self):
        r = HttpRequest(url="https://example.com", headers={"k": "v"}, body="hello")
        assert r.url == "https://example.com"
        assert r.headers == {"k": "v"}
        assert r.body == "hello"

    def test_frozen_url(self):
        r = HttpRequest(url="https://example.com", headers={}, body="")
        with pytest.raises((AttributeError, TypeError)):
            r.url = "https://other.com"

    def test_frozen_headers(self):
        r = HttpRequest(url="https://example.com", headers={}, body="")
        with pytest.raises((AttributeError, TypeError)):
            r.headers = {"x": "y"}

    def test_frozen_body(self):
        r = HttpRequest(url="https://example.com", headers={}, body="")
        with pytest.raises((AttributeError, TypeError)):
            r.body = "changed"

    def test_equality_same_fields(self):
        r1 = HttpRequest(url="https://example.com", headers={"k": "v"}, body="x")
        r2 = HttpRequest(url="https://example.com", headers={"k": "v"}, body="x")
        assert r1 == r2

    def test_inequality_different_url(self):
        r1 = HttpRequest(url="https://a.com", headers={}, body="x")
        r2 = HttpRequest(url="https://b.com", headers={}, body="x")
        assert r1 != r2

    def test_inequality_different_headers(self):
        r1 = HttpRequest(url="https://a.com", headers={"k": "1"}, body="x")
        r2 = HttpRequest(url="https://a.com", headers={"k": "2"}, body="x")
        assert r1 != r2

    def test_inequality_different_body(self):
        r1 = HttpRequest(url="https://a.com", headers={}, body="x")
        r2 = HttpRequest(url="https://a.com", headers={}, body="y")
        assert r1 != r2

    def test_accepts_empty_headers(self):
        r = HttpRequest(url="https://example.com", headers={}, body="")
        assert r.headers == {}

    def test_accepts_empty_body(self):
        r = HttpRequest(url="https://example.com", headers={}, body="")
        assert r.body == ""

    def test_multiple_headers_stored(self):
        h = {"A": "1", "B": "2", "C": "3"}
        r = HttpRequest(url="https://example.com", headers=h, body="")
        assert r.headers == h


# ── url validation ─────────────────────────────────────────────────────────

class TestUrlValidation:
    def test_rejects_non_str_url(self):
        with pytest.raises(TypeError):
            HttpRequest(url=123, headers={}, body="")

    def test_rejects_none_url(self):
        with pytest.raises(TypeError):
            HttpRequest(url=None, headers={}, body="")

    def test_rejects_empty_url(self):
        with pytest.raises(ValueError):
            HttpRequest(url="", headers={}, body="")

    def test_rejects_whitespace_url(self):
        with pytest.raises(ValueError):
            HttpRequest(url="   ", headers={}, body="")


# ── headers validation ─────────────────────────────────────────────────────

class TestHeadersValidation:
    def test_rejects_non_dict_headers(self):
        with pytest.raises(TypeError):
            HttpRequest(url="https://example.com", headers=[("k", "v")], body="")

    def test_rejects_none_headers(self):
        with pytest.raises(TypeError):
            HttpRequest(url="https://example.com", headers=None, body="")

    def test_rejects_non_str_header_key(self):
        with pytest.raises(TypeError):
            HttpRequest(url="https://example.com", headers={1: "v"}, body="")

    def test_rejects_non_str_header_value(self):
        with pytest.raises(TypeError):
            HttpRequest(url="https://example.com", headers={"k": 1}, body="")


# ── body validation ────────────────────────────────────────────────────────

class TestBodyValidation:
    def test_rejects_non_str_body(self):
        with pytest.raises(TypeError):
            HttpRequest(url="https://example.com", headers={}, body=b"bytes")

    def test_rejects_none_body(self):
        with pytest.raises(TypeError):
            HttpRequest(url="https://example.com", headers={}, body=None)


# ── headers isolation ──────────────────────────────────────────────────────

class TestHeadersIsolation:
    def test_external_mutation_does_not_affect_stored_headers(self):
        original = {"X-Key": "val"}
        r = HttpRequest(url="https://example.com", headers=original, body="")
        original["X-Key"] = "mutated"
        assert r.headers["X-Key"] == "val"

    def test_stored_headers_cannot_be_mutated(self):
        r = HttpRequest(url="https://example.com", headers={"X-Key": "val"}, body="")
        with pytest.raises(TypeError):
            r.headers["X-Key"] = "mutated"

    def test_stored_headers_cannot_be_cleared(self):
        r = HttpRequest(url="https://example.com", headers={"X-Key": "val"}, body="")
        with pytest.raises(AttributeError):
            r.headers.clear()

    def test_stored_headers_cannot_add_new_key(self):
        r = HttpRequest(url="https://example.com", headers={"X-Key": "val"}, body="")
        with pytest.raises(TypeError):
            r.headers["NEW"] = "x"


# ── tipo público (Core Hardening Pack A, Parte D) ──────────────────────────

class TestHeadersType:
    def test_headers_is_a_mapping(self):
        from collections.abc import Mapping
        r = HttpRequest(url="https://example.com", headers={"A": "1"}, body="")
        assert isinstance(r.headers, Mapping)

    def test_headers_is_mapping_proxy(self):
        from types import MappingProxyType
        r = HttpRequest(url="https://example.com", headers={"A": "1"}, body="")
        assert isinstance(r.headers, MappingProxyType)

    def test_headers_supports_items_iteration(self):
        r = HttpRequest(url="https://example.com", headers={"A": "1", "B": "2"}, body="")
        assert dict(r.headers.items()) == {"A": "1", "B": "2"}

    def test_headers_equality_against_plain_dict(self):
        r = HttpRequest(url="https://example.com", headers={"A": "1"}, body="")
        assert r.headers == {"A": "1"}


# ── aceptación de cualquier Mapping válido (Auditoría A final, H2) ─────────

class TestHeadersAcceptsAnyMapping:
    def test_accepts_plain_dict(self):
        r = HttpRequest(url="https://example.com", headers={"A": "1"}, body="")
        assert r.headers == {"A": "1"}

    def test_accepts_mapping_proxy_directly(self):
        from types import MappingProxyType
        proxy = MappingProxyType({"A": "1"})
        r = HttpRequest(url="https://example.com", headers=proxy, body="")
        assert r.headers == {"A": "1"}

    def test_accepts_custom_mapping(self):
        from collections.abc import Mapping

        class _CustomMapping(Mapping):
            def __init__(self, data):
                self._data = data
            def __getitem__(self, key):
                return self._data[key]
            def __iter__(self):
                return iter(self._data)
            def __len__(self):
                return len(self._data)

        r = HttpRequest(url="https://example.com", headers=_CustomMapping({"A": "1"}), body="")
        assert r.headers == {"A": "1"}

    def test_round_trip_accepts_own_exposed_headers(self):
        original = HttpRequest(url="https://example.com", headers={"A": "1", "B": "2"}, body="")
        round_tripped = HttpRequest(url="https://example.com", headers=original.headers, body="")
        assert round_tripped.headers == {"A": "1", "B": "2"}

    def test_round_tripped_headers_are_also_immutable(self):
        original = HttpRequest(url="https://example.com", headers={"A": "1"}, body="")
        round_tripped = HttpRequest(url="https://example.com", headers=original.headers, body="")
        with pytest.raises(TypeError):
            round_tripped.headers["A"] = "mutated"

    def test_round_trip_copies_defensively_not_by_reference(self):
        original = HttpRequest(url="https://example.com", headers={"A": "1"}, body="")
        round_tripped = HttpRequest(url="https://example.com", headers=original.headers, body="")
        assert round_tripped.headers is not original.headers

    def test_still_rejects_non_mapping_sequence(self):
        with pytest.raises(TypeError):
            HttpRequest(url="https://example.com", headers=[("k", "v")], body="")

    def test_still_rejects_none(self):
        with pytest.raises(TypeError):
            HttpRequest(url="https://example.com", headers=None, body="")

    def test_still_validates_keys_and_values_of_custom_mapping(self):
        from collections.abc import Mapping

        class _BadMapping(Mapping):
            def __init__(self, data):
                self._data = data
            def __getitem__(self, key):
                return self._data[key]
            def __iter__(self):
                return iter(self._data)
            def __len__(self):
                return len(self._data)

        with pytest.raises(TypeError):
            HttpRequest(url="https://example.com", headers=_BadMapping({1: "v"}), body="")


# ── repr seguro (Core Hardening Pack A, Parte F) ───────────────────────────

class TestSafeRepr:
    def test_repr_does_not_expose_api_key_value(self):
        marker = "ZZAPIKEYMARKER9999"
        r = HttpRequest(
            url="https://api-demo.bybit.com/v5/order/create",
            headers={"X-BAPI-API-KEY": marker},
            body="{}",
        )
        assert marker not in repr(r)

    def test_repr_does_not_expose_signature_value(self):
        marker = "ZZSIGNATUREMARKER9999"
        r = HttpRequest(
            url="https://api-demo.bybit.com/v5/order/create",
            headers={"X-BAPI-SIGN": marker},
            body="{}",
        )
        assert marker not in repr(r)

    def test_repr_does_not_expose_body(self):
        marker = "ZZBODYMARKER9999"
        r = HttpRequest(url="https://example.com", headers={}, body=f'{{"secret": "{marker}"}}')
        assert marker not in repr(r)

    def test_str_does_not_expose_secrets(self):
        marker = "ZZSTRMARKER9999"
        r = HttpRequest(
            url="https://example.com",
            headers={"X-BAPI-SIGN": marker},
            body=marker,
        )
        assert marker not in str(r)

    def test_repr_shows_url(self):
        r = HttpRequest(url="https://api-demo.bybit.com/v5/order/create", headers={}, body="")
        assert "https://api-demo.bybit.com/v5/order/create" in repr(r)

    def test_repr_shows_header_names_only(self):
        r = HttpRequest(
            url="https://example.com",
            headers={"X-BAPI-API-KEY": "secret-value", "Content-Type": "application/json"},
            body="",
        )
        assert "X-BAPI-API-KEY" in repr(r)
        assert "Content-Type" in repr(r)
        assert "secret-value" not in repr(r)

    def test_repr_is_deterministic(self):
        r = HttpRequest(url="https://example.com", headers={"B": "2", "A": "1"}, body="x")
        assert repr(r) == repr(r)

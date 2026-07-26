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

    def test_stored_headers_mutation_does_not_propagate(self):
        r = HttpRequest(url="https://example.com", headers={"X-Key": "val"}, body="")
        r.headers["X-Key"] = "mutated"
        r2 = HttpRequest(url="https://example.com", headers={"X-Key": "val"}, body="")
        assert r2.headers["X-Key"] == "val"

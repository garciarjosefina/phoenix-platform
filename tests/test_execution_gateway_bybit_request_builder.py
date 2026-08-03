import pytest
import execution_gateway
from execution_gateway.bybit_request_builder import BybitRequestBuilder
from execution_gateway.bybit_authenticator import BybitAuthentication, BybitAuthenticator
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.http_request import HttpRequest
from execution_gateway.json_serializer import JsonSerializer
from execution_gateway.credentials import BybitDemoCredentials
from execution_gateway.hmac_sha256_signer import HmacSha256Signer
from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator
from execution_gateway.standard_json_serializer import StandardJsonSerializer


# ── helpers ────────────────────────────────────────────────────────────────

def _make_auth() -> BybitAuthentication:
    return BybitAuthentication(
        timestamp_ms=1_700_000_000_000,
        api_key="test_key",
        recv_window_ms=5_000,
        signature="abc123",
    )


class _FakeSerializer:
    def __init__(self, result: str = '{"ok":1}'):
        self._result = result
        self.call_count = 0
        self.last_value = None

    def dumps(self, value: object) -> str:
        self.call_count += 1
        self.last_value = value
        return self._result

    def loads(self, value: str) -> object:
        return {}


class _FakeAuthenticator:
    def __init__(self, result: BybitAuthentication | None = None):
        self._result = result or _make_auth()
        self.call_count = 0
        self.last_body: str | None = None

    def authenticate(self, *, body: str) -> BybitAuthentication:
        self.call_count += 1
        self.last_body = body
        return self._result


class _SpyHeaderBuilder(BybitHeaderBuilder):
    def __init__(self) -> None:
        self.call_count = 0
        self.last_authentication: BybitAuthentication | None = None

    def build(self, *, authentication: BybitAuthentication) -> dict[str, str]:
        self.call_count += 1
        self.last_authentication = authentication
        return super().build(authentication=authentication)


def _make_builder(
    serializer_result: str = '{"ok":1}',
) -> tuple[BybitRequestBuilder, _FakeSerializer, _FakeAuthenticator, _SpyHeaderBuilder]:
    s = _FakeSerializer(result=serializer_result)
    a = _FakeAuthenticator()
    h = _SpyHeaderBuilder()
    b = BybitRequestBuilder(serializer=s, authenticator=a, header_builder=h)
    return b, s, a, h


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_request_builder import BybitRequestBuilder as B
        assert B is BybitRequestBuilder

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitRequestBuilder")
        assert execution_gateway.BybitRequestBuilder is BybitRequestBuilder

    def test_in_all(self):
        assert "BybitRequestBuilder" in execution_gateway.__all__


# ── constructor ────────────────────────────────────────────────────────────

class TestConstructor:
    def test_valid_construction(self):
        builder, _, _, _ = _make_builder()
        assert builder is not None

    def test_rejects_non_serializer(self):
        with pytest.raises(TypeError):
            BybitRequestBuilder(
                serializer=object(),
                authenticator=_FakeAuthenticator(),
                header_builder=_SpyHeaderBuilder(),
            )

    def test_rejects_none_serializer(self):
        with pytest.raises(TypeError):
            BybitRequestBuilder(
                serializer=None,
                authenticator=_FakeAuthenticator(),
                header_builder=_SpyHeaderBuilder(),
            )

    def test_rejects_non_authenticator(self):
        with pytest.raises(TypeError):
            BybitRequestBuilder(
                serializer=_FakeSerializer(),
                authenticator=object(),
                header_builder=_SpyHeaderBuilder(),
            )

    def test_rejects_none_authenticator(self):
        with pytest.raises(TypeError):
            BybitRequestBuilder(
                serializer=_FakeSerializer(),
                authenticator=None,
                header_builder=_SpyHeaderBuilder(),
            )

    def test_rejects_non_header_builder(self):
        with pytest.raises(TypeError):
            BybitRequestBuilder(
                serializer=_FakeSerializer(),
                authenticator=_FakeAuthenticator(),
                header_builder=object(),
            )

    def test_rejects_none_header_builder(self):
        with pytest.raises(TypeError):
            BybitRequestBuilder(
                serializer=_FakeSerializer(),
                authenticator=_FakeAuthenticator(),
                header_builder=None,
            )

    def test_accepts_protocol_compatible_serializer(self):
        class _AltSerializer:
            def dumps(self, value: object) -> str:
                return "{}"
            def loads(self, value: str) -> object:
                return {}

        assert isinstance(_AltSerializer(), JsonSerializer)
        builder = BybitRequestBuilder(
            serializer=_AltSerializer(),
            authenticator=_FakeAuthenticator(),
            header_builder=_SpyHeaderBuilder(),
        )
        assert builder is not None

    def test_accepts_protocol_compatible_authenticator(self):
        class _AltAuthenticator:
            def authenticate(self, *, body: str) -> BybitAuthentication:
                return _make_auth()

        assert isinstance(_AltAuthenticator(), BybitAuthenticator)
        builder = BybitRequestBuilder(
            serializer=_FakeSerializer(),
            authenticator=_AltAuthenticator(),
            header_builder=_SpyHeaderBuilder(),
        )
        assert builder is not None

    def test_accepts_subclass_header_builder(self):
        builder = BybitRequestBuilder(
            serializer=_FakeSerializer(),
            authenticator=_FakeAuthenticator(),
            header_builder=_SpyHeaderBuilder(),
        )
        assert builder is not None


# ── build output ───────────────────────────────────────────────────────────

class TestBuildOutput:
    def test_returns_http_request(self):
        builder, _, _, _ = _make_builder()
        result = builder.build(url="https://example.com/order", payload={"qty": "1"})
        assert isinstance(result, HttpRequest)

    def test_url_preserved(self):
        builder, _, _, _ = _make_builder()
        url = "https://api.bybit.com/v5/order/create"
        result = builder.build(url=url, payload={})
        assert result.url == url

    def test_body_preserved(self):
        body_str = '{"symbol":"BTCUSDT","qty":"0.001"}'
        builder, _, _, _ = _make_builder(serializer_result=body_str)
        result = builder.build(url="https://example.com", payload={})
        assert result.body == body_str

    def test_headers_preserved(self):
        builder, _, _, h = _make_builder()
        result = builder.build(url="https://example.com", payload={})
        expected = BybitHeaderBuilder().build(authentication=_make_auth())
        assert result.headers == expected

    def test_body_comes_from_serializer(self):
        builder, s, _, _ = _make_builder(serializer_result='{"x":42}')
        result = builder.build(url="https://example.com", payload={"x": 42})
        assert result.body == '{"x":42}'
        assert s.call_count == 1


# ── call counts ────────────────────────────────────────────────────────────

class TestCallCounts:
    def test_serializer_called_exactly_once(self):
        builder, s, _, _ = _make_builder()
        builder.build(url="https://example.com", payload={})
        assert s.call_count == 1

    def test_authenticator_called_exactly_once(self):
        builder, _, a, _ = _make_builder()
        builder.build(url="https://example.com", payload={})
        assert a.call_count == 1

    def test_header_builder_called_exactly_once(self):
        builder, _, _, h = _make_builder()
        builder.build(url="https://example.com", payload={})
        assert h.call_count == 1


# ── call order ─────────────────────────────────────────────────────────────

class TestCallOrder:
    def _make_ordered(self):
        log: list[str] = []

        class _OSerial:
            def dumps(self, value):
                log.append("dumps")
                return '{"o":1}'
            def loads(self, value):
                return {}

        class _OAuth:
            def authenticate(self, *, body):
                log.append("authenticate")
                return _make_auth()

        class _OHeader(BybitHeaderBuilder):
            def build(self, *, authentication):
                log.append("build")
                return super().build(authentication=authentication)

        b = BybitRequestBuilder(
            serializer=_OSerial(),
            authenticator=_OAuth(),
            header_builder=_OHeader(),
        )
        return b, log

    def test_serializer_before_authenticator(self):
        b, log = self._make_ordered()
        b.build(url="https://example.com", payload={})
        assert log.index("dumps") < log.index("authenticate")

    def test_authenticator_before_header_builder(self):
        b, log = self._make_ordered()
        b.build(url="https://example.com", payload={})
        assert log.index("authenticate") < log.index("build")

    def test_full_sequence(self):
        b, log = self._make_ordered()
        b.build(url="https://example.com", payload={})
        assert log == ["dumps", "authenticate", "build"]

    def test_serializer_result_passed_to_authenticator(self):
        builder, s, a, _ = _make_builder(serializer_result='{"body":true}')
        builder.build(url="https://example.com", payload={})
        assert a.last_body == '{"body":true}'

    def test_authentication_result_passed_to_header_builder(self):
        auth = _make_auth()
        s = _FakeSerializer()
        a = _FakeAuthenticator(result=auth)
        h = _SpyHeaderBuilder()
        b = BybitRequestBuilder(serializer=s, authenticator=a, header_builder=h)
        b.build(url="https://example.com", payload={})
        assert h.last_authentication is auth


# ── error propagation ──────────────────────────────────────────────────────

class TestErrorPropagation:
    def test_propagates_serializer_error(self):
        class _BrokenSerializer:
            def dumps(self, value):
                raise RuntimeError("serial fail")
            def loads(self, value):
                return {}

        b = BybitRequestBuilder(
            serializer=_BrokenSerializer(),
            authenticator=_FakeAuthenticator(),
            header_builder=_SpyHeaderBuilder(),
        )
        with pytest.raises(RuntimeError, match="serial fail"):
            b.build(url="https://example.com", payload={})

    def test_propagates_authenticator_error(self):
        class _BrokenAuth:
            def authenticate(self, *, body):
                raise ValueError("auth fail")

        b = BybitRequestBuilder(
            serializer=_FakeSerializer(),
            authenticator=_BrokenAuth(),
            header_builder=_SpyHeaderBuilder(),
        )
        with pytest.raises(ValueError, match="auth fail"):
            b.build(url="https://example.com", payload={})

    def test_propagates_header_builder_error(self):
        class _BrokenHeader(BybitHeaderBuilder):
            def build(self, *, authentication):
                raise RuntimeError("header fail")

        b = BybitRequestBuilder(
            serializer=_FakeSerializer(),
            authenticator=_FakeAuthenticator(),
            header_builder=_BrokenHeader(),
        )
        with pytest.raises(RuntimeError, match="header fail"):
            b.build(url="https://example.com", payload={})


# ── no side effects ────────────────────────────────────────────────────────

class TestNoSideEffects:
    def test_no_http_performed(self, monkeypatch):
        called = []
        import urllib.request
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        builder, _, _, _ = _make_builder()
        builder.build(url="https://example.com", payload={})
        assert called == []

    def test_no_http_transport_imported(self):
        import execution_gateway.bybit_request_builder as m
        assert not hasattr(m, "HttpTransport")
        assert not hasattr(m, "UrllibHttpTransport")

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.bybit_header_builder import BybitHeaderBuilder
        assert GatewayConfig().environment == "demo"
        auth = BybitAuthentication(timestamp_ms=1, api_key="k", recv_window_ms=1, signature="s")
        headers = BybitHeaderBuilder().build(authentication=auth)
        assert len(headers) == 5


# ── statelessness across consecutive build() calls ─────────────────────────

class _IncrementingClock:
    def __init__(self, start_ms: int = 1_700_000_000_000) -> None:
        self._value = start_ms

    def now_ms(self) -> int:
        self._value += 60_000
        return self._value


def _make_real_builder() -> BybitRequestBuilder:
    credentials = BybitDemoCredentials(api_key="ORDER-KEY", api_secret="ORDER-SECRET")
    authenticator = StandardBybitAuthenticator(
        credentials=credentials,
        clock=_IncrementingClock(),
        signer=HmacSha256Signer(),
        recv_window_ms=5_000,
    )
    return BybitRequestBuilder(
        serializer=StandardJsonSerializer(),
        authenticator=authenticator,
        header_builder=BybitHeaderBuilder(),
    )


class TestStatelessAcrossConsecutiveBuilds:
    def test_different_bodies_for_different_orders(self):
        builder = _make_real_builder()
        r1 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-1", "qty": "0.001"})
        r2 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-2", "qty": "99.0"})
        assert r1.body != r2.body
        assert "ORDEN-1" in r1.body
        assert "ORDEN-2" in r2.body

    def test_different_signatures_for_different_orders(self):
        builder = _make_real_builder()
        r1 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-1", "qty": "0.001"})
        r2 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-2", "qty": "99.0"})
        assert r1.headers["X-BAPI-SIGN"] != r2.headers["X-BAPI-SIGN"]

    def test_different_timestamps_for_consecutive_calls(self):
        builder = _make_real_builder()
        r1 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-1", "qty": "0.001"})
        r2 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-2", "qty": "99.0"})
        assert r1.headers["X-BAPI-TIMESTAMP"] != r2.headers["X-BAPI-TIMESTAMP"]

    def test_distinct_request_objects(self):
        builder = _make_real_builder()
        r1 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-1", "qty": "0.001"})
        r2 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-2", "qty": "99.0"})
        assert r1 is not r2
        assert r1.headers is not r2.headers

    def test_second_request_does_not_share_references_with_first(self):
        builder = _make_real_builder()
        r1 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-1", "qty": "0.001"})
        r2 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-2", "qty": "99.0"})
        assert dict(r1.headers) != dict(r2.headers)
        assert r1.headers["X-BAPI-SIGN"] != r2.headers["X-BAPI-SIGN"]
        assert r1.headers["X-BAPI-TIMESTAMP"] != r2.headers["X-BAPI-TIMESTAMP"]

    def test_third_call_independent_of_first_two(self):
        builder = _make_real_builder()
        r1 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-1", "qty": "0.001"})
        r2 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-2", "qty": "99.0"})
        r3 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-3", "qty": "5.0"})
        assert len({r1.body, r2.body, r3.body}) == 3
        assert len({r1.headers["X-BAPI-SIGN"], r2.headers["X-BAPI-SIGN"], r3.headers["X-BAPI-SIGN"]}) == 3

    def test_builder_gains_no_new_attributes_after_multiple_builds(self):
        builder = _make_real_builder()
        before = set(vars(builder))
        builder.build(url="https://x", payload={"orderLinkId": "ORDEN-1", "qty": "0.001"})
        builder.build(url="https://x", payload={"orderLinkId": "ORDEN-2", "qty": "99.0"})
        after = set(vars(builder))
        assert before == after
        assert after == {"_serializer", "_authenticator", "_header_builder"}

    def test_vars_identical_before_and_after_multiple_builds(self):
        builder = _make_real_builder()
        before = dict(vars(builder))
        builder.build(url="https://x", payload={"orderLinkId": "ORDEN-1", "qty": "0.001"})
        builder.build(url="https://x", payload={"orderLinkId": "ORDEN-2", "qty": "99.0"})
        after = dict(vars(builder))
        assert before.keys() == after.keys()
        for key in before:
            assert before[key] is after[key]

    def test_second_order_does_not_resend_first_orders_body(self):
        builder = _make_real_builder()
        r1 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-1", "qty": "0.001"})
        r2 = builder.build(url="https://x", payload={"orderLinkId": "ORDEN-2", "qty": "99.0"})
        assert "ORDEN-1" not in r2.body
        assert "0.001" not in r2.body

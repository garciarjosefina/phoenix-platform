import hashlib
import hmac

import pytest

import execution_gateway
from execution_gateway.bybit_authenticator import BybitAuthentication
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_private_get_request_sender import BybitPrivateGetRequestSender
from execution_gateway.credentials import BybitDemoCredentials
from execution_gateway.hmac_sha256_signer import HmacSha256Signer
from execution_gateway.http_get_request_executor import HttpGetRequestExecutor
from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator


class _FixedClock:
    def __init__(self, ms):
        self._ms = ms

    def now_ms(self):
        return self._ms


class _SpyAuthenticator:
    def __init__(self, authentication):
        self.calls = []
        self._authentication = authentication

    def authenticate(self, *, body):
        self.calls.append(body)
        return self._authentication


class _SpyTransport:
    """Test double for HttpGetTransport -- satisfies the Protocol structurally."""

    def __init__(self, *, result="body"):
        self.calls = []
        self._result = result

    def get(self, *, url, headers, timeout_seconds):
        self.calls.append(dict(url=url, headers=headers, timeout_seconds=timeout_seconds))
        return self._result


class _NotAnAuthenticator:
    pass


_AUTH = BybitAuthentication(
    timestamp_ms=1_700_000_000_000, api_key="demo-key", recv_window_ms=5000, signature="sig",
)


def _executor(*, result="body"):
    transport = _SpyTransport(result=result)
    return HttpGetRequestExecutor(transport=transport, timeout_seconds=10), transport


def _sender(*, authenticator=None, header_builder=None, request_executor=None):
    executor, transport = (request_executor, None) if request_executor is not None else _executor()
    return (
        BybitPrivateGetRequestSender(
            authenticator=authenticator or _SpyAuthenticator(_AUTH),
            header_builder=header_builder or BybitHeaderBuilder(),
            request_executor=executor,
        ),
        transport,
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitPrivateGetRequestSender")
        assert execution_gateway.BybitPrivateGetRequestSender is BybitPrivateGetRequestSender

    def test_in_all(self):
        assert "BybitPrivateGetRequestSender" in execution_gateway.__all__


class TestConstruction:
    def test_authenticator_must_satisfy_protocol(self):
        executor, _ = _executor()
        with pytest.raises(TypeError, match="BybitAuthenticator"):
            BybitPrivateGetRequestSender(
                authenticator=_NotAnAuthenticator(),
                header_builder=BybitHeaderBuilder(),
                request_executor=executor,
            )

    def test_header_builder_must_be_correct_type(self):
        executor, _ = _executor()
        with pytest.raises(TypeError, match="BybitHeaderBuilder"):
            BybitPrivateGetRequestSender(
                authenticator=_SpyAuthenticator(_AUTH),
                header_builder=object(),
                request_executor=executor,
            )

    def test_request_executor_must_be_correct_type(self):
        with pytest.raises(TypeError, match="HttpGetRequestExecutor"):
            BybitPrivateGetRequestSender(
                authenticator=_SpyAuthenticator(_AUTH),
                header_builder=BybitHeaderBuilder(),
                request_executor=object(),
            )


class TestSend:
    def test_url_must_be_str(self):
        sender, _ = _sender()
        with pytest.raises(TypeError, match="url must be str"):
            sender.send(url=1, query_string="")

    def test_url_must_not_be_empty(self):
        sender, _ = _sender()
        with pytest.raises(ValueError, match="url must not be empty"):
            sender.send(url="", query_string="")

    def test_query_string_must_be_str(self):
        sender, _ = _sender()
        with pytest.raises(TypeError, match="query_string must be str"):
            sender.send(url="https://x", query_string=None)

    def test_authenticates_with_query_string_as_body(self):
        authenticator = _SpyAuthenticator(_AUTH)
        sender, _ = _sender(authenticator=authenticator)
        sender.send(url="https://x/y", query_string="category=linear")
        assert authenticator.calls == ["category=linear"]

    def test_empty_query_string_signs_empty_body(self):
        authenticator = _SpyAuthenticator(_AUTH)
        sender, _ = _sender(authenticator=authenticator)
        sender.send(url="https://x/y", query_string="")
        assert authenticator.calls == [""]

    def test_query_string_appended_to_url(self):
        executor, transport = _executor()
        sender, _ = _sender(request_executor=executor)
        sender.send(url="https://x/y", query_string="category=linear&settleCoin=USDT")
        assert transport.calls[0]["url"] == "https://x/y?category=linear&settleCoin=USDT"

    def test_empty_query_string_does_not_append_question_mark(self):
        executor, transport = _executor()
        sender, _ = _sender(request_executor=executor)
        sender.send(url="https://x/y", query_string="")
        assert transport.calls[0]["url"] == "https://x/y"

    def test_headers_come_from_header_builder(self):
        executor, transport = _executor()
        sender, _ = _sender(request_executor=executor)
        sender.send(url="https://x/y", query_string="")
        headers = transport.calls[0]["headers"]
        assert headers["X-BAPI-API-KEY"] == "demo-key"
        assert headers["X-BAPI-SIGN"] == "sig"

    def test_returns_executor_result(self):
        executor, _ = _executor(result="raw-json")
        sender, _ = _sender(request_executor=executor)
        assert sender.send(url="https://x", query_string="") == "raw-json"

    def test_exactly_one_authenticate_call(self):
        authenticator = _SpyAuthenticator(_AUTH)
        sender, _ = _sender(authenticator=authenticator)
        sender.send(url="https://x", query_string="a=b")
        assert len(authenticator.calls) == 1

    def test_exactly_one_transport_call(self):
        executor, transport = _executor()
        sender, _ = _sender(request_executor=executor)
        sender.send(url="https://x", query_string="a=b")
        assert len(transport.calls) == 1


class TestRealSigningIntegration:
    """Reutiliza el pipeline productivo real de autenticación (StandardBybitAuthenticator +
    HmacSha256Signer + BybitHeaderBuilder) y el HttpGetRequestExecutor real, verificando la
    firma HMAC contra un cálculo independiente -- ningún componente de firma se duplica."""

    def _real_sender(self, *, transport, recv_window_ms=5000, now_ms=1_700_000_000_000):
        credentials = BybitDemoCredentials(api_key="demo-key", api_secret="demo-secret")
        authenticator = StandardBybitAuthenticator(
            credentials=credentials,
            clock=_FixedClock(now_ms),
            signer=HmacSha256Signer(),
            recv_window_ms=recv_window_ms,
        )
        executor = HttpGetRequestExecutor(transport=transport, timeout_seconds=10)
        return BybitPrivateGetRequestSender(
            authenticator=authenticator,
            header_builder=BybitHeaderBuilder(),
            request_executor=executor,
        )

    def test_signature_matches_independently_computed_hmac_for_query_string(self):
        transport = _SpyTransport()
        sender = self._real_sender(transport=transport)
        sender.send(
            url="https://api-demo.bybit.com/v5/position/list",
            query_string="category=linear&settleCoin=USDT",
        )

        headers = transport.calls[0]["headers"]
        message = (
            headers["X-BAPI-TIMESTAMP"] + headers["X-BAPI-API-KEY"]
            + headers["X-BAPI-RECV-WINDOW"] + "category=linear&settleCoin=USDT"
        )
        expected = hmac.new(b"demo-secret", message.encode("utf-8"), hashlib.sha256).hexdigest()
        assert headers["X-BAPI-SIGN"] == expected

    def test_different_query_strings_produce_different_signatures(self):
        transport = _SpyTransport()
        sender = self._real_sender(transport=transport)
        sender.send(url="https://x", query_string="category=linear")
        sender.send(url="https://x", query_string="category=inverse")
        sig1 = transport.calls[0]["headers"]["X-BAPI-SIGN"]
        sig2 = transport.calls[1]["headers"]["X-BAPI-SIGN"]
        assert sig1 != sig2

    def test_final_url_reaches_transport_with_query_string(self):
        transport = _SpyTransport()
        sender = self._real_sender(transport=transport)
        sender.send(
            url="https://api-demo.bybit.com/v5/position/list",
            query_string="category=linear&settleCoin=USDT&limit=200",
        )
        assert transport.calls[0]["url"] == (
            "https://api-demo.bybit.com/v5/position/list"
            "?category=linear&settleCoin=USDT&limit=200"
        )

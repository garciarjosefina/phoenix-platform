import os
import pytest
import execution_gateway
from execution_gateway.bybit_private_api import BybitPrivateApi
from execution_gateway.bybit_private_request_sender import BybitPrivateRequestSender
from execution_gateway.bybit_response_parser import BybitResponseParser
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError


# ── helpers ────────────────────────────────────────────────────────────────

def _make_bybit_response(**kwargs) -> BybitResponse:
    defaults = dict(ret_code=0, ret_msg="OK", result={}, ret_ext_info={}, time_ms=1_700_000_000_000)
    return BybitResponse(**{**defaults, **kwargs})


class _SpySender(BybitPrivateRequestSender):
    def __init__(self, result: str = '{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}') -> None:
        self.calls: list[dict] = []
        self._result = result

    def send(self, *, url: str, payload: object) -> str:
        self.calls.append({"url": url, "payload": payload})
        return self._result


class _SpyParser(BybitResponseParser):
    def __init__(self, result: BybitResponse | None = None) -> None:
        self.calls: list[dict] = []
        self._result = result or _make_bybit_response()

    def parse(self, *, response_text: str) -> BybitResponse:
        self.calls.append({"response_text": response_text})
        return self._result


def _make_api(
    sender_result: str = '{"retCode":0}',
    parser_result: BybitResponse | None = None,
) -> tuple[BybitPrivateApi, _SpySender, _SpyParser]:
    s = _SpySender(result=sender_result)
    p = _SpyParser(result=parser_result)
    api = BybitPrivateApi(sender=s, response_parser=p)
    return api, s, p


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_private_api import BybitPrivateApi as A
        assert A is BybitPrivateApi

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitPrivateApi")
        assert execution_gateway.BybitPrivateApi is BybitPrivateApi

    def test_in_all(self):
        assert "BybitPrivateApi" in execution_gateway.__all__


# ── constructor ────────────────────────────────────────────────────────────

class TestConstructor:
    def test_valid_construction(self):
        api, _, _ = _make_api()
        assert api is not None

    def test_stores_sender(self):
        s = _SpySender()
        p = _SpyParser()
        api = BybitPrivateApi(sender=s, response_parser=p)
        assert api._sender is s

    def test_stores_parser(self):
        s = _SpySender()
        p = _SpyParser()
        api = BybitPrivateApi(sender=s, response_parser=p)
        assert api._response_parser is p

    def test_rejects_incompatible_sender(self):
        with pytest.raises(TypeError):
            BybitPrivateApi(sender=object(), response_parser=_SpyParser())

    def test_rejects_none_sender(self):
        with pytest.raises(TypeError):
            BybitPrivateApi(sender=None, response_parser=_SpyParser())

    def test_rejects_incompatible_parser(self):
        with pytest.raises(TypeError):
            BybitPrivateApi(sender=_SpySender(), response_parser=object())

    def test_rejects_none_parser(self):
        with pytest.raises(TypeError):
            BybitPrivateApi(sender=_SpySender(), response_parser=None)

    def test_no_sender_call_during_construction(self):
        s = _SpySender()
        p = _SpyParser()
        BybitPrivateApi(sender=s, response_parser=p)
        assert s.calls == []

    def test_no_parser_call_during_construction(self):
        s = _SpySender()
        p = _SpyParser()
        BybitPrivateApi(sender=s, response_parser=p)
        assert p.calls == []

    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__api_sentinel__"
        try:
            api, _, _ = _make_api()
            assert api is not None
        finally:
            del os.environ["BYBIT_API_KEY"]


# ── url validation ─────────────────────────────────────────────────────────

class TestUrlValidation:
    def test_rejects_non_str_url(self):
        api, _, _ = _make_api()
        with pytest.raises(TypeError):
            api.request(url=123, payload={})

    def test_rejects_none_url(self):
        api, _, _ = _make_api()
        with pytest.raises(TypeError):
            api.request(url=None, payload={})

    def test_rejects_empty_url(self):
        api, _, _ = _make_api()
        with pytest.raises(ValueError):
            api.request(url="", payload={})

    def test_rejects_whitespace_url(self):
        api, _, _ = _make_api()
        with pytest.raises(ValueError):
            api.request(url="   ", payload={})

    def test_accepts_valid_url(self):
        api, _, _ = _make_api()
        result = api.request(url="https://example.com/order", payload={})
        assert isinstance(result, BybitResponse)

    def test_url_internal_spaces_preserved(self):
        api, s, _ = _make_api()
        url = "https://example.com/path with spaces"
        api.request(url=url, payload={})
        assert s.calls[0]["url"] == url


# ── payload ────────────────────────────────────────────────────────────────

class TestPayload:
    def test_accepts_none_payload(self):
        api, _, _ = _make_api()
        result = api.request(url="https://example.com", payload=None)
        assert isinstance(result, BybitResponse)

    def test_accepts_dict_payload(self):
        api, _, _ = _make_api()
        result = api.request(url="https://example.com", payload={"symbol": "BTCUSDT"})
        assert isinstance(result, BybitResponse)

    def test_accepts_list_payload(self):
        api, _, _ = _make_api()
        result = api.request(url="https://example.com", payload=[1, 2, 3])
        assert isinstance(result, BybitResponse)

    def test_accepts_str_payload(self):
        api, _, _ = _make_api()
        result = api.request(url="https://example.com", payload="raw")
        assert isinstance(result, BybitResponse)

    def test_payload_transmitted_by_identity(self):
        api, s, _ = _make_api()
        payload = {"key": "value", "nested": [1, 2]}
        api.request(url="https://example.com", payload=payload)
        assert s.calls[0]["payload"] is payload


# ── order and composition ──────────────────────────────────────────────────

class TestOrderAndComposition:
    def _make_ordered(self):
        log: list[str] = []
        sentinel_response = _make_bybit_response(ret_code=0)
        sentinel_text = "sentinel_response_text"

        class _OrdSender(BybitPrivateRequestSender):
            def __init__(self):
                self.calls = []
            def send(self, *, url, payload):
                log.append("send")
                self.calls.append({"url": url, "payload": payload})
                return sentinel_text

        class _OrdParser(BybitResponseParser):
            def __init__(self):
                self.calls = []
            def parse(self, *, response_text):
                log.append("parse")
                self.calls.append({"response_text": response_text})
                return sentinel_response

        s = _OrdSender()
        p = _OrdParser()
        api = BybitPrivateApi(sender=s, response_parser=p)
        return api, s, p, log, sentinel_text, sentinel_response

    def test_sender_called_before_parser(self):
        api, _, _, log, _, _ = self._make_ordered()
        api.request(url="https://example.com", payload={})
        assert log.index("send") < log.index("parse")

    def test_full_sequence(self):
        api, _, _, log, _, _ = self._make_ordered()
        api.request(url="https://example.com", payload={})
        assert log == ["send", "parse"]

    def test_sender_called_exactly_once(self):
        api, s, _, _, _, _ = self._make_ordered()
        api.request(url="https://example.com", payload={})
        assert len(s.calls) == 1

    def test_parser_called_exactly_once(self):
        api, _, p, _, _, _ = self._make_ordered()
        api.request(url="https://example.com", payload={})
        assert len(p.calls) == 1

    def test_url_transmitted_to_sender(self):
        url = "https://api.example.com/v5/order/create"
        api, s, _, _, _, _ = self._make_ordered()
        api.request(url=url, payload={})
        assert s.calls[0]["url"] == url

    def test_payload_transmitted_to_sender(self):
        payload = {"qty": "0.001"}
        api, s, _, _, _, _ = self._make_ordered()
        api.request(url="https://example.com", payload=payload)
        assert s.calls[0]["payload"] is payload

    def test_response_text_passed_to_parser(self):
        api, _, p, _, sentinel_text, _ = self._make_ordered()
        api.request(url="https://example.com", payload={})
        assert p.calls[0]["response_text"] is sentinel_text

    def test_bybit_response_returned_by_identity(self):
        api, _, _, _, _, sentinel_response = self._make_ordered()
        result = api.request(url="https://example.com", payload={})
        assert result is sentinel_response

    def test_no_ret_code_interpretation(self):
        api, _, _ = _make_api(parser_result=_make_bybit_response(ret_code=10001))
        result = api.request(url="https://example.com", payload={})
        assert result.ret_code == 10001


# ── multiple calls ─────────────────────────────────────────────────────────

class TestMultipleCalls:
    def test_each_call_invokes_sender(self):
        api, s, _ = _make_api()
        api.request(url="https://example.com", payload={})
        api.request(url="https://example.com", payload={})
        assert len(s.calls) == 2

    def test_each_call_invokes_parser(self):
        api, _, p = _make_api()
        api.request(url="https://example.com", payload={})
        api.request(url="https://example.com", payload={})
        assert len(p.calls) == 2

    def test_no_text_reuse(self):
        texts = ["text_one", "text_two"]
        idx = [0]

        class _RotatingSender(BybitPrivateRequestSender):
            def __init__(self): pass
            def send(self, *, url, payload):
                t = texts[idx[0]]
                idx[0] += 1
                return t

        p = _SpyParser()
        api = BybitPrivateApi(sender=_RotatingSender(), response_parser=p)
        api.request(url="https://example.com", payload={})
        api.request(url="https://example.com", payload={})
        assert p.calls[0]["response_text"] == "text_one"
        assert p.calls[1]["response_text"] == "text_two"

    def test_order_preserved_each_call(self):
        log: list[str] = []

        class _LogSender(BybitPrivateRequestSender):
            def __init__(self): pass
            def send(self, *, url, payload):
                log.append("send")
                return "text"

        class _LogParser(BybitResponseParser):
            def __init__(self): pass
            def parse(self, *, response_text):
                log.append("parse")
                return _make_bybit_response()

        api = BybitPrivateApi(sender=_LogSender(), response_parser=_LogParser())
        api.request(url="https://example.com", payload={})
        api.request(url="https://example.com", payload={})
        assert log == ["send", "parse", "send", "parse"]


# ── error propagation ──────────────────────────────────────────────────────

class TestErrorPropagation:
    def test_propagates_sender_error(self):
        class _FailSender(BybitPrivateRequestSender):
            def __init__(self): pass
            def send(self, *, url, payload):
                raise RuntimeError("sender fail")

        api = BybitPrivateApi(sender=_FailSender(), response_parser=_SpyParser())
        with pytest.raises(RuntimeError, match="sender fail"):
            api.request(url="https://example.com", payload={})

    def test_parser_not_called_when_sender_fails(self):
        class _FailSender(BybitPrivateRequestSender):
            def __init__(self): pass
            def send(self, *, url, payload):
                raise RuntimeError("sender fail")

        p = _SpyParser()
        api = BybitPrivateApi(sender=_FailSender(), response_parser=p)
        with pytest.raises(RuntimeError):
            api.request(url="https://example.com", payload={})
        assert p.calls == []

    def test_propagates_parser_error(self):
        class _FailParser(BybitResponseParser):
            def __init__(self): pass
            def parse(self, *, response_text):
                raise TypeError("parse fail")

        api = BybitPrivateApi(sender=_SpySender(), response_parser=_FailParser())
        with pytest.raises(TypeError, match="parse fail"):
            api.request(url="https://example.com", payload={})

    def test_no_retry_on_parser_error(self):
        call_count = []

        class _FailParser(BybitResponseParser):
            def __init__(self): pass
            def parse(self, *, response_text):
                call_count.append(1)
                raise OSError("fail")

        api = BybitPrivateApi(sender=_SpySender(), response_parser=_FailParser())
        with pytest.raises(OSError):
            api.request(url="https://example.com", payload={})
        assert len(call_count) == 1

    def test_exception_not_transformed(self):
        class _FailSender(BybitPrivateRequestSender):
            def __init__(self): pass
            def send(self, *, url, payload):
                raise ValueError("original error")

        api = BybitPrivateApi(sender=_FailSender(), response_parser=_SpyParser())
        with pytest.raises(ValueError, match="original error"):
            api.request(url="https://example.com", payload={})


# ── no state ───────────────────────────────────────────────────────────────

class TestNoState:
    def test_no_last_url_attr(self):
        api, _, _ = _make_api()
        api.request(url="https://example.com", payload={})
        assert not hasattr(api, "last_url")

    def test_no_last_payload_attr(self):
        api, _, _ = _make_api()
        api.request(url="https://example.com", payload={})
        assert not hasattr(api, "last_payload")

    def test_no_last_text_attr(self):
        api, _, _ = _make_api()
        api.request(url="https://example.com", payload={})
        assert not hasattr(api, "last_text")

    def test_no_last_response_attr(self):
        api, _, _ = _make_api()
        api.request(url="https://example.com", payload={})
        assert not hasattr(api, "last_response")


# ── no extra responsibilities ──────────────────────────────────────────────

class TestNoExtraResponsibilities:
    def test_no_transport_imported(self):
        import execution_gateway.bybit_private_api as m
        assert not hasattr(m, "HttpTransport")
        assert not hasattr(m, "UrllibHttpTransport")

    def test_no_authenticator_imported(self):
        import execution_gateway.bybit_private_api as m
        assert not hasattr(m, "BybitAuthenticator")
        assert not hasattr(m, "StandardBybitAuthenticator")

    def test_no_serializer_imported(self):
        import execution_gateway.bybit_private_api as m
        assert not hasattr(m, "JsonSerializer")
        assert not hasattr(m, "StandardJsonSerializer")

    def test_no_hardcoded_endpoints(self):
        import inspect
        import execution_gateway.bybit_private_api as m
        src = inspect.getsource(m)
        assert "bybit.com" not in src
        assert "/v5/" not in src

    def test_no_real_http(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        api, _, _ = _make_api()
        api.request(url="https://example.com", payload={})
        assert called == []

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.bybit_response import BybitResponse
        assert GatewayConfig().environment == "demo"
        r = BybitResponse(ret_code=0, ret_msg="OK", result={}, ret_ext_info={}, time_ms=1000)
        assert r.ret_code == 0


# ---------------------------------------------------------------------------
# Traducción de fallos de decodificación remota (corrección final Auditoría A)
#
# BybitPrivateApi es la frontera entre el transporte HTTP genérico (que
# puede lanzar UnicodeDecodeError al decodificar un body no-UTF8) y el
# procesamiento específico de Bybit. Es el único componente que sabe que un
# UnicodeDecodeError en este punto proviene de una respuesta remota.
# ---------------------------------------------------------------------------

class _UnicodeFailingSender(BybitPrivateRequestSender):
    def __init__(self, error: UnicodeDecodeError) -> None:
        self._error = error
        self.call_count = 0

    def send(self, *, url: str, payload: object) -> str:
        self.call_count += 1
        raise self._error


def _make_unicode_decode_error() -> UnicodeDecodeError:
    return UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 1, "invalid start byte")


class TestUnicodeDecodeErrorTranslation:
    def test_translated_to_bybit_response_processing_error(self):
        sender = _UnicodeFailingSender(_make_unicode_decode_error())
        api = BybitPrivateApi(sender=sender, response_parser=_SpyParser())
        with pytest.raises(BybitResponseProcessingError):
            api.request(url="https://example.com", payload={})

    def test_original_exception_conserved_as_cause(self):
        original = _make_unicode_decode_error()
        sender = _UnicodeFailingSender(original)
        api = BybitPrivateApi(sender=sender, response_parser=_SpyParser())
        with pytest.raises(BybitResponseProcessingError) as exc_info:
            api.request(url="https://example.com", payload={})
        assert exc_info.value.__cause__ is original

    def test_message_is_safe_constant_not_str_of_original_error(self):
        # El detalle técnico del UnicodeDecodeError (incluidos los bytes
        # crudos del body remoto) nunca debe copiarse al mensaje público.
        original = _make_unicode_decode_error()
        sender = _UnicodeFailingSender(original)
        api = BybitPrivateApi(sender=sender, response_parser=_SpyParser())
        with pytest.raises(BybitResponseProcessingError) as exc_info:
            api.request(url="https://example.com", payload={})
        assert str(exc_info.value) == "Bybit response could not be processed"
        assert str(exc_info.value) != str(original)
        assert "invalid start byte" not in str(exc_info.value)
        assert "\\xff" not in str(exc_info.value)

    def test_parser_not_called_when_sender_fails(self):
        sender = _UnicodeFailingSender(_make_unicode_decode_error())
        parser = _SpyParser()
        api = BybitPrivateApi(sender=sender, response_parser=parser)
        with pytest.raises(BybitResponseProcessingError):
            api.request(url="https://example.com", payload={})
        assert parser.calls == []

    def test_sender_called_exactly_once(self):
        sender = _UnicodeFailingSender(_make_unicode_decode_error())
        api = BybitPrivateApi(sender=sender, response_parser=_SpyParser())
        with pytest.raises(BybitResponseProcessingError):
            api.request(url="https://example.com", payload={})
        assert sender.call_count == 1

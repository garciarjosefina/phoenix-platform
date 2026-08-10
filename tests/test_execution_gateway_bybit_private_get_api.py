import json

import pytest

import execution_gateway
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_private_get_request_sender import BybitPrivateGetRequestSender
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_parser import BybitResponseParser
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.json_serializer_factory import create_json_serializer


def _ok_body(ret_code=0, ret_msg="OK", result=None, time_ms=1_700_000_000_000):
    return json.dumps({
        "retCode": ret_code, "retMsg": ret_msg,
        "result": result if result is not None else {"list": []},
        "retExtInfo": {}, "time": time_ms,
    })


class _SpySender(BybitPrivateGetRequestSender):
    def __init__(self, *, result: str = None, exc: Exception = None) -> None:
        self.calls: list[dict] = []
        self._result = result if result is not None else _ok_body()
        self._exc = exc

    def send(self, *, url: str, query_string: str) -> str:
        self.calls.append({"url": url, "query_string": query_string})
        if self._exc is not None:
            raise self._exc
        return self._result


def _api(*, sender=None, response_parser=None):
    return BybitPrivateGetApi(
        sender=sender or _SpySender(),
        response_parser=response_parser or BybitResponseParser(create_json_serializer()),
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitPrivateGetApi")
        assert execution_gateway.BybitPrivateGetApi is BybitPrivateGetApi

    def test_in_all(self):
        assert "BybitPrivateGetApi" in execution_gateway.__all__


class TestConstruction:
    def test_sender_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitPrivateGetRequestSender"):
            BybitPrivateGetApi(
                sender=object(),
                response_parser=BybitResponseParser(create_json_serializer()),
            )

    def test_response_parser_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitResponseParser"):
            BybitPrivateGetApi(sender=_SpySender(), response_parser=object())


class TestRequest:
    def test_url_must_be_str(self):
        api = _api()
        with pytest.raises(TypeError, match="url must be str"):
            api.request(url=1, query_string="")

    def test_url_must_not_be_empty(self):
        api = _api()
        with pytest.raises(ValueError, match="url must not be empty"):
            api.request(url="", query_string="")

    def test_query_string_must_be_str(self):
        api = _api()
        with pytest.raises(TypeError, match="query_string must be str"):
            api.request(url="https://x", query_string=None)

    def test_delegates_url_and_query_string_to_sender(self):
        sender = _SpySender()
        api = _api(sender=sender)
        api.request(url="https://x/y", query_string="category=linear")
        assert sender.calls == [{"url": "https://x/y", "query_string": "category=linear"}]

    def test_returns_bybit_response(self):
        api = _api(sender=_SpySender(result=_ok_body(ret_code=0)))
        response = api.request(url="https://x", query_string="")
        assert isinstance(response, BybitResponse)
        assert response.ret_code == 0

    def test_parses_result_payload(self):
        payload = {"category": "linear", "list": [{"symbol": "BTCUSDT"}]}
        api = _api(sender=_SpySender(result=_ok_body(result=payload)))
        response = api.request(url="https://x", query_string="")
        assert response.result["list"][0]["symbol"] == "BTCUSDT"

    def test_unicode_decode_error_translated_to_processing_error(self):
        exc = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")
        api = _api(sender=_SpySender(exc=exc))
        with pytest.raises(BybitResponseProcessingError):
            api.request(url="https://x", query_string="")

    def test_malformed_json_translated_to_processing_error(self):
        api = _api(sender=_SpySender(result="{not json"))
        with pytest.raises(BybitResponseProcessingError):
            api.request(url="https://x", query_string="")

    def test_other_sender_errors_propagate_unwrapped(self):
        api = _api(sender=_SpySender(exc=OSError("network down")))
        with pytest.raises(OSError, match="network down"):
            api.request(url="https://x", query_string="")

    def test_exactly_one_send_call(self):
        sender = _SpySender()
        api = _api(sender=sender)
        api.request(url="https://x", query_string="a=b")
        assert len(sender.calls) == 1

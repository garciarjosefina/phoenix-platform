import pytest

import execution_gateway
from execution_gateway.bybit_public_get_api import BybitPublicGetApi
from execution_gateway.bybit_public_get_request_sender import BybitPublicGetRequestSender
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_parser import BybitResponseParser
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.standard_json_serializer import StandardJsonSerializer


class _SpySender(BybitPublicGetRequestSender):
    def __init__(self, *, result="", exc=None):
        self.calls = []
        self._result = result
        self._exc = exc

    def send(self, *, url, query_string):
        self.calls.append(dict(url=url, query_string=query_string))
        if self._exc is not None:
            raise self._exc
        return self._result


def _api(*, sender=None, response_parser=None):
    return BybitPublicGetApi(
        sender=sender or _SpySender(),
        response_parser=response_parser or BybitResponseParser(serializer=StandardJsonSerializer()),
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitPublicGetApi")
        assert execution_gateway.BybitPublicGetApi is BybitPublicGetApi

    def test_in_all(self):
        assert "BybitPublicGetApi" in execution_gateway.__all__


class TestConstruction:
    def test_sender_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitPublicGetRequestSender"):
            BybitPublicGetApi(
                sender=object(),
                response_parser=BybitResponseParser(serializer=StandardJsonSerializer()),
            )

    def test_response_parser_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitResponseParser"):
            BybitPublicGetApi(sender=_SpySender(), response_parser=object())


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

    def test_sender_receives_url_and_query_string(self):
        sender = _SpySender(result='{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1}')
        api = _api(sender=sender)
        api.request(url="https://x", query_string="category=linear&symbol=BTCUSDT")
        assert sender.calls[0] == {"url": "https://x", "query_string": "category=linear&symbol=BTCUSDT"}

    def test_returns_parsed_bybit_response(self):
        sender = _SpySender(
            result='{"retCode":0,"retMsg":"OK","result":{"list":[]},"retExtInfo":{},"time":123}'
        )
        api = _api(sender=sender)
        response = api.request(url="https://x", query_string="")
        assert isinstance(response, BybitResponse)
        assert response.ret_code == 0
        assert response.time_ms == 123

    def test_unicode_decode_error_translated(self):
        sender = _SpySender(exc=UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid"))
        api = _api(sender=sender)
        with pytest.raises(BybitResponseProcessingError):
            api.request(url="https://x", query_string="")

    def test_malformed_json_translated(self):
        sender = _SpySender(result="{not json")
        api = _api(sender=sender)
        with pytest.raises(BybitResponseProcessingError):
            api.request(url="https://x", query_string="")

    def test_exactly_one_sender_call(self):
        sender = _SpySender(result='{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1}')
        api = _api(sender=sender)
        api.request(url="https://x", query_string="")
        assert len(sender.calls) == 1

    def test_reuses_same_response_parser_type_as_private_api(self):
        # Confirma que BybitResponseParser (mismo tipo que
        # BybitPrivateGetApi) se reutiliza sin duplicar -- no hay un
        # segundo parser "público" separado.
        import inspect
        import execution_gateway.bybit_public_get_api as public_module
        import execution_gateway.bybit_private_get_api as private_module
        public_src = inspect.getsource(public_module)
        private_src = inspect.getsource(private_module)
        assert "BybitResponseParser" in public_src
        assert "BybitResponseParser" in private_src

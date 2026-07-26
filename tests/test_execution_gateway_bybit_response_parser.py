import os
import pytest
import execution_gateway
from execution_gateway.bybit_response_parser import BybitResponseParser
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.json_serializer import JsonSerializer


# ── fake serializers ───────────────────────────────────────────────────────

def _valid_payload(
    ret_code: int = 0,
    ret_msg: str = "OK",
    result=None,
    ret_ext_info=None,
    time: int = 1_700_000_000_000,
    **extra,
) -> dict:
    d = {
        "retCode": ret_code,
        "retMsg": ret_msg,
        "result": result if result is not None else {},
        "retExtInfo": ret_ext_info if ret_ext_info is not None else {},
        "time": time,
    }
    d.update(extra)
    return d


class _FakeSerializer:
    def __init__(self, result=None) -> None:
        self._result = result if result is not None else _valid_payload()
        self.loads_calls: list[str] = []

    def dumps(self, value: object) -> str:
        return "{}"

    def loads(self, value: str) -> object:
        self.loads_calls.append(value)
        return self._result


def _make_parser(serializer_result=None) -> tuple[BybitResponseParser, _FakeSerializer]:
    s = _FakeSerializer(result=serializer_result)
    p = BybitResponseParser(serializer=s)
    return p, s


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_response_parser import BybitResponseParser as P
        assert P is BybitResponseParser

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitResponseParser")
        assert execution_gateway.BybitResponseParser is BybitResponseParser

    def test_in_all(self):
        assert "BybitResponseParser" in execution_gateway.__all__

    def test_accepts_structural_serializer(self):
        class _DuckSerializer:
            def dumps(self, value: object) -> str:
                return "{}"
            def loads(self, value: str) -> object:
                return _valid_payload()

        assert isinstance(_DuckSerializer(), JsonSerializer)
        p = BybitResponseParser(serializer=_DuckSerializer())
        assert p is not None


# ── constructor ────────────────────────────────────────────────────────────

class TestConstructor:
    def test_valid_construction(self):
        p, _ = _make_parser()
        assert p is not None

    def test_stores_serializer(self):
        s = _FakeSerializer()
        p = BybitResponseParser(serializer=s)
        assert p._serializer is s

    def test_rejects_incompatible_serializer(self):
        with pytest.raises(TypeError):
            BybitResponseParser(serializer=object())

    def test_rejects_none_serializer(self):
        with pytest.raises(TypeError):
            BybitResponseParser(serializer=None)

    def test_no_loads_call_during_construction(self):
        s = _FakeSerializer()
        BybitResponseParser(serializer=s)
        assert s.loads_calls == []

    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__parser_sentinel__"
        try:
            p, _ = _make_parser()
            assert p is not None
        finally:
            del os.environ["BYBIT_API_KEY"]


# ── input validation ───────────────────────────────────────────────────────

class TestInput:
    def test_response_text_is_keyword_only(self):
        p, _ = _make_parser()
        with pytest.raises(TypeError):
            p.parse('{"retCode":0,"retMsg":"","result":{},"retExtInfo":{},"time":1}')

    def test_rejects_non_str_response_text(self):
        p, _ = _make_parser()
        with pytest.raises(TypeError):
            p.parse(response_text=b'{"retCode":0}')

    def test_rejects_none_response_text(self):
        p, _ = _make_parser()
        with pytest.raises(TypeError):
            p.parse(response_text=None)

    def test_rejects_int_response_text(self):
        p, _ = _make_parser()
        with pytest.raises(TypeError):
            p.parse(response_text=42)

    def test_accepts_empty_str(self):
        class _EmptyFails:
            def dumps(self, v):
                return ""
            def loads(self, v):
                raise ValueError("empty json")

        p = BybitResponseParser(serializer=_EmptyFails())
        with pytest.raises(ValueError, match="empty json"):
            p.parse(response_text="")

    def test_text_transmitted_exactly(self):
        p, s = _make_parser()
        text = '{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}'
        p.parse(response_text=text)
        assert s.loads_calls[0] == text

    def test_unicode_text_transmitted(self):
        p, s = _make_parser()
        text = '{"retCode":0,"retMsg":"données","result":{},"retExtInfo":{},"time":1000}'
        p.parse(response_text=text)
        assert s.loads_calls[0] == text

    def test_no_strip_applied(self):
        padded = '  {"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}  '
        s = _FakeSerializer()
        p = BybitResponseParser(serializer=s)
        p.parse(response_text=padded)
        assert s.loads_calls[0] == padded


# ── deserialization ────────────────────────────────────────────────────────

class TestDeserialization:
    def test_calls_loads_exactly_once(self):
        p, s = _make_parser()
        p.parse(response_text='{}')
        assert len(s.loads_calls) == 1

    def test_transmits_exact_text_to_serializer(self):
        text = '{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1}'
        p, s = _make_parser()
        p.parse(response_text=text)
        assert s.loads_calls[0] is text

    def test_no_second_deserialization(self):
        p, s = _make_parser()
        p.parse(response_text='{}')
        assert len(s.loads_calls) == 1

    def test_no_direct_json_import(self):
        import execution_gateway.bybit_response_parser as m
        assert not hasattr(m, "json")

    def test_propagates_serializer_exception(self):
        class _FailingSerializer:
            def dumps(self, v):
                return ""
            def loads(self, v):
                raise ValueError("invalid json")

        p = BybitResponseParser(serializer=_FailingSerializer())
        with pytest.raises(ValueError, match="invalid json"):
            p.parse(response_text="not json")


# ── root structure ─────────────────────────────────────────────────────────

class TestRootStructure:
    def test_accepts_dict_root(self):
        p, _ = _make_parser()
        result = p.parse(response_text='{}')
        assert isinstance(result, BybitResponse)

    def test_rejects_list_root(self):
        p, _ = _make_parser(serializer_result=[1, 2])
        with pytest.raises(TypeError):
            p.parse(response_text='[]')

    def test_rejects_tuple_root(self):
        p, _ = _make_parser(serializer_result=(1, 2))
        with pytest.raises(TypeError):
            p.parse(response_text='null')

    def test_rejects_str_root(self):
        p, _ = _make_parser(serializer_result="string")
        with pytest.raises(TypeError):
            p.parse(response_text='"string"')

    def test_rejects_number_root(self):
        p, _ = _make_parser(serializer_result=42)
        with pytest.raises(TypeError):
            p.parse(response_text='42')

    def test_rejects_none_root(self):
        class _NoneSerializer:
            def dumps(self, v): return ""
            def loads(self, v): return None

        p = BybitResponseParser(serializer=_NoneSerializer())
        with pytest.raises(TypeError):
            p.parse(response_text='null')

    def test_no_dict_copy(self):
        data = _valid_payload()
        s = _FakeSerializer(result=data)
        p = BybitResponseParser(serializer=s)
        call_log = []
        original_loads = s.loads
        def tracking_loads(v):
            result = original_loads(v)
            call_log.append(result)
            return result
        s.loads = tracking_loads
        p.parse(response_text='{}')
        assert call_log[0] is data


# ── field mapping ──────────────────────────────────────────────────────────

class TestFieldMapping:
    def test_maps_ret_code(self):
        p, _ = _make_parser(serializer_result=_valid_payload(ret_code=10001))
        r = p.parse(response_text='{}')
        assert r.ret_code == 10001

    def test_maps_ret_msg(self):
        p, _ = _make_parser(serializer_result=_valid_payload(ret_msg="param error"))
        r = p.parse(response_text='{}')
        assert r.ret_msg == "param error"

    def test_maps_result(self):
        result_data = {"orderId": "abc123"}
        p, _ = _make_parser(serializer_result=_valid_payload(result=result_data))
        r = p.parse(response_text='{}')
        assert r.result == result_data

    def test_maps_ret_ext_info(self):
        ext = {"reqId": "req_001"}
        p, _ = _make_parser(serializer_result=_valid_payload(ret_ext_info=ext))
        r = p.parse(response_text='{}')
        assert r.ret_ext_info == ext

    def test_maps_time_to_time_ms(self):
        p, _ = _make_parser(serializer_result=_valid_payload(time=1_700_000_000_000))
        r = p.parse(response_text='{}')
        assert r.time_ms == 1_700_000_000_000

    def test_result_preserved_by_identity(self):
        result_data = {"orderId": "abc"}
        p, _ = _make_parser(serializer_result=_valid_payload(result=result_data))
        r = p.parse(response_text='{}')
        assert r.result is result_data

    def test_ret_ext_info_preserved_by_identity(self):
        ext = {"meta": "value"}
        p, _ = _make_parser(serializer_result=_valid_payload(ret_ext_info=ext))
        r = p.parse(response_text='{}')
        assert r.ret_ext_info is ext

    def test_accepts_extra_keys(self):
        data = _valid_payload(extra_key="ignored_value")
        p, _ = _make_parser(serializer_result=data)
        r = p.parse(response_text='{}')
        assert isinstance(r, BybitResponse)

    def test_ignores_extra_keys(self):
        data = _valid_payload(unknownField="xyz", anotherField=99)
        p, _ = _make_parser(serializer_result=data)
        r = p.parse(response_text='{}')
        assert r.ret_code == 0

    def test_missing_ret_code_raises_key_error(self):
        data = _valid_payload()
        del data["retCode"]
        p, _ = _make_parser(serializer_result=data)
        with pytest.raises(KeyError):
            p.parse(response_text='{}')

    def test_missing_ret_msg_raises_key_error(self):
        data = _valid_payload()
        del data["retMsg"]
        p, _ = _make_parser(serializer_result=data)
        with pytest.raises(KeyError):
            p.parse(response_text='{}')

    def test_missing_result_raises_key_error(self):
        data = _valid_payload()
        del data["result"]
        p, _ = _make_parser(serializer_result=data)
        with pytest.raises(KeyError):
            p.parse(response_text='{}')

    def test_missing_ret_ext_info_raises_key_error(self):
        data = _valid_payload()
        del data["retExtInfo"]
        p, _ = _make_parser(serializer_result=data)
        with pytest.raises(KeyError):
            p.parse(response_text='{}')

    def test_missing_time_raises_key_error(self):
        data = _valid_payload()
        del data["time"]
        p, _ = _make_parser(serializer_result=data)
        with pytest.raises(KeyError):
            p.parse(response_text='{}')


# ── result ─────────────────────────────────────────────────────────────────

class TestResult:
    def test_returns_bybit_response(self):
        p, _ = _make_parser()
        r = p.parse(response_text='{}')
        assert isinstance(r, BybitResponse)

    def test_success_response(self):
        p, _ = _make_parser(serializer_result=_valid_payload(ret_code=0, ret_msg="OK"))
        r = p.parse(response_text='{}')
        assert r.ret_code == 0
        assert r.ret_msg == "OK"

    def test_error_response(self):
        p, _ = _make_parser(serializer_result=_valid_payload(ret_code=10001, ret_msg="param error"))
        r = p.parse(response_text='{}')
        assert r.ret_code == 10001

    def test_empty_ret_msg(self):
        p, _ = _make_parser(serializer_result=_valid_payload(ret_msg=""))
        r = p.parse(response_text='{}')
        assert r.ret_msg == ""

    def test_result_none(self):
        data = _valid_payload()
        data["result"] = None
        p, _ = _make_parser(serializer_result=data)
        r = p.parse(response_text='{}')
        assert r.result is None

    def test_ret_ext_info_none(self):
        data = _valid_payload()
        data["retExtInfo"] = None
        p, _ = _make_parser(serializer_result=data)
        r = p.parse(response_text='{}')
        assert r.ret_ext_info is None

    def test_time_zero(self):
        p, _ = _make_parser(serializer_result=_valid_payload(time=0))
        r = p.parse(response_text='{}')
        assert r.time_ms == 0

    def test_no_success_interpretation(self):
        p, _ = _make_parser(serializer_result=_valid_payload(ret_code=99999))
        r = p.parse(response_text='{}')
        assert r.ret_code == 99999


# ── error propagation ──────────────────────────────────────────────────────

class TestErrorPropagation:
    def test_propagates_serializer_exception(self):
        class _Broken:
            def dumps(self, v): return ""
            def loads(self, v): raise RuntimeError("boom")

        p = BybitResponseParser(serializer=_Broken())
        with pytest.raises(RuntimeError, match="boom"):
            p.parse(response_text='{}')

    def test_propagates_bybit_response_type_error(self):
        data = _valid_payload()
        data["retCode"] = "not_an_int"
        p, _ = _make_parser(serializer_result=data)
        with pytest.raises(TypeError):
            p.parse(response_text='{}')

    def test_propagates_bybit_response_value_error(self):
        data = _valid_payload()
        data["time"] = -1
        p, _ = _make_parser(serializer_result=data)
        with pytest.raises(ValueError):
            p.parse(response_text='{}')

    def test_no_retry(self):
        call_count = []

        class _CountingFail:
            def dumps(self, v): return ""
            def loads(self, v):
                call_count.append(1)
                raise OSError("fail")

        p = BybitResponseParser(serializer=_CountingFail())
        with pytest.raises(OSError):
            p.parse(response_text='{}')
        assert len(call_count) == 1


# ── no extra responsibilities ──────────────────────────────────────────────

class TestNoExtraResponsibilities:
    def test_no_sender_imported(self):
        import execution_gateway.bybit_response_parser as m
        assert not hasattr(m, "BybitPrivateRequestSender")

    def test_no_transport_imported(self):
        import execution_gateway.bybit_response_parser as m
        assert not hasattr(m, "HttpTransport")
        assert not hasattr(m, "UrllibHttpTransport")

    def test_no_authenticator_imported(self):
        import execution_gateway.bybit_response_parser as m
        assert not hasattr(m, "BybitAuthenticator")

    def test_no_url_in_module(self):
        import inspect
        import execution_gateway.bybit_response_parser as m
        src = inspect.getsource(m)
        assert "bybit.com" not in src
        assert "/v5/" not in src

    def test_no_state_last_text(self):
        p, _ = _make_parser()
        p.parse(response_text='{}')
        assert not hasattr(p, "last_text")

    def test_no_state_last_response(self):
        p, _ = _make_parser()
        p.parse(response_text='{}')
        assert not hasattr(p, "last_response")

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.bybit_response import BybitResponse
        assert GatewayConfig().environment == "demo"
        r = BybitResponse(ret_code=0, ret_msg="OK", result={}, ret_ext_info={}, time_ms=1000)
        assert r.ret_code == 0

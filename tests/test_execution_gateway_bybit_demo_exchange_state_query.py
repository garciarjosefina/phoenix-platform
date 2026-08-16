import inspect
import json
import urllib.error
import urllib.request

import pytest

import execution_gateway
import execution_gateway.bybit_demo_exchange_state_query as _module
from execution_gateway import (
    EnvironmentConfigurationError,
    ExchangeStateSnapshot,
    query_bybit_demo_exchange_state,
)
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError

_VALID_ENV = {
    "PHOENIX_BYBIT_DEMO_API_KEY": "demo-key",
    "PHOENIX_BYBIT_DEMO_API_SECRET": "demo-secret",
    "PHOENIX_BYBIT_RECV_WINDOW_MS": "5000",
    "PHOENIX_HTTP_TIMEOUT_SECONDS": "10",
}


def _env(**overrides):
    d = dict(_VALID_ENV)
    d.update(overrides)
    return d


def _envelope(result, time_ms=1_700_000_000_000, ret_code=0, ret_msg="OK"):
    return json.dumps({
        "retCode": ret_code, "retMsg": ret_msg, "result": result,
        "retExtInfo": {}, "time": time_ms,
    }).encode()


def _positions_body(time_ms=1000):
    return _envelope({"category": "linear", "list": (), "nextPageCursor": ""}, time_ms=time_ms)


def _open_orders_body(time_ms=1000):
    return _envelope({"category": "linear", "list": (), "nextPageCursor": ""}, time_ms=time_ms)


def _wallet_balance_body(time_ms=1000):
    account_item = {
        "accountType": "UNIFIED", "totalEquity": "1", "totalWalletBalance": "1",
        "totalAvailableBalance": "1", "totalInitialMargin": "0", "totalMaintenanceMargin": "0",
        "coin": [],
    }
    return _envelope({"list": (account_item,)}, time_ms=time_ms)


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _install_sequenced_urlopen(monkeypatch, *, bodies=None, exc_on_call=None, capture=None):
    """Responde en el orden real de llamadas -- positions, open_orders,
    wallet_balance (orden fijo del agregador). `exc_on_call` es un índice
    1-based: si se especifica, esa llamada lanza `exc_on_call[1]` en vez de
    devolver un body."""
    state = {"n": 0}

    def fake(req, timeout=None):
        state["n"] += 1
        if capture is not None:
            capture.append(dict(
                n=state["n"], method=req.get_method(), url=req.full_url,
                headers={k: v for k, v in req.header_items()}, data=req.data, timeout=timeout,
            ))
        if exc_on_call is not None and state["n"] == exc_on_call[0]:
            raise exc_on_call[1]
        body = bodies[state["n"] - 1] if bodies is not None else _envelope({"list": ()})
        return _FakeResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return state


def _default_bodies(*, positions_time=1000, orders_time=1000, wallet_time=1000):
    return [
        _positions_body(positions_time),
        _open_orders_body(orders_time),
        _wallet_balance_body(wallet_time),
    ]


def _raised(fn):
    try:
        fn()
        return None
    except Exception as e:
        return e


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_demo_exchange_state_query import (
            query_bybit_demo_exchange_state as f,
        )
        assert f is query_bybit_demo_exchange_state

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "query_bybit_demo_exchange_state")
        assert execution_gateway.query_bybit_demo_exchange_state is query_bybit_demo_exchange_state

    def test_in_all(self):
        assert "query_bybit_demo_exchange_state" in execution_gateway.__all__

    def test_callable(self):
        assert callable(query_bybit_demo_exchange_state)


class TestSignature:
    def test_exactly_one_parameter(self):
        sig = inspect.signature(query_bybit_demo_exchange_state)
        assert len(sig.parameters) == 1

    def test_parameter_named_environ(self):
        sig = inspect.signature(query_bybit_demo_exchange_state)
        assert "environ" in sig.parameters

    def test_parameter_is_keyword_only(self):
        sig = inspect.signature(query_bybit_demo_exchange_state)
        assert sig.parameters["environ"].kind == inspect.Parameter.KEYWORD_ONLY

    def test_parameter_defaults_to_none(self):
        sig = inspect.signature(query_bybit_demo_exchange_state)
        assert sig.parameters["environ"].default is None

    def test_no_symbol_parameter(self):
        # Account-wide -- a diferencia de query_bybit_demo_instrument_metadata.
        sig = inspect.signature(query_bybit_demo_exchange_state)
        assert "symbol" not in sig.parameters

    def test_return_annotation_is_exchange_state_snapshot(self):
        hints = inspect.get_annotations(query_bybit_demo_exchange_state, eval_str=True)
        assert hints.get("return") is ExchangeStateSnapshot

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            query_bybit_demo_exchange_state(_VALID_ENV)


# ---------------------------------------------------------------------------
# 2. Éxito
# ---------------------------------------------------------------------------

class TestSuccess:
    def test_returns_exchange_state_snapshot(self, monkeypatch):
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies())
        result = query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert isinstance(result, ExchangeStateSnapshot)

    def test_observation_window_computed_from_three_real_responses(self, monkeypatch):
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies(
            positions_time=1000, orders_time=1200, wallet_time=1100,
        ))
        result = query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert result.observation_window.earliest_remote_time_ms == 1000
        assert result.observation_window.latest_remote_time_ms == 1200
        assert result.observation_window.remote_time_span_ms == 200

    def test_sub_snapshots_carry_their_own_server_time(self, monkeypatch):
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies(
            positions_time=111, orders_time=222, wallet_time=333,
        ))
        result = query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert result.positions.server_time_ms == 111
        assert result.open_orders.server_time_ms == 222
        assert result.wallet_balance.server_time_ms == 333


# ---------------------------------------------------------------------------
# 3. Entorno inválido
# ---------------------------------------------------------------------------

class TestInvalidEnvironment:
    def test_missing_api_key(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        env = {k: v for k, v in _VALID_ENV.items() if k != "PHOENIX_BYBIT_DEMO_API_KEY"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_KEY"):
            query_bybit_demo_exchange_state(environ=env)
        assert called == []

    def test_missing_api_secret(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        env = {k: v for k, v in _VALID_ENV.items() if k != "PHOENIX_BYBIT_DEMO_API_SECRET"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_SECRET"):
            query_bybit_demo_exchange_state(environ=env)
        assert called == []

    def test_invalid_timeout(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_HTTP_TIMEOUT_SECONDS"):
            query_bybit_demo_exchange_state(environ=_env(PHOENIX_HTTP_TIMEOUT_SECONDS="abc"))
        assert called == []


# ---------------------------------------------------------------------------
# 4. Fallos de red / HTTP -- todos traducidos, sin snapshot parcial
# ---------------------------------------------------------------------------

class TestFailuresTranslatedToInfrastructureError:
    def test_first_call_failure_translated_no_further_calls(self, monkeypatch):
        calls = []
        _install_sequenced_urlopen(
            monkeypatch, exc_on_call=(1, urllib.error.URLError("down")), capture=calls,
        )
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert len(calls) == 1

    def test_second_call_failure_translated_third_never_called(self, monkeypatch):
        calls = []
        _install_sequenced_urlopen(
            monkeypatch, exc_on_call=(2, urllib.error.URLError("down")), capture=calls,
        )
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert len(calls) == 2

    def test_third_call_failure_translated(self, monkeypatch):
        calls = []
        _install_sequenced_urlopen(
            monkeypatch, exc_on_call=(3, urllib.error.URLError("down")), capture=calls,
        )
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert len(calls) == 3

    def test_malformed_json_on_second_call_translated(self, monkeypatch):
        bodies = [_positions_body(), b"{not json", _wallet_balance_body()]
        _install_sequenced_urlopen(monkeypatch, bodies=bodies)
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_exchange_state(environ=_VALID_ENV)

    def test_auth_error_ret_code_on_first_call_translated(self, monkeypatch):
        bodies = [_envelope({}, ret_code=10003, ret_msg="invalid key"), b"", b""]
        _install_sequenced_urlopen(monkeypatch, bodies=bodies)
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_exchange_state(environ=_VALID_ENV)

    def test_bybit_processing_error_never_crosses_public_function(self, monkeypatch):
        from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
        _install_sequenced_urlopen(monkeypatch, bodies=[b"{not json", b"", b""])
        error = _raised(lambda: query_bybit_demo_exchange_state(environ=_VALID_ENV))
        assert not isinstance(error, BybitResponseProcessingError)
        assert isinstance(error, ExecutionInfrastructureError)


# ---------------------------------------------------------------------------
# 5. Exactamente tres llamadas HTTP en orden, sin I/O extra
# ---------------------------------------------------------------------------

class TestExactlyThreeCallsInOrder:
    def test_exactly_three_http_calls(self, monkeypatch):
        calls = []
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies(), capture=calls)
        query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert len(calls) == 3

    def test_urls_hit_positions_then_orders_then_wallet(self, monkeypatch):
        calls = []
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies(), capture=calls)
        query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert "/v5/position/list" in calls[0]["url"]
        assert "/v5/order/realtime" in calls[1]["url"]
        assert "/v5/account/wallet-balance" in calls[2]["url"]

    def test_all_three_are_get_with_no_body(self, monkeypatch):
        calls = []
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies(), capture=calls)
        query_bybit_demo_exchange_state(environ=_VALID_ENV)
        for call in calls:
            assert call["method"] == "GET"
            assert call["data"] is None

    def test_no_print(self, monkeypatch, capsys):
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies())
        query_bybit_demo_exchange_state(environ=_VALID_ENV)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


# ---------------------------------------------------------------------------
# 6. No trading / no metadata / no write-side
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_not_the_create_order_or_instruments_info_endpoint(self, monkeypatch):
        calls = []
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies(), capture=calls)
        query_bybit_demo_exchange_state(environ=_VALID_ENV)
        for call in calls:
            assert "/v5/order/create" not in call["url"]
            assert "/v5/market/instruments-info" not in call["url"]

    def test_does_not_import_create_order_types(self):
        src = inspect.getsource(_module)
        assert "BybitCreateOrderOperation" not in src
        assert "BybitCreateOrderRequest" not in src

    def test_does_not_use_bybit_execution_gateway(self):
        src = inspect.getsource(_module)
        assert "BybitExecutionGateway" not in src
        assert "BybitDemoClient" not in src

    def test_no_mainnet_reference(self):
        src = inspect.getsource(_module)
        assert "mainnet" not in src.lower()

    def test_no_railway_reference(self):
        src = inspect.getsource(_module)
        assert "railway" not in src.lower()

    def test_no_cancel_order_reference(self):
        src = inspect.getsource(_module)
        assert "cancel" not in src.lower()

    def test_module_only_calls_bootstrap_not_lower_factories(self):
        src = inspect.getsource(_module)
        forbidden = [
            "create_configured_bybit_demo_exchange_state_reader(",
            "create_bybit_demo_exchange_state_reader(",
            "load_bybit_demo_execution_config_from_env(",
        ]
        for f in forbidden:
            assert f not in src, f"{f} debe reutilizarse desde el grafo, no reconstruirse"


# ---------------------------------------------------------------------------
# 7. Seguridad
# ---------------------------------------------------------------------------

class TestSecurity:
    _MARKER = "ZZSUPERSECRETEXCHANGESTATE9999"

    def test_marker_absent_from_result_repr(self, monkeypatch):
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies())
        result = query_bybit_demo_exchange_state(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        )
        assert self._MARKER not in repr(result)

    def test_marker_absent_from_infrastructure_error_message(self, monkeypatch):
        bodies = [_envelope({}, ret_code=10003, ret_msg=self._MARKER), b"", b""]
        _install_sequenced_urlopen(monkeypatch, bodies=bodies)
        error = _raised(lambda: query_bybit_demo_exchange_state(
            environ=_env(PHOENIX_BYBIT_DEMO_API_SECRET=self._MARKER)
        ))
        assert error is not None
        assert self._MARKER not in str(error)

    def test_marker_absent_from_module_source(self):
        src = inspect.getsource(_module)
        assert self._MARKER not in src

    def test_no_print_in_source(self):
        assert "print(" not in inspect.getsource(_module)

    def test_no_logging_in_source(self):
        assert "logging" not in inspect.getsource(_module)


# ---------------------------------------------------------------------------
# 8. Dos rondas independientes / sin cache / sin singleton
# ---------------------------------------------------------------------------

class TestTwoRoundsIndependence:
    def test_two_calls_produce_distinct_results(self, monkeypatch):
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies(positions_time=100))
        r1 = query_bybit_demo_exchange_state(environ=_VALID_ENV)
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies(positions_time=200))
        r2 = query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert r1 is not r2
        assert r1.positions.server_time_ms == 100
        assert r2.positions.server_time_ms == 200

    def test_two_calls_each_issue_their_own_three_http_requests(self, monkeypatch):
        calls = []
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies(), capture=calls)
        query_bybit_demo_exchange_state(environ=_VALID_ENV)
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies(), capture=calls)
        query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert len(calls) == 6

    def test_no_module_level_mutable_state(self):
        mutable = [
            n for n, o in vars(_module).items()
            if not n.startswith("__") and isinstance(o, (list, dict, set))
        ]
        assert mutable == []

    def test_no_cache_or_memoization_in_source(self):
        src = inspect.getsource(_module)
        assert "cache" not in src.lower()
        assert "memo" not in src.lower()

    def test_second_call_after_first_failure_still_works(self, monkeypatch):
        _install_sequenced_urlopen(monkeypatch, exc_on_call=(1, urllib.error.URLError("down")))
        with pytest.raises(ExecutionInfrastructureError):
            query_bybit_demo_exchange_state(environ=_VALID_ENV)
        _install_sequenced_urlopen(monkeypatch, bodies=_default_bodies())
        result = query_bybit_demo_exchange_state(environ=_VALID_ENV)
        assert isinstance(result, ExchangeStateSnapshot)

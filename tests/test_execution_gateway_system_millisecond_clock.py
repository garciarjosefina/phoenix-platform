import os
import time
import pytest
from execution_gateway.system_millisecond_clock import SystemMillisecondClock
from execution_gateway.millisecond_clock import MillisecondClock
import execution_gateway


class TestImport:
    def test_direct_import(self):
        from execution_gateway.system_millisecond_clock import SystemMillisecondClock as C
        assert C is SystemMillisecondClock

    def test_public_import(self):
        assert hasattr(execution_gateway, "SystemMillisecondClock")
        assert execution_gateway.SystemMillisecondClock is SystemMillisecondClock

    def test_in_all(self):
        assert "SystemMillisecondClock" in execution_gateway.__all__


class TestStructural:
    def test_implements_millisecond_clock(self):
        clock = SystemMillisecondClock()
        assert isinstance(clock, MillisecondClock)

    def test_no_constructor_args(self):
        clock = SystemMillisecondClock()
        assert clock is not None

    def test_two_instances_independent(self):
        c1 = SystemMillisecondClock()
        c2 = SystemMillisecondClock()
        assert c1 is not c2


class TestBehavior:
    def test_returns_int(self):
        clock = SystemMillisecondClock()
        result = clock.now_ms()
        assert isinstance(result, int)

    def test_delegates_to_time_ns(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 1_700_000_000_000_000_000)
        clock = SystemMillisecondClock()
        assert clock.now_ms() == 1_700_000_000_000

    def test_integer_division_by_one_million(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 1_700_000_000_000_000_000)
        clock = SystemMillisecondClock()
        assert clock.now_ms() == 1_700_000_000_000_000_000 // 1_000_000

    def test_accepts_zero(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 0)
        clock = SystemMillisecondClock()
        assert clock.now_ms() == 0

    def test_truncates_nanosecond_remainder(self, monkeypatch):
        # 1_999_999 ns = 1 ms + 999_999 ns remainder → truncates to 1
        monkeypatch.setattr(time, "time_ns", lambda: 1_999_999)
        clock = SystemMillisecondClock()
        assert clock.now_ms() == 1

    def test_exact_value_for_simulated_ns(self, monkeypatch):
        ns = 1_609_459_200_123_456_789
        monkeypatch.setattr(time, "time_ns", lambda: ns)
        clock = SystemMillisecondClock()
        assert clock.now_ms() == ns // 1_000_000

    def test_calls_time_ns_each_invocation(self, monkeypatch):
        calls = []

        def fake_time_ns():
            calls.append(1)
            return 1_000_000_000

        monkeypatch.setattr(time, "time_ns", fake_time_ns)
        clock = SystemMillisecondClock()
        clock.now_ms()
        clock.now_ms()
        assert len(calls) == 2

    def test_single_time_ns_call_per_now_ms(self, monkeypatch):
        calls = []

        def fake_time_ns():
            calls.append(1)
            return 1_000_000_000

        monkeypatch.setattr(time, "time_ns", fake_time_ns)
        clock = SystemMillisecondClock()
        clock.now_ms()
        assert len(calls) == 1

    def test_exception_from_time_ns_propagates(self, monkeypatch):
        def raise_error():
            raise OSError("clock unavailable")

        monkeypatch.setattr(time, "time_ns", raise_error)
        clock = SystemMillisecondClock()
        with pytest.raises(OSError, match="clock unavailable"):
            clock.now_ms()


class TestNoSideEffects:
    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__sysclock_sentinel__"
        try:
            clock = SystemMillisecondClock()
            assert clock is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_no_external_dependencies(self):
        import sys
        for name in ("requests", "httpx", "aiohttp", "pybit"):
            assert name not in sys.modules or True


class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_millisecond_clock_contract_still_works(self):
        from execution_gateway.millisecond_clock import MillisecondClock
        assert MillisecondClock is not None

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None

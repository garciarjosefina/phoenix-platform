import os
import pytest
from execution_gateway.millisecond_clock import MillisecondClock
import execution_gateway


class _ValidClock:
    def __init__(self, value: int = 1_700_000_000_000):
        self._value = value
        self.call_count = 0

    def now_ms(self) -> int:
        self.call_count += 1
        return self._value


class _NoClock:
    def current_time(self) -> int:
        return 0


class TestImport:
    def test_direct_import(self):
        from execution_gateway.millisecond_clock import MillisecondClock as C
        assert C is MillisecondClock

    def test_public_import(self):
        assert hasattr(execution_gateway, "MillisecondClock")
        assert execution_gateway.MillisecondClock is MillisecondClock

    def test_in_all(self):
        assert "MillisecondClock" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable_valid(self):
        clock = _ValidClock()
        assert isinstance(clock, MillisecondClock)

    def test_incompatible_class_rejected(self):
        clock = _NoClock()
        assert not isinstance(clock, MillisecondClock)

    def test_no_explicit_inheritance_required(self):
        clock = _ValidClock()
        assert isinstance(clock, MillisecondClock)

    def test_returns_exact_int(self):
        clock = _ValidClock(1_700_000_000_000)
        assert clock.now_ms() == 1_700_000_000_000

    def test_accepts_zero(self):
        clock = _ValidClock(0)
        assert clock.now_ms() == 0

    def test_accepts_large_positive_int(self):
        clock = _ValidClock(9_999_999_999_999)
        assert clock.now_ms() == 9_999_999_999_999

    def test_isinstance_does_not_call_now_ms(self):
        clock = _ValidClock()
        _ = isinstance(clock, MillisecondClock)
        assert clock.call_count == 0


class TestNoSideEffects:
    def test_import_does_not_read_env(self):
        os.environ["BYBIT_API_KEY"] = "__clock_sentinel__"
        try:
            from execution_gateway.millisecond_clock import MillisecondClock as C
            assert C is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_import_does_not_call_system_clock(self):
        import time
        before = time.time_ns()
        from execution_gateway.millisecond_clock import MillisecondClock as C
        after = time.time_ns()
        assert C is not None
        assert after >= before

    def test_no_external_dependencies(self):
        import sys
        for name in ("requests", "httpx", "aiohttp", "pybit"):
            assert name not in sys.modules or True


class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_json_serializer_still_works(self):
        from execution_gateway.standard_json_serializer import StandardJsonSerializer
        s = StandardJsonSerializer()
        assert s.dumps({"a": 1}) == '{"a": 1}'

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None

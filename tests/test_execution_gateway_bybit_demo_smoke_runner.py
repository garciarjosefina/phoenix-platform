import importlib
import inspect
import runpy

import pytest

import execution_gateway
import execution_gateway.bybit_demo_smoke_runner as _module
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.environment_configuration_error import EnvironmentConfigurationError
from execution_gateway.smoke_test_result import SmokeTestResult

_MODULE_NAME = "execution_gateway.bybit_demo_smoke_runner"

_SUCCESS_RESULT = SmokeTestResult(
    success=True, endpoint="/v5/user/query-api", environment="demo", server_time=1_712_345_678_901,
)
_SUCCESS_RESULT_NO_OPTIONALS = SmokeTestResult(
    success=True, endpoint="/v5/user/query-api", environment="demo",
)


def _install(monkeypatch, fn):
    monkeypatch.setattr(_module, "smoke_test_bybit_demo_connection", fn)


def _counting(result=None, exc=None):
    calls = []

    def fn(*, environ=None):
        calls.append(environ)
        if exc is not None:
            raise exc
        return result

    return fn, calls


# ---------------------------------------------------------------------------
# 1. API y módulo
# ---------------------------------------------------------------------------

class TestModuleAndApi:
    def test_module_importable_without_side_effects(self):
        assert _module is not None

    def test_main_exists(self):
        assert hasattr(_module, "main")
        assert callable(_module.main)

    def test_main_signature_no_parameters(self):
        sig = inspect.signature(_module.main)
        assert len(sig.parameters) == 0

    def test_main_return_annotation_is_int(self):
        hints = inspect.get_annotations(_module.main, eval_str=True)
        assert hints.get("return") is int

    def test_source_has_dunder_main_guard(self):
        src = inspect.getsource(_module)
        assert 'if __name__ == "__main__":' in src
        assert "raise SystemExit(main())" in src

    def test_valid_python_dash_m_path(self):
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", _MODULE_NAME],
            capture_output=True, text=True, timeout=10,
            cwd="/Users/jose/phoenix-platform",
            env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "platform"},
        )
        assert result.returncode == 1
        assert "PHOENIX_BYBIT_DEMO_SMOKE_TEST_FAILURE" in result.stdout

    def test_main_not_exported_from_package(self):
        assert not hasattr(execution_gateway, "main")

    def test_runner_symbols_not_in_all(self):
        assert "main" not in execution_gateway.__all__
        assert "bybit_demo_smoke_runner" not in execution_gateway.__all__

    def test_package_init_does_not_import_runner(self):
        import execution_gateway as pkg
        src = inspect.getsource(pkg)
        assert "bybit_demo_smoke_runner" not in src


# ---------------------------------------------------------------------------
# 2. Éxito
# ---------------------------------------------------------------------------

class TestSuccess:
    def test_returns_zero(self, monkeypatch):
        fn, calls = _counting(result=_SUCCESS_RESULT)
        _install(monkeypatch, fn)
        assert _module.main() == 0

    def test_called_exactly_once(self, monkeypatch):
        fn, calls = _counting(result=_SUCCESS_RESULT)
        _install(monkeypatch, fn)
        _module.main()
        assert len(calls) == 1

    def test_called_with_environ_none(self, monkeypatch):
        fn, calls = _counting(result=_SUCCESS_RESULT)
        _install(monkeypatch, fn)
        _module.main()
        assert calls == [None]

    def test_stdout_exact_lines_and_order(self, monkeypatch, capsys):
        fn, _ = _counting(result=_SUCCESS_RESULT)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        lines = out.splitlines()
        assert lines == [
            "PHOENIX_BYBIT_DEMO_SMOKE_TEST_SUCCESS",
            "success=True",
            "endpoint=/v5/user/query-api",
            "environment=demo",
            "server_time=1712345678901",
            "account_type=NONE",
        ]

    def test_none_optionals_render_as_none_literal(self, monkeypatch, capsys):
        fn, _ = _counting(result=_SUCCESS_RESULT_NO_OPTIONALS)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "server_time=NONE" in out
        assert "account_type=NONE" in out
        assert "server_time=None\n" not in out
        assert "account_type=None\n" not in out

    def test_success_header_appears_exactly_once(self, monkeypatch, capsys):
        fn, _ = _counting(result=_SUCCESS_RESULT)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert out.count("PHOENIX_BYBIT_DEMO_SMOKE_TEST_SUCCESS") == 1

    def test_no_stderr(self, monkeypatch, capsys):
        fn, _ = _counting(result=_SUCCESS_RESULT)
        _install(monkeypatch, fn)
        _module.main()
        assert capsys.readouterr().err == ""

    def test_no_traceback_in_output(self, monkeypatch, capsys):
        fn, _ = _counting(result=_SUCCESS_RESULT)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "Traceback" not in out

    def test_no_repr_of_result_in_output(self, monkeypatch, capsys):
        fn, _ = _counting(result=_SUCCESS_RESULT)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "SmokeTestResult(" not in out


# ---------------------------------------------------------------------------
# 3. success=False
# ---------------------------------------------------------------------------

class TestNotSuccessful:
    _RESULT = SmokeTestResult(success=False, endpoint="/v5/user/query-api", environment="demo")

    def test_returns_one(self, monkeypatch):
        fn, _ = _counting(result=self._RESULT)
        _install(monkeypatch, fn)
        assert _module.main() == 1

    def test_prints_failure_header(self, monkeypatch, capsys):
        fn, _ = _counting(result=self._RESULT)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert out.splitlines()[0] == "PHOENIX_BYBIT_DEMO_SMOKE_TEST_FAILURE"

    def test_does_not_print_success_header(self, monkeypatch, capsys):
        fn, _ = _counting(result=self._RESULT)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "PHOENIX_BYBIT_DEMO_SMOKE_TEST_SUCCESS" not in out

    def test_called_exactly_once(self, monkeypatch):
        fn, calls = _counting(result=self._RESULT)
        _install(monkeypatch, fn)
        _module.main()
        assert len(calls) == 1

    def test_does_not_expose_endpoint_or_environment_fields(self, monkeypatch, capsys):
        fn, _ = _counting(result=self._RESULT)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "endpoint=" not in out
        assert "environment=" not in out


# ---------------------------------------------------------------------------
# 4. Error de entorno
# ---------------------------------------------------------------------------

class TestEnvironmentConfigurationErrorHandling:
    _ERROR = EnvironmentConfigurationError(
        message="Missing required environment variable: PHOENIX_BYBIT_DEMO_API_KEY"
    )

    def test_returns_one(self, monkeypatch):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        assert _module.main() == 1

    def test_prints_failure_header_and_safe_fields(self, monkeypatch, capsys):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert out.splitlines() == [
            "PHOENIX_BYBIT_DEMO_SMOKE_TEST_FAILURE",
            "error_type=EnvironmentConfigurationError",
            "error_message=Missing required environment variable: PHOENIX_BYBIT_DEMO_API_KEY",
        ]

    def test_called_exactly_once(self, monkeypatch):
        fn, calls = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        assert len(calls) == 1

    def test_no_traceback(self, monkeypatch, capsys):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        assert "Traceback" not in capsys.readouterr().out

    def test_message_is_verbatim_contract_message_only(self, monkeypatch, capsys):
        # EnvironmentConfigurationError sólo produce dos formas de mensaje,
        # ninguna con valores dinámicos (Hito 3.65): "Missing required
        # environment variable: {name}" o "Invalid .../numeric environment
        # variable: {name}", donde {name} es siempre el nombre de la
        # variable, nunca su valor.
        error = EnvironmentConfigurationError(
            message="Invalid numeric environment variable: PHOENIX_HTTP_TIMEOUT_SECONDS"
        )
        fn, _ = _counting(exc=error)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "error_message=Invalid numeric environment variable: PHOENIX_HTTP_TIMEOUT_SECONDS" in out


# ---------------------------------------------------------------------------
# 5. BybitApiError
# ---------------------------------------------------------------------------

class TestBybitApiErrorHandling:
    _ERROR = BybitApiError(ret_code=10003, ret_msg="API key ZZRUNNERAPIKEY9999 is invalid")

    def test_returns_one(self, monkeypatch):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        assert _module.main() == 1

    def test_no_retry_no_second_call(self, monkeypatch):
        fn, calls = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        assert len(calls) == 1

    def test_uses_generic_public_message(self, monkeypatch, capsys):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "error_message=Bybit authentication or API validation failure" in out

    def test_error_type_is_class_name(self, monkeypatch, capsys):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "error_type=BybitApiError" in out

    def test_ret_code_not_printed(self, monkeypatch, capsys):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "10003" not in out

    def test_ret_msg_not_printed(self, monkeypatch, capsys):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "invalid" not in out

    def test_marker_absent(self, monkeypatch, capsys):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        assert "ZZRUNNERAPIKEY9999" not in capsys.readouterr().out

    def test_no_headers_or_signature_leak(self, monkeypatch, capsys):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "X-BAPI" not in out


# ---------------------------------------------------------------------------
# 6. Errores HTTP y de red
# ---------------------------------------------------------------------------

class TestNetworkErrorHandling:
    def _run(self, monkeypatch, exc):
        fn, calls = _counting(exc=exc)
        _install(monkeypatch, fn)
        return calls

    def test_http_error(self, monkeypatch, capsys):
        import urllib.error
        exc = urllib.error.HTTPError(
            "https://api-demo.bybit.com/v5/user/query-api?secret=ZZRUNNERSECRET9999",
            403, "Forbidden", {}, None,
        )
        calls = self._run(monkeypatch, exc)
        assert _module.main() == 1
        out = capsys.readouterr().out
        assert "ZZRUNNERSECRET9999" not in out
        assert "error_message=Remote connectivity or HTTP failure" in out
        assert len(calls) == 1

    def test_url_error(self, monkeypatch, capsys):
        import urllib.error
        exc = urllib.error.URLError("dns resolution failed")
        calls = self._run(monkeypatch, exc)
        assert _module.main() == 1
        out = capsys.readouterr().out
        assert "error_message=Remote connectivity or HTTP failure" in out
        assert len(calls) == 1

    def test_timeout_error(self, monkeypatch, capsys):
        calls = self._run(monkeypatch, TimeoutError("timed out"))
        assert _module.main() == 1
        out = capsys.readouterr().out
        assert "error_message=Remote connectivity or HTTP failure" in out
        assert len(calls) == 1

    def test_os_error(self, monkeypatch, capsys):
        calls = self._run(monkeypatch, OSError("connection refused"))
        assert _module.main() == 1
        out = capsys.readouterr().out
        assert "error_message=Remote connectivity or HTTP failure" in out
        assert len(calls) == 1

    def test_no_url_leaked(self, monkeypatch, capsys):
        import urllib.error
        exc = urllib.error.URLError("https://api-demo.bybit.com/v5/user/query-api")
        self._run(monkeypatch, exc)
        _module.main()
        out = capsys.readouterr().out
        assert "api-demo.bybit.com" not in out

    def test_no_headers_leaked(self, monkeypatch, capsys):
        import urllib.error
        exc = urllib.error.HTTPError("u", 401, "X-BAPI-SIGN invalid", {}, None)
        self._run(monkeypatch, exc)
        _module.main()
        out = capsys.readouterr().out
        assert "X-BAPI" not in out

    def test_no_traceback(self, monkeypatch, capsys):
        self._run(monkeypatch, OSError("x"))
        _module.main()
        assert "Traceback" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 7. Error de parsing
# ---------------------------------------------------------------------------

class TestResponseProcessingErrorHandling:
    _ERROR = BybitResponseProcessingError(message="Bybit response could not be processed")

    def test_returns_one(self, monkeypatch):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        assert _module.main() == 1

    def test_safe_message_printed(self, monkeypatch, capsys):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "error_message=Bybit response could not be processed" in out

    def test_no_remote_body_leaked(self, monkeypatch, capsys):
        fn, _ = _counting(exc=self._ERROR)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "retCode" not in out
        assert "result" not in out

    def test_no_cause_leaked(self, monkeypatch, capsys):
        try:
            raise ValueError("internal parse detail with ZZRUNNERBODY9999")
        except ValueError as inner:
            error = BybitResponseProcessingError(message="Bybit response could not be processed")
            error.__cause__ = inner
        fn, _ = _counting(exc=error)
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "ZZRUNNERBODY9999" not in out


# ---------------------------------------------------------------------------
# 8. Error inesperado
# ---------------------------------------------------------------------------

class TestUnexpectedErrorHandling:
    def test_runtime_error_with_secret(self, monkeypatch, capsys):
        marker = "ZZRUNNERSECRET9999"
        fn, calls = _counting(exc=RuntimeError(f"internal failure: {marker}"))
        _install(monkeypatch, fn)
        code = _module.main()
        out = capsys.readouterr().out
        assert code == 1
        assert marker not in out
        assert "error_message=Unexpected smoke test failure" in out
        assert "error_type=RuntimeError" in out
        assert len(calls) == 1

    def test_attribute_error_with_marker(self, monkeypatch, capsys):
        marker = "ZZRUNNERAPIKEY9999"
        fn, _ = _counting(exc=AttributeError(f"'{marker}' object has no attribute 'x'"))
        _install(monkeypatch, fn)
        code = _module.main()
        out = capsys.readouterr().out
        assert code == 1
        assert marker not in out
        assert "error_type=AttributeError" in out
        assert "error_message=Unexpected smoke test failure" in out

    def test_assertion_error_with_marker(self, monkeypatch, capsys):
        marker = "ZZRUNNERSIGNATURE9999"
        fn, _ = _counting(exc=AssertionError(f"invariant broken: {marker}"))
        _install(monkeypatch, fn)
        code = _module.main()
        out = capsys.readouterr().out
        assert code == 1
        assert marker not in out
        assert "error_type=AssertionError" in out
        assert "error_message=Unexpected smoke test failure" in out

    def test_does_not_print_str_of_unexpected_error(self, monkeypatch, capsys):
        fn, _ = _counting(exc=RuntimeError("this exact text must not appear"))
        _install(monkeypatch, fn)
        _module.main()
        out = capsys.readouterr().out
        assert "this exact text must not appear" not in out

    def test_no_traceback(self, monkeypatch, capsys):
        fn, _ = _counting(exc=RuntimeError("x"))
        _install(monkeypatch, fn)
        _module.main()
        assert "Traceback" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 9. SystemExit y KeyboardInterrupt
# ---------------------------------------------------------------------------

class TestUncapturedControlFlowExceptions:
    def test_keyboard_interrupt_not_captured(self, monkeypatch):
        fn, _ = _counting(exc=KeyboardInterrupt())
        _install(monkeypatch, fn)
        with pytest.raises(KeyboardInterrupt):
            _module.main()

    def test_system_exit_not_captured(self, monkeypatch):
        fn, _ = _counting(exc=SystemExit(3))
        _install(monkeypatch, fn)
        with pytest.raises(SystemExit) as exc_info:
            _module.main()
        assert exc_info.value.code == 3

    def test_source_does_not_catch_base_exception(self):
        src = inspect.getsource(_module)
        assert "except BaseException" not in src

    def test_source_does_not_catch_keyboard_interrupt(self):
        src = inspect.getsource(_module)
        assert "KeyboardInterrupt" not in src

    def test_source_does_not_catch_system_exit_inside_main(self):
        main_src = inspect.getsource(_module.main)
        assert "SystemExit" not in main_src


# ---------------------------------------------------------------------------
# 10. Import safety
# ---------------------------------------------------------------------------

class TestImportSafety:
    def test_reimport_does_not_call_smoke_test(self, monkeypatch):
        def explode(*, environ=None):
            raise AssertionError("smoke test must not run during import")

        monkeypatch.setattr(
            "execution_gateway.bybit_demo_connectivity_smoke_test.smoke_test_bybit_demo_connection",
            explode,
        )
        importlib.reload(_module)

    def test_reimport_does_not_read_os_environ(self, monkeypatch):
        import os
        calls = []
        original = os.environ.get

        def spy(*a, **k):
            calls.append(a)
            return original(*a, **k)

        monkeypatch.setattr(os.environ, "get", spy)
        importlib.reload(_module)
        assert calls == []

    def test_reimport_does_not_open_network(self, monkeypatch):
        import urllib.request
        calls = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: calls.append(1))
        importlib.reload(_module)
        assert calls == []

    def test_reimport_does_not_print(self, monkeypatch, capsys):
        importlib.reload(_module)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_reimport_does_not_raise_system_exit(self):
        importlib.reload(_module)  # no SystemExit propagated

    def test_reimport_does_not_read_clock(self, monkeypatch):
        import time
        calls = []
        original = time.time_ns

        def spy():
            calls.append(1)
            return original()

        monkeypatch.setattr(time, "time_ns", spy)
        importlib.reload(_module)
        assert calls == []

    def test_reimport_does_not_sign(self, monkeypatch):
        from execution_gateway.hmac_sha256_signer import HmacSha256Signer
        calls = []

        def spy(self, *, secret, message):
            calls.append(1)
            return "x"

        monkeypatch.setattr(HmacSha256Signer, "sign", spy)
        importlib.reload(_module)
        assert calls == []


# ---------------------------------------------------------------------------
# 11. Exactly-once (consolidado)
# ---------------------------------------------------------------------------

class TestExactlyOnceAcrossAllPaths:
    @pytest.mark.parametrize("exc_or_result", [
        None,  # marcador para success
        SmokeTestResult(success=False, endpoint="/x", environment="demo"),
        EnvironmentConfigurationError(message="missing PHOENIX_BYBIT_DEMO_API_KEY"),
        BybitApiError(ret_code=10003, ret_msg="invalid"),
        OSError("network down"),
        RuntimeError("unexpected"),
    ])
    def test_exactly_one_call(self, monkeypatch, exc_or_result):
        if exc_or_result is None:
            fn, calls = _counting(result=_SUCCESS_RESULT)
        elif isinstance(exc_or_result, SmokeTestResult):
            fn, calls = _counting(result=exc_or_result)
        else:
            fn, calls = _counting(exc=exc_or_result)
        _install(monkeypatch, fn)
        _module.main()
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# 12. Ejecución como módulo (runpy)
# ---------------------------------------------------------------------------

class TestModuleExecution:
    def test_runpy_success_path(self, monkeypatch, capsys):
        import json
        import urllib.request

        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_KEY", "demo-key")
        monkeypatch.setenv("PHOENIX_BYBIT_DEMO_API_SECRET", "demo-secret")
        monkeypatch.setenv("PHOENIX_BYBIT_RECV_WINDOW_MS", "5000")
        monkeypatch.setenv("PHOENIX_HTTP_TIMEOUT_SECONDS", "10")

        class FakeResp:
            def read(self):
                return json.dumps({
                    "retCode": 0, "retMsg": "OK", "result": {},
                    "retExtInfo": {}, "time": 1_700_000_000_000,
                }).encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp())

        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module(_MODULE_NAME, run_name="__main__")

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "PHOENIX_BYBIT_DEMO_SMOKE_TEST_SUCCESS" in out
        assert out.count("PHOENIX_BYBIT_DEMO_SMOKE_TEST_SUCCESS") == 1

    def test_runpy_exit_code_matches_main_failure(self, monkeypatch):
        monkeypatch.delenv("PHOENIX_BYBIT_DEMO_API_KEY", raising=False)
        monkeypatch.delenv("PHOENIX_BYBIT_DEMO_API_SECRET", raising=False)
        monkeypatch.delenv("PHOENIX_BYBIT_RECV_WINDOW_MS", raising=False)
        monkeypatch.delenv("PHOENIX_HTTP_TIMEOUT_SECONDS", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module(_MODULE_NAME, run_name="__main__")

        assert exc_info.value.code == 1

    def test_runpy_no_stderr_on_failure(self, monkeypatch, capsys):
        monkeypatch.delenv("PHOENIX_BYBIT_DEMO_API_KEY", raising=False)
        with pytest.raises(SystemExit):
            runpy.run_module(_MODULE_NAME, run_name="__main__")
        assert capsys.readouterr().err == ""

    def test_import_as_non_main_does_not_execute(self):
        # ejecutar con run_name distinto de "__main__" no debe invocar main()
        module_globals = runpy.run_module(_MODULE_NAME, run_name="not_main")
        assert "main" in module_globals


# ---------------------------------------------------------------------------
# 13. Ausencia de trading
# ---------------------------------------------------------------------------

class TestNoTradingSideEffects:
    def test_no_trading_calls_on_success(self, monkeypatch):
        from execution_gateway.bybit_create_order_operation import BybitCreateOrderOperation
        from execution_gateway.bybit_gateway import BybitExecutionGateway
        from execution_gateway.bybit_client import BybitDemoClient
        from execution_gateway.urllib_http_transport import UrllibHttpTransport

        hits = []
        monkeypatch.setattr(BybitCreateOrderOperation, "execute", lambda self, **k: hits.append("op"))
        monkeypatch.setattr(BybitExecutionGateway, "execute", lambda self, r: hits.append("exec"))
        monkeypatch.setattr(BybitDemoClient, "place_order", lambda self, r: hits.append("place"))
        monkeypatch.setattr(BybitDemoClient, "create_order", lambda self, **k: hits.append("create"))
        monkeypatch.setattr(UrllibHttpTransport, "post", lambda self, **k: hits.append("post"))

        fn, _ = _counting(result=_SUCCESS_RESULT)
        _install(monkeypatch, fn)
        _module.main()
        assert hits == []

    def test_no_trading_calls_on_failure(self, monkeypatch):
        from execution_gateway.bybit_create_order_operation import BybitCreateOrderOperation
        from execution_gateway.bybit_gateway import BybitExecutionGateway

        hits = []
        monkeypatch.setattr(BybitCreateOrderOperation, "execute", lambda self, **k: hits.append("op"))
        monkeypatch.setattr(BybitExecutionGateway, "execute", lambda self, r: hits.append("exec"))

        fn, _ = _counting(exc=OSError("x"))
        _install(monkeypatch, fn)
        _module.main()
        assert hits == []


# ---------------------------------------------------------------------------
# 14. Superficie mínima
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_no_argparse(self):
        src = inspect.getsource(_module)
        assert "argparse" not in src

    def test_no_click(self):
        src = inspect.getsource(_module)
        assert "click" not in src

    def test_no_typer(self):
        src = inspect.getsource(_module)
        assert "typer" not in src

    def test_no_logging(self):
        src = inspect.getsource(_module)
        assert "logging" not in src

    def test_no_retry_or_backoff(self):
        src = inspect.getsource(_module)
        assert "retry" not in src.lower()
        assert "backoff" not in src.lower()

    def test_no_loop_constructs(self):
        src = inspect.getsource(_module)
        assert "while " not in src
        assert "for " not in src

    def test_no_sleep(self):
        src = inspect.getsource(_module)
        assert "sleep" not in src

    def test_no_dotenv(self):
        src = inspect.getsource(_module)
        assert "dotenv" not in src.lower()

    def test_no_railway_reference(self):
        src = inspect.getsource(_module)
        assert "railway" not in src.lower()

    def test_no_socket(self):
        src = inspect.getsource(_module)
        assert "socket" not in src

    def test_no_urllib(self):
        src = inspect.getsource(_module)
        assert "urllib" not in src

    def test_no_requests_library(self):
        src = inspect.getsource(_module)
        assert "import requests" not in src

    def test_no_open(self):
        src = inspect.getsource(_module)
        assert "open(" not in src

    def test_no_pathlib(self):
        src = inspect.getsource(_module)
        assert "pathlib" not in src

    def test_no_json(self):
        src = inspect.getsource(_module)
        assert "json" not in src.lower()

    def test_no_manual_gateway_construction(self):
        src = inspect.getsource(_module)
        for forbidden in (
            "bootstrap_bybit_demo_execution_gateway_from_env",
            "load_bybit_demo_execution_config_from_env",
            "create_configured_bybit_demo_execution_gateway",
            "BybitDemoExecutionConfig(",
            "BybitExecutionGateway(",
        ):
            assert forbidden not in src

    def test_no_direct_environ_read(self):
        src = inspect.getsource(_module)
        assert "os.environ" not in src
        assert "os.getenv" not in src
        assert "import os" not in src

    def test_no_sys_exit_outside_guard(self):
        main_src = inspect.getsource(_module.main)
        assert "sys.exit" not in main_src
        assert "SystemExit" not in main_src

    def test_single_public_function(self):
        public = [
            n for n, o in vars(_module).items()
            if not n.startswith("_") and inspect.isfunction(o) and o.__module__ == _module.__name__
        ]
        assert public == ["main"]

    def test_no_mutable_globals(self):
        mutable = [
            n for n, o in vars(_module).items()
            if not n.startswith("__") and isinstance(o, (list, dict, set))
        ]
        assert mutable == []

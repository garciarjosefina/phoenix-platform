"""ADR-001 — El Port del dominio (ExecutionGateway / ExecutionRequest /
ExecutionResult) no debe conocer ningún tipo Bybit*. Toda la traducción vive
exclusivamente dentro del adaptador BybitExecutionGateway.

ADR-001A — Los rechazos de negocio (BybitApiError) se traducen a
ExecutionResult(status="rejected") y los errores de infraestructura se
traducen a ExecutionInfrastructureError. Ningún tipo Bybit* cruza la
frontera del Port en ningún camino, incluido el de error."""
import inspect

import pytest

import execution_gateway.contracts as contracts_module
import execution_gateway.execution_infrastructure_error as execution_infrastructure_error_module
import execution_gateway.execution_request_not_supported_error as execution_request_not_supported_error_module
import execution_gateway.factory as factory_module
import execution_gateway.gateway as gateway_module
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.execution_request_not_supported_error import ExecutionRequestNotSupportedError
from execution_gateway.factory import create_execution_gateway
from execution_gateway.gateway import ExecutionGateway

# Módulos del Port y de sus factories genéricas: ninguno debe conocer ningún
# exchange concreto. La regla es simétrica -aplica igual a todos-, a
# diferencia de la asimetría detectada por la Auditoría Retrospectiva A
# (que sólo protegía gateway/contracts/dry_run/fake, dejando pasar
# BybitDemoClient en factory.py).
_DOMAIN_ONLY_MODULES = (
    gateway_module,
    contracts_module,
    execution_infrastructure_error_module,
    execution_request_not_supported_error_module,
    factory_module,
)

_KNOWN_EXCHANGE_NAMES = ("Bybit", "Binance", "OKX", "Hyperliquid")


class TestDomainModulesDoNotReferenceBybit:
    def test_gateway_module_source_has_no_bybit_reference(self):
        src = inspect.getsource(gateway_module)
        assert "Bybit" not in src

    def test_contracts_module_source_has_no_bybit_reference(self):
        src = inspect.getsource(contracts_module)
        assert "Bybit" not in src

    def test_gateway_module_imports_no_bybit_symbol(self):
        for name in vars(gateway_module):
            assert not name.startswith("Bybit")

    def test_contracts_module_imports_no_bybit_symbol(self):
        for name in vars(contracts_module):
            assert not name.startswith("Bybit")


class TestExecutionGatewayProtocolIsDomainOnly:
    def test_execute_parameter_annotated_with_execution_request(self):
        hints = inspect.get_annotations(ExecutionGateway.execute, eval_str=True)
        assert hints.get("request") is ExecutionRequest

    def test_execute_return_annotated_with_execution_result(self):
        hints = inspect.get_annotations(ExecutionGateway.execute, eval_str=True)
        assert hints.get("return") is ExecutionResult

    def test_protocol_exposes_no_bybit_typed_member(self):
        src = inspect.getsource(gateway_module)
        assert "Bybit" not in src


class TestBybitExecutionGatewayHonoursTheDomainContract:
    def test_execute_public_signature_is_domain_only(self):
        hints = inspect.get_annotations(BybitExecutionGateway.execute, eval_str=True)
        assert hints.get("request") is ExecutionRequest
        assert hints.get("return") is ExecutionResult

    def test_bybit_execution_gateway_satisfies_execution_gateway_protocol(self):
        class _StubClient:
            def place_order(self, request):
                from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
                return BybitCreateOrderResult(order_id="x", order_link_id="y")

        gw = BybitExecutionGateway(client=_StubClient())
        assert isinstance(gw, ExecutionGateway)

    def test_translation_helpers_are_private_to_the_adapter(self):
        public_members = [
            name for name in vars(BybitExecutionGateway)
            if not name.startswith("_")
        ]
        assert public_members == ["execute"]


class TestOnlyTheAdapterKnowsBybitTypes:
    def test_bybit_gateway_module_is_the_translation_boundary(self):
        import execution_gateway.bybit_gateway as adapter_module
        src = inspect.getsource(adapter_module)
        assert "BybitCreateOrderRequest" in src
        assert "BybitCreateOrderResult" in src

    def test_no_other_domain_module_imports_bybit_create_order_types(self):
        for module_name in ("gateway", "contracts", "dry_run_gateway", "fake_gateway", "factory"):
            module = __import__(f"execution_gateway.{module_name}", fromlist=[module_name])
            src = inspect.getsource(module)
            assert "BybitCreateOrderRequest" not in src
            assert "BybitCreateOrderResult" not in src


class TestErrorPathIsAlsoDomainOnly:
    """ADR-001A: el camino de error del Port tampoco debe conocer Bybit*."""

    def test_execution_infrastructure_error_module_has_no_bybit_reference(self):
        src = inspect.getsource(execution_infrastructure_error_module)
        assert "Bybit" not in src

    def test_execution_infrastructure_error_imports_no_bybit_symbol(self):
        for name in vars(execution_infrastructure_error_module):
            assert not name.startswith("Bybit")

    def test_gateway_module_does_not_reference_bybit_api_error(self):
        src = inspect.getsource(gateway_module)
        assert "BybitApiError" not in src

    def test_contracts_module_does_not_reference_bybit_api_error(self):
        src = inspect.getsource(contracts_module)
        assert "BybitApiError" not in src

    def test_bybit_api_error_never_crosses_execute(self):
        from execution_gateway.bybit_create_order_result import BybitCreateOrderResult

        class _RejectingClient:
            def place_order(self, request):
                raise BybitApiError(ret_code=10001, ret_msg="params error")

        gw = BybitExecutionGateway(client=_RejectingClient())
        result = gw.execute(
            ExecutionRequest(order_id="d1", symbol="BTCUSDT", side="buy", order_type="market", quantity=1.0)
        )
        assert isinstance(result, ExecutionResult)
        assert result.status == "rejected"

    def test_infrastructure_failure_never_crosses_execute_as_raw_exception(self):
        class _RaisingClient:
            def place_order(self, request):
                raise OSError("network down")

        gw = BybitExecutionGateway(client=_RaisingClient())
        try:
            gw.execute(
                ExecutionRequest(order_id="d1", symbol="BTCUSDT", side="buy", order_type="market", quantity=1.0)
            )
            assert False, "expected ExecutionInfrastructureError"
        except ExecutionInfrastructureError:
            pass
        except OSError:
            raise AssertionError("raw infrastructure exception must not cross the Port unwrapped")

    def test_programming_errors_are_not_disguised_as_infrastructure_error(self):
        class _BuggyClient:
            def place_order(self, request):
                raise TypeError("bug in adapter")

        gw = BybitExecutionGateway(client=_BuggyClient())
        try:
            gw.execute(
                ExecutionRequest(order_id="d1", symbol="BTCUSDT", side="buy", order_type="market", quantity=1.0)
            )
            assert False, "expected TypeError"
        except ExecutionInfrastructureError:
            raise AssertionError("a programming defect must not be disguised as infrastructure failure")
        except TypeError:
            pass


# ---------------------------------------------------------------------------
# Core Hardening Pack A, Parte L — pureza aplicada simétricamente a TODOS
# los módulos del Port y sus factories genéricas, no sólo a un subconjunto.
# ---------------------------------------------------------------------------

class TestSymmetricPurityAcrossAllDomainModules:
    @pytest.mark.parametrize("module", _DOMAIN_ONLY_MODULES, ids=lambda m: m.__name__)
    def test_module_source_names_no_known_exchange(self, module):
        src = inspect.getsource(module)
        for exchange in _KNOWN_EXCHANGE_NAMES:
            assert exchange not in src, f"{module.__name__} references {exchange!r}"

    @pytest.mark.parametrize("module", _DOMAIN_ONLY_MODULES, ids=lambda m: m.__name__)
    def test_module_imports_no_exchange_prefixed_symbol(self, module):
        for name in vars(module):
            for exchange in _KNOWN_EXCHANGE_NAMES:
                assert not name.startswith(exchange), f"{module.__name__} imports {name!r}"

    def test_create_execution_gateway_signature_has_no_exchange_specific_parameter(self):
        sig = inspect.signature(create_execution_gateway)
        assert list(sig.parameters) == ["config"]

    def test_create_execution_gateway_does_not_require_any_client_type(self):
        for param in inspect.signature(create_execution_gateway).parameters.values():
            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                continue
            annotation_str = str(annotation)
            for exchange in _KNOWN_EXCHANGE_NAMES:
                assert exchange not in annotation_str

    def test_live_execution_error_message_names_no_exchange(self):
        from execution_gateway.config import GatewayConfig
        try:
            create_execution_gateway(GatewayConfig(dry_run=False))
            assert False, "expected ValueError"
        except ValueError as e:
            for exchange in _KNOWN_EXCHANGE_NAMES:
                assert exchange not in str(e)

    def test_execution_request_not_supported_error_is_domain_only(self):
        src = inspect.getsource(execution_request_not_supported_error_module)
        for exchange in _KNOWN_EXCHANGE_NAMES:
            assert exchange not in src

    def test_order_id_length_incompatibility_raises_domain_exception_without_exchange_vocabulary(self):
        client_result_holder = {}

        class _StubClient:
            def place_order(self, request):
                client_result_holder["called"] = True
                from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
                return BybitCreateOrderResult(order_id="x", order_link_id=request.order_link_id)

        gw = BybitExecutionGateway(client=_StubClient())
        long_request = ExecutionRequest(
            order_id="x" * 37, symbol="BTCUSDT", side="buy", order_type="market", quantity=1.0
        )
        try:
            gw.execute(long_request)
            assert False, "expected ExecutionRequestNotSupportedError"
        except ExecutionRequestNotSupportedError as e:
            for exchange in _KNOWN_EXCHANGE_NAMES:
                assert exchange not in str(e)
            assert "order_link_id" not in str(e)
        assert "called" not in client_result_holder

"""ADR-001 — El Port del dominio (ExecutionGateway / ExecutionRequest /
ExecutionResult) no debe conocer ningún tipo Bybit*. Toda la traducción vive
exclusivamente dentro del adaptador BybitExecutionGateway.

ADR-001A — Los rechazos de negocio (BybitApiError) se traducen a
ExecutionResult(status="rejected") y los errores de infraestructura se
traducen a ExecutionInfrastructureError. Ningún tipo Bybit* cruza la
frontera del Port en ningún camino, incluido el de error."""
import inspect

import execution_gateway.contracts as contracts_module
import execution_gateway.execution_infrastructure_error as execution_infrastructure_error_module
import execution_gateway.gateway as gateway_module
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.gateway import ExecutionGateway


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
                raise RuntimeError("network down")

        gw = BybitExecutionGateway(client=_RaisingClient())
        try:
            gw.execute(
                ExecutionRequest(order_id="d1", symbol="BTCUSDT", side="buy", order_type="market", quantity=1.0)
            )
            assert False, "expected ExecutionInfrastructureError"
        except ExecutionInfrastructureError:
            pass
        except RuntimeError:
            raise AssertionError("raw infrastructure exception must not cross the Port unwrapped")

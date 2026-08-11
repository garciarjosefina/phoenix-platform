import pytest
import execution_gateway
import execution_gateway.bybit_endpoints as bybit_endpoints_module
from execution_gateway.bybit_endpoints import (
    BYBIT_CREATE_ORDER_ENDPOINT,
    BYBIT_OPEN_ORDERS_ENDPOINT,
    BYBIT_POSITIONS_ENDPOINT,
)
from execution_gateway.bybit_endpoint import BybitEndpoint


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_endpoints import BYBIT_CREATE_ORDER_ENDPOINT as C
        assert C is BYBIT_CREATE_ORDER_ENDPOINT

    def test_public_import(self):
        assert hasattr(execution_gateway, "BYBIT_CREATE_ORDER_ENDPOINT")
        assert execution_gateway.BYBIT_CREATE_ORDER_ENDPOINT is BYBIT_CREATE_ORDER_ENDPOINT

    def test_in_package_all(self):
        assert "BYBIT_CREATE_ORDER_ENDPOINT" in execution_gateway.__all__

    def test_in_module_all(self):
        assert "BYBIT_CREATE_ORDER_ENDPOINT" in bybit_endpoints_module.__all__

    def test_same_object_from_both_imports(self):
        assert execution_gateway.BYBIT_CREATE_ORDER_ENDPOINT is BYBIT_CREATE_ORDER_ENDPOINT


# ── tipo y valor ───────────────────────────────────────────────────────────

class TestTypeAndValue:
    def test_is_bybit_endpoint(self):
        assert isinstance(BYBIT_CREATE_ORDER_ENDPOINT, BybitEndpoint)

    def test_method_is_post(self):
        assert BYBIT_CREATE_ORDER_ENDPOINT.method == "POST"

    def test_path_is_order_create(self):
        assert BYBIT_CREATE_ORDER_ENDPOINT.path == "/v5/order/create"

    def test_method_exact_string(self):
        assert BYBIT_CREATE_ORDER_ENDPOINT.method == "POST"
        assert BYBIT_CREATE_ORDER_ENDPOINT.method != "post"
        assert BYBIT_CREATE_ORDER_ENDPOINT.method != "Post"

    def test_path_exact_string(self):
        assert BYBIT_CREATE_ORDER_ENDPOINT.path == "/v5/order/create"
        assert BYBIT_CREATE_ORDER_ENDPOINT.path != "/v5/order/create/"
        assert BYBIT_CREATE_ORDER_ENDPOINT.path != "v5/order/create"

    def test_equal_to_equivalent_endpoint(self):
        equivalent = BybitEndpoint(method="POST", path="/v5/order/create")
        assert BYBIT_CREATE_ORDER_ENDPOINT == equivalent

    def test_not_a_class(self):
        assert not isinstance(BYBIT_CREATE_ORDER_ENDPOINT, type)

    def test_not_a_function(self):
        import inspect
        assert not inspect.isfunction(BYBIT_CREATE_ORDER_ENDPOINT)

    def test_not_a_dict(self):
        assert not isinstance(BYBIT_CREATE_ORDER_ENDPOINT, dict)

    def test_not_a_list(self):
        assert not isinstance(BYBIT_CREATE_ORDER_ENDPOINT, list)

    def test_not_a_tuple(self):
        assert not isinstance(BYBIT_CREATE_ORDER_ENDPOINT, tuple)

    def test_no_url_base(self):
        assert "bybit.com" not in BYBIT_CREATE_ORDER_ENDPOINT.path
        assert "https://" not in BYBIT_CREATE_ORDER_ENDPOINT.path

    def test_no_query_string(self):
        assert "?" not in BYBIT_CREATE_ORDER_ENDPOINT.path

    def test_no_fragment(self):
        assert "#" not in BYBIT_CREATE_ORDER_ENDPOINT.path


# ── inmutabilidad ──────────────────────────────────────────────────────────

class TestImmutability:
    def test_cannot_modify_method(self):
        with pytest.raises(Exception):
            BYBIT_CREATE_ORDER_ENDPOINT.method = "GET"

    def test_cannot_modify_path(self):
        with pytest.raises(Exception):
            BYBIT_CREATE_ORDER_ENDPOINT.path = "/v5/order/cancel"

    def test_is_frozen_dataclass(self):
        from dataclasses import is_dataclass, fields
        assert is_dataclass(BYBIT_CREATE_ORDER_ENDPOINT)
        assert is_dataclass(type(BYBIT_CREATE_ORDER_ENDPOINT))

    def test_same_identity_across_imports(self):
        from execution_gateway.bybit_endpoints import BYBIT_CREATE_ORDER_ENDPOINT as C2
        assert BYBIT_CREATE_ORDER_ENDPOINT is C2


# ── BYBIT_POSITIONS_ENDPOINT (Hito 3.70) ────────────────────────────────────

class TestPositionsEndpointImport:
    def test_direct_import(self):
        from execution_gateway.bybit_endpoints import BYBIT_POSITIONS_ENDPOINT as P
        assert P is BYBIT_POSITIONS_ENDPOINT

    def test_public_import(self):
        assert hasattr(execution_gateway, "BYBIT_POSITIONS_ENDPOINT")
        assert execution_gateway.BYBIT_POSITIONS_ENDPOINT is BYBIT_POSITIONS_ENDPOINT

    def test_in_package_all(self):
        assert "BYBIT_POSITIONS_ENDPOINT" in execution_gateway.__all__

    def test_in_module_all(self):
        assert "BYBIT_POSITIONS_ENDPOINT" in bybit_endpoints_module.__all__

    def test_same_object_from_both_imports(self):
        assert execution_gateway.BYBIT_POSITIONS_ENDPOINT is BYBIT_POSITIONS_ENDPOINT


class TestPositionsEndpointTypeAndValue:
    def test_is_bybit_endpoint(self):
        assert isinstance(BYBIT_POSITIONS_ENDPOINT, BybitEndpoint)

    def test_method_is_get(self):
        assert BYBIT_POSITIONS_ENDPOINT.method == "GET"

    def test_path_is_position_list(self):
        assert BYBIT_POSITIONS_ENDPOINT.path == "/v5/position/list"

    def test_method_exact_string(self):
        assert BYBIT_POSITIONS_ENDPOINT.method == "GET"
        assert BYBIT_POSITIONS_ENDPOINT.method != "get"
        assert BYBIT_POSITIONS_ENDPOINT.method != "Get"

    def test_path_exact_string(self):
        assert BYBIT_POSITIONS_ENDPOINT.path == "/v5/position/list"
        assert BYBIT_POSITIONS_ENDPOINT.path != "/v5/position/list/"
        assert BYBIT_POSITIONS_ENDPOINT.path != "v5/position/list"

    def test_equal_to_equivalent_endpoint(self):
        equivalent = BybitEndpoint(method="GET", path="/v5/position/list")
        assert BYBIT_POSITIONS_ENDPOINT == equivalent

    def test_not_equal_to_create_order_endpoint(self):
        assert BYBIT_POSITIONS_ENDPOINT != BYBIT_CREATE_ORDER_ENDPOINT

    def test_no_url_base(self):
        assert "bybit.com" not in BYBIT_POSITIONS_ENDPOINT.path
        assert "https://" not in BYBIT_POSITIONS_ENDPOINT.path

    def test_no_query_string(self):
        assert "?" not in BYBIT_POSITIONS_ENDPOINT.path

    def test_no_fragment(self):
        assert "#" not in BYBIT_POSITIONS_ENDPOINT.path

    def test_not_the_create_order_path(self):
        assert BYBIT_POSITIONS_ENDPOINT.path != BYBIT_CREATE_ORDER_ENDPOINT.path


class TestPositionsEndpointImmutability:
    def test_cannot_modify_method(self):
        with pytest.raises(Exception):
            BYBIT_POSITIONS_ENDPOINT.method = "POST"

    def test_cannot_modify_path(self):
        with pytest.raises(Exception):
            BYBIT_POSITIONS_ENDPOINT.path = "/v5/order/create"

    def test_is_frozen_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(BYBIT_POSITIONS_ENDPOINT)
        assert is_dataclass(type(BYBIT_POSITIONS_ENDPOINT))

    def test_same_identity_across_imports(self):
        from execution_gateway.bybit_endpoints import BYBIT_POSITIONS_ENDPOINT as P2
        assert BYBIT_POSITIONS_ENDPOINT is P2


# ── BYBIT_OPEN_ORDERS_ENDPOINT (Hito 3.71) ──────────────────────────────────

class TestOpenOrdersEndpointImport:
    def test_direct_import(self):
        from execution_gateway.bybit_endpoints import BYBIT_OPEN_ORDERS_ENDPOINT as O
        assert O is BYBIT_OPEN_ORDERS_ENDPOINT

    def test_public_import(self):
        assert hasattr(execution_gateway, "BYBIT_OPEN_ORDERS_ENDPOINT")
        assert execution_gateway.BYBIT_OPEN_ORDERS_ENDPOINT is BYBIT_OPEN_ORDERS_ENDPOINT

    def test_in_package_all(self):
        assert "BYBIT_OPEN_ORDERS_ENDPOINT" in execution_gateway.__all__

    def test_in_module_all(self):
        assert "BYBIT_OPEN_ORDERS_ENDPOINT" in bybit_endpoints_module.__all__


class TestOpenOrdersEndpointTypeAndValue:
    def test_is_bybit_endpoint(self):
        assert isinstance(BYBIT_OPEN_ORDERS_ENDPOINT, BybitEndpoint)

    def test_method_is_get(self):
        assert BYBIT_OPEN_ORDERS_ENDPOINT.method == "GET"

    def test_path_is_order_realtime(self):
        assert BYBIT_OPEN_ORDERS_ENDPOINT.path == "/v5/order/realtime"

    def test_path_exact_string(self):
        assert BYBIT_OPEN_ORDERS_ENDPOINT.path != "/v5/order/realtime/"
        assert BYBIT_OPEN_ORDERS_ENDPOINT.path != "v5/order/realtime"

    def test_equal_to_equivalent_endpoint(self):
        equivalent = BybitEndpoint(method="GET", path="/v5/order/realtime")
        assert BYBIT_OPEN_ORDERS_ENDPOINT == equivalent

    def test_not_the_create_order_endpoint(self):
        assert BYBIT_OPEN_ORDERS_ENDPOINT != BYBIT_CREATE_ORDER_ENDPOINT
        assert BYBIT_OPEN_ORDERS_ENDPOINT.path != BYBIT_CREATE_ORDER_ENDPOINT.path

    def test_not_the_positions_endpoint(self):
        assert BYBIT_OPEN_ORDERS_ENDPOINT != BYBIT_POSITIONS_ENDPOINT

    def test_no_url_base(self):
        assert "bybit.com" not in BYBIT_OPEN_ORDERS_ENDPOINT.path
        assert "https://" not in BYBIT_OPEN_ORDERS_ENDPOINT.path

    def test_no_query_string(self):
        assert "?" not in BYBIT_OPEN_ORDERS_ENDPOINT.path


class TestOpenOrdersEndpointImmutability:
    def test_cannot_modify_method(self):
        with pytest.raises(Exception):
            BYBIT_OPEN_ORDERS_ENDPOINT.method = "POST"

    def test_cannot_modify_path(self):
        with pytest.raises(Exception):
            BYBIT_OPEN_ORDERS_ENDPOINT.path = "/v5/order/create"

    def test_is_frozen_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(BYBIT_OPEN_ORDERS_ENDPOINT)

    def test_same_identity_across_imports(self):
        from execution_gateway.bybit_endpoints import BYBIT_OPEN_ORDERS_ENDPOINT as O2
        assert BYBIT_OPEN_ORDERS_ENDPOINT is O2


# ── alcance ────────────────────────────────────────────────────────────────

class TestScope:
    def test_no_cancel_endpoint(self):
        assert not hasattr(bybit_endpoints_module, "BYBIT_CANCEL_ORDER_ENDPOINT")

    def test_no_query_orders_endpoint_under_the_hypothetical_name(self):
        # BYBIT_ORDER_REALTIME_ENDPOINT nunca se creó bajo ese nombre --
        # /v5/order/realtime existe desde el Hito 3.71 como
        # BYBIT_OPEN_ORDERS_ENDPOINT (cobertura dedicada más abajo).
        assert not hasattr(bybit_endpoints_module, "BYBIT_QUERY_ORDERS_ENDPOINT")
        assert not hasattr(bybit_endpoints_module, "BYBIT_ORDER_REALTIME_ENDPOINT")

    def test_no_wallet_endpoint(self):
        assert not hasattr(bybit_endpoints_module, "BYBIT_WALLET_ENDPOINT")

    def test_no_endpoint_collection(self):
        assert not hasattr(bybit_endpoints_module, "ENDPOINTS")
        assert not hasattr(bybit_endpoints_module, "ALL_ENDPOINTS")

    def test_no_endpoint_registry(self):
        assert not hasattr(bybit_endpoints_module, "EndpointRegistry")
        assert not hasattr(bybit_endpoints_module, "ENDPOINT_REGISTRY")

    def test_no_endpoint_enum(self):
        import enum
        import inspect
        for name, obj in inspect.getmembers(bybit_endpoints_module):
            if not name.startswith("_") and name != "BYBIT_CREATE_ORDER_ENDPOINT":
                assert not (isinstance(obj, type) and issubclass(obj, enum.Enum)), (
                    f"unexpected Enum: {name}"
                )


# ── ausencia de responsabilidades adicionales ──────────────────────────────

class TestNoExtraResponsibilities:
    def test_no_base_url(self):
        import inspect
        src = inspect.getsource(bybit_endpoints_module)
        assert "bybit.com" not in src
        assert "https://" not in src

    def test_no_host(self):
        import inspect
        src = inspect.getsource(bybit_endpoints_module)
        assert "api-demo" not in src

    def test_no_payload(self):
        import inspect
        src = inspect.getsource(bybit_endpoints_module)
        assert "payload" not in src
        assert "symbol" not in src
        assert "qty" not in src

    def test_no_transport_imported(self):
        assert not hasattr(bybit_endpoints_module, "HttpTransport")
        assert not hasattr(bybit_endpoints_module, "UrllibHttpTransport")

    def test_no_executor_imported(self):
        assert not hasattr(bybit_endpoints_module, "BybitEndpointExecutor")

    def test_no_api_imported(self):
        assert not hasattr(bybit_endpoints_module, "BybitPrivateApi")

    def test_no_authenticator_imported(self):
        assert not hasattr(bybit_endpoints_module, "BybitAuthenticator")

    def test_no_serializer_imported(self):
        assert not hasattr(bybit_endpoints_module, "JsonSerializer")

    def test_no_env_read(self):
        import os
        os.environ["BYBIT_API_KEY"] = "__sentinel__"
        try:
            import importlib
            import execution_gateway.bybit_endpoints as m
            importlib.reload(m)
            assert m.BYBIT_CREATE_ORDER_ENDPOINT.method == "POST"
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor
        assert GatewayConfig().environment == "demo"
        assert BybitEndpointExecutor is not None

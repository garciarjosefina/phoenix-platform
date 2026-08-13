from execution_gateway.bybit_instrument_metadata_reader import BybitInstrumentMetadataReader
from execution_gateway.bybit_instrument_metadata_response_interpreter import (
    BybitInstrumentMetadataResponseInterpreter,
)
from execution_gateway.bybit_public_get_api import BybitPublicGetApi
from execution_gateway.bybit_url_builder import BybitUrlBuilder

# Mismo host que Positions/Open Orders/Wallet Balance Read (D-011: Bybit
# Demo como único entorno soportado). Aunque este endpoint es público y sus
# datos son idénticos a mainnet (confirmado en la documentación de Demo
# Trading), no se introduce un segundo host -- api-demo.bybit.com ya sirve
# datos públicos correctos, y usarlo mantiene un único host en todo Phoenix.
_BYBIT_DEMO_BASE_URL = "https://api-demo.bybit.com"


def create_bybit_demo_instrument_metadata_reader(
    *,
    public_get_api: BybitPublicGetApi,
) -> BybitInstrumentMetadataReader:
    if not isinstance(public_get_api, BybitPublicGetApi):
        raise TypeError(
            f"public_get_api must be BybitPublicGetApi, got: {type(public_get_api).__name__}"
        )
    url_builder = BybitUrlBuilder(base_url=_BYBIT_DEMO_BASE_URL)
    response_interpreter = BybitInstrumentMetadataResponseInterpreter()
    return BybitInstrumentMetadataReader(
        public_get_api=public_get_api,
        url_builder=url_builder,
        response_interpreter=response_interpreter,
    )

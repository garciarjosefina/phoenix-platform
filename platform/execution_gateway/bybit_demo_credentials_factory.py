from execution_gateway.credentials import BybitDemoCredentials


def create_bybit_demo_credentials(
    *,
    api_key: str,
    api_secret: str,
) -> BybitDemoCredentials:
    return BybitDemoCredentials(
        api_key=api_key,
        api_secret=api_secret,
    )

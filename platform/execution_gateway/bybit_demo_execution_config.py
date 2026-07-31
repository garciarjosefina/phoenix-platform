from dataclasses import dataclass, field

from execution_gateway.bybit_demo_credentials_factory import create_bybit_demo_credentials
from execution_gateway.bybit_recv_window_factory import create_bybit_recv_window_ms
from execution_gateway.http_timeout_factory import create_http_timeout_seconds


@dataclass(frozen=True)
class BybitDemoExecutionConfig:
    api_key: str
    api_secret: str = field(repr=False)
    recv_window_ms: int
    timeout_seconds: int | float

    def __post_init__(self) -> None:
        create_bybit_demo_credentials(api_key=self.api_key, api_secret=self.api_secret)
        create_bybit_recv_window_ms(recv_window_ms=self.recv_window_ms)
        create_http_timeout_seconds(timeout_seconds=self.timeout_seconds)

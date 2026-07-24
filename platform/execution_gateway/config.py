from dataclasses import dataclass

_VALID_ENVIRONMENTS = {"testnet", "mainnet"}


@dataclass(frozen=True)
class GatewayConfig:
    environment: str = "testnet"
    dry_run: bool = True
    timeout_seconds: int = 10

    def __post_init__(self) -> None:
        if self.environment not in _VALID_ENVIRONMENTS:
            raise ValueError(
                f"environment must be 'testnet' or 'mainnet', got: {self.environment!r}"
            )
        if self.timeout_seconds <= 0:
            raise ValueError(
                f"timeout_seconds must be > 0, got: {self.timeout_seconds}"
            )

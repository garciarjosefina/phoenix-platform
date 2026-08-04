from dataclasses import dataclass


@dataclass(frozen=True)
class SmokeTestResult:
    success: bool
    endpoint: str
    environment: str
    server_time: int | None = None
    account_type: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool):
            raise TypeError(f"success must be bool, got: {type(self.success).__name__}")

        if not isinstance(self.endpoint, str):
            raise TypeError(f"endpoint must be str, got: {type(self.endpoint).__name__}")
        if not self.endpoint or self.endpoint.isspace():
            raise ValueError("endpoint must not be empty or whitespace-only")

        if not isinstance(self.environment, str):
            raise TypeError(f"environment must be str, got: {type(self.environment).__name__}")
        if not self.environment or self.environment.isspace():
            raise ValueError("environment must not be empty or whitespace-only")

        if self.server_time is not None:
            if isinstance(self.server_time, bool) or not isinstance(self.server_time, int):
                raise TypeError(
                    f"server_time must be int or None, got: {type(self.server_time).__name__}"
                )
            if self.server_time < 0:
                raise ValueError(f"server_time must be >= 0, got: {self.server_time}")

        if self.account_type is not None and not isinstance(self.account_type, str):
            raise TypeError(
                f"account_type must be str or None, got: {type(self.account_type).__name__}"
            )

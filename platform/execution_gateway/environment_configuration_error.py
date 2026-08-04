class EnvironmentConfigurationError(Exception):
    def __init__(self, *, message: str) -> None:
        if not isinstance(message, str):
            raise TypeError(f"message must be str, got: {type(message).__name__}")
        if not message or message.isspace():
            raise ValueError("message must not be empty or whitespace-only")
        super().__init__(message)
        self.message = message

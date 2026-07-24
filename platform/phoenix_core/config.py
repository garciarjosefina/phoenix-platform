from dataclasses import dataclass

from phoenix_core import __version__


@dataclass(frozen=True)
class Config:
    environment: str = "development"
    debug: bool = False
    version: str = __version__


def get_config() -> Config:
    return Config()

from urllib.parse import urlparse


def create_bybit_demo_base_url(*, base_url: str) -> str:
    if not isinstance(base_url, str):
        raise TypeError(f"base_url must be str, got: {type(base_url).__name__}")
    if not base_url or base_url.isspace():
        raise ValueError("base_url must not be empty or whitespace-only")
    if not base_url.startswith("https://"):
        raise ValueError(f"base_url must start with 'https://', got: {base_url!r}")

    parsed = urlparse(base_url)
    if not parsed.netloc:
        raise ValueError(f"base_url must have a non-empty host, got: {base_url!r}")
    if parsed.path:
        raise ValueError(f"base_url must not contain a path, got: {base_url!r}")
    if parsed.query:
        raise ValueError(f"base_url must not contain a query string, got: {base_url!r}")
    if parsed.fragment:
        raise ValueError(f"base_url must not contain a fragment, got: {base_url!r}")

    return base_url

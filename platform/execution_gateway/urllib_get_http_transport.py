import urllib.request
from collections.abc import Mapping


class UrllibGetHttpTransport:
    def get(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> str:
        if not isinstance(url, str):
            raise TypeError(f"url must be str, got: {type(url).__name__}")
        if not url or url.isspace():
            raise ValueError("url must not be empty or whitespace-only")

        if not isinstance(headers, Mapping):
            raise TypeError(f"headers must be a Mapping, got: {type(headers).__name__}")
        for k, v in headers.items():
            if not isinstance(k, str):
                raise TypeError(f"header key must be str, got: {type(k).__name__}")
            if not isinstance(v, str):
                raise TypeError(f"header value must be str, got: {type(v).__name__}")

        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise TypeError(
                f"timeout_seconds must be int or float, got: {type(timeout_seconds).__name__}"
            )
        if timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be > 0, got: {timeout_seconds}")

        request = urllib.request.Request(url=url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read()
        return response_body.decode("utf-8")

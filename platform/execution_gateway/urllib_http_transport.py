import urllib.request


class UrllibHttpTransport:
    def post(
        self,
        *,
        url: str,
        headers: dict[str, str],
        body: str,
        timeout_seconds: float,
    ) -> str:
        if not isinstance(url, str):
            raise TypeError(f"url must be str, got: {type(url).__name__}")
        if not url or url.isspace():
            raise ValueError("url must not be empty or whitespace-only")

        if not isinstance(headers, dict):
            raise TypeError(f"headers must be dict, got: {type(headers).__name__}")
        for k, v in headers.items():
            if not isinstance(k, str):
                raise TypeError(f"header key must be str, got: {type(k).__name__}")
            if not isinstance(v, str):
                raise TypeError(f"header value must be str, got: {type(v).__name__}")

        if not isinstance(body, str):
            raise TypeError(f"body must be str, got: {type(body).__name__}")

        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise TypeError(
                f"timeout_seconds must be int or float, got: {type(timeout_seconds).__name__}"
            )
        if timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be > 0, got: {timeout_seconds}")

        encoded_body = body.encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=encoded_body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read()
        return response_body.decode("utf-8")

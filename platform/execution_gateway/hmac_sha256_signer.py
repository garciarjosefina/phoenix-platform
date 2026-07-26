import hashlib
import hmac


class HmacSha256Signer:
    def sign(self, *, secret: str, message: str) -> str:
        return hmac.new(
            secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

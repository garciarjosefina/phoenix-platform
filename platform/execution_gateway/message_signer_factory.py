from execution_gateway.hmac_sha256_signer import HmacSha256Signer


def create_message_signer() -> HmacSha256Signer:
    return HmacSha256Signer()

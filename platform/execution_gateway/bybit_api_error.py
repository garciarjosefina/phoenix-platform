class BybitApiError(Exception):
    def __init__(self, *, ret_code: int, ret_msg: str) -> None:
        if isinstance(ret_code, bool) or not isinstance(ret_code, int):
            raise TypeError(
                f"ret_code must be int, got: {type(ret_code).__name__}"
            )
        if not isinstance(ret_msg, str):
            raise TypeError(
                f"ret_msg must be str, got: {type(ret_msg).__name__}"
            )
        super().__init__(f"Bybit API error {ret_code}: {ret_msg}")
        self.ret_code = ret_code
        self.ret_msg = ret_msg

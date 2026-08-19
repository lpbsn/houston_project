class FcmSendError(Exception):
    def __init__(self, *, error_code: str, should_revoke: bool = False) -> None:
        self.error_code = error_code
        self.should_revoke = should_revoke
        super().__init__(error_code)

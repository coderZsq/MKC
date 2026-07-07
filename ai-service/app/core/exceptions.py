class APIException(Exception):  # noqa: N818
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ValidationException(APIException):
    def __init__(self, message: str = "参数校验失败") -> None:
        super().__init__("VALIDATION_ERROR", message, 400)

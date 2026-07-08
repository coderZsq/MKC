class APIException(Exception):  # noqa: N818
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ValidationException(APIException):
    def __init__(self, message: str = "参数校验失败") -> None:
        super().__init__("VALIDATION_ERROR", message, 400)


class AudioProcessingError(APIException):
    def __init__(self, message: str = "无法解析音频文件") -> None:
        super().__init__("INVALID_AUDIO", message, 400)


class ModelLoadError(APIException):
    def __init__(self, message: str = "ASR 模型不可用") -> None:
        super().__init__("MODEL_LOAD_ERROR", message, 503)


class AsrProcessingError(APIException):
    def __init__(self, message: str = "转录失败，请重试") -> None:
        super().__init__("ASR_FAILED", message, 500)

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


class SubtitleGenerationError(APIException):
    def __init__(
        self,
        code: str = "SUBTITLE_GENERATION_ERROR",
        message: str = "字幕生成失败",
        status_code: int = 500,
    ) -> None:
        super().__init__(code, message, status_code)


class TextCleaningError(APIException):
    def __init__(
        self,
        code: str = "TEXT_CLEANING_ERROR",
        message: str = "文本清洗失败",
        status_code: int = 500,
    ) -> None:
        super().__init__(code, message, status_code)


class PdfParseError(APIException):
    def __init__(self, message: str = "PDF 解析失败") -> None:
        super().__init__("PDF_PARSE_FAILED", message, 500)


class EncryptedPdfError(APIException):
    def __init__(self, message: str = "无法解析加密 PDF") -> None:
        super().__init__("ENCRYPTED_PDF", message, 400)


class CorruptPdfError(APIException):
    def __init__(self, message: str = "PDF 文件损坏") -> None:
        super().__init__("CORRUPT_PDF", message, 400)


class NoTextLayerError(APIException):
    def __init__(self, message: str = "PDF 无文本层，需要使用 OCR 处理") -> None:
        super().__init__("NO_TEXT_LAYER", message, 400)


class PdfNotFoundError(APIException):
    def __init__(self, message: str = "PDF 文件不存在") -> None:
        super().__init__("PDF_NOT_FOUND", message, 404)


class ParserUnavailableError(APIException):
    def __init__(self, message: str = "PDF 解析器不可用") -> None:
        super().__init__("PARSER_UNAVAILABLE", message, 503)


class OcrUnavailableError(APIException):
    def __init__(self, message: str = "OCR 引擎不可用") -> None:
        super().__init__("OCR_UNAVAILABLE", message, 503)


class OcrPageFailedError(APIException):
    def __init__(self, message: str = "某页 OCR 失败") -> None:
        super().__init__("OCR_PAGE_FAILED", message, 500)


class OcrNoTextError(APIException):
    def __init__(self, message: str = "无法识别文字") -> None:
        super().__init__("OCR_NO_TEXT", message, 400)

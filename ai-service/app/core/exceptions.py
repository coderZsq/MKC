class APIException(Exception):  # noqa: N818
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ValidationException(APIException):
    def __init__(self, message: str = "参数校验失败") -> None:
        super().__init__("VALIDATION_ERROR", message, 400)


class InvalidRequestError(APIException):
    """Hybrid retrieval request failed structural validation (missing/invalid fields)."""

    def __init__(self, message: str = "请求参数无效") -> None:
        super().__init__("INVALID_REQUEST", message, 400)


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


class InvalidChunkingStrategyError(APIException):
    def __init__(self, strategy: str) -> None:
        super().__init__(
            "INVALID_STRATEGY",
            f"不支持的分块策略: {strategy}",
            400,
        )


class EmptyTextError(APIException):
    def __init__(self, message: str = "输入文本为空") -> None:
        super().__init__("EMPTY_TEXT", message, 400)


class ChunkingError(APIException):
    def __init__(self, message: str = "分块内部错误") -> None:
        super().__init__("CHUNKING_ERROR", message, 500)


class EmptyBatchError(APIException):
    def __init__(self, message: str = "输入批次为空") -> None:
        super().__init__("EMPTY_BATCH", message, 400)


class EmbeddingAuthenticationError(APIException):
    def __init__(self, message: str = "Embedding 认证失败") -> None:
        super().__init__("EMBEDDING_AUTH_FAILED", message, 401)


class EmbeddingUnavailableError(APIException):
    def __init__(self, message: str = "Embedding 服务不可用") -> None:
        super().__init__("EMBEDDING_UNAVAILABLE", message, 503)


class EmbeddingInternalError(APIException):
    def __init__(self, message: str = "Embedding 内部错误") -> None:
        super().__init__("EMBEDDING_INTERNAL_ERROR", message, 500)


class DimensionMismatchError(APIException):
    def __init__(self, message: str = "向量维度与配置不符") -> None:
        super().__init__("DIMENSION_MISMATCH", message, 500)


class EmbeddingProviderError(APIException):
    def __init__(self, message: str = "不支持的 Embedding Provider") -> None:
        super().__init__("EMBEDDING_PROVIDER_ERROR", message, 400)


class VectorStoreError(APIException):
    def __init__(self, message: str = "向量存储操作失败") -> None:
        super().__init__("VECTOR_STORE_ERROR", message, 500)


class VectorStoreUnavailableError(APIException):
    def __init__(self, message: str = "向量存储服务不可用") -> None:
        super().__init__("VECTOR_STORE_UNAVAILABLE", message, 503)


class VectorStoreConfigError(APIException):
    def __init__(self, message: str = "向量存储配置错误") -> None:
        super().__init__("VECTOR_STORE_CONFIG_ERROR", message, 400)


class RetrievalForbiddenError(APIException):
    def __init__(self, message: str = "无权访问资源") -> None:
        super().__init__("FORBIDDEN", message, 403)


class RetrievalUnavailableError(APIException):
    def __init__(self, message: str = "检索服务不可用") -> None:
        super().__init__("RETRIEVAL_UNAVAILABLE", message, 503)


class LLMAuthFailedError(APIException):
    def __init__(self, message: str = "LLM 认证失败") -> None:
        super().__init__("LLM_AUTH_FAILED", message, 401)


class LLMUnavailableError(APIException):
    def __init__(self, message: str = "LLM 服务不可用") -> None:
        super().__init__("LLM_UNAVAILABLE", message, 503)


class LLMStreamError(APIException):
    def __init__(self, message: str = "流式输出中断") -> None:
        super().__init__("LLM_STREAM_ERROR", message, 500)


class LLMTimeoutError(APIException):
    def __init__(self, message: str = "LLM 调用超时") -> None:
        super().__init__("LLM_TIMEOUT", message, 504)

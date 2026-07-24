from flask import Flask, Response

from app.agent.tools import WebSearchTool
from app.agent.tools.web_search_config import build_web_search_config
from app.api.agent import agent_bp
from app.api.asr import asr_bp
from app.api.chunking import chunking_bp
from app.api.embedding import embedding_bp
from app.api.extraction import extraction_bp
from app.api.health import health_bp
from app.api.hybrid_retrieval import hybrid_retrieval_bp
from app.api.internal import internal_bp
from app.api.llm import llm_bp
from app.api.pdf import pdf_bp
from app.api.qa import qa_bp
from app.api.retrieval import retrieval_bp
from app.api.summary import summary_bp
from app.api.vectors import vectors_bp
from app.api.web_search import web_search_bp
from app.core.config import settings
from app.core.exceptions import APIException
from app.core.logger import get_logger
from app.core.response import make_response
from app.middleware.logging import init_request_logging
from app.middleware.request_id import init_request_id
from app.observability.metrics import init_metrics
from app.observability.tracing import init_tracing
from app.services.citation_formatter import CitationFormatter
from app.services.citation_service import CitationService
from app.services.citation_validator import CitationValidator
from app.services.embedding.factory import (
    build_embedding_service,
    validate_embedding_config,
)
from app.services.embedding.service import EmbeddingService
from app.services.extraction import (
    EntityResolver,
    ExtractionRepository,
    ExtractionService,
    LLMExtractionProvider,
    RuleExtractionProvider,
    TagNormalizer,
)
from app.services.hybrid_retrieval import (
    HybridRetrievalService,
    build_hybrid_retrieval_service,
)
from app.services.llm import LLMClient, build_llm_client, validate_llm_config
from app.services.memory import MemoryService, build_memory_config, build_memory_service
from app.services.rag_engine.engine import RagEngine
from app.services.rag_engine.factory import build_rag_engine
from app.services.retrieval import RetrievalService, build_retrieval_service
from app.services.summary import (
    MapReduceSummarizer,
    SectionSplitter,
    SummaryLLMProvider,
    SummaryRepository,
    SummaryService,
)
from app.vector_store.factory import build_vector_store
from app.vector_store.vector_store import VectorStore
from celery_workers.celery_app import celery_app

logger = get_logger(__name__)


def create_app(
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStore | None = None,
    retrieval_service: RetrievalService | None = None,
    hybrid_retrieval_service: HybridRetrievalService | None = None,
    rag_engine: RagEngine | None = None,
    llm_client: LLMClient | None = None,
    memory_service: MemoryService | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.from_object(settings)
    app.config["AI_CONFIG"] = settings.ai_config

    init_extensions(
        app,
        embedding_service=embedding_service,
        vector_store=vector_store,
        retrieval_service=retrieval_service,
        hybrid_retrieval_service=hybrid_retrieval_service,
        rag_engine=rag_engine,
        llm_client=llm_client,
        memory_service=memory_service,
    )
    init_tracing(app)
    init_metrics(app)
    init_request_id(app)
    init_request_logging(app)
    register_blueprints(app)
    register_error_handlers(app)

    return app


def init_extensions(
    app: Flask,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStore | None = None,
    retrieval_service: RetrievalService | None = None,
    hybrid_retrieval_service: HybridRetrievalService | None = None,
    rag_engine: RagEngine | None = None,
    llm_client: LLMClient | None = None,
    memory_service: MemoryService | None = None,
) -> None:
    if embedding_service is not None:
        app.extensions["embedding"] = embedding_service
    else:
        validate_embedding_config()
        app.extensions["embedding"] = build_embedding_service()

    if vector_store is not None:
        app.extensions["vector_store"] = vector_store
    else:
        app.extensions["vector_store"] = build_vector_store()

    if retrieval_service is not None:
        app.extensions["retrieval"] = retrieval_service
    else:
        app.extensions["retrieval"] = build_retrieval_service(
            app.extensions["embedding"],
            app.extensions["vector_store"],
        )

    if rag_engine is not None:
        app.extensions["rag_engine"] = rag_engine
    else:
        app.extensions["rag_engine"] = build_rag_engine(
            retrieval_service=app.extensions["retrieval"],
            embedding_service=app.extensions["embedding"],
            vector_store=app.extensions["vector_store"],
        )

    if hybrid_retrieval_service is not None:
        app.extensions["hybrid_retrieval"] = hybrid_retrieval_service
    else:
        app.extensions["hybrid_retrieval"] = build_hybrid_retrieval_service(
            app.extensions["embedding"],
            app.extensions["vector_store"],
        )

    if llm_client is not None:
        app.extensions["llm"] = llm_client
    else:
        validate_llm_config()
        app.extensions["llm"] = build_llm_client()

    if memory_service is not None:
        app.extensions["memory_service"] = memory_service
    else:
        app.extensions["memory_service"] = build_memory_service(
            app.extensions["embedding"],
            app.extensions["vector_store"],
            config=build_memory_config(),
        )

    citation_cfg = (settings.ai_config or {}).get("citation", {})
    app.extensions["citation_service"] = CitationService(
        formatter=CitationFormatter(
            marker_pattern=citation_cfg.get("marker_pattern", r"\[\^(\d+)\]"),
            snippet_max_chars=int(citation_cfg.get("snippet_max_chars", 200)),
        ),
        validator=CitationValidator(
            max_citations=int(citation_cfg.get("max_citations", 8)),
            log_dropped=bool(citation_cfg.get("log_dropped", True)),
        ),
    )

    summary_cfg = (settings.ai_config or {}).get("summary", {})
    summary_llm_provider = SummaryLLMProvider(app.extensions["llm"], summary_cfg)
    app.extensions["summary_service"] = SummaryService(
        llm_provider=summary_llm_provider,
        summarizer=MapReduceSummarizer(summary_llm_provider, summary_cfg),
        splitter=SectionSplitter(),
        repository=SummaryRepository(),
        config=summary_cfg,
    )

    extraction_cfg = (settings.ai_config or {}).get("extraction", {})
    app.extensions["extraction_service"] = ExtractionService(
        llm_provider=LLMExtractionProvider(app.extensions["llm"], extraction_cfg),
        rule_provider=RuleExtractionProvider(),
        tag_normalizer=TagNormalizer(extraction_cfg.get("tags", {})),
        entity_resolver=EntityResolver(),
        repository=ExtractionRepository(),
        config=extraction_cfg,
    )

    app.extensions["web_search_tool"] = WebSearchTool(
        config=build_web_search_config((settings.ai_config or {}).get("web_search", {}))
    )

    celery_app.conf.update(
        broker_url=settings.celery_broker_url,
        result_backend=settings.celery_result_backend,
        timezone="Asia/Shanghai",
        enable_utc=True,
    )


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(internal_bp, url_prefix="/api/v1/internal")
    app.register_blueprint(asr_bp, url_prefix="/ai/v1")
    app.register_blueprint(pdf_bp, url_prefix="/ai/v1")
    app.register_blueprint(chunking_bp, url_prefix="/ai/v1")
    app.register_blueprint(embedding_bp, url_prefix="/ai/v1")
    app.register_blueprint(vectors_bp, url_prefix="/ai/v1")
    app.register_blueprint(retrieval_bp, url_prefix="/ai/v1")
    app.register_blueprint(hybrid_retrieval_bp, url_prefix="/ai/v1")
    app.register_blueprint(summary_bp, url_prefix="/ai/v1")
    app.register_blueprint(extraction_bp, url_prefix="/ai/v1")
    app.register_blueprint(llm_bp, url_prefix="/ai/v1")
    app.register_blueprint(qa_bp, url_prefix="/ai/v1")
    app.register_blueprint(agent_bp, url_prefix="/ai/v1")
    app.register_blueprint(web_search_bp, url_prefix="/ai/v1")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(APIException)
    def handle_api_exception(error: APIException) -> tuple[Response, int]:
        logger.warning("API error handled code=%s", error.code)
        return make_response(
            success=False,
            error={"code": error.code, "message": error.message},
            status=error.status_code,
        )

    @app.errorhandler(404)
    def handle_not_found(_: Exception) -> tuple[Response, int]:
        logger.warning("API error handled code=NOT_FOUND")
        return make_response(
            success=False,
            error={"code": "NOT_FOUND", "message": "资源不存在"},
            status=404,
        )

    @app.errorhandler(Exception)
    def handle_generic_exception(error: Exception) -> tuple[Response, int]:
        logger.exception("API error handled code=INTERNAL_ERROR: %s", error.__class__.__name__)
        return make_response(
            success=False,
            error={"code": "INTERNAL_ERROR", "message": "服务器内部错误"},
            status=500,
        )

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ai-service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks",
        "celery_workers.tasks.asr_task",
        "celery_workers.tasks.pdf_parse_task",
        "celery_workers.tasks.summarize_task",
        "celery_workers.tasks.extract_tags_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.transcribe.*": {"queue": "transcribe"},
        "app.tasks.parse_pdf.*": {"queue": "parse_pdf"},
        "app.tasks.embed.*": {"queue": "embed"},
        "app.tasks.rag.*": {"queue": "rag"},
        "celery_workers.tasks.asr_task.*": {"queue": "transcribe"},
        "celery_workers.tasks.pdf_parse_task.*": {"queue": "parse_pdf"},
        "celery_workers.tasks.summarize_task.*": {"queue": "rag"},
        "celery_workers.tasks.extract_tags_task.*": {"queue": "rag"},
    },
)

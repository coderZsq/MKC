from app.tasks import sample
from celery_workers.celery_app import celery_app as celery

__all__ = ["celery", "sample"]

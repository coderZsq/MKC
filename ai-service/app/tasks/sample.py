from celery_workers.celery_app import celery_app as celery


@celery.task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def hello(name: str) -> str:
    return f"Hello, {name}!"

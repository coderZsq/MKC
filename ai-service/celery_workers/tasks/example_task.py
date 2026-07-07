import time
from typing import Any

from celery_workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def example_task(self: Any, name: str) -> str:
    try:
        for i in range(5):
            self.update_state(
                state="PROGRESS",
                meta={"current": i + 1, "total": 5},
            )
            time.sleep(1)
        return f"Hello, {name}!"
    except Exception as exc:
        raise self.retry(exc=exc)  # noqa: B904

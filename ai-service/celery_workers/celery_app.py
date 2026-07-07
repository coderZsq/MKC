from celery import Celery

# Sprint 0 占位：真实配置在 config 加载后注入
celery_app = Celery("ai-service")


@celery_app.task
def add(x: int, y: int) -> int:
    return x + y

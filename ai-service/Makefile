.PHONY: install format lint test worker flower run build

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

format:
	black app celery_workers tests
	ruff check --fix app celery_workers tests

lint:
	ruff check app celery_workers tests
	mypy app

test:
	pytest --cov=app --cov-report=term-missing

worker:
	celery -A celery_workers.celery_app worker -l info -Q default,transcribe,parse_pdf,embed,rag

flower:
	celery -A celery_workers.celery_app flower --port=5555

run:
	flask --app app.main:create_app run --host=0.0.0.0 --port=5000 --debug

build:
	docker build -t mkc-ai-service:latest .

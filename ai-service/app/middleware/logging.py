from flask import Flask, Response, request

from app.core.logger import get_logger

logger = get_logger(__name__)


def init_request_logging(app: Flask) -> None:
    @app.before_request
    def log_request() -> None:
        logger.info("request started %s %s", request.method, request.path)

    @app.after_request
    def log_response(response: Response) -> Response:
        logger.info(
            "request completed %s %s %s",
            request.method,
            request.path,
            response.status_code,
        )
        return response

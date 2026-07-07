import uuid

from flask import Flask, Response, g, request


def init_request_id(app: Flask) -> None:
    @app.before_request
    def set_request_id() -> None:
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    @app.after_request
    def add_request_id_header(response: Response) -> Response:
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        return response

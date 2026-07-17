import logging
import sys

from flask import g, has_request_context

from app.core.config import settings


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = getattr(g, "request_id", None) if has_request_context() else None
        trace_id = getattr(g, "trace_id", None) if has_request_context() else None
        record.request_id = request_id if request_id else ""
        record.trace_id = trace_id if trace_id else ""
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                (
                    '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
                    '"request_id":"%(request_id)s","trace_id":"%(trace_id)s","logger":"%(name)s",'
                    '"message":"%(message)s"}'
                ),
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        handler.addFilter(_RequestIdFilter())
        logger.addHandler(handler)

    return logger

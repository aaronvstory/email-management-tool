import logging
from logging import Logger

_DEF_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

class _Formatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Minimal structured fields; avoid leaking sensitive data
        record.message = record.getMessage()
        return super().format(record)

def setup_app_logging(app) -> None:
    """Attach a sane formatter/handler to Flask app.logger if none present.
    Keeps it lightweight and avoids duplicate handlers.
    """
    try:
        logger: Logger = app.logger  # type: ignore
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            handler.setFormatter(_Formatter(_DEF_FORMAT))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
    except Exception:
        pass

__all__ = ["setup_app_logging"]

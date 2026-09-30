"""Логирование с маскированием секретов. Используется всеми модулями через get_logger."""

import logging
import re

_SENSITIVE = re.compile(
    r"(?i)(password|passwd|secret|token|authorization|api[_-]?key)(\"?\s*[:=]\s*\"?)([^\s\",]+)"
)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _SENSITIVE.sub(r"\1\2***", str(record.msg))
        if record.args:
            record.args = tuple(_SENSITIVE.sub(r"\1\2***", str(a)) for a in record.args)
        return True


def setup_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

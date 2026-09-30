"""Логирование с маскированием секретов. Используется всеми модулями через get_logger."""

import logging
import re

_SENSITIVE = re.compile(
    r"(?i)(password|passwd|secret|token|authorization|api[_-]?key)(\"?\s*[:=]\s*\"?)([^\s\",]+)"
)


def _redact(text: str) -> str:
    return _SENSITIVE.sub(r"\1\2***", text)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(str(record.msg))
        if isinstance(record.args, tuple):
            # маскируем только строки: числа и объекты должны сохранить тип для %d/%s
            record.args = tuple(_redact(a) if isinstance(a, str) else a for a in record.args)
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

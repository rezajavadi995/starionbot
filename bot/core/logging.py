import logging
from collections.abc import MutableMapping
from logging.handlers import RotatingFileHandler
from typing import Any

import structlog

SENSITIVE_KEYS = {"token", "secret", "password", "key", "session", "authorization"}


def _mask_sensitive(
    _: Any,
    __: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    for key, value in list(event_dict.items()):
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            event_dict[key] = "***MASKED***"
        elif isinstance(value, str) and len(value) > 20 and "_" in key.lower():
            event_dict[key] = "***MASKED***"

    return event_dict


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO)

    handler = RotatingFileHandler(
        "logs/starionbot.log",
        maxBytes=2_000_000,
        backupCount=5,
    )

    logging.getLogger().addHandler(handler)

    structlog.configure(
        processors=[
            _mask_sensitive,
            structlog.processors.JSONRenderer(),
        ]
    )

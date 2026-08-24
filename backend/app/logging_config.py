"""Unified logging setup for the fetch → notify pipeline.

Every log record produced along the path that pulls articles from RSSHub
(Zhihu etc.) and pushes notifications to WeClawBot lands in the same files:

- ``logs/error.log`` — every ERROR+ record from the whole pipeline, plus the
  full traceback for exceptions. This is the single file to grep for failures.
- ``logs/app.log`` — full INFO+ history for tracing a run end to end.
- console — mirror, so ``docker logs`` / local dev output stays usable.

Paths are relative to the process working directory (``/app`` inside the
Docker image, ``backend/`` in local dev) and can be overridden via ``LOG_DIR``.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import settings

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Rotation: 5MB per file, keep the last 3, so a long-running service never
# grows a single unbounded file on disk.
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3

_configured = False


def setup_logging() -> None:
    """Configure the root logger once. Safe to call from multiple entrypoints."""
    global _configured
    if _configured:
        return
    _configured = True

    log_dir = settings.log_dir
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    # Console mirror
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # Unified error file: all ERROR+ from the pipeline, errors only.
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)

    # General log: full INFO+ history for tracing a run.
    app_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    root.addHandler(app_handler)

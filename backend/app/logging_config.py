"""Unified logging setup for the fetch → notify pipeline.

Every log record produced along the path that pulls articles from RSSHub
(Zhihu etc.) and pushes notifications to WeClawBot lands in the same files:

- ``logs/error.log`` — every ERROR+ record from the whole pipeline, plus the
  full traceback for exceptions. This is the single file to grep for failures.
- ``logs/app.log`` — full INFO+ history for tracing a run end to end.
- console — mirror, so ``docker logs`` / local dev output stays usable.

Paths are relative to the process working directory (``/app`` inside the
Docker image, ``backend/`` in local dev) and can be overridden via ``LOG_DIR``.

File writing is best-effort: if the log directory can't be created or the files
can't be opened (e.g. a container bind mount the non-root user can't write),
setup falls back to console-only so logging can never take the app down.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.config import settings

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Rotation: 5MB per file, keep the last 3, so a long-running service never
# grows a single unbounded file on disk.
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3

_configured = False


def _add_file_handler(root: logging.Logger, path: str, level: int, formatter: logging.Formatter) -> None:
    handler = RotatingFileHandler(path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    root.addHandler(handler)


def setup_logging() -> None:
    """Configure the root logger once. Safe to call from multiple entrypoints."""
    global _configured
    if _configured:
        return
    _configured = True

    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    # Console mirror
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        os.makedirs(settings.log_dir, exist_ok=True)
        # Unified error file: all ERROR+ from the pipeline, errors only.
        _add_file_handler(root, os.path.join(settings.log_dir, "error.log"), logging.ERROR, formatter)
        # General log: full INFO+ history for tracing a run.
        _add_file_handler(root, os.path.join(settings.log_dir, "app.log"), logging.INFO, formatter)
    except OSError as e:
        # PermissionError / read-only mount etc. — degrade to console only rather
        # than crash startup (setup_logging runs at import time in the app).
        print(
            f"[logging] cannot write log files to '{settings.log_dir}': {e} "
            f"— continuing with console output only",
            file=sys.stderr,
        )

"""Shared logging configuration for ITBench.

CLI entry points call ``configure_logging()`` to install the Rich handler.
Library-level modules should NOT call this — they follow the stdlib convention
of adding only a NullHandler at import time so that callers (and pytest's
caplog fixture) remain in full control of handler configuration.
"""
import logging

from rich.logging import RichHandler


def configure_logging(level: int = logging.INFO) -> None:
    """Install RichHandler on the root logger. Call once per process entry point."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                show_path=False,
                log_time_format="[%X]",
            )
        ],
        force=True,
    )

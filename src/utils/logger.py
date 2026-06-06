"""
AI Cinematic Story Narrator
Structured logger using Rich for beautiful terminal output.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

_THEME = Theme(
    {
        "info": "bold cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "scene": "bold magenta",
        "audio": "bold blue",
    }
)

console = Console(theme=_THEME)


def get_logger(name: str, level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    """
    Returns a configured logger with Rich console handler and optional file handler.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    rich_handler.setLevel(logger.level)
    logger.addHandler(rich_handler)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logger.level)
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def log_banner(title: str, subtitle: str = "") -> None:
    """Print a styled section banner to the console."""
    console.rule(f"[bold cyan]{title}[/bold cyan]")
    if subtitle:
        console.print(f"  [dim]{subtitle}[/dim]\n")

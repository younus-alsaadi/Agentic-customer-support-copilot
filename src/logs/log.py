from __future__ import annotations
import logging
from logging import Logger, FileHandler
from pathlib import Path
from datetime import datetime
import re
import traceback

from pathlib import Path
DEFAULT_LOG_DIR = Path(__file__).resolve().parent / "logs"

def _safe_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9._-]", "", name)
    return name or "app"

class DatedLogger:
    def __init__(
            self,
            base_name: str="LichtBlick_case_study",
            directory: str | Path = DEFAULT_LOG_DIR,
            level: int = logging.INFO,
            date_format: str = "%Y-%m-%d",
            encoding: str = "utf-8",
            time_format: str = "%Y-%m-%d %H:%M:%S",
    ):
        self.base_name = _safe_name(base_name)
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.date_format = date_format
        self.encoding = encoding
        self.time_format = time_format

        # a stable logger name per (date, base_name) to avoid duplicate handlers
        self._current_date = self._today()
        self.logger: Logger = logging.getLogger(f"dated.{self._current_date}.{self.base_name}")
        self.logger.setLevel(logging.DEBUG)  # let handlers filter
        self.logger.propagate = False

        # clear any inherited handlers for this name
        for h in list(self.logger.handlers):
            self.logger.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass

        self._setup_handlers(level)

    def debug(self, msg: str, *args, **kwargs):
        self._ensure_today()
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._ensure_today()
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._ensure_today()
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._ensure_today()
        # goes to both the main logs and the error file (because of handler levels)
        self.logger.error(msg, *args, **kwargs)

    def exception(self, msg: str = "Unhandled exception", *args, **kwargs):
        """
        Log an ERROR with traceback; call inside except blocks.
        """
        self._ensure_today()
        self.logger.exception(msg, *args, **kwargs)

    def log(self, level: int, msg: str, *args, **kwargs):
        self._ensure_today()
        self.logger.log(level, msg, *args, **kwargs)

    def paths(self) -> tuple[Path, Path]:
        """(main_log_path, error_log_path) for today's files."""
        d = self._today()
        return (self._log_path(d), self._err_path(d))

    def _today(self) -> str:
        return datetime.now().strftime(self.date_format)

    def _log_path(self, date_str: str) -> Path:
        return self.directory / f"{date_str}_{self.base_name}.logs"

    def _err_path(self, date_str: str) -> Path:
        return self.directory / f"{date_str}_{self.base_name}.error.logs"

    def _setup_handlers(self, info_level: int):
        fmt = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(message)s",
            datefmt=self.time_format,
        )

        info_file = self._log_path(self._current_date)
        err_file = self._err_path(self._current_date)

        info_handler = FileHandler(info_file, encoding=self.encoding)
        info_handler.setLevel(info_level)  # e.g., INFO
        info_handler.setFormatter(fmt)

        err_handler = FileHandler(err_file, encoding=self.encoding)
        err_handler.setLevel(logging.ERROR)  # only ERROR and above
        err_handler.setFormatter(fmt)

        self.logger.addHandler(info_handler)
        self.logger.addHandler(err_handler)

    def _ensure_today(self):
        today = self._today()
        if today != self._current_date:
            # swap handlers to new date-stamped files
            for h in list(self.logger.handlers):
                self.logger.removeHandler(h)
                try:
                    h.close()
                except Exception:
                    pass
            self._current_date = today
            self._setup_handlers(info_level=self.logger.handlers[0].level if self.logger.handlers else logging.INFO)


def build_logger(
        base_name: str = "LichtBlick_case_study",
        directory: str | Path = DEFAULT_LOG_DIR,
        level: int = logging.INFO,
        date_format: str = "%Y-%m-%d",
        encoding: str = "utf-8",
        time_format: str = "%Y-%m-%d %H:%M:%S",
) -> DatedLogger:
    """
    Return a ready-to-use DatedLogger.
    Keeps a stable name per (date, base_name) to avoid duplicate handlers.
    """
    return DatedLogger(
        base_name=base_name,
        directory=directory,
        level=level,
        date_format=date_format,
        encoding=encoding,
        time_format=time_format,
    )


# if __name__ == "__main__":
#     logs = build_logger()
#
#     logs.info("Service starting")
#     logs.debug("Some debug detail")  # will be filtered out at INFO level
#     logs.warning("Low disk space warning")
#
#     try:
#         1 / 0
#     except Exception:
#         logs.exception("Crash in main loop")
#
#     print("Log files:", *logs.paths())
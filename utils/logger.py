"""
logger.py

Central logging utilities for GeoNode Connector.

This module provides a single logging interface for the entire plugin.
All modules should import the logger from here instead of creating
their own logger instances.

Features
--------
- Compatible with QGIS 3.28+
- Compatible with Python 3.10+
- Automatic log directory creation
- File logging
- Console logging (optional)
- Prevent duplicate handlers
"""

import logging
import os
from typing import Optional

from qgis.core import QgsApplication

from .config import (
    LOG_FILENAME,
    LOG_FORMAT,
    LOG_LEVEL,
    PLUGIN_NAME,
)

# =============================================================================
# Log Directory
# =============================================================================

LOG_DIR = os.path.join(
    QgsApplication.qgisSettingsDirPath(),
    PLUGIN_NAME.replace(" ", "")
)

os.makedirs(
    LOG_DIR,
    exist_ok=True,
)

LOG_FILE = os.path.join(
    LOG_DIR,
    LOG_FILENAME,
)

# =============================================================================
# Root Logger
# =============================================================================

ROOT_LOGGER_NAME = PLUGIN_NAME.replace(" ", "")

_root_logger = logging.getLogger(ROOT_LOGGER_NAME)

if not _root_logger.handlers:

    _root_logger.propagate = False

    level = getattr(
        logging,
        LOG_LEVEL.upper(),
        logging.INFO,
    )

    _root_logger.setLevel(level)

        # -----------------------------------------------------------------
    # Formatter
    # -----------------------------------------------------------------

    formatter = logging.Formatter(LOG_FORMAT)

    # -----------------------------------------------------------------
    # File Handler
    # -----------------------------------------------------------------

    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8",
    )

    file_handler.setLevel(level)

    file_handler.setFormatter(formatter)

    _root_logger.addHandler(file_handler)

    # -----------------------------------------------------------------
    # Console Handler
    #
    # Sangat membantu ketika plugin dijalankan
    # menggunakan Plugin Reloader atau saat debugging.
    # -----------------------------------------------------------------

    console_handler = logging.StreamHandler()

    console_handler.setLevel(level)

    console_handler.setFormatter(formatter)

    _root_logger.addHandler(console_handler)

    # =============================================================================
    # Public API
    # =============================================================================

    def get_logger(
        name: Optional[str] = None,
    ) -> logging.Logger:
        """
        Return a logger instance.

        Parameters
        ----------
        name : Optional[str]
            Module name.

        Returns
        -------
        logging.Logger
        """

        if not name:
            return _root_logger

        return logging.getLogger(
            "{}.{}".format(
                ROOT_LOGGER_NAME,
                name,
            )
        )


    def set_level(level: str) -> None:
        """
        Change logger level dynamically.

        Parameters
        ----------
        level : str
            DEBUG, INFO, WARNING, ERROR, CRITICAL
        """

        log_level = getattr(
            logging,
            level.upper(),
            logging.INFO,
        )

        _root_logger.setLevel(log_level)

        for handler in _root_logger.handlers:
            handler.setLevel(log_level)


    def log_exception(
        message: str,
    ) -> None:
        """
        Log current exception with traceback.
        """

        _root_logger.exception(message)


    # =============================================================================
    # Backward Compatibility
    # =============================================================================

    logger = get_logger()
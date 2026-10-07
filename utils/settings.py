"""
settings.py

Persistent plugin settings using QgsSettings.

All application preferences are stored under the
GeoNode Connector settings group.
"""

from typing import Any, Dict, Optional

from qgis.core import QgsSettings

from .config import (
    SETTINGS_GROUP,
    SETTING_SERVER,
    SETTING_USERNAME,
    SETTING_REMEMBER,
    SETTING_VERIFY_SSL,
    SETTING_TIMEOUT,
)

from .logger import get_logger


logger = get_logger(__name__)


class PluginSettings:
    """
    Wrapper around QgsSettings.

    Provides a centralized API for reading and writing
    plugin configuration.
    """

    _settings = QgsSettings()

    # ==============================================================
    # Internal Helper
    # ==============================================================

    @classmethod
    def _key(
        cls,
        key: str,
    ) -> str:

        return f"{SETTINGS_GROUP}/{key}"

    # ==============================================================
    # Basic API
    # ==============================================================

    @classmethod
    def set_value(
        cls,
        key: str,
        value: Any,
    ) -> None:

        logger.debug(
            "Saving setting '%s'.",
            key,
        )

        cls._settings.setValue(
            cls._key(key),
            value,
        )

    @classmethod
    def get_value(
        cls,
        key: str,
        default: Optional[Any] = None,
    ) -> Any:

        return cls._settings.value(
            cls._key(key),
            default,
        )

    @classmethod
    def contains(
        cls,
        key: str,
    ) -> bool:

        return cls._settings.contains(
            cls._key(key),
        )

    @classmethod
    def remove(
        cls,
        key: str,
    ) -> None:

        logger.debug(
            "Removing setting '%s'.",
            key,
        )

        cls._settings.remove(
            cls._key(key),
        )

    @classmethod
    def clear(cls) -> None:
        """
        Remove all plugin settings.
        """

        logger.info(
            "Clearing plugin settings."
        )

        cls._settings.remove(
            SETTINGS_GROUP,
        )

    # ==============================================================
    # Login Settings
    # ==============================================================

    @classmethod
    def save_login(
        cls,
        server: str,
        username: str,
        remember: bool,
    ) -> None:

        cls.set_value(
            SETTING_SERVER,
            server,
        )

        cls.set_value(
            SETTING_USERNAME,
            username,
        )

        cls.set_value(
            SETTING_REMEMBER,
            remember,
        )

    @classmethod
    def clear_login(cls) -> None:

        cls.remove(
            SETTING_SERVER,
        )

        cls.remove(
            SETTING_USERNAME,
        )

        cls.remove(
            SETTING_REMEMBER,
        )

    # ==============================================================
    # Shortcut
    # ==============================================================

    @classmethod
    def server_url(cls) -> str:

        return cls.get_value(
            SETTING_SERVER,
            "",
        )

    @classmethod
    def username(cls) -> str:

        return cls.get_value(
            SETTING_USERNAME,
            "",
        )

    @classmethod
    def remember(cls) -> bool:

        return bool(
            cls.get_value(
                SETTING_REMEMBER,
                False,
            )
        )

    @classmethod
    def verify_ssl(cls) -> bool:

        return bool(
            cls.get_value(
                SETTING_VERIFY_SSL,
                True,
            )
        )

    @classmethod
    def timeout(cls) -> int:

        return int(
            cls.get_value(
                SETTING_TIMEOUT,
                30,
            )
        )

    # ==============================================================
    # Export
    # ==============================================================

    @classmethod
    def all(cls) -> Dict[str, Any]:
        """
        Return current plugin settings.
        """

        return {

            "server": cls.server_url(),

            "username": cls.username(),

            "remember": cls.remember(),

            "verify_ssl": cls.verify_ssl(),

            "timeout": cls.timeout(),
        }
"""
validator.py

Validation utilities for GeoNode Connector.

This module centralizes common validation routines used
throughout the plugin.
"""

import re
from typing import Optional, Pattern
from urllib.parse import urlparse

from .logger import get_logger


logger = get_logger(__name__)


class Validator:
    """
    Common validation helper.
    """

    EMAIL_PATTERN: Pattern[str] = re.compile(
        r"^[\w\.-]+@[\w\.-]+\.\w+$"
    )

    # ==============================================================
    # URL
    # ==============================================================

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize GeoNode URL.

        - Trim whitespace
        - Add https:// if missing
        - Remove trailing slash
        """

        url = (url or "").strip()

        if not url:

            return ""

        if not url.startswith(
            (
                "http://",
                "https://",
            )
        ):

            url = "https://" + url

        return url.rstrip("/")

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format.
        """

        if not url:

            return False

        parsed = urlparse(url)

        return bool(
            parsed.scheme
            and parsed.netloc
        )

    # ==============================================================
    # Authentication
    # ==============================================================

    @staticmethod
    def validate_username(
        username: Optional[str],
    ) -> bool:
        """
        Validate username.
        """

        return not Validator.is_empty(
            username,
        )

    @staticmethod
    def validate_password(
        password: Optional[str],
    ) -> bool:
        """
        Validate password.
        """

        return bool(password)

    @staticmethod
    def validate_token(
        token: Optional[str],
    ) -> bool:
        """
        Validate OAuth access token.
        """

        return bool(
            token
            and len(token) > 10
        )

    # ==============================================================
    # General
    # ==============================================================

    @classmethod
    def validate_email(
        cls,
        email: Optional[str],
    ) -> bool:
        """
        Validate email address.
        """

        if cls.is_empty(email):

            return False

        return bool(
            cls.EMAIL_PATTERN.match(
                email.strip()
            )
        )

    @staticmethod
    def validate_positive_integer(
        value: object,
    ) -> bool:
        """
        Validate positive integer.
        """

        return (
            isinstance(value, int)
            and value > 0
        )

    @staticmethod
    def is_empty(
        value: Optional[str],
    ) -> bool:
        """
        Check whether string is empty.
        """

        return (
            value is None
            or value.strip() == ""
        )
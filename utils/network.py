"""
network.py

Reusable HTTP client for GeoNode Connector.

All HTTP communication between the plugin and GeoNode should
go through this module.

Features
--------
- Persistent requests.Session
- Singleton implementation
- Automatic Bearer Token
- Configurable timeout
- SSL verification
- Unified response format
- Standardized logging
"""

from typing import Any, Dict, Optional

import requests
from requests import Response
from requests.exceptions import RequestException

from .config import (
    CONNECT_TIMEOUT,
    CONTENT_TYPE_JSON,
    DEFAULT_HEADERS,
    DEFAULT_TIMEOUT,
    DEFAULT_TOKEN_TYPE,
    HTTP_OK,
    LOG_LEVEL,
    MAX_RETRIES,
    VERIFY_SSL,
)
from .logger import get_logger

logger = get_logger(__name__)


class NetworkClient:
    """
    Singleton HTTP Client.
    """

    _instance = None

    def __new__(cls):

        if cls._instance is None:

            cls._instance = super().__new__(cls)

            cls._instance._initialize()

        return cls._instance

    def _initialize(self):

        self.session = requests.Session()

        self.timeout = DEFAULT_TIMEOUT

        self.connect_timeout = CONNECT_TIMEOUT

        self.verify_ssl = VERIFY_SSL

        self.default_headers = DEFAULT_HEADERS.copy()

    # ==============================================================
    # Configuration
    # ==============================================================

    def set_timeout(self, timeout: int):

        self.timeout = timeout

    def set_ssl_verification(self, verify: bool):

        self.verify_ssl = verify

    def set_bearer_token(self, token: str):

        self.default_headers["Authorization"] = (
            "{} {}".format(
                DEFAULT_TOKEN_TYPE,
                token,
            )
        )

    def clear_bearer_token(self):

        self.default_headers.pop("Authorization", None)

    @property
    def bearer_token(self) -> str:

        auth = self.default_headers.get(
            "Authorization",
            "",
        )

        if not auth:

            return ""

        return auth.replace(
            "{} ".format(DEFAULT_TOKEN_TYPE),
            "",
        )

    # ==============================================================
    # Header Builder
    # ==============================================================

    def _build_headers(
        self,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:

        final_headers = self.default_headers.copy()

        if headers:

            final_headers.update(headers)

        return final_headers

    # ==============================================================
    # Request
    # ==============================================================

    def request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> Dict[str, Any]:

        headers = self._build_headers(
            kwargs.pop("headers", None)
        )

        timeout = kwargs.pop(
            "timeout",
            (
                self.connect_timeout,
                self.timeout,
            ),
        )

        verify = kwargs.pop(
            "verify",
            self.verify_ssl,
        )

        allow_redirects = kwargs.pop(
            "allow_redirects",
            True,
        )

        try:

            logger.info(
                "%s %s",
                method.upper(),
                url,
            )

            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                timeout=timeout,
                verify=verify,
                allow_redirects=allow_redirects,
                **kwargs,
            )

            logger.info(
                "HTTP %s",
                response.status_code,
            )

            return self._build_response(response)

        except RequestException as exc:

            logger.exception(exc)

            return {
                "success": False,
                "status_code": None,
                "message": str(exc),
                "headers": {},
                "data": None,
            }

    # ==============================================================
    # HTTP Methods
    # ==============================================================

    def get(self, url: str, **kwargs):

        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):

        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):

        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs):

        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs):

        return self.request("DELETE", url, **kwargs)

    # ==============================================================
    # Response Helper
    # ==============================================================

    def _build_response(
        self,
        response: Response,
    ) -> Dict[str, Any]:

        try:

            data = response.json()

        except ValueError:

            data = response.text

        if response.ok:

            logger.info(
                "Response OK (%s)",
                response.status_code,
            )

        else:

            logger.warning(
                "%s %s",
                response.status_code,
                response.reason,
            )

        return {
            "success": response.ok,
            "status_code": response.status_code,
            "message": response.reason,
            "headers": dict(response.headers),
            "data": data,
        }

    # ==============================================================
    # Session
    # ==============================================================

    def close(self):

        self.session.close()

    def reset(self):

        self.close()

        self._initialize()


network_client = NetworkClient()
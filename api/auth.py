"""
auth.py

REST Authentication API for GeoNode Connector.

This module is responsible for all authentication-related
communication with GeoNode REST API.

Responsibilities
----------------
- Server connection checking
- OAuth authentication
- Access token refresh
- Current user retrieval
- Token verification

This module DOES NOT:

- Store user session
- Update UI
- Access widgets
- Access controllers

Authentication state is managed by LoginService.
"""

from typing import Any, Dict, Optional, Sequence

from ..utils.config import (
    AUTH_API_ENDPOINTS,
    AUTH_LOGIN_ENDPOINTS,
    AUTH_USER_ENDPOINTS,
    HTTP_FORBIDDEN,
    HTTP_METHOD_NOT_ALLOWED,
    HTTP_NOT_FOUND,
    HTTP_OK,
    HTTP_UNAUTHORIZED,
    OAUTH_CLIENT_ID,
    OAUTH_CLIENT_SECRET,
)
from ..utils.logger import get_logger
from ..utils.network import network_client

logger = get_logger(__name__)


class AuthAPI:
    """
    GeoNode REST Authentication Client.
    """

    def __init__(self) -> None:

        self.server_url = ""

        #
        # Endpoint cache.
        #
        # Endpoint discovery hanya dilakukan sekali
        # untuk setiap jenis endpoint.
        #
        self._endpoint_cache: Dict[
            tuple,
            str,
        ] = {}

    # ==============================================================
    # Configuration
    # ==============================================================

    def set_server(
        self,
        server_url: str,
    ) -> None:
        """
        Set GeoNode server URL.

        Parameters
        ----------
        server_url : str
            Base GeoNode URL.
        """

        self.server_url = server_url.rstrip("/")

        #
        # Server berubah,
        # endpoint discovery harus diulang.
        #
        self._endpoint_cache.clear()

    @property
    def network(self):

        return network_client

    # ==============================================================
    # URL Builder
    # ==============================================================

    def _build_url(
        self,
        endpoint: str,
    ) -> str:
        """
        Build absolute URL.

        Parameters
        ----------
        endpoint : str

        Returns
        -------
        str
        """

        if not self.server_url:

            raise ValueError(
                "Server URL has not been configured."
            )

        endpoint = endpoint.lstrip("/")

        return "{}/{}".format(
            self.server_url,
            endpoint,
        )

    # ==============================================================
    # Endpoint Discovery
    # ==============================================================

    def _resolve_endpoint(
        self,
        candidates: Sequence[str],
        method: str = "GET",
    ) -> Optional[str]:
        """
        Discover and cache the first available endpoint.

        Parameters
        ----------
        candidates : Sequence[str]
            Candidate endpoint list.

        method : str, default="GET"
            HTTP method used during endpoint discovery.

        Returns
        -------
        """

        cache_key = (method.upper(), tuple(candidates))

        if cache_key in self._endpoint_cache:

            logger.debug(
                "Using cached endpoint: %s",
                self._endpoint_cache[cache_key],
            )

            return self._endpoint_cache[cache_key]

        method = method.upper()

        logger.info(
            "Resolving OAuth endpoint (%s)...",
            method,
        )

        attempted = []

        for endpoint in candidates:

            url = self._build_url(endpoint)

            logger.info(
                "Trying endpoint: %s",
                url,
            )

            try:

                if method == "GET":

                    result = self.network.get(url)

                else:

                    result = self.network.post(url)

            except Exception as exc:

                logger.exception(
                    "Endpoint check failed: %s",
                    url,
                )

                attempted.append(
                    f"{endpoint} -> EXCEPTION ({exc})"
                )

                continue

            status = result.get("status_code")

            attempted.append(
                f"{endpoint} -> {status}"
            )

            logger.info(
                "Response: HTTP %s",
                status,
            )

            if status is None:

                logger.warning(
                    "Unable to connect to %s",
                    url,
                )

                continue

            if status != HTTP_NOT_FOUND:

                logger.info(
                    "Resolved endpoint: %s",
                    endpoint,
                )

                self._endpoint_cache[
                    cache_key
                ] = endpoint

                return endpoint

            logger.debug(
                "Endpoint not found: %s",
                endpoint,
            )

        logger.error(
            "OAuth endpoint could not be resolved."
        )

        logger.error(
            "Endpoints tested:\n%s",
            "\n".join(attempted),
        )

        return None

    # ==============================================================
    # Generic Request
    # ==============================================================

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generic HTTP request wrapper.

        Parameters
        ----------
        method : str
            HTTP method.

        endpoint : str
            Relative endpoint.

        Returns
        -------
        Dict[str, Any]
        """

        url = self._build_url(endpoint)

        method = method.upper()

        logger.debug(
            "%s %s",
            method,
            url,
        )

        if method == "GET":

            return self.network.get(
                url,
                **kwargs,
            )

        if method == "POST":

            return self.network.post(
                url,
                **kwargs,
            )

        if method == "PUT":

            return self.network.put(
                url,
                **kwargs,
            )

        if method == "PATCH":

            return self.network.patch(
                url,
                **kwargs,
            )

        if method == "DELETE":

            return self.network.delete(
                url,
                **kwargs,
            )

        raise ValueError(
            "Unsupported HTTP method: {}".format(
                method,
            )
        )

    # ==============================================================
    # HTTP Wrapper
    # ==============================================================

    def _get(
        self,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:

        return self._request(
            "GET",
            endpoint,
            **kwargs,
        )

    def _post(
        self,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:

        return self._request(
            "POST",
            endpoint,
            **kwargs,
        )

    def _put(
        self,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:

        return self._request(
            "PUT",
            endpoint,
            **kwargs,
        )

    def _patch(
        self,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:

        return self._request(
            "PATCH",
            endpoint,
            **kwargs,
        )

    def _delete(
        self,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:

        return self._request(
            "DELETE",
            endpoint,
            **kwargs,
        )

    # ==============================================================
    # Response Helper
    # ==============================================================

    @staticmethod
    def _success(
        result: Dict[str, Any],
    ) -> bool:
        """
        Return True if request succeeded.
        """

        return bool(
            result.get(
                "success",
                False,
            )
        )

    @staticmethod
    def _status_code(
        result: Dict[str, Any],
    ) -> Optional[int]:
        """
        Return HTTP status code.
        """

        return result.get(
            "status_code",
        )

    @staticmethod
    def _message(
        result: Dict[str, Any],
    ) -> str:
        """
        Extract response message.
        """

        data = result.get(
            "data",
        )

        if isinstance(
            data,
            dict,
        ):

            for key in (
                "detail",
                "error",
                "message",
                "errors",
            ):

                if key in data:

                    value = data[key]

                    if isinstance(
                        value,
                        list,
                    ):

                        return ", ".join(
                            str(v)
                            for v in value
                        )

                    return str(value)

        return str(
            result.get(
                "message",
                "",
            )
        )

    @staticmethod
    def _data(
        result: Dict[str, Any],
    ) -> Any:
        """
        Return response payload.
        """

        return result.get(
            "data",
        )

    @staticmethod
    def _headers(
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Return response headers.
        """

        return result.get(
            "headers",
            {},
        )

    @staticmethod
    def _is_unauthorized(
        result: Dict[str, Any],
    ) -> bool:

        return (
            AuthAPI._status_code(result)
            == HTTP_UNAUTHORIZED
        )

    @staticmethod
    def _is_forbidden(
        result: Dict[str, Any],
    ) -> bool:

        return (
            AuthAPI._status_code(result)
            == HTTP_FORBIDDEN
        )

    @staticmethod
    def _is_not_found(
        result: Dict[str, Any],
    ) -> bool:

        return (
            AuthAPI._status_code(result)
            == HTTP_NOT_FOUND
        )

    @staticmethod
    def get_token_data(
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract OAuth token information.
        """

        data = result.get(
            "data",
        ) or {}

        return {

            "access_token": data.get(
                "access_token",
                "",
            ),

            "refresh_token": data.get(
                "refresh_token",
                "",
            ),

            "token_type": data.get(
                "token_type",
                "Bearer",
            ),

            "expires_in": data.get(
                "expires_in",
            ),
        }

    # ==============================================================
    # Public API
    # ==============================================================

    def check_connection(self) -> Dict[str, Any]:
        """
        Check whether GeoNode API is reachable.
        """

        endpoint = self._resolve_endpoint(
            AUTH_API_ENDPOINTS,
        )

        if endpoint is None:

            return {
                "success": False,
                "status_code": None,
                "message": "GeoNode API endpoint not found.",
                "headers": {},
                "data": None,
            }

        logger.info(
            "Checking GeoNode connection."
        )

        return self._get(endpoint)

    # ==============================================================
    # OAuth Login
    # ==============================================================

    def login(
        self,
        username: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Authenticate using OAuth2 Password Grant.
        """

        endpoint = self._resolve_endpoint(
            AUTH_LOGIN_ENDPOINTS,
            method="POST",
        )

        if endpoint is None:

            return {
                "success": False,
                "status_code": None,
                "message": "OAuth endpoint not found.",
                "headers": {},
                "data": None,
            }

        payload = {

            "grant_type": "password",

            "username": username,

            "password": password,

            "client_id": OAUTH_CLIENT_ID,

            "client_secret": OAUTH_CLIENT_SECRET,
        }

        logger.info(
            "Authenticating user '%s'.",
            username,
        )

        result = self._post(
            endpoint,
            data=payload,
        )

        if not self._success(result):

            logger.warning(
                "Authentication failed: %s",
                self._message(result),
            )

            return result

        logger.info(
            "User '%s' authenticated successfully.",
            username,
        )

        return result

    # ==============================================================
    # Refresh Token
    # ==============================================================

    def refresh_token(
        self,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """
        Request a new access token using
        an existing refresh token.
        """

        endpoint = self._resolve_endpoint(
            AUTH_LOGIN_ENDPOINTS,
            method="POST",
        )

        if endpoint is None:

            return {
                "success": False,
                "status_code": None,
                "message": "OAuth endpoint not found.",
                "headers": {},
                "data": None,
            }

        payload = {

            "grant_type": "refresh_token",

            "refresh_token": refresh_token,

            "client_id": OAUTH_CLIENT_ID,

            "client_secret": OAUTH_CLIENT_SECRET,
        }

        logger.info(
            "Refreshing OAuth access token."
        )

        result = self._post(
            endpoint,
            data=payload,
        )

        if not self._success(result):

            logger.warning(
                "Refresh token failed: %s",
                self._message(result),
            )

            return result

        logger.info(
            "Access token refreshed successfully."
        )

        return result

    # ==============================================================
    # Current User
    # ==============================================================

    def get_current_user(self) -> Dict[str, Any]:
        """
        Retrieve authenticated user information.
        """

        endpoint = self._resolve_endpoint(
            AUTH_USER_ENDPOINTS,
        )

        if endpoint is None:

            return {
                "success": False,
                "status_code": None,
                "message": "User endpoint not found.",
                "headers": {},
                "data": None,
            }

        logger.info(
            "Retrieving current user information."
        )

        result = self._get(endpoint)

        if not result.get("success"):

            return result

        data = result.get("data", {})

        #
        # GeoNode list response
        #
        if isinstance(data, dict) and "users" in data:

            username = self.network.bearer_username if hasattr(
                self.network,
                "bearer_username",
            ) else None

            #
            # fallback menggunakan session username
            #
            if username is None:

                from ..models.session import session

                username = session.username

            for user in data["users"]:

                if user.get("username") == username:

                    result["data"] = user

                    logger.info(
                        "Current user found: %s",
                        username,
                    )

                    return result

            logger.warning(
                "Current user '%s' not found.",
                username,
            )

            result["success"] = False

            result["message"] = "Current user not found."

            return result

        #
        # single user response
        #
        if isinstance(data, dict) and "user" in data:

            result["data"] = data["user"]

        return result

    # ==============================================================
    # Token Verification
    # ==============================================================

    def verify_token(self) -> Dict[str, Any]:
        """
        Verify current access token by requesting
        authenticated user information.
        """

        logger.info(
            "Verifying access token."
        )

        result = self.get_current_user()

        if self._success(result):

            logger.info(
                "Access token is valid."
            )

        else:

            logger.warning(
                "Access token verification failed."
            )

        return result

    # ==============================================================
    # Logout
    # ==============================================================

    def logout(self) -> Dict[str, Any]:
        """
        Logout from GeoNode.

        OAuth2 Password Grant does not provide
        a standard logout endpoint.

        Authentication state will be cleared
        by LoginService.
        """

        logger.info(
            "Logout requested."
        )

        return {
            "success": True,
            "status_code": HTTP_OK,
            "message": "Logout successful.",
            "headers": {},
            "data": None,
        }
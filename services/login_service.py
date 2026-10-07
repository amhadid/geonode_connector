"""
login_service.py

Business service for GeoNode authentication.

LoginService is the single entry point for authentication workflow.

Responsibilities
----------------
- Login
- Logout
- Session management
- Current user management
- Refresh access token

This class coordinates AuthAPI, Session, User and NetworkClient,
without performing any UI-related operations.
"""

from typing import Dict, Any

from ..api.auth import AuthAPI
from ..models.service_result import ServiceResult
from ..models.session import session
from ..models.user import User
from ..utils.logger import get_logger

logger = get_logger(__name__)

class LoginService:
    """
    Authentication business service.
    """

    def __init__(self) -> None:

        self._auth_api = AuthAPI()

        self._session = session

        self._user = User()

    # ==============================================================
    # Properties
    # ==============================================================

    @property
    def session(self):

        return self._session

    @property
    def current_user(self):

        return self._user

    # ==============================================================
    # Private Helper
    # ==============================================================

    def _clear_authentication(self) -> None:
        """
        Clear current authentication state.
        """

        self._auth_api.network.clear_bearer_token()

        self._session.clear()

        self._user.clear()

    def _store_session(
        self,
        server_url: str,
        username: str,
        token: Dict[str, Any],
        password: str = "",
    ) -> None:
        """
        Store authenticated session.
        """

        access_token = token.get(
            "access_token",
            "",
        )

        refresh_token = token.get(
            "refresh_token",
            "",
        )

        token_type = token.get(
            "token_type",
            "Bearer",
        )

        expires_in = token.get(
            "expires_in",
        )

        self._auth_api.network.set_bearer_token(
            access_token,
        )

        self._session.set_authenticated(
            server_url=server_url,
            username=username,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            expires_in=expires_in,
            password=password,
        )

    # ==============================================================
    # Authentication
    # ==============================================================

    def login(
        self,
        server_url: str,
        username: str,
        password: str,
    ) -> ServiceResult:
        """
        Authenticate user to GeoNode.

        Parameters
        ----------
        server_url : str
            GeoNode server URL.

        username : str
            GeoNode username.

        password : str
            GeoNode password.

        Returns
        -------
        ServiceResult
        """

        logger.info(
            "Authenticating user '%s' to '%s'.",
            username,
            server_url,
        )

        #
        # Remove previous authentication state.
        #
        self._clear_authentication()

        #
        # Configure target server.
        #
        self._auth_api.set_server(
            server_url,
        )

        #
        # Authenticate.
        #
        result = self._auth_api.login(
            username=username,
            password=password,
        )

        if not result.get(
            "success",
            False,
        ):

            logger.warning(
                "Authentication failed: %s",
                result.get(
                    "message",
                    "",
                ),
            )

            return ServiceResult.fail(
                message=result.get(
                    "message",
                    "Authentication failed.",
                )
            )
        
        token = self._auth_api.get_token_data(
            result,
        )

        self._store_session(
            server_url=server_url,
            username=username,
            token=token,
            password=password,
        )

        user_result = self.load_current_user()

        if not user_result.success:

            logger.error(
                "Authentication succeeded but failed to retrieve user profile."
            )

            self.logout()

            return user_result

        logger.info(
            "User '%s' authenticated successfully.",
            username,
        )

        return ServiceResult.ok(
            message="Authentication successful.",
            data=self._user,
        )

    # ==============================================================
    # User
    # ==============================================================

    def load_current_user(self) -> ServiceResult:
        """
        Retrieve authenticated user information.
        """

        result = self._auth_api.get_current_user()

        if not result.get("success", False):

            logger.warning(
                "Failed to retrieve current user: %s",
                result.get("message"),
            )

            return ServiceResult.fail(
                message=result.get(
                    "message",
                    "Unable to retrieve current user.",
                )
            )

        user_data = result.get("data") or {}

        logger.info(
            "User payload = %s",
            user_data,
        )

        self._user = User.from_dict(
            user_data,
        )

        logger.info(
            "Loaded username     : %s",
            self._user.username,
        )

        logger.info(
            "Loaded display name : %s",
            self._user.display_name,
        )

        return ServiceResult.ok(
            data=self._user,
        )

    # ==============================================================
    # Session
    # ==============================================================

    def verify_session(self) -> ServiceResult:
        """
        Verify current authentication session.

        Returns
        -------
        ServiceResult
        """

        if not self._session.is_logged_in():

            return ServiceResult.fail(
                message="No active session.",
            )

        result = self._auth_api.verify_token()

        if result.get(
            "success",
            False,
        ):

            logger.debug(
                "Session verification successful."
            )

            return ServiceResult.ok(
                message="Session is valid.",
            )

        logger.warning(
            "Session verification failed."
        )

        return ServiceResult.fail(
            message=result.get(
                "message",
                "Session is invalid.",
            )
        )

    def refresh_session(self) -> ServiceResult:
        """
        Refresh OAuth access token.

        Returns
        -------
        ServiceResult
        """

        refresh_token = self._session.refresh_token

        if not refresh_token:

            logger.warning(
                "Refresh token is unavailable."
            )

            return ServiceResult.fail(
                message="Refresh token is unavailable.",
            )

        result = self._auth_api.refresh_token(
            refresh_token,
        )

        if not result.get(
            "success",
            False,
        ):

            logger.warning(
                "Refresh token failed: %s",
                result.get(
                    "message",
                    "",
                ),
            )

            return ServiceResult.fail(
                message=result.get(
                    "message",
                    "Unable to refresh access token.",
                )
            )

        token = self._auth_api.get_token_data(
            result,
        )

        self._store_session(
            server_url=self._session.server_url,
            username=self._session.username,
            token=token,
        )

        logger.info(
            "Access token refreshed successfully."
        )

        return ServiceResult.ok(
            message="Access token refreshed.",
        )

    # ==============================================================
    # Logout
    # ==============================================================

    def logout(self) -> ServiceResult:
        """
        Logout current user.

        Returns
        -------
        ServiceResult
        """

        logger.info(
            "Logging out user '%s'.",
            self._session.username,
        )

        result = self._auth_api.logout()

        self._clear_authentication()

        if result.get(
            "success",
            False,
        ):

            logger.info(
                "Logout completed successfully."
            )

            return ServiceResult.ok(
                message="Logout successful.",
            )

        logger.warning(
            "Logout completed but AuthAPI returned failure."
        )

        return ServiceResult.fail(
            message=result.get(
                "message",
                "Logout failed.",
            )
        )
    
"""
login_controller.py

Controller for GeoNode Connector Login.

Responsibilities
----------------
- Validate login form
- Coordinate LoginWidget and LoginService
- Handle login/logout workflow

Navigation between pages is handled by
GeoNodeConnectorDockWidget.
"""

from __future__ import annotations

from typing import Optional

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QMessageBox

from ...services.login_service import LoginService
from ...utils.logger import get_logger
from ...utils.validator import Validator

logger = get_logger(__name__)


class LoginController(QObject):
    """
    Controller for LoginWidget.

    This controller manages the authentication workflow and emits
    signals upon success or failure.
    """

    loginSucceeded = pyqtSignal()
    loginFailed = pyqtSignal(str)

    def __init__(
        self,
        widget,
        login_service: Optional[LoginService] = None,
    ):
        super().__init__()
        self.widget = widget
        """
        Parameters
        ----------
        widget
            LoginWidget instance.

        login_service
            Optional LoginService dependency.
        """

        self.widget = widget

        self._service = (
            login_service
            or LoginService()
        )

        self.initialize()

    # ==========================================================
    # Initialization
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        """
        Connect widget signals.
        """

        self.widget.login_button.clicked.connect(
            self.login
        )

        if hasattr(self.widget, "password") and hasattr(self.widget.password, "returnPressed"):
            self.widget.password.returnPressed.connect(self.login)

        if hasattr(self.widget, "username") and hasattr(self.widget.username, "returnPressed"):
            self.widget.username.returnPressed.connect(self.login)

        from qgis.core import QgsSettings
        settings = QgsSettings()
        saved_server = settings.value("GeoNodeConnector/server_url", "")
        if saved_server and hasattr(self.widget, "server"):
            self.widget.server.setText(str(saved_server))

    # ==========================================================
    # Helper
    # ==========================================================

    def _show_status(
        self,
        message: str,
    ) -> None:
        """
        Update widget status.
        """

        self.widget.set_status(
            message
        )

    def _clear_sensitive_data(
        self,
    ) -> None:
        """
        Remove sensitive information from UI.

        Currently only clears password field.
        """

        self.widget.clear_password()

    def _read_credentials(
        self,
    ) -> dict:
        """
        Read credentials from LoginWidget.
        """

        credentials = (
            self.widget.credentials()
        )

        logger.debug(
            "Credentials successfully read."
        )

        return credentials

    def _normalize_server(
        self,
        server: str,
    ) -> str:
        """
        Normalize GeoNode URL.
        """

        return Validator.normalize_url(
            server
        )

    def _validate_login_input(
        self,
        server: str,
        username: str,
        password: str,
    ) -> Optional[str]:
        """
        Validate login form.
        """

        if not server:

            return "GeoNode URL is required."

        if not Validator.validate_username(
            username,
        ):

            return "Username is required."

        if not Validator.validate_password(
            password,
        ):

            return "Password is required."

        server = self._normalize_server(
            server,
        )

        if not Validator.validate_url(
            server,
        ):

            return "Invalid GeoNode URL."

        return None

    def _authenticate(
        self,
        server: str,
        username: str,
        password: str,
    ):
        """
        Execute authentication through
        LoginService.
        """

        logger.info(
            "Authenticating '%s'...",
            username,
        )

        return self._service.login(
            server_url=server,
            username=username,
            password=password,
        )

    def _login_success(
        self,
    ) -> None:
        """
        Handle successful authentication.
        """

        current_user = (
            self._service.current_user
        )

        display_name = (
            current_user.display_name
            or current_user.username
        )

        message = (
            f"Berhasil login sebagai "
            f"{display_name}"
        )

        logger.info(
            message,
        )

        self._show_status(
            message,
        )

        self.loginSucceeded.emit()

    def _login_failed(
        self,
        message: str,
    ) -> None:
        """
        Handle failed authentication.
        """

        logger.warning(
            message,
        )

        #
        # Demi keamanan,
        # password selalu dikosongkan.
        #
        self._clear_sensitive_data()

        self._show_status(
            message,
        )

        self.loginFailed.emit(message)

    def _handle_exception(
        self,
        exc: Exception,
    ) -> None:
        """
        Handle unexpected exception.
        """

        logger.exception(
            exc,
        )

        self._clear_sensitive_data()

        QMessageBox.critical(
            self.widget,
            "GeoNode Connector",
            str(exc),
        )

        self._show_status(
            "Unexpected error occurred."
        )

    # ==========================================================
    # Authentication
    # ==========================================================

    def login(
        self,
    ) -> None:
        """
        Execute login workflow.
        """

        try:

            #
            # Read credentials
            #
            credentials = (
                self._read_credentials()
            )

            server = (
                credentials["server"]
            )

            username = (
                credentials["username"]
            )

            password = (
                credentials["password"]
            )

            remember = (
                credentials["remember"]
            )

            logger.info(
                "========== LOGIN =========="
            )

            logger.info(
                "Server   : %s",
                server,
            )

            logger.info(
                "Username : %s",
                username,
            )

            logger.info(
                "Remember : %s",
                remember,
            )

            #
            # Validate input
            #
            error = (
                self._validate_login_input(
                    server,
                    username,
                    password,
                )
            )

            if error:

                self._login_failed(
                    error,
                )

                return

            #
            # Normalize URL
            #
            server = (
                self._normalize_server(
                    server,
                )
            )

            #
            # Authenticate
            #
            result = (
                self._authenticate(
                    server,
                    username,
                    password,
                )
            )

            logger.info(
                result.message,
            )

            if result.success:

                self._login_success()

                return

            self._login_failed(
                result.message,
            )

        except Exception as exc:

            self._handle_exception(
                exc,
            )

    def logout(
        self,
    ) -> None:
        """
        Logout current session.
        """

        logger.info(
            "========== LOGOUT =========="
        )

        result = self._service.logout()

        logger.info(
            result.message,
        )

        #
        # Bersihkan form login
        #
        self.widget.clear_form()

        self._show_status(
            result.message,
        )

    # ==============================================================
    # Session
    # ==============================================================

    def verify_session(
        self,
    ):
        """
        Verify current authentication session.

        Returns
        -------
        ServiceResult
        """

        return self._service.verify_session()

    def refresh_session(
        self,
    ):
        """
        Refresh OAuth session.

        Returns
        -------
        ServiceResult
        """

        return self._service.refresh_session()

    # ==============================================================
    # Future Feature
    # ==============================================================

    def remember_me(
        self,
    ) -> None:
        """
        Reserved for Sprint 4.

        Planned features
        ----------------
        - Save last username
        - Save last server URL
        - Remember-me preference
        - Automatic login
        """

        logger.debug(
            "remember_me() is not implemented yet."
        )

    def load_saved_session(
        self,
    ) -> None:
        """
        Reserved for Sprint 4.

        Restore previously authenticated session.
        """

        logger.debug(
            "load_saved_session() is not implemented yet."
        )

    # ==============================================================
    # Properties
    # ==============================================================

    @property
    def service(
        self,
    ) -> LoginService:
        """
        LoginService instance.
        """

        return self._service

    @property
    def current_user(
        self,
    ):
        """
        Current authenticated user.
        """

        return self._service.current_user

    @property
    def session(
        self,
    ):
        """
        Current authentication session.
        """

        return self._service.session

    @property
    def is_authenticated(
        self,
    ) -> bool:
        """
        Authentication status.
        """

        return self._service.session.is_logged_in()

    # ==============================================================
    # Debug
    # ==============================================================

    def __repr__(
        self,
    ) -> str:
        """
        Debug representation.
        """

        user = self.current_user

        username = (
            user.username
            if user and user.username
            else "Anonymous"
        )

        return (
            f"{self.__class__.__name__}"
            f"(user='{username}')"
        )

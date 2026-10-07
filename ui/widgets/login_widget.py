"""
login_widget.py

Login widget for GeoNode Connector.

This widget only provides the user interface.
All authentication logic is handled by LoginController.
"""

import os

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QScrollArea,
    QAction,
)

from ...utils.config import (
    DEFAULT_SERVER,
    ICON_PATH,
)

from ...utils.style_loader import StyleLoader


class LoginWidget(QWidget):
    """
    Login page widget.
    """

    def __init__(
        self,
        parent=None,
    ):

        super().__init__(parent)

        self._build_ui()

        self.setMinimumSize(350, 750)

    # ==========================================================
    # UI
    # ==========================================================
    def _build_ui(self) -> None:
        """
        Build login interface.
        """

        # ==========================================================
        # Main Layout
        # ==========================================================

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        main_container = QWidget()

        main_container.setMinimumHeight(550)

        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(40, 25, 40, 25)
        main_layout.setSpacing(18)
        main_layout.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(main_container)
        outer_layout.addWidget(scroll_area)

        # ==========================================================
        # Header
        # ==========================================================

        header_widget = QWidget()

        header_widget.setObjectName(
            "headerWidget"
        )

        header_layout = QVBoxLayout()

        header_layout.setContentsMargins(
            0,
            0,
            0,
            10,
        )

        header_layout.setSpacing(
            4
        )

        header_layout.setAlignment(
            Qt.AlignCenter
        )

        header_widget.setLayout(
            header_layout
        )

        # ==========================================================
        # Logo
        # ==========================================================

        self.logo = QLabel()

        self.logo.setObjectName(
            "logoLabel"
        )

        self.logo.setAlignment(
            Qt.AlignCenter
        )

        self.logo.setFixedHeight(
            72
        )

        if os.path.exists(
            ICON_PATH
        ):

            pixmap = QPixmap(
                ICON_PATH
            )

            if not pixmap.isNull():

                self.logo.setPixmap(

                    pixmap.scaled(

                        64,
                        64,

                        Qt.KeepAspectRatio,

                        Qt.SmoothTransformation,

                    )

                )

        header_layout.addWidget(
            self.logo
        )

        # ==========================================================
        # Title
        # ==========================================================

        self.title_label = QLabel(
            "GeoNode Connector"
        )

        self.title_label.setObjectName(
            "titleLabel"
        )

        self.title_label.setAlignment(
            Qt.AlignCenter
        )

        header_layout.addWidget(
            self.title_label
        )

        # ==========================================================
        # Subtitle
        # ==========================================================

        self.subtitle_label = QLabel(
            "Pemerintah Kota Yogyakarta"
        )

        self.subtitle_label.setObjectName(
            "subtitleLabel"
        )

        self.subtitle_label.setAlignment(
            Qt.AlignCenter
        )

        header_layout.addWidget(
            self.subtitle_label
        )

        main_layout.addWidget(
            header_widget
        )

        # ==========================================================
        # Form Widget
        # ==========================================================

        form_widget = QWidget()

        form_layout = QVBoxLayout()

        form_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        form_layout.setSpacing(
            14
        )

        form_widget.setLayout(
            form_layout
        )

        form_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        # ==========================================================
        # URL FIELD
        # ==========================================================

        url_widget = QWidget()

        url_layout = QVBoxLayout()

        url_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        url_layout.setSpacing(
            5
        )

        url_widget.setLayout(
            url_layout
        )

        label_server = QLabel(
            "URL GeoPortal"
        )

        label_server.setObjectName(
            "fieldLabel"
        )

        self.server = QLineEdit()

        self.server.setObjectName(
            "serverEdit"
        )

        self.server.setPlaceholderText(
            "https://geoportal.jogjakota.go.id"
        )

        self.server.setText(
            DEFAULT_SERVER
        )

        self.server.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.server.setMinimumHeight(38)

        self.server.setClearButtonEnabled(
            True
        )

        url_layout.addWidget(
            label_server
        )

        url_layout.addWidget(
            self.server
        )

        form_layout.addWidget(
            url_widget
        )

        # ==========================================================
        # USERNAME FIELD
        # ==========================================================

        username_widget = QWidget()

        username_layout = QVBoxLayout()

        username_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        username_layout.setSpacing(
            5
        )

        username_widget.setLayout(
            username_layout
        )

        label_username = QLabel(
            "Username"
        )

        label_username.setObjectName(
            "fieldLabel"
        )

        self.username = QLineEdit()

        self.username.setObjectName(
            "usernameEdit"
        )

        self.username.setPlaceholderText(
            "Masukkan username"
        )

        self.username.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.username.setMinimumHeight(38)

        self.username.setClearButtonEnabled(
            True
        )

        username_layout.addWidget(
            label_username
        )

        username_layout.addWidget(
            self.username
        )

        form_layout.addWidget(
            username_widget
        )

        # ==========================================================
        # PASSWORD FIELD
        # ==========================================================

        password_widget = QWidget()

        password_layout = QVBoxLayout()

        password_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        password_layout.setSpacing(
            5
        )

        password_widget.setLayout(
            password_layout
        )

        label_password = QLabel(
            "Password"
        )

        label_password.setObjectName(
            "fieldLabel"
        )

        self.password = QLineEdit()

        self.password.setObjectName(
            "passwordEdit"
        )

        self.password.setPlaceholderText(
            "Masukkan password"
        )

        self.password.setEchoMode(
            QLineEdit.Password
        )

        self.password.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.password.setMinimumHeight(38)

        self.password.setClearButtonEnabled(
            True
        )

        # Eye Action: Toggle Show/Hide Password
        self.act_toggle_pwd = self.password.addAction(
            QgsApplication.getThemeIcon("mActionShowAllLayers.svg"),
            QLineEdit.TrailingPosition
        )
        self.act_toggle_pwd.setToolTip("Tampilkan password")
        self.act_toggle_pwd.triggered.connect(self._toggle_password_visibility)

        password_layout.addWidget(
            label_password
        )

        password_layout.addWidget(
            self.password
        )

        form_layout.addWidget(
            password_widget
        )

        # ==========================================================
        # REMEMBER ME
        # ==========================================================

        remember_widget = QWidget()

        remember_layout = QHBoxLayout()

        remember_layout.setContentsMargins(
            0,
            4,
            0,
            0,
        )

        remember_layout.setSpacing(
            8
        )

        remember_widget.setLayout(
            remember_layout
        )

        self.remember = QCheckBox(
            "Ingat saya"
        )

        self.remember.setObjectName(
            "rememberCheck"
        )

        remember_layout.addWidget(
            self.remember
        )

        remember_layout.addStretch()

        form_layout.addWidget(
            remember_widget
        )

        # ==========================================================
        # LOGIN BUTTON
        # ==========================================================

        self.login_button = QPushButton(
            "LOGIN"
        )

        self.login_button.setObjectName(
            "loginButton"
        )

        self.login_button.setIcon(
            QgsApplication.getThemeIcon("user.svg")
        )

        self.login_button.setFixedHeight(
            44
        )

        self.login_button.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        form_layout.addSpacing(
            10
        )

        form_layout.addWidget(
            self.login_button
        )

        # ==========================================================
        # STATUS
        # ==========================================================

        self.status = QLabel(
            "Status : Belum login"
        )

        self.status.setObjectName(
            "statusLabel"
        )

        self.status.setAlignment(
            Qt.AlignCenter
        )

        self.status.setWordWrap(
            True
        )

        self.status.setContentsMargins(
            0,
            8,
            0,
            0,
        )

        form_layout.addWidget(
            self.status
        )

        # ==========================================================
        # ADD TO MAIN LAYOUT
        # ==========================================================

        main_layout.addWidget(
            form_widget
        )

        main_layout.addStretch()

        # ==========================================================
        # APPLY STYLE
        # ==========================================================

        StyleLoader.apply(
            self,
            "login.qss",
        )

    # ==============================================================
    # Helper
    # ==============================================================

    def credentials(self) -> dict:
        """
        Return login credentials.
        """

        return {
            "server": self.server.text().strip(),
            "username": self.username.text().strip(),
            "password": self.password.text(),
            "remember": self.remember.isChecked(),
        }

    def clear_password(self) -> None:
        """
        Clear password field.
        """

        self.password.clear()

    def clear_form(self) -> None:
        """
        Clear login form.
        """

        self.server.setText(DEFAULT_SERVER)

        self.username.clear()

        self.password.clear()

        self.remember.setChecked(False)

        self.username.setFocus()

        self.set_status(
            "Status : Belum login"
        )

    def _toggle_password_visibility(self) -> None:
        """
        Toggle password echo mode between Password and Normal.
        """
        if self.password.echoMode() == QLineEdit.Password:
            self.password.setEchoMode(QLineEdit.Normal)
            self.act_toggle_pwd.setIcon(
                QgsApplication.getThemeIcon("mActionHideSelectedLayers.svg")
            )
            self.act_toggle_pwd.setToolTip("Sembunyikan password")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.act_toggle_pwd.setIcon(
                QgsApplication.getThemeIcon("mActionShowAllLayers.svg")
            )
            self.act_toggle_pwd.setToolTip("Tampilkan password")

    def set_status(
        self,
        message: str,
    ) -> None:
        """
        Update status label.
        """

        self.status.setText(message)

    def set_login_enabled(
        self,
        enabled: bool,
    ) -> None:
        """
        Enable or disable login controls.
        """

        self.server.setEnabled(enabled)

        self.username.setEnabled(enabled)

        self.password.setEnabled(enabled)

        self.remember.setEnabled(enabled)

        self.login_button.setEnabled(enabled)

    def focus_username(self) -> None:
        """
        Focus username field.
        """

        self.username.setFocus()

    def focus_password(self) -> None:
        """
        Focus password field.
        """

        self.password.setFocus()

    def set_server(
        self,
        url: str,
    ) -> None:
        """
        Set server URL.
        """

        self.server.setText(url)

    def set_username(
        self,
        username: str,
    ) -> None:
        """
        Set username.
        """

        self.username.setText(username)

    def remember_enabled(self) -> bool:
        """
        Return remember state.
        """

        return self.remember.isChecked()
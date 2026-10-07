# -*- coding: utf-8 -*-
"""
GeoNode Connector Main Window / Dialog.

Responsibilities
----------------
- Build plugin interface according to Mockup 1 - 8
- Coordinate pre-login and post-login UI states with horizontally centered menus
- Coordinate navigation between tabs (DATASET, LAYER SAYA, AKTIVITAS, PENGATURAN)
- Connect services and controllers
- Use standard QGIS theme icons across all UI components
"""

from __future__ import annotations

import os
from typing import Optional

from qgis.core import QgsApplication
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt, QSettings, pyqtSignal
from qgis.PyQt.QtGui import QIcon, QGuiApplication
from qgis.PyQt.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabBar,
    QStackedWidget,
    QFrame,
    QScrollArea,
)

from .utils.config import PLUGIN_NAME
from .utils.logger import get_logger
from .models.session import session

# API
from .api.dataset import DatasetAPI

# Services
from .services.layer_service import LayerService
from .services.import_service import ImportService
from .services.activity_service import activity_service

# Widgets
from .ui.widgets.login_widget import LoginWidget
from .ui.widgets.dataset_widget import DatasetWidget
from .ui.widgets.my_layers_widget import MyLayersWidget
from .ui.widgets.activity_widget import ActivityWidget
from .ui.widgets.server_widget import ServerWidget
from .ui.widgets.about_widget import AboutWidget

# Controllers
from .ui.controllers.login_controller import LoginController
from .ui.controllers.dataset_controller import DatasetController
from .ui.controllers.server_controller import ServerController
from .ui.controllers.about_controller import AboutController
from .ui.controllers.import_controller import ImportController


logger = get_logger(__name__)

SETTINGS_GROUP = "GeoNodeConnector"
SETTINGS_GEOMETRY = f"{SETTINGS_GROUP}/geometry"
DEFAULT_WIDTH = 680
DEFAULT_HEIGHT = 600


class NavScrollArea(QScrollArea):
    """
    QScrollArea khusus tab bar navigasi yang mendukung scrolling horizontal
    langsung dengan roda mouse atau trackpad, dan menghilangkan tombol panah geser.
    """

    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.angleDelta().x()
        if delta:
            bar = self.horizontalScrollBar()
            bar.setValue(bar.value() - delta)
            event.accept()
        else:
            super().wheelEvent(event)


class GeoNodeConnectorDialog(QMainWindow):
    """
    Main plugin Window implementing the mockup screens.
    """

    closingPlugin = pyqtSignal()

    def __init__(self, iface=None, parent=None):
        super().__init__(parent)
        self.iface = iface

        self.setWindowTitle(PLUGIN_NAME)
        icon_path = os.path.join(os.path.dirname(__file__), "icon_plugin_qgis.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setWindowFlags(
            Qt.Window
            | Qt.WindowMinMaxButtonsHint
            | Qt.WindowCloseButtonHint
        )

        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.setMinimumSize(480, 480)

        # Central widget & main layout
        self._central_widget = QWidget(self)
        self.setCentralWidget(self._central_widget)

        self.root_layout = QVBoxLayout(self._central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # UI Components
        self.header_widget: Optional[QWidget] = None
        self.nav_scroll: Optional[NavScrollArea] = None
        self.nav_container: Optional[QWidget] = None
        self.tab_bar: Optional[QTabBar] = None
        self.stack: Optional[QStackedWidget] = None

        self.login_tab: Optional[LoginWidget] = None
        self.dataset_tab: Optional[DatasetWidget] = None
        self.my_layers_tab: Optional[MyLayersWidget] = None
        self.activity_tab: Optional[ActivityWidget] = None
        self.server_tab: Optional[ServerWidget] = None
        self.about_tab: Optional[AboutWidget] = None

        # Services
        self.dataset_api: Optional[DatasetAPI] = None
        self.layer_service: Optional[LayerService] = None
        self.import_service: Optional[ImportService] = None

        # Controllers
        self.login_controller: Optional[LoginController] = None
        self.dataset_controller: Optional[DatasetController] = None
        self.import_controller: Optional[ImportController] = None
        self.server_controller: Optional[ServerController] = None
        self.about_controller: Optional[AboutController] = None

        self._build_ui()
        self._create_services()
        self._create_controllers()
        self._connect_signals()

        # State awal: belum login
        self._switch_to_unauthenticated_ui()
        self._restore_geometry()

    # ==============================================================
    # UI Building
    # ==============================================================

    def _build_ui(self) -> None:
        """
        Membangun seluruh komponen visual window.
        """
        # 1. Top Header Bar (User, Server, Logout)
        self._build_top_header()

        # 2. Centered Navigation Tab Bar with Smooth Horizontal Scrolling
        self.nav_scroll = NavScrollArea()
        self.nav_scroll.setObjectName("navScrollArea")
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.nav_scroll.setFrameShape(QFrame.NoFrame)
        self.nav_scroll.setFixedHeight(46)
        self.nav_scroll.setStyleSheet("""
            QScrollArea#navScrollArea {
                background: #FFFFFF;
                border: none;
                border-bottom: 1.5px solid #E2E8F0;
            }
            QScrollArea#navScrollArea QScrollBar:horizontal {
                height: 3px;
                background: transparent;
                margin: 0px;
                border: none;
            }
            QScrollArea#navScrollArea QScrollBar::handle:horizontal {
                background: #CBD5E1;
                border-radius: 1.5px;
                min-width: 24px;
            }
            QScrollArea#navScrollArea QScrollBar::handle:horizontal:hover {
                background: #10B981;
            }
            QScrollArea#navScrollArea QScrollBar::add-line:horizontal,
            QScrollArea#navScrollArea QScrollBar::sub-line:horizontal,
            QScrollArea#navScrollArea QScrollBar::add-page:horizontal,
            QScrollArea#navScrollArea QScrollBar::sub-page:horizontal {
                width: 0px;
                height: 0px;
                background: transparent;
                border: none;
            }
        """)

        self.nav_container = QWidget()
        self.nav_container.setObjectName("navContainer")
        self.nav_container.setStyleSheet("""
            QWidget#navContainer {
                background: #FFFFFF;
                border: none;
            }
        """)
        nav_layout = QHBoxLayout(self.nav_container)
        nav_layout.setContentsMargins(10, 0, 10, 0)
        nav_layout.setSpacing(0)
        nav_layout.addStretch(1)

        self.tab_bar = QTabBar()
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setDocumentMode(True)
        self.tab_bar.setUsesScrollButtons(False)
        self.tab_bar.setCursor(Qt.PointingHandCursor)
        self.tab_bar.setStyleSheet("""
            QTabBar {
                background: transparent;
            }
            QTabBar::tab {
                background: transparent;
                padding: 10px 22px;
                min-width: 90px;
                color: #64748B;
                font-weight: 600;
                font-size: 8.5pt;
                border-bottom: 3px solid transparent;
            }
            QTabBar::tab:selected {
                color: #059669;
                font-weight: 700;
                border-bottom: 3px solid #10B981;
            }
            QTabBar::tab:hover {
                color: #10B981;
            }
            QTabBar QToolButton {
                width: 0px;
                height: 0px;
                margin: 0px;
                padding: 0px;
                border: none;
            }
            QTabBar::scroller {
                width: 0px;
            }
        """)
        nav_layout.addWidget(self.tab_bar)
        nav_layout.addStretch(1)

        self.nav_scroll.setWidget(self.nav_container)
        self.root_layout.addWidget(self.nav_scroll)

        # 3. Stacked Widget for Page Content
        self.stack = QStackedWidget(self)
        self.root_layout.addWidget(self.stack, stretch=1)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)

        # Create tab widgets
        self.login_tab = LoginWidget()
        self.dataset_tab = DatasetWidget()
        self.my_layers_tab = MyLayersWidget(iface=self.iface)
        self.activity_tab = ActivityWidget()
        self.server_tab = ServerWidget()
        self.about_tab = AboutWidget()

    def _build_top_header(self) -> None:
        """
        Membangun header atas modern untuk tampilan yang sudah login (Mockup Screen 3).
        """
        self.header_widget = QFrame()
        self.header_widget.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border-bottom: 1.5px solid #E2E8F0;
            }
        """)
        h_layout = QHBoxLayout(self.header_widget)
        h_layout.setContentsMargins(16, 8, 16, 8)
        h_layout.setSpacing(12)

        # Chips row
        info_row = QHBoxLayout()
        info_row.setSpacing(10)

        # User chip
        user_chip = QFrame()
        user_chip.setStyleSheet("""
            QFrame {
                background: #ECFDF5;
                border: 1px solid #A7F3D0;
                border-radius: 6px;
            }
        """)
        u_layout = QHBoxLayout(user_chip)
        u_layout.setContentsMargins(8, 4, 10, 4)
        u_layout.setSpacing(6)

        lbl_u_icon = QLabel()
        lbl_u_icon.setPixmap(QgsApplication.getThemeIcon("user.svg").pixmap(16, 16))
        lbl_u_icon.setStyleSheet("border: none; background: transparent;")

        lbl_u_title = QLabel("User:")
        lbl_u_title.setStyleSheet("color: #065F46; font-size: 8pt; font-weight: 500; border: none; background: transparent;")

        self.lbl_header_user = QLabel("admin_demo")
        self.lbl_header_user.setStyleSheet("color: #064E3B; font-size: 8.5pt; font-weight: 700; border: none; background: transparent;")

        u_layout.addWidget(lbl_u_icon)
        u_layout.addWidget(lbl_u_title)
        u_layout.addWidget(self.lbl_header_user)

        # Server chip
        server_chip = QFrame()
        server_chip.setStyleSheet("""
            QFrame {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
            }
        """)
        s_layout = QHBoxLayout(server_chip)
        s_layout.setContentsMargins(8, 4, 10, 4)
        s_layout.setSpacing(6)

        lbl_s_icon = QLabel()
        lbl_s_icon.setPixmap(QgsApplication.getThemeIcon("mIconConnect.svg").pixmap(16, 16))
        lbl_s_icon.setStyleSheet("border: none; background: transparent;")

        lbl_s_title = QLabel("Server:")
        lbl_s_title.setStyleSheet("color: #64748B; font-size: 8pt; font-weight: 500; border: none; background: transparent;")

        self.lbl_header_server = QLabel("http://localhost")
        self.lbl_header_server.setStyleSheet("color: #334155; font-size: 8.5pt; font-weight: 600; border: none; background: transparent;")

        s_layout.addWidget(lbl_s_icon)
        s_layout.addWidget(lbl_s_title)
        s_layout.addWidget(self.lbl_header_server)

        info_row.addWidget(user_chip)
        info_row.addWidget(server_chip)
        info_row.addStretch()

        self.btn_header_logout = QPushButton("LOGOUT")
        self.btn_header_logout.setObjectName("logoutButton")
        self.btn_header_logout.setIcon(QgsApplication.getThemeIcon("mActionClose.svg"))
        self.btn_header_logout.setCursor(Qt.PointingHandCursor)
        self.btn_header_logout.setStyleSheet("""
            QPushButton#logoutButton {
                color: #DC2626;
                border: 1.5px solid #FECACA;
                border-radius: 6px;
                background: #FEF2F2;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 8pt;
                letter-spacing: 0.3px;
            }
            QPushButton#logoutButton:hover {
                background: #FEE2E2;
                border-color: #EF4444;
            }
            QPushButton#logoutButton:pressed {
                background: #FCA5A5;
            }
        """)
        self.btn_header_logout.clicked.connect(self.logout)

        h_layout.addLayout(info_row, stretch=1)
        h_layout.addWidget(self.btn_header_logout)

        self.root_layout.addWidget(self.header_widget)

    # ==============================================================
    # Services & Controllers
    # ==============================================================

    def _create_services(self) -> None:
        self.dataset_api = DatasetAPI()
        self.layer_service = LayerService(dataset_api=self.dataset_api)
        self.import_service = ImportService()

    def _create_controllers(self) -> None:
        self.login_controller = LoginController(widget=self.login_tab)
        self.dataset_controller = DatasetController(
            widget=self.dataset_tab,
            layer_service=self.layer_service,
        )
        self.import_controller = ImportController(
            widget=self.dataset_tab,
            layer_service=self.layer_service,
            import_service=self.import_service,
            my_layers_widget=self.my_layers_tab,
        )
        if self.my_layers_tab:
            self.my_layers_tab.layer_service = self.layer_service
        self.server_controller = ServerController(
            widget=self.server_tab,
            login_widget=self.login_tab,
        )
        self.about_controller = AboutController(self.about_tab)

    def _connect_signals(self) -> None:
        if self.login_controller:
            self.login_controller.loginSucceeded.connect(self._on_login_success)
        self.my_layers_tab.switchToDatasetRequested.connect(lambda: self.tab_bar.setCurrentIndex(0))

    def _on_tab_changed(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            # Segarkan Layer Saya jika tab Layer Saya dipilih
            if self.stack.widget(index) == self.my_layers_tab and hasattr(self.my_layers_tab, "sync_with_qgis_project"):
                self.my_layers_tab.sync_with_qgis_project()
            # Pastikan tab yang dipilih terlihat di scroll area navigasi
            if hasattr(self, "nav_scroll") and self.tab_bar and hasattr(self, "nav_container"):
                tab_rect = self.tab_bar.tabRect(index)
                if tab_rect.isValid():
                    mapped_x = self.tab_bar.mapTo(self.nav_container, tab_rect.topLeft()).x()
                    self.nav_scroll.ensureVisible(mapped_x + tab_rect.width() // 2, 0, 60, 0)

    # ==============================================================
    # Navigation & Authentication State Transitions
    # ==============================================================

    def _switch_to_unauthenticated_ui(self) -> None:
        """
        Tampilan sebelum login (Mockup Screen 2):
        Header user disembunyikan.
        Tabs rata tengah: LOGIN | SERVER | ABOUT dengan ikon native QGIS.
        """
        self.header_widget.hide()
        self.tab_bar.blockSignals(True)

        while self.tab_bar.count() > 0:
            self.tab_bar.removeTab(0)

        while self.stack.count() > 0:
            self.stack.removeWidget(self.stack.widget(0))

        # Add pre-login tabs with QGIS theme icons
        self.tab_bar.addTab(QgsApplication.getThemeIcon("user.svg"), "LOGIN")
        self.tab_bar.addTab(QgsApplication.getThemeIcon("mIconConnect.svg"), "SERVER")
        self.tab_bar.addTab(QgsApplication.getThemeIcon("mActionHelpContents.svg"), "ABOUT")

        self.stack.addWidget(self.login_tab)
        self.stack.addWidget(self.server_tab)
        self.stack.addWidget(self.about_tab)

        self.tab_bar.setCurrentIndex(0)
        self.stack.setCurrentIndex(0)
        self.tab_bar.blockSignals(False)

    def _switch_to_authenticated_ui(self) -> None:
        """
        Tampilan setelah login (Mockup Screen 3):
        Header user ditampilkan.
        Tabs rata tengah: DATASET | LAYER SAYA | AKTIVITAS | PENGATURAN dengan ikon native QGIS.
        """
        uname = session.username or (
            self.login_controller.current_user.username
            if self.login_controller and self.login_controller.current_user
            else "admin_demo"
        )
        surl = session.server_url or "http://localhost"

        self.lbl_header_user.setText(uname)
        self.lbl_header_server.setText(surl)
        self.header_widget.show()

        # Update server URL di API
        if self.dataset_api:
            self.dataset_api.set_server(surl)

        self.tab_bar.blockSignals(True)

        while self.tab_bar.count() > 0:
            self.tab_bar.removeTab(0)

        while self.stack.count() > 0:
            self.stack.removeWidget(self.stack.widget(0))

        # Add post-login tabs with QGIS theme icons
        self.tab_bar.addTab(QgsApplication.getThemeIcon("mActionDataSourceManager.svg"), "DATASET")
        self.tab_bar.addTab(QgsApplication.getThemeIcon("mActionShowAllLayers.svg"), "LAYER SAYA")
        self.tab_bar.addTab(QgsApplication.getThemeIcon("mActionPropertyItem.svg"), "AKTIVITAS")
        self.tab_bar.addTab(QgsApplication.getThemeIcon("mActionOptions.svg"), "PENGATURAN")

        self.stack.addWidget(self.dataset_tab)
        self.stack.addWidget(self.my_layers_tab)
        self.stack.addWidget(self.activity_tab)
        self.stack.addWidget(self.server_tab)

        self.tab_bar.setCurrentIndex(0)
        self.stack.setCurrentIndex(0)
        self.tab_bar.blockSignals(False)

        # Sync layer list with QGIS Canvas
        if hasattr(self.my_layers_tab, "sync_with_qgis_project"):
            self.my_layers_tab.sync_with_qgis_project()

    def _on_login_success(self) -> None:
        """
        Dipanggil setelah LoginController berhasil mengautentikasi pengguna.
        """
        logger.info("Login succeeded signal received. Switching to main tabs...")
        self._switch_to_authenticated_ui()

        # Catat aktivitas login
        uname = session.username or (
            self.login_controller.current_user.username
            if self.login_controller and self.login_controller.current_user
            else "admin_demo"
        )
        activity_service.log(
            category="login",
            username=uname,
            description="Login berhasil",
        )

        # Memuat dataset
        if self.dataset_controller:
            self.dataset_controller.load()

    def logout(self) -> None:
        """
        Logout dari sesi saat ini dan kembali ke form login.
        """
        logger.info("Logging out from GeoNode...")
        if self.login_controller:
            self.login_controller.logout()

        if self.layer_service:
            self.layer_service.clear_cache()

        if self.dataset_controller:
            self.dataset_controller.clear()

        self._switch_to_unauthenticated_ui()
        logger.info("Returned to login screen.")

    # ==============================================================
    # Window Geometry & Cleanup
    # ==============================================================

    def _restore_geometry(self) -> None:
        settings = QSettings()
        geometry = settings.value(SETTINGS_GEOMETRY, None)
        if geometry:
            self.restoreGeometry(geometry)
            return

        screen = QGuiApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            frame = self.frameGeometry()
            frame.moveCenter(available.center())
            self.move(frame.topLeft())

    def _save_geometry(self) -> None:
        settings = QSettings()
        settings.setValue(SETTINGS_GEOMETRY, self.saveGeometry())

    def closeEvent(self, event) -> None:
        logger.info("%s window closed.", PLUGIN_NAME)
        try:
            self.closingPlugin.emit()
            self._save_geometry()
        except Exception:
            logger.exception("Error while closing window.")
        event.accept()
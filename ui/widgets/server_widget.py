"""
server_widget.py

Widget Pengaturan Server GeoNode dengan fitur Test Connection dan Status Respons.
"""

from __future__ import annotations

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QWidget,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QLabel,
    QFrame,
    QProgressBar,
    QScrollArea,
)

from ...utils.config import DEFAULT_SERVER


class ServerWidget(QWidget):
    """
    Widget Pengaturan & Uji Koneksi Server GeoNode.
    """

    saveRequested = pyqtSignal(str, int, bool)
    testRequested = pyqtSignal(str, int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(container)
        outer_layout.addWidget(scroll_area)

        # ------------------------------------------------------
        # Header / Info Box
        # ------------------------------------------------------
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_card.setStyleSheet("""
            QFrame#headerCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F8FAFC, stop:1 #F1F5F9);
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(16, 14, 16, 14)
        h_layout.setSpacing(14)

        icon_badge = QLabel()
        icon_badge.setFixedSize(36, 36)
        icon_badge.setAlignment(Qt.AlignCenter)
        icon_badge.setPixmap(QgsApplication.getThemeIcon("mActionOptions.svg").pixmap(20, 20))
        icon_badge.setStyleSheet("""
            QLabel {
                background-color: #ECFDF5;
                border: 1px solid #A7F3D0;
                border-radius: 18px;
            }
        """)

        h_text_layout = QVBoxLayout()
        h_text_layout.setSpacing(2)

        title = QLabel("Konfigurasi Server GeoNode")
        title.setStyleSheet("font-size: 10.5pt; font-weight: 700; color: #0F172A; border: none; background: transparent;")
        desc = QLabel("Atur URL endpoint instance GeoNode, batas waktu, dan opsi keamanan jaringan.")
        desc.setStyleSheet("color: #64748B; font-size: 8.5pt; border: none; background: transparent;")

        h_text_layout.addWidget(title)
        h_text_layout.addWidget(desc)

        h_layout.addWidget(icon_badge)
        h_layout.addLayout(h_text_layout, stretch=1)
        main_layout.addWidget(header_card)

        # ------------------------------------------------------
        # Settings Card (Form)
        # ------------------------------------------------------
        form_card = QFrame()
        form_card.setObjectName("formCard")
        form_card.setStyleSheet("""
            QFrame#formCard {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            QLineEdit {
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                background: #FFFFFF;
                color: #1E293B;
                font-size: 9pt;
            }
            QLineEdit:hover {
                border-color: #94A3B8;
            }
            QLineEdit:focus {
                border: 1.5px solid #10B981;
                background: #FFFFFF;
            }
            QSpinBox {
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 10px;
                background: #FFFFFF;
                color: #1E293B;
                font-size: 9pt;
            }
            QSpinBox:focus {
                border: 1.5px solid #10B981;
            }
            QCheckBox {
                color: #334155;
                font-size: 8.5pt;
                font-weight: 500;
                spacing: 8px;
                border: none;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1.5px solid #CBD5E1;
                border-radius: 4px;
                background: #FFFFFF;
            }
            QCheckBox::indicator:hover {
                border-color: #10B981;
            }
            QCheckBox::indicator:checked {
                background: #10B981;
                border-color: #10B981;
            }
        """)
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(20, 18, 20, 18)
        form_layout.setSpacing(16)

        # URL Field
        url_layout = QVBoxLayout()
        url_layout.setSpacing(6)

        lbl_url_row = QHBoxLayout()
        lbl_url_row.setSpacing(6)
        url_ico = QLabel()
        url_ico.setFixedSize(14, 14)
        url_ico.setPixmap(QgsApplication.getThemeIcon("mIconConnect.svg").pixmap(14, 14))
        url_ico.setStyleSheet("border: none; background: transparent;")
        lbl_url = QLabel("URL Server GeoNode")
        lbl_url.setStyleSheet("border: none; background: transparent; font-weight: 600; color: #1E293B; font-size: 8.5pt;")
        lbl_url_row.addWidget(url_ico)
        lbl_url_row.addWidget(lbl_url)
        lbl_url_row.addStretch()

        self.url = QLineEdit()
        self.url.setText(DEFAULT_SERVER)
        self.url.setPlaceholderText("http://localhost atau https://geoportal.jogjakota.go.id")
        self.url.setClearButtonEnabled(True)

        lbl_url_hint = QLabel("Contoh: http://localhost (tanpa garis miring di akhir)")
        lbl_url_hint.setStyleSheet("color: #94A3B8; font-size: 8pt; font-weight: normal; border: none; background: transparent;")

        url_layout.addLayout(lbl_url_row)
        url_layout.addWidget(self.url)
        url_layout.addWidget(lbl_url_hint)
        form_layout.addLayout(url_layout)

        # Divider halus di form
        div1 = QFrame()
        div1.setFrameShape(QFrame.HLine)
        div1.setFixedHeight(1)
        div1.setStyleSheet("background-color: #F1F5F9; border: none; max-height: 1px;")
        form_layout.addWidget(div1)

        # Timeout & SSL Row
        row_opts = QHBoxLayout()
        row_opts.setSpacing(24)

        # Timeout
        to_layout = QVBoxLayout()
        to_layout.setSpacing(6)

        to_lbl_row = QHBoxLayout()
        to_lbl_row.setSpacing(6)
        to_ico = QLabel()
        to_ico.setFixedSize(14, 14)
        to_ico.setPixmap(QgsApplication.getThemeIcon("mActionHistory.svg").pixmap(14, 14))
        to_ico.setStyleSheet("border: none; background: transparent;")
        lbl_to = QLabel("Timeout Request")
        lbl_to.setStyleSheet("border: none; background: transparent; font-weight: 600; color: #1E293B; font-size: 8.5pt;")
        to_lbl_row.addWidget(to_ico)
        to_lbl_row.addWidget(lbl_to)
        to_lbl_row.addStretch()

        self.timeout = QSpinBox()
        self.timeout.setValue(30)
        self.timeout.setRange(3, 300)

        lbl_to_hint = QLabel("Waktu tunggu respons (3-300 detik)")
        lbl_to_hint.setStyleSheet("color: #94A3B8; font-size: 8pt; font-weight: normal; border: none; background: transparent;")

        to_layout.addLayout(to_lbl_row)
        to_layout.addWidget(self.timeout)
        to_layout.addWidget(lbl_to_hint)
        row_opts.addLayout(to_layout, stretch=1)

        # SSL
        ssl_layout = QVBoxLayout()
        ssl_layout.setSpacing(6)

        ssl_lbl_row = QHBoxLayout()
        ssl_lbl_row.setSpacing(6)
        ssl_ico = QLabel()
        ssl_ico.setFixedSize(14, 14)
        ssl_ico.setPixmap(QgsApplication.getThemeIcon("mIconSuccess.svg").pixmap(14, 14))
        ssl_ico.setStyleSheet("border: none; background: transparent;")
        lbl_ssl_title = QLabel("Keamanan Jaringan")
        lbl_ssl_title.setStyleSheet("border: none; background: transparent; font-weight: 600; color: #1E293B; font-size: 8.5pt;")
        ssl_lbl_row.addWidget(ssl_ico)
        ssl_lbl_row.addWidget(lbl_ssl_title)
        ssl_lbl_row.addStretch()

        self.ssl = QCheckBox("Verifikasi Sertifikat SSL/TLS")
        self.ssl.setChecked(False)

        lbl_ssl_hint = QLabel("Nonaktifkan jika menggunakan HTTP lokal")
        lbl_ssl_hint.setStyleSheet("color: #94A3B8; font-size: 8pt; font-weight: normal; border: none; background: transparent;")

        ssl_layout.addLayout(ssl_lbl_row)
        ssl_layout.addWidget(self.ssl)
        ssl_layout.addWidget(lbl_ssl_hint)
        row_opts.addLayout(ssl_layout, stretch=1)

        form_layout.addLayout(row_opts)
        main_layout.addWidget(form_card)

        # ------------------------------------------------------
        # Action Buttons
        # ------------------------------------------------------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_test = QPushButton("UJI KONEKSI SERVER")
        self.btn_test.setCursor(Qt.PointingHandCursor)
        self.btn_test.setIcon(QgsApplication.getThemeIcon("mIconConnect.svg"))
        self.btn_test.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #059669;
                border: 1.5px solid #10B981;
                border-radius: 7px;
                padding: 10px 18px;
                font-weight: 700;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background: #ECFDF5;
                color: #047857;
            }
            QPushButton:pressed {
                background: #D1FAE5;
            }
            QPushButton:disabled {
                background: #F8FAFC;
                color: #94A3B8;
                border-color: #E2E8F0;
            }
        """)

        self.btn_save = QPushButton("SIMPAN PENGATURAN")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setIcon(QgsApplication.getThemeIcon("mActionFileSave.svg"))
        self.btn_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 7px;
                padding: 10px 22px;
                font-weight: 700;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #059669, stop:1 #047857);
            }
            QPushButton:pressed {
                background: #047857;
            }
            QPushButton:disabled {
                background: #E2E8F0;
                color: #94A3B8;
            }
        """)

        btn_layout.addWidget(self.btn_test)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # ------------------------------------------------------
        # Progress Bar & Live Status Result Box
        # ------------------------------------------------------
        self.progress = QProgressBar()
        self.progress.setMaximum(0)
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #E2E8F0;
                border-radius: 1.5px;
            }
            QProgressBar::chunk {
                background: #10B981;
                border-radius: 1.5px;
            }
        """)
        self.progress.hide()
        main_layout.addWidget(self.progress)

        self.status_card = QFrame()
        self.status_card.setObjectName("statusCard")
        self.status_card.setStyleSheet("""
            QFrame#statusCard {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        card_layout = QVBoxLayout(self.status_card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)

        status_header = QHBoxLayout()
        status_header.setSpacing(8)
        self.lbl_status_icon = QLabel()
        self.lbl_status_icon.setFixedSize(18, 18)
        self.lbl_status_icon.setPixmap(QgsApplication.getThemeIcon("mIconInfo.svg").pixmap(18, 18))
        self.lbl_status_icon.setStyleSheet("border: none; background: transparent;")
        self.lbl_status_title = QLabel("Status Koneksi: Menunggu Pengujian")
        self.lbl_status_title.setStyleSheet("font-weight: bold; font-size: 9pt; color: #334155; border: none; background: transparent;")
        status_header.addWidget(self.lbl_status_icon)
        status_header.addWidget(self.lbl_status_title)
        status_header.addStretch()

        self.lbl_status_detail = QLabel("Klik tombol 'Uji Koneksi Server' untuk memverifikasi URL GeoNode.")
        self.lbl_status_detail.setStyleSheet("color: #64748B; font-size: 8.5pt; border: none; background: transparent;")
        self.lbl_status_detail.setWordWrap(True)

        card_layout.addLayout(status_header)
        card_layout.addWidget(self.lbl_status_detail)

        main_layout.addWidget(self.status_card)
        main_layout.addStretch()

    def set_loading(self, is_loading: bool, message: str = "Sedang memeriksa koneksi server..."):
        self.btn_test.setEnabled(not is_loading)
        self.btn_save.setEnabled(not is_loading)
        if is_loading:
            self.progress.show()
            self.status_card.setStyleSheet("""
                QFrame#statusCard {
                    background: #F0F9FF;
                    border: 1px solid #BAE6FD;
                    border-radius: 8px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            self.lbl_status_title.setStyleSheet("font-weight: bold; font-size: 9pt; color: #0284C7; border: none; background: transparent;")
            self.lbl_status_title.setText("Memeriksa Koneksi...")
            self.lbl_status_detail.setStyleSheet("color: #0369A1; font-size: 8.5pt; border: none; background: transparent;")
            self.lbl_status_detail.setText(message)
            self.lbl_status_icon.setPixmap(QgsApplication.getThemeIcon("mActionRefresh.svg").pixmap(18, 18))
        else:
            self.progress.hide()

    def show_success(self, title: str, details: str):
        self.status_card.setStyleSheet("""
            QFrame#statusCard {
                background: #ECFDF5;
                border: 1px solid #A7F3D0;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        self.lbl_status_title.setStyleSheet("font-weight: bold; font-size: 9pt; color: #065F46; border: none; background: transparent;")
        self.lbl_status_title.setText(title)
        self.lbl_status_detail.setStyleSheet("color: #047857; font-size: 8.5pt; border: none; background: transparent;")
        self.lbl_status_detail.setText(details)
        self.lbl_status_icon.setPixmap(QgsApplication.getThemeIcon("mIconSuccess.svg").pixmap(20, 20))

    def show_error(self, title: str, details: str):
        self.status_card.setStyleSheet("""
            QFrame#statusCard {
                background: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        self.lbl_status_title.setStyleSheet("font-weight: bold; font-size: 9pt; color: #991B1B; border: none; background: transparent;")
        self.lbl_status_title.setText(title)
        self.lbl_status_detail.setStyleSheet("color: #B91C1C; font-size: 8.5pt; border: none; background: transparent;")
        self.lbl_status_detail.setText(details)
        self.lbl_status_icon.setPixmap(QgsApplication.getThemeIcon("mIconCritical.svg").pixmap(20, 20))
"""
metadata_dialog.py

Dialog Editor Metadata (Mockup Screen 7).
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from qgis.PyQt.QtCore import Qt, QDate
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QDateEdit,
    QPushButton,
    QTabWidget,
    QWidget,
    QFormLayout,
    QMessageBox,
)

from ...models.layer import Layer
from ...services.activity_service import activity_service
from ...services.metadata_service import metadata_service
from ...models.session import session
from ...utils.logger import get_logger

logger = get_logger(__name__)


class MetadataDialog(QDialog):
    """
    Editor Metadata Dialog sesuai Mockup Screen 7.
    """

    def __init__(self, layer: Layer, parent=None):
        super().__init__(parent)
        self.layer = layer

        self.setWindowTitle(f"Metadata - {layer.display_name}")
        self.resize(560, 520)
        self.setMinimumSize(480, 420)

        self._setup_ui()
        self._load_layer_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Title Header
        title_label = QLabel(f"Metadata - {self.layer.display_name}")
        title_label.setStyleSheet("font-size: 15pt; font-weight: bold; color: #1e1e1e;")
        main_layout.addWidget(title_label)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                background: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: transparent;
                padding: 8px 14px;
                color: #555555;
                font-weight: 600;
                font-size: 8.5pt;
            }
            QTabBar::tab:selected {
                color: #2E9E55;
                border-bottom: 3px solid #2E9E55;
            }
        """)

        self.tab_info = self._create_info_tab()
        self.tab_kontak = self._create_kontak_tab()
        self.tab_klasifikasi = self._create_klasifikasi_tab()
        self.tab_kata_kunci = self._create_kata_kunci_tab()
        self.tab_lainnya = self._create_lainnya_tab()

        self.tabs.addTab(self.tab_info, "INFO DASAR")
        self.tabs.addTab(self.tab_kontak, "KONTAK")
        self.tabs.addTab(self.tab_klasifikasi, "KLASIFIKASI")
        self.tabs.addTab(self.tab_kata_kunci, "KATA KUNCI")
        self.tabs.addTab(self.tab_lainnya, "LAINNYA")

        main_layout.addWidget(self.tabs, stretch=1)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_update = QPushButton("UPDATE METADATA")
        self.btn_update.setCursor(Qt.PointingHandCursor)
        self.btn_update.setStyleSheet("""
            QPushButton {
                background-color: #2E9E55;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 10px 20px;
                border: none;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #268547;
            }
        """)
        self.btn_update.clicked.connect(self._on_update_clicked)

        self.btn_batal = QPushButton("BATAL")
        self.btn_batal.setCursor(Qt.PointingHandCursor)
        self.btn_batal.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #555555;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 9pt;
            }
            QPushButton:hover {
                border-color: #999999;
                background-color: #F8F8F8;
            }
        """)
        self.btn_batal.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_batal)
        main_layout.addLayout(btn_layout)

    def _create_info_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        input_style = """
            QLineEdit, QTextEdit, QComboBox, QDateEdit {
                border: 1px solid #D2D2D2;
                border-radius: 4px;
                padding: 6px;
                background: white;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #2E9E55;
            }
        """
        widget.setStyleSheet(input_style)

        self.txt_title = QLineEdit()
        layout.addRow("Judul", self.txt_title)

        self.txt_abstract = QTextEdit()
        self.txt_abstract.setMaximumHeight(85)
        layout.addRow("Abstrak", self.txt_abstract)

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Vector Data", "Raster Data"])
        layout.addRow("Tipe", self.cmb_type)

        self.cmb_category = QComboBox()
        self.cmb_category.addItems([
            "Transportasi",
            "Batas Administrasi",
            "Infrastruktur",
            "Lingkungan Hidup",
            "Perencanaan Tata Ruang",
            "Kependudukan",
            "Kebencanaan",
            "Lainnya",
        ])
        layout.addRow("Kategori", self.cmb_category)

        self.cmb_license = QComboBox()
        self.cmb_license.addItems([
            "CC BY 4.0",
            "CC BY-SA 4.0",
            "Public Domain (CC0)",
            "Open Data Commons (ODC)",
            "Hak Cipta Dilindungi",
        ])
        layout.addRow("Lisensi", self.cmb_license)

        self.date_published = QDateEdit()
        self.date_published.setCalendarPopup(True)
        self.date_published.setDate(QDate.currentDate())
        layout.addRow("Tanggal Publikasi", self.date_published)

        return widget

    def _create_kontak_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.txt_contact_name = QLineEdit()
        self.txt_contact_email = QLineEdit()
        self.txt_organization = QLineEdit()

        layout.addRow("Kontak Utama", self.txt_contact_name)
        layout.addRow("Email Kontak", self.txt_contact_email)
        layout.addRow("Institusi / OPD", self.txt_organization)
        return widget

    def _create_klasifikasi_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.cmb_access = QComboBox()
        self.cmb_access.addItems(["Publik (Terbuka)", "Terbatas (Pegawai)", "Privat"])
        self.txt_maintenance = QLineEdit("Sesuai Kebutuhan")

        layout.addRow("Aksesibilitas", self.cmb_access)
        layout.addRow("Frekuensi Pembaruan", self.txt_maintenance)
        return widget

    def _create_kata_kunci_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.txt_keywords = QLineEdit()
        self.txt_keywords.setPlaceholderText("Pisahkan dengan koma, contoh: jalan, transportasi, jogja")
        layout.addRow("Kata Kunci", self.txt_keywords)
        return widget

    def _create_lainnya_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.txt_srid = QLineEdit()
        self.txt_srid.setReadOnly(True)
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["Bahasa Indonesia (ind)", "English (eng)"])

        layout.addRow("Sistem Koordinat (CRS)", self.txt_srid)
        layout.addRow("Bahasa Metadata", self.cmb_lang)
        return widget

    def _load_layer_data(self):
        """
        Mengisi form dengan informasi dataset saat ini.
        """
        self.txt_title.setText(self.layer.title or self.layer.name)
        self.txt_abstract.setText(self.layer.abstract or "")

        if self.layer.is_raster:
            self.cmb_type.setCurrentText("Raster Data")
        else:
            self.cmb_type.setCurrentText("Vector Data")

        self.txt_contact_name.setText(self.layer.owner_username or "admin")
        self.txt_organization.setText("Pemerintah Kota Yogyakarta")
        self.txt_srid.setText(self.layer.srid or "EPSG:4326")

        if self.layer.created:
            d = self.layer.created
            self.date_published.setDate(QDate(d.year, d.month, d.day))

    def _on_update_clicked(self):
        """
        Menyimpan perubahan metadata via GeoNode REST API.
        """
        new_title = self.txt_title.text().strip()
        new_abstract = self.txt_abstract.toPlainText().strip()

        if not new_title:
            QMessageBox.warning(self, "Peringatan", "Judul dataset tidak boleh kosong.")
            return

        payload = {
            "title": new_title,
            "abstract": new_abstract,
        }

        pk = self.layer.pk or self.layer.id
        if pk:
            res = metadata_service.update_metadata(pk, payload)
            if not res.success:
                QMessageBox.warning(self, "Peringatan", f"Gagal memperbarui metadata di server:\n{res.message}")
                return

        self.layer.title = new_title
        self.layer.abstract = new_abstract

        QMessageBox.information(
            self,
            "Berhasil",
            f"Metadata untuk layer \"{new_title}\" berhasil diperbarui di GeoNode.",
        )
        self.accept()

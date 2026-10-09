"""
upload_wizard_dialog.py

Dialog Wizard Upload Dataset dan Input Metadata (Sprint 6 & Sprint 7).
Memungkinkan user memilih:
1. Mode: Updating Dataset Lama vs Kategori Dataset Baru
2. Input Metadata lengkap sesuai skema GeoNode (ISO 19115 / SNI ISO 19115)
3. Eksekusi upload dan monitoring progres
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from qgis.core import QgsVectorLayer, QgsProject, QgsApplication
from qgis.PyQt.QtCore import Qt, QDate, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QPushButton,
    QProgressBar,
    QStackedWidget,
    QFrame,
    QWidget,
    QFormLayout,
    QMessageBox,
    QScrollArea,
    QFileDialog,
    QCheckBox,
    QSizePolicy,
)

from ...services.upload_service import upload_service
from ...services.metadata_service import metadata_service
from ...services.layer_service import LayerService
from ...models.session import session
from ...utils.logger import get_logger

logger = get_logger(__name__)


class UploadWizardDialog(QDialog):
    """
    Wizard Dialog untuk Upload Dataset dan Pengisian Metadata GeoNode.
    """
    uploadCompleted = pyqtSignal(dict)

    def __init__(
        self,
        layer: Optional[QgsVectorLayer] = None,
        layer_service: Optional[LayerService] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.layer = layer
        self.layer_service = layer_service or LayerService()
        self.setWindowTitle("Upload Dataset & Kelola Metadata - GeoNode Connector")
        self.resize(750, 660)
        self.setMinimumSize(680, 560)

        self._all_datasets = []
        self._current_step = 0

        self._setup_ui()
        self._populate_qgis_layers()
        self._load_datasets_and_categories()
        self._prefill_from_layer()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 20, 22, 20)
        main_layout.setSpacing(16)

        # Header Title
        lbl_header = QLabel("Upload & Sinkronisasi Dataset ke GeoNode")
        lbl_header.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1E293B;")
        main_layout.addWidget(lbl_header)

        # Stepper Indicator
        self.stepper_widget = self._create_stepper()
        main_layout.addWidget(self.stepper_widget)

        # Stacked Pages
        self.pages_stack = QStackedWidget()
        self.page_1 = self._create_step1_page()
        self.page_2 = self._create_step2_page()
        self.page_3 = self._create_step3_page()

        self.pages_stack.addWidget(self.page_1)
        self.pages_stack.addWidget(self.page_2)
        self.pages_stack.addWidget(self.page_3)
        main_layout.addWidget(self.pages_stack, stretch=1)

        # Navigation Buttons
        btn_bar = QHBoxLayout()
        self.btn_prev = QPushButton("Kembali")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setIcon(QgsApplication.getThemeIcon("mActionArrowLeft.svg"))
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background: white;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
            }
            QPushButton:hover { background: #F1F5F9; }
        """)
        self.btn_prev.clicked.connect(self._on_prev_clicked)
        self.btn_prev.hide()

        btn_bar.addWidget(self.btn_prev)
        btn_bar.addStretch()

        self.btn_batal = QPushButton("Batal")
        self.btn_batal.setCursor(Qt.PointingHandCursor)
        self.btn_batal.setStyleSheet("""
            QPushButton {
                background: white;
                color: #64748B;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover { background: #F8FAFC; }
        """)
        self.btn_batal.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_batal)

        self.btn_next = QPushButton("Lanjut: Isi Metadata")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setIcon(QgsApplication.getThemeIcon("mActionArrowRight.svg"))
        self.btn_next.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
                color: white;
                font-weight: 700;
                border: none;
                border-radius: 6px;
                padding: 8px 22px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #059669, stop:1 #047857);
            }
        """)
        self.btn_next.clicked.connect(self._on_next_clicked)
        btn_bar.addWidget(self.btn_next)

        main_layout.addLayout(btn_bar)

    def _create_stepper(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 8)
        layout.setSpacing(8)

        steps = ["1. Sumber & Mode Ekspor", "2. Isian Metadata", "3. Upload & Selesai"]
        self.step_labels = []

        for i, name in enumerate(steps):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #94A3B8; font-size: 8.5pt; font-weight: 600; padding: 4px 8px;")
            layout.addWidget(lbl)
            self.step_labels.append(lbl)
            if i < len(steps) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setStyleSheet("color: #E2E8F0;")
                layout.addWidget(line, stretch=1)

        self._update_stepper_ui(0)
        return widget

    def _update_stepper_ui(self, step_idx: int):
        self._current_step = step_idx
        for i, lbl in enumerate(self.step_labels):
            if i == step_idx:
                lbl.setStyleSheet("color: white; background: #059669; font-size: 8.5pt; font-weight: bold; border-radius: 12px; padding: 4px 12px;")
            elif i < step_idx:
                lbl.setStyleSheet("color: #059669; font-size: 8.5pt; font-weight: bold; padding: 4px 8px;")
            else:
                lbl.setStyleSheet("color: #94A3B8; font-size: 8.5pt; font-weight: 500; padding: 4px 8px;")

    # ==========================================================
    # Step 1: Mode & Source Selection Page
    # ==========================================================

    def _create_step1_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        desc = QLabel("Pilih sumber layer spasial dari proyek QGIS atau file dari komputer, lalu tentukan apakah ingin mempublikasikan sebagai dataset baru atau memperbarui dataset yang sudah ada.")
        desc.setStyleSheet("color: #64748B; font-size: 8.5pt; border: none; background: transparent;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ------------------------------------------------------
        # Card 1: Sumber Data Spasial
        # ------------------------------------------------------
        src_box = QFrame()
        src_box.setObjectName("srcBox")
        src_box.setStyleSheet("""
            QFrame#srcBox {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#srcBox QLabel {
                border: none;
                background: transparent;
            }
            QFrame#srcBox QRadioButton {
                color: #1E293B;
                font-size: 8.5pt;
                font-weight: 500;
                border: none;
                background: transparent;
                spacing: 8px;
            }
            QFrame#srcBox QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        src_layout = QVBoxLayout(src_box)
        src_layout.setContentsMargins(18, 16, 18, 16)
        src_layout.setSpacing(12)

        lbl_src_title = QLabel("📍 Sumber Layer Spasial")
        lbl_src_title.setStyleSheet("font-weight: 700; font-size: 9.5pt; color: #0F172A; border: none; background: transparent;")
        src_layout.addWidget(lbl_src_title)

        self.btn_group_src = QButtonGroup(self)
        self.radio_src_qgis = QRadioButton("Pilih dari Layer Kanvas QGIS")
        self.radio_src_qgis.setChecked(True)
        self.radio_src_file = QRadioButton("Pilih File Spasial dari Disk (.gpkg, .shp, .geojson)")
        self.btn_group_src.addButton(self.radio_src_qgis)
        self.btn_group_src.addButton(self.radio_src_file)

        src_radio_row = QHBoxLayout()
        src_radio_row.setSpacing(20)
        src_radio_row.addWidget(self.radio_src_qgis)
        src_radio_row.addWidget(self.radio_src_file)
        src_radio_row.addStretch()
        src_layout.addLayout(src_radio_row)

        # Dropdown Layer QGIS
        self.cmb_qgis_layers = QComboBox()
        self.cmb_qgis_layers.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_qgis_layers.setMinimumContentsLength(25)
        self.cmb_qgis_layers.setStyleSheet("""
            QComboBox {
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 12px;
                background: #FFFFFF;
                color: #1E293B;
                font-size: 9pt;
            }
            QComboBox:hover {
                border-color: #94A3B8;
            }
            QComboBox:focus {
                border-color: #10B981;
            }
        """)
        self.cmb_qgis_layers.currentIndexChanged.connect(self._on_qgis_layer_selected)
        src_layout.addWidget(self.cmb_qgis_layers)

        # File Chooser Box
        self.file_chooser_box = QWidget()
        self.file_chooser_box.setStyleSheet("background: transparent; border: none;")
        fc_layout = QHBoxLayout(self.file_chooser_box)
        fc_layout.setContentsMargins(0, 0, 0, 0)
        fc_layout.setSpacing(8)

        self.txt_file_path = QLineEdit()
        self.txt_file_path.setPlaceholderText("Pilih file GeoPackage, Shapefile, atau GeoJSON...")
        self.txt_file_path.setReadOnly(True)
        self.txt_file_path.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 12px;
                background: #F8FAFC;
                color: #334155;
                font-size: 8.5pt;
            }
        """)

        self.btn_browse_file = QPushButton("Cari File...")
        self.btn_browse_file.setIcon(QgsApplication.getThemeIcon("mActionFileOpen.svg"))
        self.btn_browse_file.setCursor(Qt.PointingHandCursor)
        self.btn_browse_file.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #0F172A;
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 600;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background: #F1F5F9;
                border-color: #94A3B8;
            }
        """)
        self.btn_browse_file.clicked.connect(self._on_browse_file_clicked)

        fc_layout.addWidget(self.txt_file_path, stretch=1)
        fc_layout.addWidget(self.btn_browse_file)
        self.file_chooser_box.hide()
        src_layout.addWidget(self.file_chooser_box)

        # Chip Ringkasan Layer Terpilih
        self.lbl_layer_info = QLabel("Memuat informasi layer...")
        self.lbl_layer_info.setObjectName("layerInfoChip")
        self.lbl_layer_info.setWordWrap(True)
        self.lbl_layer_info.setStyleSheet("""
            QLabel#layerInfoChip {
                background-color: #ECFDF5;
                border: 1px solid #A7F3D0;
                border-radius: 6px;
                padding: 8px 12px;
                color: #065F46;
                font-size: 8.5pt;
            }
        """)
        src_layout.addWidget(self.lbl_layer_info)

        layout.addWidget(src_box)
        self.radio_src_qgis.toggled.connect(self._on_src_type_toggled)

        # ------------------------------------------------------
        # Card 2: Mode Publikasi ke GeoNode
        # ------------------------------------------------------
        mode_box = QFrame()
        mode_box.setObjectName("modeBox")
        mode_box.setStyleSheet("""
            QFrame#modeBox {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#modeBox QLabel {
                border: none;
                background: transparent;
            }
            QFrame#modeBox QRadioButton {
                color: #1E293B;
                font-size: 9pt;
                font-weight: 700;
                border: none;
                background: transparent;
                spacing: 8px;
            }
            QFrame#modeBox QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        mode_layout = QVBoxLayout(mode_box)
        mode_layout.setContentsMargins(18, 16, 18, 16)
        mode_layout.setSpacing(12)

        lbl_mode_title = QLabel("🚀 Tujuan Publikasi di GeoNode")
        lbl_mode_title.setStyleSheet("font-weight: 700; font-size: 9.5pt; color: #0F172A; border: none; background: transparent;")
        mode_layout.addWidget(lbl_mode_title)

        self.btn_group_mode = QButtonGroup(self)

        # Radio 1: Dataset Baru (Default)
        self.radio_new = QRadioButton("Publikasikan sebagai Dataset Baru (Ekspor Baru)")
        self.btn_group_mode.addButton(self.radio_new)
        mode_layout.addWidget(self.radio_new)

        self.frame_new_details = QWidget()
        self.frame_new_details.setStyleSheet("background: transparent; border: none;")
        layout_new = QVBoxLayout(self.frame_new_details)
        layout_new.setContentsMargins(24, 4, 0, 8)
        layout_new.setSpacing(8)

        lbl_id = QLabel("Nama Layer Identifier (*):")
        lbl_id.setStyleSheet("font-weight: 600; font-size: 8.5pt; color: #334155; border: none;")
        self.txt_new_identifier = QLineEdit()
        self.txt_new_identifier.setPlaceholderText("contoh: sebaran_fasilitas_kesehatan_2026")
        self.txt_new_identifier.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 12px;
                background: #FFFFFF;
                color: #1E293B;
                font-size: 9pt;
            }
            QLineEdit:hover { border-color: #94A3B8; }
            QLineEdit:focus { border-color: #10B981; }
        """)
        lbl_id_hint = QLabel("Hanya gunakan huruf kecil, angka, dan garis bawah tanpa spasi.")
        lbl_id_hint.setStyleSheet("color: #94A3B8; font-size: 8pt; border: none;")

        lbl_fmt = QLabel("Format Ekspor File (*):")
        lbl_fmt.setStyleSheet("font-weight: 600; font-size: 8.5pt; color: #334155; border: none; margin-top: 4px;")
        self.cmb_format = QComboBox()
        self.cmb_format.addItems([
            "GeoPackage (.gpkg) - Direkomendasikan",
            "GeoJSON (.geojson)",
            "ESRI Shapefile (.shp)",
        ])
        self.cmb_format.setStyleSheet("""
            QComboBox {
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 12px;
                background: #FFFFFF;
                color: #1E293B;
                font-size: 9pt;
            }
            QComboBox:hover { border-color: #94A3B8; }
            QComboBox:focus { border-color: #10B981; }
        """)

        layout_new.addWidget(lbl_id)
        layout_new.addWidget(self.txt_new_identifier)
        layout_new.addWidget(lbl_id_hint)
        layout_new.addWidget(lbl_fmt)
        layout_new.addWidget(self.cmb_format)
        mode_layout.addWidget(self.frame_new_details)

        # Divider halus
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #F1F5F9; border: none; max-height: 1px;")
        mode_layout.addWidget(sep)

        # Radio 2: Update Lama
        self.radio_update = QRadioButton("Perbarui dataset yang sudah ada sebelumnya")
        self.btn_group_mode.addButton(self.radio_update)
        mode_layout.addWidget(self.radio_update)

        self.frame_update_details = QWidget()
        self.frame_update_details.setStyleSheet("background: transparent; border: none;")
        layout_update = QVBoxLayout(self.frame_update_details)
        layout_update.setContentsMargins(24, 4, 0, 8)
        layout_update.setSpacing(8)

        lbl_target = QLabel("Pilih Dataset Target di GeoNode (*):")
        lbl_target.setStyleSheet("font-weight: 600; font-size: 8.5pt; color: #334155; border: none;")
        self.cmb_existing_datasets = QComboBox()
        self.cmb_existing_datasets.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_existing_datasets.setMinimumContentsLength(25)
        self.cmb_existing_datasets.setStyleSheet("""
            QComboBox {
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 12px;
                background: #FFFFFF;
                color: #1E293B;
                font-size: 9pt;
            }
            QComboBox:hover { border-color: #94A3B8; }
            QComboBox:focus { border-color: #10B981; }
        """)
        self.cmb_existing_datasets.currentIndexChanged.connect(self._on_existing_dataset_selected)

        lbl_update_hint = QLabel("Fitur dan geometri layer akan disinkronkan ke dataset yang dipilih di server.")
        lbl_update_hint.setStyleSheet("color: #94A3B8; font-size: 8pt; border: none;")

        layout_update.addWidget(lbl_target)
        layout_update.addWidget(self.cmb_existing_datasets)
        layout_update.addWidget(lbl_update_hint)
        mode_layout.addWidget(self.frame_update_details)

        layout.addWidget(mode_box)

        # ------------------------------------------------------
        # Card 3: Penyelarasan Style Simbologi (.sld)
        # ------------------------------------------------------
        style_box = QFrame()
        style_box.setObjectName("styleBox")
        style_box.setStyleSheet("""
            QFrame#styleBox {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#styleBox QLabel {
                border: none;
                background: transparent;
            }
            QFrame#styleBox QCheckBox {
                color: #1E293B;
                font-size: 8.5pt;
                font-weight: 600;
                border: none;
                background: transparent;
                spacing: 8px;
            }
        """)
        style_layout = QVBoxLayout(style_box)
        style_layout.setContentsMargins(18, 14, 18, 14)
        style_layout.setSpacing(10)

        lbl_style_title = QLabel("🎨 Penyelarasan Style Simbologi (.sld)")
        lbl_style_title.setStyleSheet("font-weight: 700; font-size: 9.5pt; color: #0F172A; border: none;")
        style_layout.addWidget(lbl_style_title)

        self.chk_include_style = QCheckBox("Ikutkan style simbologi layer dari QGIS ke GeoNode (.sld)")
        self.chk_include_style.setChecked(True)
        self.chk_include_style.setToolTip("Simbologi warna, ikon, dan label dari QGIS akan diekspor sebagai file SLD dan disinkronkan ke GeoNode.")
        style_layout.addWidget(self.chk_include_style)

        style_hint = QLabel("Format OGC Styled Layer Descriptor (.sld) akan dibuat otomatis dari layer aktif di QGIS dan dipasang sebagai default style di GeoNode.")
        style_hint.setStyleSheet("color: #64748B; font-size: 8pt; border: none;")
        style_hint.setWordWrap(True)
        style_layout.addWidget(style_hint)

        btn_row = QHBoxLayout()
        self.btn_export_sld = QPushButton("💾 Simpan Berkas .SLD ke Komputer...")
        self.btn_export_sld.setCursor(Qt.PointingHandCursor)
        self.btn_export_sld.setIcon(QgsApplication.getThemeIcon("mActionFileSave.svg"))
        self.btn_export_sld.setStyleSheet("""
            QPushButton {
                background: #F8FAFC;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 8.5pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #EDF2F7;
                color: #0F172A;
            }
        """)
        self.btn_export_sld.clicked.connect(self._on_export_sld_clicked)
        btn_row.addWidget(self.btn_export_sld)
        btn_row.addStretch()
        style_layout.addLayout(btn_row)

        layout.addWidget(style_box)
        layout.addStretch()

        self.radio_new.toggled.connect(self._on_mode_radio_toggled)
        self.radio_new.setChecked(True)
        self.frame_update_details.hide()

        scroll.setWidget(container)
        return scroll

    def _on_src_type_toggled(self, is_qgis: bool):
        self.cmb_qgis_layers.setVisible(is_qgis)
        self.file_chooser_box.setVisible(not is_qgis)

    def _on_mode_radio_toggled(self, is_new: bool):
        self.frame_new_details.setVisible(is_new)
        self.frame_update_details.setVisible(not is_new)
        if not is_new and hasattr(self, "cmb_existing_datasets"):
            self._on_existing_dataset_selected(self.cmb_existing_datasets.currentIndex())

    def _on_mode_toggled(self, is_update: bool):
        self.radio_update.setChecked(is_update)
        self.radio_new.setChecked(not is_update)

    # ==========================================================
    # Step 2: Metadata Input Page (Sprint 7)
    # ==========================================================

    def _create_step2_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        desc = QLabel("Lengkapi metadata dataset sesuai standar GeoNode & SNI/ISO 19115. Bidang dengan tanda (*) wajib diisi.")
        desc.setStyleSheet("color: #64748B; font-size: 8.5pt;")
        layout.addWidget(desc)

        # ------------------------------------------------------
        # Card Form Metadata (Modernized layout)
        # ------------------------------------------------------
        form_card = QFrame()
        form_card.setObjectName("metadataCard")
        form_card.setStyleSheet("""
            QFrame#metadataCard {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#metadataCard QLabel {
                border: none;
                background: transparent;
                color: #1E293B;
                font-size: 8.5pt;
                font-weight: 600;
            }
            QFrame#metadataCard QLineEdit,
            QFrame#metadataCard QTextEdit,
            QFrame#metadataCard QComboBox {
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 10px;
                background: #FFFFFF;
                color: #1E293B;
                font-size: 9pt;
            }
            QFrame#metadataCard QLineEdit:hover,
            QFrame#metadataCard QTextEdit:hover,
            QFrame#metadataCard QComboBox:hover {
                border-color: #94A3B8;
            }
            QFrame#metadataCard QLineEdit:focus,
            QFrame#metadataCard QTextEdit:focus,
            QFrame#metadataCard QComboBox:focus {
                border-color: #10B981;
                background: #FFFFFF;
            }
        """)
        card_layout = QVBoxLayout(form_card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(14)

        # 1. Judul Dataset
        v_title = QVBoxLayout()
        v_title.setSpacing(4)
        lbl_title = QLabel("Judul Dataset (*):")
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Judul dataset resmi yang mudah dipahami...")
        v_title.addWidget(lbl_title)
        v_title.addWidget(self.txt_title)
        card_layout.addLayout(v_title)

        # 2. Abstrak / Deskripsi
        v_abstract = QVBoxLayout()
        v_abstract.setSpacing(4)
        lbl_abstract = QLabel("Abstrak / Deskripsi Dataset (*):")
        self.txt_abstract = QTextEdit()
        self.txt_abstract.setFixedHeight(68)
        self.txt_abstract.setPlaceholderText("Deskripsi ringkas mengenai isi, cakupan wilayah, dan kegunaan data...")
        v_abstract.addWidget(lbl_abstract)
        v_abstract.addWidget(self.txt_abstract)
        card_layout.addLayout(v_abstract)

        # 3. Kategori Tema & Kata Kunci (2 Kolom berdampingan)
        row_cat_kw = QHBoxLayout()
        row_cat_kw.setSpacing(16)

        v_cat = QVBoxLayout()
        v_cat.setSpacing(4)
        lbl_cat = QLabel("Kategori Tema (Topic Category):")
        self.cmb_category = QComboBox()
        self.cmb_category.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_category.setMinimumContentsLength(20)
        v_cat.addWidget(lbl_cat)
        v_cat.addWidget(self.cmb_category)
        row_cat_kw.addLayout(v_cat, stretch=1)

        v_kw = QVBoxLayout()
        v_kw.setSpacing(4)
        lbl_kw = QLabel("Kata Kunci (Tags):")
        self.txt_keywords = QLineEdit()
        self.txt_keywords.setPlaceholderText("contoh: kantor, yogya, fasilitas")
        v_kw.addWidget(lbl_kw)
        v_kw.addWidget(self.txt_keywords)
        row_cat_kw.addLayout(v_kw, stretch=1)

        card_layout.addLayout(row_cat_kw)

        # 4. Tujuan Pembuatan (Purpose)
        v_purpose = QVBoxLayout()
        v_purpose.setSpacing(4)
        lbl_purpose = QLabel("Tujuan Pembuatan (Purpose):")
        self.txt_purpose = QLineEdit()
        self.txt_purpose.setPlaceholderText("Tujuan pembuatan atau pemanfaatan dataset ini...")
        v_purpose.addWidget(lbl_purpose)
        v_purpose.addWidget(self.txt_purpose)
        card_layout.addLayout(v_purpose)

        # Divider garis halus
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #F1F5F9; border: none; max-height: 1px;")
        card_layout.addWidget(div)

        # 5. Bahasa & Lisensi (2 Kolom berdampingan)
        row_lang_lic = QHBoxLayout()
        row_lang_lic.setSpacing(16)

        v_lang = QVBoxLayout()
        v_lang.setSpacing(4)
        lbl_lang = QLabel("Bahasa Metadata:")
        self.cmb_language = QComboBox()
        self.cmb_language.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_language.addItems(["ind (Bahasa Indonesia)", "eng (English)"])
        v_lang.addWidget(lbl_lang)
        v_lang.addWidget(self.cmb_language)
        row_lang_lic.addLayout(v_lang, stretch=1)

        v_lic = QVBoxLayout()
        v_lic.setSpacing(4)
        lbl_lic = QLabel("Lisensi Data:")
        self.cmb_license = QComboBox()
        self.cmb_license.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        for lic in metadata_service.get_licenses():
            self.cmb_license.addItem(lic["name"], lic["identifier"])
        v_lic.addWidget(lbl_lic)
        v_lic.addWidget(self.cmb_license)
        row_lang_lic.addLayout(v_lic, stretch=1)

        card_layout.addLayout(row_lang_lic)

        # 6. Frekuensi Pembaruan & Representasi Spasial (2 Kolom berdampingan)
        row_freq_spat = QHBoxLayout()
        row_freq_spat.setSpacing(16)

        v_freq = QVBoxLayout()
        v_freq.setSpacing(4)
        lbl_maint = QLabel("Frekuensi Pembaruan:")
        self.cmb_maintenance = QComboBox()
        self.cmb_maintenance.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        for k, v in metadata_service.get_maintenance_frequencies():
            self.cmb_maintenance.addItem(v, k)
        v_freq.addWidget(lbl_maint)
        v_freq.addWidget(self.cmb_maintenance)
        row_freq_spat.addLayout(v_freq, stretch=1)

        v_spat = QVBoxLayout()
        v_spat.setSpacing(4)
        lbl_spat = QLabel("Representasi Spasial:")
        self.cmb_spatial_repr = QComboBox()
        self.cmb_spatial_repr.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        for k, v in metadata_service.get_spatial_representations():
            self.cmb_spatial_repr.addItem(v, k)
        v_spat.addWidget(lbl_spat)
        v_spat.addWidget(self.cmb_spatial_repr)
        row_freq_spat.addLayout(v_spat, stretch=1)

        card_layout.addLayout(row_freq_spat)

        layout.addWidget(form_card)
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    # ==========================================================
    # Step 3: Execution & Monitoring Page
    # ==========================================================

    def _create_step3_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        self.lbl_exec_title = QLabel("Siap Mengunggah / Menyimpan Dataset")
        self.lbl_exec_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #1E293B;")
        layout.addWidget(self.lbl_exec_title)

        self.lbl_exec_desc = QLabel("Klik tombol 'Mulai Upload & Simpan' di bawah untuk mengeksekusi pengunggahan data dan pendaftaran metadata ke GeoNode.")
        self.lbl_exec_desc.setStyleSheet("color: #64748B; font-size: 8.5pt;")
        self.lbl_exec_desc.setWordWrap(True)
        layout.addWidget(self.lbl_exec_desc)

        # Progress Card
        prog_card = QFrame()
        prog_card.setObjectName("progCard")
        prog_card.setStyleSheet("""
            QFrame#progCard {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 16px;
            }
            QFrame#progCard QLabel {
                border: none;
                background: transparent;
            }
        """)
        prog_layout = QVBoxLayout(prog_card)
        prog_layout.setSpacing(12)

        self.lbl_progress_status = QLabel("Menunggu konfirmasi...")
        self.lbl_progress_status.setStyleSheet("font-size: 9pt; font-weight: 600; color: #334155;")
        prog_layout.addWidget(self.lbl_progress_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #E2E8F0;
                border-radius: 5px;
                border: none;
            }
            QProgressBar::chunk {
                background: #10B981;
                border-radius: 5px;
            }
        """)
        prog_layout.addWidget(self.progress_bar)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(140)
        self.txt_log.setStyleSheet("font-family: monospace; font-size: 8pt; background: #F8FAFC; border: 1px solid #CBD5E1;")
        prog_layout.addWidget(self.txt_log)

        layout.addWidget(prog_card)
        layout.addStretch()

        return widget

    # ==========================================================
    # Logic & Data Population
    # ==========================================================

    def _populate_qgis_layers(self):
        """Memuat seluruh vector layer dari kanvas proyek QGIS aktif."""
        if not hasattr(self, "cmb_qgis_layers"):
            return

        self.cmb_qgis_layers.blockSignals(True)
        self.cmb_qgis_layers.clear()

        project = QgsProject.instance()
        map_layers = project.mapLayers().values()
        vector_layers = [l for l in map_layers if isinstance(l, QgsVectorLayer) and l.isValid()]

        if not vector_layers:
            self.cmb_qgis_layers.addItem("- Tidak ada layer vektor aktif di kanvas QGIS -", None)
            self.cmb_qgis_layers.setEnabled(False)
            self.radio_src_file.setChecked(True)
            self._on_src_type_toggled(False)
        else:
            self.cmb_qgis_layers.setEnabled(True)
            selected_idx = 0
            for i, lyr in enumerate(vector_layers):
                feat_count = lyr.featureCount()
                geom_type = lyr.geometryType()
                geom_name = ["Titik", "Garis", "Poligon", "Tabel", "Lainnya"][min(int(geom_type), 4)]
                label = f"{lyr.name()} [{geom_name}, {feat_count} fitur]"
                self.cmb_qgis_layers.addItem(label, lyr)
                if self.layer and self.layer.id() == lyr.id():
                    selected_idx = i

            self.cmb_qgis_layers.setCurrentIndex(selected_idx)
            if not self.layer and vector_layers:
                self.layer = vector_layers[selected_idx]

        self.cmb_qgis_layers.blockSignals(False)
        self._update_layer_info()

    def _on_qgis_layer_selected(self, index: int):
        if index < 0 or not self.cmb_qgis_layers.isEnabled():
            return
        lyr = self.cmb_qgis_layers.itemData(index)
        if lyr and isinstance(lyr, QgsVectorLayer):
            self.layer = lyr
            self._update_layer_info()
            self._prefill_from_layer()

    def _on_browse_file_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File Spasial untuk Diekspor ke GeoNode",
            "",
            "File Spasial (*.gpkg *.shp *.geojson *.json);;GeoPackage (*.gpkg);;ESRI Shapefile (*.shp);;GeoJSON (*.geojson *.json)",
        )
        if not file_path:
            return

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        vlayer = QgsVectorLayer(file_path, base_name, "ogr")
        if not vlayer.isValid():
            QMessageBox.warning(self, "File Tidak Valid", f"Tidak dapat membaca data vektor dari file:\n{file_path}")
            return

        self.layer = vlayer
        self.txt_file_path.setText(file_path)
        self._update_layer_info()
        self._prefill_from_layer()

    def _update_layer_info(self):
        if not hasattr(self, "lbl_layer_info"):
            return

        if not self.layer or not self.layer.isValid():
            self.lbl_layer_info.setText("Belum ada layer yang dipilih.")
            self.lbl_layer_info.setStyleSheet("color: #94A3B8; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px; padding: 6px 12px; font-size: 8.5pt;")
            return

        name = self.layer.name()
        count = self.layer.featureCount()
        geom = self.layer.geometryType()
        geom_str = ["Point", "LineString", "Polygon", "Table", "Unknown"][min(int(geom), 4)]
        crs_auth = self.layer.crs().authid() or "Tidak diketahui"

        self.lbl_layer_info.setText(
            f"<b>✔ Layer Terpilih:</b> {name}<br>"
            f"• <b>Tipe Geometri:</b> {geom_str} &nbsp;|&nbsp; "
            f"<b>Fitur:</b> {count} &nbsp;|&nbsp; "
            f"<b>CRS:</b> {crs_auth}"
        )
        self.lbl_layer_info.setStyleSheet("color: #065F46; background: #ECFDF5; border: 1.5px solid #A7F3D0; border-radius: 6px; padding: 8px 12px; font-size: 8.5pt; font-weight: 500;")

    def _load_datasets_and_categories(self):
        """Memuat daftar dataset GeoNode dan kategori tema."""
        # 1. Kategori
        categories = metadata_service.get_categories()
        self.cmb_category.clear()
        self.cmb_category.addItem("- Pilih Kategori -", None)
        for cat in categories:
            desc = cat.get("gn_description") or cat.get("description") or cat.get("identifier")
            self.cmb_category.addItem(desc, cat.get("identifier"))

        # 2. Dataset yang ada
        try:
            # Gunakan cache dataset di memori jika sudah tersedia agar UI tidak membeku
            cached_layers = getattr(self.layer_service, "_layers", [])
            if not cached_layers:
                # Jika cache memori masih kosong, muat halaman pertama saja (cepat, tanpa timeout ratusan dataset)
                cached_layers = self.layer_service._dataset_api.get_datasets(page=1, page_size=100, fetch_all=False)
                if cached_layers:
                    self.layer_service._update_cache(cached_layers)

            # Jika layer aktif memiliki PK atau nama spesifik, pastikan ada dalam opsi
            target_ds = None
            if self.layer:
                layer_pk = self.layer.customProperty("geonode_pk")
                if not layer_pk:
                    m_path = re.search(r"[\\/]([^\\/]+)_(\d+)[\\/]", self.layer.source())
                    if m_path:
                        layer_pk = m_path.group(2)

                if layer_pk:
                    target_ds = self.layer_service.get(layer_pk)

            layers_to_show = list(cached_layers)
            if target_ds and target_ds not in layers_to_show:
                layers_to_show.insert(0, target_ds)

            if layers_to_show:
                self._all_datasets = layers_to_show
                self.cmb_existing_datasets.clear()
                for ds in self._all_datasets:
                    self.cmb_existing_datasets.addItem(f"{ds.display_name} ({ds.name})", ds)
        except Exception as e:
            logger.warning(f"Gagal memuat daftar layer: {e}")

    def _prefill_from_layer(self):
        """Mengisi nilai awal form dari layer aktif."""
        if not self.layer:
            self._update_layer_info()
            return

        name = self.layer.name()
        self.txt_title.setText(name.replace("_", " ").title())
        self.txt_new_identifier.setText("".join(c for c in name.lower() if c.isalnum() or c == "_"))
        self.txt_abstract.setText(f"Dataset {name} yang diekspor dan dikelola melalui GeoNode Connector QGIS.")
        self._update_layer_info()

        # Cek apakah layer ini cocok dengan dataset yang ada di GeoNode
        clean_layer_name = "".join(c for c in name.lower() if c.isalnum() or c == "_")
        layer_pk = self.layer.customProperty("geonode_pk")
        if not layer_pk:
            m_path = re.search(r"[\\/]([^\\/]+)_(\d+)[\\/]", self.layer.source())
            if m_path:
                layer_pk = m_path.group(2)

        is_match = False
        for i in range(self.cmb_existing_datasets.count()):
            ds = self.cmb_existing_datasets.itemData(i)
            if not ds:
                continue
            if (layer_pk and str(ds.pk) == str(layer_pk)) or (
                ds.name.lower() == clean_layer_name or ds.title.lower() == name.lower()
            ):
                self.cmb_existing_datasets.setCurrentIndex(i)
                self.radio_update.setChecked(True)
                is_match = True
                return

        # Jika bukan layer dari GeoNode (layer baru dari QGIS/file), aktifkan Publish Baru
        if not is_match:
            self.radio_new.setChecked(True)

    def _on_existing_dataset_selected(self, index: int):
        if index < 0 or index >= self.cmb_existing_datasets.count():
            return
        ds = self.cmb_existing_datasets.itemData(index)
        if not ds:
            return

        # Muat metadata dataset terpilih ke form Step 2
        raw_title = ds.title or ds.name or ""
        clean_title = raw_title.replace("_", " ").title() if ("_" in raw_title and " " not in raw_title) else raw_title
        self.txt_title.setText(clean_title)
        if ds.abstract and ds.abstract.lower() != "no abstract provided":
            self.txt_abstract.setText(ds.abstract)
        elif not self.txt_abstract.toPlainText().strip():
            self.txt_abstract.setText(f"Dataset {ds.title} yang dikelola melalui GeoNode Connector QGIS.")

        # Set kategori jika cocok
        cat = getattr(ds, "category", None)
        if cat:
            cat_id = cat if isinstance(cat, str) else cat.get("identifier")
            for c_idx in range(self.cmb_category.count()):
                if self.cmb_category.itemData(c_idx) == cat_id:
                    self.cmb_category.setCurrentIndex(c_idx)
                    break

    # ==========================================================
    # Navigation
    # ==========================================================

    def _on_prev_clicked(self):
        if self._current_step > 0:
            self._current_step -= 1
            self.pages_stack.setCurrentIndex(self._current_step)
            self._update_stepper_ui(self._current_step)
            self._update_nav_buttons()

    def _on_next_clicked(self):
        if self._current_step == 0:
            # Validasi nama jika mode baru
            if self.radio_new.isChecked():
                new_id = self.txt_new_identifier.text().strip()
                if not new_id:
                    QMessageBox.warning(self, "Peringatan", "Nama layer baru (Identifier) wajib diisi.")
                    return

            self._current_step = 1
            self.pages_stack.setCurrentIndex(1)
            self._update_stepper_ui(1)
            self._update_nav_buttons()

        elif self._current_step == 1:
            # Validasi Metadata Wajib
            meta = self._collect_metadata()
            is_valid, errs = metadata_service.validate_metadata(meta)
            if not is_valid:
                QMessageBox.warning(self, "Validasi Metadata", "Mohon lengkapi metadata wajib:\n• " + "\n• ".join(errs))
                return

            self._current_step = 2
            self.pages_stack.setCurrentIndex(2)
            self._update_stepper_ui(2)
            self._update_nav_buttons()

        elif self._current_step == 2:
            # Eksekusi proses upload
            self._start_upload_process()

    def _update_nav_buttons(self):
        self.btn_prev.setVisible(self._current_step > 0)
        if self._current_step == 0:
            self.btn_next.setText("Lanjut: Isi Metadata")
        elif self._current_step == 1:
            self.btn_next.setText("Lanjut: Konfirmasi Upload")
        elif self._current_step == 2:
            self.btn_next.setText("Mulai Upload & Simpan")

    def _collect_metadata(self) -> Dict[str, Any]:
        """Mengumpulkan isian metadata dari form Step 2."""
        keywords_str = self.txt_keywords.text().strip()
        keywords_list = [k.strip() for k in keywords_str.split(",") if k.strip()] if keywords_str else []

        meta = {
            "title": self.txt_title.text().strip(),
            "abstract": self.txt_abstract.toPlainText().strip(),
            "purpose": self.txt_purpose.text().strip() or None,
            "category": {"identifier": self.cmb_category.currentData()} if self.cmb_category.currentData() else None,
            "keywords": keywords_list,
            "language": "ind" if "ind" in self.cmb_language.currentText() else "eng",
            "license": {"identifier": self.cmb_license.currentData() or "not_specified"},
            "maintenance_frequency": self.cmb_maintenance.currentData(),
            "spatial_representation_type": self.cmb_spatial_repr.currentData(),
        }
        return meta

    # ==========================================================
    # Upload Execution
    # ==========================================================

    def _on_export_sld_clicked(self):
        """Menyimpan file .sld layer terpilih ke lokasi lokal di komputer."""
        if not self.layer or not self.layer.isValid():
            QMessageBox.warning(self, "Peringatan", "Silakan pilih layer spasial yang valid terlebih dahulu.")
            return

        safe_name = "".join(c for c in self.layer.name().lower() if c.isalnum() or c == "_") or "style"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Berkas SLD Simbologi QGIS",
            f"{safe_name}.sld",
            "Styled Layer Descriptor (*.sld);;Semua Berkas (*.*)",
        )
        if file_path:
            from ...services.style_service import style_service
            ok, res = style_service.export_sld_from_layer(self.layer, output_path=file_path)
            if ok:
                QMessageBox.information(
                    self,
                    "Berhasil",
                    f"Berkas style .sld berhasil disimpan ke:\n{file_path}\n\n"
                    "Berkas ini siap digunakan atau diimpor ke GeoServer / GeoNode.",
                )
            else:
                QMessageBox.critical(self, "Gagal", f"Gagal mengekspor file SLD:\n{res}")

    def _start_upload_process(self):
        if not self.layer:
            QMessageBox.warning(self, "Peringatan", "Layer tidak ditemukan di QGIS.")
            return

        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.btn_batal.setEnabled(False)
        self.txt_log.clear()

        meta = self._collect_metadata()
        include_style = self.chk_include_style.isChecked() if hasattr(self, "chk_include_style") else True

        def update_progress(pct: int, msg: str):
            self.progress_bar.setValue(pct)
            self.lbl_progress_status.setText(msg)
            self.txt_log.append(f"[{pct}%] {msg}")
            QgsApplication.processEvents()

        is_update_mode = self.radio_update.isChecked()

        if is_update_mode:
            ds = self.cmb_existing_datasets.currentData()
            if not ds:
                QMessageBox.warning(self, "Peringatan", "Silakan pilih dataset target terlebih dahulu.")
                self.btn_prev.setEnabled(True)
                self.btn_next.setEnabled(True)
                return

            res = upload_service.update_existing_dataset(
                layer=self.layer,
                target_pk=ds.pk,
                target_name=ds.name,
                metadata_dict=meta,
                include_style=include_style,
                progress_callback=update_progress,
            )
        else:
            fmt_str = self.cmb_format.currentText()
            fmt = "GPKG" if "GPKG" in fmt_str else ("GeoJSON" if "GeoJSON" in fmt_str else "Shapefile")
            res = upload_service.upload_new_dataset(
                layer=self.layer,
                dataset_name=self.txt_new_identifier.text().strip(),
                output_format=fmt,
                metadata_dict=meta,
                include_style=include_style,
                progress_callback=update_progress,
            )

        if res.success:
            self.progress_bar.setValue(100)
            self.lbl_progress_status.setText("Selesai! Berhasil diproses.")
            self.btn_next.setText("Selesai")
            self.btn_next.setEnabled(True)
            self.btn_next.clicked.disconnect()
            self.btn_next.clicked.connect(self.accept)
            QMessageBox.information(self, "Berhasil", res.message)
            self.uploadCompleted.emit(res.data or {})
        else:
            self.lbl_progress_status.setText("Proses gagal.")
            self.btn_prev.setEnabled(True)
            self.btn_next.setEnabled(True)
            self.btn_batal.setEnabled(True)
            QMessageBox.critical(self, "Gagal", res.message)

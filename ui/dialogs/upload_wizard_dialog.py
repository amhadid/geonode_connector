"""
upload_wizard_dialog.py

Dialog Wizard Upload Dataset dan Input Metadata (Sprint 6 & Sprint 7).
Memungkinkan user memilih:
1. Mode: Updating Dataset Lama vs Kategori Dataset Baru
2. Input Metadata lengkap sesuai skema GeoNode (ISO 19115 / SNI ISO 19115)
3. Eksekusi upload dan monitoring progres
"""

from __future__ import annotations

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
        self.resize(650, 600)
        self.setMinimumSize(580, 520)

        self._all_datasets = []
        self._current_step = 0

        self._setup_ui()
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

        steps = ["1. Pilihan Kategori", "2. Isian Metadata", "3. Upload & Selesai"]
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
    # Step 1: Mode Selection Page
    # ==========================================================

    def _create_step1_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)

        desc = QLabel("Pilih apakah hasil editing layer akan memperbarui dataset lama atau dipublikasikan sebagai dataset baru.")
        desc.setStyleSheet("color: #64748B; font-size: 9pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Mode Box
        mode_box = QFrame()
        mode_box.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        mode_layout = QVBoxLayout(mode_box)
        mode_layout.setSpacing(14)

        self.btn_group_mode = QButtonGroup(self)

        # Radio 1: Updating Dataset Lama
        self.radio_update = QRadioButton("Updating dataset lama sebelumnya")
        self.radio_update.setStyleSheet("font-weight: bold; font-size: 9.5pt; color: #1E293B;")
        self.btn_group_mode.addButton(self.radio_update)
        mode_layout.addWidget(self.radio_update)

        self.frame_update_details = QFrame()
        layout_update = QFormLayout(self.frame_update_details)
        layout_update.setContentsMargins(24, 0, 0, 0)
        self.cmb_existing_datasets = QComboBox()
        self.cmb_existing_datasets.setStyleSheet("padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px; background: white;")
        self.cmb_existing_datasets.currentIndexChanged.connect(self._on_existing_dataset_selected)
        layout_update.addRow("Pilih Dataset GeoNode:", self.cmb_existing_datasets)
        mode_layout.addWidget(self.frame_update_details)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #F1F5F9;")
        mode_layout.addWidget(sep)

        # Radio 2: Kategori Dataset Baru
        self.radio_new = QRadioButton("Kategori dataset baru (Publish Baru)")
        self.radio_new.setStyleSheet("font-weight: bold; font-size: 9.5pt; color: #1E293B;")
        self.btn_group_mode.addButton(self.radio_new)
        mode_layout.addWidget(self.radio_new)

        self.frame_new_details = QFrame()
        layout_new = QFormLayout(self.frame_new_details)
        layout_new.setContentsMargins(24, 0, 0, 0)
        layout_new.setSpacing(10)

        self.txt_new_identifier = QLineEdit()
        self.txt_new_identifier.setPlaceholderText("contoh: sebaran_posko_yogyakarta_2026")
        self.txt_new_identifier.setStyleSheet("padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px; background: white;")
        layout_new.addRow("Nama Layer (Identifier):", self.txt_new_identifier)

        self.cmb_format = QComboBox()
        self.cmb_format.addItems([
            "GeoPackage (.gpkg) - Direkomendasikan",
            "GeoJSON (.geojson)",
            "ESRI Shapefile (.shp)",
        ])
        self.cmb_format.setStyleSheet("padding: 6px; border: 1px solid #CBD5E1; border-radius: 4px; background: white;")
        layout_new.addRow("Format Upload:", self.cmb_format)

        mode_layout.addWidget(self.frame_new_details)

        layout.addWidget(mode_box)
        layout.addStretch()

        self.radio_update.toggled.connect(self._on_mode_toggled)
        self.radio_update.setChecked(True)

        return widget

    def _on_mode_toggled(self, is_update: bool):
        self.frame_update_details.setEnabled(is_update)
        self.frame_new_details.setEnabled(not is_update)
        if is_update:
            self._on_existing_dataset_selected(self.cmb_existing_datasets.currentIndex())

    # ==========================================================
    # Step 2: Metadata Input Page (Sprint 7)
    # ==========================================================

    def _create_step2_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        desc = QLabel("Lengkapi metadata dataset sesuai standar GeoNode & SNI/ISO 19115. Bidang dengan tanda (*) wajib diisi.")
        desc.setStyleSheet("color: #64748B; font-size: 8.5pt;")
        layout.addWidget(desc)

        form_card = QFrame()
        form_card.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 14px;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 6px;
                background: white;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #10B981;
            }
        """)
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(10)

        # 1. Judul (Wajib)
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Judul dataset yang mudah dipahami...")
        form_layout.addRow("Judul Dataset (*):", self.txt_title)

        # 2. Abstrak (Wajib)
        self.txt_abstract = QTextEdit()
        self.txt_abstract.setMaximumHeight(70)
        self.txt_abstract.setPlaceholderText("Deskripsi ringkas mengenai isi dan cakupan data...")
        form_layout.addRow("Abstrak / Deskripsi (*):", self.txt_abstract)

        # 3. Kategori Tema (GeoNode Categories)
        self.cmb_category = QComboBox()
        form_layout.addRow("Kategori Tema:", self.cmb_category)

        # 4. Kata Kunci (Keywords)
        self.txt_keywords = QLineEdit()
        self.txt_keywords.setPlaceholderText("Pisahkan dengan koma (contoh: kantor, yogya, fasilitas)")
        form_layout.addRow("Kata Kunci (Tags):", self.txt_keywords)

        # 5. Tujuan (Purpose)
        self.txt_purpose = QLineEdit()
        self.txt_purpose.setPlaceholderText("Tujuan pembuatan atau pemanfaatan dataset...")
        form_layout.addRow("Tujuan Pembuatan:", self.txt_purpose)

        # 6. Bahasa & Lisensi
        lang_lic_row = QHBoxLayout()
        self.cmb_language = QComboBox()
        self.cmb_language.addItems(["ind (Bahasa Indonesia)", "eng (English)"])

        self.cmb_license = QComboBox()
        for lic in metadata_service.get_licenses():
            self.cmb_license.addItem(lic["name"], lic["identifier"])

        lang_lic_row.addWidget(self.cmb_language, stretch=1)
        lang_lic_row.addWidget(self.cmb_license, stretch=1)
        form_layout.addRow("Bahasa / Lisensi:", lang_lic_row)

        # 7. Frekuensi Pembaruan & Representasi Spasial
        freq_repr_row = QHBoxLayout()
        self.cmb_maintenance = QComboBox()
        for k, v in metadata_service.get_maintenance_frequencies():
            self.cmb_maintenance.addItem(v, k)

        self.cmb_spatial_repr = QComboBox()
        for k, v in metadata_service.get_spatial_representations():
            self.cmb_spatial_repr.addItem(v, k)

        freq_repr_row.addWidget(self.cmb_maintenance, stretch=1)
        freq_repr_row.addWidget(self.cmb_spatial_repr, stretch=1)
        form_layout.addRow("Frekuensi / Tipe:", freq_repr_row)

        layout.addWidget(form_card)
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
        prog_card.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 16px;
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
            layers = self.layer_service.get_all() if hasattr(self.layer_service, "get_all") else getattr(self.layer_service, "layers", [])
            if layers:
                self._all_datasets = layers
                self.cmb_existing_datasets.clear()
                for ds in self._all_datasets:
                    self.cmb_existing_datasets.addItem(f"{ds.display_name} ({ds.name})", ds)
        except Exception as e:
            logger.warning(f"Gagal memuat daftar layer: {e}")

    def _prefill_from_layer(self):
        """Mengisi nilai awal form dari layer aktif."""
        if not self.layer:
            return

        name = self.layer.name()
        self.txt_title.setText(name.replace("_", " ").title())
        self.txt_new_identifier.setText("".join(c for c in name.lower() if c.isalnum() or c == "_"))
        self.txt_abstract.setText(f"Dataset hasil pembaruan dari layer {name} di QGIS.")

        # Cek apakah layer ini cocok dengan dataset yang ada di GeoNode
        clean_layer_name = "".join(c for c in name.lower() if c.isalnum() or c == "_")
        for i in range(self.cmb_existing_datasets.count()):
            ds = self.cmb_existing_datasets.itemData(i)
            if ds and (ds.name.lower() == clean_layer_name or ds.title.lower() == name.lower()):
                self.cmb_existing_datasets.setCurrentIndex(i)
                self.radio_update.setChecked(True)
                return

    def _on_existing_dataset_selected(self, index: int):
        if index < 0 or index >= self.cmb_existing_datasets.count():
            return
        ds = self.cmb_existing_datasets.itemData(index)
        if not ds:
            return

        # Muat metadata dataset terpilih ke form Step 2
        self.txt_title.setText(ds.title or ds.name)
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

    def _start_upload_process(self):
        if not self.layer:
            QMessageBox.warning(self, "Peringatan", "Layer tidak ditemukan di QGIS.")
            return

        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.btn_batal.setEnabled(False)
        self.txt_log.clear()

        meta = self._collect_metadata()

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

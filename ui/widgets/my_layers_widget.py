"""
my_layers_widget.py

Widget Layer Saya & Status Sinkronisasi (Mockup Screen 4 & Screen 5).
Menampilkan layer nyata yang telah diimpor dari GeoNode ke dalam QGIS.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

from qgis.core import QgsProject, QgsVectorLayer, QgsMapLayer, QgsApplication
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)

from ..dialogs.sync_dialog import SyncDialog
from ..dialogs.change_detail_dialog import ChangeDetailDialog
from ...models.session import session
from ...services.activity_service import activity_service
from ...services.sync_service import sync_service
from ...services.layer_service import LayerService
from ...utils.logger import get_logger

logger = get_logger(__name__)


class MyLayersWidget(QWidget):
    """
    Widget untuk menampilkan status layer yang telah diimpor ke QGIS
    dan memantau sinkronisasi perubahan (Mockup Screen 4 & Screen 5).
    """

    switchToDatasetRequested = pyqtSignal()

    def __init__(self, iface=None, layer_service: Optional[LayerService] = None, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.sync_service = sync_service
        self.layer_service = layer_service or LayerService()

        # State per layer: {layer_id: {"name": str, "source": str, "sync_time": str, "features": int, "crs": str, "is_synced": bool, "inserts": int, "updates": int, "deletes": int, "change_log": list}}
        self._imported_layers: Dict[str, Dict[str, Any]] = {}
        self._current_layer_id: Optional[str] = None
        self._connected_layer: Optional[QgsVectorLayer] = None

        self._setup_ui()
        self.sync_with_qgis_project()

        # Pantau jika ada layer yang ditambah atau dihapus dari project QGIS
        try:
            QgsProject.instance().layersAdded.connect(self._on_project_layers_changed)
            QgsProject.instance().layersRemoved.connect(self._on_project_layers_changed)
        except Exception:
            pass

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 16, 20, 16)
        self.main_layout.setSpacing(14)

        # ------------------------------------------------------
        # Top Selector Row
        # ------------------------------------------------------
        self.sel_row_widget = QWidget()
        sel_row = QHBoxLayout(self.sel_row_widget)
        sel_row.setContentsMargins(0, 0, 0, 0)
        sel_row.setSpacing(8)

        lbl_select = QLabel("Pilih Layer:")
        lbl_select.setStyleSheet("font-weight: bold; color: #334155; font-size: 8.5pt;")

        self.cmb_layer = QComboBox()
        self.cmb_layer.setStyleSheet("""
            QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 5px 10px;
                background: white;
                font-weight: 500;
                color: #1E293B;
            }
        """)
        self.cmb_layer.currentIndexChanged.connect(self._on_layer_selection_changed)

        self.btn_refresh_layers = QPushButton()
        self.btn_refresh_layers.setToolTip("Segarkan dari Canvas QGIS")
        self.btn_refresh_layers.setIcon(QgsApplication.getThemeIcon("mActionRefresh.svg"))
        self.btn_refresh_layers.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_layers.setFixedSize(32, 32)
        self.btn_refresh_layers.clicked.connect(self.sync_with_qgis_project)

        self.lbl_mode_status = QLabel("Mode: Tersinkron")
        self.lbl_mode_status.setAlignment(Qt.AlignCenter)
        self.lbl_mode_status.setStyleSheet("""
            QLabel {
                background: #ECFDF5;
                color: #065F46;
                border: 1px solid #A7F3D0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 8pt;
                font-weight: 700;
            }
        """)

        sel_row.addWidget(lbl_select)
        sel_row.addWidget(self.cmb_layer, stretch=1)
        sel_row.addWidget(self.btn_refresh_layers)
        sel_row.addWidget(self.lbl_mode_status)
        self.main_layout.addWidget(self.sel_row_widget)

        # ------------------------------------------------------
        # Header Info Row: Layer Name & Badge
        # ------------------------------------------------------
        self.header_card = QFrame()
        self.header_card.setStyleSheet("QFrame { background: transparent; }")
        header_layout = QHBoxLayout(self.header_card)
        header_layout.setContentsMargins(0, 4, 0, 4)

        self.lbl_layer_name = QLabel("Layer : -")
        self.lbl_layer_name.setStyleSheet("font-size: 11.5pt; font-weight: bold; color: #0F172A;")

        self.badge_sync = QLabel("Tersinkron")
        self.badge_sync.setAlignment(Qt.AlignCenter)
        self._update_badge_style(is_synced=True)

        header_layout.addWidget(self.lbl_layer_name)
        header_layout.addStretch()
        header_layout.addWidget(self.badge_sync)
        self.main_layout.addWidget(self.header_card)

        # ------------------------------------------------------
        # Empty State Card (When no layers are imported)
        # ------------------------------------------------------
        self.empty_card = QFrame()
        self.empty_card.setObjectName("emptyLayerCard")
        self.empty_card.setStyleSheet("""
            QFrame#emptyLayerCard {
                background: #F8FAFC;
                border: 1.5px dashed #CBD5E1;
                border-radius: 10px;
                padding: 30px 20px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        empty_layout = QVBoxLayout(self.empty_card)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(10)

        lbl_empty_icon = QLabel()
        lbl_empty_icon.setPixmap(QgsApplication.getThemeIcon("mActionDataSourceManager.svg").pixmap(48, 48))
        lbl_empty_icon.setAlignment(Qt.AlignCenter)
        lbl_empty_icon.setStyleSheet("border: none; background: transparent;")

        lbl_empty_title = QLabel("Belum Ada Layer yang Diimpor")
        lbl_empty_title.setAlignment(Qt.AlignCenter)
        lbl_empty_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #334155; border: none; background: transparent;")

        lbl_empty_desc = QLabel(
            "Layer yang Anda impor dari katalog GeoNode akan muncul di sini\n"
            "untuk pemantauan status data, jumlah fitur, dan sinkronisasi."
        )
        lbl_empty_desc.setAlignment(Qt.AlignCenter)
        lbl_empty_desc.setStyleSheet("color: #64748B; font-size: 8.5pt; border: none; background: transparent;")

        self.btn_go_dataset = QPushButton("BUKA KATALOG DATASET")
        self.btn_go_dataset.setCursor(Qt.PointingHandCursor)
        self.btn_go_dataset.setIcon(QgsApplication.getThemeIcon("mActionAddWfsLayer.svg"))
        self.btn_go_dataset.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
                color: white;
                font-weight: 700;
                font-size: 8.5pt;
                border: none;
                border-radius: 6px;
                padding: 9px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #059669, stop:1 #047857);
            }
        """)
        self.btn_go_dataset.clicked.connect(self.switchToDatasetRequested.emit)

        empty_layout.addWidget(lbl_empty_icon)
        empty_layout.addWidget(lbl_empty_title)
        empty_layout.addWidget(lbl_empty_desc)
        empty_layout.addSpacing(10)
        empty_layout.addWidget(self.btn_go_dataset, alignment=Qt.AlignCenter)

        self.main_layout.addWidget(self.empty_card)

        # ------------------------------------------------------
        # Container for View A (Synced - Screen 4)
        # ------------------------------------------------------
        self.view_synced = self._create_synced_view()
        self.main_layout.addWidget(self.view_synced, stretch=1)

        # ------------------------------------------------------
        # Container for View B (Unsynced - Screen 5)
        # ------------------------------------------------------
        self.view_unsynced = self._create_unsynced_view()
        self.main_layout.addWidget(self.view_unsynced, stretch=1)
        self.view_unsynced.hide()

        self._refresh_visibility()

    def _create_synced_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(16)

        # Info Card
        card = QFrame()
        card.setObjectName("infoCard")
        card.setStyleSheet("""
            QFrame#infoCard {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(4)

        self.lbl_sumber = self._create_info_item("Sumber", "-", card_layout, icon_name="mActionDataSourceManager.svg")
        self.lbl_sync_time = self._create_info_item("Terakhir Sync", "-", card_layout, icon_name="mActionHistory.svg")
        self.lbl_fitur = self._create_info_item("Fitur", "0", card_layout, icon_name="mActionOpenTable.svg")
        self.lbl_crs = self._create_info_item("CRS", "-", card_layout, icon_name="mActionSetProjection.svg")
        self.lbl_status_layer = self._create_info_item("Status", "Read Only", card_layout, icon_name="mIconSuccess.svg", add_divider=False)

        layout.addWidget(card)
        layout.addStretch()

        # Action Buttons (Screen 4 Bottom)
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_lihat_data = QPushButton("LIHAT DATA DI QGIS")
        self.btn_lihat_data.setCursor(Qt.PointingHandCursor)
        self.btn_lihat_data.setIcon(QgsApplication.getThemeIcon("mActionOpenTable.svg"))
        self.btn_lihat_data.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #059669;
                border: 1.5px solid #10B981;
                border-radius: 7px;
                padding: 10px;
                font-weight: 700;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background: #ECFDF5;
            }
        """)
        self.btn_lihat_data.clicked.connect(self._on_lihat_data_clicked)

        self.btn_upload_as_new = QPushButton("UPLOAD / SINKRONKAN KE GEONODE")
        self.btn_upload_as_new.setCursor(Qt.PointingHandCursor)
        self.btn_upload_as_new.setIcon(QgsApplication.getThemeIcon("mActionSharingExport.svg"))
        self.btn_upload_as_new.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 7px;
                padding: 10px;
                font-weight: 700;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #059669, stop:1 #047857);
            }
        """)
        self.btn_upload_as_new.clicked.connect(self._on_upload_wizard_clicked)

        self.btn_edit_meta = QPushButton("KELOLA METADATA GEONODE")
        self.btn_edit_meta.setCursor(Qt.PointingHandCursor)
        self.btn_edit_meta.setIcon(QgsApplication.getThemeIcon("mActionEditTable.svg"))
        self.btn_edit_meta.setStyleSheet("""
            QPushButton {
                background: white;
                color: #2563EB;
                border: 1.5px solid #93C5FD;
                border-radius: 7px;
                padding: 10px;
                font-weight: 700;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background: #EFF6FF;
            }
        """)
        self.btn_edit_meta.clicked.connect(self._on_edit_metadata_clicked)

        self.btn_hapus_layer = QPushButton("HAPUS LAYER DARI CANVAS")
        self.btn_hapus_layer.setCursor(Qt.PointingHandCursor)
        self.btn_hapus_layer.setIcon(QgsApplication.getThemeIcon("mActionDeleteSelected.svg"))
        self.btn_hapus_layer.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #DC2626;
                border: 1.5px solid #FECACA;
                border-radius: 7px;
                padding: 10px;
                font-weight: 700;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background: #FEF2F2;
                border-color: #EF4444;
            }
        """)
        self.btn_hapus_layer.clicked.connect(self._on_hapus_layer_clicked)

        btn_layout.addWidget(self.btn_lihat_data)
        btn_layout.addWidget(self.btn_upload_as_new)
        btn_layout.addWidget(self.btn_edit_meta)
        btn_layout.addWidget(self.btn_hapus_layer)
        layout.addLayout(btn_layout)

        return widget

    def _create_info_item(
        self,
        label: str,
        value: str,
        parent_layout: QVBoxLayout,
        icon_name: Optional[str] = None,
        add_divider: bool = True,
    ) -> QLabel:
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent; border: none;")
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(10)

        if icon_name:
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(16, 16)
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setPixmap(QgsApplication.getThemeIcon(icon_name).pixmap(14, 14))
            icon_lbl.setStyleSheet("border: none; background: transparent;")
            row.addWidget(icon_lbl)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #64748B; font-size: 8.5pt; font-weight: 500; border: none; background: transparent;")
        lbl.setFixedWidth(105 if icon_name else 120)

        val = QLabel(value)
        val.setStyleSheet("color: #0F172A; font-size: 8.5pt; font-weight: 600; border: none; background: transparent;")
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)

        row.addWidget(lbl)
        row.addWidget(val)
        row.addStretch()

        parent_layout.addWidget(row_widget)

        if add_divider:
            divider = QFrame()
            divider.setFrameShape(QFrame.HLine)
            divider.setFixedHeight(1)
            divider.setStyleSheet("background-color: #F1F5F9; border: none; max-height: 1px;")
            parent_layout.addWidget(divider)

        return val

    def _create_unsynced_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(12)

        lbl_perubahan = QLabel("Perubahan")
        lbl_perubahan.setStyleSheet("font-size: 9.5pt; font-weight: bold; color: #1E293B;")
        layout.addWidget(lbl_perubahan)

        # 3 Statistics Cards Box (Screen 5)
        stat_card = QFrame()
        stat_card.setObjectName("statCard")
        stat_card.setStyleSheet("""
            QFrame#statCard {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        stat_layout = QHBoxLayout(stat_card)
        stat_layout.setContentsMargins(12, 14, 12, 14)
        stat_layout.setSpacing(12)

        self.lbl_tambah_val = self._create_stat_column("Tambah", "0", "#059669", stat_layout)
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #E2E8F0;")
        stat_layout.addWidget(sep1)

        self.lbl_ubah_val = self._create_stat_column("Ubah", "0", "#D97706", stat_layout)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: #E2E8F0;")
        stat_layout.addWidget(sep2)

        self.lbl_hapus_val = self._create_stat_column("Hapus", "0", "#DC2626", stat_layout)

        layout.addWidget(stat_card)

        # Notice jika ada penambahan field baru
        self.banner_field_notice = QFrame()
        self.banner_field_notice.setObjectName("bannerFieldNotice")
        self.banner_field_notice.setStyleSheet("""
            QFrame#bannerFieldNotice {
                background: #EFF6FF;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        bfn_layout = QHBoxLayout(self.banner_field_notice)
        bfn_layout.setContentsMargins(10, 6, 10, 6)
        bfn_layout.setSpacing(8)

        ico_bfn = QLabel()
        ico_bfn.setPixmap(QgsApplication.getThemeIcon("mActionNewAttribute.svg").pixmap(16, 16))
        ico_bfn.setStyleSheet("border: none; background: transparent;")
        self.lbl_field_notice_text = QLabel("Field Baru Ditambahkan:")
        self.lbl_field_notice_text.setStyleSheet("color: #1D4ED8; font-size: 8.5pt; font-weight: 600; border: none; background: transparent;")
        bfn_layout.addWidget(ico_bfn)
        bfn_layout.addWidget(self.lbl_field_notice_text, stretch=1)
        self.banner_field_notice.hide()
        layout.addWidget(self.banner_field_notice)

        # Log Table
        self.table_changes = QTableWidget()
        self.table_changes.setColumnCount(5)
        self.table_changes.setHorizontalHeaderLabels(["ID FITUR", "JENIS", "WAKTU", "OLEH", "DETAIL"])
        self.table_changes.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_changes.setSelectionMode(QTableWidget.SingleSelection)
        self.table_changes.verticalHeader().setVisible(False)
        self.table_changes.cellDoubleClicked.connect(self._on_table_cell_double_clicked)
        self.table_changes.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                gridline-color: transparent;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                color: #64748B;
                font-weight: bold;
                font-size: 8pt;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #E2E8F0;
            }
            QTableWidget::item {
                padding: 4px 6px;
                border-bottom: 1px solid #F1F5F9;
                font-size: 8.5pt;
            }
        """)
        header = self.table_changes.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        layout.addWidget(self.table_changes, stretch=1)

        # Bottom Action Buttons
        bot_layout = QVBoxLayout()
        bot_layout.setSpacing(8)

        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(8)

        self.btn_sync_now = QPushButton("SINKRONISASI CEPAT")
        self.btn_sync_now.setCursor(Qt.PointingHandCursor)
        self.btn_sync_now.setIcon(QgsApplication.getThemeIcon("mActionReload.svg"))
        self.btn_sync_now.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #059669, stop:1 #047857);
            }
        """)
        self.btn_sync_now.clicked.connect(self._on_sync_now_clicked)

        self.btn_revert = QPushButton("BATALKAN PERUBAHAN")
        self.btn_revert.setCursor(Qt.PointingHandCursor)
        self.btn_revert.setIcon(QgsApplication.getThemeIcon("mActionDeleteSelected.svg"))
        self.btn_revert.setStyleSheet("""
            QPushButton {
                background: white;
                color: #DC2626;
                border: 1px solid #FECACA;
                border-radius: 6px;
                padding: 10px;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background: #FEF2F2;
            }
        """)
        self.btn_revert.clicked.connect(self._on_revert_clicked)

        btn_row1.addWidget(self.btn_sync_now, stretch=2)
        btn_row1.addWidget(self.btn_revert, stretch=1)

        self.btn_upload_wizard = QPushButton("UPLOAD / SINKRONKAN DENGAN METADATA WIZARD")
        self.btn_upload_wizard.setCursor(Qt.PointingHandCursor)
        self.btn_upload_wizard.setIcon(QgsApplication.getThemeIcon("mActionSharingExport.svg"))
        self.btn_upload_wizard.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #059669;
                border: 1.5px solid #10B981;
                border-radius: 6px;
                padding: 10px;
                font-weight: 700;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background: #ECFDF5;
            }
        """)
        self.btn_upload_wizard.clicked.connect(self._on_upload_wizard_clicked)

        bot_layout.addLayout(btn_row1)
        bot_layout.addWidget(self.btn_upload_wizard)
        layout.addLayout(bot_layout)

        return widget

    def _create_stat_column(self, title: str, value: str, val_color: str, parent_layout: QHBoxLayout) -> QLabel:
        col = QVBoxLayout()
        col.setAlignment(Qt.AlignCenter)
        col.setSpacing(2)

        lbl = QLabel(title)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #64748B; font-size: 8pt; font-weight: 500; border: none; background: transparent;")

        val = QLabel(value)
        val.setAlignment(Qt.AlignCenter)
        val.setStyleSheet(f"color: {val_color}; font-size: 14pt; font-weight: bold; border: none; background: transparent;")

        col.addWidget(lbl)
        col.addWidget(val)
        parent_layout.addLayout(col)
        return val

    def _update_badge_style(self, is_synced: bool):
        if is_synced:
            self.badge_sync.setText("Tersinkron")
            self.badge_sync.setStyleSheet("""
                QLabel {
                    background-color: #ECFDF5;
                    color: #065F46;
                    border: 1px solid #A7F3D0;
                    border-radius: 12px;
                    padding: 4px 14px;
                    font-size: 8pt;
                    font-weight: 700;
                }
            """)
        else:
            self.badge_sync.setText("Belum Disinkronkan")
            self.badge_sync.setStyleSheet("""
                QLabel {
                    background-color: #FEF2F2;
                    color: #991B1B;
                    border: 1px solid #FECACA;
                    border-radius: 12px;
                    padding: 4px 14px;
                    font-size: 8pt;
                    font-weight: 700;
                }
            """)

    def _refresh_visibility(self):
        """Menyesuaikan visibilitas card apakah ada layer atau kosong."""
        has_layers = len(self._imported_layers) > 0
        self.sel_row_widget.setVisible(has_layers)
        self.header_card.setVisible(has_layers)
        self.empty_card.setVisible(not has_layers)

        if not has_layers:
            self.view_synced.hide()
            self.view_unsynced.hide()
        else:
            self._render_current_layer()

    def showEvent(self, event):
        super().showEvent(event)
        self.sync_with_qgis_project()

    def _on_project_layers_changed(self, *args):
        self.sync_with_qgis_project()

    def _get_current_qgs_layer(self) -> Optional[QgsVectorLayer]:
        """
        Mengambil objek QgsVectorLayer dari project QGIS yang sedang aktif dipilih.
        """
        layer_id = self.cmb_layer.currentData()
        if not layer_id:
            return None

        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if layer and isinstance(layer, QgsVectorLayer):
            return layer

        # Fallback cari berdasarkan nama
        if layer_id in self._imported_layers:
            name = self._imported_layers[layer_id]["name"]
            for l in project.mapLayers().values():
                if isinstance(l, QgsVectorLayer) and l.name().lower() == name.lower():
                    return l

        return None

    def _disconnect_layer_signals(self):
        """Memutuskan koneksi signal dari layer yang sebelumnya dipantau."""
        if self._connected_layer is not None:
            try:
                layer = self._connected_layer
                layer.layerModified.disconnect(self._on_layer_data_modified)
                layer.editingStarted.disconnect(self._on_layer_data_modified)
                layer.editingStopped.disconnect(self._on_layer_data_modified)
                layer.featureAdded.disconnect(self._on_layer_data_modified)
                layer.featureDeleted.disconnect(self._on_layer_data_modified)
                layer.geometryChanged.disconnect(self._on_layer_data_modified)
                layer.attributeValueChanged.disconnect(self._on_layer_data_modified)
                layer.attributeAdded.disconnect(self._on_layer_data_modified)
                layer.attributeDeleted.disconnect(self._on_layer_data_modified)
                layer.updatedFields.disconnect(self._on_layer_data_modified)
            except (RuntimeError, Exception):
                pass
        self._connected_layer = None

    def _connect_layer_signals(self, layer: Optional[QgsVectorLayer]):
        """Menghubungkan signal modifikasi data dan skema layer agar UI terupdate secara reaktif."""
        self._disconnect_layer_signals()
        if not layer or not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            return

        self._connected_layer = layer
        try:
            layer.layerModified.connect(self._on_layer_data_modified)
            layer.editingStarted.connect(self._on_layer_data_modified)
            layer.editingStopped.connect(self._on_layer_data_modified)
            layer.featureAdded.connect(self._on_layer_data_modified)
            layer.featureDeleted.connect(self._on_layer_data_modified)
            layer.geometryChanged.connect(self._on_layer_data_modified)
            layer.attributeValueChanged.connect(self._on_layer_data_modified)
            layer.attributeAdded.connect(self._on_layer_data_modified)
            layer.attributeDeleted.connect(self._on_layer_data_modified)
            layer.updatedFields.connect(self._on_layer_data_modified)
        except Exception as err:
            logger.warning(f"Gagal menghubungkan signal edit layer: {err}")

    def _on_layer_data_modified(self, *args):
        """Dipanggil seketika saat ada fitur yang ditambah, diedit, atau dihapus di QGIS."""
        layer = self._connected_layer or self._get_current_qgs_layer()
        if not layer or not layer.isValid():
            return

        layer_id = self.cmb_layer.currentData()
        if not layer_id or layer_id not in self._imported_layers:
            return

        changes = self.sync_service.get_pending_changes(layer)
        is_synced = (changes["total"] == 0)

        data = self._imported_layers[layer_id]
        data["inserts"] = changes["inserts"]
        data["updates"] = changes["updates"]
        data["deletes"] = changes["deletes"]
        data["change_log"] = changes["change_log"]
        data["added_fields"] = changes.get("added_fields", [])
        data["is_synced"] = is_synced
        data["status"] = "Edit Mode" if layer.isEditable() else ("Tersinkron" if is_synced else "Dimodifikasi")

        self._render_current_layer()

    def sync_with_qgis_project(self):
        """
        Sinkronisasi otomatis dengan layer yang sedang aktif di Canvas QGIS.
        Mendeteksi perubahan lokal secara riil pada setiap layer.
        """
        project = QgsProject.instance()
        current_map_layers = project.mapLayers()

        # Bersihkan layer yang sudah tidak ada di Canvas
        active_ids = set(current_map_layers.keys())
        for l_id in list(self._imported_layers.keys()):
            if l_id not in active_ids:
                matching = [k for k, v in current_map_layers.items() if v.name() == self._imported_layers[l_id]["name"]]
                if not matching:
                    del self._imported_layers[l_id]

        # Scan semua layer GeoServer / WFS / OGR yang terbuka di QGIS
        for l_id, layer in current_map_layers.items():
            if not isinstance(layer, QgsVectorLayer):
                continue

            src = layer.source().lower()
            provider = layer.providerType().lower()
            if "geoserver" in src or "geonode" in src or provider in ("wfs", "ogr"):
                # Pastikan kompatibilitas WFS-T 1.0.0 & kredensial
                if provider == "wfs":
                    try:
                        self.sync_service._ensure_wfs_datasource_compatibility(layer)
                    except Exception as err:
                        logger.warning(f"Gagal memastikan kompatibilitas WFS: {err}")

                fc = layer.featureCount() if hasattr(layer, "featureCount") else 0
                crs_auth = layer.crs().authid() if hasattr(layer, "crs") else "EPSG:4326"
                provider_name = layer.providerType().upper()

                # Periksa pending changes secara nyata
                changes = self.sync_service.get_pending_changes(layer)
                is_synced = (changes["total"] == 0)

                existing = self._imported_layers.get(l_id, {})
                sync_time = existing.get("sync_time", datetime.now().strftime("%d/%m/%Y %H:%M"))

                self._imported_layers[l_id] = {
                    "name": layer.name(),
                    "source": f"GeoNode ({provider_name})",
                    "sync_time": sync_time,
                    "features": max(0, fc),
                    "crs": crs_auth,
                    "status": "Edit Mode" if layer.isEditable() else ("Tersinkron" if is_synced else "Dimodifikasi"),
                    "is_synced": is_synced,
                    "inserts": changes["inserts"],
                    "updates": changes["updates"],
                    "deletes": changes["deletes"],
                    "change_log": changes["change_log"],
                    "added_fields": changes.get("added_fields", []),
                }

        self.update_layer_list()

    def update_layer_list(self):
        """
        Memperbarui dropdown layer yang sedang aktif di QGIS.
        """
        self.cmb_layer.blockSignals(True)
        prev_id = self.cmb_layer.currentData()
        self.cmb_layer.clear()

        for l_id, data in self._imported_layers.items():
            self.cmb_layer.addItem(data["name"], l_id)

        # Pertahankan pilihan layer sebelumnya jika masih ada
        if prev_id:
            idx = self.cmb_layer.findData(prev_id)
            if idx >= 0:
                self.cmb_layer.setCurrentIndex(idx)
            elif self.cmb_layer.count() > 0:
                self.cmb_layer.setCurrentIndex(0)
        elif self.cmb_layer.count() > 0:
            self.cmb_layer.setCurrentIndex(0)

        self.cmb_layer.blockSignals(False)
        self._current_layer_id = self.cmb_layer.currentData()

        # Sambungkan signal pada layer yang sedang dipilih
        current_layer = self._get_current_qgs_layer()
        self._connect_layer_signals(current_layer)

        self._refresh_visibility()

    def register_imported_layer(
        self,
        layer_id: str,
        name: str,
        source_type: str = "WFS",
        crs: str = "EPSG:4326",
        features: int = 0
    ):
        """
        Mendaftarkan layer yang baru saja diimpor ke dalam daftar Layer Saya.
        """
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        self._imported_layers[layer_id] = {
            "name": name,
            "source": f"GeoNode ({source_type})",
            "sync_time": now_str,
            "features": features,
            "crs": crs,
            "status": "Read Only",
            "is_synced": True,
            "inserts": 0,
            "updates": 0,
            "deletes": 0,
            "change_log": [],
        }
        self.update_layer_list()

        # Set selection ke layer baru
        idx = self.cmb_layer.findData(layer_id)
        if idx >= 0:
            self.cmb_layer.setCurrentIndex(idx)

    def _on_layer_selection_changed(self, index: int):
        if index < 0:
            self._disconnect_layer_signals()
            return

        layer_id = self.cmb_layer.itemData(index)
        self._current_layer_id = layer_id

        layer = self._get_current_qgs_layer()
        self._connect_layer_signals(layer)

        if layer and layer_id in self._imported_layers:
            changes = self.sync_service.get_pending_changes(layer)
            is_synced = (changes["total"] == 0)
            self._imported_layers[layer_id]["inserts"] = changes["inserts"]
            self._imported_layers[layer_id]["updates"] = changes["updates"]
            self._imported_layers[layer_id]["deletes"] = changes["deletes"]
            self._imported_layers[layer_id]["change_log"] = changes["change_log"]
            self._imported_layers[layer_id]["added_fields"] = changes.get("added_fields", [])
            self._imported_layers[layer_id]["is_synced"] = is_synced
            self._imported_layers[layer_id]["status"] = (
                "Edit Mode" if layer.isEditable() else ("Tersinkron" if is_synced else "Dimodifikasi")
            )

        self._render_current_layer()

    def _render_current_layer(self):
        layer_id = self.cmb_layer.currentData()
        if not layer_id or layer_id not in self._imported_layers:
            return

        data = self._imported_layers[layer_id]
        self.lbl_layer_name.setText(f"Layer : {data['name']}")

        is_synced = data.get("is_synced", True)
        self._update_badge_style(is_synced)

        # Selalu perbarui angka statistik perubahan
        self.lbl_tambah_val.setText(str(data.get("inserts", 0)))
        self.lbl_ubah_val.setText(str(data.get("updates", 0)))
        self.lbl_hapus_val.setText(str(data.get("deletes", 0)))
        self._populate_changes_table(data.get("change_log", []))

        added_fields = data.get("added_fields", [])
        if added_fields and not is_synced:
            self.lbl_field_notice_text.setText(f"Field Baru Ditambahkan: {', '.join(added_fields)}")
            self.banner_field_notice.show()
        else:
            self.banner_field_notice.hide()

        if is_synced:
            self.view_synced.show()
            self.view_unsynced.hide()
            self.lbl_mode_status.setText("Mode: Tersinkron")
            self.lbl_mode_status.setStyleSheet("""
                QLabel {
                    background: #ECFDF5;
                    color: #065F46;
                    border: 1px solid #A7F3D0;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 8pt;
                    font-weight: 700;
                }
            """)

            self.lbl_sumber.setText(data["source"])
            self.lbl_sync_time.setText(data["sync_time"])
            self.lbl_fitur.setText(f"{data['features']:,}".replace(",", "."))
            self.lbl_crs.setText(data["crs"])
            self.lbl_status_layer.setText(data["status"])
        else:
            self.view_synced.hide()
            self.view_unsynced.show()
            self.lbl_mode_status.setText("Mode: Belum Disinkron")
            self.lbl_mode_status.setStyleSheet("""
                QLabel {
                    background: #FEF2F2;
                    color: #991B1B;
                    border: 1px solid #FECACA;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 8pt;
                    font-weight: 700;
                }
            """)

    def _populate_changes_table(self, changes: List[Dict[str, Any]]):
        self._current_changes = changes
        self.table_changes.setRowCount(len(changes))
        for row, item in enumerate(changes):
            id_item = QTableWidgetItem(str(item.get("id", "-")))
            jenis_item = QTableWidgetItem(str(item.get("jenis", "")))
            jenis = str(item.get("jenis", ""))
            if "Field" in jenis:
                jenis_item.setForeground(Qt.blue)
            elif "Ubah" in jenis:
                jenis_item.setForeground(Qt.darkYellow)
            elif "Tambah" in jenis:
                jenis_item.setForeground(Qt.darkGreen)
            elif "Hapus" in jenis:
                jenis_item.setForeground(Qt.red)

            waktu_item = QTableWidgetItem(str(item.get("waktu", "-")))
            oleh_item = QTableWidgetItem(str(item.get("oleh", "-")))

            self.table_changes.setItem(row, 0, id_item)
            self.table_changes.setItem(row, 1, jenis_item)
            self.table_changes.setItem(row, 2, waktu_item)
            self.table_changes.setItem(row, 3, oleh_item)

            # Tombol Lihat Detail Perubahan
            btn_detail = QPushButton("Detail")
            btn_detail.setIcon(QgsApplication.getThemeIcon("mActionPropertyItem.svg"))
            btn_detail.setToolTip("Klik untuk melihat rincian lengkap perubahan")
            btn_detail.setCursor(Qt.PointingHandCursor)
            btn_detail.setStyleSheet("""
                QPushButton {
                    background: #F1F5F9;
                    color: #0F172A;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 8pt;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #ECFDF5;
                    color: #059669;
                    border-color: #10B981;
                }
            """)
            btn_detail.clicked.connect(lambda checked=False, ch=item: self._show_change_detail(ch))

            cell_widget = QWidget()
            cell_widget.setStyleSheet("background: transparent; border: none;")
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(4, 2, 4, 2)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(btn_detail)
            self.table_changes.setCellWidget(row, 4, cell_widget)

    def _show_change_detail(self, change_data: Dict[str, Any]):
        """Membuka dialog rincian lengkap perubahan fitur atau field."""
        dlg = ChangeDetailDialog(change_data, parent=self)
        dlg.exec_()

    def _on_table_cell_double_clicked(self, row: int, col: int):
        """Membuka detail perubahan ketika baris tabel di-klik ganda."""
        if hasattr(self, "_current_changes") and 0 <= row < len(self._current_changes):
            self._show_change_detail(self._current_changes[row])

    def _on_toggle_mode_clicked(self):
        """Mode tombol sekarang bersifat statis/indikator saja."""
        pass

    def _on_lihat_data_clicked(self):
        """
        Membuka tabel atribut di QGIS dan zoom ke layer.
        """
        layer = self._get_current_qgs_layer()
        name = self.cmb_layer.currentText()

        if layer and self.iface:
            self.iface.setActiveLayer(layer)
            self.iface.zoomToActiveLayer()
            self.iface.showAttributeTable(layer)
        else:
            QMessageBox.information(
                self,
                "Lihat Data",
                f"Layer '{name}' sedang aktif di canvas QGIS.",
            )

    def _on_hapus_layer_clicked(self):
        layer = self._get_current_qgs_layer()
        layer_id = self.cmb_layer.currentData()
        name = self.cmb_layer.currentText()

        reply = QMessageBox.question(
            self,
            "Hapus Layer",
            f"Apakah Anda yakin ingin menghapus layer '{name}' dari proyek QGIS?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._disconnect_layer_signals()
            project = QgsProject.instance()
            if layer:
                project.removeMapLayer(layer.id())
            elif layer_id:
                project.removeMapLayer(layer_id)

            if layer_id in self._imported_layers:
                del self._imported_layers[layer_id]

            self.update_layer_list()
            QMessageBox.information(self, "Berhasil", f"Layer '{name}' berhasil dihapus dari canvas.")

    def _on_sync_now_clicked(self):
        """
        Mengeksekusi proses sinkronisasi perubahan riil ke GeoNode via WFS-T.
        """
        layer = self._get_current_qgs_layer()
        if not layer:
            QMessageBox.warning(self, "Peringatan", "Layer tidak ditemukan di Canvas QGIS.")
            return

        changes = self.sync_service.get_pending_changes(layer)
        if changes["total"] == 0:
            QMessageBox.information(
                self,
                "Sinkronisasi",
                f"Layer '{layer.name()}' sudah tersinkronisasi. Tidak ada perubahan lokal yang perlu disimpan.",
            )
            return

        dlg = SyncDialog(
            layer=layer,
            sync_service_instance=self.sync_service,
            parent=self,
        )
        dlg.syncCompleted.connect(self._on_sync_success)
        dlg.exec_()

    def _on_sync_success(self):
        """Dipanggil setelah dialog sinkronisasi selesai dan berhasil."""
        layer = self._get_current_qgs_layer()
        layer_id = self.cmb_layer.currentData()
        if layer_id in self._imported_layers:
            self._imported_layers[layer_id]["is_synced"] = True
            self._imported_layers[layer_id]["sync_time"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            self._imported_layers[layer_id]["inserts"] = 0
            self._imported_layers[layer_id]["updates"] = 0
            self._imported_layers[layer_id]["deletes"] = 0
            self._imported_layers[layer_id]["change_log"] = []
            if layer:
                self._imported_layers[layer_id]["features"] = max(0, layer.featureCount())
                self._imported_layers[layer_id]["status"] = "Edit Mode" if layer.isEditable() else "Tersinkron"
            self._render_current_layer()

    def _on_revert_clicked(self):
        """
        Membatalkan seluruh perubahan lokal yang belum dikomit (rollback).
        """
        layer = self._get_current_qgs_layer()
        if not layer:
            QMessageBox.warning(self, "Peringatan", "Layer tidak ditemukan di Canvas QGIS.")
            return

        name = layer.name()
        reply = QMessageBox.question(
            self,
            "Batalkan Perubahan",
            f"Apakah Anda yakin ingin membatalkan semua perubahan yang belum disimpan pada layer '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        res = self.sync_service.revert_changes(layer)
        if res.success:
            layer_id = self.cmb_layer.currentData()
            if layer_id in self._imported_layers:
                self._imported_layers[layer_id]["is_synced"] = True
                self._imported_layers[layer_id]["inserts"] = 0
                self._imported_layers[layer_id]["updates"] = 0
                self._imported_layers[layer_id]["deletes"] = 0
                self._imported_layers[layer_id]["change_log"] = []
                self._imported_layers[layer_id]["status"] = "Tersinkron"
                self._render_current_layer()
            QMessageBox.information(self, "Berhasil", res.message)
        else:
            QMessageBox.warning(self, "Gagal", res.message)

    def _on_upload_wizard_clicked(self):
        """Membuka dialog wizard upload dataset dan metadata (Sprint 6 & 7)."""
        layer = self._get_current_qgs_layer()
        if not layer:
            QMessageBox.warning(self, "Peringatan", "Silakan pilih layer terlebih dahulu di daftar layer.")
            return

        from ..dialogs.upload_wizard_dialog import UploadWizardDialog
        dlg = UploadWizardDialog(layer=layer, layer_service=self.layer_service, parent=self)
        dlg.uploadCompleted.connect(self._on_upload_completed)
        dlg.exec_()

    def _on_upload_completed(self, data: dict):
        """Dipanggil setelah upload dataset atau update metadata berhasil."""
        layer = self._get_current_qgs_layer()
        layer_id = self.cmb_layer.currentData()
        if layer_id in self._imported_layers:
            self._imported_layers[layer_id]["is_synced"] = True
            self._imported_layers[layer_id]["sync_time"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            self._imported_layers[layer_id]["inserts"] = 0
            self._imported_layers[layer_id]["updates"] = 0
            self._imported_layers[layer_id]["deletes"] = 0
            self._imported_layers[layer_id]["change_log"] = []
            if layer:
                self._imported_layers[layer_id]["features"] = max(0, layer.featureCount())
                self._imported_layers[layer_id]["status"] = "Tersinkron"
            self._render_current_layer()
        self.update_layer_list()

    def _on_edit_metadata_clicked(self):
        """Membuka dialog editor metadata untuk layer terpilih."""
        layer = self._get_current_qgs_layer()
        if not layer:
            QMessageBox.warning(self, "Peringatan", "Silakan pilih layer terlebih dahulu.")
            return

        # Cari model Layer yang sesuai dari cache / server
        target_layer_model = None
        clean_name = "".join(c for c in layer.name().lower() if c.isalnum() or c == "_")
        try:
            layers_list = self.layer_service.layers if hasattr(self.layer_service, "layers") else self.layer_service.get_all()
        except Exception:
            layers_list = []

        for lyr in layers_list:
            if lyr.name.lower() == clean_name or lyr.title.lower() == layer.name().lower():
                target_layer_model = lyr
                break

        if not target_layer_model:
            # Jika belum dicache atau layer baru, buka via UploadWizardDialog
            self._on_upload_wizard_clicked()
            return

        from ..dialogs.metadata_dialog import MetadataDialog
        dlg = MetadataDialog(layer=target_layer_model, parent=self)
        dlg.exec_()


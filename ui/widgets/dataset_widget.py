"""
dataset_widget.py

Widget Browser Dataset GeoNode (Mockup Screen 3).

Modernized with sleek UI, custom pill badges, notification banner,
and refined table rows.
"""

from __future__ import annotations

from typing import Optional, List
from datetime import datetime

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt, pyqtSignal, QTimer, QPoint
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTableView,
    QHeaderView,
    QProgressBar,
    QFrame,
    QMenu,
)
from qgis.PyQt.QtGui import QColor, QFont

from ...models.layer import Layer
from ..models.dataset_table_model import DatasetTableModel, DatasetProxyModel
from ...utils.style_loader import StyleLoader
from ...utils.logger import get_logger

logger = get_logger(__name__)


class DatasetWidget(QWidget):
    """
    Browser Dataset Widget dengan UI modern dan responsif.
    """

    # Signals
    searchRequested = pyqtSignal(str)
    refreshRequested = pyqtSignal()
    layerActivated = pyqtSignal(str)
    layerSelected = pyqtSignal(str)
    importRequested = pyqtSignal(str)
    detailRequested = pyqtSignal(str)
    exportRequested = pyqtSignal()
    importWmsRequested = pyqtSignal(str)
    importWfsRequested = pyqtSignal(str)
    importGpkgRequested = pyqtSignal(str)
    importGeoJsonRequested = pyqtSignal(str)
    importShapefileRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layers: List[Layer] = []
        self._selected_pk: Optional[str] = None

        self._setup_ui()
        self._connect_signals()
        StyleLoader.apply(self, "dataset.qss")

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(10)

        # 1. Notification / Toast Banner (hidden by default)
        self._create_notification_banner()

        # 2. Search Bar Row
        self._create_search_bar()

        # 3. Dataset Table
        self._create_table()

        # 4. Bottom Action Buttons
        self._create_action_buttons()

        # 5. Status Bar
        self._create_statusbar()

    def _create_notification_banner(self):
        """
        Banner notifikasi inline modern untuk feedback sukses/error.
        """
        self.banner = QFrame()
        self.banner.setFixedHeight(40)
        self.banner.hide()

        b_layout = QHBoxLayout(self.banner)
        b_layout.setContentsMargins(12, 4, 8, 4)
        b_layout.setSpacing(8)

        self.lbl_banner_icon = QLabel("✅")
        self.lbl_banner_icon.setStyleSheet("font-size: 11pt;")

        self.lbl_banner_text = QLabel("Operasi berhasil.")
        self.lbl_banner_text.setStyleSheet("font-size: 8.5pt; font-weight: 500;")

        self.btn_banner_close = QPushButton("✕")
        self.btn_banner_close.setCursor(Qt.PointingHandCursor)
        self.btn_banner_close.setFixedSize(20, 20)
        self.btn_banner_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #64748B;
                font-weight: bold;
                font-size: 9pt;
            }
            QPushButton:hover {
                color: #0F172A;
            }
        """)
        self.btn_banner_close.clicked.connect(self.banner.hide)

        b_layout.addWidget(self.lbl_banner_icon)
        b_layout.addWidget(self.lbl_banner_text, stretch=1)
        b_layout.addWidget(self.btn_banner_close)

        self.main_layout.addWidget(self.banner)

    def show_notification(self, message: str, is_error: bool = False, duration_ms: int = 5000):
        """
        Menampilkan notifikasi modern dengan timeout.
        """
        if is_error:
            self.lbl_banner_icon.setPixmap(
                QgsApplication.getThemeIcon("mIconCritical.svg").pixmap(18, 18)
            )
            self.lbl_banner_text.setText(message)
            self.banner.setStyleSheet("""
                QFrame {
                    background-color: #FEF2F2;
                    border: 1px solid #FECACA;
                    border-radius: 6px;
                }
                QLabel {
                    color: #991B1B;
                }
            """)
        else:
            self.lbl_banner_icon.setPixmap(
                QgsApplication.getThemeIcon("mIconSuccess.svg").pixmap(18, 18)
            )
            self.lbl_banner_text.setText(message)
            self.banner.setStyleSheet("""
                QFrame {
                    background-color: #ECFDF5;
                    border: 1px solid #A7F3D0;
                    border-radius: 6px;
                }
                QLabel {
                    color: #065F46;
                }
            """)

        self.banner.show()
        if duration_ms > 0:
            QTimer.singleShot(duration_ms, self.banner.hide)

    def _create_search_bar(self):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("searchEdit")
        self.search_edit.setPlaceholderText("Cari dataset spasial...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedHeight(36)
        self.search_edit.addAction(
            QgsApplication.getThemeIcon("search.svg"),
            QLineEdit.LeadingPosition
        )

        # Refresh button
        self.refresh_button = QPushButton()
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setIcon(QgsApplication.getThemeIcon("mActionRefresh.svg"))
        self.refresh_button.setToolTip("Segarkan daftar dataset")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setFixedSize(36, 36)

        layout.addWidget(self.search_edit, stretch=1)
        layout.addWidget(self.refresh_button)

        self.main_layout.addLayout(layout)

    def _create_table(self):
        self.table_view = QTableView(self)
        self.source_model = DatasetTableModel(self)
        self.proxy_model = DatasetProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.table_view.setModel(self.proxy_model)

        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setShowGrid(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(46)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table_view.setColumnWidth(0, 36)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)

        # Backward compatibility alias
        self.table = self.table_view

        self.main_layout.addWidget(self.table_view, stretch=1)

    def _create_action_buttons(self):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        # Import button + dropdown arrow group
        import_btn_layout = QHBoxLayout()
        import_btn_layout.setSpacing(2)

        # 1. IMPORT LAYER Button (Emerald gradient)
        self.btn_import = QPushButton("IMPORT LAYER")
        self.btn_import.setObjectName("importButton")
        self.btn_import.setIcon(QgsApplication.getThemeIcon("mActionAddWfsLayer.svg"))
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.setEnabled(False)

        # Format Options Menu
        self.import_menu = QMenu(self)
        self.import_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px;
                font-size: 8.5pt;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
                color: #1E293B;
            }
            QMenu::item:selected {
                background-color: #ECFDF5;
                color: #059669;
                font-weight: 600;
            }
        """)

        self.act_import_wfs = self.import_menu.addAction(
            QgsApplication.getThemeIcon("mActionAddWfsLayer.svg"),
            "Live WFS (OWS Vector) — [Disarankan]"
        )
        self.act_import_gpkg = self.import_menu.addAction(
            QgsApplication.getThemeIcon("mActionAddOgrLayer.svg"),
            "GeoPackage (.gpkg) — [Standard Cache Native]"
        )
        self.act_import_geojson = self.import_menu.addAction(
            QgsApplication.getThemeIcon("mActionAddOgrLayer.svg"),
            "GeoJSON (Vector Layer)"
        )
        self.act_import_shp = self.import_menu.addAction(
            QgsApplication.getThemeIcon("mActionFileSave.svg"),
            "Shapefile (.shp Vector)"
        )
        self.import_menu.addSeparator()
        self.act_import_wms = self.import_menu.addAction(
            QgsApplication.getThemeIcon("mActionAddWmsLayer.svg"),
            "WMS (Raster Image)"
        )

        self.act_import_wfs.triggered.connect(lambda: self._on_import_format("WFS"))
        self.act_import_gpkg.triggered.connect(lambda: self._on_import_format("GEOPACKAGE"))
        self.act_import_geojson.triggered.connect(lambda: self._on_import_format("GEOJSON"))
        self.act_import_shp.triggered.connect(lambda: self._on_import_format("SHAPEFILE"))
        self.act_import_wms.triggered.connect(lambda: self._on_import_format("WMS"))

        self.btn_import_menu = QPushButton("▼")
        self.btn_import_menu.setObjectName("importMenuButton")
        self.btn_import_menu.setToolTip("Pilih format import (WFS, GeoPackage, GeoJSON, Shapefile, WMS)")
        self.btn_import_menu.setCursor(Qt.PointingHandCursor)
        self.btn_import_menu.setFixedSize(26, 34)
        self.btn_import_menu.setEnabled(False)
        self.btn_import_menu.clicked.connect(self._show_import_menu)
        self.btn_import_menu.setStyleSheet("""
            QPushButton#importMenuButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
                color: white;
                font-weight: bold;
                border-radius: 6px;
                border: none;
                font-size: 7.5pt;
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton#importMenuButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #059669, stop:1 #047857);
            }
            QPushButton#importMenuButton:disabled {
                background: #E2E8F0;
                color: #94A3B8;
            }
        """)

        import_btn_layout.addWidget(self.btn_import)
        import_btn_layout.addWidget(self.btn_import_menu)

        # 2. DETAIL Button
        self.btn_detail = QPushButton("DETAIL")
        self.btn_detail.setObjectName("detailButton")
        self.btn_detail.setIcon(QgsApplication.getThemeIcon("mActionPropertyItem.svg"))
        self.btn_detail.setCursor(Qt.PointingHandCursor)
        self.btn_detail.setEnabled(False)

        # 3. REFRESH Button
        self.btn_refresh_bottom = QPushButton("REFRESH")
        self.btn_refresh_bottom.setObjectName("refreshBottomButton")
        self.btn_refresh_bottom.setIcon(QgsApplication.getThemeIcon("mActionRefresh.svg"))
        self.btn_refresh_bottom.setCursor(Qt.PointingHandCursor)

        # 4. EKSPOR KE GEONODE Button (Sky Blue gradient)
        self.btn_export = QPushButton("EKSPOR KE GEONODE")
        self.btn_export.setObjectName("exportButton")
        self.btn_export.setIcon(QgsApplication.getThemeIcon("mActionSharingExport.svg"))
        self.btn_export.setToolTip("Ekspor layer aktif QGIS atau file spasial lokal sebagai dataset baru ke GeoNode")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setStyleSheet("""
            QPushButton#exportButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0284C7, stop:1 #0369A1);
                color: white;
                font-weight: 700;
                border-radius: 6px;
                padding: 8px 16px;
                border: none;
                font-size: 8.5pt;
            }
            QPushButton#exportButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0369A1, stop:1 #075985);
            }
            QPushButton#exportButton:pressed {
                background: #0C4A6E;
            }
        """)
        self.btn_export.clicked.connect(self.exportRequested.emit)

        layout.addLayout(import_btn_layout)
        layout.addWidget(self.btn_detail)
        layout.addWidget(self.btn_refresh_bottom)
        layout.addWidget(self.btn_export)
        layout.addStretch()

        self.main_layout.addLayout(layout)

    def _create_statusbar(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(8)

        self.status_chip = QLabel("Terhubung")
        self.status_chip.setStyleSheet("""
            QLabel {
                background: #F1F5F9;
                color: #475569;
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 8pt;
                font-weight: 600;
            }
        """)

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

        self.status_label = QLabel("Siap")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_label.setStyleSheet("color: #64748B; font-size: 8.5pt;")

        layout.addWidget(self.status_chip)
        layout.addWidget(self.progress, stretch=1)
        layout.addWidget(self.status_label)

        self.main_layout.addLayout(layout)

    def _connect_signals(self):
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_edit.returnPressed.connect(lambda: self.searchRequested.emit(self.search_edit.text()))
        self.refresh_button.clicked.connect(self.refreshRequested.emit)
        self.btn_refresh_bottom.clicked.connect(self.refreshRequested.emit)

        self.table_view.selectionModel().selectionChanged.connect(self._on_table_selection_changed)
        self.table_view.doubleClicked.connect(self._on_table_double_clicked)
        self.table_view.clicked.connect(self._on_table_clicked)

        self.btn_import.clicked.connect(self._on_import_clicked)
        self.btn_detail.clicked.connect(self._on_detail_clicked)

    def _on_search_text_changed(self, text: str):
        """
        Pencarian instan di level C++ menggunakan QSortFilterProxyModel (0ms delay).
        """
        self.proxy_model.set_filter_text(text)
        count = self.proxy_model.rowCount()
        total = self.source_model.rowCount()
        if text.strip():
            self.status_label.setText(f"Ditemukan {count} dari {total} dataset")
        else:
            self.status_label.setText(f"{total} dataset tersedia")

    # ==========================================================
    # Data Population
    # ==========================================================

    def populate(self, layers: list[Layer]) -> None:
        """
        Menampilkan daftar dataset secara virtual rendering instan melalui Model/View.
        """
        self._layers = list(layers)
        self.source_model.set_layers(layers)

        self.btn_import.setEnabled(False)
        self.btn_import_menu.setEnabled(False)
        self.btn_detail.setEnabled(False)
        self.status_chip.setText(f"🟢 Terhubung ({len(layers)} dataset)")
        self.status_label.setText(f"{len(layers)} dataset tersedia")

    def clear(self) -> None:
        self._layers.clear()
        self.source_model.set_layers([])
        self._selected_pk = None
        self.btn_import.setEnabled(False)
        self.btn_import_menu.setEnabled(False)
        self.btn_detail.setEnabled(False)
        self.status_chip.setText("⚪ Siap")
        self.status_label.setText("Siap")

    def show_loading(self, text: str = "Memuat dataset...") -> None:
        self.progress.show()
        self.status_label.setText(text)
        self.setEnabled(False)

    def hide_loading(self, text: str = "Siap") -> None:
        self.progress.hide()
        self.status_label.setText(text)
        self.setEnabled(True)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def row_count(self) -> int:
        if hasattr(self, "source_model") and self.source_model:
            return self.source_model.rowCount()
        return 0

    def selected_layer(self) -> Optional[str]:
        return self._selected_pk

    # Backward compatibility helper
    @property
    def tree(self):
        return self.table_view

    def update_detail_panel(self, title: str, abstract: str, has_wms: bool, has_wfs: bool):
        self.btn_import.setEnabled(True)
        self.btn_import_menu.setEnabled(True)
        self.btn_detail.setEnabled(True)

    def clear_detail_panel(self):
        self.btn_import.setEnabled(False)
        self.btn_import_menu.setEnabled(False)
        self.btn_detail.setEnabled(False)

    # ==========================================================
    # Events & Interaction
    # ==========================================================

    def _on_table_clicked(self, proxy_index):
        self._update_selection_from_proxy_index(proxy_index)

    def _on_table_selection_changed(self, selected=None, deselected=None):
        selected_rows = self.table_view.selectionModel().selectedRows()
        if selected_rows:
            self._update_selection_from_proxy_index(selected_rows[0])
        else:
            self._selected_pk = None
            self.source_model.set_selected_pk(None)
            self.btn_import.setEnabled(False)
            self.btn_import_menu.setEnabled(False)
            self.btn_detail.setEnabled(False)

    def _update_selection_from_proxy_index(self, proxy_index):
        if not proxy_index.isValid():
            return
        source_index = self.proxy_model.mapToSource(proxy_index)
        layer = self.source_model.get_layer(source_index.row())
        if not layer:
            return

        pk = str(layer.pk if layer.pk else layer.id)
        self._selected_pk = pk
        self.source_model.set_selected_pk(pk)

        self.btn_import.setEnabled(True)
        self.btn_import_menu.setEnabled(True)
        self.btn_detail.setEnabled(True)

        logger.debug("Table selection updated: PK=%s", self._selected_pk)
        self.layerSelected.emit(str(pk))

    def _show_table_context_menu(self, pos):
        proxy_index = self.table_view.indexAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet(self.import_menu.styleSheet())

        act_export = menu.addAction(
            QgsApplication.getThemeIcon("mActionSharingExport.svg"),
            "Ekspor / Tambah Dataset Baru ke GeoNode..."
        )
        act_export.triggered.connect(self.exportRequested.emit)

        if proxy_index.isValid():
            self._update_selection_from_proxy_index(proxy_index)
            menu.addSeparator()
            act_wfs = menu.addAction(QgsApplication.getThemeIcon("mActionAddWfsLayer.svg"), "Import Live WFS")
            act_wfs.triggered.connect(lambda: self._on_import_format("WFS"))
            act_gpkg = menu.addAction(QgsApplication.getThemeIcon("mActionAddOgrLayer.svg"), "Import GeoPackage (.gpkg)")
            act_gpkg.triggered.connect(lambda: self._on_import_format("GEOPACKAGE"))
            act_geojson = menu.addAction(QgsApplication.getThemeIcon("mActionAddOgrLayer.svg"), "Import GeoJSON")
            act_geojson.triggered.connect(lambda: self._on_import_format("GEOJSON"))
            act_shp = menu.addAction(QgsApplication.getThemeIcon("mActionFileSave.svg"), "Import Shapefile (.shp)")
            act_shp.triggered.connect(lambda: self._on_import_format("SHAPEFILE"))
            act_wms = menu.addAction(QgsApplication.getThemeIcon("mActionAddWmsLayer.svg"), "Import WMS (Raster)")
            act_wms.triggered.connect(lambda: self._on_import_format("WMS"))
            menu.addSeparator()
            act_detail = menu.addAction(QgsApplication.getThemeIcon("mActionPropertyItem.svg"), "Lihat Detail Metadata")
            act_detail.triggered.connect(self._on_detail_clicked)

        menu.exec_(self.table_view.mapToGlobal(pos))

    def _on_import_format(self, format_name: str):
        if not self._selected_pk:
            return
        logger.info("Import format requested: %s for PK: %s", format_name, self._selected_pk)
        if format_name in ("GPKG", "GEOPACKAGE"):
            self.importGpkgRequested.emit(self._selected_pk)
        elif format_name == "WFS":
            self.importWfsRequested.emit(self._selected_pk)
        elif format_name == "GEOJSON":
            self.importGeoJsonRequested.emit(self._selected_pk)
        elif format_name == "SHAPEFILE":
            self.importShapefileRequested.emit(self._selected_pk)
        elif format_name == "WMS":
            self.importWmsRequested.emit(self._selected_pk)

    def _on_table_item_double_clicked(self, item=None):
        self._on_table_double_clicked(self.table_view.currentIndex())

    def _on_table_double_clicked(self, proxy_index):
        if proxy_index.isValid():
            self._update_selection_from_proxy_index(proxy_index)
            if self._selected_pk:
                self.layerActivated.emit(self._selected_pk)
                self._on_import_clicked()

    def _on_import_clicked(self):
        if self._selected_pk:
            self.importRequested.emit(self._selected_pk)
            layer = self._get_layer_by_pk(self._selected_pk)
            if layer and layer.is_raster:
                self.importWmsRequested.emit(self._selected_pk)
            else:
                self.importWfsRequested.emit(self._selected_pk)

    def _show_import_menu(self):
        """Menampilkan menu pilihan format import tepat di bawah tombol opsi."""
        if hasattr(self, "import_menu") and self.import_menu:
            pos = self.btn_import_menu.mapToGlobal(QPoint(0, self.btn_import_menu.height() + 2))
            self.import_menu.exec_(pos)

    def _on_detail_clicked(self):
        if self._selected_pk:
            self.detailRequested.emit(self._selected_pk)

    def _get_layer_by_pk(self, pk: str) -> Optional[Layer]:
        return self.source_model.get_layer_by_pk(pk)
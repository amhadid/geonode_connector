"""
dataset_table_model.py

Model/View Table Model untuk Dataset GeoNode menggunakan QAbstractTableModel
dan QSortFilterProxyModel. Mengimplementasikan virtual rendering cepat
sehingga ribuan dataset dapat ditampilkan secara instan dan efisien memori.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from qgis.PyQt.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)
from qgis.PyQt.QtGui import QColor, QFont, QIcon
from qgis.core import QgsApplication

from ...models.layer import Layer
from ...utils.logger import get_logger

logger = get_logger(__name__)


class DatasetTableModel(QAbstractTableModel):
    """
    Model tabel untuk daftar dataset GeoNode.
    """

    HEADERS = ["", "NAMA DATASET", "TIPE", "TERAKHIR DIPERBARUI"]

    def __init__(self, parent: Optional[Any] = None):
        super().__init__(parent)
        self._layers: List[Layer] = []
        self._selected_pk: Optional[str] = None

        # Pre-cache icons & fonts
        self._vector_icon = QgsApplication.getThemeIcon("mIconVector.svg")
        self._raster_icon = QgsApplication.getThemeIcon("mIconRaster.svg")
        self._mesh_icon = QgsApplication.getThemeIcon("mIconMesh.svg")
        self._bold_font = QFont()
        self._bold_font.setBold(True)
        self._bold_font.setPointSize(9)

        self._title_color = QColor("#1E293B")
        self._vector_color = QColor("#0284C7")
        self._raster_color = QColor("#D97706")
        self._mesh_color = QColor("#7C3AED")
        self._date_color = QColor("#64748B")

    def set_layers(self, layers: List[Layer]) -> None:
        """
        Memperbarui seluruh data layer secara batch dengan notifikasi model.
        """
        self.beginResetModel()
        self._layers = list(layers)
        self.endResetModel()

    def get_layers(self) -> List[Layer]:
        return self._layers

    def get_layer(self, row: int) -> Optional[Layer]:
        if 0 <= row < len(self._layers):
            return self._layers[row]
        return None

    def get_layer_by_pk(self, pk: str) -> Optional[Layer]:
        pk_str = str(pk)
        for layer in self._layers:
            if str(layer.pk) == pk_str or (layer.id is not None and str(layer.id) == pk_str):
                return layer
        return None

    def set_selected_pk(self, pk: Optional[str]) -> None:
        self._selected_pk = str(pk) if pk else None
        # Notify row checkbox updates
        if self._layers:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._layers) - 1, 0),
                [Qt.CheckStateRole]
            )

    @property
    def selected_pk(self) -> Optional[str]:
        return self._selected_pk

    # ==========================================================
    # QAbstractTableModel Implementation
    # ==========================================================

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._layers)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.HEADERS):
                return self.HEADERS[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 0:
            flags |= Qt.ItemIsUserCheckable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        if not (0 <= row < len(self._layers)):
            return None

        layer = self._layers[row]
        pk_str = str(layer.pk if layer.pk else layer.id)

        # User Role: Selalu kembalikan PK
        if role == Qt.UserRole:
            return pk_str

        # Kolom 0: Centered Checkbox
        if col == 0:
            if role == Qt.CheckStateRole:
                return Qt.Checked if self._selected_pk == pk_str else Qt.Unchecked
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return None

        # Kolom 1: Nama Dataset (Title / Name)
        if col == 1:
            if role == Qt.DisplayRole:
                return layer.title or layer.name
            if role == Qt.FontRole:
                return self._bold_font
            if role == Qt.ForegroundRole:
                return self._title_color
            if role == Qt.ToolTipRole:
                return f"{layer.title or layer.name}\nAlternate: {layer.alternate or layer.name}\nAbstrak: {layer.abstract or '-'}"
            return None

        # Kolom 2: Tipe Badge (Vector / Raster / 3D Tiles)
        if col == 2:
            subtype = (layer.subtype or "").lower()
            if "3d" in subtype or subtype == "3dtiles":
                type_name = "3D Tiles"
                icon = self._mesh_icon
                color = self._mesh_color
            elif layer.is_raster or subtype == "raster":
                type_name = "Raster"
                icon = self._raster_icon
                color = self._raster_color
            else:
                type_name = "Vector"
                icon = self._vector_icon
                color = self._vector_color

            if role == Qt.DisplayRole:
                return type_name
            if role == Qt.DecorationRole:
                return icon
            if role == Qt.FontRole:
                return self._bold_font
            if role == Qt.ForegroundRole:
                return color
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return None

        # Kolom 3: Tanggal Modifikasi
        if col == 3:
            if role == Qt.DisplayRole:
                dt = layer.modified or layer.created
                if dt:
                    if isinstance(dt, datetime):
                        return dt.strftime("%d/%m/%Y")
                    return str(dt)[:10]
                return "-"
            if role == Qt.ForegroundRole:
                return self._date_color
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return None

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if index.isValid() and index.column() == 0 and role == Qt.CheckStateRole:
            row = index.row()
            if 0 <= row < len(self._layers):
                layer = self._layers[row]
                pk_str = str(layer.pk if layer.pk else layer.id)
                self._selected_pk = pk_str if value == Qt.Checked else None
                self.dataChanged.emit(self.index(0, 0), self.index(len(self._layers) - 1, 0), [Qt.CheckStateRole])
                return True
        return False


class DatasetProxyModel(QSortFilterProxyModel):
    """
    QSortFilterProxyModel untuk filter pencarian instan sisi klien di level C++.
    """

    def __init__(self, parent: Optional[Any] = None):
        super().__init__(parent)
        self._filter_keyword = ""
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def set_filter_text(self, text: str) -> None:
        self._filter_keyword = text.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._filter_keyword:
            return True

        model = self.sourceModel()
        if not isinstance(model, DatasetTableModel):
            return True

        layer = model.get_layer(source_row)
        if not layer:
            return False

        # Cari pada title, name, abstract, alternate, dan subtype
        keyword = self._filter_keyword
        title = (layer.title or "").lower()
        name = (layer.name or "").lower()
        abstract = (layer.abstract or "").lower()
        alternate = (layer.alternate or "").lower()
        subtype = (layer.subtype or "").lower()

        return (
            keyword in title
            or keyword in name
            or keyword in abstract
            or keyword in alternate
            or keyword in subtype
        )

"""
import_controller.py

Controller khusus untuk menangani interaksi import layer ke QGIS.
Menjaga pemisahan tugas agar dataset_controller.py tidak bloated.
"""

from __future__ import annotations
from typing import Optional

from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QMessageBox

from ..widgets.dataset_widget import DatasetWidget
from ...services.import_service import ImportService
from ...services.layer_service import LayerService
from ...services.activity_service import activity_service
from ...models.session import session
from ...utils.logger import get_logger

logger = get_logger(__name__)

class ImportController:
    """
    Menghubungkan aksi UI pada DatasetWidget dengan logika bisnis ImportService.
    """

    def __init__(
        self,
        widget: DatasetWidget,
        layer_service: LayerService,
        import_service: Optional[ImportService] = None,
        my_layers_widget=None,
    ):
        self.widget = widget
        self.layer_service = layer_service
        self.import_service = import_service or ImportService()
        self.my_layers_widget = my_layers_widget

        self._connect_signals()

    def _connect_signals(self) -> None:
        """
        Menghubungkan sinyal dari widget ke method import.
        """
        self.widget.importWmsRequested.connect(self.handle_import_wms)
        self.widget.importWfsRequested.connect(self.handle_import_wfs)
        if hasattr(self.widget, "importGeoJsonRequested"):
            self.widget.importGeoJsonRequested.connect(self.handle_import_geojson)
        if hasattr(self.widget, "importShapefileRequested"):
            self.widget.importShapefileRequested.connect(self.handle_import_shapefile)

    def handle_import_wms(self, pk: str) -> None:
        """Handler untuk permintaan import WMS."""
        self._execute_import(pk, service_type="WMS")

    def handle_import_wfs(self, pk: str) -> None:
        """Handler untuk permintaan import WFS."""
        self._execute_import(pk, service_type="WFS")

    def handle_import_geojson(self, pk: str) -> None:
        """Handler untuk permintaan import GeoJSON."""
        self._execute_import(pk, service_type="GEOJSON")

    def handle_import_shapefile(self, pk: str) -> None:
        """Handler untuk permintaan import Shapefile."""
        self._execute_import(pk, service_type="SHAPEFILE")

    def _execute_import(self, pk: str, service_type: str) -> None:
        """
        Alur kerja (workflow) utama proses import.
        1. Ambil detail layer terbaru via API.
        2. Jalankan import melalui ImportService.
        3. Tampilkan feedback ke UI (Message Bar / Status).
        """
        self.widget.set_status(f"Mempersiapkan import {service_type}...")

        # 1. Pastikan kita punya detail lengkap (termasuk URI/Links)
        layer = self.layer_service.load_detail(pk)

        if not layer:
            layer = self.layer_service.get(pk)

        if not layer:
            self.widget.set_status(f"Gagal mengambil detail untuk layer PK: {pk}")
            self._show_error("Data tidak lengkap", "Gagal memuat informasi metadata dari server.")
            return

        self.widget.set_status(f"Mengimpor {layer.title} sebagai {service_type}...")

        # 2. Eksekusi Import
        if service_type == "WMS":
            result = self.import_service.import_wms(layer)
        elif service_type == "WFS":
            result = self.import_service.import_wfs(layer)
        elif service_type == "GEOJSON":
            result = self.import_service.import_geojson(layer)
        elif service_type == "SHAPEFILE":
            result = self.import_service.import_shapefile(layer)
        else:
            return

        # 3. Handle Result
        if result.success:
            success_msg = f"Layer '{layer.title or layer.name}' berhasil diimpor ke QGIS ({service_type})."
            self.widget.set_status(f"Berhasil: {result.message}")
            if hasattr(self.widget, "show_notification"):
                self.widget.show_notification(success_msg, is_error=False)

            logger.info(result.message)

            # Log to Activity Log (Mockup Screen 8)
            username = session.username or "admin_demo"
            activity_service.log(
                category="import",
                username=username,
                description=f'Import layer "{layer.title or layer.name}"',
            )

            # Register to My Layers (Mockup Screen 4)
            if self.my_layers_widget:
                layer_id = ""
                if result.data and isinstance(result.data, dict):
                    layer_id = result.data.get("layer_id", "")
                if not layer_id:
                    layer_id = f"geonode_{layer.name}"

                from qgis.core import QgsProject
                qgs_l = QgsProject.instance().mapLayer(layer_id)
                feat_count = qgs_l.featureCount() if qgs_l and hasattr(qgs_l, "featureCount") else 0
                crs_auth = qgs_l.crs().authid() if qgs_l and hasattr(qgs_l, "crs") else (layer.srid or "EPSG:4326")

                self.my_layers_widget.register_imported_layer(
                    layer_id=layer_id,
                    name=layer.title or layer.name,
                    source_type=service_type,
                    crs=crs_auth,
                    features=feat_count,
                )
        else:
            self.widget.set_status("Gagal melakukan import.")
            if hasattr(self.widget, "show_notification"):
                self.widget.show_notification(f"Gagal import: {result.message}", is_error=True)
            self._show_error("Import Error", result.message)

    def _show_error(self, title: str, message: str) -> None:
        """Menampilkan dialog error kepada user"""
        logger.error(f"ImportController Error - {title}: {message}")
        QMessageBox.warning(self.widget, title, message)
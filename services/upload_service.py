"""
upload_service.py

Business service untuk Upload Dataset dan Integrasi Metadata (Sprint 6 & 7).
Mendukung:
- Pilihan mode: Updating Dataset Lama vs Kategori Dataset Baru
- Export layer QGIS ke GeoPackage, GeoJSON, Shapefile, CSV, GeoTIFF
- Monitoring progres upload
- Penerapan metadata standar ISO 19115 ke GeoNode
"""

from __future__ import annotations

import os
import time
import tempfile
import shutil
from typing import Any, Callable, Dict, Optional

from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsMapLayer,
    QgsVectorFileWriter,
    QgsCoordinateTransformContext,
    QgsProject,
)

from ..api.upload import UploadAPI
from ..models.service_result import ServiceResult
from ..models.session import session
from ..services.activity_service import activity_service
from ..services.metadata_service import metadata_service
from ..services.sync_service import sync_service
from ..utils.logger import get_logger

logger = get_logger(__name__)


class UploadService:
    """
    Business service untuk mengunggah atau memperbarui dataset di GeoNode.
    """

    def __init__(self, upload_api: Optional[UploadAPI] = None) -> None:
        self.api = upload_api or UploadAPI()
        self._session = session

    # ==========================================================
    # Layer Exporter Helper
    # ==========================================================

    def export_layer(
        self,
        layer: QgsMapLayer,
        output_format: str = "GPKG",
        custom_name: str = "",
    ) -> Dict[str, str]:
        """
        Mengekspor layer QGIS ke file lokal sementara.

        Parameters
        ----------
        layer : QgsMapLayer
            Layer yang akan diekspor.
        output_format : str
            'GPKG', 'GeoJSON', 'ESRI Shapefile'
        custom_name : str
            Nama dasar file.

        Returns
        -------
        Dict[str, str]
            File map untuk diunggah (misal {'base_file': path, ...}).
        """
        temp_dir = tempfile.mkdtemp(prefix="geonode_upload_")
        base_name = "".join(c for c in (custom_name or layer.name()).lower() if c.isalnum() or c == "_")
        if not base_name:
            base_name = "dataset"

        if isinstance(layer, QgsVectorLayer):
            transform_context = QgsProject.instance().transformContext()
            save_options = QgsVectorFileWriter.SaveVectorOptions()
            save_options.layerName = base_name

            fmt_upper = output_format.upper()
            if "GPKG" in fmt_upper or "GEOPACKAGE" in fmt_upper:
                save_options.driverName = "GPKG"
                out_path = os.path.join(temp_dir, f"{base_name}.gpkg")
                res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, out_path, transform_context, save_options)
                err, msg = res[0], res[1]
                if err == QgsVectorFileWriter.NoError:
                    return {"base_file": out_path, "_temp_dir": temp_dir}
                raise RuntimeError(f"Gagal ekspor ke GeoPackage: {msg}")

            elif "GEOJSON" in fmt_upper or "JSON" in fmt_upper:
                save_options.driverName = "GeoJSON"
                out_path = os.path.join(temp_dir, f"{base_name}.geojson")
                res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, out_path, transform_context, save_options)
                err, msg = res[0], res[1]
                if err == QgsVectorFileWriter.NoError:
                    return {"base_file": out_path, "_temp_dir": temp_dir}
                raise RuntimeError(f"Gagal ekspor ke GeoJSON: {msg}")

            else:
                # Shapefile
                save_options.driverName = "ESRI Shapefile"
                out_path = os.path.join(temp_dir, f"{base_name}.shp")
                res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, out_path, transform_context, save_options)
                err, msg = res[0], res[1]
                if err == QgsVectorFileWriter.NoError:
                    file_map = {"base_file": out_path, "_temp_dir": temp_dir}
                    for ext in [".shx", ".dbf", ".prj"]:
                        p = os.path.join(temp_dir, f"{base_name}{ext}")
                        if os.path.isfile(p) and os.path.getsize(p) > 0:
                            file_map[f"{ext[1:]}_file"] = p
                    # Pastikan cpg memiliki isi (> 0 bytes) untuk menghindari error GeoNode 'application/x-empty'
                    cpg_p = os.path.join(temp_dir, f"{base_name}.cpg")
                    if os.path.isfile(cpg_p):
                        if os.path.getsize(cpg_p) == 0:
                            try:
                                with open(cpg_p, "w", encoding="utf-8") as f:
                                    f.write("UTF-8\n")
                            except Exception:
                                pass
                        if os.path.getsize(cpg_p) > 0:
                            file_map["cpg_file"] = cpg_p
                    return file_map
                raise RuntimeError(f"Gagal ekspor ke Shapefile: {msg}")

        raise ValueError("Format layer tidak didukung untuk ekspor.")

    # ==========================================================
    # Mode 1: Update Dataset Lama
    # ==========================================================

    def update_existing_dataset(
        self,
        layer: QgsVectorLayer,
        target_pk: int | str,
        target_name: str,
        metadata_dict: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> ServiceResult:
        """
        Memperbarui dataset yang sudah ada sebelumnya di GeoNode.
        1. Sinkronisasi data fitur dan skema ke basis data GeoNode.
        2. Memperbarui metadata ISO 19115 via REST API.
        3. Memuat ulang katalog GeoServer dan merefresh GeoNode updatelayers.
        """
        try:
            if progress_callback:
                progress_callback(10, "Menvalidasi metadata...")

            # 1. Validasi Metadata Wajib
            is_valid, errs = metadata_service.validate_metadata(metadata_dict)
            if not is_valid:
                return ServiceResult.fail(message="Validasi metadata gagal:\n• " + "\n• ".join(errs))

            if progress_callback:
                progress_callback(30, "Menyimpan data dan skema fitur ke basis data...")

            # 2. Sinkronkan data fitur dan kolom baru (WFS-T HTTP atau PostGIS)
            sync_res = sync_service.sync_layer(layer)
            if not sync_res.success:
                msg_lower = (sync_res.message or "").lower()
                if "tidak ada perubahan" not in msg_lower:
                    return ServiceResult.fail(message=f"Gagal sinkronisasi data: {sync_res.message}")

            if progress_callback:
                progress_callback(65, "Menyimpan perubahan metadata ke GeoNode...")

            # 3. Update Metadata melalui REST API
            meta_res = metadata_service.update_metadata(target_pk, metadata_dict)
            if not meta_res.success:
                logger.warning(f"Metadata update warning: {meta_res.message}")

            if progress_callback:
                progress_callback(85, "Menyegarkan katalog GeoServer & GeoNode...")

            sync_service._reload_geoserver_catalog()
            sync_service._trigger_geonode_updatelayers(target_name)

            if progress_callback:
                progress_callback(100, "Dataset lama berhasil diperbarui!")

            title = metadata_dict.get("title", target_name)
            activity_service.log(
                category="update",
                username=self._session.username or "admin",
                description=f"Dataset '{title}' (ID: {target_pk}) berhasil diperbarui dan disinkronkan.",
            )

            status_msg = f"Dataset '{title}' berhasil diperbarui di GeoNode beserta metadatanya."
            if not meta_res.success:
                status_msg = f"Data spasial '{title}' berhasil disimpan di GeoNode (Catatan metadata: {meta_res.message})."

            return ServiceResult.ok(
                message=status_msg,
                data={"pk": target_pk, "title": title, "metadata_updated": meta_res.success},
            )

        except Exception as e:
            logger.exception("Gagal memperbarui dataset lama:")
            return ServiceResult.fail(message=f"Terjadi kesalahan saat memperbarui dataset: {str(e)}")

    # ==========================================================
    # Mode 2: Kategori Dataset Baru
    # ==========================================================

    def upload_new_dataset(
        self,
        layer: QgsVectorLayer,
        dataset_name: str,
        output_format: str,
        metadata_dict: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> ServiceResult:
        """
        Mengunggah layer sebagai dataset baru di GeoNode.
        1. Validasi metadata.
        2. Ekspor layer ke format yang didukung (GeoPackage/GeoJSON/Shapefile).
        3. Upload ke GeoNode Importer (/uploads/upload).
        4. Polling proses hingga selesai (status: finished).
        5. Mengatur metadata lengkap pada dataset baru.
        """
        temp_dir = None
        try:
            if progress_callback:
                progress_callback(10, "Menvalidasi metadata dataset baru...")

            # 1. Validasi Metadata
            is_valid, errs = metadata_service.validate_metadata(metadata_dict)
            if not is_valid:
                return ServiceResult.fail(message="Validasi metadata gagal:\n• " + "\n• ".join(errs))

            clean_name = "".join(c for c in dataset_name.lower() if c.isalnum() or c == "_")
            if not clean_name:
                clean_name = "layer_baru_" + str(int(time.time()))

            if progress_callback:
                progress_callback(25, f"Mengekspor layer ke format {output_format}...")

            # 2. Ekspor ke file
            file_map = self.export_layer(layer, output_format, custom_name=clean_name)
            temp_dir = file_map.pop("_temp_dir", None)

            if progress_callback:
                progress_callback(45, "Mengunggah dataset ke server GeoNode...")

            # 3. Upload via Importer API
            upload_resp = self.api.upload_dataset(file_map, action="upload")
            exec_id = upload_resp.get("execution_id")

            if not exec_id:
                err_msg = upload_resp.get("error") or upload_resp.get("errors") or "Server tidak mengembalikan execution_id."
                return ServiceResult.fail(message=f"Gagal mengunggah dataset: {err_msg}")

            if progress_callback:
                progress_callback(60, "Memproses dataset di GeoNode Importer...")

            # 4. Polling Execution Request
            new_resource_pk = None
            max_retries = 25
            for i in range(max_retries):
                time.sleep(1.0)
                status_data = self.api.get_execution_status(exec_id)
                if not status_data:
                    continue

                status = status_data.get("status")
                step = status_data.get("step", "")
                if progress_callback:
                    pct = min(90, 60 + int(i * 1.2))
                    progress_callback(pct, f"Proses importer: {status or step}...")

                if status == "finished":
                    new_resource_pk = status_data.get("geonode_resource")
                    if not new_resource_pk and "output_params" in status_data:
                        resources = status_data["output_params"].get("resources", [])
                        if resources:
                            new_resource_pk = resources[0].get("id")
                    break
                elif status in ("failed", "error"):
                    err = status_data.get("log") or "Proses import gagal di GeoNode."
                    return ServiceResult.fail(message=f"Importer GeoNode gagal: {err}")

            if progress_callback:
                progress_callback(92, "Menyimpan metadata lengkap...")

            # 5. Terapkan metadata ke dataset baru jika pk berhasil didapat
            if new_resource_pk:
                metadata_service.update_metadata(new_resource_pk, metadata_dict)
                logger.info(f"Metadata berhasil diterapkan pada dataset baru ID: {new_resource_pk}")

            if progress_callback:
                progress_callback(100, "Dataset baru berhasil dipublikasikan!")

            title = metadata_dict.get("title", clean_name)
            activity_service.log(
                category="upload",
                username=self._session.username or "admin",
                description=f"Dataset baru '{title}' berhasil diupload dan dipublikasikan di GeoNode.",
            )

            return ServiceResult.ok(
                message=f"Dataset baru '{title}' berhasil dipublikasikan di GeoNode!",
                data={"pk": new_resource_pk, "name": clean_name, "title": title},
            )

        except Exception as e:
            logger.exception("Gagal upload dataset baru:")
            return ServiceResult.fail(message=f"Terjadi kesalahan saat upload dataset baru: {str(e)}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


upload_service = UploadService()

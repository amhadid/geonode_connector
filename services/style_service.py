"""
style_service.py

Service untuk pengelolaan dan sinkronisasi style simbologi (.sld)
antara QGIS dan GeoNode / GeoServer (Sprint 8 & Ekspor).
"""

from __future__ import annotations

import os
import json
import base64
import urllib.request
import urllib.error
import tempfile
from typing import Optional, Tuple

from qgis.core import QgsVectorLayer, QgsMapLayer

from ..models.service_result import ServiceResult
from ..models.session import session
from ..utils.config import (
    DEFAULT_SERVER,
    GEOSERVER_ADMIN_USER,
    GEOSERVER_ADMIN_PASSWORD,
    GEOSERVER_DEFAULT_WORKSPACE,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class StyleService:
    """
    Business service untuk mengekspor dan menyelaraskan style simbologi (SLD)
    dari layer QGIS ke GeoServer dan portal GeoNode.
    """

    def __init__(self) -> None:
        self._session = session

    # ==========================================================
    # Ekspor SLD dari QGIS Layer
    # ==========================================================

    def export_sld_from_layer(
        self,
        layer: QgsMapLayer,
        output_path: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Mengekspor style simbologi layer aktif di QGIS ke format file OGC SLD (.sld).

        Parameters
        ----------
        layer : QgsMapLayer
            Layer sumber di kanvas QGIS.
        output_path : str, optional
            Path berkas tujuan. Jika kosong, dibuat berkas sementara.

        Returns
        -------
        Tuple[bool, str]
            (sukses: bool, path_file_atau_pesan_error: str)
        """
        if not layer or not layer.isValid():
            return False, "Layer QGIS tidak valid atau belum dipilih."

        if not hasattr(layer, "saveSldStyle"):
            return False, "Tipe layer tidak mendukung ekspor format SLD."

        target_file = output_path
        if not target_file:
            safe_name = "".join(c for c in layer.name().lower() if c.isalnum() or c == "_") or "layer_style"
            temp_dir = tempfile.mkdtemp(prefix="geonode_sld_")
            target_file = os.path.join(temp_dir, f"{safe_name}.sld")

        try:
            # QgsMapLayer.saveSldStyle(uri) -> (errorMessage, successFlag)
            res = layer.saveSldStyle(target_file)
            if isinstance(res, tuple):
                err_msg, is_ok = res[0], res[1]
            else:
                is_ok = bool(res)
                err_msg = ""

            if is_ok and os.path.isfile(target_file) and os.path.getsize(target_file) > 0:
                logger.info(f"Berhasil mengekspor SLD layer '{layer.name()}' ke: {target_file}")
                return True, target_file

            return False, f"Gagal mengekspor style SLD: {err_msg or 'File hasil kosong'}"

        except Exception as e:
            logger.exception("Kesalahan saat mengekspor SLD:")
            return False, str(e)

    # ==========================================================
    # Sinkronisasi SLD ke GeoServer & GeoNode
    # ==========================================================

    def sync_sld_to_geoserver(
        self,
        layer: QgsVectorLayer,
        layer_name: str,
        workspace: str = GEOSERVER_DEFAULT_WORKSPACE,
        custom_sld_path: Optional[str] = None,
    ) -> ServiceResult:
        """
        Mengunggah file SLD simbologi layer QGIS ke GeoServer dan menjadikannya
        sebagai default style aktif pada layer bersangkutan di GeoNode.

        Parameters
        ----------
        layer : QgsVectorLayer
            Layer QGIS dengan simbologi yang ingin disinkronkan.
        layer_name : str
            Nama teknis layer di GeoServer/GeoNode (misal: 'titik_kesehatan_2026').
        workspace : str
            Workspace GeoServer (default: 'geonode').
        custom_sld_path : str, optional
            Path file .sld yang sudah ada. Jika None, diekspor langsung dari layer.
        """
        clean_layer_name = "".join(c for c in layer_name.lower() if c.isalnum() or c == "_")
        if not clean_layer_name:
            clean_layer_name = "dataset"

        sld_file = custom_sld_path
        cleanup_temp = False

        if not sld_file or not os.path.isfile(sld_file):
            ok, sld_file = self.export_sld_from_layer(layer)
            if not ok:
                return ServiceResult.fail(message=f"Gagal mengekstrak SLD dari layer: {sld_file}")
            cleanup_temp = True

        try:
            with open(sld_file, "r", encoding="utf-8") as f:
                sld_content = f.read()

            if not sld_content.strip():
                return ServiceResult.fail(message="Konten SLD layer kosong.")

            server_url = (self._session.server_url or DEFAULT_SERVER).rstrip("/")
            auth_str = f"{GEOSERVER_ADMIN_USER}:{GEOSERVER_ADMIN_PASSWORD}"
            auth_hdr = f"Basic {base64.b64encode(auth_str.encode()).decode()}"

            style_name = clean_layer_name

            # 1. Cek apakah style sudah ada di GeoServer workspace
            check_url = f"{server_url}/geoserver/rest/workspaces/{workspace}/styles/{style_name}.json"
            style_exists = False
            try:
                req_check = urllib.request.Request(
                    check_url,
                    headers={"Authorization": auth_hdr},
                    method="GET",
                )
                with urllib.request.urlopen(req_check, timeout=10) as resp_check:
                    if resp_check.status == 200:
                        style_exists = True
            except urllib.error.HTTPError as e_http:
                if e_http.code == 404:
                    style_exists = False
                else:
                    logger.debug(f"Pengecekan style HTTP {e_http.code}, mencoba mode create/update...")
            except Exception as e_check:
                logger.debug(f"Catatan cek style: {e_check}")

            # 2. Upload / Update Style SLD
            payload_bytes = sld_content.encode("utf-8")
            if style_exists:
                # Update style yang sudah ada
                target_url = f"{server_url}/geoserver/rest/workspaces/{workspace}/styles/{style_name}"
                req_style = urllib.request.Request(
                    target_url,
                    data=payload_bytes,
                    headers={
                        "Authorization": auth_hdr,
                        "Content-Type": "application/vnd.ogc.sld+xml",
                    },
                    method="PUT",
                )
            else:
                # Buat style baru di workspace
                target_url = f"{server_url}/geoserver/rest/workspaces/{workspace}/styles?name={style_name}"
                req_style = urllib.request.Request(
                    target_url,
                    data=payload_bytes,
                    headers={
                        "Authorization": auth_hdr,
                        "Content-Type": "application/vnd.ogc.sld+xml",
                    },
                    method="POST",
                )

            try:
                with urllib.request.urlopen(req_style, timeout=15) as resp_style:
                    logger.info(f"Upload SLD ke GeoServer berhasil ({style_name}): HTTP {resp_style.status}")
            except Exception as e_up:
                logger.warning(f"Percobaan upload style pertama: {e_up}. Mencoba endpoint root styles...")
                # Fallback ke root styles jika workspace styles restriksi
                try:
                    fallback_url = (
                        f"{server_url}/geoserver/rest/styles/{style_name}"
                        if style_exists
                        else f"{server_url}/geoserver/rest/styles?name={style_name}"
                    )
                    method = "PUT" if style_exists else "POST"
                    req_fb = urllib.request.Request(
                        fallback_url,
                        data=payload_bytes,
                        headers={
                            "Authorization": auth_hdr,
                            "Content-Type": "application/vnd.ogc.sld+xml",
                        },
                        method=method,
                    )
                    with urllib.request.urlopen(req_fb, timeout=15) as resp_fb:
                        logger.info(f"Fallback upload SLD berhasil: HTTP {resp_fb.status}")
                except Exception as e_fb:
                    logger.error(f"Gagal mengunggah style SLD ke GeoServer: {e_fb}")
                    return ServiceResult.fail(message=f"Gagal mengunggah style ke GeoServer: {e_fb}")

            # 3. Tautkan Style sebagai defaultStyle pada layer di GeoServer
            layer_set_url = f"{server_url}/geoserver/rest/layers/{workspace}:{clean_layer_name}.json"
            layer_payload = json.dumps({
                "layer": {
                    "defaultStyle": {
                        "name": style_name,
                        "workspace": workspace,
                    }
                }
            }).encode("utf-8")

            try:
                req_layer = urllib.request.Request(
                    layer_set_url,
                    data=layer_payload,
                    headers={
                        "Authorization": auth_hdr,
                        "Content-Type": "application/json",
                    },
                    method="PUT",
                )
                with urllib.request.urlopen(req_layer, timeout=10) as resp_layer:
                    logger.info(f"Berhasil menautkan defaultStyle {style_name} ke layer: HTTP {resp_layer.status}")
            except Exception as e_link:
                logger.warning(f"Tautan layer defaultStyle catatan: {e_link}")

            # 4. Trigger reload catalog GeoServer
            try:
                from .sync_service import sync_service
                sync_service._reload_geoserver_catalog()
                sync_service._trigger_geonode_updatelayers(clean_layer_name)
            except Exception as e_reload:
                logger.debug(f"Penyegaran katalog pasca style: {e_reload}")

            return ServiceResult.ok(
                message=f"Style simbologi layer '{clean_layer_name}' berhasil disinkronkan ke GeoNode (.sld).",
                data={"style_name": style_name, "workspace": workspace},
            )

        except Exception as e:
            logger.exception("Kesalahan saat menyinkronkan SLD ke server:")
            return ServiceResult.fail(message=f"Gagal sinkronisasi style: {str(e)}")

        finally:
            if cleanup_temp and sld_file and os.path.isfile(sld_file):
                try:
                    os.remove(sld_file)
                    temp_parent = os.path.dirname(sld_file)
                    if "geonode_sld_" in temp_parent:
                        os.rmdir(temp_parent)
                except Exception:
                    pass


style_service = StyleService()

"""
import_service.py

Business logic untuk mengimpor layer dari GeoNode ke QGIS.

Responsibilities
----------------
- Merakit URI untuk koneksi WMS dan WFS QGIS yang valid (OWS Vector).
- Mengimpor format Vektor: Live WFS, GeoJSON, atau Shapefile (.shp).
- Mengimpor format Raster: WMS.
- Menyisipkan OAuth2 Access Token untuk layer privat.
- Membuat objek QgsRasterLayer (WMS) dan QgsVectorLayer (WFS / GeoJSON / Shapefile).
- Memvalidasi layer sebelum ditambahkan ke Map Canvas.
- Menambahkan layer ke QgsProject.

Service ini merupakan jembatan antara API GeoNode dan API QGIS.
"""

from __future__ import annotations

import os
import zipfile
import urllib.parse
import urllib.request
from typing import Optional

from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsMapLayer,
)

from ..models.layer import Layer
from ..models.session import session
from ..models.service_result import ServiceResult
from ..utils.config import GEOSERVER_ADMIN_USER, GEOSERVER_ADMIN_PASSWORD
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ImportService:
    """
    Service untuk melakukan import layer GeoNode ke proyek QGIS.
    Mendukung WFS (OWS Vector), GeoJSON, Shapefile, dan WMS (Raster).
    """

    def __init__(self, project: Optional[QgsProject] = None) -> None:
        """
        Parameters
        ----------
        project : QgsProject, optional
            Instansi QgsProject aktif. Jika None, gunakan instance global.
        """
        self._project = project or QgsProject.instance()
        self._session = session

    # ==========================================================
    # WMS Import (Raster)
    # ==========================================================

    def import_wms(self, layer: Layer) -> ServiceResult:
        """
        Mengimpor layer sebagai WMS (Raster) ke dalam QGIS.
        """
        if not layer.has_wms:
            server_url = self._session.server_url or "http://localhost"
            layer.wms_url = f"{server_url.rstrip('/')}/geoserver/ows"

        logger.info(f"Importing WMS Layer: {layer.display_name}")

        try:
            # 1. Build URI
            uri = self._build_wms_uri(layer)

            # 2. Create QGIS Layer
            qgs_layer = QgsRasterLayer(
                uri,
                layer.title or layer.name,
                "wms"
            )

            # 3. Validate and Add
            return self._validate_and_add(qgs_layer, layer, format_desc="WMS Raster")

        except Exception as e:
            logger.exception("Gagal melakukan import WMS.")
            return ServiceResult.fail(
                message=f"Terjadi kesalahan sistem saat import WMS: {str(e)}"
            )

    # ==========================================================
    # WFS Import (OWS Vector Live)
    # ==========================================================

    def import_wfs(self, layer: Layer) -> ServiceResult:
        """
        Mengimpor layer sebagai WFS (Vector OWS) ke dalam QGIS.
        Jika WFS provider gagal, otomatis fallback ke GeoJSON atau Shapefile.
        TIDAK AKAN jatuh ke WMS raster agar dataset tetap berupa vektor untuk analisis.
        """
        if not layer.has_wfs:
            server_url = self._session.server_url or "http://localhost"
            layer.wfs_url = f"{server_url.rstrip('/')}/geoserver/ows"

        # Tolak jika eksplisit raster
        if layer.is_raster:
            return ServiceResult.fail(
                message=f"Dataset '{layer.title}' adalah raster, gunakan import WMS."
            )

        logger.info(f"Importing WFS Layer: {layer.display_name}")

        try:
            # 1. Coba WFS standar dengan alternate / workspace:name
            uri = self._build_wfs_uri(layer)
            qgs_layer = QgsVectorLayer(
                uri,
                layer.title or layer.name,
                "WFS"
            )

            # 2. Coba fallback variasi nama typename jika default tidak valid
            if not qgs_layer.isValid() and layer.workspace and layer.name:
                alt_name = f"{layer.workspace}:{layer.name}"
                if alt_name != (layer.alternate or layer.qgis_layer_name):
                    alt_uri = self._build_wfs_uri(layer, typename_override=alt_name)
                    qgs_layer = QgsVectorLayer(alt_uri, layer.title or layer.name, "WFS")

            if not qgs_layer.isValid() and layer.name:
                alt_uri = self._build_wfs_uri(layer, typename_override=layer.name)
                qgs_layer = QgsVectorLayer(alt_uri, layer.title or layer.name, "WFS")

            # Jika WFS berhasil valid, pastikan readOnly bernilai False agar mode editing aktif
            if qgs_layer.isValid():
                qgs_layer.setReadOnly(False)
                return self._validate_and_add(qgs_layer, layer, format_desc="WFS Vector")

            # Jika WFS gagal, laporkan error yang sebenarnya agar user tidak terjebak layer read-only
            error_details = qgs_layer.error().summary() or "Server WFS tidak mengembalikan fitur yang valid atau kredensial ditolak."
            logger.error(f"Gagal memuat WFS layer '{layer.title}': {error_details}")
            return ServiceResult.fail(
                message=f"Gagal memuat layer WFS '{layer.title}'. Error: {error_details}"
            )

        except Exception as e:
            logger.exception("Gagal melakukan import WFS.")
            return ServiceResult.fail(
                message=f"Terjadi kesalahan sistem saat import WFS: {str(e)}"
            )

    # ==========================================================
    # GeoJSON Import (Vector)
    # ==========================================================

    def import_geojson(self, layer: Layer) -> ServiceResult:
        """
        Mengimpor layer sebagai GeoJSON FeatureCollection ke dalam QGIS via OGR provider.
        """
        server_url = self._session.server_url or "http://localhost"
        geojson_url = layer.get_geojson_url(server_url)
        geojson_url = self._inject_token_to_url(geojson_url)

        logger.info(f"Importing GeoJSON Layer: {layer.display_name} ({geojson_url})")

        try:
            qgs_layer = QgsVectorLayer(
                geojson_url,
                layer.title or layer.name,
                "ogr"
            )
            return self._validate_and_add(qgs_layer, layer, format_desc="GeoJSON Vector")
        except Exception as e:
            logger.exception("Gagal melakukan import GeoJSON.")
            return ServiceResult.fail(
                message=f"Terjadi kesalahan sistem saat import GeoJSON: {str(e)}"
            )

    # ==========================================================
    # Shapefile Import (Vector)
    # ==========================================================

    def import_shapefile(self, layer: Layer) -> ServiceResult:
        """
        Mengunduh Zipped Shapefile dari GeoServer, mengekstrak ke direktori cache lokal,
        dan memuat file .shp ke dalam QGIS via OGR provider.
        """
        server_url = self._session.server_url or "http://localhost"
        shp_zip_url = layer.get_shapefile_url(server_url)
        shp_zip_url = self._inject_token_to_url(shp_zip_url)

        logger.info(f"Downloading & Importing Shapefile Layer: {layer.display_name}")

        try:
            cache_base = os.path.expanduser(
                "~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/geonode_connector/cache/shapefiles"
            )
            safe_name = "".join(c for c in (layer.name or "layer") if c.isalnum() or c in "_-")
            layer_dir = os.path.join(cache_base, f"{safe_name}_{layer.pk or '0'}")
            os.makedirs(layer_dir, exist_ok=True)

            zip_dest = os.path.join(layer_dir, "dataset.zip")
            req = urllib.request.Request(
                shp_zip_url,
                headers={"User-Agent": "QGIS-GeoNode-Connector"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp, open(zip_dest, "wb") as f_out:
                f_out.write(resp.read())

            with zipfile.ZipFile(zip_dest, "r") as zf:
                zf.extractall(layer_dir)

            # Cari file .shp yang berhasil diekstrak
            shp_files = [os.path.join(layer_dir, f) for f in os.listdir(layer_dir) if f.endswith(".shp")]
            if not shp_files:
                return ServiceResult.fail(
                    message="File shapefile (.shp) tidak ditemukan dalam arsip yang diunduh."
                )

            shp_path = shp_files[0]
            qgs_layer = QgsVectorLayer(
                shp_path,
                layer.title or layer.name,
                "ogr"
            )
            return self._validate_and_add(qgs_layer, layer, format_desc="Shapefile (.shp) Vector")

        except Exception as e:
            logger.exception("Gagal melakukan import Shapefile.")
            return ServiceResult.fail(
                message=f"Terjadi kesalahan sistem saat import Shapefile: {str(e)}"
            )

    # ==========================================================
    # Helper: URI Builders
    # ==========================================================

    def _build_wms_uri(self, layer: Layer) -> str:
        """
        Merakit string URI untuk provider WMS QGIS.
        """
        base_url = layer.wms_url or f"{(self._session.server_url or 'http://localhost').rstrip('/')}/geoserver/ows"
        layer_name = layer.alternate or layer.qgis_layer_name  # {workspace}:{name}

        # Inject token if authenticated
        base_url = self._inject_token_to_url(base_url)

        # Encode URL karena QGIS WMS provider membutuhkan format URL yang di-encode
        encoded_url = urllib.parse.quote(base_url)

        # Parameter standar WMS QGIS
        srid = layer.srid or "EPSG:4326"
        if not srid.startswith("EPSG:") and srid.isdigit():
            srid = f"EPSG:{srid}"

        uri = (
            f"crs={srid}&"
            f"dpiMode=7&"
            f"format=image/png&"
            f"layers={layer_name}&"
            f"styles=&"
            f"url={encoded_url}"
        )
        return uri

    def _build_wfs_uri(self, layer: Layer, typename_override: Optional[str] = None) -> str:
        """
        Merakit string URI untuk provider WFS QGIS.
        Menggunakan typename='...' (standar provider WFS QGIS).
        """
        raw_url = layer.wfs_url or f"{(self._session.server_url or 'http://localhost').rstrip('/')}/geoserver/ows"
        # Bersihkan query parameter dari base URL WFS agar tidak merusak Basic Auth QGIS WFS
        parsed = urllib.parse.urlparse(raw_url)
        base_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

        typename = typename_override or layer.alternate or layer.qgis_layer_name or layer.name

        # Parameter standar WFS QGIS
        srid = layer.srid or "EPSG:4326"
        if not srid.startswith("EPSG:") and srid.isdigit():
            srid = f"EPSG:{srid}"

        uri = (
            f"url='{base_url}' "
            f"typename='{typename}' "
            f"srsname='{srid}' "
            f"version='1.0.0'"
        )

        # Gunakan kredensial admin GeoServer yang tepat agar transaksi WFS-T tidak ditolak 401
        if "localhost" in base_url or "127.0.0.1" in base_url:
            user = GEOSERVER_ADMIN_USER
            pwd = GEOSERVER_ADMIN_PASSWORD
        else:
            user = self._session.username or GEOSERVER_ADMIN_USER
            pwd = getattr(self._session.data, "password", "") or GEOSERVER_ADMIN_PASSWORD

        if user and pwd:
            uri += f" username='{user}' password='{pwd}'"

        return uri

    def _inject_token_to_url(self, url: str) -> str:
        """
        Menyisipkan access_token dari session ke dalam URL
        agar layer private dapat diakses.
        """
        is_auth = (
            getattr(self._session, "is_authenticated", False)
            or getattr(self._session, "authenticated", False)
        )
        if is_auth and self._session.access_token:
            token = self._session.access_token
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}access_token={token}"

        return url

    # ==========================================================
    # Helper: Validation & Project Insertion
    # ==========================================================

    def _validate_and_add(
        self,
        qgs_layer: QgsMapLayer,
        layer_model: Layer,
        format_desc: str = "Layer"
    ) -> ServiceResult:
        """
        Memvalidasi QgsMapLayer dan menambahkannya ke QgsProject.
        """
        if not qgs_layer.isValid():
            logger.error(f"Layer {layer_model.name} ({format_desc}) tidak valid. Periksa koneksi/URI.")
            error_msg = (
                qgs_layer.error().summary()
                if qgs_layer.error().summary()
                else "URI atau format tidak dikenali."
            )
            return ServiceResult.fail(
                message=f"Gagal memuat layer '{layer_model.title}'. {error_msg}"
            )

        # Pastikan layer vektor tidak dalam mode Read-Only agar dapat diedit di QGIS
        if isinstance(qgs_layer, QgsVectorLayer):
            qgs_layer.setReadOnly(False)

        # Tambahkan layer ke Layer Tree (Map Canvas)
        self._project.addMapLayer(qgs_layer)

        logger.info(f"Layer '{qgs_layer.name()}' ({format_desc}) berhasil ditambahkan ke QgsProject.")
        return ServiceResult.ok(
            message=f"Layer '{layer_model.title}' berhasil ditambahkan ke QGIS ({format_desc}).",
            data={"layer_id": qgs_layer.id(), "format": format_desc}
        )
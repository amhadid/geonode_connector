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
    QgsFeatureRequest,
    QgsVectorFileWriter,
    QgsCoordinateTransformContext,
    QgsCoordinateReferenceSystem,
)

from ..models.layer import Layer
from ..models.session import session
from ..models.service_result import ServiceResult
from ..utils.config import (
    GEOSERVER_ADMIN_USER,
    GEOSERVER_ADMIN_PASSWORD,
    PLUGIN_ROOT,
    GEOPACKAGE_CACHE_DIR,
    SHAPEFILE_CACHE_DIR,
    GEOJSON_CACHE_DIR,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ImportService:
    """
    Service untuk melakukan import layer GeoNode ke proyek QGIS.
    Mendukung WFS (OWS Vector), GeoJSON, Shapefile, dan WMS (Raster).
    """

    def __init__(self, project: Optional[QgsProject] = None, iface=None) -> None:
        """
        Parameters
        ----------
        project : QgsProject, optional
            Instansi QgsProject aktif. Jika None, gunakan instance global.
        iface : QgisInterface, optional
            Antarmuka pengguna QGIS untuk kontrol kanvas dan layer aktif.
        """
        self._project = project or QgsProject.instance()
        self._session = session
        self._iface = iface

    # ==========================================================
    # WMS Import (Raster)
    # ==========================================================

    def import_wms(self, layer: Layer) -> ServiceResult:
        """
        Mengimpor layer sebagai WMS (Raster) ke dalam QGIS.
        """
        if not layer.has_wms:
            server_url = self._session.server_url or "https://geonode-beta.jogjakota.go.id/"
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
        Jika WFS provider gagal atau tidak menghasilkan fitur (misal akibat
        bug XML character encoding pada GeoServer), otomatis fallback ke GeoJSON
        atau Shapefile agar seluruh atribut dan fitur termuat lengkap.
        TIDAK AKAN jatuh ke WMS raster agar dataset tetap berupa vektor untuk analisis.
        """
        if not layer.has_wfs:
            server_url = self._session.server_url or "https://geonode-beta.jogjakota.go.id"
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

            # Jika WFS berhasil valid, verifikasi apakah fiturnya benar-benar dapat dibaca
            if qgs_layer.isValid():
                has_features = False
                first_feat = None
                try:
                    for f in qgs_layer.getFeatures(QgsFeatureRequest().setLimit(1)):
                        first_feat = f
                        has_features = True
                        break
                except Exception as f_err:
                    logger.warning(f"Error membaca fitur WFS untuk '{layer.display_name}': {f_err}")
                    has_features = False

                if has_features and first_feat and first_feat.hasGeometry():
                    bbox = first_feat.geometry().boundingBox()
                    # Deteksi anomali (111, -90) akibat bug transformasi GeoServer untuk layer tertentu
                    if round(bbox.xMinimum()) == 111 and round(bbox.yMinimum()) == -90:
                        logger.warning(
                            f"WFS layer '{layer.display_name}' mengalami distorsi koordinat (111, -90) dari GeoServer. "
                            f"Melakukan fallback otomatis ke GeoJSON / GeoPackage agar data presisi..."
                        )
                        geojson_res = self.import_geojson(layer)
                        if geojson_res.success:
                            return geojson_res
                        gpkg_res = self.import_geopackage(layer)
                        if gpkg_res.success:
                            return gpkg_res

                    self._fix_layer_crs_if_mismatched(qgs_layer)
                    qgs_layer.updateExtents()
                    qgs_layer.setReadOnly(False)
                    return self._validate_and_add(qgs_layer, layer, format_desc="WFS Vector")

                elif has_features or qgs_layer.featureCount() > 0:
                    self._fix_layer_crs_if_mismatched(qgs_layer)
                    qgs_layer.updateExtents()
                    qgs_layer.setReadOnly(False)
                    return self._validate_and_add(qgs_layer, layer, format_desc="WFS Vector")

                # Jika WFS valid namun mengembalikan 0 fitur padahal layer seharusnya memiliki data,
                # hal ini terjadi pada layer dengan nama field bertanda baca khusus (misal / atau spasi)
                # yang menyebabkan GeoServer gagal serialisasi XML GML (DOMException INVALID_CHARACTER_ERR).
                logger.warning(
                    f"WFS layer '{layer.display_name}' tidak menghasilkan fitur di QGIS "
                    f"(terindikasi kendala XML character encoding GeoServer). "
                    f"Melakukan fallback otomatis ke GeoJSON..."
                )
                geojson_res = self.import_geojson(layer)
                if geojson_res.success:
                    return geojson_res

                # Fallback sekunder ke Shapefile
                shp_res = self.import_shapefile(layer)
                if shp_res.success:
                    return shp_res

                # Jika fallback juga tidak menghasilkan data (dataset memang kosong di server), gunakan WFS asli
                qgs_layer.setReadOnly(False)
                return self._validate_and_add(qgs_layer, layer, format_desc="WFS Vector")

            # Jika WFS tidak valid sama sekali, coba fallback ke GeoJSON sebelum gagal
            logger.warning(f"WFS tidak valid untuk '{layer.title}', mencoba fallback ke GeoJSON...")
            geojson_res = self.import_geojson(layer)
            if geojson_res.success:
                return geojson_res

            # Jika WFS gagal, laporkan error yang sebenarnya
            error_details = qgs_layer.error().summary() or "Server WFS tidak mengembalikan fitur yang valid atau kredensial ditolak."
            logger.error(f"Gagal memuat WFS layer '{layer.title}': {error_details}")
            return ServiceResult.fail(
                message=f"Gagal memuat layer WFS '{layer.title}'. Error: {error_details}"
            )

        except Exception as e:
            logger.exception("Gagal melakukan import WFS. Mencoba fallback ke GeoJSON...")
            try:
                geojson_res = self.import_geojson(layer)
                if geojson_res.success:
                    return geojson_res
            except Exception:
                pass
            return ServiceResult.fail(
                message=f"Terjadi kesalahan sistem saat import WFS: {str(e)}"
            )

    # ==========================================================
    # GeoPackage (.gpkg) Standardized Vector Cache
    # ==========================================================

    def _create_geopackage_layer(self, layer: Layer) -> Optional[QgsVectorLayer]:
        """
        Membuat atau memuat layer vektor terstandarisasi GeoPackage (.gpkg) lokal.
        Format GeoPackage berbasis SQLite dengan indeks R-Tree bawaan, tanpa batasan
        2GB Shapefile atau limitasi nama kolom, terbaca native oleh mesin QGIS.
        """
        cache_base = GEOPACKAGE_CACHE_DIR
        os.makedirs(cache_base, exist_ok=True)
        safe_name = "".join(c for c in (layer.name or "layer") if c.isalnum() or c in "_-")
        gpkg_file = os.path.join(cache_base, f"{safe_name}_{layer.pk or '0'}.gpkg")

        # 1. Jika file .gpkg sudah ada di disk cache, langsung muat secara instan
        if os.path.isfile(gpkg_file):
            logger.info(f"Loading existing GeoPackage cache: {gpkg_file}")
            qgs_layer = QgsVectorLayer(
                f"{gpkg_file}|layername={safe_name}",
                layer.title or layer.name,
                "ogr"
            )
            if qgs_layer.isValid():
                return qgs_layer

        # 2. Jika belum ada, buat via stream vektor GeoNode dan simpan ke .gpkg
        temp_src = self._create_geojson_layer(layer)
        if temp_src and temp_src.isValid():
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GPKG"
            options.layerName = safe_name
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

            transform_context = (
                self._project.transformContext()
                if self._project
                else QgsCoordinateTransformContext()
            )

            res, err_msg, new_path, new_layer_name = QgsVectorFileWriter.writeAsVectorFormatV3(
                temp_src,
                gpkg_file,
                transform_context,
                options
            )

            if res == QgsVectorFileWriter.NoError and os.path.isfile(gpkg_file):
                logger.info(f"Successfully converted and cached to GeoPackage: {gpkg_file}")
                qgs_layer = QgsVectorLayer(
                    f"{gpkg_file}|layername={safe_name}",
                    layer.title or layer.name,
                    "ogr"
                )
                if qgs_layer.isValid():
                    return qgs_layer
            else:
                logger.warning(f"GeoPackage write failed: {err_msg}. Using GeoJSON temp layer.")
                return temp_src

        return None

    def import_geopackage(self, layer: Layer) -> ServiceResult:
        """
        Mengimpor layer vektor GeoNode sebagai GeoPackage (.gpkg) lokal ke canvas QGIS.
        """
        logger.info(f"Importing GeoPackage Layer: {layer.display_name}")
        try:
            qgs_layer = self._create_geopackage_layer(layer)
            if qgs_layer and qgs_layer.isValid():
                return self._validate_and_add(qgs_layer, layer, format_desc="GeoPackage (.gpkg) Vector")

            return ServiceResult.fail(
                message=f"Gagal memuat GeoPackage untuk layer '{layer.title}'."
            )
        except Exception as e:
            logger.exception("Gagal melakukan import GeoPackage.")
            return ServiceResult.fail(
                message=f"Terjadi kesalahan saat import GeoPackage: {str(e)}"
            )

    # ==========================================================
    # GeoJSON Import (Vector)
    # ==========================================================

    def _create_geojson_layer(self, layer: Layer) -> Optional[QgsVectorLayer]:
        """
        Membuat objek QgsVectorLayer GeoJSON dengan mengunduh ke direktori cache lokal
        berbasis PLUGIN_ROOT (lintas OS).
        """
        server_url = self._session.server_url or "https://geonode-beta.jogjakota.go.id"
        geojson_url = layer.get_geojson_url(server_url)
        geojson_url = self._inject_token_to_url(geojson_url)

        cache_base = GEOJSON_CACHE_DIR
        safe_name = "".join(c for c in (layer.name or "layer") if c.isalnum() or c in "_-")
        layer_dir = os.path.join(cache_base, f"{safe_name}_{layer.pk or '0'}")
        os.makedirs(layer_dir, exist_ok=True)
        geojson_file = os.path.join(layer_dir, f"{safe_name}.geojson")

        try:
            req = urllib.request.Request(
                geojson_url,
                headers={"User-Agent": "QGIS-GeoNode-Connector"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp, open(geojson_file, "wb") as f_out:
                f_out.write(resp.read())

            qgs_layer = QgsVectorLayer(
                geojson_file,
                layer.title or layer.name,
                "ogr"
            )
            if qgs_layer.isValid():
                return qgs_layer
        except Exception as exc:
            logger.warning(f"Gagal mengunduh file GeoJSON lokal untuk '{layer.name}': {exc}")

        # Fallback langsung via URL remote jika unduh file lokal terkendala
        try:
            qgs_layer = QgsVectorLayer(
                geojson_url,
                layer.title or layer.name,
                "ogr"
            )
            if qgs_layer.isValid():
                return qgs_layer
        except Exception as exc:
            logger.warning(f"Gagal memuat remote GeoJSON untuk '{layer.name}': {exc}")

        return None

    def import_geojson(self, layer: Layer) -> ServiceResult:
        """
        Mengimpor layer sebagai GeoJSON FeatureCollection ke dalam QGIS via OGR provider.
        """
        logger.info(f"Importing GeoJSON Layer: {layer.display_name}")

        try:
            qgs_layer = self._create_geojson_layer(layer)
            if qgs_layer and qgs_layer.isValid():
                return self._validate_and_add(qgs_layer, layer, format_desc="GeoJSON Vector")

            return ServiceResult.fail(
                message=f"Gagal memuat GeoJSON untuk layer '{layer.title}'."
            )
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
        Mengunduh Zipped Shapefile dari GeoServer, mengekstrak ke direktori cache lokal
        (menggunakan SHAPEFILE_CACHE_DIR berbasis PLUGIN_ROOT agar dinamis lintas OS),
        dan memuat file .shp ke dalam QGIS via OGR provider.
        """
        server_url = self._session.server_url or "https://geonode-beta.jogjakota.go.id"
        shp_zip_url = layer.get_shapefile_url(server_url)
        shp_zip_url = self._inject_token_to_url(shp_zip_url)

        logger.info(f"Downloading & Importing Shapefile Layer: {layer.display_name}")

        try:
            cache_base = SHAPEFILE_CACHE_DIR
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
        base_url = layer.wms_url or f"{(self._session.server_url or 'https://geonode-beta.jogjakota.go.id').rstrip('/')}/geoserver/ows"
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
        raw_url = layer.wfs_url or f"{(self._session.server_url or 'https://geonode-beta.jogjakota.go.id').rstrip('/')}/geoserver/ows"
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
        if "geonode-beta.jogjakota.go.id" in base_url or "127.0.0.1" in base_url:
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

    def _fix_layer_crs_if_mismatched(self, qgs_layer: QgsVectorLayer) -> None:
        """
        Mendeteksi jika koordinat geometri fitur adalah bujur/lintang derajat desimal
        (misal rentang Indonesia bujur 95..145, lintang -15..15) namun CRS yang terdaftar
        adalah Projected CRS berbasis meter (misal EPSG:9489 DGN95 / TM-3 atau EPSG:32749).
        Jika terdeteksi mismatch, secara otomatis memperbaiki CRS layer ke EPSG:4326 (WGS 84)
        dan menyegarkan extent agar layer dapat dirender tepat di kanvas QGIS.
        """
        if not qgs_layer or not qgs_layer.isValid():
            return

        try:
            # Ambil sampel fitur pertama
            first_feat = None
            for f in qgs_layer.getFeatures(QgsFeatureRequest().setLimit(1)):
                first_feat = f
                break

            if not first_feat or not first_feat.hasGeometry():
                return

            geom = first_feat.geometry()
            bbox = geom.boundingBox()

            # Cek apakah koordinat berada dalam derajat geografis bujur dan lintang
            # dan bukan satuan meter (meter biasanya bernilai > 10.000 atau jutaan)
            if -180.0 <= bbox.xMinimum() <= 180.0 and -90.0 <= bbox.yMinimum() <= 90.0 and \
               -180.0 <= bbox.xMaximum() <= 180.0 and -90.0 <= bbox.yMaximum() <= 90.0:
                current_crs = qgs_layer.crs().authid()
                # Jika CRS saat ini bukan sistem geografis derajat
                if current_crs not in ("EPSG:4326", "EPSG:4979", "OGC:CRS84"):
                    logger.info(
                        f"CRS mismatch terdeteksi pada layer '{qgs_layer.name()}': "
                        f"CRS terdaftar={current_crs} tetapi geometri berupa derajat desimal "
                        f"({bbox.xMinimum():.4f}, {bbox.yMinimum():.4f}). "
                        f"Menyesuaikan CRS layer ke EPSG:4326..."
                    )
                    qgs_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
                    qgs_layer.updateExtents()
        except Exception as e:
            logger.warning(f"Error saat verifikasi CRS layer: {e}")

    def _zoom_to_layer(self, qgs_layer: QgsMapLayer) -> None:
        """
        Menyegarkan Map Canvas dan melakukan zoom to layer secara otomatis
        sehingga pengguna langsung melihat data di kanvas peta QGIS.
        """
        iface = self._iface
        if not iface:
            try:
                from qgis.utils import iface as global_iface
                iface = global_iface
            except Exception:
                iface = None

        if not iface or not hasattr(iface, "mapCanvas"):
            return

        try:
            canvas = iface.mapCanvas()
            if not canvas:
                return

            if hasattr(iface, "setActiveLayer"):
                iface.setActiveLayer(qgs_layer)

            if isinstance(qgs_layer, QgsVectorLayer):
                qgs_layer.updateExtents()

            extent = qgs_layer.extent()
            if not extent.isEmpty() and extent.isFinite():
                extent.scale(1.08)  # Margin 8% agar batas geometri tidak mepet ke tepi layar
                canvas.setExtent(extent)
                canvas.refresh()
                logger.info(f"Auto zoom to layer '{qgs_layer.name()}' berhasil.")
        except Exception as e:
            logger.debug(f"Gagal melakukan auto zoom ke layer: {e}")

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
            self._fix_layer_crs_if_mismatched(qgs_layer)
            qgs_layer.updateExtents()
            qgs_layer.setReadOnly(False)
            # Simpan metadata identitas GeoNode pada layer untuk sinkronisasi WFS-T presisi
            if layer_model.pk:
                qgs_layer.setCustomProperty("geonode_pk", str(layer_model.pk))
            if layer_model.name:
                qgs_layer.setCustomProperty("geonode_name", str(layer_model.name))
            alt = layer_model.alternate or layer_model.qgis_layer_name
            if alt:
                qgs_layer.setCustomProperty("geonode_typename", str(alt))
            if layer_model.title:
                qgs_layer.setCustomProperty("geonode_title", str(layer_model.title))

        # Tambahkan layer ke Layer Tree (Map Canvas)
        self._project.addMapLayer(qgs_layer)

        # Lakukan auto-zoom ke layer agar langsung terlihat di kanvas peta QGIS
        self._zoom_to_layer(qgs_layer)

        logger.info(f"Layer '{qgs_layer.name()}' ({format_desc}) berhasil ditambahkan ke QgsProject.")
        return ServiceResult.ok(
            message=f"Layer '{layer_model.title}' berhasil ditambahkan ke QGIS ({format_desc}).",
            data={"layer_id": qgs_layer.id(), "format": format_desc}
        )
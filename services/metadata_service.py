"""
metadata_service.py

Business logic untuk Pengelolaan Metadata GeoNode (Sprint 7).
Mendukung standar ISO 19115 / SNI ISO 19115:
- Pembacaan metadata
- Validasi metadata wajib (Title, Abstract)
- Penyimpanan pembaruan metadata melalui REST API
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..api.metadata import MetadataAPI
from ..models.service_result import ServiceResult
from ..models.session import session
from ..services.activity_service import activity_service
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Kategori ISO 19115 standar jika GeoNode belum mengembalikan daftar
DEFAULT_ISO_CATEGORIES = [
    {"identifier": "biota", "gn_description": "Biota & Keanekaragaman Hayati"},
    {"identifier": "boundaries", "gn_description": "Batas Wilayah Administrasi"},
    {"identifier": "climatologyMeteorologyAtmosphere", "gn_description": "Klimatologi & Atmosfer"},
    {"identifier": "economy", "gn_description": "Ekonomi & Keuangan"},
    {"identifier": "elevation", "gn_description": "Ketinggian & Topografi"},
    {"identifier": "environment", "gn_description": "Lingkungan Hidup"},
    {"identifier": "farming", "gn_description": "Pertanian & Perkebunan"},
    {"identifier": "geoscientificInformation", "gn_description": "Informasi Kebumian & Geologi"},
    {"identifier": "health", "gn_description": "Kesehatan Masyarakat"},
    {"identifier": "imageryBaseMapsEarthCover", "gn_description": "Citra Satelit & Peta Dasar"},
    {"identifier": "inlandWaters", "gn_description": "Perairan Darat & Hidrologi"},
    {"identifier": "location", "gn_description": "Lokasi & Titik Penting"},
    {"identifier": "oceans", "gn_description": "Kelautan & Pesisir"},
    {"identifier": "planningCadastre", "gn_description": "Tata Ruang & Kadaster"},
    {"identifier": "society", "gn_description": "Sosial & Kependudukan"},
    {"identifier": "structure", "gn_description": "Fasilitas & Bangunan"},
    {"identifier": "transportation", "gn_description": "Jaringan Transportasi"},
    {"identifier": "utilitiesCommunication", "gn_description": "Utilitas & Jaringan Komunikasi"},
]

DEFAULT_LICENSES = [
    {"identifier": "not_specified", "name": "Tidak Ditentukan (Not Specified)"},
    {"identifier": "cc-by", "name": "Creative Commons Attribution (CC BY 4.0)"},
    {"identifier": "cc-by-sa", "name": "Creative Commons Attribution-ShareAlike (CC BY-SA 4.0)"},
    {"identifier": "cc-zero", "name": "Public Domain (CC0)"},
    {"identifier": "proprietary", "name": "Hak Cipta Dilindungi (All Rights Reserved)"},
]

DEFAULT_MAINTENANCE_FREQUENCIES = [
    ("asNeeded", "Sesuai Kebutuhan (As Needed)"),
    ("continual", "Berkelanjutan (Continual)"),
    ("daily", "Harian (Daily)"),
    ("weekly", "Mingguan (Weekly)"),
    ("monthly", "Bulanan (Monthly)"),
    ("quarterly", "Triwulanan (Quarterly)"),
    ("biannually", "Semesteran (Biannually)"),
    ("annually", "Tahunan (Annually)"),
    ("notPlanned", "Tidak Direncanakan (Not Planned)"),
]

DEFAULT_SPATIAL_REPRESENTATIONS = [
    ("vector", "Vektor (Vector)"),
    ("grid", "Raster / Grid"),
    ("textTable", "Tabel Teks (Text Table)"),
    ("tin", "TIN (Triangulated Irregular Network)"),
]


class MetadataService:
    """
    Business service untuk pengelolaan metadata dataset GeoNode.
    """

    def __init__(self, metadata_api: Optional[MetadataAPI] = None) -> None:
        self.api = metadata_api or MetadataAPI()
        self._session = session
        self._categories_cache: List[Dict[str, Any]] = []

    def set_server(self, server_url: str) -> None:
        self.api.set_server(server_url)

    # ==========================================================
    # Validation (Standar ISO 19115)
    # ==========================================================

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validasi kelengkapan metadata wajib sesuai ISO 19115 / SNI ISO 19115.
        Wajib:
        - title: Judul dataset
        - abstract: Ringkasan atau deskripsi dataset
        """
        errors = []
        title = (metadata.get("title") or "").strip()
        abstract = (metadata.get("abstract") or "").strip()

        if not title:
            errors.append("Judul dataset (Title) wajib diisi.")
        elif len(title) < 3:
            errors.append("Judul dataset terlalu pendek (minimal 3 karakter).")

        if not abstract or abstract.lower() == "no abstract provided":
            errors.append("Abstrak (Abstract / Deskripsi) dataset wajib diisi sesuai standar ISO 19115.")
        elif len(abstract) < 10:
            errors.append("Abstrak terlalu singkat (minimal 10 karakter).")

        return (len(errors) == 0, errors)

    # ==========================================================
    # Data Retrieval
    # ==========================================================

    def get_metadata(self, pk: int | str) -> ServiceResult:
        """
        Mengambil metadata dataset dari GeoNode.
        """
        try:
            data = self.api.get_dataset_metadata(pk)
            if data:
                return ServiceResult.ok(data=data, message="Metadata berhasil dimuat.")
            return ServiceResult.fail(message=f"Dataset dengan ID {pk} tidak ditemukan atau metadata gagal dimuat.")
        except Exception as e:
            logger.exception("Gagal memuat metadata:")
            return ServiceResult.fail(message=f"Kesalahan saat memuat metadata: {str(e)}")

    def get_categories(self) -> List[Dict[str, Any]]:
        """
        Mengembalikan daftar kategori GeoNode (dengan cache lokal & fallback ISO).
        """
        if self._categories_cache:
            return self._categories_cache

        try:
            remote = self.api.get_categories()
            if remote:
                self._categories_cache = remote
                return remote
        except Exception as e:
            logger.warning(f"Tidak dapat memuat kategori dari server: {e}")

        return DEFAULT_ISO_CATEGORIES

    def get_licenses(self) -> List[Dict[str, Any]]:
        return DEFAULT_LICENSES

    def get_maintenance_frequencies(self) -> List[Tuple[str, str]]:
        return DEFAULT_MAINTENANCE_FREQUENCIES

    def get_spatial_representations(self) -> List[Tuple[str, str]]:
        return DEFAULT_SPATIAL_REPRESENTATIONS

    # ==========================================================
    # Save & Update Metadata
    # ==========================================================

    def update_metadata(self, pk: int | str, metadata_fields: Dict[str, Any]) -> ServiceResult:
        """
        Menyimpan perubahan metadata ke GeoNode melalui REST API.
        """
        is_valid, errors = self.validate_metadata(metadata_fields)
        if not is_valid:
            return ServiceResult.fail(
                message="Validasi metadata gagal:\n• " + "\n• ".join(errors)
            )

        try:
            # Format payload untuk GeoNode API v2
            payload: Dict[str, Any] = {}
            keywords_to_apply: List[Any] = []

            for k in [
                "title",
                "abstract",
                "purpose",
                "category",
                "keywords",
                "regions",
                "language",
                "license",
                "doi",
                "attribution",
                "maintenance_frequency",
                "spatial_representation_type",
                "data_quality_statement",
                "supplemental_information",
                "constraints_other",
            ]:
                if k in metadata_fields and metadata_fields[k] is not None:
                    val = metadata_fields[k]
                    if k == "category":
                        if isinstance(val, str) and val.strip():
                            val = {"identifier": val.strip()}
                        elif isinstance(val, dict) and "identifier" in val:
                            val = {"identifier": val["identifier"]}
                        elif not val:
                            continue
                    elif k == "license":
                        if isinstance(val, str) and val.strip():
                            val = {"identifier": val.strip()}
                        elif isinstance(val, dict) and "identifier" in val:
                            val = {"identifier": val["identifier"]}
                    elif k == "spatial_representation_type":
                        if isinstance(val, str) and val.strip():
                            val = {"identifier": val.strip()}
                        elif isinstance(val, dict) and "identifier" in val:
                            val = {"identifier": val["identifier"]}
                        elif not val:
                            continue
                    elif k == "keywords":
                        # Simpan keywords untuk diterapkan langsung ke model dataset
                        # Jangan masukkan ke payload REST API serializer karena bug internal GeoNode 5:
                        # AttributeError: 'list' object has no attribute 'all' pada catalogue_post_save
                        if isinstance(val, list):
                            keywords_to_apply = val
                        elif isinstance(val, str) and val.strip():
                            keywords_to_apply = [w.strip() for w in val.split(",") if w.strip()]
                        continue

                    payload[k] = val

            success = self.api.update_dataset_metadata(pk, payload)

            # Terapkan kata kunci jika ada
            if keywords_to_apply:
                self._apply_dataset_keywords(pk, keywords_to_apply)

            if success:
                # Catat ke log aktivitas
                username = self._session.username or "admin"
                title = payload.get("title", f"Dataset #{pk}")
                activity_service.log(
                    category="metadata",
                    username=username,
                    description=f"Metadata dataset '{title}' (ID: {pk}) berhasil diperbarui.",
                )
                return ServiceResult.ok(
                    message=f"Metadata untuk '{title}' berhasil disimpan di GeoNode.",
                    data=payload,
                )
            return ServiceResult.fail(message="Server GeoNode menolak pembaruan metadata.")
        except Exception as e:
            logger.exception("Gagal menyimpan metadata:")
            return ServiceResult.fail(message=f"Gagal menyimpan metadata: {str(e)}")

    def _apply_dataset_keywords(self, pk: int | str, keywords: List[Any]) -> None:
        """
        Menerapkan kata kunci langsung ke model dataset GeoNode (Taggit)
        tanpa melewati serializer DRF yang memiliki bug korelasi ManyToMany.
        """
        if not keywords:
            return
        clean_words = []
        for kw in keywords:
            if isinstance(kw, str) and kw.strip():
                clean_words.append(kw.strip())
            elif isinstance(kw, dict) and "name" in kw:
                clean_words.append(kw["name"])
        if not clean_words:
            return
        try:
            import subprocess
            py_code = (
                f"from geonode.layers.models import Dataset; "
                f"ds = Dataset.objects.get(pk={pk}); "
                f"ds.keywords.add(*{repr(clean_words)})"
            )
            subprocess.run(
                ["docker", "exec", "django4geonode_project", "python", "manage.py", "shell", "-c", py_code],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            logger.info(f"Keywords {clean_words} berhasil dikaitkan ke dataset pk={pk}.")
        except Exception as e:
            logger.warning(f"Tidak dapat menerapkan keywords ke dataset {pk}: {e}")


metadata_service = MetadataService()

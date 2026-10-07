"""
metadata.py

REST API client untuk Pengelolaan Metadata GeoNode (Sprint 7).
Menangani pembacaan dan pembaruan metadata dataset, pengambilan kategori,
keywords, dan regions via GeoNode REST API v2.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..utils.network import NetworkClient, network_client
from ..utils.config import DEFAULT_SERVER
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MetadataAPI:
    """
    Klien REST API untuk Metadata GeoNode.
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        network: Optional[NetworkClient] = None,
    ) -> None:
        self.server_url = (server_url or DEFAULT_SERVER).rstrip("/")
        self.network = network or network_client

    def set_server(self, server_url: str) -> None:
        """Update base server URL."""
        if server_url:
            self.server_url = server_url.rstrip("/")

    # ==========================================================
    # Metadata Retrieval & Update
    # ==========================================================

    def get_dataset_metadata(self, pk: int | str) -> Optional[Dict[str, Any]]:
        """
        Mengambil metadata lengkap dari sebuah dataset via GeoNode API v2.
        """
        url = f"{self.server_url}/api/v2/datasets/{pk}/"
        logger.info(f"Mengambil metadata dataset pk={pk} dari {url}")
        resp = self.network.get(url)
        if resp.get("success") or resp.get("status_code") == 200:
            data = resp.get("data")
            if isinstance(data, dict):
                return data.get("dataset", data)
            return None
        logger.error(f"Gagal mengambil metadata pk={pk}: HTTP {resp.get('status_code')} - {resp.get('message')}")
        return None

    def update_dataset_metadata(self, pk: int | str, metadata_fields: Dict[str, Any]) -> bool:
        """
        Menyimpan pembaruan metadata ke GeoNode melalui PATCH /api/v2/datasets/{pk}/.
        """
        url = f"{self.server_url}/api/v2/datasets/{pk}/"
        payload = {"dataset": metadata_fields}
        logger.info(f"Mengirim pembaruan metadata ke {url}: {list(metadata_fields.keys())}")
        resp = self.network.patch(url, json=payload)
        if resp.get("success") or resp.get("status_code") in (200, 204):
            logger.info(f"Metadata dataset pk={pk} berhasil diperbarui di GeoNode.")
            return True
        logger.error(f"Gagal update metadata pk={pk}: HTTP {resp.get('status_code')} - {resp.get('message')}")
        return False

    # ==========================================================
    # Vocabulary & Categories
    # ==========================================================

    def get_categories(self) -> List[Dict[str, Any]]:
        """
        Mengambil daftar kategori tema resmi dari GeoNode (ISO 19115 topic categories).
        """
        url = f"{self.server_url}/api/v2/categories/"
        resp = self.network.get(url)
        if resp.get("success") or resp.get("status_code") == 200:
            data = resp.get("data")
            if isinstance(data, dict):
                return data.get("categories", [])
        return []

    def get_regions(self) -> List[Dict[str, Any]]:
        """
        Mengambil daftar wilayah dari GeoNode.
        """
        url = f"{self.server_url}/api/v2/regions/"
        resp = self.network.get(url)
        if resp.get("success") or resp.get("status_code") == 200:
            data = resp.get("data")
            if isinstance(data, dict):
                return data.get("regions", [])
        return []

"""
layer_service.py

Business logic untuk pengelolaan Dataset GeoNode.

LayerService bertanggung jawab terhadap:

- Load dataset
- Cache management
- Refresh dataset
- Pencarian layer
- Filtering
- Sorting

LayerService TIDAK melakukan komunikasi HTTP secara langsung.
Seluruh komunikasi REST dilakukan oleh DatasetAPI.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from ..api.dataset import DatasetAPI
from ..models.layer import Layer
from ..utils.config import CACHE_DIR
from ..utils.logger import get_logger

logger = get_logger(__name__)

DATASETS_CACHE_FILE = os.path.join(CACHE_DIR, "datasets_cache.json")


class LayerService:
    """
    Business Service untuk Dataset GeoNode.
    """

    def __init__(
        self,
        dataset_api: Optional[DatasetAPI] = None,
    ):
        """
        Parameters
        ----------
        dataset_api : DatasetAPI
            REST API Dataset.
        """

        self._dataset_api = (
            dataset_api
            or DatasetAPI()
        )

        self._layers: list[Layer] = []

        self._loaded: bool = False

    # ==========================================================
    # Disk Cache
    # ==========================================================

    def load_disk_cache(self) -> list[Layer]:
        """
        Memuat dataset dari file cache lokal (sangat cepat, <0.05s).
        """
        if not os.path.isfile(DATASETS_CACHE_FILE):
            return []

        try:
            with open(DATASETS_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list) and data:
                layers = [Layer.from_dict(item) for item in data if isinstance(item, dict)]
                if layers:
                    self._layers = layers
                    self._loaded = True
                    logger.info("Loaded %d datasets from persistent disk cache.", len(layers))
                    return layers
        except Exception as exc:
            logger.warning("Could not load dataset disk cache: %s", exc)

        return []

    def save_disk_cache(self, layers: list[Layer]) -> bool:
        """
        Menyimpan daftar layer ke file cache lokal.
        """
        if not layers:
            return False

        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            data = [l.to_dict() for l in layers]
            with open(DATASETS_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str)
            logger.info("Saved %d datasets to persistent disk cache.", len(layers))
            return True
        except Exception as exc:
            logger.warning("Failed to save datasets disk cache: %s", exc)
            return False

    def clear_disk_cache(self) -> None:
        """
        Menghapus file cache dataset lokal.
        """
        try:
            if os.path.isfile(DATASETS_CACHE_FILE):
                os.remove(DATASETS_CACHE_FILE)
                logger.info("Persistent datasets cache removed.")
        except Exception as exc:
            logger.warning("Failed to delete disk cache file: %s", exc)

    # ==========================================================
    # Internal
    # ==========================================================

    def _load(
        self,
        progress_callback: Optional[Any] = None,
        force_reload: bool = False,
    ) -> list[Layer]:
        """
        Memuat dataset dari GeoNode apabila cache
        belum tersedia atau dipaksa muat ulang.
        """

        if self._loaded and not force_reload:
            return self._layers

        if not force_reload:
            disk_layers = self.load_disk_cache()
            if disk_layers:
                return disk_layers

        logger.info(
            "Loading dataset cache from network..."
        )

        self._layers = (
            self._dataset_api.get_datasets(
                fetch_all=True,
                progress_callback=progress_callback,
            )
        )

        self._loaded = True
        self.save_disk_cache(self._layers)

        logger.info(
            "Dataset cache loaded (%s layer).",
            len(self._layers),
        )

        return self._layers

    def load_detail(self, pk: str) -> Optional[Layer]:
        """
        Mengambil detail spesifik dataset dari API dan memperbarui cache jika perlu.
        """
        logger.info(f"Loading details for dataset PK: {pk}")
        
        detailed_layer = self._dataset_api.get_dataset_detail(pk)
        
        if detailed_layer:
            for i, layer in enumerate(self._layers):
                if str(layer.pk) == str(pk) or (layer.id is not None and str(layer.id) == str(pk)):
                    self._layers[i] = detailed_layer
                    break
                    
        return detailed_layer

    def _update_cache(
        self,
        layers: list[Layer],
        save_disk: bool = True,
    ) -> None:
        """
        Memperbarui isi cache.
        """

        self._layers = list(layers)

        self._loaded = True

        if save_disk:
            self.save_disk_cache(self._layers)

        logger.debug(
            "Cache updated (%s layer).",
            len(self._layers),
        )

    def _find(
        self,
        pk: int | str,
    ) -> Optional[Layer]:
        """
        Mencari layer berdasarkan
        ID atau PK.
        """

        self._load()

        pk = str(pk)

        for layer in self._layers:

            if str(layer.pk) == pk:

                return layer

            if layer.id is not None:

                if str(layer.id) == pk:

                    return layer

        return None

    def get_latest_modified_timestamp(self) -> Optional[str]:
        """
        Mendapatkan ISO timestamp modifikasi terbaru dari layer yang ada di cache.
        """
        latest = None
        for layer in self._layers:
            if layer.modified:
                if latest is None or layer.modified > latest:
                    latest = layer.modified
        if latest:
            return latest.isoformat()
        return None

    def merge_layers(self, updated_layers: list[Layer]) -> list[Layer]:
        """
        Menggabungkan layer baru / termodifikasi ke dalam daftar layer lokal,
        lalu memperbarui persistent disk cache.
        """
        if not updated_layers:
            return self._layers

        existing_map = {str(l.pk): i for i, l in enumerate(self._layers)}
        for item in updated_layers:
            pk_str = str(item.pk)
            if pk_str in existing_map:
                self._layers[existing_map[pk_str]] = item
            else:
                self._layers.append(item)
                existing_map[pk_str] = len(self._layers) - 1

        self.save_disk_cache(self._layers)
        return self._layers

    def sync_delta(
        self,
        progress_callback: Optional[Any] = None,
    ) -> list[Layer]:
        """
        Melakukan delta sync: hanya meminta layer yang dimodifikasi setelah
        timestamp modifikasi terakhir yang tersimpan di cache lokal.
        """
        if not self._layers:
            self.load_disk_cache()

        if not self._layers:
            return self._load(progress_callback=progress_callback, force_reload=True)

        latest_ts = self.get_latest_modified_timestamp()
        if not latest_ts:
            return self._load(progress_callback=progress_callback, force_reload=True)

        logger.info("Syncing delta datasets since: %s", latest_ts)
        delta = self._dataset_api.get_delta_datasets(
            since_timestamp=latest_ts,
            progress_callback=progress_callback,
        )

        if delta:
            logger.info("Delta sync found %d modified/added layers.", len(delta))
            self.merge_layers(delta)
        else:
            logger.info("Delta sync: all local datasets are up to date.")

        return self._layers

    # ==========================================================
    # Public API
    # ==========================================================

    def refresh(
        self,
        progress_callback: Optional[Any] = None,
    ) -> list[Layer]:
        """
        Mengambil ulang dataset
        dari server.
        """

        logger.info(
            "Refreshing dataset..."
        )

        layers = (
            self._dataset_api.refresh(
                progress_callback=progress_callback,
            )
        )

        self._update_cache(
            layers
        )

        logger.info(
            "Dataset refreshed (%s layer).",
            len(self._layers),
        )

    def filter_layers_for_user(
        self,
        layers: list[Layer],
        username: Optional[str] = None,
        is_superuser: Optional[bool] = None,
        user_id: Optional[int] = None,
    ) -> list[Layer]:
        """
        Menyaring dataset berdasarkan hak akses pengguna GeoNode:
        - Super Admin (is_superuser=True): melihat semua dataset di geoportal.
        - Staff User / Non-admin: hanya melihat dataset yang diunggah
          oleh pengguna tersebut (berdasarkan owner_username, owner_id,
          atau metadata_author).
        """
        from ..models.session import session

        if is_superuser is None:
            is_superuser = bool(getattr(session, "is_superuser", False))

        # Super admin mendapatkan akses penuh ke seluruh dataset
        if is_superuser:
            return list(layers)

        if username is None:
            username = getattr(session, "username", "")
        if user_id is None:
            user_id = getattr(session, "user_id", None)

        if not username and user_id is None:
            return []

        filtered = [
            layer for layer in layers
            if layer.is_authored_by(username=username, user_id=user_id)
        ]
        return filtered

    def get_all(
        self,
        progress_callback: Optional[Any] = None,
        filter_by_user: bool = True,
    ) -> list[Layer]:
        """
        Mengambil seluruh dataset.

        Apabila cache belum tersedia, data akan diambil dari server.
        Jika filter_by_user=True, dataset disaring sesuai hak akses user.
        """

        layers = list(
            self._load(progress_callback=progress_callback)
        )
        if filter_by_user:
            return self.filter_layers_for_user(layers)
        return layers

    def get(
        self,
        pk: int | str,
    ) -> Optional[Layer]:
        """
        Mengambil satu layer berdasarkan
        ID atau PK.
        """

        layer = self._find(pk)

        if layer:

            return layer

        logger.debug(
            "Layer %s not found in cache. "
            "Requesting from server...",
            pk,
        )

        layer = self._dataset_api.get_dataset(pk)

        if layer:

            if layer not in self._layers:

                self._layers.append(layer)

        return layer

    def get_layer_by_pk(
        self,
        pk: int | str,
    ) -> Optional[Layer]:
        """
        Alias untuk get(pk).
        """
        return self.get(pk)

    def search(
        self,
        keyword: str,
        filter_by_user: bool = True,
    ) -> list[Layer]:
        """
        Melakukan pencarian dataset pada cache.
        Jika filter_by_user=True, pencarian hanya dilakukan pada dataset yang diizinkan untuk user saat ini.

        Pencarian dilakukan terhadap:
        - name
        - title
        - abstract
        - owner
        """

        layers = self._load()
        if filter_by_user:
            layers = self.filter_layers_for_user(layers)

        keyword = keyword.strip().lower()

        if not keyword:
            return list(layers)

        results: list[Layer] = []

        for layer in layers:

            values = (
                layer.name,
                layer.title,
                layer.abstract,
                layer.owner_username,
            )

            text = " ".join(
                value.lower()
                for value in values
                if value
            )

            if keyword in text:
                results.append(layer)

        logger.debug(
            "Search '%s' -> %s result(s).",
            keyword,
            len(results),
        )

        return results

    def filter_owner(
        self,
        owner_username: str,
    ) -> list[Layer]:
        """
        Filter layer berdasarkan owner.
        """

        owner_username = owner_username.lower()

        return [

            layer

            for layer in self._load()

            if (
                layer.owner_username
                and layer.owner_username.lower()
                == owner_username
            )
        ]

    def filter_vector(
        self,
    ) -> list[Layer]:
        """
        Mengambil seluruh Vector Layer.
        """

        return [

            layer

            for layer in self._load()

            if layer.is_vector
        ]

    def filter_raster(
        self,
    ) -> list[Layer]:
        """
        Mengambil seluruh Raster Layer.
        """

        return [

            layer

            for layer in self._load()

            if layer.is_raster
        ]

    def sort_name(
        self,
        reverse: bool = False,
    ) -> list[Layer]:
        """
        Mengurutkan layer berdasarkan nama.
        """

        return sorted(

            self._load(),

            key=lambda layer:
            (layer.display_name or "").lower(),

            reverse=reverse,
        )

    def sort_modified(
        self,
        reverse: bool = True,
    ) -> list[Layer]:
        """
        Mengurutkan layer berdasarkan
        tanggal modifikasi.

        Default:
            terbaru -> terlama
        """

        return sorted(

            self._load(),

            key=lambda layer:
            layer.modified
            or layer.created,

            reverse=reverse,
        )

    def clear_cache(
        self,
        clear_disk: bool = False,
    ) -> None:
        """
        Menghapus cache dataset di memori dan disk.
        """

        self._layers.clear()

        self._loaded = False

        if clear_disk:
            self.clear_disk_cache()

        logger.info(
            "Dataset cache cleared."
        )

    def cache_size(
        self,
    ) -> int:
        """
        Jumlah layer pada cache.
        """

        return len(
            self._layers
        )

    @property
    def loaded(
        self,
    ) -> bool:
        """
        Status cache.
        """

        return self._loaded

    @property
    def layers(
        self,
    ) -> list[Layer]:
        """
        Mengembalikan salinan cache.

        Digunakan hanya untuk kebutuhan
        read-only.
        """

        return list(
            self._layers
        )

    def __len__(
        self,
    ) -> int:
        """
        Jumlah dataset yang tersimpan
        pada cache.
        """

        return len(
            self._layers
        )

    def __repr__(
        self,
    ) -> str:

        return (
            "LayerService("
            f"layers={len(self._layers)}, "
            f"loaded={self._loaded})"
        )
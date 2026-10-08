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

from typing import Optional

from ..api.dataset import DatasetAPI
from ..models.layer import Layer
from ..utils.logger import get_logger

logger = get_logger(__name__)

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

        if not self._loaded or force_reload:

            logger.info(
                "Loading dataset cache..."
            )

            self._layers = (
                self._dataset_api.get_datasets(
                    fetch_all=True,
                    progress_callback=progress_callback,
                )
            )

            self._loaded = True

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
    ) -> None:
        """
        Memperbarui isi cache.
        """

        self._layers = list(layers)

        self._loaded = True

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

        return self._layers

    def get_all(
        self,
        progress_callback: Optional[Any] = None,
    ) -> list[Layer]:
        """
        Mengambil seluruh dataset.

        Apabila cache belum tersedia,
        data akan diambil dari server.
        """

        return list(
            self._load(progress_callback=progress_callback)
        )

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
    ) -> list[Layer]:
        """
        Melakukan pencarian dataset pada cache.

        Pencarian dilakukan terhadap:
        - name
        - title
        - abstract
        - owner
        """

        layers = self._load()

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
    ) -> None:
        """
        Menghapus cache dataset.
        """

        self._layers.clear()

        self._loaded = False

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
"""
dataset_controller.py

Controller for GeoNode Dataset Browser.

Responsibilities
----------------
- Load dataset
- Refresh dataset
- Search dataset
- Populate DatasetWidget
- Handle user interaction

Business logic remains inside LayerService.
"""

from __future__ import annotations

from typing import Optional

from ...models.layer import Layer
from ...services.layer_service import LayerService
from ...utils.logger import get_logger
from ..widgets.dataset_widget import DatasetWidget

logger = get_logger(__name__)


class DatasetController:
    """
    Controller for Browser Dataset.
    """

    def __init__(
        self,
        widget: DatasetWidget,
        layer_service: Optional[LayerService] = None,
    ):
        """
        Parameters
        ----------
        widget
            Dataset browser widget.

        layer_service
            Optional LayerService dependency.
        """

        self.widget = widget

        self.layer_service = (
            layer_service
            or LayerService()
        )

        #
        # Selected layer
        #
        self._selected_layer: Optional[Layer] = None

        self._connect_signals()

    # ==========================================================
    # Initialization
    # ==========================================================

    def _connect_signals(
        self,
    ) -> None:
        """
        Connect all widget signals.
        """

        self.widget.refreshRequested.connect(
            self.refresh
        )

        self.widget.searchRequested.connect(
            self.search
        )

        self.widget.layerSelected.connect(
            self._on_layer_selected
        )

        self.widget.layerActivated.connect(
            self._on_layer_activated
        )

        if hasattr(self.widget, "detailRequested"):
            self.widget.detailRequested.connect(
                self._on_detail_requested
            )

        if hasattr(self.widget, "exportRequested"):
            self.widget.exportRequested.connect(
                self.open_export_wizard
            )

    # ==========================================================
    # Helper
    # ==========================================================

    def _show_loading(
        self,
        message: str = "Loading dataset...",
    ) -> None:
        """
        Display loading state.
        """

        logger.debug(message)

        self.widget.show_loading(
            message
        )

    def _hide_loading(
        self,
        message: str = "",
    ) -> None:
        """
        Hide loading state.
        """

        self.widget.hide_loading()

        if message:

            self.widget.set_status(
                message
            )

    def _set_status(
        self,
        message: str,
    ) -> None:
        """
        Update widget status.
        """

        self.widget.set_status(
            message
        )

    def _populate(
        self,
        layers: list[Layer],
    ) -> None:
        """
        Populate DatasetWidget.
        """

        self.widget.populate(
            layers
        )

        logger.info(
            "Dataset browser populated (%s dataset).",
            len(layers),
        )

    # ==========================================================
    # Public API
    # ==========================================================

    def load(
        self,
    ) -> None:
        """
        Load datasets: instantly restore from disk cache if available,
        then sync silently in background; otherwise fetch asynchronously.
        """
        logger.info(
            "Loading dataset browser..."
        )

        # 1. Fast Path: Coba restore langsung dari disk cache (< 0.05 detik)
        disk_layers = self.layer_service.load_disk_cache()
        if disk_layers:
            logger.info("Restored %d datasets from disk cache instantly.", len(disk_layers))
            self._populate(disk_layers)
            self._set_status(f"{len(disk_layers)} dataset(s) (Lokal)")
            self.widget.hide_loading()
            # Sinkronisasi senyap di latar belakang menggunakan delta sync
            self._start_fetch_worker(silent=True, delta_sync=True)
            return

        # 2. Cold Path: Belum ada cache, unduh secara asinkron di background thread
        self._show_loading("Menghubungkan ke GeoNode...")
        self._start_fetch_worker(silent=False)

    def _start_fetch_worker(
        self,
        silent: bool = False,
        delta_sync: bool = False,
    ) -> None:
        """
        Menjalankan fetching dataset menggunakan background thread (QThread)
        sehingga UI QGIS tetap mulus dan responsif.
        Mendukung delta sync untuk memperbarui hanya layer yang berubah.
        """
        # Hentikan worker sebelumnya jika masih berjalan
        if hasattr(self, "_worker") and self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(500)

        from ...services.dataset_worker import DatasetFetchWorker

        since_ts = None
        if delta_sync:
            since_ts = self.layer_service.get_latest_modified_timestamp()
            if not since_ts:
                # Jika tidak ada timestamp di cache, lakukan full sync
                delta_sync = False

        self._worker = DatasetFetchWorker(
            dataset_api=self.layer_service._dataset_api,
            delta_sync=delta_sync,
            since_timestamp=since_ts,
            parent=self.widget,
        )

        def on_page_loaded(accumulated: list[Layer], count: int, total: int):
            if not silent:
                self._set_status(f"Mengunduh dataset ({count}/{total})...")
                # Tampilkan batch pertama segera agar user tidak menunggu lama
                if self.widget.row_count() == 0 and len(accumulated) > 0:
                    self._populate(accumulated)
                    self._hide_loading()

        def on_finished(fetched_layers: list[Layer]):
            if delta_sync:
                if fetched_layers:
                    merged = self.layer_service.merge_layers(fetched_layers)
                    self._populate(merged)
                    self._set_status(f"{len(merged)} dataset(s)")
                    logger.info("Delta sync merged %d updated datasets. Total: %d", len(fetched_layers), len(merged))
                else:
                    logger.info("Delta sync: all datasets up to date.")
            else:
                self.layer_service._update_cache(fetched_layers, save_disk=True)
                self._populate(fetched_layers)
                self._set_status(f"{len(fetched_layers)} dataset(s)")
                logger.info("Background dataset fetch completed successfully (%d datasets).", len(fetched_layers))

            self._hide_loading()

        def on_error(error_msg: str):
            logger.warning("Background dataset fetch encountered error: %s", error_msg)
            if not silent:
                self._hide_loading()
                if self.widget.row_count() == 0:
                    self._set_status(f"Gagal memuat dataset: {error_msg}")
                    self.widget.show_notification(f"Gagal mengambil dataset: {error_msg}", is_error=True)

        self._worker.pageLoaded.connect(on_page_loaded)
        self._worker.finished.connect(on_finished)
        self._worker.error.connect(on_error)
        self._worker.start()

    def open_export_wizard(self) -> None:
        """
        Membuka dialog wizard ekspor/upload dataset baru ke GeoNode.
        """
        from ...models.session import session
        if not session.is_authenticated:
            self.widget.show_notification("Silakan login terlebih dahulu sebelum mengekspor dataset.", is_error=True)
            return

        from ..dialogs.upload_wizard_dialog import UploadWizardDialog

        # Ambil layer aktif di QGIS jika tersedia
        active_layer = None
        try:
            from qgis.utils import iface
            if iface and iface.activeLayer():
                active_layer = iface.activeLayer()
        except Exception:
            pass

        dlg = UploadWizardDialog(
            layer=active_layer,
            layer_service=self.layer_service,
            parent=self.widget,
        )

        def on_upload_completed(data: dict):
            layer_title = data.get("title") or data.get("name") or "Dataset"
            self.widget.show_notification(f"Dataset '{layer_title}' berhasil diekspor dan ditambahkan ke GeoNode!")
            # Trigger refresh di background agar layer baru langsung masuk ke tabel katalog
            self._start_fetch_worker(silent=False, delta_sync=False)

        dlg.uploadCompleted.connect(on_upload_completed)
        dlg.exec_()

    def refresh(
        self,
    ) -> None:
        """
        Reload datasets from GeoNode asynchronously.
        """
        logger.info(
            "Refreshing dataset browser asynchronously..."
        )

        self._show_loading(
            "Memperbarui dataset dari server..."
        )
        self._start_fetch_worker(silent=False)

    def search(
        self,
        keyword: str,
    ) -> None:
        """
        Search dataset from local cache.
        """

        logger.debug(
            "Searching dataset: %s",
            keyword,
        )

        keyword = keyword.strip()

        try:

            if keyword:

                layers = (
                    self.layer_service.search(
                        keyword
                    )
                )

            else:

                layers = (
                    self.layer_service.get_all()
                )

            self._populate(
                layers
            )

            self._set_status(
                f"{len(layers)} dataset(s)"
            )

        except Exception as exc:

            logger.exception(exc)

            self.widget.clear()

            self._set_status(
                "Search failed."
            )

    # ==========================================================
    # Layer Selection
    # ==========================================================

    def _on_layer_selected(
        self,
        pk: str,
    ) -> None:
        """
        Triggered when user selects a dataset.
        Zero network delay: uses cached metadata directly.
        """

        logger.debug(
            "Dataset selected: %s",
            pk,
        )

        layer = self.layer_service.get(
            pk
        )

        if layer is None:

            self._selected_layer = None

            self._set_status(
                "Dataset not found."
            )

            return

        self._selected_layer = layer

        # Update UI Panel if widget has update_detail_panel (instan tanpa blocking HTTP)
        if hasattr(self.widget, "update_detail_panel"):
            self.widget.update_detail_panel(
                title=self._selected_layer.title or self._selected_layer.name,
                abstract=self._selected_layer.abstract or "Tidak ada deskripsi tersedia.",
                has_wms=self._selected_layer.has_wms,
                has_wfs=self._selected_layer.has_wfs
            )

        self._set_status(
            f"Selected: {self._selected_layer.display_name}"
        )

    def _on_layer_activated(
        self,
        pk: str,
    ) -> None:
        """
        Triggered when user double-clicks
        a dataset.

        Sprint 3
        --------
        Only stores the active dataset.

        Sprint 4
        --------
        Import WMS/WFS layer into QGIS.
        """

        logger.info(
            "Dataset activated: %s",
            pk,
        )

        layer = self.layer_service.get(
            pk
        )

        if layer is None:

            logger.warning(
                "Dataset not found."
            )

            return

        self._selected_layer = layer

        logger.info(
            "Current dataset: %s",
            layer.display_name,
        )

    def _on_detail_requested(
        self,
        pk: str,
    ) -> None:
        """
        Triggered when user clicks DETAIL button.
        """
        logger.info("Opening metadata editor for PK: %s", pk)
        layer = self.layer_service.get(pk)
        if layer:
            from ..dialogs.metadata_dialog import MetadataDialog
            dlg = MetadataDialog(layer=layer, parent=self.widget)
            dlg.exec_()

    # ==========================================================
    # Utility
    # ==========================================================

    def selected_layer(
        self,
    ) -> Optional[Layer]:
        """
        Return selected dataset.
        """

        return self._selected_layer

    def reset_selection(
        self,
    ) -> None:
        """
        Clear current selected dataset.
        """

        logger.debug(
            "Reset current dataset selection."
        )

        self._selected_layer = None

    def clear(
        self,
    ) -> None:
        """
        Clear Dataset Browser.
        """

        logger.info(
            "Clearing Dataset Browser..."
        )

        self.reset_selection()

        self.widget.clear()

        self._set_status(
            "Ready"
        )

    def set_busy(
        self,
        busy: bool,
        message: str = "",
    ) -> None:
        """
        Set busy state.
        """

        if busy:

            self._show_loading(
                message
                or "Loading..."
            )

        else:

            self._hide_loading(
                message
                or "Ready"
            )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def has_selection(
        self,
    ) -> bool:
        """
        True if a dataset
        is currently selected.
        """

        return (
            self._selected_layer
            is not None
        )

    @property
    def current_layer(
        self,
    ) -> Optional[Layer]:
        """
        Current active dataset.
        """

        return self._selected_layer

    @property
    def current_dataset(
        self,
    ) -> Optional[Layer]:
        """
        Alias for current_layer.

        Added for future compatibility.
        """

        return self._selected_layer

    # ==========================================================
    # Debug
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        dataset = (
            self._selected_layer.display_name
            if self._selected_layer
            else "None"
        )

        return (
            "DatasetController("
            f"selected='{dataset}', "
            f"loaded={self.layer_service.loaded}, "
            f"cache={self.layer_service.cache_size()}"
            ")"
        )
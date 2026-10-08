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
        Load all datasets from LayerService.
        """

        logger.info(
            "Loading dataset browser..."
        )

        self._show_loading("Memuat dataset...")

        def on_progress(layers_so_far: list[Layer], count: int, total: int):
            self._populate(layers_so_far)
            self._set_status(f"Memuat dataset ({count}/{total})...")
            try:
                from qgis.PyQt.QtCore import QCoreApplication
                QCoreApplication.processEvents()
            except Exception:
                pass

        try:

            layers = (
                self.layer_service.get_all(progress_callback=on_progress)
            )

            if not layers:
                layers = self.layer_service.refresh(progress_callback=on_progress)

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
                "Failed to load dataset."
            )

        finally:

            self._hide_loading()

    def refresh(
        self,
    ) -> None:
        """
        Reload datasets from GeoNode.
        """

        logger.info(
            "Refreshing dataset browser..."
        )

        self._show_loading(
            "Refreshing dataset..."
        )

        def on_progress(layers_so_far: list[Layer], count: int, total: int):
            self._populate(layers_so_far)
            self._set_status(f"Refreshing dataset ({count}/{total})...")
            try:
                from qgis.PyQt.QtCore import QCoreApplication
                QCoreApplication.processEvents()
            except Exception:
                pass

        try:

            layers = (
                self.layer_service.refresh(progress_callback=on_progress)
            )

            self._populate(
                layers
            )

            self._set_status(
                f"{len(layers)} dataset(s)"
            )

        except Exception as exc:

            logger.exception(exc)

            self._set_status(
                "Refresh failed."
            )

        finally:

            self._hide_loading()

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
        Triggered when user selects
        a dataset.
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
        
        # Ambil detail layer (API Call jika ada)
        try:
            detailed_layer = self.layer_service.load_detail(pk)
            if detailed_layer:
                self._selected_layer = detailed_layer
        except Exception as exc:
            logger.warning("Could not fetch detailed layer: %s", exc)

        # Update UI Panel if widget has update_detail_panel
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
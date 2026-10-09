"""
dataset_worker.py

Background QThread Worker untuk fetching dataset GeoNode secara asinkron.
Mencegah GUI QGIS freeze saat melakukan paginasi dataset dalam jumlah besar.
"""

from __future__ import annotations

from typing import Any, Optional

from qgis.PyQt.QtCore import QThread, pyqtSignal

from ..api.dataset import DatasetAPI
from ..models.layer import Layer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatasetFetchWorker(QThread):
    """
    QThread Worker untuk mengambil dataset dari GeoNode di latar belakang (non-blocking).
    """

    # Sinyal kemajuan setiap halaman selesai: (list[Layer], count_loaded, total_expected)
    pageLoaded = pyqtSignal(list, int, int)

    # Sinyal selesai seluruh dataset: (list[Layer])
    finished = pyqtSignal(list)

    # Sinyal error: (str)
    error = pyqtSignal(str)

    def __init__(
        self,
        dataset_api: DatasetAPI,
        search: Optional[str] = None,
        delta_sync: bool = False,
        since_timestamp: Optional[str] = None,
        parent: Optional[Any] = None,
    ):
        super().__init__(parent)
        self._dataset_api = dataset_api
        self._search = search
        self._delta_sync = delta_sync
        self._since_timestamp = since_timestamp
        self._is_cancelled = False

    def cancel(self) -> None:
        """
        Membatalkan proses fetch.
        """
        self._is_cancelled = True

    def run(self) -> None:
        """
        Dijalankan di thread terpisah.
        """
        if self._delta_sync and self._since_timestamp:
            logger.info("DatasetFetchWorker running delta sync since %s...", self._since_timestamp)
        else:
            logger.info("DatasetFetchWorker started full fetch (search=%s)...", self._search)

        try:
            def on_progress(accumulated: list[Layer], count: int, total: int):
                if self._is_cancelled:
                    raise InterruptedError("Dataset fetch cancelled by user.")
                # Emit update ke UI thread
                self.pageLoaded.emit(list(accumulated), count, total)

            if self._delta_sync and self._since_timestamp:
                layers = self._dataset_api.get_delta_datasets(
                    since_timestamp=self._since_timestamp,
                    progress_callback=on_progress,
                )
            else:
                layers = self._dataset_api.get_datasets(
                    search=self._search,
                    fetch_all=True,
                    progress_callback=on_progress,
                )

            if not self._is_cancelled:
                logger.info("DatasetFetchWorker finished with %d datasets.", len(layers))
                self.finished.emit(layers)

        except InterruptedError:
            logger.info("DatasetFetchWorker was cancelled.")
        except Exception as exc:
            logger.exception("Error in DatasetFetchWorker: %s", exc)
            self.error.emit(str(exc))

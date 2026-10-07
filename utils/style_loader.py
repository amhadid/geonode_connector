# -*- coding: utf-8 -*-
"""
style_loader.py

Utility untuk memuat Qt Style Sheet (.qss)
yang digunakan oleh seluruh widget GeoNode Connector.

Author : GeoNode Connector
"""

from __future__ import annotations

from pathlib import Path

from ..utils.logger import get_logger


LOGGER = get_logger(__name__)


class StyleLoader:
    """
    Utility class untuk memuat stylesheet (.qss).

    Contoh:
        StyleLoader.apply(self, "dataset.qss")

    atau

        css = StyleLoader.load("dataset.qss")
        self.setStyleSheet(css)
    """

    # Folder styles
    STYLE_DIR = (
        Path(__file__).resolve().parent.parent
        / "ui"
        / "styles"
    )

    @classmethod
    def get_path(cls, filename: str) -> Path:
        """
        Mengembalikan path absolut file stylesheet.

        Parameters
        ----------
        filename : str

        Returns
        -------
        Path
        """

        return cls.STYLE_DIR / filename

    @classmethod
    def exists(cls, filename: str) -> bool:
        """
        Mengecek apakah file stylesheet tersedia.
        """

        return cls.get_path(filename).exists()

    @classmethod
    def load(cls, filename: str) -> str:
        """
        Membaca isi file stylesheet.

        Parameters
        ----------
        filename : str

        Returns
        -------
        str
            Isi stylesheet.
        """

        path = cls.get_path(filename)

        if not path.exists():
            LOGGER.warning(
                "Stylesheet '%s' tidak ditemukan.",
                path
            )
            return ""

        try:

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as f:

                css = f.read()

            LOGGER.info(
                "Stylesheet loaded : %s",
                filename
            )

            return css

        except Exception:

            LOGGER.exception(
                "Gagal membaca stylesheet '%s'.",
                filename
            )

            return ""

    @classmethod
    def apply(
        cls,
        widget,
        filename: str,
    ) -> bool:
        """
        Mengaplikasikan stylesheet ke widget.

        Parameters
        ----------
        widget : QWidget

        filename : str

        Returns
        -------
        bool
        """

        css = cls.load(filename)

        if not css:
            return False

        widget.setStyleSheet(css)

        LOGGER.debug(
            "Stylesheet '%s' diterapkan.",
            filename
        )

        return True
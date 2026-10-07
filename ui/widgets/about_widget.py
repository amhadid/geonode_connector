"""
about_widget.py

Widget Informasi Plugin GeoNode Connector Jogjakota.
"""

from __future__ import annotations

import os
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
)

from ...utils.config import ICON_PATH, PLUGIN_NAME, PLUGIN_VERSION


class AboutWidget(QWidget):
    """
    Halaman Tentang Plugin.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

        # ------------------------------------------------------
        # Header Card
        # ------------------------------------------------------
        card = QFrame()
        card.setObjectName("aboutCard")
        card.setStyleSheet("""
            QFrame#aboutCard {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 16px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setAlignment(Qt.AlignCenter)
        c_layout.setSpacing(10)

        # Logo
        lbl_logo = QLabel()
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setStyleSheet("border: none; background: transparent;")
        if os.path.exists(ICON_PATH):
            pix = QPixmap(ICON_PATH)
            if not pix.isNull():
                lbl_logo.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            lbl_logo.setPixmap(QgsApplication.getThemeIcon("mActionHelpContents.svg").pixmap(48, 48))

        # Title & Subtitle
        lbl_title = QLabel(PLUGIN_NAME)
        lbl_title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #0F172A; border: none; background: transparent;")
        lbl_title.setAlignment(Qt.AlignCenter)

        lbl_version = QLabel(f"Versi {PLUGIN_VERSION}")
        lbl_version.setStyleSheet("background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; border-radius: 10px; padding: 2px 10px; font-weight: 700; font-size: 8pt;")
        lbl_version.setAlignment(Qt.AlignCenter)

        lbl_desc = QLabel(
            "Plugin integrasi data spasial resmi antara GeoNode / GeoServer\n"
            "dan QGIS Desktop untuk Pemerintah Kota Yogyakarta."
        )
        lbl_desc.setStyleSheet("color: #64748B; font-size: 8.5pt; line-height: 1.4; border: none; background: transparent;")
        lbl_desc.setAlignment(Qt.AlignCenter)

        c_layout.addWidget(lbl_logo)
        c_layout.addWidget(lbl_title)
        c_layout.addWidget(lbl_version, alignment=Qt.AlignCenter)
        c_layout.addWidget(lbl_desc)

        main_layout.addWidget(card)

        # ------------------------------------------------------
        # Info Details Card
        # ------------------------------------------------------
        detail_card = QFrame()
        detail_card.setObjectName("aboutDetailCard")
        detail_card.setStyleSheet("""
            QFrame#aboutDetailCard {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        d_layout = QVBoxLayout(detail_card)
        d_layout.setSpacing(10)

        self._add_detail_row("Pengembang", "Alif Marwan Hadid", d_layout)
        self._add_detail_row("Instansi", "Pemerintah Kota Yogyakarta", d_layout)
        self._add_detail_row("Kompatibilitas", "QGIS 3.22 - 3.40 LTR (Python 3.9+)", d_layout)
        self._add_detail_row("Dukungan Layanan", "WFS (Vector OWS), GeoJSON, Shapefile, WMS", d_layout)

        main_layout.addWidget(detail_card)
        main_layout.addStretch()

    def _add_detail_row(self, label: str, value: str, parent_layout: QVBoxLayout):
        row = QHBoxLayout()
        row.setSpacing(10)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #64748B; font-size: 8.5pt; font-weight: 500; border: none; background: transparent;")
        lbl.setFixedWidth(130)

        val = QLabel(value)
        val.setStyleSheet("color: #1E293B; font-size: 8.5pt; font-weight: 600; border: none; background: transparent;")

        row.addWidget(lbl)
        row.addWidget(val)
        row.addStretch()
        parent_layout.addLayout(row)
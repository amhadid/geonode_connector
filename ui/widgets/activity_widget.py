"""
activity_widget.py

Widget Log Aktivitas (Mockup Screen 8).
Menampilkan riwayat aktivitas pengguna dengan ikon tema bawaan QGIS.
"""

from __future__ import annotations

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QMessageBox,
)

from ...services.activity_service import activity_service, ActivityItem
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ActivityWidget(QWidget):
    """
    Menampilkan riwayat aktivitas pengguna (Mockup Screen 8).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self.reload_activities()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Title
        title_lbl = QLabel("Aktivitas Pengguna")
        title_lbl.setStyleSheet("font-size: 13pt; font-weight: bold; color: #0F172A;")
        main_layout.addWidget(title_lbl)

        # Scroll Area for Activity List
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.list_container)
        main_layout.addWidget(self.scroll, stretch=1)

        # Bottom Button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.btn_clear = QPushButton("BERSIHKAN LOG")
        self.btn_clear.setIcon(QgsApplication.getThemeIcon("mActionDeleteSelected.svg"))
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #475569;
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 8.5pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #F1F5F9;
                border-color: #94A3B8;
                color: #0F172A;
            }
        """)
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        bottom_layout.addWidget(self.btn_clear)

        main_layout.addLayout(bottom_layout)

    def _connect_signals(self):
        activity_service.activity_added.connect(self._on_activity_added)
        activity_service.activities_cleared.connect(self.reload_activities)

    def reload_activities(self):
        """
        Memuat ulang seluruh log aktivitas ke UI.
        """
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        activities = activity_service.get_activities()

        if not activities:
            empty_card = QFrame()
            empty_card.setObjectName("emptyActCard")
            empty_card.setStyleSheet("""
                QFrame#emptyActCard {
                    background: #F8FAFC;
                    border: 1px dashed #CBD5E1;
                    border-radius: 8px;
                    padding: 24px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            e_layout = QVBoxLayout(empty_card)
            e_layout.setAlignment(Qt.AlignCenter)
            e_layout.setSpacing(6)

            ico = QLabel()
            ico.setPixmap(QgsApplication.getThemeIcon("mActionPropertyItem.svg").pixmap(32, 32))
            ico.setAlignment(Qt.AlignCenter)
            ico.setStyleSheet("border: none; background: transparent;")

            lbl = QLabel("Belum ada riwayat aktivitas tercatat.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #64748B; font-size: 9pt; font-weight: 500; border: none; background: transparent;")

            e_layout.addWidget(ico)
            e_layout.addWidget(lbl)
            self.list_layout.addWidget(empty_card)
            return

        for act in activities:
            card = self._create_activity_card(act)
            self.list_layout.addWidget(card)

    def _on_activity_added(self, act: ActivityItem):
        self.reload_activities()

    def _create_activity_card(self, act: ActivityItem) -> QWidget:
        card = QFrame()
        card.setObjectName("actCard")
        card.setStyleSheet("""
            QFrame#actCard {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QFrame#actCard:hover {
                border-color: #CBD5E1;
                background: #F8FAFC;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        icon_name, bg_color = self._get_icon_props(act.category)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setAlignment(Qt.AlignCenter)
        pix = QgsApplication.getThemeIcon(icon_name).pixmap(18, 18)
        icon_lbl.setPixmap(pix)
        icon_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border: none;
                border-radius: 16px;
            }}
        """)

        # Text column
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        # Meta row: Timestamp + username (tanpa outline)
        meta_lbl = QLabel(f"{act.formatted_time}   •   {act.username}")
        meta_lbl.setStyleSheet("color: #64748B; font-size: 8pt; font-weight: 500; border: none; background: transparent;")

        # Description / isi log aktivitas (tanpa outline)
        desc_lbl = QLabel(act.description)
        desc_lbl.setStyleSheet("color: #1E293B; font-size: 9pt; font-weight: 600; border: none; background: transparent;")
        desc_lbl.setWordWrap(True)

        text_layout.addWidget(meta_lbl)
        text_layout.addWidget(desc_lbl)

        layout.addWidget(icon_lbl)
        layout.addLayout(text_layout, stretch=1)

        return card

    def _get_icon_props(self, category: str):
        mapping = {
            "login": ("user.svg", "#DCFCE7"),                    # Light Green
            "import": ("mActionAddWfsLayer.svg", "#E0F2FE"),       # Light Blue
            "edit": ("mActionToggleEditing.svg", "#FEF3C7"),       # Light Amber
            "validate": ("mIconSuccess.svg", "#DCFCE7"),           # Light Green
            "sync": ("mActionRefresh.svg", "#CCFBF1"),             # Light Teal
            "metadata": ("mActionPropertyItem.svg", "#F1F5F9"),    # Light Slate
        }
        return mapping.get(category.lower(), ("mActionPropertyItem.svg", "#F1F5F9"))

    def _on_clear_clicked(self):
        reply = QMessageBox.question(
            self,
            "Bersihkan Riwayat",
            "Apakah Anda yakin ingin menghapus seluruh log aktivitas?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            activity_service.clear()

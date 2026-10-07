"""
sync_dialog.py

Dialog Proses Sinkronisasi Layer (Mockup Screen 6).
"""

from __future__ import annotations

from typing import Optional

from qgis.core import QgsVectorLayer
from qgis.PyQt.QtCore import Qt, QTimer, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QFrame,
    QWidget,
)

from ...services.activity_service import activity_service
from ...services.sync_service import sync_service, SyncService
from ...models.session import session
from ...utils.logger import get_logger

logger = get_logger(__name__)


class SyncDialog(QDialog):
    """
    Dialog Sinkronisasi Layer sesuai Mockup Screen 6.
    Menampilkan visual stepper 5 langkah, progress bar, dan status operasi insert/update/delete.
    """
    syncCompleted = pyqtSignal()

    def __init__(
        self,
        layer: Optional[QgsVectorLayer] = None,
        layer_name: str = "",
        inserts: int = 0,
        updates: int = 0,
        deletes: int = 0,
        sync_service_instance: Optional[SyncService] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.layer = layer
        self.sync_service = sync_service_instance or sync_service

        if self.layer:
            changes = self.sync_service.get_pending_changes(self.layer)
            self.layer_name = self.layer.name()
            self.inserts = changes["inserts"]
            self.updates = changes["updates"]
            self.deletes = changes["deletes"]
            self.total_changes = changes["total"]
        else:
            self.layer_name = layer_name or "Layer"
            self.inserts = inserts
            self.updates = updates
            self.deletes = deletes
            self.total_changes = inserts + updates + deletes

        self.setWindowTitle("GeoNode Connector")
        self.resize(500, 480)
        self.setMinimumSize(450, 420)

        self._current_step = 1
        self._progress_value = 0

        self._setup_ui()
        self._start_sync()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Title Header
        title_label = QLabel("Sinkronisasi Layer")
        title_label.setStyleSheet("font-size: 15pt; font-weight: bold; color: #1e1e1e;")
        main_layout.addWidget(title_label)

        # Stepper Widget
        self.stepper_widget = self._create_stepper()
        main_layout.addWidget(self.stepper_widget)

        # Status Subtitle
        self.lbl_status = QLabel("Mempersiapkan sinkronisasi...")
        self.lbl_status.setStyleSheet("font-size: 10pt; font-weight: 500; color: #333333;")
        main_layout.addWidget(self.lbl_status)

        # Progress Bar Layout
        prog_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E6E6E6;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #2E9E55;
                border-radius: 4px;
            }
        """)

        self.lbl_percent = QLabel("0%")
        self.lbl_percent.setStyleSheet("font-size: 9pt; font-weight: bold; color: #444444; min-width: 38px;")

        prog_layout.addWidget(self.progress_bar, stretch=1)
        prog_layout.addWidget(self.lbl_percent)
        main_layout.addLayout(prog_layout)

        # Changes Breakdown Card
        changes_card = QFrame()
        changes_card.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #ECECEC;
                border-radius: 8px;
            }
        """)
        changes_layout = QVBoxLayout(changes_card)
        changes_layout.setContentsMargins(16, 14, 16, 14)
        changes_layout.setSpacing(12)

        # Insert Row
        self.row_insert = self._create_change_row("➕", "#2E9E55", "Insert", f"0 / {self.inserts}")
        # Update Row
        self.row_update = self._create_change_row("✓", "#2E9E55", "Update", f"0 / {self.updates}")
        # Delete Row
        self.row_delete = self._create_change_row("✖", "#D23B3B", "Delete", f"0 / {self.deletes}")

        changes_layout.addLayout(self.row_insert[0])
        changes_layout.addLayout(self.row_update[0])
        changes_layout.addLayout(self.row_delete[0])

        main_layout.addWidget(changes_card)

        main_layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("BATAL")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #555555;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 8px 24px;
                font-size: 9pt;
                font-weight: 500;
            }
            QPushButton:hover {
                border-color: #999999;
                background-color: #F8F8F8;
            }
        """)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)

    def _create_stepper(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(6)

        steps = ["Validasi", "Perbandingan", "Sinkronisasi", "Hasil", "Selesai"]
        self.step_circles = []
        self.step_labels = []

        for i, name in enumerate(steps, start=1):
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignCenter)
            col.setSpacing(4)

            circle = QLabel(str(i))
            circle.setFixedSize(26, 26)
            circle.setAlignment(Qt.AlignCenter)
            circle.setStyleSheet("""
                QLabel {
                    background: #EAEAEA;
                    color: #777777;
                    border-radius: 13px;
                    font-weight: bold;
                    font-size: 9pt;
                }
            """)

            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #777777; font-size: 8pt;")

            col.addWidget(circle, 0, Qt.AlignCenter)
            col.addWidget(lbl, 0, Qt.AlignCenter)

            layout.addLayout(col)
            self.step_circles.append(circle)
            self.step_labels.append(lbl)

            if i < len(steps):
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFixedHeight(2)
                line.setStyleSheet("background-color: #E2E2E2;")
                layout.addWidget(line, stretch=1)

        return widget

    def _create_change_row(self, icon_char: str, color: str, title: str, count_str: str):
        row = QHBoxLayout()
        row.setSpacing(10)

        icon_lbl = QLabel(icon_char)
        icon_lbl.setFixedSize(22, 22)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 11px;
                font-weight: bold;
                font-size: 9pt;
            }}
        """)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 9.5pt; font-weight: 500; color: #333333;")

        count_lbl = QLabel(count_str)
        count_lbl.setStyleSheet("font-size: 9.5pt; font-weight: bold; color: #555555;")
        count_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        row.addWidget(icon_lbl)
        row.addWidget(title_lbl)
        row.addStretch()
        row.addWidget(count_lbl)

        return row, count_lbl

    def _set_step(self, step_idx: int):
        self._current_step = step_idx
        for i in range(5):
            circle = self.step_circles[i]
            lbl = self.step_labels[i]
            if i + 1 < step_idx:
                circle.setStyleSheet("background: #2E9E55; color: white; border-radius: 13px; font-weight: bold;")
                lbl.setStyleSheet("color: #2E9E55; font-size: 8pt; font-weight: bold;")
            elif i + 1 == step_idx:
                circle.setStyleSheet("background: #2E9E55; color: white; border-radius: 13px; font-weight: bold;")
                lbl.setStyleSheet("color: #2E9E55; font-size: 8pt; font-weight: bold;")
            else:
                circle.setStyleSheet("background: #EAEAEA; color: #777777; border-radius: 13px; font-weight: bold;")
                lbl.setStyleSheet("color: #777777; font-size: 8pt;")

    def _start_sync(self):
        """
        Menjalankan proses sinkronisasi nyata secara bertahap.
        """
        self._set_step(1)
        self.lbl_status.setText("Memvalidasi perubahan lokal...")
        self.progress_bar.setValue(15)
        self.lbl_percent.setText("15%")

        # Step 2: Penyiapan
        QTimer.singleShot(250, self._step_prepare)

    def _step_prepare(self):
        self._set_step(2)
        self.lbl_status.setText("Menyiapkan transaksi WFS-T dengan GeoServer...")
        self.progress_bar.setValue(35)
        self.lbl_percent.setText("35%")

        # Step 3: Eksekusi WFS-T
        QTimer.singleShot(350, self._step_execute)

    def _step_execute(self):
        self._set_step(3)
        self.lbl_status.setText("Mengirim perubahan ke GeoNode / GeoServer...")
        self.progress_bar.setValue(65)
        self.lbl_percent.setText("65%")

        # Jalankan sinkronisasi sesungguhnya
        result = self.sync_service.sync_layer(self.layer)

        if not result.success:
            self._handle_error(result.message)
            return

        # Step 4: Konfirmasi
        QTimer.singleShot(300, self._step_confirm)

    def _step_confirm(self):
        self._set_step(4)
        self.lbl_status.setText("Menerima konfirmasi dari GeoServer (WFS-T)...")
        self.progress_bar.setValue(90)
        self.lbl_percent.setText("90%")

        # Step 5: Selesai
        QTimer.singleShot(300, self._step_finish)

    def _step_finish(self):
        self._set_step(5)
        self.lbl_status.setText("Sinkronisasi berhasil disimpan ke GeoNode!")
        self.progress_bar.setValue(100)
        self.lbl_percent.setText("100%")

        self.row_insert[1].setText(f"{self.inserts} / {self.inserts}")
        self.row_update[1].setText(f"{self.updates} / {self.updates}")
        self.row_delete[1].setText(f"{self.deletes} / {self.deletes}")

        # Switch button to Selesai
        self.btn_cancel.setText("SELESAI")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #2E9E55;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 24px;
                font-size: 9pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #268547;
            }
        """)

        # Catat aktivitas sinkronisasi
        username = session.username or "admin"
        activity_service.log(
            category="sync",
            username=username,
            description=f"Sinkronisasi berhasil ({self.total_changes} perubahan)",
        )
        self.syncCompleted.emit()

    def _handle_error(self, error_message: str):
        """
        Menampilkan feedback saat sinkronisasi gagal tanpa menghilangkan data lokal pengguna.
        """
        self.lbl_status.setText(f"Gagal: {error_message}")
        self.lbl_status.setStyleSheet("color: #DC2626; font-size: 8.5pt; font-weight: bold;")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #FEE2E2;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #EF4444;
                border-radius: 4px;
            }
        """)
        self.btn_cancel.setText("TUTUP")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 24px;
                font-size: 9pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
        """)

    def _on_cancel_clicked(self):
        if self._progress_value >= 100:
            self.accept()
        else:
            self.reject()

"""
change_detail_dialog.py

Dialog modern untuk menampilkan rincian lengkap perubahan fitur atau penambahan field
pada layer sebelum disinkronkan ke GeoNode.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QWidget,
)


class ChangeDetailDialog(QDialog):
    """
    Dialog untuk melihat rincian lengkap perubahan fitur atau struktur field.
    """

    def __init__(self, change_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.change_data = change_data or {}
        self.setWindowTitle("Detail Perubahan Fitur / Layer")
        self.setMinimumSize(520, 420)
        self.resize(560, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 18)
        main_layout.setSpacing(16)

        jenis = self.change_data.get("jenis", "Ubah")
        item_id = self.change_data.get("id", "-")
        waktu = self.change_data.get("waktu", "-")
        oleh = self.change_data.get("oleh", "admin")
        details = self.change_data.get("details", {})

        # ------------------------------------------------------
        # Header Card
        # ------------------------------------------------------
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_card.setStyleSheet("""
            QFrame#headerCard {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(16, 14, 16, 14)
        h_layout.setSpacing(14)

        # Ikon & badge styling sesuai jenis aksi
        icon_name, badge_bg, badge_border, badge_color, badge_text = self._get_badge_props(jenis)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(QgsApplication.getThemeIcon(icon_name).pixmap(20, 20))
        icon_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                border: 1px solid {badge_border};
                border-radius: 18px;
            }}
        """)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        lbl_title = QLabel(self._get_title_text(jenis, item_id))
        lbl_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #0F172A;")

        badge_lbl = QLabel(badge_text)
        badge_lbl.setAlignment(Qt.AlignCenter)
        badge_lbl.setStyleSheet(f"""
            QLabel {{
                background: {badge_bg};
                color: {badge_color};
                border: 1px solid {badge_border};
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 8pt;
                font-weight: 700;
            }}
        """)

        title_row.addWidget(lbl_title)
        title_row.addWidget(badge_lbl)
        title_row.addStretch()

        lbl_meta = QLabel(f"Waktu Edit: {waktu}   •   Oleh: {oleh}")
        lbl_meta.setStyleSheet("color: #64748B; font-size: 8.5pt;")

        title_layout.addLayout(title_row)
        title_layout.addWidget(lbl_meta)

        h_layout.addWidget(icon_lbl)
        h_layout.addLayout(title_layout, stretch=1)
        main_layout.addWidget(header_card)

        # ------------------------------------------------------
        # Content Section (Berdasarkan Jenis Perubahan)
        # ------------------------------------------------------
        content_widget = self._create_content_widget(jenis, details, item_id)
        main_layout.addWidget(content_widget, stretch=1)

        # ------------------------------------------------------
        # Bottom Buttons
        # ------------------------------------------------------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_close = QPushButton("TUTUP")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #059669;
                color: white;
                font-weight: bold;
                font-size: 8.5pt;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background: #047857;
            }
        """)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        main_layout.addLayout(btn_layout)

    def _get_badge_props(self, jenis: str):
        if "Tambah Field" in jenis:
            return ("mActionNewAttribute.svg", "#EFF6FF", "#BFDBFE", "#1D4ED8", "Field Baru")
        elif "Hapus Field" in jenis:
            return ("mActionDeleteAttribute.svg", "#FEF2F2", "#FECACA", "#991B1B", "Hapus Field")
        elif "Ubah" in jenis:
            return ("mActionToggleEditing.svg", "#FEF3C7", "#FDE68A", "#B45309", "Fitur Diubah")
        elif "Tambah" in jenis:
            return ("mActionAddFeature.svg", "#ECFDF5", "#A7F3D0", "#065F46", "Fitur Baru")
        elif "Hapus" in jenis:
            return ("mActionDeleteSelected.svg", "#FEF2F2", "#FECACA", "#991B1B", "Fitur Dihapus")
        return ("mIconInfo.svg", "#F8FAFC", "#CBD5E1", "#475569", jenis)

    def _get_title_text(self, jenis: str, item_id: str) -> str:
        if "Field" in jenis:
            return f"Field : {item_id}"
        return f"ID Fitur : {item_id}"

    def _create_content_widget(self, jenis: str, details: Dict[str, Any], item_id: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. KASUS: TAMBAH FIELD BARU
        if "Tambah Field" in jenis:
            info_box = QFrame()
            info_box.setObjectName("fieldCard")
            info_box.setStyleSheet("""
                QFrame#fieldCard {
                    background: white;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            ib_layout = QVBoxLayout(info_box)
            ib_layout.setContentsMargins(18, 16, 18, 16)
            ib_layout.setSpacing(10)

            lbl_heading = QLabel("Rincian Kolom / Field Atribut Baru:")
            lbl_heading.setStyleSheet("font-weight: bold; color: #1E293B; font-size: 9pt;")
            ib_layout.addWidget(lbl_heading)

            fname = details.get("field_name", item_id)
            ftype = details.get("type_name", "String (Teks)")
            flen = details.get("length", 0)
            fprec = details.get("precision", 0)

            self._add_key_val_row("Nama Kolom Baru", fname, ib_layout)
            self._add_key_val_row("Tipe Data", str(ftype), ib_layout)
            if flen and flen > 0:
                self._add_key_val_row("Panjang Karakter", str(flen), ib_layout)
            if fprec and fprec > 0:
                self._add_key_val_row("Presisi Desimal", str(fprec), ib_layout)

            note_banner = QLabel(
                "💡 Field baru ini akan secara otomatis dibuatkan kolom barunya pada "
                "tabel basis data PostGIS dan skema GeoNode saat proses sinkronisasi dijalankan."
            )
            note_banner.setWordWrap(True)
            note_banner.setStyleSheet("""
                background: #F0FDF4;
                color: #166534;
                border: 1px solid #BBF7D0;
                border-radius: 6px;
                padding: 10px;
                font-size: 8.5pt;
            """)
            ib_layout.addSpacing(6)
            ib_layout.addWidget(note_banner)
            ib_layout.addStretch()

            layout.addWidget(info_box)
            return widget

        # 2. KASUS: UBAH FITUR (UPDATE NILAI ATRIBUT / GEOMETRI)
        elif "Ubah" in jenis:
            attrs = details.get("attributes", [])
            geom_changed = details.get("geometry_changed", False)

            lbl_sub = QLabel("Daftar Perubahan Nilai Atribut:")
            lbl_sub.setStyleSheet("font-weight: bold; color: #1E293B; font-size: 9pt;")
            layout.addWidget(lbl_sub)

            if attrs:
                table = QTableWidget()
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["NAMA FIELD", "NILAI LAMA", "NILAI BARU"])
                table.setSelectionBehavior(QTableWidget.SelectRows)
                table.setSelectionMode(QTableWidget.NoSelection)
                table.verticalHeader().setVisible(False)
                table.setStyleSheet("""
                    QTableWidget {
                        background: white;
                        border: 1px solid #E2E8F0;
                        border-radius: 6px;
                        gridline-color: transparent;
                    }
                    QHeaderView::section {
                        background-color: #F8FAFC;
                        color: #475569;
                        font-weight: bold;
                        font-size: 8pt;
                        padding: 6px 10px;
                        border: none;
                        border-bottom: 1px solid #E2E8F0;
                    }
                    QTableWidget::item {
                        padding: 6px 10px;
                        border-bottom: 1px solid #F1F5F9;
                        font-size: 8.5pt;
                    }
                """)
                header = table.horizontalHeader()
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(1, QHeaderView.Stretch)
                header.setSectionResizeMode(2, QHeaderView.Stretch)

                table.setRowCount(len(attrs))
                for row, diff in enumerate(attrs):
                    f_item = QTableWidgetItem(diff.get("field", "-"))
                    f_item.setFont(table.font())

                    old_val = diff.get("old_value", "-")
                    old_item = QTableWidgetItem(old_val)
                    old_item.setForeground(Qt.gray)

                    new_val = diff.get("new_value", "-")
                    new_item = QTableWidgetItem(new_val)
                    new_item.setForeground(Qt.darkGreen)

                    table.setItem(row, 0, f_item)
                    table.setItem(row, 1, old_item)
                    table.setItem(row, 2, new_item)

                layout.addWidget(table, stretch=1)
            else:
                lbl_no_attr = QLabel("Tidak ada perubahan atribut tekstual.")
                lbl_no_attr.setStyleSheet("color: #64748B; font-size: 8.5pt;")
                layout.addWidget(lbl_no_attr)

            if geom_changed:
                geom_box = QLabel("📍 Bentuk atau koordinat geometri fitur ini telah dimodifikasi pada peta canvas QGIS.")
                geom_box.setWordWrap(True)
                geom_box.setStyleSheet("""
                    background: #FEF3C7;
                    color: #92400E;
                    border: 1px solid #FDE68A;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 8.5pt;
                    font-weight: 500;
                """)
                layout.addWidget(geom_box)

            return widget

        # 3. KASUS: TAMBAH FITUR BARU
        elif "Tambah" in jenis:
            attrs = details.get("attributes", [])
            has_geom = details.get("has_geometry", True)

            lbl_sub = QLabel("Nilai Atribut Fitur Baru:")
            lbl_sub.setStyleSheet("font-weight: bold; color: #1E293B; font-size: 9pt;")
            layout.addWidget(lbl_sub)

            if attrs:
                table = QTableWidget()
                table.setColumnCount(2)
                table.setHorizontalHeaderLabels(["NAMA FIELD", "NILAI ISIAN"])
                table.setSelectionBehavior(QTableWidget.SelectRows)
                table.setSelectionMode(QTableWidget.NoSelection)
                table.verticalHeader().setVisible(False)
                table.setStyleSheet("""
                    QTableWidget {
                        background: white;
                        border: 1px solid #E2E8F0;
                        border-radius: 6px;
                        gridline-color: transparent;
                    }
                    QHeaderView::section {
                        background-color: #F8FAFC;
                        color: #475569;
                        font-weight: bold;
                        font-size: 8pt;
                        padding: 6px 10px;
                        border: none;
                        border-bottom: 1px solid #E2E8F0;
                    }
                    QTableWidget::item {
                        padding: 6px 10px;
                        border-bottom: 1px solid #F1F5F9;
                        font-size: 8.5pt;
                    }
                """)
                header = table.horizontalHeader()
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(1, QHeaderView.Stretch)

                table.setRowCount(len(attrs))
                for row, item in enumerate(attrs):
                    f_item = QTableWidgetItem(item.get("field", "-"))
                    v_item = QTableWidgetItem(item.get("value", "-"))
                    v_item.setForeground(Qt.darkGreen)
                    table.setItem(row, 0, f_item)
                    table.setItem(row, 1, v_item)

                layout.addWidget(table, stretch=1)
            else:
                lbl_no_attr = QLabel("Fitur baru belum memiliki nilai atribut.")
                lbl_no_attr.setStyleSheet("color: #64748B; font-size: 8.5pt;")
                layout.addWidget(lbl_no_attr)

            if has_geom:
                geom_box = QLabel("✨ Objek geometri fitur baru telah digambar pada canvas.")
                geom_box.setStyleSheet("""
                    background: #ECFDF5;
                    color: #065F46;
                    border: 1px solid #A7F3D0;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 8.5pt;
                    font-weight: 500;
                """)
                layout.addWidget(geom_box)

            return widget

        # 4. KASUS: HAPUS FITUR
        elif "Hapus" in jenis:
            info_box = QFrame()
            info_box.setStyleSheet("""
                background: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 8px;
                padding: 16px;
            """)
            ib_layout = QVBoxLayout(info_box)
            lbl_del = QLabel(f"⚠️ Fitur ID #{item_id} telah dihapus dari layer.")
            lbl_del.setStyleSheet("font-weight: bold; color: #991B1B; font-size: 9.5pt;")
            lbl_del_desc = QLabel(
                "Fitur ini ditandai untuk dihapus secara permanen dari server GeoNode "
                "dan basis data PostGIS setelah Anda menekan tombol 'SINKRONISASI'."
            )
            lbl_del_desc.setWordWrap(True)
            lbl_del_desc.setStyleSheet("color: #B91C1C; font-size: 8.5pt;")
            ib_layout.addWidget(lbl_del)
            ib_layout.addWidget(lbl_del_desc)
            layout.addWidget(info_box)
            layout.addStretch()
            return widget

        else:
            lbl_misc = QLabel("Tidak ada rincian tambahan untuk aksi ini.")
            lbl_misc.setStyleSheet("color: #64748B; font-size: 8.5pt;")
            layout.addWidget(lbl_misc)
            return widget

    def _add_key_val_row(self, key: str, val: str, parent_layout: QVBoxLayout):
        row = QHBoxLayout()
        row.setSpacing(10)

        lbl_k = QLabel(key)
        lbl_k.setFixedWidth(140)
        lbl_k.setStyleSheet("color: #64748B; font-size: 8.5pt; font-weight: 500;")

        lbl_v = QLabel(val)
        lbl_v.setStyleSheet("color: #0F172A; font-size: 8.5pt; font-weight: 600;")
        lbl_v.setTextInteractionFlags(Qt.TextSelectableByMouse)

        row.addWidget(lbl_k)
        row.addWidget(lbl_v)
        row.addStretch()
        parent_layout.addLayout(row)

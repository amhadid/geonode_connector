"""
metadata_dialog.py

Dialog Detail, Preview & Editor Metadata GeoNode berstandar ISO 19115 / ISO 19139.
Menampilkan struktur preview lengkap persis seperti web GeoNode (/metadata/{id})
serta struktur XML CSW ISO 19115 (http://www.isotc211.org/2005/gmd).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt, QDate, QUrl
from qgis.PyQt.QtGui import QIcon, QFont, QDesktopServices, QColor
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
    QComboBox,
    QDateEdit,
    QPushButton,
    QTabWidget,
    QWidget,
    QFormLayout,
    QMessageBox,
    QScrollArea,
    QFrame,
    QFileDialog,
    QApplication,
    QGridLayout,
    QSizePolicy,
)

from ...models.layer import Layer
from ...services.activity_service import activity_service
from ...services.metadata_service import metadata_service
from ...models.session import session
from ...utils.logger import get_logger

logger = get_logger(__name__)


class MetadataDialog(QDialog):
    """
    Dialog Detail & Preview Metadata GeoNode berstandar ISO 19115:2003
    dan CSW pycsw.
    """

    def __init__(self, layer: Layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self._meta_data: Dict[str, Any] = {}
        self._raw_csw_xml: str = ""

        self.setWindowTitle(f"Metadata — {layer.display_name}")
        self.resize(980, 720)
        self.setMinimumSize(820, 580)

        # Gunakan styling yang selaras dengan palet bawaan QGIS
        self._setup_ui()
        self._load_metadata()

    # ==========================================================
    # UI Setup
    # ==========================================================

    def _setup_ui(self):
        # Dialog styling adaptif terhadap tema QGIS (Light / Dark)
        self.setStyleSheet("""
            QDialog {
                background-color: palette(window);
                color: palette(window-text);
            }
            QTabWidget::pane {
                border: 1px solid palette(midlight);
                background-color: palette(window);
                border-radius: 6px;
                top: -1px;
            }
            QTabBar::tab {
                background: transparent;
                padding: 9px 18px;
                color: palette(window-text);
                font-weight: 600;
                font-size: 8.5pt;
                border-bottom: 2.5px solid transparent;
            }
            QTabBar::tab:selected {
                color: #059669;
                border-bottom: 2.5px solid #10B981;
                font-weight: 700;
            }
            QTabBar::tab:hover {
                color: #10B981;
                background-color: rgba(16, 185, 129, 0.08);
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QFrame.metadataCard {
                background-color: palette(base);
                border: 1px solid palette(midlight);
                border-radius: 8px;
                padding: 16px 20px;
            }
            QFrame.heroCard {
                background-color: palette(base);
                border: 1px solid palette(midlight);
                border-radius: 8px;
                padding: 16px 20px;
            }
            QFrame.quoteBox {
                background-color: palette(window);
                border-left: 4px solid #10B981;
                border-radius: 4px;
                padding: 10px 14px;
            }
            QLabel.groupTitle {
                font-weight: 700;
                font-size: 10pt;
                color: #059669;
                border-bottom: 1.5px solid #10B981;
                padding-bottom: 5px;
                margin-bottom: 8px;
            }
            QLabel.fieldLabel {
                color: palette(text);
                opacity: 0.75;
                font-weight: 600;
                font-size: 8.5pt;
            }
            QLabel.fieldValue {
                color: palette(text);
                font-size: 8.5pt;
            }
            QLineEdit, QTextEdit, QComboBox, QDateEdit {
                border: 1.5px solid palette(midlight);
                border-radius: 6px;
                padding: 6px 10px;
                background-color: palette(base);
                color: palette(text);
                font-size: 8.5pt;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1.5px solid #10B981;
            }
            QPushButton.actionBtn {
                background-color: palette(button);
                color: palette(button-text);
                border: 1px solid palette(midlight);
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 8pt;
            }
            QPushButton.actionBtn:hover {
                background-color: rgba(16, 185, 129, 0.12);
                border-color: #10B981;
                color: #059669;
            }
            QPushButton.primaryBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
                font-size: 8.5pt;
            }
            QPushButton.primaryBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #059669, stop:1 #047857);
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # 1. Top Header Banner
        self._build_header(main_layout)

        # 2. Main Tabs
        self.tabs = QTabWidget()
        self.tab_preview = self._create_preview_tab()
        self.tab_xml = self._create_xml_tab()
        self.tab_edit = self._create_edit_tab()

        self.tabs.addTab(
            self.tab_preview,
            QgsApplication.getThemeIcon("mActionPropertyItem.svg"),
            "PREVIEW METADATA (ISO 19115)"
        )
        self.tabs.addTab(
            self.tab_xml,
            QgsApplication.getThemeIcon("mActionShowAllLayers.svg"),
            "STRUKTUR XML CSW (GMD)"
        )
        self.tabs.addTab(
            self.tab_edit,
            QgsApplication.getThemeIcon("mActionEditTable.svg"),
            "EDIT METADATA"
        )

        main_layout.addWidget(self.tabs, stretch=1)

        # 3. Bottom Footer Actions
        self._build_footer(main_layout)

    def _build_header(self, parent_layout: QVBoxLayout):
        """Header dengan info judul dataset, subtype, dan quick links."""
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet("""
            QFrame#headerFrame {
                background-color: palette(base);
                border: 1px solid palette(midlight);
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(10, 8, 10, 8)
        h_layout.setSpacing(12)

        # Icon dataset
        icon_lbl = QLabel()
        icon_svg = "mActionAddWfsLayer.svg" if self.layer.is_vector else "mActionAddWmsLayer.svg"
        icon_lbl.setPixmap(QgsApplication.getThemeIcon(icon_svg).pixmap(32, 32))
        h_layout.addWidget(icon_lbl)

        # Judul & UUID
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        self.lbl_header_title = QLabel(self.layer.display_name)
        self.lbl_header_title.setStyleSheet("font-size: 12pt; font-weight: 700; color: palette(text);")
        self.lbl_header_title.setWordWrap(True)
        title_row.addWidget(self.lbl_header_title, stretch=1)

        # Badge Tipe
        type_str = "VEKTOR" if self.layer.is_vector else ("RASTER" if self.layer.is_raster else "DATASET")
        badge_type = QLabel(type_str)
        badge_type.setStyleSheet("""
            background-color: #ECFDF5;
            color: #065F46;
            font-size: 7.5pt;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid #A7F3D0;
        """)
        title_row.addWidget(badge_type)

        title_box.addLayout(title_row)

        # Subtitle: Workspace:Layer & UUID
        sub_text = f"Layer: {self.layer.layer_name}"
        if self.layer.uuid:
            sub_text += f"  •  UUID: {self.layer.uuid}"
        self.lbl_header_sub = QLabel(sub_text)
        self.lbl_header_sub.setStyleSheet("font-size: 8pt; color: #64748B;")
        self.lbl_header_sub.setWordWrap(True)
        title_box.addWidget(self.lbl_header_sub)

        h_layout.addLayout(title_box, stretch=1)

        # Quick Buttons di Header
        self.btn_open_web = QPushButton("Buka di Web")
        self.btn_open_web.setProperty("class", "actionBtn")
        self.btn_open_web.setIcon(QgsApplication.getThemeIcon("mIconConnect.svg"))
        self.btn_open_web.setCursor(Qt.PointingHandCursor)
        self.btn_open_web.clicked.connect(self._open_web_preview)
        h_layout.addWidget(self.btn_open_web)

        parent_layout.addWidget(header_frame)

    # ==========================================================
    # Tab 1: Preview Metadata (Tampilan persis /metadata/{id})
    # ==========================================================

    def _create_preview_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.preview_layout = QVBoxLayout(container)
        self.preview_layout.setContentsMargins(12, 12, 12, 12)
        self.preview_layout.setSpacing(14)

        # Placeholder loading
        self.lbl_loading_preview = QLabel("Memuat metadata lengkap dari GeoNode...")
        self.lbl_loading_preview.setStyleSheet("color: #64748B; font-style: italic;")
        self.preview_layout.addWidget(self.lbl_loading_preview)

        scroll.setWidget(container)
        return scroll

    # Helper formatters data
    def _clean_str(self, val: Any, default: str = "-") -> str:
        if val is None:
            return default
        if isinstance(val, dict):
            return val.get("name") or val.get("identifier") or val.get("title") or val.get("gn_description") or default
        s = str(val).strip()
        return s if s else default

    def _clean_restriction(self, val: Any) -> str:
        if isinstance(val, dict):
            code = val.get("identifier") or val.get("code") or ""
        else:
            code = str(val or "")
        code_lower = code.lower()
        if "copyright" in code_lower:
            return "Hak Cipta Dilindungi (Copyright)"
        if "license" in code_lower:
            return "Penggunaan Sesuai Lisensi Dataset"
        if "patent" in code_lower:
            return "Paten Terdaftar"
        if "trademark" in code_lower:
            return "Merek Dagang Terdaftar"
        if "restricted" in code_lower:
            return "Terbatas / Akses Bersyarat"
        if "other" in code_lower:
            return "Batasan Tertentu Lainnya"
        return code.capitalize() if code else "Hak Cipta Dilindungi (Copyright)"

    def _copy_text_to_clipboard(self, text: str, hint: str = "Teks"):
        QApplication.clipboard().setText(text)
        self.lbl_status.setText(f"✓ {hint} berhasil disalin ke clipboard.")

    def _populate_preview_ui(self, meta: Dict[str, Any]):
        """Menyusun seluruh informasi metadata dalam format kartu modern persis GeoNode."""
        # Bersihkan container
        while self.preview_layout.count() > 0:
            item = self.preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Ekstraksi field-field utama
        uuid_str = meta.get("uuid") or getattr(self.layer, "uuid", "") or "-"
        title_str = meta.get("title") or getattr(self.layer, "title", self.layer.display_name)
        alt_title = meta.get("alternate") or getattr(self.layer, "alternate", self.layer.layer_name)
        abstract_str = meta.get("abstract") or getattr(self.layer, "abstract", "Tidak ada ringkasan abstrak yang disediakan.")
        
        cat_val = meta.get("category")
        cat_name = (cat_val.get("gn_description") or cat_val.get("identifier")) if isinstance(cat_val, dict) else (str(cat_val) if cat_val else "Location")
        
        lic_val = meta.get("license")
        lic_name = (lic_val.get("name") or lic_val.get("identifier")) if isinstance(lic_val, dict) else (str(lic_val) if lic_val else "Public Domain")
        
        srid_val = meta.get("srid") or getattr(self.layer, "srid", "EPSG:4326")
        rep_val = meta.get("spatial_representation_type")
        rep_name = rep_val.get("identifier", "vector") if isinstance(rep_val, dict) else (str(rep_val) if rep_val else ("Vektor" if self.layer.is_vector else "Grid / Raster"))

        date_str = str(meta.get("date") or meta.get("created") or "-")
        date_type = str(meta.get("date_type") or "publication").capitalize()

        # ------------------------------------------------------
        # KARTU HERO: RINGKASAN DATASET & ABSTRAK
        # ------------------------------------------------------
        card_hero = QFrame()
        card_hero.setProperty("class", "heroCard")
        hero_layout = QVBoxLayout(card_hero)
        hero_layout.setSpacing(10)

        # Title & Badges Bar
        lbl_h_title = QLabel(title_str)
        lbl_h_title.setStyleSheet("font-size: 13pt; font-weight: 800; color: palette(text);")
        lbl_h_title.setWordWrap(True)
        lbl_h_title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        hero_layout.addWidget(lbl_h_title)

        pills_row = QHBoxLayout()
        pills_row.setSpacing(6)

        def make_pill(text: str, bg: str, fg: str, bd: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"""
                background-color: {bg};
                color: {fg};
                border: 1px solid {bd};
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 7.5pt;
                font-weight: 700;
            """)
            return lbl

        pills_row.addWidget(make_pill(f"TEMA: {cat_name.upper()}", "#EFF6FF", "#1E40AF", "#BFDBFE"))
        pills_row.addWidget(make_pill(f"LISENSI: {lic_name}", "#ECFDF5", "#065F46", "#A7F3D0"))
        pills_row.addWidget(make_pill(f"CRS: {srid_val}", "#F5F3FF", "#5B21B6", "#DDD6FE"))
        pills_row.addWidget(make_pill(f"TIPE: {rep_name.upper()}", "#FFFBEB", "#92400E", "#FDE68A"))
        pills_row.addStretch()
        hero_layout.addLayout(pills_row)

        # Quote Abstrak
        quote_box = QFrame()
        quote_box.setProperty("class", "quoteBox")
        q_box_layout = QVBoxLayout(quote_box)
        q_box_layout.setContentsMargins(12, 10, 12, 10)
        q_box_layout.setSpacing(4)

        lbl_q_header = QLabel("Ringkasan & Abstrak (Abstract):")
        lbl_q_header.setStyleSheet("font-weight: 700; font-size: 8pt; color: #059669;")
        lbl_q_text = QLabel(abstract_str)
        lbl_q_text.setStyleSheet("font-size: 8.5pt; line-height: 1.4; color: palette(text);")
        lbl_q_text.setWordWrap(True)
        lbl_q_text.setTextInteractionFlags(Qt.TextSelectableByMouse)

        q_box_layout.addWidget(lbl_q_header)
        q_box_layout.addWidget(lbl_q_text)
        hero_layout.addWidget(quote_box)

        self.preview_layout.addWidget(card_hero)

        # ------------------------------------------------------
        # KARTU 1: IDENTITAS & INFORMASI GEOSPASIAL (GENERAL)
        # ------------------------------------------------------
        card_general = QFrame()
        card_general.setProperty("class", "metadataCard")
        g_layout = QVBoxLayout(card_general)
        g_layout.setSpacing(8)

        title_g = QLabel("Informasi Umum & Identitas Geospasial (General)")
        title_g.setProperty("class", "groupTitle")
        g_layout.addWidget(title_g)

        def add_detail_row(label: str, widget_or_text: Any):
            row_frame = QFrame()
            row_frame.setStyleSheet("border-bottom: 1px solid palette(midlight);")
            r_box = QHBoxLayout(row_frame)
            r_box.setContentsMargins(4, 5, 4, 5)
            r_box.setSpacing(12)

            lbl = QLabel(label)
            lbl.setProperty("class", "fieldLabel")
            lbl.setFixedWidth(175)
            r_box.addWidget(lbl, alignment=Qt.AlignTop)

            if isinstance(widget_or_text, QWidget):
                r_box.addWidget(widget_or_text, stretch=1)
            else:
                val_lbl = QLabel(str(widget_or_text))
                val_lbl.setProperty("class", "fieldValue")
                val_lbl.setWordWrap(True)
                val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                r_box.addWidget(val_lbl, stretch=1)

            g_layout.addWidget(row_frame)

        # UUID dengan copy button
        uuid_widget = QWidget()
        uw_layout = QHBoxLayout(uuid_widget)
        uw_layout.setContentsMargins(0, 0, 0, 0)
        uw_layout.setSpacing(8)

        lbl_uuid_val = QLabel(uuid_str)
        lbl_uuid_val.setStyleSheet("""
            font-family: monospace;
            background-color: palette(window);
            border: 1px solid palette(midlight);
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 8.5pt;
            font-weight: 600;
            color: palette(text);
        """)
        lbl_uuid_val.setTextInteractionFlags(Qt.TextSelectableByMouse)

        btn_copy_uuid = QPushButton("Salin UUID")
        btn_copy_uuid.setProperty("class", "actionBtn")
        btn_copy_uuid.setIcon(QgsApplication.getThemeIcon("mActionEditCopy.svg"))
        btn_copy_uuid.setCursor(Qt.PointingHandCursor)
        btn_copy_uuid.clicked.connect(lambda: self._copy_text_to_clipboard(uuid_str, "UUID"))

        uw_layout.addWidget(lbl_uuid_val)
        uw_layout.addWidget(btn_copy_uuid)
        uw_layout.addStretch()
        add_detail_row("Identifier / UUID", uuid_widget)

        # Alternate Title
        add_detail_row("Judul Teknis (Alternate)", alt_title)

        # Group
        group_val = meta.get("group")
        group_name = group_val.get("name", str(group_val)) if isinstance(group_val, dict) else (str(group_val) if group_val else "Simpul Jaringan Kota Yogyakarta")
        add_detail_row("Kelompok (Group)", group_name)

        # Keywords as Tag Pills
        raw_kw = meta.get("keywords") or meta.get("raw_keywords") or []
        kw_list = []
        if isinstance(raw_kw, list):
            for k in raw_kw:
                kw_list.append(k.get("name", str(k)) if isinstance(k, dict) else str(k))
        elif isinstance(raw_kw, str):
            kw_list = [w.strip() for w in raw_kw.split(",") if w.strip()]

        if kw_list:
            tags_widget = QWidget()
            tags_layout = QHBoxLayout(tags_widget)
            tags_layout.setContentsMargins(0, 0, 0, 0)
            tags_layout.setSpacing(6)
            for kw in kw_list:
                tag = QLabel(kw)
                tag.setStyleSheet("""
                    background-color: palette(window);
                    color: palette(text);
                    border: 1px solid palette(midlight);
                    border-radius: 10px;
                    padding: 2px 10px;
                    font-size: 7.5pt;
                    font-weight: 600;
                """)
                tags_layout.addWidget(tag)
            tags_layout.addStretch()
            add_detail_row("Kata Kunci (Keywords)", tags_widget)
        else:
            add_detail_row("Kata Kunci (Keywords)", "-")

        # Regions
        reg_val = meta.get("regions")
        reg_name = "Indonesia, D.I. Yogyakarta, Kota Yogyakarta"
        if isinstance(reg_val, list) and reg_val:
            reg_name = ", ".join([r.get("name", str(r)) if isinstance(r, dict) else str(r) for r in reg_val])
        add_detail_row("Cakupan Wilayah", reg_name)

        # Date
        add_detail_row("Tanggal Pembaruan", f"{date_str} ({date_type})")

        # Spatial Representation
        add_detail_row("Representasi Spasial", rep_name)

        # CRS
        add_detail_row("Sistem Koordinat (CRS)", f"{srid_val} (WGS 84 / Geographic)")

        # Bounding Box 4 Kotak Presisi
        bbox = meta.get("extent") or getattr(self.layer, "extent", None)
        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            w, s, e, n = bbox[0], bbox[1], bbox[2], bbox[3]
        else:
            w, s, e, n = 110.34563, -7.83566, 110.40433, -7.77119

        bbox_widget = QWidget()
        bb_layout = QHBoxLayout(bbox_widget)
        bb_layout.setContentsMargins(0, 4, 0, 4)
        bb_layout.setSpacing(8)

        def make_bbox_card(dir_label: str, coord_val: float) -> QFrame:
            f = QFrame()
            f.setStyleSheet("""
                QFrame {
                    background-color: palette(window);
                    border: 1px solid palette(midlight);
                    border-radius: 6px;
                    padding: 6px 10px;
                }
            """)
            fl = QVBoxLayout(f)
            fl.setContentsMargins(4, 2, 4, 2)
            fl.setSpacing(1)
            lbl_d = QLabel(dir_label)
            lbl_d.setStyleSheet("font-size: 7pt; font-weight: 700; color: #64748B;")
            lbl_v = QLabel(f"{coord_val:.5f}°")
            lbl_v.setStyleSheet("font-size: 8.5pt; font-weight: 700; font-family: monospace; color: palette(text);")
            fl.addWidget(lbl_d)
            fl.addWidget(lbl_v)
            return f

        bb_layout.addWidget(make_bbox_card("BARAT (WEST)", w))
        bb_layout.addWidget(make_bbox_card("SELATAN (SOUTH)", s))
        bb_layout.addWidget(make_bbox_card("TIMUR (EAST)", e))
        bb_layout.addWidget(make_bbox_card("UTARA (NORTH)", n))
        bb_layout.addStretch()
        add_detail_row("Batas Koordinat (BBOX)", bbox_widget)

        self.preview_layout.addWidget(card_general)

        # ------------------------------------------------------
        # KARTU 2: KETENTUAN, HAK AKSES & LISENSI
        # ------------------------------------------------------
        card_terms = QFrame()
        card_terms.setProperty("class", "metadataCard")
        t_layout = QVBoxLayout(card_terms)
        t_layout.setSpacing(8)

        title_t = QLabel("Ketentuan Penggunaan & Lisensi (Rights & Licensing)")
        title_t.setProperty("class", "groupTitle")
        t_layout.addWidget(title_t)

        def add_term_row(label: str, val_text: str):
            row_frame = QFrame()
            row_frame.setStyleSheet("border-bottom: 1px solid palette(midlight);")
            r_box = QHBoxLayout(row_frame)
            r_box.setContentsMargins(4, 5, 4, 5)
            r_box.setSpacing(12)

            lbl = QLabel(label)
            lbl.setProperty("class", "fieldLabel")
            lbl.setFixedWidth(175)
            r_box.addWidget(lbl, alignment=Qt.AlignTop)

            val_lbl = QLabel(val_text)
            val_lbl.setProperty("class", "fieldValue")
            val_lbl.setWordWrap(True)
            val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            r_box.addWidget(val_lbl, stretch=1)

            t_layout.addWidget(row_frame)

        add_term_row("Lisensi Resmi", lic_name)

        # Restrictions dibersihkan dari raw dict python
        raw_restr = meta.get("restriction_code_type") or meta.get("constraints_other") or "copyright"
        cleaned_restr = self._clean_restriction(raw_restr)
        add_term_row("Batasan Akses (Restrictions)", cleaned_restr)

        attr_val = meta.get("attribution") or f"Pencipta: {self.layer.owner_username or 'Pemerintah Kota Yogyakarta'}"
        add_term_row("Atribusi Pencipta", attr_val)

        purpose_val = meta.get("purpose") or "Publikasi data spasial resmi Pemerintah Kota Yogyakarta untuk integrasi geospasial."
        add_term_row("Tujuan Penggunaan (Purpose)", purpose_val)

        maint_val = meta.get("maintenance_frequency") or "irregular (sesuai kebutuhan perbaruan data OPD)"
        add_term_row("Frekuensi Pemeliharaan", maint_val)

        supp_val = meta.get("supplemental_information") or "Dataset ini diintegrasikan melalui GeoNode & GeoServer Kota Yogyakarta."
        add_term_row("Informasi Tambahan", supp_val)

        self.preview_layout.addWidget(card_terms)

        # ------------------------------------------------------
        # KARTU 3: KUALITAS DATA & LINEAGE
        # ------------------------------------------------------
        card_dq = QFrame()
        card_dq.setProperty("class", "metadataCard")
        dq_layout = QVBoxLayout(card_dq)
        dq_layout.setSpacing(8)

        title_dq = QLabel("Kualitas Data & Riwayat Pengolahan (Lineage)")
        title_dq.setProperty("class", "groupTitle")
        dq_layout.addWidget(title_dq)

        dq_text = meta.get("data_quality_statement") or (
            "1. Keakuratan Posisi: Mengikuti sistem referensi koordinat resmi WGS 84 (EPSG:4326).\n"
            "2. Keakuratan Atribut: Atribut diverifikasi oleh dinas pengampu pengelola data spasial.\n"
            "3. Kelengkapan: Data mencakup batas administratif resmi Pemerintah Kota Yogyakarta.\n"
            "4. Konsistensi Logis: Topologi dan konsistensi data telah divalidasi dengan standar OGC.\n"
            "5. Riwayat Pengolahan: Dikelola melalui QGIS Desktop dan disinkronkan ke server GeoNode."
        )
        lbl_dq_val = QLabel(dq_text)
        lbl_dq_val.setProperty("class", "fieldValue")
        lbl_dq_val.setWordWrap(True)
        lbl_dq_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        dq_layout.addWidget(lbl_dq_val)

        self.preview_layout.addWidget(card_dq)

        # ------------------------------------------------------
        # KARTU 4: KONTAK & PENANGGUNG JAWAB (CONTACTS)
        # ------------------------------------------------------
        card_contacts = QFrame()
        card_contacts.setProperty("class", "metadataCard")
        c_layout = QVBoxLayout(card_contacts)
        c_layout.setSpacing(10)

        title_c = QLabel("Kontak & Penanggung Jawab (Contacts & Roles)")
        title_c.setProperty("class", "groupTitle")
        c_layout.addWidget(title_c)

        roles_to_display = [
            ("Owner", meta.get("owner"), "#ECFDF5", "#065F46", "#A7F3D0"),
            ("Metadata Author", meta.get("metadata_author") or meta.get("owner"), "#EFF6FF", "#1E40AF", "#BFDBFE"),
            ("Point of Contact", meta.get("poc") or meta.get("owner"), "#F0FDFA", "#0F766E", "#99F6E4"),
            ("Publisher", meta.get("publisher"), "#F5F3FF", "#5B21B6", "#DDD6FE"),
            ("Custodian", meta.get("custodian") or meta.get("owner"), "#FFFBEB", "#92400E", "#FDE68A"),
            ("Distributor", meta.get("distributor"), "#F8FAFC", "#334155", "#CBD5E1"),
            ("Processor", meta.get("processor") or meta.get("owner"), "#FEF2F2", "#991B1B", "#FECACA"),
            ("Resource Provider", meta.get("resource_provider") or meta.get("owner"), "#ECFDF5", "#065F46", "#A7F3D0"),
        ]

        contacts_grid = QGridLayout()
        contacts_grid.setSpacing(10)
        contacts_grid.setColumnStretch(0, 1)
        contacts_grid.setColumnStretch(1, 1)
        c_col = 0
        c_row = 0

        for r_title, r_obj, bg_c, fg_c, bd_c in roles_to_display:
            r_name = "-"
            r_org = "Dinas Terkait Pemkot Yogyakarta"
            r_email = "kominfosandi@jogjakota.go.id"

            if isinstance(r_obj, dict):
                r_name = r_obj.get("username") or r_obj.get("name") or "-"
                first = r_obj.get("first_name", "")
                last = r_obj.get("last_name", "")
                if first or last:
                    r_org = f"{first} {last}".strip()
                r_email = r_obj.get("email") or r_email
            elif isinstance(r_obj, str) and r_obj:
                r_name = r_obj
                r_org = r_obj
            elif r_title in ("Publisher", "Distributor"):
                r_name = "Kominfo"
                r_org = "Dinas Komunikasi Informatika dan Persandian Kota Yogyakarta"
            else:
                r_name = self.layer.owner_username or "admin"
                r_org = "Pemerintah Kota Yogyakarta"

            item_card = QFrame()
            item_card.setStyleSheet("""
                QFrame {
                    background-color: palette(window);
                    border: 1px solid palette(midlight);
                    border-radius: 6px;
                    padding: 8px 10px;
                }
            """)
            i_box = QVBoxLayout(item_card)
            i_box.setContentsMargins(6, 6, 6, 6)
            i_box.setSpacing(4)

            # Role pill
            role_badge = QLabel(r_title.upper())
            role_badge.setStyleSheet(f"""
                font-size: 7pt;
                font-weight: 700;
                color: {fg_c};
                background-color: {bg_c};
                border: 1px solid {bd_c};
                border-radius: 3px;
                padding: 1px 6px;
            """)
            i_box.addWidget(role_badge, alignment=Qt.AlignLeft)

            lbl_nm = QLabel(r_org)
            lbl_nm.setStyleSheet("font-size: 8.5pt; font-weight: 700; color: palette(text);")
            lbl_nm.setWordWrap(True)
            i_box.addWidget(lbl_nm)

            lbl_sub = QLabel(f"Akun: {r_name}  •  {r_email}")
            lbl_sub.setStyleSheet("font-size: 7.5pt; color: #64748B;")
            lbl_sub.setWordWrap(True)
            i_box.addWidget(lbl_sub)

            contacts_grid.addWidget(item_card, c_row, c_col)
            c_col += 1
            if c_col > 1:
                c_col = 0
                c_row += 1

        c_layout.addLayout(contacts_grid)
        self.preview_layout.addWidget(card_contacts)

        # ------------------------------------------------------
        # KARTU 5: LAYANAN DISTRIBUSI & ENDPOINT OGC
        # ------------------------------------------------------
        card_dist = QFrame()
        card_dist.setProperty("class", "metadataCard")
        d_layout = QVBoxLayout(card_dist)
        d_layout.setSpacing(10)

        title_d = QLabel("Layanan & Akses Data (Online Resources & Endpoints)")
        title_d.setProperty("class", "groupTitle")
        d_layout.addWidget(title_d)

        server_url = metadata_service.api.server_url.rstrip("/")
        endpoints = [
            (
                "OGC WFS",
                "Web Feature Service (Vector Features OWS)",
                getattr(self.layer, "wfs_url", f"{server_url}/geoserver/ows?service=WFS&version=2.0.0"),
                "#EFF6FF", "#1E40AF"
            ),
            (
                "OGC WMS",
                "Web Map Service (Raster Map Tiles OWS)",
                getattr(self.layer, "wms_url", f"{server_url}/geoserver/ows?service=WMS&version=1.3.0"),
                "#ECFDF5", "#065F46"
            ),
            (
                "GeoJSON",
                "Direct Feature Download Endpoint",
                getattr(self.layer, "geojson_url", f"{server_url}/geoserver/ows?service=WFS&request=GetFeature&outputFormat=json"),
                "#FFFBEB", "#92400E"
            ),
            (
                "CSW ISO",
                "Catalogue Service for the Web (ISO 19115 Output)",
                f"{server_url}/catalogue/csw?request=GetRecordById&service=CSW&version=2.0.2&id={uuid_str}&outputschema=http%3A%2F%2Fwww.isotc211.org%2F2005%2Fgmd&elementsetname=full",
                "#F5F3FF", "#5B21B6"
            ),
        ]

        for p_badge, p_desc, p_url, bg_p, fg_p in endpoints:
            ep_card = QFrame()
            ep_card.setStyleSheet("""
                QFrame {
                    background-color: palette(window);
                    border: 1px solid palette(midlight);
                    border-radius: 6px;
                    padding: 8px 12px;
                }
            """)
            ep_layout = QHBoxLayout(ep_card)
            ep_layout.setContentsMargins(6, 6, 6, 6)
            ep_layout.setSpacing(10)

            # Badge protokol
            badge_lbl = QLabel(p_badge)
            badge_lbl.setStyleSheet(f"""
                font-size: 7.5pt;
                font-weight: 700;
                background-color: {bg_p};
                color: {fg_p};
                border-radius: 4px;
                padding: 4px 8px;
            """)
            badge_lbl.setFixedWidth(70)
            badge_lbl.setAlignment(Qt.AlignCenter)
            ep_layout.addWidget(badge_lbl)

            # Deskripsi
            desc_box = QVBoxLayout()
            desc_box.setSpacing(2)
            lbl_title_ep = QLabel(p_desc)
            lbl_title_ep.setStyleSheet("font-size: 8.5pt; font-weight: 600; color: palette(text);")
            lbl_url_hint = QLabel(p_url[:80] + "..." if len(p_url) > 80 else p_url)
            lbl_url_hint.setStyleSheet("font-size: 7.5pt; color: #64748B; font-family: monospace;")
            desc_box.addWidget(lbl_title_ep)
            desc_box.addWidget(lbl_url_hint)
            ep_layout.addLayout(desc_box, stretch=1)

            # Action Buttons: Salin URL & Buka URL
            btn_copy_ep = QPushButton("Salin URL")
            btn_copy_ep.setProperty("class", "actionBtn")
            btn_copy_ep.setIcon(QgsApplication.getThemeIcon("mActionEditCopy.svg"))
            btn_copy_ep.setCursor(Qt.PointingHandCursor)
            btn_copy_ep.clicked.connect(lambda checked=False, u=p_url, b=p_badge: self._copy_text_to_clipboard(u, f"URL {b}"))
            ep_layout.addWidget(btn_copy_ep)

            btn_open_ep = QPushButton("Buka")
            btn_open_ep.setProperty("class", "actionBtn")
            btn_open_ep.setIcon(QgsApplication.getThemeIcon("mIconConnect.svg"))
            btn_open_ep.setCursor(Qt.PointingHandCursor)
            btn_open_ep.clicked.connect(lambda checked=False, u=p_url: QDesktopServices.openUrl(QUrl(u)))
            ep_layout.addWidget(btn_open_ep)

            d_layout.addWidget(ep_card)

        self.preview_layout.addWidget(card_dist)

    # ==========================================================
    # Tab 2: XML Metadata (ISO 19115 CSW)
    # ==========================================================

    def _create_xml_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Bar Info & Action
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        lbl_info = QLabel("Struktur XML Metadata Standar ISO 19115 / ISO 19139 (Output CSW pycsw):")
        lbl_info.setStyleSheet("font-weight: 600; font-size: 8.5pt; color: #64748B;")
        top_bar.addWidget(lbl_info, stretch=1)

        self.btn_copy_xml = QPushButton("Salin XML")
        self.btn_copy_xml.setProperty("class", "actionBtn")
        self.btn_copy_xml.setIcon(QgsApplication.getThemeIcon("mActionEditCopy.svg"))
        self.btn_copy_xml.clicked.connect(self._copy_xml_to_clipboard)
        top_bar.addWidget(self.btn_copy_xml)

        self.btn_save_xml = QPushButton("Simpan File XML...")
        self.btn_save_xml.setProperty("class", "actionBtn")
        self.btn_save_xml.setIcon(QgsApplication.getThemeIcon("mActionFileSave.svg"))
        self.btn_save_xml.clicked.connect(self._save_xml_to_file)
        top_bar.addWidget(self.btn_save_xml)

        layout.addLayout(top_bar)

        # Editor View Monospace
        self.txt_xml_viewer = QPlainTextEdit()
        self.txt_xml_viewer.setReadOnly(True)
        self.txt_xml_viewer.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.txt_xml_viewer.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'DejaVu Sans Mono', 'Consolas', 'Courier New', monospace;
                font-size: 8.5pt;
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(midlight);
                border-radius: 6px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.txt_xml_viewer, stretch=1)

        return widget

    # ==========================================================
    # Tab 3: Edit Metadata (Editor)
    # ==========================================================

    def _create_edit_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        form_layout = QFormLayout(widget)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)

        # Judul
        self.edit_title = QLineEdit()
        form_layout.addRow("Judul (Title) *", self.edit_title)

        # Abstrak
        self.edit_abstract = QTextEdit()
        self.edit_abstract.setMaximumHeight(85)
        form_layout.addRow("Abstrak (Abstract) *", self.edit_abstract)

        # Tujuan
        self.edit_purpose = QTextEdit()
        self.edit_purpose.setMaximumHeight(65)
        form_layout.addRow("Tujuan (Purpose)", self.edit_purpose)

        # Kategori
        self.edit_category = QComboBox()
        for cat in metadata_service.get_categories():
            self.edit_category.addItem(cat.get("gn_description") or cat.get("identifier"), cat.get("identifier"))
        form_layout.addRow("Kategori Tema", self.edit_category)

        # Kata Kunci
        self.edit_keywords = QLineEdit()
        self.edit_keywords.setPlaceholderText("Pisahkan dengan koma, contoh: Kota Yogyakarta, Jalan, GSB")
        form_layout.addRow("Kata Kunci (Keywords)", self.edit_keywords)

        # Lisensi
        self.edit_license = QComboBox()
        for lic in metadata_service.get_licenses():
            self.edit_license.addItem(lic.get("name"), lic.get("identifier"))
        form_layout.addRow("Lisensi (License)", self.edit_license)

        # Pemeliharaan
        self.edit_maintenance = QComboBox()
        for code, label in metadata_service.get_maintenance_frequencies():
            self.edit_maintenance.addItem(label, code)
        form_layout.addRow("Frekuensi Pemeliharaan", self.edit_maintenance)

        # Informasi Tambahan
        self.edit_supplemental = QTextEdit()
        self.edit_supplemental.setMaximumHeight(65)
        form_layout.addRow("Informasi Tambahan", self.edit_supplemental)

        # Kualitas Data Lineage
        self.edit_lineage = QTextEdit()
        self.edit_lineage.setMaximumHeight(85)
        form_layout.addRow("Pernyataan Kualitas Data", self.edit_lineage)

        # Tombol Simpan
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_save_changes = QPushButton("SIMPAN PERUBAHAN KE GEONODE")
        self.btn_save_changes.setProperty("class", "primaryBtn")
        self.btn_save_changes.setIcon(QgsApplication.getThemeIcon("mActionFileSave.svg"))
        self.btn_save_changes.clicked.connect(self._on_save_metadata_clicked)
        btn_box.addWidget(self.btn_save_changes)

        form_layout.addRow("", btn_box)

        scroll.setWidget(widget)
        return scroll

    # ==========================================================
    # Footer
    # ==========================================================

    def _build_footer(self, parent_layout: QVBoxLayout):
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.lbl_status = QLabel("Memuat...")
        self.lbl_status.setStyleSheet("color: #64748B; font-size: 8pt;")
        footer.addWidget(self.lbl_status, stretch=1)

        btn_close = QPushButton("Tutup")
        btn_close.setProperty("class", "actionBtn")
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)

        parent_layout.addLayout(footer)

    # ==========================================================
    # Data Loading & Handling
    # ==========================================================

    def _load_metadata(self):
        """Memuat metadata lengkap dari server GeoNode dan menyusun UI."""
        pk = self.layer.pk or self.layer.id
        uuid_str = self.layer.uuid

        # 1. Ambil detail metadata via REST API
        meta_res = metadata_service.get_metadata(pk)
        if meta_res.success and isinstance(meta_res.data, dict):
            self._meta_data = meta_res.data
        else:
            # Fallback ke atribut Layer jika API gagal
            self._meta_data = {
                "pk": pk,
                "uuid": uuid_str,
                "title": self.layer.title or self.layer.name,
                "alternate": self.layer.alternate or self.layer.layer_name,
                "abstract": self.layer.abstract or "",
                "srid": self.layer.srid or "EPSG:4326",
                "extent": self.layer.extent or [110.34563, -7.83566, 110.40433, -7.77119],
                "owner": {"username": self.layer.owner_username or "admin"},
            }

        # 2. Ambil XML CSW ISO 19115
        self._raw_csw_xml = metadata_service.get_csw_xml(
            uuid_str=uuid_str,
            pk=pk,
            layer=self.layer,
            meta_dict=self._meta_data,
        )

        # 3. Populate UI
        self._populate_preview_ui(self._meta_data)
        self.txt_xml_viewer.setPlainText(self._raw_csw_xml)
        self._populate_edit_form(self._meta_data)

        self.lbl_status.setText(f"Metadata berhasil dimuat ({len(self._raw_csw_xml):,} bytes XML)")

    def _populate_edit_form(self, meta: Dict[str, Any]):
        """Mengisi form di tab Edit."""
        self.edit_title.setText(meta.get("title") or getattr(self.layer, "title", ""))
        self.edit_abstract.setPlainText(meta.get("abstract") or getattr(self.layer, "abstract", ""))
        self.edit_purpose.setPlainText(meta.get("purpose") or "")

        # Category
        cat_val = meta.get("category")
        cat_id = cat_val.get("identifier") if isinstance(cat_val, dict) else str(cat_val or "")
        idx = self.edit_category.findData(cat_id)
        if idx >= 0:
            self.edit_category.setCurrentIndex(idx)

        # Keywords
        kw_list = []
        raw_kw = meta.get("keywords") or meta.get("raw_keywords") or []
        if isinstance(raw_kw, list):
            for k in raw_kw:
                kw_list.append(k.get("name", str(k)) if isinstance(k, dict) else str(k))
        elif isinstance(raw_kw, str):
            kw_list = [w.strip() for w in raw_kw.split(",") if w.strip()]
        self.edit_keywords.setText(", ".join(kw_list))

        # License
        lic_val = meta.get("license")
        lic_id = lic_val.get("identifier") if isinstance(lic_val, dict) else str(lic_val or "")
        idx_l = self.edit_license.findData(lic_id)
        if idx_l >= 0:
            self.edit_license.setCurrentIndex(idx_l)

        # Maintenance
        maint_val = meta.get("maintenance_frequency") or "irregular"
        idx_m = self.edit_maintenance.findData(maint_val)
        if idx_m >= 0:
            self.edit_maintenance.setCurrentIndex(idx_m)

        self.edit_supplemental.setPlainText(meta.get("supplemental_information") or "")
        self.edit_lineage.setPlainText(meta.get("data_quality_statement") or "")

    # ==========================================================
    # Actions
    # ==========================================================

    def _copy_xml_to_clipboard(self):
        """Salin XML ke clipboard."""
        if self._raw_csw_xml:
            QApplication.clipboard().setText(self._raw_csw_xml)
            QMessageBox.information(self, "Tersalin", "XML Metadata ISO 19115 berhasil disalin ke clipboard.")

    def _save_xml_to_file(self):
        """Simpan XML ke file lokal."""
        if not self._raw_csw_xml:
            return

        filename = f"metadata_{self.layer.name or 'dataset'}.xml"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan XML Metadata",
            filename,
            "XML Files (*.xml);;All Files (*)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._raw_csw_xml)
                QMessageBox.information(self, "Berhasil", f"File XML berhasil disimpan ke:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "Gagal Menyimpan", f"Gagal menulis file XML:\n{e}")

    def _open_web_preview(self):
        """Membuka halaman web /metadata/{pk} di browser default."""
        server_url = metadata_service.api.server_url.rstrip("/")
        pk = self.layer.pk or self.layer.id
        if pk:
            web_url = f"{server_url}/metadata/{pk}"
            QDesktopServices.openUrl(QUrl(web_url))

    def _on_save_metadata_clicked(self):
        """Menyimpan pembaruan metadata ke GeoNode melalui REST API."""
        new_title = self.edit_title.text().strip()
        new_abstract = self.edit_abstract.toPlainText().strip()

        if not new_title:
            QMessageBox.warning(self, "Peringatan", "Judul dataset wajib diisi.")
            return

        if not new_abstract:
            QMessageBox.warning(self, "Peringatan", "Abstrak dataset wajib diisi.")
            return

        payload = {
            "title": new_title,
            "abstract": new_abstract,
            "purpose": self.edit_purpose.toPlainText().strip(),
            "category": self.edit_category.currentData(),
            "keywords": self.edit_keywords.text().strip(),
            "license": self.edit_license.currentData(),
            "maintenance_frequency": self.edit_maintenance.currentData(),
            "supplemental_information": self.edit_supplemental.toPlainText().strip(),
            "data_quality_statement": self.edit_lineage.toPlainText().strip(),
        }

        pk = self.layer.pk or self.layer.id
        if not pk:
            QMessageBox.warning(self, "Peringatan", "ID dataset tidak valid.")
            return

        self.lbl_status.setText("Menyimpan perubahan metadata ke server...")
        QApplication.processEvents()

        res = metadata_service.update_metadata(pk, payload)
        if not res.success:
            QMessageBox.warning(self, "Gagal Menyimpan", f"Gagal memperbarui metadata di server:\n{res.message}")
            self.lbl_status.setText("Gagal menyimpan metadata.")
            return

        # Update model layer lokal
        self.layer.title = new_title
        self.layer.abstract = new_abstract
        self.lbl_header_title.setText(new_title)

        QMessageBox.information(
            self,
            "Berhasil",
            f"Metadata untuk dataset \"{new_title}\" berhasil diperbarui di GeoNode!"
        )

        # Refresh preview & xml
        self._load_metadata()
        self.tabs.setCurrentIndex(0)

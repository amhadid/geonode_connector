"""
server_controller.py

Controller untuk menguji koneksi dan menyimpan konfigurasi server GeoNode.
"""

from __future__ import annotations

import time
import ssl
import json
import urllib.request
import urllib.error
from typing import Optional

from qgis.PyQt.QtCore import QSettings
from ...utils.logger import get_logger
from ...models.session import session

logger = get_logger(__name__)


class ServerController:
    """
    Controller konfigurasi server & health-check koneksi.
    """

    def __init__(self, widget, login_widget=None):
        self.widget = widget
        self.login_widget = login_widget
        self.initialize()

    def initialize(self):
        self.widget.btn_save.clicked.connect(self.save)
        self.widget.btn_test.clicked.connect(self.test_connection)
        self.load_server()

    def load_server(self):
        """Memuat URL server yang tersimpan dari session atau QSettings."""
        settings = QSettings()
        saved_url = settings.value("GeoNodeConnector/server_url", session.server_url or "http://localhost")
        saved_timeout = settings.value("GeoNodeConnector/timeout", 30, type=int)
        saved_ssl = settings.value("GeoNodeConnector/verify_ssl", False, type=bool)

        if saved_url:
            self.widget.url.setText(str(saved_url))
        self.widget.timeout.setValue(saved_timeout)
        self.widget.ssl.setChecked(saved_ssl)

    def save(self):
        """Menyimpan konfigurasi server ke session dan QSettings."""
        raw_url = self.widget.url.text().strip()
        if not raw_url:
            self.widget.show_error("URL Tidak Boleh Kosong", "Silakan masukkan URL GeoNode yang valid.")
            return

        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = f"http://{raw_url}"
            self.widget.url.setText(raw_url)

        timeout = self.widget.timeout.value()
        verify_ssl = self.widget.ssl.isChecked()

        session.server_url = raw_url

        settings = QSettings()
        settings.setValue("GeoNodeConnector/server_url", raw_url)
        settings.setValue("GeoNodeConnector/timeout", timeout)
        settings.setValue("GeoNodeConnector/verify_ssl", verify_ssl)

        # Sync to login form if available
        if self.login_widget and hasattr(self.login_widget, "server"):
            self.login_widget.server.setText(raw_url)

        logger.info(f"Server configuration saved: {raw_url} (timeout={timeout}s, ssl={verify_ssl})")
        self.widget.show_success(
            "Konfigurasi Berhasil Disimpan",
            f"URL server aktif diatur ke: {raw_url}. Form login telah diselaraskan."
        )

    def test_connection(self):
        """Melakukan tes ping/request HTTP ke endpoint GeoNode."""
        raw_url = self.widget.url.text().strip()
        if not raw_url:
            self.widget.show_error("URL Kosong", "Masukkan URL GeoNode terlebih dahulu sebelum melakukan pengujian.")
            return

        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = f"http://{raw_url}"
            self.widget.url.setText(raw_url)

        timeout = self.widget.timeout.value()
        verify_ssl = self.widget.ssl.isChecked()

        self.widget.set_loading(True, f"Menghubungi {raw_url}...")

        try:
            start_time = time.time()

            ctx = ssl.create_default_context()
            if not verify_ssl:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            # 1. Cek endpoint API v2
            api_v2_url = f"{raw_url.rstrip('/')}/api/v2/"
            req = urllib.request.Request(
                api_v2_url,
                headers={"User-Agent": "QGIS-GeoNode-Connector", "Accept": "application/json"}
            )

            status_code = 0
            api_info = ""

            try:
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    status_code = resp.status
                    latency_ms = int((time.time() - start_time) * 1000)
                    body = resp.read().decode("utf-8", errors="ignore")
                    try:
                        data = json.loads(body)
                        endpoints = list(data.keys()) if isinstance(data, dict) else []
                        api_info = f"Endpoints terdeteksi: {', '.join(endpoints[:5])}..."
                    except Exception:
                        api_info = "GeoNode web server aktif."

            except urllib.error.HTTPError as e:
                # Bila /api/v2/ mengembalikan 401/403/404, coba root endpoint
                status_code = e.code
                latency_ms = int((time.time() - start_time) * 1000)
                api_info = f"Respon HTTP status: {status_code}"

            except urllib.error.URLError as e:
                # Coba root URL jika subpath belum terpasang
                root_req = urllib.request.Request(raw_url, headers={"User-Agent": "QGIS-GeoNode-Connector"})
                try:
                    with urllib.request.urlopen(root_req, timeout=timeout, context=ctx) as resp:
                        status_code = resp.status
                        latency_ms = int((time.time() - start_time) * 1000)
                        api_info = "GeoNode root web portal terjangkau."
                except Exception:
                    raise e

            self.widget.set_loading(False)
            self.widget.show_success(
                f"Koneksi Berhasil! (HTTP {status_code})",
                f"Terhubung ke {raw_url} dalam {latency_ms} ms. {api_info}"
            )
            logger.info(f"Test connection success: {raw_url} in {latency_ms}ms")

        except Exception as e:
            self.widget.set_loading(False)
            err_msg = str(e)
            logger.error(f"Test connection failed: {err_msg}")
            self.widget.show_error(
                "Koneksi Gagal",
                f"Tidak dapat terhubung ke {raw_url}.\nDetail Kesalahan: {err_msg}"
            )
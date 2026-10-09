"""
auth_manager.py

Modul integrasi keamanan QGIS Authentication Manager (QgsAuthManager).
Mengamankan kredensial sensitif pengguna dan instance GeoNode menggunakan
master password QGIS, menggantikan penyimpanan teks biasa pada file .env.
"""

from __future__ import annotations

from typing import Optional, Tuple
from qgis.core import (
    QgsApplication,
    QgsAuthMethodConfig,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)

AUTH_CONFIG_PREFIX = "geonode_connector_"


class AuthManagerService:
    """
    Layanan manajemen kredensial menggunakan QgsAuthManager bawaan QGIS.
    """

    @staticmethod
    def is_auth_manager_ready() -> bool:
        """
        Memeriksa apakah QgsAuthManager telah diinisialisasi dan master password aktif.
        """
        auth_mgr = QgsApplication.authManager()
        if not auth_mgr:
            return False
        return auth_mgr.masterPasswordIsSet()

    @staticmethod
    def get_or_create_basic_auth_config(
        config_name: str,
        username: str,
        password: str,
        auth_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Menyimpan kredensial username/password ke QgsAuthManager dengan enkripsi master password.
        Mengembalikan authcfg ID 7-karakter yang dapat disematkan ke QgsDataSourceUri atau NetworkClient.
        """
        auth_mgr = QgsApplication.authManager()
        if not auth_mgr:
            logger.warning("QgsAuthManager tidak tersedia.")
            return None

        # Jika auth_id sudah ada, verifikasi apakah konfigurasi valid
        if auth_id and auth_mgr.configIds():
            if auth_id in auth_mgr.configIds():
                config = QgsAuthMethodConfig()
                if auth_mgr.loadAuthenticationConfig(auth_id, config, True):
                    # Update config jika perlu
                    config.setConfig("username", username)
                    config.setConfig("password", password)
                    if auth_mgr.updateAuthenticationConfig(config):
                        logger.info("Konfigurasi auth '%s' berhasil diperbarui.", auth_id)
                        return auth_id

        # Buat konfigurasi baru
        config = QgsAuthMethodConfig("Basic", config_name)
        config.setConfig("username", username)
        config.setConfig("password", password)
        if auth_id:
            config.setId(auth_id)

        if auth_mgr.storeAuthenticationConfig(config):
            stored_id = config.id()
            logger.info("Berhasil menyimpan kredensial ke QgsAuthManager dengan authcfg: %s", stored_id)
            return stored_id

        logger.error("Gagal menyimpan kredensial ke QgsAuthManager.")
        return None

    @staticmethod
    def get_credentials(auth_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Mengambil kredensial (username, password) secara terenkripsi dari QgsAuthManager.
        """
        auth_mgr = QgsApplication.authManager()
        if not auth_mgr or not auth_id:
            return None, None

        config = QgsAuthMethodConfig()
        if auth_mgr.loadAuthenticationConfig(auth_id, config, True):
            username = config.config("username")
            password = config.config("password")
            return username, password

        return None, None

    @staticmethod
    def remove_auth_config(auth_id: str) -> bool:
        """
        Menghapus konfigurasi otentikasi dari QgsAuthManager.
        """
        auth_mgr = QgsApplication.authManager()
        if not auth_mgr or not auth_id:
            return False
        return auth_mgr.removeAuthenticationConfig(auth_id)

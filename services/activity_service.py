"""
activity_service.py

Service untuk mencatat dan mengelola log aktivitas pengguna di GeoNode Connector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from qgis.PyQt.QtCore import QObject, pyqtSignal

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ActivityItem:
    """
    Representasi satu entri log aktivitas.
    """
    id: str
    category: str  # login, import, edit, validate, sync, metadata
    timestamp: datetime
    username: str
    description: str

    @property
    def formatted_time(self) -> str:
        return self.timestamp.strftime("%d/%m/%Y %H:%M")


class ActivityService(QObject):
    """
    Service singleton untuk riwayat log aktivitas.
    """
    _instance: Optional["ActivityService"] = None
    activity_added = pyqtSignal(object)
    activities_cleared = pyqtSignal()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            super(ActivityService, cls._instance).__init__()
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        super().__init__()
        self._activities: List[ActivityItem] = []
        self._seed_default_activities()
        self._initialized = True

    def _seed_default_activities(self):
        """
        Menyediakan riwayat aktivitas awal sesuai mockup jika belum ada.
        """
        now = datetime.now()
        initial_logs = [
            ("login", "admin_demo", "Login berhasil"),
            ("import", "admin_demo", 'Import layer "Jalan"'),
            ("edit", "admin_demo", 'Edit 40 feature pada layer "Jalan"'),
            ("validate", "admin_demo", "Validasi berhasil"),
            ("sync", "admin_demo", "Sinkronisasi berhasil (40 perubahan)"),
            ("metadata", "admin_demo", "Metadata diperbarui"),
        ]
        for i, (cat, user, desc) in enumerate(initial_logs):
            item = ActivityItem(
                id=f"act_{i+1}",
                category=cat,
                timestamp=now,
                username=user,
                description=desc,
            )
            self._activities.append(item)

    def log(self, category: str, username: str, description: str) -> ActivityItem:
        """
        Mencatat aktivitas baru.
        """
        item = ActivityItem(
            id=f"act_{len(self._activities) + 1}",
            category=category,
            timestamp=datetime.now(),
            username=username or "admin_demo",
            description=description,
        )
        self._activities.insert(0, item)
        logger.info("Activity logged: [%s] %s - %s", category, username, description)
        self.activity_added.emit(item)
        return item

    def get_activities(self) -> List[ActivityItem]:
        """
        Mengambil semua riwayat aktivitas.
        """
        return list(self._activities)

    def clear(self) -> None:
        """
        Membersihkan log aktivitas.
        """
        self._activities.clear()
        self.activities_cleared.emit()
        logger.info("Activity log cleared.")


activity_service = ActivityService()

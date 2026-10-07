"""
service_result.py

Model standar hasil eksekusi Service Layer.

Digunakan oleh seluruh service pada GeoNode Connector
untuk mengembalikan hasil operasi secara konsisten.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceResult:
    """
    Standar hasil eksekusi sebuah service.

    Attributes
    ----------
    success : bool
        Status keberhasilan operasi.

    message : str
        Pesan yang dapat ditampilkan ke UI.

    data : Any
        Data hasil operasi.

    errors : dict
        Detail error apabila ada.

    status_code : int | None
        Status HTTP apabila berasal dari REST API.
    """

    success: bool

    message: str = ""

    data: Any = None

    errors: dict = field(default_factory=dict)

    status_code: int | None = None

    @classmethod
    def ok(
        cls,
        message: str = "",
        data: Any = None,
        status_code: int | None = None,
    ) -> "ServiceResult":
        """
        Membuat ServiceResult berhasil.
        """

        return cls(
            success=True,
            message=message,
            data=data,
            status_code=status_code,
        )

    @classmethod
    def fail(
        cls,
        message: str,
        *,
        errors: dict | None = None,
        status_code: int | None = None,
        data: Any = None,
    ) -> "ServiceResult":
        """
        Membuat ServiceResult gagal.
        """

        return cls(
            success=False,
            message=message,
            errors=errors or {},
            status_code=status_code,
            data=data,
        )
"""
upload.py

REST API client untuk Upload Dataset GeoNode (Sprint 6).
Berinteraksi dengan endpoint GeoNode Importer:
- POST /uploads/upload (multipart/form-data)
- GET /api/v2/executionrequest/{execution_id}
"""

from __future__ import annotations

import os
import mimetypes
from typing import Any, Dict, Optional

from ..models.session import session
from ..utils.network import NetworkClient, network_client
from ..utils.config import DEFAULT_SERVER
from ..utils.logger import get_logger

logger = get_logger(__name__)


class UploadAPI:
    """
    Klien REST API untuk Upload Dataset ke GeoNode.
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        network: Optional[NetworkClient] = None,
    ) -> None:
        self.server_url = (server_url or DEFAULT_SERVER).rstrip("/")
        self.network = network or network_client
        self._session = session

    def set_server(self, server_url: str) -> None:
        if server_url:
            self.server_url = server_url.rstrip("/")

    def upload_dataset(
        self,
        file_map: Dict[str, str],
        action: str = "upload",
        resource_pk: Optional[int | str] = None,
    ) -> Dict[str, Any]:
        """
        Mengunggah file dataset ke endpoint GeoNode Importer (/uploads/upload).

        Parameters
        ----------
        file_map : Dict[str, str]
            Pemetaan nama field ke path file lokal.
            Contoh GeoPackage: {'base_file': '/path/to/data.gpkg'}
            Contoh Shapefile: {'base_file': '...shp', 'dbf_file': '...dbf', 'shx_file': '...shx', 'prj_file': '...prj'}
        action : str
            'upload' untuk dataset baru, atau 'replace' / 'upsert' untuk pembaruan.
        resource_pk : int | str, optional
            PK dataset target jika action adalah 'replace'.

        Returns
        -------
        Dict[str, Any]
            Hasil respons JSON dari server (misal {'execution_id': '...'}).
        """
        url = f"{self.server_url}/uploads/upload"
        boundary = "----QgisGeoNodeConnectorBoundary7MA4YWxkTrZu0gW"
        
        body_parts = []

        # Tambahkan form field action
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(b'Content-Disposition: form-data; name="action"\r\n\r\n')
        body_parts.append(f"{action}\r\n".encode())

        # Tambahkan resource_pk jika ada
        if resource_pk is not None:
            body_parts.append(f"--{boundary}\r\n".encode())
            body_parts.append(b'Content-Disposition: form-data; name="resource_pk"\r\n\r\n')
            body_parts.append(f"{resource_pk}\r\n".encode())

        # Tambahkan file-file
        for field_name, file_path in file_map.items():
            if not os.path.isfile(file_path):
                continue
            filename = os.path.basename(file_path)
            content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            
            body_parts.append(f"--{boundary}\r\n".encode())
            body_parts.append(
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
            )
            body_parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
            with open(file_path, "rb") as f:
                body_parts.append(f.read())
            body_parts.append(b"\r\n")

        body_parts.append(f"--{boundary}--\r\n".encode())
        payload = b"".join(body_parts)

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        if self._session.access_token:
            headers["Authorization"] = f"Bearer {self._session.access_token}"

        logger.info(f"Mengirim upload dataset ke {url} (action={action}, files={list(file_map.keys())})")
        resp = self.network.post(url, data=payload, headers=headers)

        if resp.get("success") or resp.get("status_code") in (200, 201):
            data = resp.get("data")
            return data if isinstance(data, dict) else {"data": data}

        logger.error(f"Upload gagal: HTTP {resp.get('status_code')} - {resp.get('message')}")
        err_data = resp.get("data")
        if isinstance(err_data, dict):
            return err_data
        return {"error": resp.get("message"), "status_code": resp.get("status_code")}

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Memeriksa progres dan status eksekusi upload di /api/v2/executionrequest/{execution_id}.
        """
        url = f"{self.server_url}/api/v2/executionrequest/{execution_id}"
        resp = self.network.get(url)
        if resp.get("success") or resp.get("status_code") == 200:
            data = resp.get("data")
            if isinstance(data, dict):
                return data.get("request", data)
        return None

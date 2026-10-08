"""
layer.py

Model Layer GeoNode.

Class ini hanya merepresentasikan satu dataset/layer GeoNode.
Tidak memiliki tanggung jawab melakukan komunikasi HTTP.

Digunakan oleh:

- DatasetAPI
- LayerService
- Dataset Browser
- Import Layer
- Metadata Editor
- Synchronization
"""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Layer:
    """
    Representasi Dataset GeoNode.
    """

    # ==========================================================
    # Identity
    # ==========================================================

    id: int | None = None
    pk: str = ""
    uuid: str = ""

    # ==========================================================
    # Basic Information
    # ==========================================================

    name: str = ""
    title: str = ""
    abstract: str = ""

    # ==========================================================
    # Ownership
    # ==========================================================

    owner_id: int | None = None
    owner_username: str = ""

    # ==========================================================
    # GeoServer
    # ==========================================================

    workspace: str = ""
    store: str = ""
    alternate: str = ""

    # ==========================================================
    # Resource
    # ==========================================================

    resource_type: str = ""
    subtype: str = ""

    state: str = ""

    advertised: bool = False
    is_published: bool = False
    is_approved: bool = False

    # ==========================================================
    # Spatial
    # ==========================================================

    srid: str = ""
    crs_string: str = ""
    bbox_x0: float | None = None
    bbox_x1: float | None = None
    bbox_y0: float | None = None
    bbox_y1: float | None = None
    extent: list[float] = field(default_factory=list)
    extent_srid: str = ""

    # ==========================================================
    # Style
    # ==========================================================

    default_style: str = ""

    # ==========================================================
    # Thumbnail
    # ==========================================================

    thumbnail_url: str = ""

    # ==========================================================
    # Metadata
    # ==========================================================

    created: datetime | None = None
    modified: datetime | None = None

    # ==========================================================
    # API
    # ==========================================================

    detail_url: str = ""
    api_url: str = ""

    # ==========================================================
    # Download
    # ==========================================================

    download_urls: list[dict[str, Any]] = field(default_factory=list)

    # ==========================================================
    # OGC Links
    # ==========================================================

    links: list[dict[str, Any]] = field(default_factory=list)

    # ==========================================================
    # Services
    # ==========================================================
    wms_url: str = ""
    wfs_url: str = ""
    geojson_url: str = ""
    shapefile_url: str = ""
    download_url: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Layer":
        """
        Membuat object Layer dari dictionary.

        Dictionary ini diasumsikan sudah dipetakan
        oleh DatasetAPI.
        """

        return cls(
            id=data.get("id"),
            pk=data.get("pk", ""),
            uuid=data.get("uuid", ""),

            name=data.get("name", ""),
            title=data.get("title", ""),
            abstract=data.get("abstract", ""),

            owner_id=data.get("owner_id"),
            owner_username=data.get("owner_username", ""),

            workspace=data.get("workspace", ""),
            store=data.get("store", ""),
            alternate=data.get("alternate", ""),

            resource_type=data.get("resource_type", ""),
            subtype=data.get("subtype", ""),

            state=data.get("state", ""),

            advertised=data.get("advertised", False),
            is_published=data.get("is_published", False),
            is_approved=data.get("is_approved", False),

            srid=data.get("srid", ""),

            extent=data.get("extent", []),
            extent_srid=data.get("extent_srid", ""),

            default_style=data.get("default_style", ""),

            thumbnail_url=data.get("thumbnail_url", ""),

            created=cls._parse_datetime(
                data.get("created")
            ),

            modified=cls._parse_datetime(
                data.get("modified")
            ),

            detail_url=data.get("detail_url", ""),
            api_url=data.get("api_url", ""),

            download_urls=data.get("download_urls", []),

            links=data.get("links", []),
            wms_url=data.get("wms_url", ""),
            wfs_url=data.get("wfs_url", ""),
            geojson_url=data.get("geojson_url", ""),
            shapefile_url=data.get("shapefile_url", ""),
            download_url=data.get("download_url", ""),
        )

    # ==========================================================
    # Serialize
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Mengubah Layer menjadi dictionary.
        """

        return asdict(self)

    # ==========================================================
    # Validation
    # ==========================================================

    def is_valid(self) -> bool:
        """
        Validasi sederhana.
        """

        return bool(
            self.name
            and self.workspace
            and self.subtype
        )

    # ==========================================================
    # Computed Properties
    # ==========================================================

    @property
    def display_name(self) -> str:
        """
        Nama yang ditampilkan di UI.
        """

        return self.title or self.name

    @property
    def layer_name(self) -> str:
        """
        workspace:layer
        """

        if self.alternate:
            return self.alternate

        if self.workspace:
            return f"{self.workspace}:{self.name}"

        return self.name

    @property
    def qgis_layer_name(self) -> str:
        """
        Alias for layer_name used by QGIS importers.
        """
        return self.layer_name

    @property
    def is_vector(self) -> bool:
        return (self.subtype or "").lower() == "vector"

    @property
    def is_raster(self) -> bool:
        return (self.subtype or "").lower() == "raster"

    @property
    def has_thumbnail(self) -> bool:
        return bool(self.thumbnail_url)

    @property
    def has_download(self) -> bool:
        return len(self.download_urls) > 0

    @property
    def has_links(self) -> bool:
        return len(self.links) > 0

    @property
    def has_wms(self) -> bool:
        return bool(self.wms_url)

    @property
    def has_wfs(self) -> bool:
        return bool(self.wfs_url)

    @property
    def has_geojson(self) -> bool:
        return bool(self.geojson_url)

    @property
    def has_shapefile(self) -> bool:
        return bool(self.shapefile_url)

    def get_geojson_url(self, server_url: str = "") -> str:
        """
        Mengembalikan URL endpoint GeoJSON langsung dari GeoServer.
        """
        if self.geojson_url:
            return self.geojson_url

        target_server = server_url or "http://localhost"
        layer_name = self.alternate or self.layer_name
        srid = self.srid or "EPSG:4326"
        return (
            f"{target_server.rstrip('/')}/geoserver/ows?"
            f"service=WFS&version=1.0.0&request=GetFeature&"
            f"typename={layer_name}&outputFormat=json&srs={srid}&srsName={srid}"
        )

    def get_shapefile_url(self, server_url: str = "") -> str:
        """
        Mengembalikan URL download Zipped Shapefile langsung dari GeoServer.
        """
        if self.shapefile_url:
            return self.shapefile_url

        target_server = server_url or "http://localhost"
        layer_name = self.alternate or self.layer_name
        srid = self.srid or "EPSG:4326"
        return (
            f"{target_server.rstrip('/')}/geoserver/ows?"
            f"service=WFS&version=1.0.0&request=GetFeature&"
            f"typename={layer_name}&outputFormat=SHAPE-ZIP&srs={srid}&format_options=charset:UTF-8"
        )

    # ==========================================================
    # Helper
    # ==========================================================

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """
        Parsing datetime ISO8601.
        """

        if not value:
            return None

        if isinstance(value, datetime):
            return value

        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except Exception:
            return None

    def __str__(self) -> str:
        return self.display_name

    def __repr__(self) -> str:
        return (
            f"Layer("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"subtype='{self.subtype}')"
        )
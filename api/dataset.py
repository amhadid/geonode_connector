"""
dataset.py

REST API untuk Dataset GeoNode.

Class ini bertanggung jawab terhadap seluruh komunikasi
dengan endpoint Dataset GeoNode.

Responsibilities
----------------
- Request Dataset
- Request Detail Dataset
- Search Dataset
- Pagination
- Mapping JSON -> Layer
- Error Handling

Class ini TIDAK memiliki business logic.
Business logic berada pada LayerService.
"""

from __future__ import annotations

from typing import Any

from ..models.layer import Layer

from ..utils.network import NetworkClient

from ..utils.config import (
    API_BASE,
    DATASET_ENDPOINT,
    DEFAULT_SERVER,
    DEFAULT_TIMEOUT,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatasetAPI:
    """
    REST API client untuk Dataset GeoNode.
    """

    def __init__(
        self,
        server_url: str | None = None,
        network: NetworkClient | None = None,
    ):
        """
        Parameters
        ----------
        server_url : str, optional
            URL GeoNode.

        network : NetworkClient, optional
            Shared HTTP Client.
        """

        self.server_url = (
            server_url.rstrip("/")
            if server_url
            else DEFAULT_SERVER.rstrip("/")
        )

        self.network = (
            network
            or NetworkClient()
        )

    # ==========================================================
    # Configuration
    # ==========================================================

    def set_server(
        self,
        server_url: str,
    ) -> None:
        """
        Update GeoNode server URL.
        """

        if not server_url:

            return

        self.server_url = server_url.rstrip("/")

        logger.info(
            "DatasetAPI server updated: %s",
            self.server_url,
        )

    # ==========================================================
    # Internal
    # ==========================================================

    def _build_url(
        self,
        endpoint: str,
    ) -> str:
        """
        Build endpoint URL.
        """

        endpoint = endpoint.lstrip("/")

        return (
            f"{self.server_url}"
            f"{API_BASE}"
            f"/{endpoint}"
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Wrapper seluruh HTTP request.

        Menggunakan NetworkClient yang mengembalikan
        standardized response dictionary.
        """

        url = self._build_url(endpoint)

        logger.debug(
            "%s %s",
            method.upper(),
            url,
        )

        response = self.network.request(
            method=method,
            url=url,
            timeout=DEFAULT_TIMEOUT,
            **kwargs,
        )

        if not response.get("success", False):

            logger.error(
                "HTTP %s : %s",
                response.get("status_code"),
                response.get("message"),
            )

            raise RuntimeError(
                response.get(
                    "message",
                    "Unknown network error.",
                )
            )

        data = response.get("data")

        if data is None:

            logger.warning(
                "Empty response received."
            )

            return {}

        if isinstance(data, dict):

            logger.info(
                "Response keys: %s",
                list(data.keys()),
            )

            return data

        if isinstance(data, list):

            logger.info(
                "Response is list (%d items)",
                len(data),
            )

            return data

        logger.warning(
            "Unexpected response type: %s",
            type(data).__name__,
        )

        return {}

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        return self._request(
            "GET",
            endpoint,
            params=params,
        )

    def _post(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        return self._request(
            "POST",
            endpoint,
            json=json,
        )

    def _put(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        return self._request(
            "PUT",
            endpoint,
            json=json,
        )

    def _delete(
        self,
        endpoint: str,
    ) -> dict[str, Any]:

        return self._request(
            "DELETE",
            endpoint,
        )

    # ==========================================================
    # Mapping
    # ==========================================================

    def _map_layer(
        self,
        item: dict[str, Any],
    ) -> Layer:
        """
        Mapping JSON response GeoNode
        menjadi Layer Model.
        """

        owner = (
            item.get("owner")
            or {}
        )

        extent = self._parse_extent(
            item.get(
                "extent",
                {},
            )
        )

        default_style = (
            item.get("default_style")
            or {}
        )

        mapped = {

            # --------------------------------------------------
            # Identity
            # --------------------------------------------------

            "id": item.get("id"),

            "pk": item.get("pk"),

            "uuid": item.get("uuid"),

            # --------------------------------------------------
            # Basic
            # --------------------------------------------------

            "name": item.get("name"),

            "title": item.get("title"),

            "abstract": item.get("abstract"),

            # --------------------------------------------------
            # Owner
            # --------------------------------------------------

            "owner_id": owner.get("pk"),

            "owner_username": owner.get(
                "username"
            ),

            # --------------------------------------------------
            # GeoServer
            # --------------------------------------------------

            "workspace": item.get(
                "workspace"
            ),

            "store": item.get(
                "store"
            ),

            "alternate": item.get(
                "alternate"
            ),

            # --------------------------------------------------
            # Resource
            # --------------------------------------------------

            "resource_type": item.get(
                "resource_type"
            ),

            "subtype": item.get(
                "subtype"
            ),

            "state": item.get(
                "state"
            ),

            "advertised": item.get(
                "advertised",
                False,
            ),

            "is_published": item.get(
                "is_published",
                False,
            ),

            "is_approved": item.get(
                "is_approved",
                False,
            ),

            # --------------------------------------------------
            # Spatial
            # --------------------------------------------------

            "srid": extent["srid"],

            "extent": extent["coords"],

            "extent_srid": extent["srid"],

            # --------------------------------------------------
            # Style
            # --------------------------------------------------

            "default_style": default_style.get(
                "name",
                "",
            ),

            # --------------------------------------------------
            # Thumbnail
            # --------------------------------------------------

            "thumbnail_url": item.get(
                "thumbnail_url",
                "",
            ),

            # --------------------------------------------------
            # Metadata
            # --------------------------------------------------

            "created": item.get(
                "date"
            ),

            "modified": item.get(
                "date_modified"
            ),

            # --------------------------------------------------
            # API
            # --------------------------------------------------

            "detail_url": item.get(
                "detail_url"
            ),

            "api_url": item.get(
                "link"
            ),

            # --------------------------------------------------
            # Links & Services
            # --------------------------------------------------

            "download_urls": self._parse_downloads(
                item.get(
                    "download_urls",
                    [],
                )
            ),

            "links": self._parse_links(
                item.get(
                    "links",
                    [],
                )
            ),
        }

        # Extract WMS / WFS / GeoJSON / Shapefile / Download URLs from links
        wms_url = ""
        wfs_url = ""
        geojson_url = ""
        shapefile_url = ""
        download_url = ""
        for lk in mapped["links"]:
            name = (lk.get("name") or lk.get("title") or lk.get("type") or "").upper()
            url = lk.get("url") or lk.get("href") or ""
            ext = (lk.get("extension") or "").lower()
            mime = (lk.get("mime") or "").lower()

            if "OGC:WMS" in name or (not wms_url and "WMS" in name and "service=wms" in url.lower()):
                wms_url = wms_url or url
            elif "OGC:WFS" in name or (not wfs_url and "WFS" in name and "geoserver/ows" in url.lower() and "getfeature" not in url.lower()):
                wfs_url = wfs_url or url
            elif ext == "json" or "GEOJSON" in name or "outputformat=json" in url.lower():
                geojson_url = geojson_url or url
            elif ext == "zip" or "SHAPE-ZIP" in mime.upper() or "SHAPEFILE" in name or "outputformat=shape-zip" in url.lower():
                shapefile_url = shapefile_url or url
            elif "DOWNLOAD" in name:
                download_url = download_url or url

        # Fallback to standard GeoServer endpoint if server URL is known
        if not wms_url and self.server_url:
            wms_url = f"{self.server_url}/geoserver/ows"
        if not wfs_url and (item.get("subtype") or "").lower() == "vector" and self.server_url:
            wfs_url = f"{self.server_url}/geoserver/ows"

        # Synthesize GeoJSON and Shapefile endpoints if vector
        alt_name = item.get("alternate") or (f"{item.get('workspace')}:{item.get('name')}" if item.get("workspace") else item.get("name"))
        srid = extent["srid"] or "EPSG:4326"
        if not geojson_url and (item.get("subtype") or "").lower() == "vector" and self.server_url and alt_name:
            geojson_url = (
                f"{self.server_url}/geoserver/ows?"
                f"service=WFS&version=1.0.0&request=GetFeature&"
                f"typename={alt_name}&outputFormat=json&srs={srid}&srsName={srid}"
            )
        if not shapefile_url and (item.get("subtype") or "").lower() == "vector" and self.server_url and alt_name:
            shapefile_url = (
                f"{self.server_url}/geoserver/ows?"
                f"service=WFS&version=1.0.0&request=GetFeature&"
                f"typename={alt_name}&outputFormat=SHAPE-ZIP&srs={srid}&format_options=charset:UTF-8"
            )

        mapped["wms_url"] = wms_url
        mapped["wfs_url"] = wfs_url
        mapped["geojson_url"] = geojson_url
        mapped["shapefile_url"] = shapefile_url
        mapped["download_url"] = download_url

        return Layer.from_dict(
            mapped
        )

    # ==========================================================
    # Parser
    # ==========================================================

    def _parse_extent(
        self,
        extent: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Parsing spatial extent.
        """

        return {

            "coords": extent.get(
                "coords",
                [],
            ),

            "srid": extent.get(
                "srid",
                "",
            ),
        }

    def _parse_downloads(
        self,
        downloads: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Parsing download URLs.
        """

        results = []

        for item in downloads:

            results.append(

                {

                    "name": item.get(
                        "name"
                    ),

                    "format": item.get(
                        "mime"
                    ),

                    "url": item.get(
                        "href"
                    ),
                }

            )

        return results

    def _parse_links(
        self,
        links: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Parsing OGC links.
        """

        results = []

        for item in links:

            results.append(

                {
                    "name": item.get("name", ""),
                    "type": item.get("type", item.get("link_type", "")),
                    "title": item.get("title", ""),
                    "href": item.get("href", item.get("url", "")),
                    "url": item.get("url", item.get("href", "")),
                    "rel": item.get("rel", ""),
                    "extension": item.get("extension", ""),
                    "mime": item.get("mime", ""),
                }

            )

        return results

    def _map_layers(
        self,
        items: list[dict[str, Any]],
    ) -> list[Layer]:
        """
        Mapping list JSON response
        menjadi list Layer.
        
        """

        if not items:

            logger.info(
                "No dataset found."
            )

            return []

        logger.info(
            "Mapping %d dataset(s)...",
            len(items),
        )

        layers: list[Layer] = []

        for index, item in enumerate(items, start=1):

            try:

                layer = self._map_layer(item)

                layers.append(layer)

                logger.debug(
                    "[%d/%d] %s",
                    index,
                    len(items),
                    layer.display_name,
                )

            except Exception as exc:

                logger.exception(
                    "Failed mapping dataset '%s': %s",
                    item.get(
                        "title",
                        item.get(
                            "name",
                            "<unknown>",
                        ),
                    ),
                    exc,
                )

        logger.info(
            "Mapped %d Layer object(s).",
            len(layers),
        )

        return layers

    # ==========================================================
    # Public API
    # ==========================================================

    def check_connection(
        self,
    ) -> bool:
        """
        Check whether Dataset endpoint
        is reachable.
        """

        try:

            self._get(
                DATASET_ENDPOINT,
                params={
                    "page_size": 1,
                },
            )

            return True

        except Exception:

            logger.exception(
                "Unable to connect to Dataset API."
            )

            return False

    def get_datasets(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        owner: str | None = None,
        subtype: str | None = None,
        resource_type: str | None = None,
    ) -> list[Layer]:
        """
        Retrieve dataset list.
        """

        params: dict[str, Any] = {

            "page": page,

            "page_size": page_size,
        }

        if search:

            params["search"] = search

        if owner:

            params["owner"] = owner

        if subtype:

            params["subtype"] = subtype

        if resource_type:

            params["resource_type"] = resource_type

        logger.info(
            "Loading datasets..."
        )

        response = self._get(
            DATASET_ENDPOINT,
            params=params,
        )

        items = (
            response.get("datasets")
            or response.get("resources")
            or response.get("results")
            or response.get("items")
            or []
        )

        logger.info(
            "Loaded %s dataset(s).",
            len(items),
        )

        return self._map_layers(
            items
        )

    def get_dataset(
        self,
        pk: int | str,
    ) -> Layer | None:
        """
        Retrieve dataset detail.
        """

        endpoint = (
            f"{DATASET_ENDPOINT}/{pk}"
        )

        response = self._get(
            endpoint
        )

        if not response:

            return None

        return self._map_layer(
            response
        )

    def get_dataset_detail(self, pk: int | str) -> Layer | None:
        """
        Mengambil detail lengkap dari satu dataset spesifik.
        """
        endpoint = f"{DATASET_ENDPOINT}/{pk}"
        try:
            response = self._get(endpoint)
            if not response:
                return None
            item = response.get("dataset") or response.get("resource") or response
            if isinstance(item, dict):
                return self._map_layer(item)
            return None
        except Exception as exc:
            logger.warning("Failed getting dataset detail for %s: %s", pk, exc)
            return None

    def _to_layer(self, data: dict[str, Any]) -> Layer:
        """
        Mapping dari JSON GeoNode ke objek Layer (delegasi ke _map_layer).
        """
        item = data.get("dataset") or data.get("resource") or data
        if isinstance(item, dict):
            return self._map_layer(item)
        return Layer()

    def search(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Layer]:
        """
        Search dataset.
        """

        return self.get_datasets(
            page=page,
            page_size=page_size,
            search=keyword,
        )

    def refresh(
        self,
    ) -> list[Layer]:
        """
        Refresh dataset from server.

        DatasetAPI does not manage cache.
        Cache is handled by LayerService.
        """

        logger.info(
            "Refreshing datasets..."
        )

        return self.get_datasets()

    # ==========================================================
    # Download
    # ==========================================================

    def get_download_urls(
        self,
        pk: int | str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve download URLs.
        """

        layer = self.get_dataset(
            pk
        )

        if not layer:

            return []

        return layer.download_urls

    # ==========================================================
    # Links
    # ==========================================================

    def get_links(
        self,
        pk: int | str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve OGC links.
        """

        layer = self.get_dataset(
            pk
        )

        if not layer:

            return []

        return layer.links

    def get_wms_url(
        self,
        pk: int | str,
    ) -> str | None:
        """
        Retrieve WMS URL.
        """

        links = self.get_links(
            pk
        )

        for link in links:

            title = (
                link.get(
                    "title",
                    "",
                ).lower()
            )

            if "wms" in title:

                return link.get(
                    "href"
                )

        return None

    def get_wfs_url(
        self,
        pk: int | str,
    ) -> str | None:
        """
        Retrieve WFS URL.
        """

        links = self.get_links(
            pk
        )

        for link in links:

            title = (
                link.get(
                    "title",
                    "",
                ).lower()
            )

            if "wfs" in title:

                return link.get(
                    "href"
                )

        return None

    # ==========================================================
    # Utility
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            "DatasetAPI("
            f"server='{self.server_url}')"
        )
"""
config.py

Global configuration for GeoNode Connector.

This module centralizes every constant used throughout the plugin,
including:

- Plugin information
- Compatibility
- Network configuration
- OAuth configuration
- REST API endpoints
- GeoServer REST endpoints
- Upload configuration
- Logging
- QSettings keys
- Plugin paths

Keeping all configuration in a single place makes the plugin easier to
maintain and compatible with multiple versions of GeoNode, QGIS and Python.
"""

import os

# =============================================================================
# Plugin Information
# =============================================================================

PLUGIN_NAME = "GeoNode Connector"

PLUGIN_VERSION = "0.1.0"

PLUGIN_AUTHOR = "Alif Marwan Hadid"

PLUGIN_ORGANIZATION = "Pemerintah Kota Yogyakarta"

PLUGIN_DESCRIPTION = (
    "Plugin integrasi GeoNode dengan QGIS untuk "
    "sinkronisasi dataset, metadata, WFS-T, "
    "dan GeoServer REST API."
)

PLUGIN_ID = "geonode_connector"

# =============================================================================
# Compatibility
# =============================================================================

SUPPORTED_GEONODE_VERSIONS = (
    "4",
    "5",
)

SUPPORTED_QGIS_VERSIONS = (
    "3.28",
    "3.34",
    "3.40",
    "3.44",
)

SUPPORTED_PYTHON_VERSIONS = (
    "3.10",
    "3.11",
    "3.12",
)

# =============================================================================
# Default Connection
# =============================================================================

DEFAULT_SERVER = "http://localhost"

VERIFY_SSL = True

DEFAULT_TIMEOUT = 30

CONNECT_TIMEOUT = 10

READ_TIMEOUT = 30

MAX_RETRIES = 3

# =============================================================================
# HTTP Configuration
# =============================================================================

USER_AGENT = f"{PLUGIN_NAME}/{PLUGIN_VERSION}"

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": USER_AGENT,
}

CONTENT_TYPE_JSON = "application/json"

CONTENT_TYPE_FORM = "application/x-www-form-urlencoded"

CONTENT_TYPE_MULTIPART = "multipart/form-data"

DEFAULT_ENCODING = "utf-8"

DEFAULT_TOKEN_TYPE = "Bearer"

# =============================================================================
# OAuth Configuration
# =============================================================================

OAUTH_CLIENT_ID = (
    "p7PQ487EG3VCEoc4seo0Jh6pSM80L4Z82T1EKnGK"
)

OAUTH_CLIENT_SECRET = (
    "Dwfeqt8GVwVREVDVWOIfUjFlYk8xEMIM9f0KXi1Eo6mhebExPtiY3DgKv6EtPTNv5eW3I0t4YhZn6f4ZaAOHKYoNujRktR0Pj03ukS2Oo3sx2TwLHQAUZeMjKYtdL44P"
)

# =============================================================================
# Endpoint Discovery
# =============================================================================

AUTH_LOGIN_ENDPOINTS = (
    "/o/token/",
    "/api/o/token/",
    "/oauth/token/",
    "/api/v2/o/token/",
)

AUTH_REFRESH_ENDPOINTS = AUTH_LOGIN_ENDPOINTS

AUTH_LOGOUT_ENDPOINTS = (
    "/api/v2/logout/",
    "/logout/",
)

AUTH_USER_ENDPOINTS = (
    "/api/v2/users/",
)

AUTH_API_ENDPOINTS = (
    "/api/v2/",
    "/api/v2",
    "/api/",
)

# =============================================================================
# REST API
# =============================================================================

API_VERSION = "v2"

API_BASE = f"/api/{API_VERSION}"

DATASET_ENDPOINT = "datasets"

UPLOAD_ENDPOINT = "uploads"

STYLE_ENDPOINT = "styles"

METADATA_ENDPOINT = "metadata"

SYNC_ENDPOINT = "sync"

DOCUMENT_ENDPOINT = "documents"

LAYER_ENDPOINT = "layers"

DEFAULT_PAGE_SIZE = 20

MAX_PAGE_SIZE = 100

DEFAULT_WMS_VERSION = "1.3.0"

DEFAULT_WFS_VERSION = "2.0.0"

CACHE_TIMEOUT = 300

# =============================================================================
# GeoServer REST
# =============================================================================

GEOSERVER_REST = "/geoserver/rest"

GEOSERVER_DEFAULT_WORKSPACE = "geonode"

GEOSERVER_TIMEOUT = 60

GEOSERVER_ADMIN_USER = "admin"

GEOSERVER_ADMIN_PASSWORD = "7hVVGXu40mpDyyc"

# =============================================================================
# PostGIS Datastore Configuration (GeoNode backend)
# =============================================================================

POSTGIS_DEFAULT_HOST = "172.19.0.2"
POSTGIS_DEFAULT_PORT = 5432
POSTGIS_DEFAULT_DB = "geonode_project_data"
POSTGIS_DEFAULT_USER = "geonode_project_data"
POSTGIS_DEFAULT_PASSWORD = "feNbHr705xgTtHh"

# =============================================================================
# Upload Configuration
# =============================================================================

UPLOAD_CHUNK_SIZE = 1024 * 1024          # 1 MB

MAX_UPLOAD_SIZE = 1024 * 1024 * 500      # 500 MB

SUPPORTED_VECTOR_FORMATS = (
    ".shp",
    ".gpkg",
    ".geojson",
    ".json",
    ".zip",
)

SUPPORTED_RASTER_FORMATS = (
    ".tif",
    ".tiff",
)

# =============================================================================
# Logging
# =============================================================================

LOG_LEVEL = "INFO"

LOG_FILENAME = "geonode_connector.log"

LOG_FORMAT = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(name)s | "
    "%(message)s"
)

# =============================================================================
# Plugin Paths
# =============================================================================

PLUGIN_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

ICON_PATH = os.path.join(
    PLUGIN_ROOT,
    "icon_plugin_qgis.png",
)

ICONS_DIR = os.path.join(
    PLUGIN_ROOT,
    "ui",
    "icons",
)

IMAGES_DIR = os.path.join(
    PLUGIN_ROOT,
    "ui",
    "images",
)

STYLE_DIR = os.path.join(
    PLUGIN_ROOT,
    "ui",
    "styles",
)

# =============================================================================
# QSettings
# =============================================================================

SETTINGS_GROUP = "GeoNodeConnector"

SETTING_SERVER = "server"

SETTING_USERNAME = "username"

SETTING_REMEMBER = "remember"

SETTING_VERIFY_SSL = "verify_ssl"

SETTING_TIMEOUT = "timeout"

SETTING_ACCESS_TOKEN = "access_token"

SETTING_REFRESH_TOKEN = "refresh_token"

SETTING_TOKEN_TYPE = "token_type"

SETTING_EXPIRES_AT = "expires_at"

SETTING_LAST_SERVER = "last_server"

# =============================================================================
# Request Status
# =============================================================================

HTTP_OK = 200

HTTP_CREATED = 201

HTTP_ACCEPTED = 202

HTTP_NO_CONTENT = 204

HTTP_BAD_REQUEST = 400

HTTP_UNAUTHORIZED = 401

HTTP_FORBIDDEN = 403

HTTP_NOT_FOUND = 404

HTTP_METHOD_NOT_ALLOWED = 405

HTTP_INTERNAL_SERVER_ERROR = 500

# =============================================================================
# Miscellaneous
# =============================================================================

DATE_FORMAT = "%Y-%m-%d"

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

TRUE_VALUES = (
    "true",
    "1",
    "yes",
)

FALSE_VALUES = (
    "false",
    "0",
    "no",
)
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
# Plugin Root & Environment Initialization (.env)
# =============================================================================

PLUGIN_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

def _load_env_file(env_path: str) -> None:
    """Memuat variabel konfigurasi dan kredensial dari file .env ke os.environ."""
    if not os.path.isfile(env_path):
        return
    # Coba gunakan python-dotenv jika terpasang
    try:
        import dotenv
        dotenv.load_dotenv(env_path, override=False)
        return
    except Exception:
        pass

    # Parser mandiri bawaan Python sebagai fallback tanpa ketergantungan library luar
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

_ENV_PATH = os.path.join(PLUGIN_ROOT, ".env")
_load_env_file(_ENV_PATH)

# =============================================================================
# Plugin Information
# =============================================================================

PLUGIN_NAME = "GeoNode Connector"

PLUGIN_VERSION = "1.0.0"

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

DEFAULT_SERVER = os.getenv("DEFAULT_SERVER", "https://geonode-beta.jogjakota.go.id")

VERIFY_SSL = True

DEFAULT_TIMEOUT = 60

CONNECT_TIMEOUT = 10

READ_TIMEOUT = 60

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

OAUTH_CLIENT_ID = os.getenv(
    "OAUTH_CLIENT_ID",
    "fkl0njOmuQeyDEtzR4Oq3b3iRAnVXwNYCUeHXbku"
)

OAUTH_CLIENT_SECRET = os.getenv(
    "OAUTH_CLIENT_SECRET",
    "MWtM6EX1lBRi82MKzyvINIBxYYweYQjLunrLS9OxuFPPpDP36wvyundSK8MUejNcJIVGJDhq81bsNCEg6m658ahJDu3qQYhL87822K2i1JoBIiRMZ1elh3iWjbyUokOj"
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

GEOSERVER_ADMIN_USER = os.getenv("GEOSERVER_ADMIN_USER", "admin")

GEOSERVER_ADMIN_PASSWORD = os.getenv("GEOSERVER_ADMIN_PASSWORD", "WzL2i0Nfy7gossM")

# =============================================================================
# PostGIS Datastore Configuration (GeoNode backend)
# =============================================================================

POSTGIS_DEFAULT_HOST = os.getenv("POSTGIS_DEFAULT_HOST", "192.168.10.83")
POSTGIS_DEFAULT_PORT = int(os.getenv("POSTGIS_DEFAULT_PORT", "5432"))
POSTGIS_DEFAULT_DB = os.getenv("POSTGIS_DEFAULT_DB", "project_name_data")
POSTGIS_DEFAULT_USER = os.getenv("POSTGIS_DEFAULT_USER", "project_name_data")
POSTGIS_DEFAULT_PASSWORD = os.getenv("POSTGIS_DEFAULT_PASSWORD", "kNgo46mCu5jErcJ")

# Kredensial Superuser PostgreSQL Backend
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "yhK7USMSVAlUV47")

# Kredensial Basis Data Internal GeoNode (Metadata/Django Database)
GEONODE_DATABASE = os.getenv("GEONODE_DATABASE", "project_name")
GEONODE_DATABASE_USER = os.getenv("GEONODE_DATABASE_USER", "project_name")
GEONODE_DATABASE_PASSWORD = os.getenv("GEONODE_DATABASE_PASSWORD", "JNOFc3PEBJriqvm")
GEONODE_DATABASE_SCHEMA = os.getenv("GEONODE_DATABASE_SCHEMA", "public")
GEONODE_GEODATABASE_SCHEMA = os.getenv("GEONODE_GEODATABASE_SCHEMA", "public")

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

CACHE_DIR = os.path.join(
    PLUGIN_ROOT,
    "cache",
)

SHAPEFILE_CACHE_DIR = os.path.join(
    CACHE_DIR,
    "shapefiles",
)

GEOJSON_CACHE_DIR = os.path.join(
    CACHE_DIR,
    "geojson",
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
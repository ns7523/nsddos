"""Application constants."""

import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

APP_NAME = "nsddos"
APP_HOME_ENV = "NSDDOS_HOME"
APP_CONFIG_ENV = "NSDDOS_CONFIG"
APP_COMPOSE_ENV = "NSDDOS_COMPOSE_FILE"
APP_ASSET_ROOT_ENV = "NSDDOS_ASSET_ROOT"
APP_RUNTIME_VERSION_ENV = "NSDDOS_RUNTIME_VERSION"
APP_RUNTIME_ASSET_BASE_URL_ENV = "NSDDOS_RUNTIME_ASSET_BASE_URL"
RUNTIME_ASSET_RELEASE_REPO = "ns7523/nsddos"
RUNTIME_ASSET_BUNDLE_PATTERN = "nsddos-runtime-{version}.tar.gz"
RUNTIME_ASSET_MANIFEST_PATTERN = "nsddos-runtime-{version}.manifest.json"

try:
    APP_VERSION = version(APP_NAME)
except PackageNotFoundError:
    APP_VERSION = "unknown"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PROJECT_ROOT


def _default_app_dir() -> Path:
    explicit = os.getenv(APP_HOME_ENV)
    if explicit:
        return Path(explicit).expanduser()
    return PROJECT_ROOT / ".nsddos-home"


APP_DIR = _default_app_dir()
LOG_DIR = APP_DIR / "logs"
MODELS_DIR = APP_DIR / "models"
DATA_DIR = APP_DIR / "data"
RUNTIME_DIR = APP_DIR / "runtime"
SNAPSHOT_DIR = RUNTIME_DIR / "snapshots"
CONFIG_PATH = Path(os.getenv(APP_CONFIG_ENV, APP_DIR / "config.yaml")).expanduser()
STATE_PATH = RUNTIME_DIR / "state.json"
EVENTS_PATH = RUNTIME_DIR / "events.log"
ASSET_CACHE_DIR = Path.home() / ".nsddos" / "cache"
COMPOSE_FILE = Path(
    os.getenv(APP_COMPOSE_ENV, PROJECT_ROOT / "docker-compose.yml")
).expanduser()

FLOODLIGHT_JAR = REPOSITORY_ROOT / "external" / "floodlight" / "floodlight.jar"
SFLOWRT_JAR = REPOSITORY_ROOT / "external" / "sflowrt" / "lib" / "sflowrt.jar"
MININET_BIN = Path(os.getenv("NSDDOS_MININET_BIN", "mn")).expanduser()
OVS_VSCTL_BIN = Path(os.getenv("NSDDOS_OVS_VSCTL_BIN", "ovs-vsctl")).expanduser()
OVS_OFCTL_BIN = Path(os.getenv("NSDDOS_OVS_OFCTL_BIN", "ovs-ofctl")).expanduser()

DEFAULT_FLOODLIGHT_PORT = 8080
DEFAULT_FLOODLIGHT_OF_PORT = 6653
DEFAULT_SFLOWRT_PORT = 8008
DEFAULT_SFLOW_PORT = 6343
DEFAULT_DETECTOR_PORT = 9000

RUNTIME_DIRECTORIES = (
    APP_DIR,
    LOG_DIR,
    MODELS_DIR,
    DATA_DIR,
    RUNTIME_DIR,
    SNAPSHOT_DIR,
)


def get_runtime_asset_version() -> str:
    """Return effective runtime asset version."""

    return os.getenv(APP_RUNTIME_VERSION_ENV, APP_VERSION).strip() or APP_VERSION


def get_compose_file() -> Path:
    """Return effective compose file path."""

    from nsddos.bootstrap.assets import compose_file_path

    return compose_file_path()


def get_floodlight_jar() -> Path:
    """Return effective Floodlight jar path."""

    from nsddos.bootstrap.assets import floodlight_jar_path

    return floodlight_jar_path()


def get_sflowrt_jar() -> Path:
    """Return effective sFlow-RT jar path."""

    from nsddos.bootstrap.assets import sflowrt_jar_path

    return sflowrt_jar_path()

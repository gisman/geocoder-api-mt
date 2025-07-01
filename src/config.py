from environs import Env
import logging

env = Env()
env.read_env()  # read .env file, if it exists

JUSO_DATA_DIR = env("JUSO_DATA_DIR")
CODE_DATA_DIR = env("CODE_DATA_DIR", "/disk/nvme1t/geocoder-api-db/code")
GEOCODE_DB = env("GEOCODE_DB", "/disk/nvme1t/geocoder-api-db/rocks_debug_mt")
BIGCACHE_DB = env("BIGCACHE_DB", "/disk/nvme1t/geocoder-api-db/bigcache_debug_mt")
READONLY = env.bool("READONLY", False)
REVERSE_GEOCODE_DB = env(
    "REVERSE_GEOCODE_DB", "/disk/nvme1t/geocoder-api-db/rocks-reverse-geocoder_debug_mt"
)
HD_HISTORY_DB = env(
    "HD_HISTORY_DB", "/disk/nvme1t/geocoder-api-db/rocks_hd_history_debug_mt"
)
FULL_HISTORY_LIST = env.bool("FULL_HISTORY_LIST", False)
HD_HISTORY_START_YYYYMM = env("HD_HISTORY_START_YYYYMM", "202305")
HD_HISTORY_END_YYYYMM = env("HD_HISTORY_END_YYYYMM", "202504")
USE_HASH_CACHE = env.bool("USE_HASH_CACHE", True)

DATABASE_NAME = env("DATABASE_NAME", "geocode")
DATABASE_USER = env("DATABASE_USER")
DATABASE_PASSWORD = env("DATABASE_PASSWORD")
DATABASE_HOST = env("DATABASE_HOST", "localhost")
DATABASE_PORT = env("DATABASE_PORT", "5432")

log_level = env("LOG_LEVEL", "INFO")
if log_level.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    raise ValueError(
        f"Invalid LOG_LEVEL: {log_level}. Must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL."
    )
else:
    if log_level.upper() == "DEBUG":
        LOG_LEVEL = logging.DEBUG
    elif log_level.upper() == "INFO":
        LOG_LEVEL = logging.INFO
    elif log_level.upper() == "WARNING":
        LOG_LEVEL = logging.WARNING
    elif log_level.upper() == "ERROR":
        LOG_LEVEL = logging.ERROR
    elif log_level.upper() == "CRITICAL":
        LOG_LEVEL = logging.CRITICAL

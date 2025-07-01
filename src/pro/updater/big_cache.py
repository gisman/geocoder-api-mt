import json
from pathlib import Path
from typing import Optional, Any
import threading
from src import config
from src.geocoder.db.gimi9_rocks import Gimi9RocksDB


class BigCache:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BigCache, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Load config (assuming config.py exists)
        try:
            self.db_path = config.BIGCACHE_DB
        except ImportError:
            self.db_path = "/tmp/rocksdb_cache"

        # Create directory if it doesn't exist
        Path(self.db_path).mkdir(parents=True, exist_ok=True)

        # Initialize RocksDB
        self.db = Gimi9RocksDB(self.db_path)
        self._initialized = True

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.db.get(key.encode("utf-8"))
            if value is None:
                return None
            return json.loads(value.decode("utf-8"))
        except Exception:
            return None

    def put(self, key: str, value: Any) -> bool:
        """Put value into cache"""
        try:
            serialized_value = json.dumps(value).encode("utf-8")
            self.db.put(key.encode("utf-8"), serialized_value)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            self.db.delete(key.encode("utf-8"))
            return True
        except Exception:
            return False

    def close(self):
        """Close database connection"""
        if hasattr(self, "db"):
            del self.db


# Usage example:
# cache = BigCache()
# cache.put("key1", {"data": "value"})
# result = cache.get("key1")
# cache.delete("key1")

import rocksdb
import json
import asyncio
from .base import DbBase


class RocksDbGeocode(DbBase):
    """
    A class to interact with RocksDB for geocoding purposes.

    Attributes:
        _db (rocksdb.DB): The RocksDB database instance.

    Methods:
        __init__(db_name, **kwargs):
            Initializes the RocksDbGeocode instance and opens the RocksDB database.
        get(k):
            Retrieves the value associated with the given key from the database.
        delete(k):
            Deletes the value associated with the given key from the database.
        put(k, json_val):
            Stores the given key-value pair in the database.
    """

    _db = None  # leveldb.LevelDB(db_name, **kwargs)

    def __init__(self, db_name, **kwargs):
        """
        Initializes the RocksDbGeocode instance and opens the RocksDB database.

        Args:
            db_name (str): The name of the database.
            **kwargs: Additional arguments for the database.
        """
        if not self._db:
            # self._db = rocksdb.open_as_secondary(
            #     db_name, "/disk/nvme1t/geocoder-api-db/rocks_debug_secondary"
            # )
            options = rocksdb.Options()
            options.max_open_files = -1
            # options.block_cache = rocksdb.LRUCache(1024 * 1024 * 1024)  # 1GB

            self._db = rocksdb.RocksDB(db_name, options=options)
            # self._db = rocksdb.open_default(db_name)

    def __iter__(self):
        """
        Returns an iterator for the database.

        Returns:
            rocksdb.Iterator: An iterator for the database.
        """
        return self._db.get_iter()

    # def get(self, k):
    #     return asyncio.run(self.get_async(k))

    async def get(self, k):
        """
        Retrieves the value associated with the given key from the database.

        Args:
            k (str or bytes): The key to retrieve the value for.

        Returns:
            bytes: The value associated with the given key.
        """
        # v = db.get("가평_가평_마장리_67-2".encode())

        if type(k) == bytes:
            return await asyncio.to_thread(self._db.get, None, k)
            # return await self._db.get(None, k)
        else:
            return await asyncio.to_thread(self._db.get, None, k.encode())
            # return await self._db.get(None, k.encode())

    def delete(self, k):
        """
        Deletes the value associated with the given key from the database.

        Args:
            k (str or bytes): The key to delete the value for.
        """
        if type(k) == bytes:
            self._db.delete(k)
        else:
            self._db.delete(k.encode())

    def put(self, k, json_val):
        """
        Stores the given key-value pair in the database.

        Args:
            k (str or bytes): The key to store the value for.
            json_val (dict): The value to store, which will be converted to JSON.
        """
        if type(k) == bytes:
            self._db.put(k, json_val)
        else:
            self._db.put(k.encode(), json.dumps(json_val).encode("utf8"))

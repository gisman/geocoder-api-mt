import rocksdb3
import json

from src import config
from .base import DbBase


class RocksDbGeocode(DbBase):
    """
    A class to interact with RocksDB for geocoding purposes.

    Attributes:
        _db (rocksdb3.DB): The RocksDB database instance.

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
            # self._db = rocksdb3.open_as_secondary(
            #     db_name, "/disk/nvme1t/geocoder-api-db/rocks_debug_secondary"
            # )
            if config.READONLY:
                self._db = rocksdb3.open_as_secondary(db_name, db_name + "_secondary")
            else:
                self._db = rocksdb3.open_default(db_name)

    def __iter__(self):
        """
        Returns an iterator for the database.

        Returns:
            rocksdb3.Iterator: An iterator for the database.
        """
        return self._db.get_iter()

    def get(self, k):
        """
        Retrieves the value associated with the given key from the database.

        Args:
            k (str or bytes): The key to retrieve the value for.

        Returns:
            bytes: The value associated with the given key.
        """
        # v = db.get("가평_가평_마장리_67-2".encode())

        if type(k) == bytes:
            return self._db.get(k)
        else:
            return self._db.get(k.encode())

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

    def write_batch(self, batch):
        """
        Writes a batch of operations to the database.

        Args:
            batch (rocksdb3.WriteBatch): The batch of operations to write.
        """
        self._db.write(batch)

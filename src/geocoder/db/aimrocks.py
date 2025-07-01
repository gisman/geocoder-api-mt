import aimrocks
import json

from src import config
from .base import DbBase


class AimrocksDbGeocode(DbBase):
    """
    A class to interact with AimrocksDB for geocoding purposes.

    Attributes:
        _db (AimrocksDB.DB): The RocksDB database instance.

    Methods:
        __init__(db_name, **kwargs):
            Initializes the AimrocksDbGeocode instance and opens the RocksDB database.
        get(k):
            Retrieves the value associated with the given key from the database.
        delete(k):
            Deletes the value associated with the given key from the database.
        put(k, json_val):
            Stores the given key-value pair in the database.
    """

    _db: aimrocks.DB = None  # leveldb.LevelDB(db_name, **kwargs)

    def __init__(self, db_name, **kwargs):
        """
        Initializes the AimrocksDbGeocode instance and opens the RocksDB database.

        Args:
            db_name (str): The name of the database.
            **kwargs: Additional arguments for the database.
        """
        if not self._db:
            opts = aimrocks.Options(create_if_missing=True, max_write_buffer_number=8)

            self._db = aimrocks.DB(db_name, opts, read_only=config.READONLY)

    def __iter__(self):
        """
        Returns an iterator for the database.

        Returns:
            aimrocks.Iterator: An iterator for the database.
        """
        return self._db.__iter__

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
        if config.READONLY:
            print("write_batch: Cannot write to database in read-only mode.")
        else:
            self._db.write(batch)

    def flush(self):
        """
        Flushes the database to ensure all changes are written.
        """
        self._db.flush()

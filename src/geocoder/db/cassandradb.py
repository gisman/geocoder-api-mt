from unittest import result
from cassandra.cluster import Cluster
from cassandra.query import dict_factory
import json
from geocoder.db.base import DbBase


class CassandraDbGeocode(DbBase):
    """
    A class to interact with a Cassandra database for geocoding operations.
    """

    def __init__(self, db_name, **kwargs):
        """
        Initialize the CassandraDbGeocode instance.

        :param db_name: The name of the Cassandra keyspace.
        :param kwargs: Additional keyword arguments.
        """
        self.cluster = Cluster()
        self.session = self.cluster.connect(db_name)  # keyspace: ks_geocode
        self.session.row_factory = dict_factory

    def get(self, k):
        """
        Retrieve records from the database based on the hash key.

        :param k: The hash key to search for.
        :return: A list of records matching the hash key.
        """
        sql = f"""select hash_key, bm, bn, h1, hd_cd, ld_cd, road_cd, road_nm, x, y, z 
            from addr_hash 
            where hash_key = '{k}'"""

        rows = self.session.execute(sql)
        result = []
        for row in rows:
            result.append(row)

        return result

    def delete(self, k):
        """
        Delete records from the database based on the hash key.

        :param k: The hash key of the records to delete.
        """
        sql = f"""delete from addr_hash
            where hash_key = '{k}'"""

        self.session.execute(sql)

    def put(self, k, json_val):
        """
        Insert a new record into the database.

        :param k: The hash key for the new record.
        :param json_val: A dictionary containing the values to insert.
        """
        sql = f"""insert into addr_hash(hash_key, bm, bn, h1, hd_cd, ld_cd, road_cd, road_nm, x, y, z) 
            values('{json_val["hash_key"]}'
            ,'{json_val["bm"]}'
            ,'{json_val["bn"]}'
            ,'{json_val["h1"]}'
            ,'{json_val["hd_cd"]}'
            ,'{json_val["ld_cd"]}'
            ,'{json_val["road_cd"]}'
            ,'{json_val["road_nm"]}'
            ,'{json_val["x"]}'
            ,'{json_val["y"]}'
            ,'{json_val["z"]}'
            ) """

        self.session.execute(sql)

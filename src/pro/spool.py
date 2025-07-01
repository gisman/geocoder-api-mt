import leveldb
import json
import csv


def db_to_text(from_db, to_text):
    """Transfer leveldb to text file."""
    _db = (
        leveldb.LevelDB(from_db, create_if_missing=False)
        if isinstance(from_db, str)
        else from_db
    )
    with open(to_text, "w", encoding="utf-8") as _f:
        for _k, _v in _db.RangeIter(
            key_from="영등포_".encode(), key_to="영등표_".encode()
        ):
            j = json.loads(_v.decode())
            _f.write(_k.decode() + "," + _v.decode() + "\n")


def db_to_dynamodb(from_db, to_json):
    """Transfer leveldb to dynamodb json file."""
    _db = (
        leveldb.LevelDB(from_db, create_if_missing=False)
        if isinstance(from_db, str)
        else from_db
    )
    with open(to_json, "w", encoding="utf-8") as _f:
        for _k, _v in _db.RangeIter(
            key_from="영등포_".encode(), key_to="영등표_".encode()
        ):
            j = json.loads(_v.decode())
            _f.write(_k.decode() + "," + _v.decode() + "\n")


# {
#     "geocode": [
#         {
#             "PutRequest": {
#                 "Item": {
#                     "key": {"S":"Amazon DynamoDB"},
#                     "val": {"S":"Amazon Web Services"}
#                 }
#             }
#         },
#         {
#             "PutRequest": {
#                 "Item": {
#                     "key": {"S":"Amazon S3"},
#                     "val": {"S":"Amazon Web Services"}
#                 }
#             }
#         }
#     ]
# }


def db_to_csv(from_db, to_text):
    """Transfer leveldb to text file."""
    _db = (
        leveldb.LevelDB(from_db, create_if_missing=False)
        if isinstance(from_db, str)
        else from_db
    )

    with open(to_text, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        for _k, _v in _db.RangeIter():
            # for _k, _v in _db.RangeIter(key_from="영등포_".encode(), key_to="영등표_".encode()):
            jj = json.loads(_v.decode())
            for j in jj:
                # print([_k.decode(), j['bm'][0] if len(j['bm'])>0 else '', j['x'], j['y'], j['z'], j['hc'], j['lc'], j['rc'], j['bn'], j['h1'], j['rm']])
                csvwriter.writerow(
                    [
                        _k.decode(),
                        j["bm"][0] if len(j["bm"]) > 0 else "",
                        j["x"],
                        j["y"],
                        j["z"],
                        j["hc"],
                        j["lc"],
                        j["rc"],
                        j["bn"],
                        j["h1"],
                        j["rm"],
                    ]
                )


def db_to_rocksdb(level_path, rocks_path):
    """Transfer leveldb to rocksdb."""
    import rocksdb3

    from_db = leveldb.LevelDB(level_path, create_if_missing=False)
    target_db = rocksdb3.open_default(rocks_path)
    # target_db = rocksdb3.open_as_secondary(rocks_path, rocks_path + "_secondary")

    total_read = 0
    total_write = 0
    for k, v in from_db.RangeIter():
        total_read += 1
        # print([_k.decode(), j['bm'][0] if len(j['bm'])>0 else '', j['x'], j['y'], j['z'], j['hc'], j['lc'], j['rc'], j['bn'], j['h1'], j['rm']])
        # key가 최소 4자 이상이어야 함
        source_key = k.decode()
        if len(source_key) > 3 and not source_key.startswith("_"):
            # print(k.decode(), v.decode())
            target_db.put(source_key.encode(), v.decode().encode())
            total_write += 1

        if total_read % 100000 == 0:
            print(f"total_read: {total_read:,}, total_write: {total_write:,}")

    # assert db.get(b"my key") is None
    # db.put(b"my key", b"my value")
    # assert db.get(b"my key") == b"my value"
    # assert list(db.get_iter()) == [(b"my key", b"my value")]

    del from_db
    del target_db  # auto close db
    # rocksdb3.destroy(rocks_path)

    # _db = leveldb.LevelDB(from_db, create_if_missing=False) if isinstance(from_db, str) else from_db

    # with open(to_text, 'w', newline='') as csvfile:
    #     csvwriter = csv.writer(csvfile)
    #     for _k, _v in _db.RangeIter():
    #     # for _k, _v in _db.RangeIter(key_from="영등포_".encode(), key_to="영등표_".encode()):
    #         jj = json.loads(_v.decode())
    #         for j in jj:
    #             # print([_k.decode(), j['bm'][0] if len(j['bm'])>0 else '', j['x'], j['y'], j['z'], j['hc'], j['lc'], j['rc'], j['bn'], j['h1'], j['rm']])
    #             csvwriter.writerow([_k.decode(), j['bm'][0] if len(j['bm'])>0 else '', j['x'], j['y'], j['z'], j['hc'], j['lc'], j['rc'], j['bn'], j['h1'], j['rm']])


if __name__ == "__main__":
    db_to_rocksdb(
        "/home/gisman/projects/geocoder-api/db/current",
        "/home/gisman/projects/geocoder-api/db/rocks",
    )
    # db_to_text("/home/gisman/projects/geocoder-api/db/db_20211114", "spool.csv")
    # db_to_dynamodb('/home/gisman/projects/geocoder-api/db/db_20210505', 'dynamodb.json')
    # db_to_csv('/home/gisman/projects/geocoder-api/db/current', 'spool_cassandra.csv')

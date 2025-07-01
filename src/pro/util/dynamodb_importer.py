import sys

sys.path.insert(1, "/home/gisman/projects/geocoder-api")
from geocoder.db.dynamodb import DynamoDbGeocode
import json

# import boto3


def create_geocode_table(dynamodb):
    # if not dynamodb:
    #     dynamodb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")

    return dynamodb.init_table("geocode")


if __name__ == "__main__":
    db = DynamoDbGeocode("dynamodb", endpoint_url="http://localhost:8000")
    # db = DynamoDbGeocode('dynamodb', region_name='ap-northeast-2')

    # geocode_table = create_geocode_table(db)
    geocode_table = db.init_table("geocode")
    print("Table status:", geocode_table.table_status)

    # geocode_table.scan()
    f = open("spool.csv", "r")
    line = f.readline()
    n = 0
    keys = []
    vals = []
    while line:
        # print(line)
        line = f.readline()
        # 영등포_영등포로62가길_4-4,[{"x": 948430, "y": 1946418, "z": "07309", "hc": "1156051500", "lc": "1156013200", "rc": "115604154734", "bn": "1156013200100480005015140", "h1": "\uc11c\uc6b8", "rm": "\uc601\ub4f1\ud3ec\ub85c62\uac00\uae38", "bm": []}]

        a = line.split(",", maxsplit=1)

        key = a[0]  #'영등포_영등포로62가길_4-4'
        val = a[1]
        keys.append(key)
        vals.append(val)
        # val = json.loads('[{"x": 948430, "y": 1946418, "z": "07309", "hc": "1156051500", "lc": "1156013200", "rc": "115604154734", "bn": "1156013200100480005015140", "h1": "\uc11c\uc6b8", "rm": "\uc601\ub4f1\ud3ec\ub85c62\uac00\uae38", "bm": []}]')

        n += 1
        if not (n % 25):
            db.BatchPut(keys, vals)
            keys.clear()
            vals.clear()
            print(n)

    if not (n % 25):
        db.BatchPut(keys, vals)
        keys.clear()
        vals.clear()
        print(n)

    f.close()

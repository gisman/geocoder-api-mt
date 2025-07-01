# python 3
import re

# import csv
import json

# import leveldb # faster than plyvel
# from geocoder.db.leveldb import LevelDbGeocode
from geocoder.db.rocksdb import RocksDbGeocode

# from geocoder.db.dynamodb import DynamoDbGeocode
# from geocoder.db.cassandradb import CassandraDbGeocode
import psycopg2
import psycopg2.extras

# import plyvel
import time
import sys

# import os
import shutil

# sys.path.insert(1, "/home/gisman/projects/geocoder-api")

from geocoder.Geocoder import Geocoder
from pro.DbCreator import table_to_hash

# from AddressClassifier import AddressClassifier

DB_NAME = "/home/gisman/projects/geocoder-api/db/current"
# DB_NAME = 'ks_geocode'
# DB_NAME = '/home/gisman/projects/geocoder-api/db/db_20210221'


def deleteDb():
    try:
        shutil.rmtree(DB_NAME)
    except OSError as e:
        print("Error: %s : %s" % (DB_NAME, e.strerror))


def addAddress():
    # db = CassandraDbGeocode(DB_NAME)
    db = LevelDbGeocode(DB_NAME, create_if_missing=False)
    # db = DynamoDbGeocode('dynamodb', endpoint_url="http://localhost:8000")

    # try:
    connection = psycopg2.connect(
        user="gisman",
        password="xhddlfd0",
        host="dev.gimi9.com",
        # host="localhost",
        port="5432",
        database="geocode",
    )

    sqlSelect = """
        select 
            a.h1_nm,	a.h23_nm,	a.ld_nm,	a.h4_nm,	a.ri_nm,	a.road_nm
        ,	a.undgrnd_yn,	cast(a.bld1 as text),	cast(a.bld2 as text)
        ,	a.san,	cast(a.bng1 as text),	cast(a.bng2 as text)
        ,	a.bld_reg,	a.bld_nm_text, a.bld_nm
        ,	a.ld_cd,	a.h4_cd,	a.road_cd,	a.zip,	a.bld_mgt_no
        ,	a.bld_x,	a.bld_y
        from geocode.tbaddress a
    """

    sqlWheres = [
        # "bld_nm_text like '%주민센터'"
        # "h23_nm = '강서구' and h4_nm like '화곡%' and a.bld_nm_text like '%주민센터'"
        # "h23_nm = '달성군' and ri_nm = '교항리' and bld_reg like '%제림%'"
        "h23_nm = '시흥시' and road_nm = '호현로63번길' and bld1 = 11",
        # "h23_nm = '제주시' and h4_nm = '이도2동' and bng1 = 1080 and bng2 = 1",
        # "h1_nm = '제주특별자치도'",
        # "h1_nm = '대구광역시'",
        # "h1_nm = '광주광역시'",
        # "h1_nm = '부산광역시'",
        # "h1_nm = '서울특별시'",
        # "h23_nm = '성남시 중원구' and h4_nm = '금광2동' and bng1 = 4308",
        # "ld_nm = '신길동' and bng1 = 48 and bld_nm <> ''",
        # "ld_nm = '금곡동' and bld_mgt_no = '2632010100108100005012963'",
        # "h1_nm = '세종특별자치시'",
        # "h1_nm = '세종특별자치시' and road_nm = '나성북로' and bld1 = 30",
        # "h23_nm = '오산시' and road_nm = '여계산로' and bld1 = '58'",
        # "h23_nm = '오산시'",
        # "h23_nm = '영천시' and road_nm = '포은로' and bld1 = 491",
        # "h23_nm = '영주시' and road_nm = '천상로'",
        # "h23_nm = '양덕군' and road_nm = '진불길'",
        # "h23_nm = '강남구' and road_nm = '도곡로57길' and bld1 = 12",
        # "h23_nm = '영등포구' and road_nm = '가마산로' and bld1 = 426",
        # "h23_nm = '창원시 마산회원구' and road_nm like '3·15대로' and bld1 = 558",
        # "h4_nm = '종로1.2.3.4가동' and bng1 = 171 and bng2=1",
        # "h23_nm = '동대문구' and road_nm like '서울시립대로1%'",
        # "h23_nm = '부천시' and road_nm = '경인로160번길' and bld1 = 70",
        # "road_nm = '불광로' and undgrnd_yn = '1'",
        # "h23_nm = '부산진구' and h4_nm = '가야제1동' and bng1 = 303",
        # "h23_nm = '동구' and road_nm = '안심로' and bld1 = 363",
        # "h23_nm = '종로구' and ld_nm = '홍지동' and bng1 = 127",
    ]

    for sqlW in sqlWheres:
        sql = " ".join([sqlSelect, "where", sqlW])
        # for i in range(1000):
        table_to_hash(connection, db, sql)

    del db
    # ldb = leveldb.LevelDB(DB_NAME, create_if_missing=True)
    # db = CassandraDbGeocode(DB_NAME, create_if_missing=False)
    db = LevelDbGeocode(DB_NAME, create_if_missing=False)
    # db = DynamoDbGeocode('dynamodb', endpoint_url="http://localhost:8000")

    del db
    # time.sleep(1)


if __name__ == "__main__":
    # create db
    # deleteDb()

    # leveldb에 DB의 주소 추가.
    # addAddress()

    # run test
    # print result

    # db = leveldb.LevelDB(DB_NAME, create_if_missing=False)
    # db = DynamoDbGeocode('dynamodb', endpoint_url="http://localhost:8000")
    # db = LevelDbGeocode(DB_NAME, create_if_missing=False)
    db = RocksDbGeocode(DB_NAME, create_if_missing=False)
    # db = CassandraDbGeocode(DB_NAME)

    geocoder = Geocoder(db)

    # with open('/home/gisman/projects/geocoder-api/test/test신길동.txt', 'r', encoding='cp949') as f:
    # with open('/home/gisman/projects/geocoder-api/test/test2.txt', 'r', encoding='utf8') as f:
    # with open('/home/gisman/projects/geocoder-api/test/test3.txt', 'r', encoding='utf8') as f:
    # with open('/home/gisman/projects/geocoder-api/test/testfiles/test.txt', 'r', encoding='utf8') as f:
    with open(
        "/home/gisman/projects/geocoder-api/test/testfiles/필수test.txt",
        "r",
        encoding="utf8",
    ) as f:
        n = 0
        errcnt = 0
        start_time = time.time()

        for line in f:
            address = line.strip()
            if address == "":
                break
            elif address.startswith("#"):  # 주석
                print(address)
                continue

            n = n + 1

            print("===============================================")
            val = geocoder.search(address)
            # key, address, addressCls, toksString = geocoder.addressHash(address)

            # if val['success'] or val['errmsg'] != 'RUNTIME ERROR':
            if not val["success"]:
                errcnt = errcnt + 1
                # continue

            print(val["address"])
            if val["errmsg"]:
                print(val["errmsg"])
            print(val["hash"])
            print(val["addressCls"])
            print(val["toksString"])

        elapsed_time = time.time() - start_time
        print(
            "total count=",
            n,
            " elapsed_time(s)=",
            elapsed_time,
            " count/sec= ",
            n / elapsed_time,
        )
        print(f"err={errcnt}, success={(n-errcnt)/n*100:2.2f}%")

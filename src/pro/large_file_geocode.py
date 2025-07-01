from pathlib import Path
import time
import logging
import csv
from markupsafe import escape
import os

from geocoder.Geocoder import Geocoder
from geocoder.db.rocksdb import RocksDbGeocode
import json
import leveldb
from pyproj import Transformer, CRS
import time
import config

# LINES_LIMIT = 50000
LINES_LIMIT = 3000

"""
2024.4.27 
산업연 지오코딩 200만건 급하게 납품하기 위해 임시로 제작.
이후 geocode.gimi9.com에 통합 함.
"""


def get_h1(val):
    if val["bn"]:
        return val["bn"][:2]
    elif val["hc"]:
        return val["hc"][:2]
    elif val["lc"]:
        return val["lc"][:2]


def get_h2(val):
    if val["bn"]:
        return val["bn"][:5]
    elif val["hc"]:
        return val["hc"][:5]
    elif val["lc"]:
        return val["lc"][:5]


def geocode_file(filepath, download_dir, limit=10000):
    # 주소 컬럼, 인코딩, 구분자 자동으로 찾기

    geocoder = Geocoder(
        RocksDbGeocode(config.GEOCODE_DB, create_if_missing=True)
        # RocksDbGeocode(
        #     "/home/gisman/projects/geocoder-api/db/rocks", create_if_missing=True
        # )
    )
    # geocoder = ApiHandler.geocoder

    tf = get_csr_transformer()
    # tf = ApiHandler.tf

    with open(
        filepath,
        "r",
        encoding="utf8",
    ) as f:
        summary = {}
        # result = []
        count = 0
        success_count = 0
        hd_success_count = 0
        fail_count = 0
        start_time = time.time()

        csv_input = csv.reader(f, delimiter="%")
        headers = next(csv_input)

        filename = os.path.basename(filepath)
        csvfile = open(f"{download_dir}/{filename}.csv", "w", newline="")
        writer = csv.DictWriter(
            csvfile,
            fieldnames=headers + ["success", "x_axis", "y_axis", "h1", "h2"],
            delimiter="%",
        )
        writer.writeheader()

        for line in csv_input:
            # for line in f:
            count += 1

            # limit 체크. 1만건 또는 남은 쿼터 중 작은 것. 용역은 무제한
            if limit > 0 and count > limit:
                break

            addr = line[6].strip()

            # make dict from line(list) as values and headers as keys
            prefix = dict(zip(headers, line))

            if addr == "":
                row = {
                    # "no": count,
                    # "address": "",
                    "success": "실패",
                    "x_axis": 0.0,
                    "y_axis": 0.0,
                    "h1": "",
                    "h2": "",
                }

                # merge prefix and row
                row.update(prefix)

                writer.writerow(row)
                continue

            val = geocoder.search(addr)
            x1 = 0.0
            y1 = 0.0
            success = "실패"
            if not val:
                val = {}
                fail_count += 1
            elif val["success"]:
                if val["x"]:
                    x1, y1 = tf.transform(val["x"], val["y"])
                    success = "성공"
                    success_count += 1
                else:
                    fail_count += 1

                if val.get("hd_cd"):
                    hd_success_count += 1

            val["inputaddr"] = addr
            if val["success"]:
                h1 = get_h1(val)
                h2 = get_h2(val)
            else:
                h1 = ""
                h2 = ""

            row = {
                # 원본 데이터
                # "no": count,
                # "address": addr,
                # "h1": success,
                # "h2": success,
                "success": success,
                "x_axis": int(x1),
                "y_axis": int(y1),
                "h1": h1,
                "h2": h2,
                # 2,경남 김해시 한림면 용덕로 282-1,성공,128.828816,35.301403
            }

            # merge prefix and row
            row.update(prefix)

            writer.writerow(row)

            if count % 10000 == 0:
                print(
                    f"{count}, {time.time() - start_time}, success:{success_count}, fail:{fail_count}"
                )

        csvfile.close()
        summary["total_time"] = time.time() - start_time
        summary["total_count"] = count
        summary["success_count"] = success_count
        summary["hd_success_count"] = hd_success_count
        fail_count = count - success_count
        summary["fail_count"] = fail_count
        summary["filename"] = filename
        # summary["results"] = result
        with open(
            f"{download_dir}/{filename}.summary", "w", newline=""
        ) as summary_file:
            json.dump(summary, summary_file)

        # self.send_response(200)  # 응답코드
        # self.end_headers()  # 헤더와 본문을 구분
        # self.wfile.write(json.dumps(summary).encode("utf-8"))
        print(json.dumps(summary))


def get_csr_transformer():
    """
    UTM-K (GRS80) to TM128(KATECH)
    """
    KATECH = {
        "proj": "tmerc",
        "lat_0": "38",
        "lon_0": "128",
        "ellps": "bessel",
        "x_0": "400000",
        "y_0": "600000",
        "k": "0.9999",
        "units": "m",
        "no_defs": True,
        "towgs84": "-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43",
    }

    CRS_TM128 = CRS(**KATECH)

    tf = Transformer.from_crs(CRS.from_string("EPSG:5179"), CRS_TM128, always_xy=True)

    return tf


if __name__ == "__main__":
    from sys import argv

    # filepath = Path("/home/gisman/test/kiet-geocode") / "emlist.txt"
    filepath = Path("/home/gisman/test/kiet-geocode") / "emlist_100.txt"
    download_dir = "/home/gisman/test/kiet-geocode/out"
    geocode_file(filepath, download_dir, 0)

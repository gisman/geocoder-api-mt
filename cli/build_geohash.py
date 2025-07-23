#!/usr/bin/env python3

# python build_geohash.py \
# --shp=/disk/hdd-lv/juso-data/행정동/202305/11000/TL_SCCO_GEMD.shp \
# --output_dir=/disk/hdd-lv/juso-data/행정동/202305/11000/TL_SCCO_GEMD \
# --depth=7 \
# --key_prefix=202305

import argparse
import os
import geopandas as gpd

import pygeohash as geohash
import json
import time
import logging
import numpy as np

# import rocksdb3
import sys
import os

# Add the parent directory of 'src' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.geocoder.db.gimi9_rocks import Gimi9RocksDB
from shapely.geometry import box, MultiPolygon
from shapely.validation import make_valid
from tqdm import tqdm
import sys
from polygon_geohasher.polygon_geohasher import polygon_to_geohashes

# import geohash

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def open_rocksdb(db_path, create_if_missing=True):
    """
    RocksDB를 열거나 생성합니다.

    Args:
        db_path: 데이터베이스 경로
        create_if_missing: 데이터베이스가 없을 경우 생성할지 여부

    Returns:
        RocksDB 인스턴스
    """
    try:
        db = Gimi9RocksDB(db_path)
        # db = rocksdb3.open_default(db_path)
        return db

    except Exception as e:
        logger.error(f"Error opening RocksDB: {str(e)}")
        raise


def get_equal_data(existing_data, attr_dict):
    # existing_data의 hd가 같은것 추출
    equal_data_list = []
    for item in existing_data:
        if item.get("hd_cd") == attr_dict.get("hd_cd"):
            equal_data_list.append(item)

    if equal_data_list:
        for item in equal_data_list:
            if item.get("intersection_wkt") == attr_dict.get("intersection_wkt"):
                # intersection_wkt가 같으면 기존 데이터를 그대로 반환
                return item

    return None


def process_region_to_rocksdb(shp_file, db_path, yyyymm, batch_size=1000):
    """
    Shapefile을 읽어 형상을 simplify하여 RocksDB에 저장합니다.

    Args:
        shp_file: Shapefile 경로
        db_path: RocksDB 데이터베이스 경로
        region_prefix: 키 접두사
        batch_size: 한 번에 처리할 피처 수
    """

    logger.info(f"Reading shapefile: {shp_file}")

    # RocksDB 열기
    db = open_rocksdb(db_path)

    CODE: str = ""  # 코드 필드명
    REGION_PREFIX: str = ""  # 지역 접두사
    TOLERANCE: float = 0.0001  # 단순화 허용 오차

    if shp_file.endswith("TL_SCCO_GEMD.shp"):
        CODE = "EMD_CD"
        REGION_PREFIX = "hd"
        TOLERANCE = 10 / 111320  # 10m tolerance in degrees
    elif shp_file.endswith("TL_SCCO_SIG.shp"):
        CODE = "SIG_CD"
        REGION_PREFIX = "h23"
        TOLERANCE = 20 / 111320  # 20m tolerance in degrees
    elif shp_file.endswith("TL_SCCO_CTPRVN.shp"):
        CODE = "CTPRVN_CD"
        REGION_PREFIX = "h1"
        TOLERANCE = 50 / 111320  # 50m tolerance in degrees
    else:
        logger.error(f"Unsupported shapefile: {shp_file}")
        raise ValueError(f"Unsupported shapefile: {shp_file}")

    # 행정동 geohash로 검색
    # TL_SCCO_GEMD.shp    행정동
    # TL_SCCO_SIG.shp     시군구
    # TL_SCCO_CTPRVN.shp  광역시도

    # geohash가 업어서 검색 불가
    # TL_KODIS_BAS.shp    기초구역
    # TL_SCCO_EMD.shp     법정동
    # TL_SCCO_LI.shp      리
    # TL_SPPN_MAKAREA.shp 지점번호표기 의무지역

    try:
        # Shapefile 읽기
        gdf = gpd.read_file(shp_file, encoding="cp949")
        logger.info(f"Loaded {len(gdf)} features")

        # CRS가 EPSG:4326(WGS84)이 아닌 경우 변환
        if gdf.crs != "EPSG:4326":
            logger.info(f"Converting CRS from {gdf.crs} to EPSG:4326")
            gdf.set_crs("EPSG:5179", inplace=True)  # 원래 CRS 설정
            gdf = gdf.to_crs("EPSG:4326")

        # 일괄 쓰기 및 메모리 관리를 위한 배치 처리
        # wb = rocksdb.WriteBatch()
        batch_count = 0

        # 진행률 표시
        logger.info(f"Add features {REGION_PREFIX}, yyyymm {yyyymm}...")

        for idx, row in tqdm(gdf.iterrows(), total=len(gdf)):
            geom = row.geometry
            attr_dict = row.drop("geometry").to_dict()

            if geom.geom_type == "Point":
                continue  # 포인트는 처리하지 않음

            # Simplify the geometry to reduce complexity
            if not geom.is_valid:
                geom = make_valid(geom)

            simplified_geom = geom.simplify(
                tolerance=TOLERANCE, preserve_topology=False
            )  # 10m tolerance in degrees

            if not simplified_geom.is_valid:
                simplified_geom = make_valid(geom)

            if simplified_geom.is_empty or not simplified_geom.is_valid:
                continue  # Skip invalid or empty geometries

            # .js의 WKT 라이브러리가 MultiCollection을 지원하지 않으므로 MultiPolygon으로 변환
            if hasattr(simplified_geom, "geoms"):
                # print(
                #     [
                #         g.geom_type
                #         for g in simplified_geom.geoms
                #         if g.geom_type == "Point"
                #     ]
                # )
                polygons = [
                    geom
                    for geom in simplified_geom.geoms
                    if geom != geom.geom_type in ("Polygon", "MultiPolygon")
                ]
                if len(polygons) == 1 and polygons[0].geom_type == "MultiPolygon":
                    simplified_geom = MultiPolygon(polygons[0])
                else:
                    simplified_geom = MultiPolygon(polygons)
            geom = simplified_geom

            # h = geohash.encode(y, x, depth)
            # key = h
            key = f"{REGION_PREFIX}-{yyyymm}-{attr_dict[CODE]}"

            attr_dict["wkt"] = geom.wkt
            attr_dict["yyyymm"] = yyyymm
            db.put(key.encode(), json.dumps(attr_dict).encode())

            # stats["total_geohashes"] += 1
            batch_count += 1
            # stats["processed_features"] += 1
    except Exception as e:
        logger.error(f"Error processing shapefile: {str(e)}")
        raise
    finally:
        # RocksDB는 명시적으로 닫을 필요가 없음
        pass

        # 남은 배치 쓰기
        # if batch_count > 0:
        #     db.write(wb)

        # # 메타데이터 작성
        # stats["end_time"] = time.time()
        # stats["elapsed_time"] = stats["end_time"] - stats["start_time"]

        # metadata = {
        #     "count": stats["total_geohashes"],
        #     "features": stats["total_features"],
        #     "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        #     "elapsed_time": stats["elapsed_time"],
        #     "description": "Geohash database generated from shapefile",
        # }

        # # 메타데이터 저장
        # db.put(b"__metadata__", json.dumps(metadata).encode())

        # logger.info(f"Processed {stats['processed_features']} features")
        # logger.info(f"Generated {stats['total_geohashes']} geohashes")
        # logger.info(f"Time elapsed: {stats['elapsed_time']:.2f} seconds")

        # return stats


def process_shapefile_to_rocksdb(shp_file, db_path, depth, key_prefix, batch_size=1000):
    """
    Shapefile을 읽어 geohash를 생성하고 바로 RocksDB에 저장합니다.

    Args:
        shp_file: Shapefile 경로
        db_path: RocksDB 데이터베이스 경로
        depth: Geohash 깊이
        key_prefix: 키 접두사 (사용하지 않음)
        batch_size: 한 번에 처리할 피처 수

    Returns:
        dict: 처리 통계
    """
    logger.info(f"Reading shapefile: {shp_file}")

    # RocksDB 열기
    db = open_rocksdb(db_path)

    try:
        # Shapefile 읽기
        gdf = gpd.read_file(shp_file, encoding="cp949")
        logger.info(f"Loaded {len(gdf)} features")

        # CRS가 EPSG:4326(WGS84)이 아닌 경우 변환
        if gdf.crs != "EPSG:4326":
            logger.info(f"Converting CRS from {gdf.crs} to EPSG:4326")
            gdf.set_crs("EPSG:5179", inplace=True)  # 원래 CRS 설정
            gdf = gdf.to_crs("EPSG:4326")

        # 처리 통계
        stats = {
            "total_features": len(gdf),
            "processed_features": 0,
            "total_geohashes": 0,
            "start_time": time.time(),
        }

        # 일괄 쓰기 및 메모리 관리를 위한 배치 처리
        # wb = rocksdb.WriteBatch()
        batch_count = 0

        # 진행률 표시
        logger.info(f"Generating geohashes with depth {depth}...")

        for idx, row in tqdm(gdf.iterrows(), total=len(gdf)):
            geom = row.geometry
            attr_dict = row.drop("geometry").to_dict()

            # 포인트의 경우 간단히 처리
            if geom.geom_type == "Point":
                x, y = geom.x, geom.y
                h = geohash.encode(y, x, depth)
                key = h
                # key = f"{key_prefix}_{h}" if key_prefix else h

                # 기존 값이 있는지 확인
                existing_value = db.get(key.encode())
                if existing_value:
                    existing_data = json.loads(existing_value)
                    if isinstance(existing_data, list):
                        existing_data.append(attr_dict)
                    else:
                        existing_data = [existing_data, attr_dict]
                    db.put(key.encode(), json.dumps(existing_data).encode())
                else:
                    db.put(key.encode(), json.dumps(attr_dict).encode())

                stats["total_geohashes"] += 1
                batch_count += 1

            # 폴리곤/라인의 경우
            elif geom.geom_type in [
                "Polygon",
                "MultiPolygon",
                "LineString",
                "MultiLineString",
            ]:
                # 해당 지오메트리의 경계 가져오기
                minx, miny, maxx, maxy = geom.bounds

                # 경계 내의 geohash 박스들을 생성
                # geohash_boxes = create_geohash_boxes(minx, miny, maxx, maxy, depth)
                hash_list = polygon_to_geohashes(geom, precision=depth, inner=False)
                for h in hash_list:
                    key = h
                    # key = f"{key_prefix}_{h}" if key_prefix else h

                    # geom과 h의 경계 추출
                    lat_min, lon_min, lat_max, lon_max = geohash.get_bounding_box(h)
                    geohash_box = box(lon_min, lat_min, lon_max, lat_max)

                    # 폴리곤과 geohash 박스의 교차 영역 계산
                    intersection = geom.intersection(geohash_box)

                    # 교차 영역이 유효한 경우만 처리
                    if not intersection.is_empty:
                        attr_dict["intersection_wkt"] = intersection.wkt

                    attr_dict["from_yyyymm"] = ""  # key_prefix
                    attr_dict["to_yyyymm"] = ""  # key_prefix

                    # 기존 값이 있는지 확인
                    existing_value = db.get(key.encode())
                    if existing_value:
                        existing_data = json.loads(existing_value)

                        # 기존 값과 병합
                        equal_data = get_equal_data(existing_data, attr_dict)
                        if equal_data:
                            # 기존 데이터와 동일한 hd_cd와 intersection_wkt가 있는 경우
                            # 기존 데이터를 그대로 사용
                            continue

                        if isinstance(existing_data, list):
                            existing_data.append(attr_dict)
                        else:
                            existing_data = [existing_data, attr_dict]

                        db.put(key.encode(), json.dumps(existing_data).encode())
                    else:
                        db.put(key.encode(), json.dumps([attr_dict]).encode())

                    stats["total_geohashes"] += 1
                    batch_count += 1

            stats["processed_features"] += 1

        # 남은 배치 쓰기
        # if batch_count > 0:
        #     db.write(wb)

        # 메타데이터 작성
        stats["end_time"] = time.time()
        stats["elapsed_time"] = stats["end_time"] - stats["start_time"]

        metadata = {
            "count": stats["total_geohashes"],
            "features": stats["total_features"],
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_time": stats["elapsed_time"],
            "description": "Geohash database generated from shapefile",
        }

        # 메타데이터 저장
        db.put(b"__metadata__", json.dumps(metadata).encode())

        logger.info(f"Processed {stats['processed_features']} features")
        logger.info(f"Generated {stats['total_geohashes']} geohashes")
        logger.info(f"Time elapsed: {stats['elapsed_time']:.2f} seconds")

        return stats

    except Exception as e:
        logger.error(f"Error processing shapefile: {str(e)}")
        raise
    finally:
        # RocksDB는 명시적으로 닫을 필요가 없음
        pass


def main():
    # 명령줄 인수 파싱
    parser = argparse.ArgumentParser(
        description="Build geohash database from shapefile"
    )
    parser.add_argument("--shp", required=True, help="Input shapefile path")
    parser.add_argument("--output_dir", required=True, help="Output RocksDB directory")
    parser.add_argument(
        "--depth", type=int, default=7, help="Geohash precision/depth (default: 7)"
    )
    # 사용하지 않음
    parser.add_argument(
        "--key_prefix", default="", help="Key prefix for geohash (default: none)"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=1000,
        help="Batch size for processing (default: 1000)",
    )
    parser.add_argument(
        "-r",
        action="store_true",
        help="영역 형상 추가 (default: hd)",
    )

    args = parser.parse_args()

    # 입력 확인
    if not os.path.exists(args.shp):
        logger.error(f"Error: Shapefile {args.shp} does not exist")
        return 1

    # 출력 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)

    # RocksDB 경로
    db_path = args.output_dir

    try:
        if args.r:
            # region_prefix = args.region
            # --shp=/disk/hdd-lv/juso-data/전체분/202305/map/50000/TL_SCCO_GEMD.shp
            yyyymm = args.shp.split("/")[-4]  # 예: 202305
            process_region_to_rocksdb(args.shp, db_path, yyyymm, args.batch_size)

            logger.info(f"Region add complete! Database saved to {db_path}")
            return 0
        else:
            # Shapefile 처리 및 RocksDB 저장
            stats = process_shapefile_to_rocksdb(
                args.shp, db_path, args.depth, args.key_prefix, args.batch_size
            )

            # 메타데이터 파일 작성 (RocksDB 외부에도 저장)
            metadata = {
                "count": stats["total_geohashes"],
                "features": stats["total_features"],
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_time": stats["elapsed_time"],
                "description": "Geohash database generated from shapefile",
            }

            with open(
                os.path.join(args.output_dir, "metadata.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            logger.info(f"Process completed successfully! Database saved to {db_path}")
            return 0

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

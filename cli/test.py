#!/usr/bin/env python3

import argparse
import os
import json
import rocksdb3
import pygeohash as geohash
import logging
from pprint import pprint

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def open_rocksdb(db_path):
    """
    RocksDB를 엽니다.

    Args:
        db_path: 데이터베이스 경로

    Returns:
        RocksDB 인스턴스
    """
    try:
        db = rocksdb3.open_default(db_path)
        return db

    except Exception as e:
        logger.error(f"Error opening RocksDB: {str(e)}")
        raise


def find_administrative_district(db, x, y, precision=7, key_prefix=None):
    """
    주어진 좌표에 해당하는 행정동을 찾습니다.

    Args:
        db: RocksDB 인스턴스
        x: 경도 좌표
        y: 위도 좌표
        precision: GeoHash 정밀도 (기본값: 7)
        key_prefix: 키 접두사 (기본값: None)

    Returns:
        행정동 정보 또는 None
    """
    # 좌표로부터 GeoHash 생성
    h = geohash.encode(y, x, precision)
    key = f"{key_prefix}_{h}" if key_prefix else h

    # GeoHash로 데이터베이스 조회
    value_bytes = db.get(key.encode())
    if not value_bytes:
        # 정밀도를 낮춰서 다시 시도
        for p in range(precision - 1, 0, -1):
            h = geohash.encode(y, x, p)
            key = f"{key_prefix}_{h}" if key_prefix else h
            value_bytes = db.get(key.encode())
            if value_bytes:
                break

    # 결과 처리
    if value_bytes:
        return json.loads(value_bytes)

    return None


def find_districts_with_history(db, x, y, precision=7, key_prefix=None):
    """
    주어진 좌표에 해당하는 행정동 이력을 모두 찾습니다.

    Args:
        db: RocksDB 인스턴스
        x: 경도 좌표
        y: 위도 좌표
        precision: GeoHash 정밀도 (기본값: 7)
        key_prefix: 키 접두사 (기본값: None)

    Returns:
        행정동 이력 정보 리스트
    """
    district_data = find_administrative_district(db, x, y, precision, key_prefix)

    if not district_data:
        return []

    # 항목이 리스트가 아니면 리스트로 변환
    if not isinstance(district_data, list):
        district_data = [district_data]

    # 시간순으로 정렬
    sorted_data = sorted(district_data, key=lambda x: x.get("from_yyyymm", "000000"))

    return sorted_data


def get_key_prefixes(db):
    """
    데이터베이스에서 사용 중인 키 접두사 목록을 가져옵니다.

    Args:
        db: RocksDB 인스턴스

    Returns:
        키 접두사 목록
    """
    prefixes = set()

    it = db.iterkeys()
    it.seek_to_first()

    # 최대 1000개 키만 검사
    count = 0
    for key_bytes in it:
        if count > 1000:
            break

        key = key_bytes.decode("utf-8", errors="ignore")
        parts = key.split("_", 1)

        if len(parts) > 1:
            prefixes.add(parts[0])

        count += 1

    return list(prefixes)


def contains(x: float, y: float, intersection_wkt: str) -> bool:
    """
    주어진 좌표가 WKT 형식의 폴리곤 내에 포함되어 있는지 확인합니다.

    Args:
        x: 경도 좌표
        y: 위도 좌표
        intersection_wkt: WKT 형식의 폴리곤 문자열

    Returns:
        폴리곤 내에 점이 포함되어 있으면 True, 그렇지 않으면 False
    """
    if not intersection_wkt:
        return False

    try:
        from shapely.geometry import Point
        from shapely import wkt

        # 좌표로부터 Point 객체 생성
        point = Point(x, y)

        # WKT 문자열을 shapely 지오메트리로 변환
        geom = wkt.loads(intersection_wkt)

        # 점이 폴리곤 내에 있는지 확인
        return geom.contains(point)
    except Exception as e:
        logger.error(f"Error checking if point is in polygon: {str(e)}")
        return False


def main():
    # 명령줄 인수 파싱
    parser = argparse.ArgumentParser(
        description="Test administrative district lookup by coordinates"
    )
    parser.add_argument("--base", required=True, help="Base RocksDB path")
    parser.add_argument(
        "--x", type=float, required=True, help="Longitude coordinate (X)"
    )
    parser.add_argument(
        "--y", type=float, required=True, help="Latitude coordinate (Y)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output"
    )

    args = parser.parse_args()

    # 좌표 유효성 확인
    if not (-180 <= args.x <= 180) or not (-90 <= args.y <= 90):
        logger.error(
            "Invalid coordinates. Longitude (x) must be between -180 and 180, and Latitude (y) must be between -90 and 90."
        )
        return 1

    try:
        # 데이터베이스 열기
        db = open_rocksdb(args.base)

        # GeoHash 생성 및 표시
        precision = 7  # 기본 정밀도
        key_prefix = None  # 키 접두사 기본값
        h = geohash.encode(args.y, args.x, precision)
        key = h
        logger.info(f"Generated GeoHash: {h}")
        logger.info(f"Database lookup key: {key}")

        # 행정동 이력 검색
        districts = find_districts_with_history(
            db, args.x, args.y, precision, key_prefix
        )

        # 결과 출력
        if not districts:
            print("\n❌ No administrative district found for the given coordinates.")
        else:
            print(f"\n✅ Found {len(districts)} administrative district record(s):")

            for i, district in enumerate(districts):
                print(f"\n🏙️ District Record #{i+1}:")

                # 핵심 정보 간단히 출력
                print(f"  📍 Name: {district.get('EMD_KOR_NM', 'N/A')}")
                print(f"  🏢 Code: {district.get('EMD_CD', 'N/A')}")
                print(
                    f"  📅 Valid period: {district.get('from_yyyymm', 'N/A')} to {district.get('to_yyyymm', 'N/A')}"
                )

                # contains test
                if contains(args.x, args.y, district.get("intersection_wkt")):
                    print("  ✅ Point is inside the polygon")
                else:
                    print("  ❌ Point is outside the polygon")

                # 자세한 정보는 verbose 모드에서만 출력
                if args.verbose:
                    print("\n  📋 Full details:")
                    pprint(district)

        # 현재 유효한 행정동 정보 표시
        current_district = next(
            (d for d in districts if d.get("to_yyyymm", "999999") == "999999"), None
        )
        if current_district:
            print("\n🌟 Currently valid administrative district:")
            print(f"  📍 Name: {current_district.get('EMD_KOR_NM', 'N/A')}")
            print(f"  🏢 Code: {current_district.get('EMD_CD', 'N/A')}")
            print(f"  📅 Valid since: {current_district.get('from_yyyymm', 'N/A')}")

        return 0

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())

#!/usr/bin/env python3

import argparse
import os
import json
import time
import logging

# import rocksdb3
import sys
import os

# Add the parent directory of 'src' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.geocoder.db.gimi9_rocks import Gimi9RocksDB

from tqdm import tqdm
import sys

"""
# merge
과거부터 차례대로 merge

python merge_geohash.py \
  --base=/path/to/output/merged_db \
  --input=/path/to/input/db1 /path/to/input/db2 /path/to/input/db3

value: [
            {
                EMD_CD
                EMD_KOR_NM
                EMD_ENG_NM
                from_yyyymm
                to_yyyymm
                intersection_wkt
            },
            {}, ...
        ]

문제를 단순화하기 위해서 yyyymm 순서대로 merge 진행

추출
1. key로 검색하여 EMD_CD가, EMD_KOR_NM 같은 것들 추출
2. to_yyyymm이 가장 큰 item 1개 추출

3. item 없으면 추가
4. item 있으면 intersection_wkt 비교

5. intersection_wkt가 다르면 추가
6. intersection_wkt가 같으면 item의 to_yyyymm 업데이트

input: base db 경로
output: 추가할 db 경로

"""


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


def get_latest_item(items, yyyymm_field="to_yyyymm"):
    """
    to_yyyymm이 가장 최신인 항목을 반환합니다.

    Args:
        items: 항목 리스트
        yyyymm_field: 년월 필드명 (기본값: 'to_yyyymm')

    Returns:
        to_yyyymm이 가장 큰 항목
    """
    if not items:
        return None

    # 단일 항목인 경우 리스트로 변환
    if not isinstance(items, list):
        return items

    # to_yyyymm 기준으로 정렬
    sorted_items = sorted(
        items, key=lambda x: x.get(yyyymm_field, "000000"), reverse=True
    )

    return sorted_items[0] if sorted_items else None


def find_matching_items(existing_data, new_item, fields=None):
    """
    기존 데이터에서 지정된 필드값이 일치하는 항목들을 찾습니다.

    Args:
        existing_data: 기존 데이터 (단일 항목 또는 항목 리스트)
        new_item: 비교할 새 항목
        fields: 비교할 필드명 리스트 (기본값: ['EMD_CD', 'EMD_KOR_NM'])

    Returns:
        일치하는 항목들의 리스트
    """
    if fields is None:
        fields = ["EMD_CD", "EMD_KOR_NM"]

    # 기존 데이터가 없으면 빈 리스트 반환
    if not existing_data:
        return []

    # 단일 항목인 경우 리스트로 변환
    if not isinstance(existing_data, list):
        existing_data = [existing_data]

    matching_items = []

    for item in existing_data:
        match = True
        for field in fields:
            if item.get(field) != new_item.get(field):
                match = False
                break

        if match:
            matching_items.append(item)

    return matching_items


def update_yyymm(new_data, input_yyyymm):
    for item in new_data:
        item["from_yyyymm"] = input_yyyymm
        item["to_yyyymm"] = input_yyyymm


def merge_geohash_dbs(base_db_path, input_db_paths):
    """
    여러 geohash 데이터베이스를 병합합니다.

    Args:
        base_db_path: 기본 데이터베이스 경로 (결과가 저장될 위치)
        input_db_paths: 추가될 데이터베이스 경로 리스트

    Returns:
        병합 통계 정보
    """
    # 기본 데이터베이스 열기 (없으면 생성)
    base_db = open_rocksdb(base_db_path)

    stats = {
        "total_keys_processed": 0,
        "new_keys_added": 0,
        "updated_keys": 0,
        "start_time": time.time(),
    }

    # 입력 데이터베이스 순회
    for input_path in input_db_paths:
        logger.info(f"Processing database: {input_path}")

        try:
            input_db = open_rocksdb(input_path, create_if_missing=False)

            # 입력 DB의 키 개수 가져오기
            # it = input_db.iterkeys()
            # it.seek_to_first()
            # key_count = sum(1 for _ in it)
            key_count = json.loads(input_db.get(b"__metadata__").decode()).get(
                "count", 0
            )

            # 진행 상황 표시를 위한 tqdm 초기화
            # it = input_db.iterkeys()
            # it.seek_to_first()

            # WriteBatch 초기화
            # wb = rocksdb.WriteBatch()
            batch_count = 0

            # 모든 키 처리
            for key, val in tqdm(
                input_db,
                # input_db.get_iter(),
                total=key_count,
                desc=f"Merging {os.path.basename(input_path)}",
            ):
                key_bytes = key
                # 메타데이터 키 건너뛰기
                if key_bytes == "__metadata__":
                    continue

                # 입력 DB에서 값 가져오기
                value_bytes = val
                if not value_bytes:
                    continue

                new_data = json.loads(value_bytes)
                input_yyyymm = input_path.split("/")[-4]  # 예: 202305
                update_yyymm(new_data, input_yyyymm)

                # 기본 DB에서 값 가져오기
                base_value_bytes = base_db.get(key_bytes)

                if not base_value_bytes:
                    # 기본 DB에 해당 키가 없으면 그대로 추가
                    base_db.put(key_bytes, json.dumps(new_data).encode())
                    stats["new_keys_added"] += 1
                else:
                    # 기존 데이터와 병합
                    existing_data = json.loads(base_value_bytes)
                    merged_data = merge_data(existing_data, new_data)
                    base_db.put(key_bytes, json.dumps(merged_data).encode())
                    stats["updated_keys"] += 1

                # batch_count += 1
                stats["total_keys_processed"] += 1
                # for key_bytes in tqdm(
                #     it, total=key_count, desc=f"Merging {os.path.basename(input_path)}"
                # ):

                # # 일정 크기마다 배치 쓰기
                # if batch_count >= 1000:
                #     base_db.write(wb)
                #     wb = rocksdb.WriteBatch()
                #     batch_count = 0

            # # 남은 배치 쓰기
            # if batch_count > 0:
            #     base_db.write(wb)

            # 메타데이터 업데이트
            update_metadata(base_db, input_db)

        except Exception as e:
            logger.error(f"Error processing database {input_path}: {str(e)}")
            continue

    # 통계 계산
    stats["end_time"] = time.time()
    stats["elapsed_time"] = stats["end_time"] - stats["start_time"]

    logger.info(f"Merge completed. Processed {stats['total_keys_processed']} keys.")
    logger.info(
        f"Added {stats['new_keys_added']} new keys, updated {stats['updated_keys']} existing keys."
    )
    logger.info(f"Time elapsed: {stats['elapsed_time']:.2f} seconds")

    return stats


def merge_data(existing_data, new_data):
    """
    기존 데이터와 새 데이터를 병합합니다.

    Args:
        existing_data: 기존 데이터 (단일 항목 또는 항목 리스트)
        new_data: 새 데이터 (단일 항목 또는 항목 리스트)

    Returns:
        병합된 데이터 리스트
    """
    # 단일 항목인 경우 리스트로 변환
    if not isinstance(existing_data, list):
        existing_data = [existing_data]

    if not isinstance(new_data, list):
        new_data = [new_data]

    result = existing_data.copy()

    for new_item in new_data:
        # EMD_CD와 EMD_KOR_NM이 같은 항목들 찾기
        matching_items = find_matching_items(existing_data, new_item)

        if not matching_items:
            # 일치하는 항목이 없으면 새로 추가
            result.append(new_item)
        else:
            # 일치하는 항목 중 to_yyyymm이 가장 큰 항목 찾기
            latest_item = get_latest_item(matching_items)

            # intersection_wkt 비교
            if latest_item.get("intersection_wkt") != new_item.get("intersection_wkt"):
                # 다르면 새로 추가
                result.append(new_item)
            else:
                # 같으면 to_yyyymm만 업데이트
                latest_item["to_yyyymm"] = new_item.get("from_yyyymm")

    return result


def update_metadata(base_db: Gimi9RocksDB, input_db):
    """
    데이터베이스 메타데이터를 업데이트합니다.

    Args:
        base_db: 기본 데이터베이스
        input_db: 입력 데이터베이스
    """
    try:
        # 기존 메타데이터 가져오기
        base_metadata_bytes = base_db.get(b"__metadata__")
        input_metadata_bytes = input_db.get(b"__metadata__")

        if base_metadata_bytes and input_metadata_bytes:
            base_metadata = json.loads(base_metadata_bytes)
            input_metadata = json.loads(input_metadata_bytes)

            # 메타데이터 병합
            merged_metadata = base_metadata.copy()

            # 카운트 업데이트
            if "count" in base_metadata and "count" in input_metadata:
                # 정확한 개수는 이미 위에서 키를 모두 처리하며 계산됨
                # it = base_db.get_iter()
                # it.seek_to_first()
                count = sum(1 for k in base_db if k != b"__metadata__")
                merged_metadata["count"] = count

            # 피처 개수 병합
            if "features" in base_metadata and "features" in input_metadata:
                merged_metadata["features"] = (
                    base_metadata["features"] + input_metadata["features"]
                )

            # 업데이트 시간
            merged_metadata["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

            # # 원본 DB 리스트 추가
            # if "source_dbs" not in merged_metadata:
            #     merged_metadata["source_dbs"] = []

            # # 입력 DB 경로 추가
            # input_path = (
            #     input_db.path.decode() if hasattr(input_db, "path") else "unknown"
            # )
            # if input_path not in merged_metadata["source_dbs"]:
            #     merged_metadata["source_dbs"].append(input_path)

            # 메타데이터 저장
            base_db.put(b"__metadata__", json.dumps(merged_metadata).encode())

        elif input_metadata_bytes:
            # 기본 DB에 메타데이터가 없는 경우 입력 DB의 메타데이터 사용
            base_db.put(b"__metadata__", input_metadata_bytes)

    except Exception as e:
        logger.error(f"Error updating metadata: {str(e)}")


def main():
    # 명령줄 인수 파싱
    parser = argparse.ArgumentParser(
        description="Merge multiple geohash databases into one"
    )
    parser.add_argument("--base", required=True, help="Base database path (output)")
    parser.add_argument(
        "--input", required=True, nargs="+", help="Input database paths to merge"
    )

    args = parser.parse_args()

    # 입력 확인
    for path in args.input:
        if not os.path.exists(path):
            logger.error(f"Error: Database path {path} does not exist")
            return 1

    try:
        # 기본 DB 경로 생성
        os.makedirs(os.path.dirname(args.base), exist_ok=True)

        # 데이터베이스 병합
        stats = merge_geohash_dbs(args.base, args.input)

        logger.info("Process completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

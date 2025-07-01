#!/usr/bin/env python3
"""
RocksDB Python 바인딩 사용 예제
GIL-free 연산을 통한 고성능 키-값 저장소
"""

import src.geocoder.db.gimi9_rocks as gimi9_rocks
import tempfile
import os
import shutil
import json


def simple_example():
    """간단한 사용 예제"""
    # 임시 DB 경로
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "my_database")

        # DB 열기
        db = gimi9_rocks.RocksDB(db_path)

        # 데이터 저장
        db.put("hello", "world")
        db.put("python", "rocks")

        # 데이터 조회
        print(db.get("hello"))  # "world"
        print(db.get("python"))  # "rocks"
        print(db.get("missing"))  # None

        # 데이터 삭제
        db.delete("hello")
        print(db.get("hello"))  # None


def json_storage_example():
    """JSON 데이터 저장 예제"""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "json_db")
        db = gimi9_rocks.RocksDB(db_path)

        # JSON 데이터 저장
        user_data = {
            "id": 1001,
            "name": "김철수",
            "email": "kim@example.com",
            "age": 30,
        }

        db.put("user:1001", json.dumps(user_data, ensure_ascii=False))

        # JSON 데이터 조회
        stored_data = db.get("user:1001")
        if stored_data:
            user = json.loads(stored_data)
            print(f"사용자: {user['name']} ({user['email']})")


if __name__ == "__main__":
    print("=== 간단한 예제 ===")
    simple_example()

    print("\n=== JSON 저장 예제 ===")
    json_storage_example()

#!/usr/bin/env python3
"""
gimi9_rocks Cython 확장 테스트
"""

import os
import tempfile
import shutil
from src.geocoder.db.gimi9_rocks import Gimi9RocksDB, RocksDBError, create_db


def test_basic_operations():
    """기본 동작 테스트"""
    # 임시 데이터베이스 경로
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_db")

    try:
        # 컨텍스트 매니저 사용
        with Gimi9RocksDB() as db:
            db.open(db_path)

            # 데이터 저장
            db.put("key1", "value1")
            db.put("key2", "한글 값")
            db.put(b"binary_key", b"binary_value")

            # 데이터 조회
            assert db.get_string("key1") == "value1"
            assert db.get_string("key2") == "한글 값"
            assert db.get(b"binary_key") == b"binary_value"

            # 존재하지 않는 키
            assert db.get("nonexistent") is None
            assert db.get_string("nonexistent") is None

            # 데이터 삭제
            db.delete("key1")
            assert db.get_string("key1") is None

            print("✓ 기본 동작 테스트 통과")

    except Exception as e:
        print(f"✗ 기본 동작 테스트 실패: {e}")
        raise
    finally:
        # 임시 디렉토리 정리
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_create_db_function():
    """create_db 편의 함수 테스트"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_db2")

    try:
        with create_db(db_path) as db:
            db.put("test", "success")
            assert db.get_string("test") == "success"
            print("✓ create_db 함수 테스트 통과")

    except Exception as e:
        print(f"✗ create_db 함수 테스트 실패: {e}")
        raise
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_error_handling():
    """오류 처리 테스트"""
    try:
        # 존재하지 않는 경로로 데이터베이스 열기 시도
        db = Gimi9RocksDB()

        # 열지 않고 작업 시도
        try:
            db.put("key", "value")
            assert False, "예외가 발생해야 함"
        except RocksDBError:
            print("✓ 미개방 데이터베이스 오류 처리 통과")

    except Exception as e:
        print(f"✗ 오류 처리 테스트 실패: {e}")
        raise


if __name__ == "__main__":
    print("Gimi9RocksDB Cython 확장 테스트 시작...")

    try:
        test_basic_operations()
        test_create_db_function()
        test_error_handling()
        print("\n🎉 모든 테스트 통과!")

    except Exception as e:
        print(f"\n💥 테스트 실패: {e}")
        exit(1)

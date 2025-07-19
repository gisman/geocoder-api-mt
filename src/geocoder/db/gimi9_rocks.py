#!/usr/bin/env python3
"""
gimi9_rocks.py - RocksDB 라이브러리 관련 유틸리티 모듈

이 모듈은 RocksDB 라이브러리와 관련된 기능을 제공합니다.
librocksdb.so 라이브러리를 사용하여 데이터베이스 작업을 지원합니다.
"""

import os
import ctypes
from ctypes import c_char_p, c_void_p, c_size_t, c_int, POINTER
from typing import Optional, Union, Dict, Any
import threading
from .base import DbBase
from src import config


class RocksDBError(Exception):
    """RocksDB 관련 예외 클래스"""

    pass


class RocksDBLibrary:
    """RocksDB 라이브러리 싱글톤 클래스"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        lib_path = "lib/librocksdb.so"

        if not os.path.exists(lib_path):
            raise RocksDBError(f"RocksDB 라이브러리를 찾을 수 없습니다: {lib_path}")

        try:
            self.lib = ctypes.CDLL(lib_path)
        except OSError as e:
            raise RocksDBError(f"RocksDB 라이브러리 로드 실패: {e}")

        self._setup_functions()
        self._initialized = True

    def _setup_functions(self):
        """RocksDB C API 함수들을 설정"""
        try:
            # 메모리 해제 함수 (중요!)
            self.lib.rocksdb_free.restype = None
            self.lib.rocksdb_free.argtypes = [c_void_p]

            # WriteBatch 관련
            self.lib.rocksdb_writebatch_create.restype = c_void_p
            self.lib.rocksdb_writebatch_create.argtypes = []

            self.lib.rocksdb_writebatch_destroy.restype = None
            self.lib.rocksdb_writebatch_destroy.argtypes = [c_void_p]

            self.lib.rocksdb_writebatch_put.restype = None
            self.lib.rocksdb_writebatch_put.argtypes = [
                c_void_p,
                c_char_p,
                c_size_t,
                c_char_p,
                c_size_t,
            ]

            self.lib.rocksdb_writebatch_delete.restype = None
            self.lib.rocksdb_writebatch_delete.argtypes = [c_void_p, c_char_p, c_size_t]

            self.lib.rocksdb_writebatch_clear.restype = None
            self.lib.rocksdb_writebatch_clear.argtypes = [c_void_p]

            # WriteOptions 관련
            self.lib.rocksdb_writeoptions_create.restype = c_void_p
            self.lib.rocksdb_writeoptions_create.argtypes = []

            self.lib.rocksdb_writeoptions_destroy.restype = None
            self.lib.rocksdb_writeoptions_destroy.argtypes = [c_void_p]

            # Write 관련
            self.lib.rocksdb_write.restype = None
            self.lib.rocksdb_write.argtypes = [
                c_void_p,
                c_void_p,
                c_void_p,
                POINTER(c_char_p),
            ]

            # Options 관련
            self.lib.rocksdb_options_create.restype = c_void_p
            self.lib.rocksdb_options_create.argtypes = []

            self.lib.rocksdb_options_destroy.restype = None
            self.lib.rocksdb_options_destroy.argtypes = [c_void_p]

            self.lib.rocksdb_options_set_create_if_missing.restype = None
            self.lib.rocksdb_options_set_create_if_missing.argtypes = [c_void_p, c_int]

            # DB 관련
            self.lib.rocksdb_open.restype = c_void_p
            self.lib.rocksdb_open.argtypes = [c_void_p, c_char_p, POINTER(c_char_p)]

            # OpenForReadOnly
            self.lib.rocksdb_open_for_read_only.restype = c_void_p
            self.lib.rocksdb_open_for_read_only.argtypes = [
                c_void_p,
                c_char_p,
                POINTER(c_char_p),
            ]

            # rocksdb_open_as_secondary
            self.lib.rocksdb_open_as_secondary.restype = c_void_p
            self.lib.rocksdb_open_as_secondary.argtypes = [
                c_void_p,  # const rocksdb_options_t* options
                c_char_p,  # const char* name
                c_char_p,  # const char* secondary_path
                POINTER(c_char_p),  # char** errptr
            ]

            self.lib.rocksdb_close.restype = None
            self.lib.rocksdb_close.argtypes = [c_void_p]

            # Get/Put/Delete 관련
            self.lib.rocksdb_get.restype = c_void_p
            # self.lib.rocksdb_get.restype = c_char_p
            self.lib.rocksdb_get.argtypes = [
                c_void_p,
                c_void_p,
                c_char_p,
                c_size_t,
                POINTER(c_size_t),
                POINTER(c_char_p),
            ]

            self.lib.rocksdb_put.restype = None
            self.lib.rocksdb_put.argtypes = [
                c_void_p,
                c_void_p,
                c_char_p,
                c_size_t,
                c_char_p,
                c_size_t,
                POINTER(c_char_p),
            ]

            self.lib.rocksdb_delete.restype = None
            self.lib.rocksdb_delete.argtypes = [
                c_void_p,
                c_void_p,
                c_char_p,
                c_size_t,
                POINTER(c_char_p),
            ]

            # ReadOptions/WriteOptions
            self.lib.rocksdb_readoptions_create.restype = c_void_p
            self.lib.rocksdb_readoptions_create.argtypes = []

            self.lib.rocksdb_readoptions_destroy.restype = None
            self.lib.rocksdb_readoptions_destroy.argtypes = [c_void_p]

            self.lib.rocksdb_writeoptions_create.restype = c_void_p
            self.lib.rocksdb_writeoptions_create.argtypes = []

            self.lib.rocksdb_writeoptions_destroy.restype = None
            self.lib.rocksdb_writeoptions_destroy.argtypes = [c_void_p]

            # Iterator 관련
            self.lib.rocksdb_create_iterator.restype = c_void_p
            self.lib.rocksdb_create_iterator.argtypes = [c_void_p, c_void_p]

            self.lib.rocksdb_iter_destroy.restype = None
            self.lib.rocksdb_iter_destroy.argtypes = [c_void_p]

            self.lib.rocksdb_iter_seek.restype = None
            self.lib.rocksdb_iter_seek.argtypes = [c_void_p, c_char_p, c_size_t]

            self.lib.rocksdb_iter_seek_to_first.restype = None
            self.lib.rocksdb_iter_seek_to_first.argtypes = [c_void_p]

            self.lib.rocksdb_iter_valid.restype = c_int
            self.lib.rocksdb_iter_valid.argtypes = [c_void_p]

            self.lib.rocksdb_iter_next.restype = None
            self.lib.rocksdb_iter_next.argtypes = [c_void_p]

            self.lib.rocksdb_iter_key.restype = c_char_p
            self.lib.rocksdb_iter_key.argtypes = [c_void_p, POINTER(c_size_t)]

            self.lib.rocksdb_iter_value.restype = c_char_p
            self.lib.rocksdb_iter_value.argtypes = [c_void_p, POINTER(c_size_t)]

            # Flush 관련
            self.lib.rocksdb_flushoptions_create.restype = c_void_p
            self.lib.rocksdb_flushoptions_create.argtypes = []

            self.lib.rocksdb_flushoptions_destroy.restype = None
            self.lib.rocksdb_flushoptions_destroy.argtypes = [c_void_p]

            self.lib.rocksdb_flush.restype = None
            self.lib.rocksdb_flush.argtypes = [c_void_p, c_void_p, POINTER(c_char_p)]

            # 메모리 해제
            self.lib.rocksdb_free.restype = None
            self.lib.rocksdb_free.argtypes = [c_void_p]

        except AttributeError as e:
            raise RocksDBError(f"RocksDB 함수 설정 실패: {e}")


class WriteBatch:
    """RocksDB WriteBatch 래퍼 클래스"""

    batch = None

    def __init__(self):
        """
        WriteBatch 초기화

        Args:
            lib: RocksDB ctypes 라이브러리 인스턴스
        """
        # lib_path: str = "lib/librocksdb.so"

        # if lib_path is None:
        #     # 현재 파일 기준으로 lib 디렉토리의 librocksdb.so 찾기
        #     current_dir = os.path.dirname(os.path.abspath(__file__))
        #     lib_path = os.path.join(
        #         os.path.dirname(current_dir), "lib", "librocksdb.so"
        #     )

        # if not os.path.exists(lib_path):
        #     raise RocksDBError(f"RocksDB 라이브러리를 찾을 수 없습니다: {lib_path}")

        # try:
        #     self.lib = ctypes.CDLL(lib_path)
        # except OSError as e:
        #     raise RocksDBError(f"RocksDB 라이브러리 로드 실패: {e}")

        self.lib_instance = RocksDBLibrary()
        self.lib = self.lib_instance.lib
        self.batch = None
        self._is_destroyed = False
        # self._setup_functions()
        self._create_batch()

    def _create_batch(self):
        """WriteBatch 인스턴스 생성"""
        if self._is_destroyed:
            raise RocksDBError("WriteBatch가 이미 해제되었습니다")

        self.batch = self.lib.rocksdb_writebatch_create()
        if not self.batch:
            raise RocksDBError("WriteBatch 생성 실패")

    def put(self, key: Union[str, bytes], value: Union[str, bytes]):
        """
        배치에 PUT 작업 추가

        Args:
            key: 저장할 키
            value: 저장할 값
        """
        if self._is_destroyed or not self.batch:
            raise RocksDBError("WriteBatch가 유효하지 않습니다")

        key_bytes = key.encode("utf-8") if isinstance(key, str) else key
        value_bytes = value.encode("utf-8") if isinstance(value, str) else value

        self.lib.rocksdb_writebatch_put(
            self.batch, key_bytes, len(key_bytes), value_bytes, len(value_bytes)
        )

    def delete(self, key: Union[str, bytes]):
        """
        배치에 DELETE 작업 추가

        Args:
            key: 삭제할 키
        """
        if self._is_destroyed or not self.batch:
            raise RocksDBError("WriteBatch가 유효하지 않습니다")

        key_bytes = key.encode("utf-8") if isinstance(key, str) else key

        self.lib.rocksdb_writebatch_delete(self.batch, key_bytes, len(key_bytes))

    def clear(self):
        """배치의 모든 작업 제거"""
        if self._is_destroyed or not self.batch:
            return

        self.lib.rocksdb_writebatch_clear(self.batch)

    def destroy(self):
        """WriteBatch 리소스 해제"""
        if not self._is_destroyed and self.batch:
            self.lib.rocksdb_writebatch_destroy(self.batch)
            self.batch = None
            self._is_destroyed = True

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.destroy()

    def __del__(self):
        """소멸자"""
        self.destroy()


class Gimi9RocksDB(DbBase):
    """RocksDB 래퍼 클래스"""

    db = None
    options = None

    # def __init__(self, db_name, **kwargs):
    def __init__(self, db_name: str, **kwargs):
        """
        RocksDB 초기화

        Args:
            lib_path: librocksdb.so 파일 경로 (기본값: ../lib/librocksdb.so)
        """
        # lib_path: str = "lib/librocksdb.so"

        # if lib_path is None:
        #     # 현재 파일 기준으로 lib 디렉토리의 librocksdb.so 찾기
        #     current_dir = os.path.dirname(os.path.abspath(__file__))
        #     lib_path = os.path.join(
        #         os.path.dirname(current_dir), "lib", "librocksdb.so"
        #     )

        # if not os.path.exists(lib_path):
        #     raise RocksDBError(f"RocksDB 라이브러리를 찾을 수 없습니다: {lib_path}")

        # try:
        #     self.lib = ctypes.CDLL(lib_path)
        # except OSError as e:
        #     raise RocksDBError(f"RocksDB 라이브러리 로드 실패: {e}")

        self.lib_instance = RocksDBLibrary()
        self.lib = self.lib_instance.lib

        self.db = None
        # self.options = None
        # self._setup_functions()
        self.open(db_name, **kwargs)

    def open(
        self,
        db_path: str,
        create_if_missing: bool = True,
        read_only: bool = False,
        open_secondary: bool = False,
        secondary_path: Optional[str] = None,
    ) -> None:
        """
        데이터베이스 열기

        Args:
            db_path: 데이터베이스 경로
            create_if_missing: 데이터베이스가 없으면 생성할지 여부
        """
        if self.db is not None:
            self.close()

        self.read_only = read_only

        # Options 생성
        self.options = self.lib.rocksdb_options_create()
        if not read_only and create_if_missing:
            self.lib.rocksdb_options_set_create_if_missing(self.options, 1)

        # DB 열기
        err = c_char_p()
        if open_secondary:
            # 읽기 전용 모드에서 secondary DB 열기
            self.db = self.lib.rocksdb_open_as_secondary(
                self.options,
                db_path.encode("utf-8"),
                secondary_path.encode("utf-8"),
                ctypes.byref(err),
            )
            self.secondary_path = secondary_path
        else:
            if read_only:
                self.db = self.lib.rocksdb_open_for_read_only(
                    self.options, db_path.encode("utf-8"), ctypes.byref(err)
                )
            else:
                self.db = self.lib.rocksdb_open(
                    self.options, db_path.encode("utf-8"), ctypes.byref(err)
                )

        if err.value:
            error_msg = err.value.decode("utf-8")
            self.lib.rocksdb_free(err)
            raise RocksDBError(f"데이터베이스 열기 실패: {error_msg}")

        print(f"RocksDB 데이터베이스 열기 성공: {db_path}")

    def __iter__(self):
        """
        데이터베이스의 모든 키-값 쌍을 순회하는 이터레이터 반환

        Returns:
            이터레이터: (key, value) 튜플의 이터레이터
        """
        if self.db is None:
            raise RocksDBError("데이터베이스가 열려있지 않습니다")

        # ReadOptions 생성
        read_options = self.lib.rocksdb_readoptions_create()

        it = None
        try:
            it = self.lib.rocksdb_create_iterator(self.db, read_options)
            if not it:
                raise RocksDBError("Iterator 생성 실패")

            self.lib.rocksdb_iter_seek_to_first(it)

            while self.lib.rocksdb_iter_valid(it):
                key_len = c_size_t()
                value_len = c_size_t()

                key_ptr = self.lib.rocksdb_iter_key(it, ctypes.byref(key_len))
                value_ptr = self.lib.rocksdb_iter_value(it, ctypes.byref(value_len))

                key = ctypes.string_at(key_ptr, key_len.value)
                value = ctypes.string_at(value_ptr, value_len.value)

                yield key.decode("utf-8"), value.decode("utf-8")

                self.lib.rocksdb_iter_next(it)

        finally:
            self.lib.rocksdb_readoptions_destroy(read_options)
            if it:
                self.lib.rocksdb_iter_destroy(it)

    def next(self, it) -> Optional[tuple]:
        """
        이터레이터의 다음 키-값 쌍을 반환

        Args:
            it: RocksDB 이터레이터 객체

        Returns:
            다음 (key, value) 튜플 또는 None
        """
        if not it:
            return None

        if not self.lib.rocksdb_iter_valid(it):
            self.lib.rocksdb_iter_destroy(it)
            return None

        key_len = c_size_t()
        value_len = c_size_t()
        key_ptr = self.lib.rocksdb_iter_key(it, ctypes.byref(key_len))
        value_ptr = self.lib.rocksdb_iter_value(it, ctypes.byref(value_len))
        key = ctypes.string_at(key_ptr, key_len.value)
        value = ctypes.string_at(value_ptr, value_len.value)

        self.lib.rocksdb_iter_next(it)

        return key.decode("utf-8"), value.decode("utf-8")

    def seek(self, key: Union[str, bytes]):
        if self.db is None:
            raise RocksDBError("데이터베이스가 열려있지 않습니다")

        # ReadOptions 생성
        read_options = self.lib.rocksdb_readoptions_create()

        it = None
        try:
            it = self.lib.rocksdb_create_iterator(self.db, read_options)
            if not it:
                raise RocksDBError("Iterator 생성 실패")

            self.lib.rocksdb_iter_seek(
                it, key.encode("utf-8") if isinstance(key, str) else key, len(key)
            )
            if self.lib.rocksdb_iter_valid(it):
                return it
            else:
                self.lib.rocksdb_iter_destroy(it)
                return None
        except Exception as e:
            if it:
                self.lib.rocksdb_iter_destroy(it)
            raise RocksDBError(f"Iterator 생성 중 오류 발생: {e}")

    def put(self, key: Union[str, bytes], value: Union[str, bytes]) -> None:
        """
        키-값 쌍 저장

        Args:
            key: 저장할 키
            value: 저장할 값
        """
        if self.db is None:
            raise RocksDBError("데이터베이스가 열려있지 않습니다")

        if self.read_only:
            # return None
            raise RocksDBError("읽기 전용 모드에서는 데이터를 저장할 수 없습니다")

        # 문자열을 바이트로 변환
        key_bytes = key.encode("utf-8") if isinstance(key, str) else key
        value_bytes = value.encode("utf-8") if isinstance(value, str) else value

        # WriteOptions 생성
        write_options = self.lib.rocksdb_writeoptions_create()

        try:
            err = c_char_p()
            self.lib.rocksdb_put(
                self.db,
                write_options,
                key_bytes,
                len(key_bytes),
                value_bytes,
                len(value_bytes),
                ctypes.byref(err),
            )

            if err.value:
                error_msg = err.value.decode("utf-8")
                self.lib.rocksdb_free(err)
                raise RocksDBError(f"데이터 저장 실패: {error_msg}")

        finally:
            self.lib.rocksdb_writeoptions_destroy(write_options)

    def get(self, key: Union[str, bytes]) -> Optional[bytes]:
        """
        키에 해당하는 값 조회

        Args:
            key: 조회할 키

        Returns:
            키에 해당하는 값 (없으면 None)
        """
        if self.db is None:
            raise RocksDBError("데이터베이스가 열려있지 않습니다")

        # 문자열을 바이트로 변환
        key_bytes = key.encode("utf-8") if isinstance(key, str) else key

        # ReadOptions 생성
        read_options = self.lib.rocksdb_readoptions_create()

        try:
            value_len = c_size_t()
            err = c_char_p()

            value_ptr = self.lib.rocksdb_get(
                self.db,
                read_options,
                key_bytes,
                len(key_bytes),
                ctypes.byref(value_len),
                ctypes.byref(err),
            )

            if err.value:
                error_msg = err.value.decode("utf-8")
                self.lib.rocksdb_free(err)
                raise RocksDBError(f"데이터 조회 실패: {error_msg}")

            if value_ptr:
                # 값을 복사하고 메모리 해제
                value = ctypes.string_at(value_ptr, value_len.value)
                self.lib.rocksdb_free(value_ptr)
                return value
            else:
                return None

        finally:
            self.lib.rocksdb_readoptions_destroy(read_options)

    def get_string(self, key: Union[str, bytes]) -> Optional[str]:
        """
        키에 해당하는 값을 문자열로 조회

        Args:
            key: 조회할 키

        Returns:
            키에 해당하는 값 (문자열, 없으면 None)
        """
        value = self.get(key)
        return value.decode("utf-8") if value else None

    def delete(self, key: Union[str, bytes]) -> None:
        """
        키 삭제

        Args:
            key: 삭제할 키
        """
        if self.db is None:
            raise RocksDBError("데이터베이스가 열려있지 않습니다")

        # 문자열을 바이트로 변환
        key_bytes = key.encode("utf-8") if isinstance(key, str) else key

        # WriteOptions 생성
        write_options = self.lib.rocksdb_writeoptions_create()

        try:
            err = c_char_p()
            self.lib.rocksdb_delete(
                self.db, write_options, key_bytes, len(key_bytes), ctypes.byref(err)
            )

            if err.value:
                error_msg = err.value.decode("utf-8")
                self.lib.rocksdb_free(err)
                raise RocksDBError(f"데이터 삭제 실패: {error_msg}")

        finally:
            self.lib.rocksdb_writeoptions_destroy(write_options)

    def close(self) -> None:
        """데이터베이스 닫기"""
        if self.db is not None:
            self.lib.rocksdb_close(self.db)
            self.db = None
            print("RocksDB 데이터베이스 닫기 완료")

        if self.options is not None:
            self.lib.rocksdb_options_destroy(self.options)
            self.options = None

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.close()

    def __del__(self):
        """소멸자"""
        self.close()

    def write_batch(self, write_batch, batch_operations=None):
        """
        WriteBatch를 사용하여 데이터베이스에 일괄 작업 수행

        Args:
            write_batch: WriteBatch 인스턴스
            batch_operations: 추가적인 배치 작업 (선택적)
        """
        if self.db is None:
            raise RocksDBError("데이터베이스가 열려있지 않습니다")

        # WriteOptions 생성
        write_options = self.lib.rocksdb_writeoptions_create()

        try:
            err = c_char_p()
            self.lib.rocksdb_write(
                self.db, write_options, write_batch.batch, ctypes.byref(err)
            )

            if err.value:
                error_msg = err.value.decode("utf-8")
                self.lib.rocksdb_free(err)
                raise RocksDBError(f"WriteBatch 실행 실패: {error_msg}")

            if batch_operations:
                try:
                    for op in batch_operations:
                        op()
                except Exception as e:
                    # 추가 작업 실패 시에도 리소스는 정리됨
                    raise RocksDBError(f"배치 후 작업 실패: {e}")

        finally:
            self.lib.rocksdb_writeoptions_destroy(write_options)

    def flush(self):
        """
        데이터베이스를 플러시하여 모든 변경 사항을 디스크에 기록합니다.
        """
        if self.db is None:
            raise RocksDBError("데이터베이스가 열려있지 않습니다")

        # FlushOptions 생성
        flush_options = self.lib.rocksdb_flushoptions_create()

        try:
            err = c_char_p()
            self.lib.rocksdb_flush(self.db, flush_options, ctypes.byref(err))

            if err.value:
                error_msg = err.value.decode("utf-8")
                self.lib.rocksdb_free(err)
                raise RocksDBError(f"플러시 실패: {error_msg}")

        finally:
            self.lib.rocksdb_flushoptions_destroy(flush_options)


# 편의 함수들
def create_db(db_path: str, lib_path: str = None) -> Gimi9RocksDB:
    """
    RocksDB 인스턴스 생성 및 열기

    Args:
        db_path: 데이터베이스 경로
        lib_path: librocksdb.so 파일 경로

    Returns:
        열린 RocksDB 인스턴스
    """
    db = Gimi9RocksDB(lib_path)
    db.open(db_path)
    return db


# 사용 예제
if __name__ == "__main__":
    # 사용 예제
    db_path = "/tmp/test_rocksdb"

    try:
        # 컨텍스트 매니저 사용
        with Gimi9RocksDB() as db:
            db.open(db_path)

            # 데이터 저장
            db.put("key1", "value1")
            db.put("key2", "한글 값")
            db.put(b"binary_key", b"binary_value")

            # 데이터 조회
            print("key1:", db.get_string("key1"))
            print("key2:", db.get_string("key2"))
            print("binary_key:", db.get(b"binary_key"))

            # 데이터 삭제
            db.delete("key1")
            print("key1 after delete:", db.get_string("key1"))

    except RocksDBError as e:
        print(f"RocksDB 오류: {e}")
    except Exception as e:
        print(f"일반 오류: {e}")

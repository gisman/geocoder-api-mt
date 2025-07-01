import os
import asyncpg
import logging
from typing import Optional
import src.config as config


class Database:
    """PostgreSQL 데이터베이스 연결을 관리하는 클래스"""

    _pool: Optional[asyncpg.Pool] = None

    @staticmethod
    async def _setup_connection(connection):
        """
        각 데이터베이스 연결에 대한 설정을 수행하는 함수입니다.
        기본 스키마를 geocode_dj로 설정합니다.
        """
        await connection.execute("SET search_path TO geocode_dj")

    @classmethod
    async def create_pool(cls, min_size=5, max_size=10):
        """
        데이터베이스 연결 풀 생성

        Args:
            min_size: 풀 최소 크기
            max_size: 풀 최대 크기
        """
        if cls._pool is None:
            try:
                cls._pool = await asyncpg.create_pool(
                    user=config.DATABASE_USER,
                    password=config.DATABASE_PASSWORD,
                    database=config.DATABASE_NAME,
                    host=config.DATABASE_HOST,
                    port=config.DATABASE_PORT,
                    min_size=min_size,
                    max_size=max_size,
                    command_timeout=60,
                    statement_cache_size=0,  # 선택적: 캐시 제한
                    setup=cls._setup_connection,  # 연결 설정 함수 추가
                )
                logging.info(
                    f"PostgreSQL connection pool created with size {min_size}-{max_size}, default schema: geocode_dj"
                )
            except Exception as e:
                logging.error(f"Failed to create connection pool: {str(e)}")
                raise

    @classmethod
    async def close_pool(cls):
        """데이터베이스 연결 풀 종료"""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logging.info("PostgreSQL connection pool closed")

    @classmethod
    async def get_pool(cls):
        """
        연결 풀 반환 (없으면 생성)
        """
        if cls._pool is None:
            await cls.create_pool()
        return cls._pool

    @classmethod
    async def execute(cls, query: str, *args, timeout: float = None):
        """
        SQL 실행 (INSERT, UPDATE, DELETE)

        Args:
            query: SQL 쿼리
            *args: 쿼리 파라미터
            timeout: 쿼리 타임아웃(초)

        Returns:
            실행 결과
        """
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            return await connection.execute(query, *args, timeout=timeout)

    @classmethod
    async def fetch(cls, query: str, *args, timeout: float = None):
        """
        여러 행 조회

        Args:
            query: SQL 쿼리
            *args: 쿼리 파라미터
            timeout: 쿼리 타임아웃(초)

        Returns:
            조회 결과 행 리스트
        """
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            return await connection.fetch(query, *args, timeout=timeout)

    @classmethod
    async def fetchrow(cls, query: str, *args, timeout: float = None):
        """
        단일 행 조회

        Args:
            query: SQL 쿼리
            *args: 쿼리 파라미터
            timeout: 쿼리 타임아웃(초)

        Returns:
            조회 결과 행(없으면 None)
        """
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            return await connection.fetchrow(query, *args, timeout=timeout)

    @classmethod
    async def fetchval(cls, query: str, *args, column: int = 0, timeout: float = None):
        """
        단일 값 조회

        Args:
            query: SQL 쿼리
            *args: 쿼리 파라미터
            column: 반환할 열 번호
            timeout: 쿼리 타임아웃(초)

        Returns:
            조회 결과 값(없으면 None)
        """
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            return await connection.fetchval(
                query, *args, column=column, timeout=timeout
            )

    @classmethod
    async def transaction(cls):
        """
        트랜잭션 컨텍스트 매니저 반환

        사용 예:
        async with Database.transaction() as connection:
            await connection.execute("INSERT INTO ...")
            await connection.execute("UPDATE ...")
        """
        pool = await cls.get_pool()
        connection = await pool.acquire()
        tr = connection.transaction()
        await tr.start()

        try:
            yield connection
            await tr.commit()
        except Exception:
            await tr.rollback()
            raise
        finally:
            await pool.release(connection)

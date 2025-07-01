import src.geocoder.db.gimi9_rocks as gimi9_rocks
import tempfile
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor


def threading_test():
    """멀티스레딩 환경에서의 GIL 해제 테스트"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "threading_test_db")

    try:
        db = gimi9_rocks.RocksDB(db_path)

        def worker_put(thread_id, start_idx, count):
            """PUT 작업을 수행하는 워커 함수"""
            for i in range(count):
                key = f"thread_{thread_id}_key_{start_idx + i}"
                value = f"thread_{thread_id}_value_{start_idx + i}_{'x' * 100}"
                db.put(key, value)
            print(f"스레드 {thread_id}: {count}개 PUT 작업 완료")

        def worker_get(thread_id, start_idx, count):
            """GET 작업을 수행하는 워커 함수"""
            found = 0
            for i in range(count):
                key = f"thread_{thread_id}_key_{start_idx + i}"
                value = db.get(key)
                if value is not None:
                    found += 1
            print(f"스레드 {thread_id}: {count}개 GET 작업 완료 (찾은 키: {found}개)")
            return found

        print("=== 멀티스레딩 테스트 ===")

        # PUT 작업을 여러 스레드에서 동시 실행
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for thread_id in range(4):
                future = executor.submit(worker_put, thread_id, thread_id * 1000, 1000)
                futures.append(future)

            # 모든 PUT 작업 완료 대기
            for future in futures:
                future.result()

        put_time = time.time() - start_time
        print(f"4개 스레드로 4000개 PUT 작업: {put_time:.2f}초")

        # GET 작업을 여러 스레드에서 동시 실행
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for thread_id in range(4):
                future = executor.submit(worker_get, thread_id, thread_id * 1000, 1000)
                futures.append(future)

            # 모든 GET 작업 완료 대기 및 결과 수집
            total_found = 0
            for future in futures:
                total_found += future.result()

        get_time = time.time() - start_time
        print(
            f"4개 스레드로 4000개 GET 작업: {get_time:.2f}초 (총 찾은 키: {total_found}개)"
        )

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    threading_test()

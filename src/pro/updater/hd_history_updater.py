import asyncio
import json
import os
import time

import geopandas as gpd
import pygeohash as geohash
from polygon_geohasher.polygon_geohasher import polygon_to_geohashes
from shapely.geometry import box, MultiPolygon
from tqdm import tqdm
from src.geocoder.db.gimi9_rocks import Gimi9RocksDB
from .updater import BaseUpdater


class HdHistoryUpdater(BaseUpdater):
    """
    A class that represents a history updater for the geocoder and reverse geocoder.

    1. 매달 juso.go.kr에서 "구역의 도형 (.shp)" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 TL_SCCO_GEMD.shp 등의 파일이 생성됨.
    3. 파일의 위치는 /disk/hdd-lv/juso-data/전체분/{yyyymm}/map/*/TL_SCCO_GEMD.shp

    주어진 shapefile 경로에서 행정동 변동 이력을 생성합니다.
    Geohash를 사용하여 행정동 변동 이력을 RocksDB에 저장합니다.

    Airflow:  geocoder_monthly_update.merge_hd_history
    ex)
        curl 'http://localhost:4009/merge_hd_history?name=11000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=26000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=27000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=28000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=29000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=30000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=31000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=36000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=41000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=43000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=44000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=46000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=47000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=48000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=50000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=51000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=52000&db_name=hd_history&yyyymm=202507'


    Attributes:
        yyyymm (str): 다운받은 파일 경로의 yyyymm.
        geocoder (Geocoder): The geocoder instance.

    Methods:
        __init__(yyyymm: str, geocoder: Geocoder): Initializes a HdHistoryUpdater instance.
        update(wfile): Updates the geocoder with the address entries.
    """

    def __init__(self, hd_db: Gimi9RocksDB):
        super().__init__(None)
        self.hd_db = hd_db

    async def merge_history(self, input_db_path: str, yyyymm: str):
        return await asyncio.to_thread(self._merge_history, input_db_path, yyyymm)

    def _merge_history(self, input_db_path: str, yyyymm: str):
        self.outpath = input_db_path
        self._prepare_updater_logger("merge_history.log")

        # 기본 데이터베이스 열기 (없으면 생성)
        base_db = self.hd_db

        stats = {
            "total_keys_processed": 0,
            "new_keys_added": 0,
            "updated_keys": 0,
            "start_time": time.time(),
        }

        # 입력 데이터베이스 Merge
        try:
            input_db = Gimi9RocksDB(input_db_path, create_if_missing=False)

            # 입력 DB의 키 개수 가져오기
            # it = input_db.iterkeys()
            # it.seek_to_first()
            # key_count = sum(1 for _ in it)
            key_count = json.loads(input_db.get(b"__metadata__").decode()).get(
                "count", 0
            )

            # batch_count = 0

            # 모든 키 처리
            for key, val in tqdm(
                input_db,
                # input_db.get_iter(),
                total=key_count,
                desc=f"Merging {os.path.basename(input_db_path)}",
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
                input_yyyymm = yyyymm or input_db_path.split("/")[-4]  # 예: 202305
                self._update_yyymm(new_data, input_yyyymm)

                # 기본 DB에서 값 가져오기
                base_value_bytes = base_db.get(key_bytes)

                if not base_value_bytes:
                    # 기본 DB에 해당 키가 없으면 그대로 추가
                    base_db.put(key_bytes, json.dumps(new_data).encode())
                    stats["new_keys_added"] += 1
                else:
                    # 기존 데이터와 병합
                    existing_data = json.loads(base_value_bytes)
                    merged_data = self._merge_data(existing_data, new_data)
                    base_db.put(key_bytes, json.dumps(merged_data).encode())
                    stats["updated_keys"] += 1

                # batch_count += 1
                stats["total_keys_processed"] += 1
                # for key_bytes in tqdm(
                #     it, total=key_count, desc=f"Merging {os.path.basename(input_db_path)}"
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
            self._update_metadata(base_db, input_db)

        except Exception as e:
            self.logger.error(f"Error processing database {input_db_path}: {str(e)}")
            raise e

        # 통계 계산
        stats["end_time"] = time.time()
        stats["elapsed_time"] = stats["end_time"] - stats["start_time"]

        self.logger.info(
            f"Merge completed. Processed {stats['total_keys_processed']} keys."
        )
        self.logger.info(
            f"Added {stats['new_keys_added']} new keys, updated {stats['updated_keys']} existing keys."
        )
        self.logger.info(f"Time elapsed: {stats['elapsed_time']:.2f} seconds")

        return stats

    def _update_yyymm(self, new_data, input_yyyymm):
        for item in new_data:
            item["from_yyyymm"] = input_yyyymm
            item["to_yyyymm"] = input_yyyymm

    def _merge_data(self, existing_data, new_data):
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
            matching_items = self._find_matching_items(existing_data, new_item)

            if not matching_items:
                # 일치하는 항목이 없으면 새로 추가
                result.append(new_item)
            else:
                # 일치하는 항목 중 to_yyyymm이 가장 큰 항목 찾기
                latest_item = self._get_latest_item(matching_items)

                # intersection_wkt 비교
                if latest_item.get("intersection_wkt") != new_item.get(
                    "intersection_wkt"
                ):
                    # 다르면 새로 추가
                    result.append(new_item)
                else:
                    # 같으면 to_yyyymm만 업데이트
                    latest_item["to_yyyymm"] = new_item.get("from_yyyymm")

        return result

    def _get_latest_item(self, items, yyyymm_field="to_yyyymm"):
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

    def _find_matching_items(self, existing_data, new_item, fields=None):
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

    def _update_metadata(self, base_db: Gimi9RocksDB, input_db):
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
            self.logger.error(f"Error updating metadata: {str(e)}")

    async def build_history(self, shp_file, db_path, depth):
        return await asyncio.to_thread(self._build_history, shp_file, db_path, depth)

    def _build_history(self, shp_file, db_path, depth):
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
        self.outpath = db_path
        self._prepare_updater_logger("build_history.log")

        self.logger.info(f"Reading shapefile: {shp_file}")

        # RocksDB 열기
        db = Gimi9RocksDB(db_path, create_if_missing=True)

        try:
            # Shapefile 읽기
            gdf = gpd.read_file(shp_file, encoding="cp949")
            self.logger.info(f"Loaded {len(gdf)} features")

            # CRS가 EPSG:4326(WGS84)이 아닌 경우 변환
            if gdf.crs != "EPSG:4326":
                self.logger.info(f"Converting CRS from {gdf.crs} to EPSG:4326")
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
            self.logger.info(f"Generating geohashes with depth {depth}...")

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
                            equal_data = self._get_equal_data(existing_data, attr_dict)
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

            self.logger.info(f"Processed {stats['processed_features']} features")
            self.logger.info(f"Generated {stats['total_geohashes']} geohashes")
            self.logger.info(f"Time elapsed: {stats['elapsed_time']:.2f} seconds")

            return stats

        except Exception as e:
            self.logger.error(f"Error processing shapefile: {str(e)}")
            raise
        finally:
            # RocksDB는 명시적으로 닫을 필요가 없지만 merge_hd_history api가 DB를 열기 때문에 닫음.
            db.close()
            del db  # Clean up the db variable to free resources
            pass

    def _get_equal_data(self, existing_data, attr_dict):
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

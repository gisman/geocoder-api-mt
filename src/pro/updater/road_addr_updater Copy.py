import asyncio

# import pyogrio
from .shp_reader import ShpReader

# import fiona
import json
from shapely.geometry import shape
import geopandas as gpd
import pandas as pd

from src.geocoder.geocoder import Geocoder
from src.geocoder.pos_cd import ROAD_ADDR_FILTER
from .updater import BaseUpdater, DbCreateContext


# TL_SPRD_INTRVL.shp    기초구간
# TL_SPRD_MANAGE.shp    도로구간
# TL_SPRD_RW.shp        실폭도로


class RoadAddrUpdater(BaseUpdater):
    """
    도로 도형 Map을 이용하여 도로 대표 주소 추가
    1. 매달 juso.go.kr에서 "도로명이 부여된 도로 도형 (.shp)" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 여러 .shp 파일이 생성됨.
    3. 파일의 위치는 /disk/hdd-lv/juso-data/전체분/{yyyymm}/road/{name}/TL_SPRD_MANAGE.shp

    Attributes:
        name (str): 다운받은 파일명.
        geocoder (Geocoder): The geocoder instance.

    Methods:
        __init__(name: str, geocoder: Geocoder): Initializes a instance.
        prepare_dic(key, value): Prepares a dictionary for the address entry.
        update(wfile): Updates the geocoder with the address.
    """

    def __init__(self, geocoder: Geocoder, name: str, yyyymm: str):
        super().__init__(geocoder)
        self.name = name
        self.yyyymm = yyyymm

        # 파일 다운로드 경로 지정
        self.outpath = f"{self.JUSO_DATA_DIR}/전체분/{yyyymm}/road/{name}/"
        self.shp_path = f"{self.outpath}TL_SPRD_MANAGE.shp"
        
        # 성능 최적화를 위한 캐시
        self._h23_cache = {}
        self._h1_cache = {}
        self._address_cache = {}  # 주소 조합 캐시

    def _get_cached_h23_info(self, h23_cd):
        """시군구 정보를 캐시를 통해 가져옵니다."""
        if h23_cd not in self._h23_cache:
            h23_full = self.geocoder.hcodeMatcher.get_h23_nm(h23_cd) if h23_cd else None
            h23_nm = self.geocoder.hsimplifier.h23Hash(h23_full) if h23_full else None
            self._h23_cache[h23_cd] = (h23_full, h23_nm)
        return self._h23_cache[h23_cd]
    
    def _get_cached_h1_info(self, h23_cd):
        """광역시도 정보를 캐시를 통해 가져옵니다."""
        if h23_cd not in self._h1_cache:
            h1_cd = self.geocoder.hcodeMatcher.get_h1_cd(h23_cd) if h23_cd else None
            h1_nm_full = self.geocoder.hcodeMatcher.get_h1_nm(h23_cd) if h23_cd else None
            h1_nm = self.geocoder.hsimplifier.h1Hash(h1_nm_full) if h1_nm_full else None
            self._h1_cache[h23_cd] = (h1_cd, h1_nm_full, h1_nm)
        return self._h1_cache[h23_cd]

    async def update(self, wfile):
        """
        Updates the geocoder with the shp.

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.
        """
        # CPU 바운드 작업을 별도의 스레드로 오프로드
        return await asyncio.to_thread(self._update_sync, wfile)

    def prepare_road_hd_matching_table(self, hd_shp_name: str) -> dict:
        """
        도로와 행(법)정동 매칭 테이블을 준비합니다.
        도로가 어떤 행(법)정동에 속하는지 매핑합니다.
        GeoPandas와 공간 인덱스를 사용해 성능을 최적화합니다.

        Returns:
            dict: RN_CD(도로명코드)를 키로 하고,
                행(법)정동 정보(EMD_CD, EMD_KOR_NM)를 값으로 하는 딕셔너리
        """

        road_hd_matching = {}

        # 길이 비율 임계값 (5% 미만이면 포함된 것으로 간주)
        LENGTH_THRESHOLD = 0.05

        self.logger.info(f"도로-행(법)정동 매칭 테이블 생성 시작. {hd_shp_name}")

        # GeoPandas로 도로 shapefile 읽기 (최적화된 읽기)
        self.logger.info(f"도로 shapefile 읽기: {self.shp_path}")
        
        # 필요한 컬럼만 선택하여 메모리 사용량 최적화
        road_columns = ["RN_CD", "RN", "SIG_CD", "geometry"]
        road_gdf = gpd.read_file(self.shp_path, encoding="cp949", columns=road_columns)
        
        road_count = len(road_gdf)
        self.logger.info(f"도로 데이터 로드 완료: {road_count} 건")

        # 도로 길이 계산 (벡터화된 연산)
        road_gdf["length"] = road_gdf.geometry.length

        # 행정동 shapefile 읽기 (최적화된 읽기)
        hd_shp_path = self.shp_path.replace("TL_SPRD_MANAGE.shp", hd_shp_name).replace(
            "/road/", "/map/"
        )
        self.logger.info(f"행(법)정동 shapefile 읽기: {hd_shp_path}")
        
        # 필요한 컬럼만 선택
        hd_columns = ["EMD_CD", "EMD_KOR_NM", "geometry"]
        hd_gdf = gpd.read_file(hd_shp_path, encoding="cp949", columns=hd_columns)
        
        hd_count = len(hd_gdf)
        self.logger.info(f"행(법)정동 데이터 로드 완료: {hd_count} 건")

        # 성능 향상을 위한 설정
        # CRS 통일 (UTM 좌표계 사용으로 보다 정확한 거리 계산)
        if road_gdf.crs != hd_gdf.crs:
            hd_gdf = hd_gdf.to_crs(road_gdf.crs)
        
        # 행정동별 bounds 미리 계산 (성능 최적화)
        hd_gdf['bounds'] = hd_gdf.geometry.bounds
        
        # 공간 인덱스를 활용한 처리 시작
        self.logger.info("공간 조인 및 매칭 분석 시작 (최적화된 버전)")

        # 배치 크기 증가 (메모리 사용량과 성능의 균형)
        batch_size = 500
        total_batches = (road_count + batch_size - 1) // batch_size

        processed = 0
        for i in range(total_batches):
            # 배치 처리할 도로 범위 선택
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, road_count)
            road_batch = road_gdf.iloc[start_idx:end_idx]

            # 벡터화된 공간 조인 사용 (sjoin 활용)
            # 먼저 intersects로 후보군을 빠르게 필터링
            spatial_join = gpd.sjoin(road_batch, hd_gdf, how='left', predicate='intersects')
            
            # 도로별로 그룹화하여 처리
            for road_idx in road_batch.index:
                road_row = road_gdf.loc[road_idx]
                road_cd = road_row["RN_CD"]
                road_geom = road_row.geometry
                road_length = road_row["length"]

                # 해당 도로와 매칭된 행정동들 가져오기
                matched_rows = spatial_join[spatial_join.index == road_idx]
                
                if len(matched_rows) == 0:
                    processed += 1
                    continue

                best_match = None
                max_overlap_length = 0
                found_complete_contain = False

                # 매칭된 행정동들에 대해서만 정밀 분석
                for _, matched_row in matched_rows.iterrows():
                    if pd.isna(matched_row.get('EMD_CD_right')):
                        continue
                        
                    hd_cd = matched_row['EMD_CD_right']
                    hd_geom = hd_gdf.loc[matched_row['index_right']].geometry

                    try:
                        # 1단계: 완전 포함 여부 확인 (가장 빠른 방법)
                        if hd_geom.contains(road_geom):
                            best_match = {
                                "EMD_CD": hd_cd,
                                "EMD_KOR_NM": matched_row['EMD_KOR_NM_right'],
                            }
                            found_complete_contain = True
                            break

                        # 2단계: 교차 비율 계산 (contains가 실패한 경우만)
                        if not found_complete_contain:
                            # 빠른 bounds 체크로 사전 필터링
                            road_bounds = road_geom.bounds
                            hd_bounds = hd_geom.bounds
                            
                            # bounds 겹침이 없으면 스킵
                            if (road_bounds[2] < hd_bounds[0] or road_bounds[0] > hd_bounds[2] or
                                road_bounds[3] < hd_bounds[1] or road_bounds[1] > hd_bounds[3]):
                                continue

                            # 실제 교차 계산
                            intersection_geom = road_geom.intersection(hd_geom)
                            if intersection_geom.is_empty:
                                continue
                                
                            intersection_length = intersection_geom.length
                            overlap_ratio = intersection_length / road_length

                            # 임계값 체크 및 최적 매치 업데이트
                            if (overlap_ratio > LENGTH_THRESHOLD and 
                                intersection_length > max_overlap_length):
                                max_overlap_length = intersection_length
                                best_match = {
                                    "EMD_CD": hd_cd,
                                    "EMD_KOR_NM": matched_row['EMD_KOR_NM_right'],
                                }
                    except Exception as e:
                        # 기하학적 오류 발생 시 스킵
                        continue

                # 매칭 결과 저장
                if best_match:
                    existing_match = road_hd_matching.get(road_cd)
                    if existing_match:
                        if existing_match["EMD_CD"] != best_match["EMD_CD"]:
                            existing_match["중복"] = True
                    else:
                        road_hd_matching[road_cd] = best_match

                processed += 1
                
            # 배치 단위로 진행상황 로깅
            if processed % 5000 == 0:
                self.logger.info(
                    f"도로 처리 진행: {processed}/{road_count} ({processed/road_count*100:.1f}%) - 배치 {i+1}/{total_batches}"
                )

        self.logger.info(
            f"도로-행(법)정동 매칭 테이블 생성 완료: {len(road_hd_matching)}/{road_count} 건 매칭됨"
        )
        return road_hd_matching

    def process_batch(self, batch_records):
        """
        배치 단위로 레코드를 처리하여 성능을 향상시킵니다.
        
        Args:
            batch_records: 처리할 레코드들의 리스트
            
        Returns:
            int: 추가된 레코드 수
        """
        batch_add_count = 0
        
        for road_dic in batch_records:
            try:
                # db value 준비
                val = {
                    "x": road_dic["x"],
                    "y": road_dic["y"],
                    "h1_nm": road_dic["h1_nm"],
                    "h23_nm": road_dic["h23_nm"],
                    "hd_nm": road_dic["hd_nm"],
                    "ld_nm": road_dic["ld_nm"],
                    "road_cd": road_dic["road_cd"],
                    "h1_cd": road_dic["h1_cd"],
                    "h23_cd": road_dic["h23_cd"],
                    "hd_cd": road_dic["hd_cd"],
                    "ld_cd": road_dic["ld_cd"],
                    "road_nm": road_dic["road_full"],
                    "pos_cd": road_dic["pos_cd"],
                }

                val_json = json.dumps(val).encode()
                self.ctx = DbCreateContext(val, val_json, road_dic)

                batch_add_count += self.update_record(
                    road_dic,
                    merge_if_exists=True,
                )
            except Exception as e:
                self.logger.error(f"Error processing batch record: {e}")
                continue
                
        return batch_add_count

    def _update_sync(self, wfile):
        """
        Updates the geocoder with the shp.

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.

        """
        self._prepare_updater_logger(f"{self.name}.log")

        # 매칭 테이블 초기화
        self.road_hd_matching = self.prepare_road_hd_matching_table(
            "TL_SCCO_GEMD.shp"
        )  # 행정동
        self.road_ld_matching = self.prepare_road_hd_matching_table(
            "TL_SCCO_EMD.shp"
        )  # 법정동

        extras = {"yyyymm": self.yyyymm, "updater": "road_addr_updater"}

        cnt = 0
        add_count = 0
        has_xy = 0

        # SHP 파일 읽기
        sr = ShpReader(self.shp_path, encoding="cp949")
        
        self.logger.info(f"Update: {self.outpath}")

        # 배치 처리를 위한 리스트
        batch_records = []
        batch_size = 1000  # 배치 크기 설정
        
        # 모든 지오메트리 처리
        cnt = 0
        for value, geom in sr:
            try:
                representative_point = self.representative_point(geom)
                value["X좌표"] = int(representative_point.x)
                value["Y좌표"] = int(representative_point.y)

                road_dic = self.prepare_dic(value)
                road_dic["pos_cd"] = ROAD_ADDR_FILTER
                road_dic["extras"] = extras

                # 배치에 추가
                batch_records.append(road_dic)
                
                # 배치가 가득 찼거나 마지막 레코드인 경우 처리
                if len(batch_records) >= batch_size:
                    add_count += self.process_batch(batch_records)
                    batch_records = []
                    
                    if cnt % 10000 == 0:
                        self.logger.info(
                            f"{self.name} {add_count:,} 건 추가, {cnt:,} 건 처리 중"
                        )
                        
            except Exception as e:
                self.logger.error(f"Error processing record {cnt}: {e}")
                continue
                
            cnt += 1

        # 남은 배치 처리
        if batch_records:
            add_count += self.process_batch(batch_records)

        self.logger.info(
            f"도로 SHP {self.name}: {cnt:,} 건, : {has_xy:,} 건. hash 추가: {add_count:,} 건"
        )

        self.logger.info(f"완료: {self.name}")

        log_file = f"{self.outpath}{self.name}.log"
        with open(log_file, "r") as f:
            log = f.read()
            wfile.write(log)

        self._stop_updater_logging()
        return True

    def representative_point(self, wgs84_geom):
        """
        Returns the representative point of the geometry.
        도로의 무게 중심을 대표 좌표로 사용

        Args:
            wgs84_geom: The geometry in WGS84 coordinates.

        Returns:
            Point: The representative point of the geometry.
        """

        # Shapely를 사용하여 도로의 무게 중심을 계산
        if wgs84_geom.is_empty:
            return None

        # 무게 중심 계산
        # 도로 line 위에 있는 중심점 추출
        centroid = wgs84_geom.interpolate(wgs84_geom.length / 2)

        # WGS84 좌표계로 변환
        return centroid

    def prepare_dic(self, value):
        """
        Prepares a dictionary for the address.

        Args:
            value: The value of the address.

        Returns:
            dict: The prepared dictionary for the address.

        """
        # ALWNC_DE: 20090105
        # ALWNC_RESN: 안흥 시가지를 지나는 중심도로로 행정구역명(안흥) 반영
        # BSI_INT: 20
        # ENG_RN: Anheung-ro
        # MVMN_DE: 20230611
        # MVMN_RESN: 강원도 도(道)명칭 변경(강원특별자치도)
        # MVM_RES_CD: 41
        # NTFC_DE: 20090203
        # OPERT_DE: 20230611000000
        # RBP_CN: 안흥리 317
        # RDS_DPN_SE: 0
        # RDS_MAN_NO: 1043
        # REP_CN: 안흥리 277-3
        # * RN: 안흥로
        # * RN_CD: 3226041
        # ROAD_BT: 8.000
        # ROAD_LT: 657.000
        # ROA_CLS_SE: 3
        # * SIG_CD: 51730
        # WDR_RD_CD: 3

        # 기본값 설정 (None 체크 최소화)
        road_full = value.get("RN", "")
        road_cd = value.get("RN_CD")
        h23_cd = value.get("SIG_CD")

        # 매칭 정보 미리 가져오기 (딕셔너리 조회 최소화)
        hd_match = self.road_hd_matching.get(road_cd, {})
        ld_match = self.road_ld_matching.get(road_cd, {})
        
        # 행정동 정보
        hd_cd = hd_match.get("EMD_CD") if not hd_match.get("중복", False) else None
        hd_full = hd_match.get("EMD_KOR_NM") if hd_cd else None
        hd_nm = hd_full

        # 법정동 정보  
        ld_cd = ld_match.get("EMD_CD") if not ld_match.get("중복", False) else None
        ld_full = ld_match.get("EMD_KOR_NM") if ld_cd else None
        ld_nm = ld_full

        # 시군구 정보 (캐싱 활용)
        h23_full, h23_nm = self._get_cached_h23_info(h23_cd)

        # 광역시도 정보 (캐싱 활용)
        h1_cd, h1_nm_full, h1_nm = self._get_cached_h1_info(h23_cd) if (h23_cd and (hd_match or ld_match)) else (None, None, None)

        return {
            "h1_nm": h1_nm,
            "h23_nm": h23_nm,
            "h23_full": h23_full,
            "ld_nm": ld_nm,
            "ld_full": ld_full,
            "hd_nm": hd_nm,
            "hd_full": hd_full,
            "road_full": road_full,
            "h1_cd": h1_cd,
            "h23_cd": h23_cd,
            "ld_cd": ld_cd,
            "hd_cd": hd_cd,
            "road_cd": road_cd,
            "rm": road_full,
            "x": value["X좌표"],
            "y": value["Y좌표"],
        }

    def put(self, address: str):
        if self._del_and_put(
            address,
            True,
            force_delete=False,
        ):
            return 1

        return 0

    def update_record(self, d: dict, merge_if_exists=True, extras: dict = {}):
        """
        레코드 업데이트를 최적화된 방식으로 처리합니다.
        중복 생성을 줄이고 배치 처리를 활용합니다.
        """
        add_count = 0
        
        # 기본 주소 조합들을 리스트로 미리 생성
        base_addresses = [
            f'{d["road_full"]}',  # 길만
            f'{d["h23_full"]} {d["road_full"]}',  # 시군구 + 길
        ]
        
        # 광역시도가 있는 경우 추가
        if d["h1_nm"]:
            base_addresses.extend([
                f'{d["h1_nm"]} {d["road_full"]}',  # 광역시도 + 길
                f'{d["h1_nm"]} {d["h23_full"]} {d["road_full"]}',  # 광역시도 + 시군구 + 길
            ])

        # 기본 주소들 처리
        for addr in base_addresses:
            if addr and addr.strip():  # 빈 문자열 체크
                add_count += self.put(addr)

        # 동별 주소 처리 (행정동, 법정동)
        for dong_type in ["ld_full", "hd_full"]:
            dong_name = d.get(dong_type)
            if not dong_name:  # 여러 동에 속하는 도로는 동 대표도로 제외
                continue
                
            dong_addresses = [
                f'{dong_name} {d["road_full"]}',  # 동 + 길
                f'{d["h23_full"]} {dong_name} {d["road_full"]}',  # 시군구 + 동 + 길
            ]
            
            # 광역시도가 있는 경우 추가
            if d["h1_nm"]:
                dong_addresses.extend([
                    f'{d["h1_nm"]} {dong_name} {d["road_full"]}',  # 광역시도 + 동 + 길
                    f'{d["h1_nm"]} {d["h23_full"]} {dong_name} {d["road_full"]}',  # 광역시도 + 시군구 + 동 + 길
                ])
            
            # 동 주소들 처리
            for addr in dong_addresses:
                if addr and addr.strip():
                    add_count += self.put(addr)

        return add_count

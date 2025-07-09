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

        # GeoPandas로 도로 shapefile 읽기
        self.logger.info(f"도로 shapefile 읽기: {self.shp_path}")
        road_gdf = gpd.read_file(self.shp_path, encoding="cp949")
        road_count = len(road_gdf)
        self.logger.info(f"도로 데이터 로드 완료: {road_count} 건")

        # 도로 길이 계산
        road_gdf["length"] = road_gdf.geometry.length

        # 행정동 shapefile 읽기
        hd_shp_path = self.shp_path.replace("TL_SPRD_MANAGE.shp", hd_shp_name).replace(
            "/road/", "/map/"
        )
        self.logger.info(f"행(법)정동 shapefile 읽기: {hd_shp_path}")
        hd_gdf = gpd.read_file(hd_shp_path, encoding="cp949")
        hd_count = len(hd_gdf)
        self.logger.info(f"행(법)정동 데이터 로드 완료: {hd_count} 건")

        # 공간 인덱스를 활용한 처리 시작
        self.logger.info("공간 조인 및 매칭 분석 시작")

        # 일괄 처리를 위한 배치 크기 설정
        batch_size = 100
        total_batches = (road_count + batch_size - 1) // batch_size

        processed = 0
        for i in range(total_batches):
            # 배치 처리할 도로 범위 선택
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, road_count)
            road_batch = road_gdf.iloc[start_idx:end_idx]

            # 각 도로에 대한 처리
            for idx, road_row in road_batch.iterrows():
                road_cd = road_row["RN_CD"]
                road_nm = road_row["RN"]
                road_geom = road_row.geometry
                road_length = road_row["length"]

                # 공간 인덱스를 사용하여 이 도로와 교차하는 모든 행정동 찾기
                # sindex는 내부적으로 R-tree 인덱스 사용
                possible_matches_idx = list(
                    hd_gdf.sindex.intersection(road_geom.bounds)
                )
                possible_matches = hd_gdf.iloc[possible_matches_idx]

                best_match = None
                max_overlap_length = 0

                # 후보 행(법)정동들만 자세히 분석
                match_count = 0
                for _, hd_row in possible_matches.iterrows():
                    hd_cd = hd_row["EMD_CD"]
                    hd_geom = hd_row.geometry

                    # 포함 여부 확인
                    try:
                        if hd_geom.contains(road_geom):
                            best_match = {
                                "EMD_CD": hd_cd,
                                "EMD_KOR_NM": hd_row["EMD_KOR_NM"],
                            }
                            break  # 가장 적합한 행(법)정동을 찾았으므로 루프 종료

                        # 실제 교차 여부 확인
                        if road_geom.intersects(hd_geom):

                            # 겹치는 영역 계산
                            intersection_geom = road_geom.intersection(hd_geom)
                            intersection_length = intersection_geom.length

                            # 면적 비율 계산
                            overlap_ratio = intersection_length / road_length

                            # 임계값보다 큰 경우에만 고려
                            if overlap_ratio > LENGTH_THRESHOLD:
                                match_count += 1
                                if intersection_length > max_overlap_length:
                                    max_overlap_length = intersection_length
                                    best_match = {
                                        "EMD_CD": hd_cd,
                                        "EMD_KOR_NM": hd_row["EMD_KOR_NM"],
                                    }
                    except Exception as e:
                        pass

                # 가장 적합한 행(법)정동 매칭 추가
                if best_match:
                    if match_count > 1:
                        road_hd_matching[road_cd] = {"중복": True}

                    # # 다른 행정동에도 속하는지 확인. 중복 코드 추가
                    # val = road_hd_matching.get(road_cd)
                    # if val:
                    #     # 이미 다른 행정동과 매칭된 경우, 중복되지 않도록 처리
                    #     if val["EMD_CD"] != best_match["EMD_CD"]:
                    #         val["중복"] = True
                    #         # self.logger.warning(
                    #         #     f"중복 도로명 코드 발견: {road_cd}, 기존: {val['EMD_CD']}, 새: {best_match['EMD_CD']}"
                    #         # )
                    else:
                        # 새로운 매칭 추가
                        # self.logger.info(
                        #     f"도로명 코드 {road_cd}에 행정동 {best_match['EMD_CD']} 매칭 추가"
                        # )
                        # 도로명 코드에 행정동 매칭 추가
                        road_hd_matching[road_cd] = best_match

                processed += 1
                if processed % 10000 == 0:
                    self.logger.info(
                        f"도로 처리 진행: {processed}/{road_count} ({processed/road_count*100:.1f}%)"
                    )

        self.logger.info(
            f"도로-행(법)정동 매칭 테이블 생성 완료: {len(road_hd_matching)}/{road_count} 건 매칭됨"
        )
        return road_hd_matching

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
        # shp_file = pyogrio.read_dataframe(self.shp_path, encoding="cp949")
        # with fiona.open(f"{self.shp_path}", "r", encoding="cp949") as shp_file:

        self.logger.info(f"Update: {self.outpath}")

        # for all geometry
        cnt = 0
        for value, geom in sr:
            # for feature in shp_file.itertuples(index=False):
            # value = feature._asdict()
            # geom = shape(value.pop("geometry"))

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
            # * RN_CD: 3226041      도로 식별자. 여러개가 존재할 수 있음
            # ROAD_BT: 8.000
            # ROAD_LT: 657.000
            # ROA_CLS_SE: 3
            # * SIG_CD: 51730
            # WDR_RD_CD: 3

            # value = dict(feature.properties)
            # geom = shape(feature["geometry"])
            representative_point = self.representative_point(geom)
            # 14134909,4512659
            value["X좌표"] = int(representative_point.x)
            value["Y좌표"] = int(representative_point.y)

            try:
                road_dic = self.prepare_dic(value)
                road_dic["pos_cd"] = ROAD_ADDR_FILTER
                road_dic["extras"] = extras

                # if value["RN"] != "가곡천로":
                #     continue

                # db value
                val = {
                    "x": road_dic["x"],
                    "y": road_dic["y"],
                    # "z": road_dic["zip"],
                    "h1_nm": road_dic["h1_nm"],
                    "h23_nm": road_dic["h23_nm"],
                    "hd_nm": road_dic["hd_nm"],
                    "ld_nm": road_dic["ld_nm"],
                    "road_cd": road_dic["road_cd"],
                    "h1_cd": road_dic["h1_cd"],
                    "h23_cd": road_dic["h23_cd"],
                    "hd_cd": road_dic["hd_cd"],
                    "ld_cd": road_dic["ld_cd"],
                    # "ri_nm": road_dic["ri_nm"],
                    "road_nm": road_dic["road_full"],
                    "pos_cd": road_dic["pos_cd"],
                }

                val_json = json.dumps(val).encode()
                self.ctx = DbCreateContext(val, val_json, road_dic)

                add_count += self.update_record(
                    road_dic,
                    merge_if_exists=True,
                )
                if add_count and cnt % 10000 == 0:
                    self.logger.info(
                        f"{self.name} {add_count:,} 건 추가, {cnt:,} 건 처리 중"
                    )
            except Exception as e:
                self.logger.error(f"Error: {e}")
                # continue
            cnt += 1
            # if cnt % 10000 == 0:
            #     self.logger.info(f"{self.name} {cnt:,}")
            #     print(f"{self.name} {cnt:,}")

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

        road_full = value["RN"]
        road_cd = value["RN_CD"]
        # road_nm = self.geocoder.roadSimplifier.roadHash(road_full)

        # 매칭 행정동
        hd_cd = None
        hd_full = None
        hd_nm = None
        matching_hd = self.road_hd_matching.get(road_cd, {})
        if matching_hd and matching_hd.get("중복", False) == False:
            hd_cd = matching_hd["EMD_CD"]
            hd_full = matching_hd["EMD_KOR_NM"]
            hd_nm = hd_full
            # hd_nm = self.geocoder.hsimplifier.h4Hash(hd_full, keep_dong=True)

        # 매칭 법정동
        ld_cd = None
        ld_full = None
        ld_nm = None
        matching_hd = self.road_ld_matching.get(road_cd, {})
        if matching_hd and matching_hd.get("중복", False) == False:
            ld_cd = matching_hd["EMD_CD"]
            ld_full = matching_hd["EMD_KOR_NM"]
            ld_nm = ld_full  # self.geocoder.hsimplifier.h4Hash(ld_full)

        # 시군구
        h23_cd = None
        h23_full = None
        h23_nm = None
        h23_cd = value.get("SIG_CD")
        h23_full = self.geocoder.hcodeMatcher.get_h23_nm(h23_cd)
        h23_nm = self.geocoder.hsimplifier.h23Hash(h23_full)

        # 광역시도코드, 이름
        h1_cd = None
        h1_nm_full = None
        h1_nm = None
        if matching_hd:
            h1_cd = self.geocoder.hcodeMatcher.get_h1_cd(h23_cd)
            h1_nm_full = self.geocoder.hcodeMatcher.get_h1_nm(h23_cd)
            h1_nm = self.geocoder.hsimplifier.h1Hash(h1_nm_full)

        d = {
            "h1_nm": h1_nm_full,  # 검색용
            "h1_nm": h1_nm,  # db 추가용
            "h23_nm": h23_nm,
            "h23_full": h23_full,
            "ld_nm": ld_nm,
            "ld_full": ld_full,
            "hd_nm": hd_nm,
            "hd_full": hd_full,
            # "ri_nm": None,
            # "ri_full": None,
            "road_full": road_full,
            "h1_cd": h1_cd,  # 광역시도 코드
            "h23_cd": h23_cd,
            "ld_cd": ld_cd,
            "hd_cd": hd_cd,
            "road_cd": road_cd,
            "rm": road_full,
            "x": value["X좌표"],
            "y": value["Y좌표"],
        }

        return d

    def put(self, address: str):
        if self._del_and_put(
            address,
            True,
            force_delete=False,
        ):
            return 1

        return 0

    def update_record(self, d: dict, merge_if_exists=True, extras: dict = {}):
        add_count = 0

        # 광역시도 길
        add_count += self.put(f'{d["h1_nm"]} {d["road_full"]}')
        # 광역시도 시군구 길
        add_count += self.put(f'{d["h1_nm"]} {d["h23_full"]} {d["road_full"]}')
        # 시군구 길
        add_count += self.put(f'{d["h23_full"]} {d["road_full"]}')
        # 길
        add_count += self.put(f'{d["road_full"]}')

        for DONG in ["ld_full", "hd_full"]:
            # self.logger.info(f"추가: {DONG}")
            if not d[DONG]:  # 여러 동에 속하는 도로는 동 대표도로 제외
                continue
            if d[DONG]:
                # 광역시도 행(법)정동 길
                add_count += self.put(f'{d["h1_nm"]} {d[DONG]} {d["road_full"]}')
                # 광역시도 시군구 행(법)정동 길
                add_count += self.put(
                    f'{d["h1_nm"]} {d["h23_full"]} {d[DONG]} {d["road_full"]}'
                )
                # 시군구 행(법)정동 길
                add_count += self.put(f'{d["h23_full"]} {d[DONG]} {d["road_full"]}')
                # 행(법)정동 길
                add_count += self.put(f'{d[DONG]} {d["road_full"]}')

        return add_count

import asyncio
from .shp_reader import ShpReader

# import pyogrio

# import fiona
import json
from shapely.geometry import shape
import geopandas as gpd
import pandas as pd

from src.geocoder.geocoder import Geocoder
from src.geocoder.pos_cd import *
from .updater import BaseUpdater, DbCreateContext


# TL_SCCO_CTPRVN.shp: 광역시도
# TL_SCCO_SIG.shp: 시군구
# TL_SCCO_GEMD.shp: 읍면동
# TL_SCCO_EMD.shp: 법정동
# TL_KODIS_BAS.shp: 우편번호
# TL_SCCO_LI.shp: 리


class RiAddrUpdater(BaseUpdater):
    """
    리 경계 Map을 이용하여 리 대표 주소 추가
    1. 매달 juso.go.kr에서 "구역의 도형 (.shp)" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 여러 .shp 파일이 생성됨.
    3. 파일의 위치는 /disk/hdd-lv/juso-data/전체분/{yyyymm}/map/*/TL_SCCO_LI.shp

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
        self.outpath = f"{self.JUSO_DATA_DIR}/전체분/{yyyymm}/map/{name}/"
        self.shp_path = f"{self.outpath}TL_SCCO_LI.shp"

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

    def prepare_ri_hd_matching_table(self, hd_shp_name: str) -> dict:
        """
        리과 행정동(법정동) 매칭 테이블을 준비합니다.
        리가 어떤 행정동(법정동)에 속하는지 매핑합니다.
        GeoPandas와 공간 인덱스를 사용해 성능을 최적화합니다.

        Returns:
            dict: 리 코드(LI_CD)를 키로 하고,
                행정동(법정동) 정보(EMD_CD, EMD_KOR_NM)를 값으로 하는 딕셔너리
        """

        ri_hd_matching = {}

        # 면적 비율 임계값 (5% 미만이면 겹치지 않는 것으로 간주)
        AREA_THRESHOLD = 0.05

        self.logger.info("리-행정동(법정동) 매칭 테이블 생성 시작")

        # GeoPandas로 리 shapefile 읽기
        self.logger.info(f"리 shapefile 읽기: {self.shp_path}")
        ri_gdf = gpd.read_file(self.shp_path, encoding="cp949")
        ri_count = len(ri_gdf)
        self.logger.info(f"리 데이터 로드 완료: {ri_count} 건")

        # 리 면적 계산
        ri_gdf["area"] = ri_gdf.geometry.area

        # 행정동(법정동) shapefile 읽기
        hd_shp_path = self.shp_path.replace("TL_SCCO_LI.shp", hd_shp_name)
        self.logger.info(f"행정동(법정동) shapefile 읽기: {hd_shp_path}")
        hd_gdf = gpd.read_file(hd_shp_path, encoding="cp949")
        hd_count = len(hd_gdf)
        self.logger.info(f"행정동(법정동) 데이터 로드 완료: {hd_count} 건")

        # 공간 인덱스를 활용한 처리 시작
        self.logger.info("공간 조인 및 매칭 분석 시작")

        # 일괄 처리를 위한 배치 크기 설정
        batch_size = 100
        total_batches = (ri_count + batch_size - 1) // batch_size

        processed = 0
        for i in range(total_batches):
            # 배치 처리할 리 범위 선택
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, ri_count)
            ri_batch = ri_gdf.iloc[start_idx:end_idx]

            # 각 리에 대한 처리
            for idx, ri_row in ri_batch.iterrows():
                ri_cd = ri_row["LI_CD"]
                ri_geom = ri_row.geometry
                ri_area = ri_row["area"]

                # 공간 인덱스를 사용하여 이 리와 교차하는 모든 행정동(법정동) 찾기
                # sindex는 내부적으로 R-tree 인덱스 사용
                possible_matches_idx = list(hd_gdf.sindex.intersection(ri_geom.bounds))
                possible_matches = hd_gdf.iloc[possible_matches_idx]

                best_match = None
                max_overlap_area = 0

                # 후보 행정동(법정동)들만 자세히 분석
                for _, hd_row in possible_matches.iterrows():
                    hd_cd = hd_row["EMD_CD"]
                    hd_geom = hd_row.geometry

                    # 포함 여부 확인
                    try:
                        if hd_geom.contains(ri_geom):
                            best_match = {
                                "EMD_CD": hd_cd,
                                "EMD_KOR_NM": hd_row["EMD_KOR_NM"],
                            }
                            break  # 가장 적합한 행정동(법정동)을 찾았으므로 루프 종료

                        # 실제 교차 여부 확인
                        if ri_geom.intersects(hd_geom):

                            # 겹치는 영역 계산
                            intersection_geom = ri_geom.intersection(hd_geom)
                            intersection_area = intersection_geom.area

                            # 면적 비율 계산
                            overlap_ratio = intersection_area / ri_area

                            # 임계값보다 큰 경우에만 고려
                            if (
                                overlap_ratio > AREA_THRESHOLD
                                and intersection_area > max_overlap_area
                            ):
                                max_overlap_area = intersection_area
                                best_match = {
                                    "EMD_CD": hd_cd,
                                    "EMD_KOR_NM": hd_row["EMD_KOR_NM"],
                                }
                    except Exception as e:
                        pass

                # 가장 적합한 행정동(법정동) 매칭 추가
                if best_match:
                    ri_hd_matching[ri_cd] = best_match

                processed += 1
                if processed % 100 == 0:
                    self.logger.info(
                        f"리 처리 진행: {processed}/{ri_count} ({processed/ri_count*100:.1f}%)"
                    )

        self.logger.info(
            f"리-행정동(법정동) 매칭 테이블 생성 완료: {len(ri_hd_matching)}/{ri_count} 건 매칭됨"
        )
        return ri_hd_matching

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
        self.ri_ld_matching = self.prepare_ri_hd_matching_table(
            "TL_SCCO_EMD.shp"
        )  # 법정동
        self.ri_hd_matching = self.prepare_ri_hd_matching_table(
            "TL_SCCO_GEMD.shp"
        )  # 행정동

        cnt = 0
        add_count = 0
        has_xy = 0

        # SHP 파일 읽기
        sr = ShpReader(self.shp_path, encoding="cp949")
        # shp_file = pyogrio.read_dataframe(self.shp_path, encoding="cp949")
        # with fiona.open(f"{self.shp_path}", "r", encoding="cp949") as shp_file:
        self.logger.info(f"Update: {self.outpath}{self.name}")

        extras = {"yyyymm": self.yyyymm, "updater": "ri_addr_updater"}

        # for all geometry
        n = 0
        for value, geom in sr:
            # value = dict(feature.properties)

            # LI_CD: 5173038023
            # LI_ENG_NM: Wolhyeon-ri
            # LI_KOR_NM: 월현리

            # geom = shape(feature["geometry"])
            representative_point = self.representative_point(geom)
            # 14134909,4512659
            value["X좌표"] = int(representative_point.x)
            value["Y좌표"] = int(representative_point.y)

            try:
                ri_dic = self.prepare_dic(value)
                ri_dic["pos_cd"] = RI_ADDR_FILTER
                ri_dic["extras"] = extras

                # db value
                val = {
                    "x": ri_dic["x"],
                    "y": ri_dic["y"],
                    # "z": ri_dic["zip"],
                    "h1_nm": ri_dic["h1_nm"],
                    "h23_nm": ri_dic["h23_nm"],
                    "hd_nm": ri_dic["hd_nm"],
                    "ld_nm": ri_dic["ld_nm"],
                    "h1_cd": ri_dic["h1_cd"],
                    "h23_cd": ri_dic["h23_cd"],
                    "hd_cd": ri_dic["hd_cd"],
                    "ld_cd": ri_dic["ld_cd"],
                    "ri_nm": ri_dic["ri_nm"],
                    "pos_cd": ri_dic["pos_cd"],
                }

                val_json = json.dumps(val).encode()
                self.ctx = DbCreateContext(val, val_json, ri_dic)

                add_count += self.update_record(
                    ri_dic,
                    merge_if_exists=True,
                )
            except Exception as e:
                self.logger.error(f"Error: {e}")
                # continue
            cnt += 1
            if cnt % 10000 == 0:
                self.logger.info(f"{self.name} {cnt:,}")
                print(f"{self.name} {cnt:,}")

        self.logger.info(
            f"리 SHP {self.name}: {cnt:,} 건, : {has_xy:,} 건. hash 추가: {add_count:,} 건"
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
        바다에 찍히지 않게 면적 가장 큰 Polygon의 무게 중심을 대표 좌표로 사용

        Args:
            wgs84_geom: The geometry in WGS84 coordinates.

        Returns:
            Point: The representative point of the geometry.
        """

        if wgs84_geom.geom_type == "MultiPolygon":
            # Find the largest polygon by area
            largest_polygon = max(wgs84_geom.geoms, key=lambda p: p.area)
            return largest_polygon.centroid
        elif wgs84_geom.geom_type == "Polygon":
            return wgs84_geom.centroid
        else:
            raise ValueError("Unsupported geometry type for representative point")

    def prepare_dic(self, value):
        """
        Prepares a dictionary for the address.

        Args:
            value: The value of the address.

        Returns:
            dict: The prepared dictionary for the address.

        """
        # LI_CD: 5173038023
        # LI_ENG_NM: Wolhyeon-ri
        # LI_KOR_NM: 월현리
        ri_full = value["LI_KOR_NM"]
        ri_cd = value["LI_CD"]
        ri_nm = self.geocoder.hsimplifier.h4Hash(ri_full)

        # 매칭 법정동
        ld_cd = None
        ld_full = None
        ld_nm = None
        matching_ld = self.ri_ld_matching.get(ri_cd, {})
        if matching_ld:
            ld_cd = matching_ld["EMD_CD"]
            ld_full = matching_ld["EMD_KOR_NM"]
            ld_nm = self.geocoder.hsimplifier.h4Hash(ld_full)

        # 매칭 행정동
        hd_cd = None
        hd_full = None
        hd_nm = None
        matching_hd = self.ri_hd_matching.get(ri_cd, {})
        if matching_hd:
            hd_cd = matching_hd["EMD_CD"]
            hd_full = matching_hd["EMD_KOR_NM"]
            hd_nm = hd_full
            # hd_nm = self.geocoder.hsimplifier.h4Hash(hd_full, keep_dong=True)

        # 시군구
        h23_cd = ri_cd[:5]
        h23_full = self.geocoder.hcodeMatcher.get_h23_nm(h23_cd)
        h23_nm = self.geocoder.hsimplifier.h23Hash(h23_full)

        # 광역시도코드, 이름
        h1_cd = self.geocoder.hcodeMatcher.get_h1_cd(h23_cd)
        h1_nm_full = self.geocoder.hcodeMatcher.get_h1_nm(h23_cd)
        h1_nm = self.geocoder.hsimplifier.h1Hash(h1_nm_full)

        d = {
            "h1_nm": h1_nm,  # 검색용
            "h1": h1_nm,  # db 추가용
            "h23_nm": h23_nm,
            "h23_full": h23_full,
            "ld_nm": ld_nm,
            "ld_full": ld_full,
            "hd_nm": hd_nm,
            "hd_full": hd_full,
            "ri_nm": ri_nm,
            "ri_full": ri_full,
            "h1_cd": h23_cd[:2],  # 광역시도 코드
            "h23_cd": h23_cd,
            "hd_cd": hd_cd,
            "ld_cd": ld_cd,
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

        for DONG in ("ld_full", "hd_full"):
            # 광역시도 시군구 행(법)정동 리
            add_count += self.put(
                f'{d["h1_nm"]} {d["h23_full"]} {d[DONG]} {d["ri_full"]}'
            )
            # 강원도 횡성군 월현리
            add_count += self.put(f'{d["h1_nm"]} {d["h23_full"]} {d["ri_full"]}')
            # 강원도 월현리
            add_count += self.put(f'{d["h1_nm"]} {d["ri_full"]}')

            # 광역시도 행(법)정동 리
            add_count += self.put(f'{d["h1_nm"]} {d[DONG]} {d["ri_full"]}')
            # 시군구 행(법)정동 리
            add_count += self.put(f'{d["h23_full"]} {d[DONG]} {d["ri_full"]}')
            # 횡성군 월현리
            add_count += self.put(f'{d["h23_full"]} {d["ri_full"]}')
            # 행(법)정동 리
            add_count += self.put(f'{d[DONG]} {d["ri_full"]}')

        # 리
        add_count += self.put(f'{d["ri_full"]}')

        return add_count

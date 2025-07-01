import asyncio


# import fiona
import json
from shapely.geometry import shape
import geopandas as gpd
import pandas as pd

from src.geocoder.geocoder import Geocoder
from src.geocoder.pos_cd import LD_ADDR_FILTER
from .updater import BaseUpdater, DbCreateContext
from .shp_reader import ShpReader


# TL_SCCO_CTPRVN.shp: 광역시도
# TL_SCCO_SIG.shp: 시군구
# TL_SCCO_GEMD.shp: 읍면동
# TL_SCCO_EMD.shp: 법정동
# TL_KODIS_BAS.shp: 우편번호
# TL_SCCO_LI.shp: 리


class LdAddrUpdater(BaseUpdater):
    """
    법정동 경계 Map을 이용하여 법정동 대표 주소 추가
    1. 매달 juso.go.kr에서 "구역의 도형 (.shp)" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 여러 .shp 파일이 생성됨.
    3. 파일의 위치는 /disk/hdd-lv/juso-data/전체분/{yyyymm}/map/*/TL_SCCO_EMD.shp

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
        self.shp_path = f"{self.outpath}TL_SCCO_EMD.shp"

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

    def prepare_ld_hd_matching_table(self):
        """
        법정동과 행정동 매칭 테이블을 준비합니다.
        법정동이 어떤 행정동에 속하는지 매핑합니다.
        GeoPandas와 공간 인덱스를 사용해 성능을 최적화합니다.

        Returns:
            dict: 법정동 코드(EMD_CD)를 키로 하고,
                행정동 정보(EMD_CD, EMD_KOR_NM)를 값으로 하는 딕셔너리
        """

        # 매칭 테이블 초기화
        self.ld_hd_matching = {}

        # 면적 비율 임계값 (5% 미만이면 겹치지 않는 것으로 간주)
        AREA_THRESHOLD = 0.05

        self.logger.info("법정동-행정동 매칭 테이블 생성 시작")

        # GeoPandas로 법정동 shapefile 읽기
        self.logger.info(f"법정동 shapefile 읽기: {self.shp_path}")
        ld_gdf = gpd.read_file(self.shp_path, encoding="cp949")
        ld_count = len(ld_gdf)
        self.logger.info(f"법정동 데이터 로드 완료: {ld_count} 건")

        # 법정동 면적 계산
        ld_gdf["area"] = ld_gdf.geometry.area

        # 행정동 shapefile 읽기
        hd_shp_path = self.shp_path.replace("TL_SCCO_EMD.shp", "TL_SCCO_GEMD.shp")
        self.logger.info(f"행정동 shapefile 읽기: {hd_shp_path}")
        hd_gdf = gpd.read_file(hd_shp_path, encoding="cp949")
        hd_count = len(hd_gdf)
        self.logger.info(f"행정동 데이터 로드 완료: {hd_count} 건")

        # 공간 인덱스를 활용한 처리 시작
        self.logger.info("공간 조인 및 매칭 분석 시작")

        # 일괄 처리를 위한 배치 크기 설정
        batch_size = 100
        total_batches = (ld_count + batch_size - 1) // batch_size

        processed = 0
        for i in range(total_batches):
            # 배치 처리할 법정동 범위 선택
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, ld_count)
            ld_batch = ld_gdf.iloc[start_idx:end_idx]

            # 각 법정동에 대한 처리
            for idx, ld_row in ld_batch.iterrows():
                ld_cd = ld_row["EMD_CD"]
                ld_geom = ld_row.geometry
                ld_area = ld_row["area"]

                # 공간 인덱스를 사용하여 이 법정동과 교차하는 모든 행정동 찾기
                # sindex는 내부적으로 R-tree 인덱스 사용
                possible_matches_idx = list(hd_gdf.sindex.intersection(ld_geom.bounds))
                possible_matches = hd_gdf.iloc[possible_matches_idx]

                best_match = None
                max_overlap_area = 0

                # 후보 행정동들만 자세히 분석
                for _, hd_row in possible_matches.iterrows():
                    hd_cd = hd_row["EMD_CD"]
                    hd_geom = hd_row.geometry

                    # 포함 여부 확인
                    if hd_geom.contains(ld_geom):
                        best_match = {
                            "EMD_CD": hd_cd,
                            "EMD_KOR_NM": hd_row["EMD_KOR_NM"],
                        }
                        break  # 가장 적합한 행정동을 찾았으므로 루프 종료

                    # 실제 교차 여부 확인
                    if ld_geom.intersects(hd_geom):

                        # 겹치는 영역 계산
                        intersection_geom = ld_geom.intersection(hd_geom)
                        intersection_area = intersection_geom.area

                        # 면적 비율 계산
                        overlap_ratio = intersection_area / ld_area

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

                # 가장 적합한 행정동 매칭 추가
                if best_match:
                    self.ld_hd_matching[ld_cd] = best_match

                processed += 1
                if processed % 100 == 0:
                    self.logger.info(
                        f"법정동 처리 진행: {processed}/{ld_count} ({processed/ld_count*100:.1f}%)"
                    )

        self.logger.info(
            f"법정동-행정동 매칭 테이블 생성 완료: {len(self.ld_hd_matching)}/{ld_count} 건 매칭됨"
        )
        return self.ld_hd_matching

    def _update_sync(self, wfile):
        """
        Updates the geocoder with the shp.

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.

        """
        self._prepare_updater_logger(f"{self.name}.log")

        self.prepare_ld_hd_matching_table()

        extras = {"yyyymm": self.yyyymm, "updater": "hd_addr_updater"}

        cnt = 0
        add_count = 0
        has_xy = 0

        # SHP 파일 읽기
        sr = ShpReader(self.shp_path, encoding="cp949")
        # shp_file = pyogrio.read_dataframe(self.shp_path, encoding="cp949")
        # with fiona.open(f"{self.shp_path}", "r", encoding="cp949") as shp_file:

        self.logger.info(f"Update: {self.outpath}{self.name}")

        # for all geometry
        n = 0
        for value, geom in sr:
            # EMD_CD: 51730380
            # EMD_ENG_NM: Gangnim-myeon
            # EMD_KOR_NM: 강림면

            # value = feature._asdict()
            # geom = shape(value.pop("geometry"))

            representative_point = self.representative_point(geom)
            # 14134909,4512659
            value["X좌표"] = int(representative_point.x)
            value["Y좌표"] = int(representative_point.y)

            try:
                ld_dic = self.prepare_dic(value)
                ld_dic["pos_cd"] = LD_ADDR_FILTER
                ld_dic["extras"] = extras

                val = {
                    "x": ld_dic["x"],
                    "y": ld_dic["y"],
                    # "z": ld_dic["zip"],
                    "h1_nm": ld_dic["h1_nm"],
                    "h23_nm": ld_dic["h23_nm"],
                    "hd_nm": ld_dic["hd_nm"],
                    "ld_nm": ld_dic["ld_nm"],
                    "h1_cd": ld_dic["h1_cd"],
                    "h23_cd": ld_dic["h23_cd"],
                    "hd_cd": ld_dic["hd_cd"],
                    "ld_cd": ld_dic["ld_cd"],
                    "pos_cd": ld_dic["pos_cd"],
                }
                val_json = json.dumps(val).encode()
                self.ctx = DbCreateContext(val, val_json, ld_dic)

                add_count += self.update_record(
                    ld_dic,
                    merge_if_exists=True,
                    force_delete=False,
                )
            except Exception as e:
                self.logger.error(f"Error: {e}")
                # continue
            cnt += 1
            if cnt % 10000 == 0:
                self.logger.info(f"{self.name} {cnt:,}")
                print(f"{self.name} {cnt:,}")

        self.logger.info(
            f"법정동 SHP {self.name}: {cnt:,} 건, : {has_xy:,} 건. hash 추가: {add_count:,} 건"
        )

        self.logger.info(f"완료: {self.name}")

        log_file = f"{self.outpath}{self.name}.log"
        with open(log_file, "r") as f:
            log = f.read()
            wfile.write(log)

        self._stop_updater_logging()
        return True

    def _update_sync_fiona(self, wfile):
        """
        Updates the geocoder with the shp.

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.

        """
        self._prepare_updater_logger(f"{self.name}.log")

        self.prepare_ld_hd_matching_table()

        extras = {"yyyymm": self.yyyymm, "updater": "hd_addr_updater"}

        cnt = 0
        add_count = 0
        has_xy = 0

        # SHP 파일 읽기
        with fiona.open(f"{self.shp_path}", "r", encoding="cp949") as shp_file:
            self.logger.info(f"Update: {self.outpath}{self.name}")

            # for all geometry
            n = 0
            for feature in shp_file:
                value = dict(feature.properties)

                # EMD_CD: 51730380
                # EMD_ENG_NM: Gangnim-myeon
                # EMD_KOR_NM: 강림면

                geom = shape(feature["geometry"])
                representative_point = self.representative_point(geom)
                # 14134909,4512659
                value["X좌표"] = int(representative_point.x)
                value["Y좌표"] = int(representative_point.y)

                try:
                    ld_dic = self.prepare_dic(value)
                    ld_dic["pos_cd"] = LD_ADDR_FILTER
                    ld_dic["extras"] = extras

                    val = {
                        "x": ld_dic["x"],
                        "y": ld_dic["y"],
                        # "z": ld_dic["zip"],
                        "h1_nm": ld_dic["h1_nm"],
                        "h23_nm": ld_dic["h23_nm"],
                        "hd_nm": ld_dic["hd_nm"],
                        "ld_nm": ld_dic["ld_nm"],
                        "h1_cd": ld_dic["h1_cd"],
                        "h23_cd": ld_dic["h23_cd"],
                        "hd_cd": ld_dic["hd_cd"],
                        "ld_cd": ld_dic["ld_cd"],
                        "pos_cd": ld_dic["pos_cd"],
                    }
                    val_json = json.dumps(val).encode()
                    self.ctx = DbCreateContext(val, val_json, ld_dic)

                    add_count += self.update_record(
                        ld_dic,
                        merge_if_exists=True,
                        force_delete=False,
                    )
                except Exception as e:
                    self.logger.error(f"Error: {e}")
                    # continue
                cnt += 1
                if cnt % 10000 == 0:
                    self.logger.info(f"{self.name} {cnt:,}")
                    print(f"{self.name} {cnt:,}")

        self.logger.info(
            f"법정동 SHP {self.name}: {cnt:,} 건, : {has_xy:,} 건. hash 추가: {add_count:,} 건"
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
        # EMD_CD: 51730380
        # EMD_ENG_NM: Gangnim-myeon
        # EMD_KOR_NM: 강림면
        ld_full = value["EMD_KOR_NM"]
        ld_cd = value["EMD_CD"]
        ld_nm = self.geocoder.hsimplifier.h4Hash(ld_full)

        # 매칭 행정동
        hd_cd = None
        hd_full = None
        hd_nm = None
        matching_hd = self.ld_hd_matching.get(ld_cd, {})
        if matching_hd:
            hd_cd = matching_hd["EMD_CD"]
            hd_full = matching_hd["EMD_KOR_NM"]
            hd_nm = hd_full
            # hd_nm = self.geocoder.hsimplifier.h4Hash(hd_full, keep_dong=True)

        # 시군구
        h23_cd = ld_cd[:5]
        h23_full = self.geocoder.hcodeMatcher.get_h23_nm(h23_cd)
        h23_nm = self.geocoder.hsimplifier.h23Hash(h23_full)

        # 광역시도코드, 이름
        h1_cd = self.geocoder.hcodeMatcher.get_h1_cd(h23_cd)
        h1_nm_full = self.geocoder.hcodeMatcher.get_h1_nm(h23_cd)
        h1_nm = self.geocoder.hsimplifier.h1Hash(h1_nm_full)

        d = {
            "h1_nm": h1_nm,  # 검색용
            "h1": h1_nm,  # db 추가용
            "h23_nm": h23_full,
            "h23_full": h23_full,
            "ld_nm": ld_full,
            "ld_full": ld_full,
            "hd_nm": hd_nm,
            "hd_full": hd_full,
            "h1_cd": h23_cd[:2],  # 광역시도 코드
            "h23_cd": h23_cd,
            "hd_cd": hd_cd,
            "ld_cd": ld_cd,
            "x": value["X좌표"],
            "y": value["Y좌표"],
        }

        return d

    def update_record(
        self, daddr: dict, merge_if_exists=True, force_delete=False, extras: dict = {}
    ):
        add_count = 0

        # 광역시도 시군구 법정동
        if self._del_and_put(
            f'{daddr["h1_nm"]} {daddr["h23_full"]} {daddr["ld_full"]}',
            merge_if_exists,
            force_delete=force_delete,
        ):
            add_count += 1
        if daddr["h3_nm"]:
            # 광역시도 h2_nm 법정동 (h3)
            if self._del_and_put(
                f'{daddr["h1_nm"]} {daddr["h2_nm"]} {daddr["ld_full"]}',
                merge_if_exists,
                force_delete=force_delete,
            ):
                add_count += 1
            # 광역시도 h3_nm 법정동 (h3)
            if self._del_and_put(
                f'{daddr["h1_nm"]} {daddr["h3_nm"]} {daddr["ld_full"]}',
                merge_if_exists,
                force_delete=force_delete,
            ):
                add_count += 1

        # 광역시도 법정동
        if self._del_and_put(
            f'{daddr["h1_nm"]} {daddr["ld_full"]}',
            merge_if_exists,
            force_delete=force_delete,
        ):
            add_count += 1

        # 시군구 법정동
        if self._del_and_put(
            f'{daddr["h23_full"]} {daddr["ld_full"]}',
            merge_if_exists,
            force_delete=force_delete,
        ):
            add_count += 1
        if daddr["h3_nm"]:
            # h2_nm 법정동 (h2)
            if self._del_and_put(
                f'{daddr["h2_nm"]} {daddr["ld_full"]}',
                merge_if_exists,
                force_delete=force_delete,
            ):
                add_count += 1
            # h3_nm 법정동 (h3)
            if self._del_and_put(
                f'{daddr["h3_nm"]} {daddr["ld_full"]}',
                merge_if_exists,
                force_delete=force_delete,
            ):
                add_count += 1

        # 법정동
        if self._del_and_put(
            f'{daddr["ld_full"]}', merge_if_exists, force_delete=force_delete
        ):
            add_count += 1

        return add_count

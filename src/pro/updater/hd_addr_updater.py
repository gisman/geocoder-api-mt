import asyncio

# import fiona
# import pyogrio
from .shp_reader import ShpReader

import json
from shapely.geometry import shape

from src.geocoder.geocoder import Geocoder
from src.geocoder.pos_cd import HD_ADDR, HD_ADDR_FILTER
from .updater import BaseUpdater, DbCreateContext


# TL_SCCO_CTPRVN.shp: 광역시도
# TL_SCCO_SIG.shp: 시군구
# TL_SCCO_GEMD.shp: 읍면동
# TL_SCCO_EMD.shp: 법정동
# TL_KODIS_BAS.shp: 우편번호
# TL_SCCO_LI.shp: 리


class HdAddrUpdater(BaseUpdater):
    """
    행정동 경계 Map을 이용하여 행정동 대표 주소 추가
    1. 매달 juso.go.kr에서 "구역의 도형 (.shp)" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 여러 .shp 파일이 생성됨.
    3. 파일의 위치는 /disk/hdd-lv/juso-data/전체분/{yyyymm}/map/*/TL_SCCO_GEMD.shp

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
        self.shp_path = f"{self.outpath}TL_SCCO_GEMD.shp"

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

    def _update_sync(self, wfile):
        """
        Updates the geocoder with the shp.

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.

        """
        self._prepare_updater_logger(f"{self.name}.log")

        cnt = 0
        add_count = 0
        has_xy = 0

        # SHP 파일 읽기
        sr = ShpReader(self.shp_path, encoding="cp949")
        # shp_file = pyogrio.read_dataframe(self.shp_path, encoding="cp949")
        # with fiona.open(f"{self.shp_path}", "r", encoding="cp949") as shp_file:

        self.logger.info(f"Update: {self.outpath}{self.name}")

        extras = {"yyyymm": self.yyyymm, "updater": "hd_addr_updater"}
        # for all geometry
        n = 0
        for value, geom in sr:
            # EMD_CD: 5173038000
            # EMD_KOR_NM: 강림면
            # EMD_ENG_NM: Gangnim-myeon

            representative_point = self.representative_point(geom)
            # 14134909,4512659
            value["X좌표"] = int(representative_point.x)
            value["Y좌표"] = int(representative_point.y)

            try:
                hd_dic = self.prepare_dic(value)
                hd_dic["pos_cd"] = HD_ADDR_FILTER
                hd_dic["extras"] = extras

                val = {
                    "x": hd_dic["x"],
                    "y": hd_dic["y"],
                    # "z": hd_dic["zip"],
                    "h1_nm": hd_dic["h1_nm"],
                    "h23_nm": hd_dic["h23_nm"],
                    "hd_nm": hd_dic["hd_nm"],
                    "h1_cd": hd_dic["h1_cd"],
                    "h23_cd": hd_dic["h23_cd"],
                    "hd_cd": hd_dic["hd_cd"],
                    "pos_cd": hd_dic["pos_cd"],
                }
                val_json = json.dumps(val).encode()
                self.ctx = DbCreateContext(val, val_json, hd_dic)
                add_count += self.update_record(
                    hd_dic, merge_if_exists=True, force_delete=False
                )
            except Exception as e:
                self.logger.error(f"Error: {e}")
                # continue
            cnt += 1
            if cnt % 10000 == 0:
                self.logger.info(f"{self.name} {cnt:,}")
                print(f"{self.name} {cnt:,}")

        self.logger.info(
            f"행정동 SHP {self.name}: {cnt:,} 건, : {has_xy:,} 건. hash 추가: {add_count:,} 건"
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

        cnt = 0
        add_count = 0
        has_xy = 0

        # SHP 파일 읽기
        with fiona.open(f"{self.shp_path}", "r", encoding="cp949") as shp_file:
            self.logger.info(f"Update: {self.outpath}{self.name}")

            extras = {"yyyymm": self.yyyymm, "updater": "hd_addr_updater"}
            # for all geometry
            n = 0
            for feature in shp_file:
                value = dict(feature.properties)

                # EMD_CD: 5173038000
                # EMD_KOR_NM: 강림면
                # EMD_ENG_NM: Gangnim-myeon

                geom = shape(feature["geometry"])
                representative_point = self.representative_point(geom)
                # 14134909,4512659
                value["X좌표"] = int(representative_point.x)
                value["Y좌표"] = int(representative_point.y)

                try:
                    hd_dic = self.prepare_dic(value)
                    hd_dic["pos_cd"] = HD_ADDR_FILTER
                    hd_dic["extras"] = extras

                    val = {
                        "x": hd_dic["x"],
                        "y": hd_dic["y"],
                        # "z": hd_dic["zip"],
                        "h1_nm": hd_dic["h1_nm"],
                        "h23_nm": hd_dic["h23_nm"],
                        "hd_nm": hd_dic["hd_nm"],
                        "h1_cd": hd_dic["h1_cd"],
                        "h23_cd": hd_dic["h23_cd"],
                        "hd_cd": hd_dic["hd_cd"],
                        "pos_cd": hd_dic["pos_cd"],
                    }
                    val_json = json.dumps(val).encode()
                    self.ctx = DbCreateContext(val, val_json, hd_dic)
                    add_count += self.update_record(
                        hd_dic, merge_if_exists=True, force_delete=False
                    )
                except Exception as e:
                    self.logger.error(f"Error: {e}")
                    # continue
                cnt += 1
                if cnt % 10000 == 0:
                    self.logger.info(f"{self.name} {cnt:,}")
                    print(f"{self.name} {cnt:,}")

        self.logger.info(
            f"행정동 SHP {self.name}: {cnt:,} 건, : {has_xy:,} 건. hash 추가: {add_count:,} 건"
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
        # EMD_CD: 5173038000
        # EMD_KOR_NM: 강림면
        # EMD_ENG_NM: Gangnim-myeon
        hd_full = value["EMD_KOR_NM"]
        hd_cd = value["EMD_CD"]
        hd_nm = hd_full
        # hd_nm = self.geocoder.hsimplifier.h4Hash(hd_full)

        h23_cd = hd_cd[:5]
        h23_full = self.geocoder.hcodeMatcher.get_h23_nm(h23_cd)
        h23_nm = self.geocoder.hsimplifier.h23Hash(h23_full)

        # 광역시도코드, 이름
        h1_cd = self.geocoder.hcodeMatcher.get_h1_cd(h23_cd)
        h1_nm_full = self.geocoder.hcodeMatcher.get_h1_nm(h23_cd)
        h1_nm = self.geocoder.hsimplifier.h1Hash(h1_nm_full)

        d = {
            "h1": h1_nm,  # db 추가용
            "h1_nm": h1_nm,  # 검색용
            "h23_nm": h23_full,
            "h23_full": h23_full,
            "hd_nm": hd_full,
            "hd_full": hd_full,
            "h1_cd": h23_cd[:2],  # 광역시도 코드
            "h23_cd": h23_cd,
            "hd_cd": hd_cd,
            "x": value["X좌표"],
            "y": value["Y좌표"],
        }

        return d

    def update_record(
        self, daddr: dict, merge_if_exists=True, force_delete=False, extras: dict = {}
    ):
        add_count = 0

        # 광역시도 시군구 행정동
        if self._del_and_put(
            f'{daddr["h1_nm"]} {daddr["h23_full"]} {daddr["hd_full"]}',
            merge_if_exists,
            force_delete=force_delete,
        ):
            add_count += 1
        if daddr["h3_nm"]:
            # 광역시도 h2_nm 행정동 (h3)
            if self._del_and_put(
                f'{daddr["h1_nm"]} {daddr["h2_nm"]} {daddr["hd_full"]}',
                merge_if_exists,
                force_delete=force_delete,
            ):
                add_count += 1
            # 광역시도 h3_nm 행정동 (h3)
            if self._del_and_put(
                f'{daddr["h1_nm"]} {daddr["h3_nm"]} {daddr["hd_full"]}',
                merge_if_exists,
                force_delete=force_delete,
            ):
                add_count += 1

        # 광역시도 행정동
        if self._del_and_put(
            f'{daddr["h1_nm"]} {daddr["hd_full"]}',
            merge_if_exists,
            force_delete=force_delete,
        ):
            add_count += 1

        # 시군구 행정동
        if self._del_and_put(
            f'{daddr["h23_full"]} {daddr["hd_full"]}',
            merge_if_exists,
            force_delete=force_delete,
        ):
            add_count += 1
        if daddr["h3_nm"]:
            # h2_nm 행정동 (h3)
            if self._del_and_put(
                f'{daddr["h2_nm"]} {daddr["hd_full"]}',
                merge_if_exists,
                force_delete=force_delete,
            ):
                add_count += 1
            # h3_nm 행정동 (h3)
            if self._del_and_put(
                f'{daddr["h3_nm"]} {daddr["hd_full"]}',
                merge_if_exists,
                force_delete=force_delete,
            ):
                add_count += 1

        # 행정동
        if self._del_and_put(
            f'{daddr["hd_full"]}',
            merge_if_exists,
            force_delete=force_delete,
        ):
            add_count += 1

        return add_count

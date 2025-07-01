import asyncio

# import fiona
import json
from shapely.geometry import shape

from src.geocoder.geocoder import Geocoder
from src.geocoder.pos_cd import H23_ADDR, H23_ADDR_FILTER
from .updater import BaseUpdater, DbCreateContext
from .shp_reader import ShpReader
import pyogrio

# TL_SCCO_CTPRVN.shp: 광역시도
# TL_SCCO_SIG.shp: 시군구
# TL_SCCO_GEMD.shp: 읍면동
# TL_SCCO_EMD.shp: 법정동
# TL_KODIS_BAS.shp: 우편번호
# TL_SCCO_LI.shp: 리


class H23AddrUpdater(BaseUpdater):
    """
    시군구 경계 Map을 이용하여 시군구 대표 주소 추가
    1. 매달 juso.go.kr에서 "구역의 도형 (.shp)" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 여러 .shp 파일이 생성됨.
    3. 파일의 위치는 /disk/hdd-lv/juso-data/전체분/{yyyymm}/map/*/TL_SCCO_SIG.shp

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
        self.shp_path = f"{self.outpath}TL_SCCO_SIG.shp"

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
        # 파일 읽기
        # 한 줄씩 객체 생성해서 update_record() 호출
        self._prepare_updater_logger(f"{self.name}.log")

        cnt = 0
        add_count = 0
        has_xy = 0

        # from_crs = pyproj.CRS("EPSG:5179")
        # to_crs = pyproj.CRS("EPSG:5186")

        # proj_transform = pyproj.Transformer.from_crs(
        #     from_crs, to_crs, always_xy=True
        # ).transform

        sr = ShpReader(self.shp_path, encoding="cp949")
        # with pyogrio.open(f"{self.shp_path}", encoding="cp949") as shp_file:
        # with fiona.open(f"{self.shp_path}", "r", encoding="cp949") as shp_file:
        self.logger.info(f"Update: {self.outpath}{self.name}")

        extras = {"yyyymm": self.yyyymm, "updater": "h23_addr_updater"}
        n = 0

        for value, geom in sr:
            # print(value, geom)

            representative_point = self.representative_point(geom)
            # 14134909,4512659
            value["X좌표"] = int(representative_point.x)
            value["Y좌표"] = int(representative_point.y)

            try:
                h23_dic = self.prepare_dic(value)
                h23_dic["pos_cd"] = H23_ADDR_FILTER
                h23_dic["extras"] = extras

                val = {
                    "x": h23_dic["x"],
                    "y": h23_dic["y"],
                    # "z": h23_dic["zip"],
                    "h1_cd": h23_dic["h1_cd"],
                    "h23_cd": h23_dic["h23_cd"],
                    "h1_nm": h23_dic["h1_nm"],
                    "h23_nm": h23_dic["h23_nm"],
                    "pos_cd": h23_dic["pos_cd"],
                }
                val_json = json.dumps(val).encode()
                self.ctx = DbCreateContext(val, val_json, h23_dic)

                add_count += self.update_record(
                    h23_dic,
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
            f"시군구 SHP {self.name}: {cnt:,} 건, : {has_xy:,} 건. hash 추가: {add_count:,} 건"
        )

        self.logger.info(f"완료: {self.name}")

        log_file = f"{self.outpath}{self.name}.log"
        with open(log_file, "r") as f:
            log = f.read()
            wfile.write(log)

        self._stop_updater_logging()
        return True

    def _update_sync_pyogrio(self, wfile):
        """
        Updates the geocoder with the shp.

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.

        """
        # 파일 읽기
        # 한 줄씩 객체 생성해서 update_record() 호출
        self._prepare_updater_logger(f"{self.name}.log")

        cnt = 0
        add_count = 0
        has_xy = 0

        # from_crs = pyproj.CRS("EPSG:5179")
        # to_crs = pyproj.CRS("EPSG:5186")

        # proj_transform = pyproj.Transformer.from_crs(
        #     from_crs, to_crs, always_xy=True
        # ).transform

        sr = ShpReader(self.shp_path, encoding="cp949")
        for value, geom in sr:
            print(value, geom)

        shp_file = pyogrio.read_dataframe(self.shp_path, encoding="cp949")

        # with pyogrio.open(f"{self.shp_path}", encoding="cp949") as shp_file:
        # with fiona.open(f"{self.shp_path}", "r", encoding="cp949") as shp_file:
        self.logger.info(f"Update: {self.outpath}{self.name}")

        extras = {"yyyymm": self.yyyymm, "updater": "h23_addr_updater"}

        # for all geometry
        n = 0
        for feature in shp_file.itertuples(
            index=False
        ):  # index=False to exclude the index
            # for feature in pyogrio.read_bounds(self.shp_path, encoding="cp949"):
            # for feature in shp_file:
            # Convert pandas Series to dict for compatibility
            value = feature._asdict()
            # Remove geometry from the dict as it's handled separately
            if "geometry" in value:
                del value["geometry"]

            # SIG_CD: 51170
            # SIG_ENG_NM: Donghae-si
            # SIG_KOR_NM: 동해시

            geom = shape(feature.geometry)
            representative_point = self.representative_point(geom)
            # 14134909,4512659
            value["X좌표"] = int(representative_point.x)
            value["Y좌표"] = int(representative_point.y)

            try:
                h23_dic = self.prepare_dic(value)
                h23_dic["pos_cd"] = H23_ADDR_FILTER
                h23_dic["extras"] = extras

                val = {
                    "x": h23_dic["x"],
                    "y": h23_dic["y"],
                    # "z": h23_dic["zip"],
                    "h1_cd": h23_dic["h1_cd"],
                    "h23_cd": h23_dic["h23_cd"],
                    "h1_nm": h23_dic["h1_nm"],
                    "h23_nm": h23_dic["h23_nm"],
                    "pos_cd": h23_dic["pos_cd"],
                }
                val_json = json.dumps(val).encode()
                self.ctx = DbCreateContext(val, val_json, h23_dic)

                add_count += self.update_record(
                    h23_dic,
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
            f"시군구 SHP {self.name}: {cnt:,} 건, : {has_xy:,} 건. hash 추가: {add_count:,} 건"
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
        # 파일 읽기
        # 한 줄씩 객체 생성해서 update_record() 호출
        self._prepare_updater_logger(f"{self.name}.log")

        cnt = 0
        add_count = 0
        has_xy = 0

        # from_crs = pyproj.CRS("EPSG:5179")
        # to_crs = pyproj.CRS("EPSG:5186")

        # proj_transform = pyproj.Transformer.from_crs(
        #     from_crs, to_crs, always_xy=True
        # ).transform

        with pyogrio.open(f"{self.shp_path}", encoding="cp949") as shp_file:
            # with fiona.open(f"{self.shp_path}", "r", encoding="cp949") as shp_file:
            self.logger.info(f"Update: {self.outpath}{self.name}")

            extras = {"yyyymm": self.yyyymm, "updater": "h23_addr_updater"}

            # for all geometry
            n = 0
            for feature in shp_file:
                value = dict(feature.properties)

                # SIG_CD: 51170
                # SIG_ENG_NM: Donghae-si
                # SIG_KOR_NM: 동해시

                geom = shape(feature["geometry"])
                representative_point = self.representative_point(geom)
                # 14134909,4512659
                value["X좌표"] = int(representative_point.x)
                value["Y좌표"] = int(representative_point.y)

                try:
                    h23_dic = self.prepare_dic(value)
                    h23_dic["pos_cd"] = H23_ADDR_FILTER
                    h23_dic["extras"] = extras

                    val = {
                        "x": h23_dic["x"],
                        "y": h23_dic["y"],
                        # "z": h23_dic["zip"],
                        "h1_cd": h23_dic["h1_cd"],
                        "h23_cd": h23_dic["h23_cd"],
                        "h1_nm": h23_dic["h1_nm"],
                        "h23_nm": h23_dic["h23_nm"],
                        "pos_cd": h23_dic["pos_cd"],
                    }
                    val_json = json.dumps(val).encode()
                    self.ctx = DbCreateContext(val, val_json, h23_dic)

                    add_count += self.update_record(
                        h23_dic,
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
            f"시군구 SHP {self.name}: {cnt:,} 건, : {has_xy:,} 건. hash 추가: {add_count:,} 건"
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
        h23_full = value["SIG_KOR_NM"]
        h23_cd = value["SIG_CD"]
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
            "h23_cd": h23_cd,  # 시군구 코드
            "h1_cd": h23_cd[:2],  # 광역시도 코드
            "x": value["X좌표"],
            "y": value["Y좌표"],
        }

        return d

    def update_record(self, daddr: dict, merge_if_exists=True, extras: dict = {}):
        add_count = 0

        if self._del_and_put(
            f'{daddr["h1_nm"]} {daddr["h23_full"]}', merge_if_exists, force_delete=False
        ):
            add_count += 1
        if daddr["h3_nm"]:
            # h2
            if self._del_and_put(
                f'{daddr["h1_nm"]} {daddr["h2_nm"]}',
                merge_if_exists,
                force_delete=False,
            ):
                add_count += 1
            # h3
            if self._del_and_put(
                f'{daddr["h1_nm"]} {daddr["h3_nm"]}',
                merge_if_exists,
                force_delete=False,
            ):
                add_count += 1

        if self._del_and_put(
            f'{daddr["h23_full"]}', merge_if_exists, force_delete=False
        ):
            add_count += 1
        if daddr["h3_nm"]:
            # h2
            if self._del_and_put(
                f'{daddr["h2_nm"]}',
                merge_if_exists,
                force_delete=False,
            ):
                add_count += 1
            # h3
            if self._del_and_put(
                f'{daddr["h3_nm"]}',
                merge_if_exists,
                force_delete=False,
            ):
                add_count += 1

        return add_count

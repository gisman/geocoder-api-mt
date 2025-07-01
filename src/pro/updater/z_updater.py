import asyncio
import json
import geopandas as gpd
from shapely.geometry import Point
import glob

from src.geocoder.geocoder import Geocoder
from .updater import BaseUpdater


class ZUpdater(BaseUpdater):
    """
    A class that represents a monthly updater for the geocoder and reverse geocoder.
    1. 매달 juso.go.kr에서 "구역의 도형 (.shp)" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 TL_KODIS_BAS.shp 등의 파일이 생성됨.
    3. 파일의 위치는 /disk/hdd-lv/juso-data/전체분/{yyyymm}/map/*/TL_KODIS_BAS.shp

    Attributes:
        yyyymm (str): 다운받은 파일 경로의 yyyymm.
        geocoder (Geocoder): The geocoder instance.

    Methods:
        __init__(yyyymm: str, geocoder: Geocoder): Initializes a ZUpdater instance.
        update(wfile): Updates the geocoder with the address entries.

    """

    def __init__(self, yyyymm: str, geocoder: Geocoder):
        super().__init__(geocoder)
        self.yyyymm = yyyymm
        self.name = f"z_updater_{yyyymm}"
        # self.navi_dic = {}

        self.last_match = None  # 마지막 매칭 geometry 캐시

        # 파일 다운로드 경로 지정
        self.outpath = f"{self.JUSO_DATA_DIR}/전체분/{yyyymm}/map/"

    def cache_shp(self, h1_cd=None):
        """
        Reads all .shp files from the specified directory and merges them into a single GeoDataFrame.
        # /disk/hdd-lv/juso-data/전체분/{yyyymm}/map/*/TL_KODIS_BAS.shp 를 모두 읽어 gdf에 합치기
        """
        # 경로에서 모든 .shp 파일 검색
        shp_files = glob.glob(f"{self.outpath}*/TL_KODIS_BAS.shp")
        if h1_cd:
            shp_files = [f for f in shp_files if f.split("/")[-2].startswith(h1_cd)]

        if not shp_files:
            if hasattr(self, "logger") and self.logger:
                self.logger.error("No shapefiles found in the specified directory.")
            return

        # 모든 .shp 파일 읽어서 GeoDataFrame으로 병합
        gdfs = []
        for shp_file in shp_files:
            try:
                gdf = gpd.read_file(shp_file, encoding="cp949")
                # simplify geometry
                gdf["geometry"] = gdf.simplify(tolerance=5, preserve_topology=True)

                gdfs.append(gdf)
            except Exception as e:
                if hasattr(self, "logger") and self.logger:
                    self.logger.error(f"Error reading {shp_file}: {e}")

        import pandas as pd

        if gdfs:
            self.gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
            if hasattr(self, "logger") and self.logger:
                self.logger.info(f"Successfully merged {len(gdfs)} shapefiles.")
            # 공간 인덱스 생성
            self.spatial_index = self.gdf.sindex
        else:
            if hasattr(self, "logger") and self.logger:
                self.logger.error("No valid shapefiles could be read.")

    def search_shp(self, x, y):
        """
        Optimized search for the shapefile entry that contains the given x, y coordinates.

        Args:
            x (float): The x-coordinate (longitude).
            y (float): The y-coordinate (latitude).

        Returns:
            dict: A dictionary containing the matched area's code and name.
        """
        # 대상 점 생성
        target_point = Point(x, y)

        # 캐시 검사
        if self.last_match is not None and self.last_match.geometry.contains(
            target_point
        ):
            return {
                "zip": self.last_match.get("BAS_ID", None),
            }

        # 공간 인덱스를 사용해 잠재적 매칭 후보 검색 (bounding box)
        possible_matches_index = list(
            self.spatial_index.intersection(target_point.bounds)
        )
        if not possible_matches_index:
            return {"zip": None}

        # 후보군 필터링
        possible_matches = self.gdf.iloc[possible_matches_index]

        # 정확히 포함하는 객체만 필터링
        precise_match = possible_matches[
            possible_matches.geometry.contains(target_point)
        ]

        if not precise_match.empty:
            match = precise_match.iloc[0]
            self.last_match = match
            return {
                "zip": match.get("BAS_ID", None),
            }
        else:
            return {"zip": None}

    async def update(self, wfile):
        # CPU 바운드 작업을 별도의 스레드로 오프로드
        return await asyncio.to_thread(self._update_sync, wfile)

    def _update_sync(self, wfile):
        self._prepare_updater_logger(f"{self.name}.log")

        log_file = f"{self.outpath}{self.name}.log"
        self.cache_shp()

        # iterate geocoder
        n = 0
        for item in self.geocoder:
            # search
            key = item[0].decode("utf8")
            try:
                dic = json.loads(item[1].decode("utf8"))
                if not dic[0]["x"] or not dic[0]["y"]:
                    continue

                hd_dic = self.search_shp(dic[0]["x"], dic[0]["y"])

                # update
                changed = False
                for d in dic:
                    if d.get("pos_cd") == None and d.get("z", "") != hd_dic["zip"]:
                        d["z"] = hd_dic["zip"]
                        changed = True

                if changed:
                    self.geocoder.db.put(key, dic)

                n += 1
                if n % 100000 == 0:
                    print(f"update {self.name} {n:,} {key}")
            except Exception as e:
                print(f"Error processing key {key}: {e}")

        with open(log_file, "r") as f:
            log = f.read()
            wfile.write(log)

        self._stop_updater_logging()
        return True

    def update_rev_gc(self, wfile):
        pass

import asyncio
import json
import pyproj

from src.geocoder.geocoder import Geocoder
from src.geocoder.pos_cd import *
from .updater import BaseUpdater, DbCreateContext


class H1AddrUpdater(BaseUpdater):
    """
    광역시도 대표 주소 추가. 지오코딩 결과를 좌표로 사용.

    실행: curl 'http://localhost:4009/update_h1_addr'

    Attributes:
        geocoder (Geocoder): The geocoder instance.

    Methods:
        __init__(name: str, geocoder: Geocoder): Initializes a instance.
        prepare_dic(key, value): Prepares a dictionary for the address entry.
        update(wfile): Updates the geocoder with the address.
    """

    h1_addrs = [
        "서울특별시 중구 세종대로 110 서울특별시청",
        "부산광역시 연제구 중앙대로 1001(연산동) 부산광역시청",
        "대구광역시 중구 공평로 88 (동인동1가) 대구광역시청",
        "인천광역시 남동구 정각로29 (구월동 1138) 인천광역시청",
        "광주광역시 서구 내방로 111(치평동) 광주광역시청",
        "대전 서구 둔산로 100 대전광역시청",
        "울산광역시 남구 중앙로 201 (신정동) 울산광역시청",
        "세종특별자치시 한누리대로 2130 (보람동) 세종특별자치시청",
        "경기도 수원시 영통구 도청로 30 경기도청",
        "강원특별자치도 춘천시 중앙로1 (봉의동) 강원특별자치도청",
        "충청북도 청주시 상당구 상당로 82(문화동) 충청북도청",
        "충청남도 홍성군 홍북면 충남대로 21 충청남도청",
        "전북 전주시 완산구 효자로 225 전북특별자치도청",
        "전남 무안군 삼향읍 오룡길 1(남악리 100) 전라남도청",
        "경상북도 안동시 풍천면 도청대로 455 경상북도청",
        "경상남도 창원시 의창구 중앙대로 300(사림동) 경상남도청",
        "제주특별자치도 제주시 문연로 6(연동) 제주특별자치도청",
    ]

    def __init__(self, geocoder: Geocoder):
        super().__init__(geocoder)
        # 파일 다운로드 경로 지정
        self.name = "h1_addr_updater"
        self.outpath = f"{self.JUSO_DATA_DIR}/전체분/"

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
        # 상수 주소를 한 줄씩 객체 생성해서 update_record() 호출
        self._prepare_updater_logger(f"{self.name}.log")

        cnt = 0
        add_count = 0
        has_xy = 0

        # from_crs = pyproj.CRS("EPSG:5186")
        # to_crs = pyproj.CRS("EPSG:5179")

        # proj_transform = pyproj.Transformer.from_crs(
        #     from_crs, to_crs, always_xy=True
        # ).transform

        # geocode
        count = 0
        add_count = 0
        extras = {"updater": "h1_addr_updater"}
        for addr in self.h1_addrs:
            count += 1
            geocode_result = self.geocoder.search(addr)
            if geocode_result:
                h1_dic = self.prepare_dic(geocode_result)
                h1_dic["pos_cd"] = H1_ADDR_FILTER
                h1_dic["extras"] = extras

                val = {
                    "x": h1_dic["x"],
                    "y": h1_dic["y"],
                    # "z": h1_dic["zip"],
                    "h1_nm": h1_dic["h1_nm"],
                    "h1_cd": h1_dic["h1_cd"],
                    "pos_cd": h1_dic["pos_cd"],
                    # "hd_cd": h1_dic["hd_cd"],
                    # "ld_cd": h1_dic["ld_cd"],
                    # "road_cd": h1_dic["road_cd"],
                    # "bld_mgt_no": h1_dic["bld_mgt_no"],
                    # "hd_nm": h1_dic["hd_nm"],
                    # "road_nm": h1_dic["road_nm"],
                    # "bm": [],
                }
                val_json = json.dumps(val).encode()
                self.ctx = DbCreateContext(val, val_json, h1_dic)

                add_count += self.update_record(h1_dic, merge_if_exists=True)
                self.logger.info(f"Geocode success for: {addr}")
            else:
                self.logger.error(f"Geocode failed for: {addr}")
            self.logger.info(f"Update: {self.outpath}{self.name}")

        self.logger.info(
            f"광역시도 ADDR {self.name}: {cnt:,} 건, : {has_xy:,} 건. hash 추가: {add_count:,} 건"
        )

        self.logger.info(f"완료: {self.name}")

        log_file = f"{self.outpath}{self.name}.log"
        with open(log_file, "r") as f:
            log = f.read()
            wfile.write(log)

        self._stop_updater_logging()
        return True

    def prepare_dic(self, geocode_result):
        """
        Prepares a dictionary for the address.

        Args:
            value: The value of the address.

        Returns:
            dict: The prepared dictionary for the address.

        """
        h1_nm = geocode_result["h1_nm"]

        d = {
            "h1_nm": h1_nm,  # 검색용
            "h1_cd": geocode_result["h23_cd"][:2],  # 검색용
            "x": geocode_result["x"],
            "y": geocode_result["y"],
        }

        return d

    def update_record(self, daddr: dict, merge_if_exists=True, extras: dict = {}):
        add_count = 0

        # pos_cd가 있으면 주소가 완전하지 않으므로 추가
        if self._del_and_put(daddr["h1_nm"], merge_if_exists, force_delete=True):
            add_count += 1

        return add_count

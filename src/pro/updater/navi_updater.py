import asyncio
import csv

# import rocksdb3
# import aimrocks
from src.geocoder.db.gimi9_rocks import WriteBatch
from src.geocoder.geocoder import Geocoder
from .updater import BaseUpdater
from .csv_reader import CsvReader

# from ..util.hd_and_z_search_util import update_hd_and_z
from .hd_updater import HdUpdater
from .z_updater import ZUpdater
from .big_cache import BigCache

NAVI_CACHE_COLS = [
    "bld_mgt_no",
    "zip",
    "bld_reg",
    "bld_nm",
    "hd_cd",
    "hd_nm",
    "bld_x",
    "bld_y",
    # "이동사유코드",
]


class NaviUpdater(BaseUpdater):
    """
    A class that represents a monthly updater for the geocoder.
    1. 매달 juso.go.kr에서 "위치정보요약DB" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 navi_busan.txt 등의 파일이 생성됨.
    3. 파일의 위치는 ~/projects/geocoder-api/juso-data/전체분/navi

    Attributes:
        name (str): 다운받은 파일명.
        geocoder (Geocoder): The geocoder instance.

    Methods:
        __init__(name: str, geocoder: Geocoder): Initializes a NaviUpdater instance.
        prepare_dic_navi(key, value): Prepares a dictionary for the match_bld data
        update(wfile): Updates the geocoder with the address entries.

    """

    BATCH_SIZE: int = 5000  # 배치 크기

    def __init__(self, yyyymm: str, name: str, geocoder: Geocoder):
        super().__init__(geocoder)
        self.yyyymm = yyyymm
        self.name = name
        self.navi_dic = {}

        # 파일 다운로드 경로 지정
        self.outpath = f"{self.JUSO_DATA_DIR}/전체분/{yyyymm}/navi/"

        self.big_cache = BigCache()

    def cache_navi_dic(self, navi_dic):
        val = {k: v for k, v in navi_dic.items() if k in NAVI_CACHE_COLS}

        key = f'{self.name}_{self.yyyymm}_{navi_dic["bld_mgt_no"]}'
        self.big_cache.put(key, val)

    def cache_navi_dic_mem(self, navi_dic):
        usecols = [
            "bld_mgt_no",
            "zip",
            "bld_reg",
            "bld_nm",
            "hd_cd",
            "hd_nm",
            "bld_x",
            "bld_y",
            # "이동사유코드",
        ]
        self.navi_dic[navi_dic["bld_mgt_no"]] = {
            k: v for k, v in navi_dic.items() if k in usecols
        }

    def search_navi(self, bld_mgt_no):
        key = f"{self.name}_{self.yyyymm}_{bld_mgt_no}"
        d = self.big_cache.get(key)
        return d or {}

    def search_navi_mem(self, bld_mgt_no):
        d = self.navi_dic.get(bld_mgt_no)
        return d or {}

    def prepare_dic_jibun(self, value):
        d_navi = self.search_navi(value["건물관리번호"])

        d = {
            "h1_nm": value["시도명"],
            "h23_nm": value["시군구명"] or value["시도명"],  # 세종시 예외 처리
            "ld_nm": value["읍면동명"],
            "hd_nm": d_navi.get("hd_nm"),
            "ri_nm": value["리명"],
            "road_nm": "",
            "undgrnd_yn": "",
            "bld1": "",
            "bld2": "",
            "san": value["산여부"],
            "bng1": value["지번본번"],
            "bng2": value["지번부번"],
            "bld_reg": d_navi.get("bld_reg"),
            "bld_nm_text": "",
            "bld_nm": d_navi.get("bld_nm"),
            "ld_cd": "",
            "hd_cd": d_navi.get("hd_cd"),
            "road_cd": "",
            "zip": d_navi.get("zip"),
            "bld_mgt_no": value["건물관리번호"],
            "bld_x": d_navi.get("bld_x"),
            "bld_y": d_navi.get("bld_y"),
        }

        if d["bld_x"] and not d["hd_cd"]:
            self.update_hd(d)
        if d["bld_x"] and not d["zip"]:
            self.update_z(d)

        return d

    def prepare_dic_navi(self, value):
        """
        Prepares a dictionary for the address entry.

        Args:
            value: The value of the address entry.

        Returns:
            dict: The prepared dictionary for the address entry.

        """
        d = {
            "h1_nm": value["시도명"],
            "h23_nm": value["시군구명"] or value["시도명"],  # 세종시 예외 처리
            "ld_nm": value["읍면동명"],
            "hd_nm": value["행정동명"],
            "ri_nm": "",
            "road_nm": value["도로명"],
            "undgrnd_yn": value["지하여부"],
            "bld1": value["건물본번"],
            "bld2": value["건물부번"],
            "san": "",
            "bng1": "",
            "bng2": "",
            "bld_reg": value["시군구용건물명"],
            "bld_nm_text": "",
            "bld_nm": value["상세건물명"],  # 동명
            "h1_cd": value["주소관할읍면동코드"][:2],
            "h23_cd": value["주소관할읍면동코드"][:5],
            "ld_cd": value["주소관할읍면동코드"],
            "hd_cd": value["행정동코드"],
            "road_cd": value["도로명코드"],
            "zip": value["우편번호"],
            "bld_mgt_no": value["건물관리번호"],
            "bld_x": value["건물중심점_x좌표"] or value["출입구_x좌표"],
            "bld_y": value["건물중심점_y좌표"] or value["출입구_y좌표"],
        }

        if d["bld_x"] and not d["hd_cd"]:
            self.update_hd(d)
        if d["bld_x"] and not d["zip"]:
            self.update_z(d)

        return d

    async def update(self, wfile):
        # CPU 바운드 작업을 별도의 스레드로 오프로드
        return await asyncio.to_thread(self._update_sync, wfile)

    def name_to_h1_cd(self, name):
        h1_map = {
            "match_build_gangwon.txt": "51",
            "match_build_gyunggi.txt": "41",
            "match_build_gyeongnam.txt": "48",
            "match_build_gyeongbuk.txt": "47",
            "match_build_gwangju.txt": "29",
            "match_build_daegu.txt": "27",
            "match_build_daejeon.txt": "30",
            "match_build_busan.txt": "26",
            "match_build_seoul.txt": "11",
            "match_build_sejong.txt": "36",
            "match_build_ulsan.txt": "31",
            "match_build_incheon.txt": "28",
            "match_build_jeonnam.txt": "46",
            "match_build_jeonbuk.txt": "52",
            "match_build_jeju.txt": "50",
            "match_build_chungnam.txt": "44",
            "match_build_chungbuk.txt": "43",
        }

        return h1_map.get(name)

    def _update_sync(self, wfile):
        self._prepare_updater_logger(f"{self.name}.log")

        log_file = f"{self.outpath}{self.name}.log"

        # import cProfile
        # import pstats
        # from pstats import SortKey

        # # cProfile을 사용하여 성능 측정
        # profiler = cProfile.Profile()
        # profiler.enable()

        h1_cd = self.name_to_h1_cd(self.name)

        self.hu = HdUpdater("202504", None)
        self.hu.cache_shp(h1_cd)

        self.zu = ZUpdater("202504", None)
        self.zu.cache_shp(h1_cd)

        # match_build_*.txt
        if not self.update_navi(wfile):
            return False

        # profiler.disable()

        # # 결과 분석
        # stats = pstats.Stats(profiler).sort_stats(SortKey.CUMULATIVE)
        # stats.print_stats(20)  # 상위 20개 항목 출력

        # # 결과 파일로 저장 (나중에 snakeviz로 시각화 가능)
        # stats.dump_stats("ld_hd_matching_profile.prof")
        # return True

        if not self.update_jibun(wfile):
            return False

        with open(log_file, "r") as f:
            log = f.read()
            wfile.write(log)

        self._stop_updater_logging()
        return True

    def update_navi(self, wfile):
        """
        Updates the geocoder with the address entries.

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.

        """
        # 파일 읽기
        # 한 줄씩 객체 생성해서 update_record() 호출

        cnt = 0
        add_count = 0
        has_xy = 0

        with open(
            f"{self.outpath}{self.name}", "r", encoding="euc-kr", errors="ignore"
        ) as file:
            self.logger.info(f"Update navi: {self.outpath}{self.name}")

            # 전체 row수 얻기
            total_rows = sum(1 for _ in file)
            file.seek(0)  # Reset file pointer to the beginning
            self.logger.info(f"Total rows in {self.name}: {total_rows:,}")

            csv_reader = CsvReader()
            reader = csv.reader(file, delimiter="|")
            extras = {"yyyymm": self.yyyymm, "updater": "navi_updater"}
            batch = WriteBatch()
            # batch = aimrocks.WriteBatch()
            bcount = 0
            # batch = rocksdb3.WriterBatch()
            for value in csv_reader.iter_navi_csv(reader):
                address_dic = self.prepare_dic_navi(value)

                # # [TODO 삭제]
                # if (
                #     address_dic.get("ld_nm") != "신북면"
                #     or address_dic.get("hd_nm") != "신북면"
                # ):
                #     continue

                # [TODO: 지번 업데이트 제외 테스트]
                self.cache_navi_dic(address_dic)

                # # [TODO 삭제]
                # continue

                added = self.update_record(address_dic, extras=extras)
                if address_dic["bld_x"]:
                    has_xy += 1
                add_count += added
                bcount += added
                cnt += 1
                if cnt % 10000 == 0:
                    progress = (cnt / total_rows) * 100
                    self.logger.info(
                        f"navi {self.name} {cnt:,} +{add_count:,} ({progress:.2f}%)"
                    )
                if bcount > self.BATCH_SIZE:
                    self.write_batch(batch)
                    batch.clear()
                    # batch = WriteBatch()
                    # batch = aimrocks.WriteBatch()
                    bcount = 0
                    # batch = rocksdb3.WriterBatch()

        # 마지막 배치 처리
        if bcount != 0:
            self.write_batch(batch)
            batch.clear()

        self.ldb.flush()

        self.logger.info(
            f"건물정보 navi {self.name}: {cnt:,} 건, 좌표있는 건물: {has_xy:,} 건. hash 추가: {add_count:,} 건"
        )

        self.logger.info(f"완료 navi: {self.name}")
        return True

    def update_jibun(self, wfile):
        """
        Updates the geocoder with the jibun entries.

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.

        """
        # 파일 읽기
        # 한 줄씩 객체 생성해서 update_record() 호출

        extras = {"yyyymm": self.yyyymm, "updater": "navi_updater:jibun"}

        cnt = 0
        add_count = 0
        has_xy = 0

        # match_jibun_*.txt
        jubun_name = self.name.replace(
            "build", "jibun"
        )  # match_build_busan.txt -> match_jibun_busan.txt 파일명으로 변경

        with open(
            f"{self.outpath}{jubun_name}", "r", encoding="euc-kr", errors="ignore"
        ) as file:
            self.logger.info(f"Update 지번: {self.outpath}{jubun_name}")

            # 전체 row수 얻기
            total_rows = sum(1 for _ in file)
            file.seek(0)  # Reset file pointer to the beginning
            self.logger.info(f"Total rows in {jubun_name}: {total_rows:,}")

            csv_reader = CsvReader()
            reader = csv.reader(file, delimiter="|")
            batch = WriteBatch()
            # batch = aimrocks.WriteBatch()
            bcount = 0
            # batch = rocksdb3.WriterBatch()
            for value in csv_reader.iter_jibun_csv(reader):

                # # [TODO 삭제]
                # if value.get("읍면동명") != "신북면":
                #     continue

                # # [TODO 삭제]
                # if cnt < 460000:
                #     cnt += 1
                #     continue

                address_dic = self.prepare_dic_jibun(value)

                added = self.update_record(address_dic, extras=extras, batch=batch)
                add_count += added
                bcount += added
                if address_dic["bld_x"]:
                    has_xy += 1
                cnt += 1
                if cnt % 10000 == 0:
                    progress = (cnt / total_rows) * 100
                    self.logger.info(
                        f"지번 {jubun_name} {cnt:,} {add_count:,} ({progress:.2f}%)"
                    )
                if bcount > self.BATCH_SIZE:
                    self.write_batch(batch)
                    batch.clear()
                    # batch = aimrocks.WriteBatch()
                    bcount = 0
                    # batch = rocksdb3.WriterBatch()

        # 마지막 배치 처리
        if bcount != 0:
            self.write_batch(batch)
            batch.clear()

        self.ldb.flush()

        self.logger.info(
            f"지번정보 {jubun_name}: {cnt:,} 건, 좌표있는 건물: {has_xy:,} 건. hash 추가: {add_count:,} 건"
        )

        self.logger.info(f"완료: {jubun_name}")
        return True

    def update_hd_and_z(self, val):
        if val.get("pos_cd") != None:
            return

        # hu = HdUpdater("202504", None)

        x = val["bld_x"]
        y = val["bld_y"]

        # self.hu.cache_shp(val["h23_cd"][:2])
        hd_dic = self.hu.search_shp(x, y)
        if hd_dic:
            # val["hc"] = hd_dic["hd_cd"]
            val["hd_cd"] = hd_dic["hd_cd"]
            val["hd_nm"] = hd_dic["hd_nm"]

        if val.get("z"):
            return

        # z 값이 없으면 우편번호로 설정
        # zu = ZUpdater("202504", None)
        z_dic = self.zu.search_shp(x, y)
        if z_dic and z_dic["zip"]:
            val["zip"] = z_dic["zip"]

    def update_hd(self, val):
        """
        Updates the hd_cd and hd_nm in the address dictionary.

        Args:
            val: The address dictionary to update.

        Returns:
            None
        """
        if val.get("pos_cd") != None:
            return

        # hu = HdUpdater("202504", None)

        x = val["bld_x"]
        y = val["bld_y"]

        # self.hu.cache_shp(val["h23_cd"][:2])
        hd_dic = self.hu.search_shp(x, y)
        if hd_dic:
            # val["hc"] = hd_dic["hd_cd"]
            val["hd_cd"] = hd_dic["hd_cd"]
            val["hd_nm"] = hd_dic["hd_nm"]

    def update_z(self, val):
        """
        Updates the zip code in the address dictionary.

        Args:
            val: The address dictionary to update.

        Returns:
            None
        """
        # z 값이 없으면 우편번호로 설정
        # zu = ZUpdater("202504", None)
        if val.get("zip"):
            return

        x = val["bld_x"]
        y = val["bld_y"]

        z_dic = self.zu.search_shp(x, y)
        if z_dic and z_dic["zip"]:
            val["zip"] = z_dic["zip"]

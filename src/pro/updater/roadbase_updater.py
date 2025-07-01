import asyncio
import csv

from src.geocoder.db.gimi9_rocks import WriteBatch

# import aimrocks
import pyproj

from src.geocoder.geocoder import Geocoder
from .updater import BaseUpdater
from .csv_reader import CsvReader

from .hd_updater import HdUpdater
from .z_updater import ZUpdater


class RoadbaseUpdater(BaseUpdater):
    """
    A class that represents a monthly updater for the geocoder.
    1. 매달 juso.go.kr에서 "기초번호 DB" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 BSISNDATA_2505_11000.txt 등의 파일이 생성됨.
    3. 파일의 위치는 ~/projects/geocoder-api/juso-data/전체분/roadbase

    Attributes:
        name (str): 다운받은 파일명.
        geocoder (Geocoder): The geocoder instance.

    Methods:
        __init__(name: str, geocoder: Geocoder): Initializes a RoadbaseUpdater instance.
        prepare_dic_roadbase(key, value): Prepares a dictionary for the match_bld data
        update(wfile): Updates the geocoder with the address entries.

    """

    def __init__(self, yyyymm: str, name: str, geocoder: Geocoder):
        super().__init__(geocoder)
        self.yyyymm = yyyymm
        self.name = name

        # 파일 다운로드 경로 지정
        self.outpath = f"{self.JUSO_DATA_DIR}/전체분/{yyyymm}/roadbase/"

        from_crs = pyproj.CRS("EPSG:4326")
        to_crs = pyproj.CRS("EPSG:5179")

        self.proj_transform = pyproj.Transformer.from_crs(
            from_crs, to_crs, always_xy=True
        )

    async def update(self, wfile):
        # CPU 바운드 작업을 별도의 스레드로 오프로드
        return await asyncio.to_thread(self._update_sync, wfile)

    def _update_sync(self, wfile):
        self._prepare_updater_logger(f"{self.name}.log")

        log_file = f"{self.outpath}{self.name}.log"

        # BSISNDATA_2505_11000.txt
        h1_cd = self.name.split("_")[2][:2]

        self.hu = HdUpdater("202504", None)
        self.hu.cache_shp(h1_cd)

        self.zu = ZUpdater("202504", None)
        self.zu.cache_shp(h1_cd)

        # match_build_*.txt
        if not self.update_roadbase(wfile):
            return False

        self._stop_updater_logging()
        return True

    def update_roadbase(self, wfile):
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
            self.logger.info(f"Update roadbase: {self.outpath}{self.name}")

            # 전체 row수 얻기
            total_rows = sum(1 for _ in file)
            file.seek(0)  # Reset file pointer to the beginning
            self.logger.info(f"Total rows in {self.name}: {total_rows:,}")

            csv_reader = CsvReader()
            reader = csv.reader(file, delimiter="|")
            extras = {"yyyymm": self.yyyymm, "updater": "roadbase_updater"}
            batch = WriteBatch()
            bcount = 0
            added = 0

            for value in csv_reader.iter_roadbase_csv(reader):
                # # [TODO: 삭제]
                # if not value["시군구코드"].startswith(
                #     ("41650", "41810", "42110", "42710", "42715", "46830")
                # ):
                #     continue

                address_dic = self.prepare_dic(value)

                # # [TODO: 삭제]
                # if address_dic["ld_nm"] != "신북면":
                #     continue

                added = self.update_record(address_dic, extras=extras, batch=batch)
                add_count += added
                bcount += added

                cnt += 1
                if cnt % 10000 == 0:
                    progress = (cnt / total_rows) * 100
                    self.logger.info(
                        f"roadbase {self.name} {cnt:,} +{add_count:,} ({progress:.2f}%)"
                    )
                if bcount > 5000:
                    self.write_batch(batch)
                    batch.clear()
                    bcount = 0

                    # batch = rocksdb3.WriterBatch()

        # 마지막 배치 처리
        if bcount > 0:
            self.write_batch(batch)
            batch.clear()

        self.ldb.flush()

        self.logger.info(
            f"roadbase {self.name}: {cnt:,} 건, hash 추가: {add_count:,} 건"
        )

        self.logger.info(f"완료 roadbase: {self.name}")
        return True

    def prepare_dic(self, value):
        """
        Prepares a dictionary for the address entry.

        Args:
            value: The value of the address entry.

        Returns:
            dict: The prepared dictionary for the address entry.

        """
        h1_cd = value["시군구코드"][:2]  # 광역시도 코드
        wgs_x = float(value["중심점좌표_X"])
        wgs_y = float(value["중심점좌표_Y"])
        bld_x, bld_y = self.proj_transform.transform(wgs_x, wgs_y)

        d = {
            "h1_nm": value["시도명"],
            "h23_nm": value["시군구명"],
            "ld_nm": value["읍면동명"],
            "hd_nm": "",
            "ri_nm": "",
            "road_nm": value["도로명"],
            "undgrnd_yn": "",
            "bld1": value["기초번호본번"],
            "bld2": value["기초번호부번"],
            "h1_cd": h1_cd,
            "h23_cd": value["시군구코드"],
            "ld_cd": f'{value["읍면동코드"]}00',
            "hd_cd": "",
            "road_cd": value["도로명코드"],
            "zip": "",
            "bld_mgt_no": "",
            "bld_x": int(bld_x),
            "bld_y": int(bld_y),
            "san": "",
            "bng1": "",
            "bng2": "",
        }

        if d["bld_x"] and not d["zip"]:
            self.update_hd(d)
            self.update_z(d)

        return d

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

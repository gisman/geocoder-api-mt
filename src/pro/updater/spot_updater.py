import asyncio
import os
import csv
import fnmatch

from src.geocoder.geocoder import Geocoder
from .updater import BaseUpdater
from .csv_reader import CsvReader

from pyproj import Transformer, CRS


class SpotUpdater(BaseUpdater):
    """
    실행 전에 할 일:
    1. 매달 juso.go.kr에서 "사물주소" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
        파일명 예: 사물주소기준점_전체분_전북특별자치도.zip 등 17개
    2. 파일을 projects/geocoder-api/juso-data/전체분/spot 에 복사한다.
    3. 모든 zip 파일의 압축을 푼다. unzip \*.zip

    Attributes:
        geocoder (Geocoder): The geocoder instance.

    """

    def __init__(self, yyyymm: str, geocoder: Geocoder):
        super().__init__(geocoder)

        self.yyyymm = yyyymm

        # 파일 다운로드 경로 지정
        self.outpath = f"{self.JUSO_DATA_DIR}/전체분/{yyyymm}/spot/"

        self.tf = Transformer.from_crs(
            CRS.from_string("EPSG:4326"), CRS.from_string("EPSG:5179"), always_xy=True
        )

    def prepare_dic_spot(self, value):
        """
        Prepares a dictionary for the spot.

        Args:
            value: The value of the spot.

        Returns:
            dict: The prepared dictionary for the spot.

        """

        # wgs84 to utm-k
        # x, y = self.tf.transform(float(value["X좌표"]), float(value["Y좌표"]))

        d = {
            "h1_nm": value["시도명"],
            "h23_nm": value["시군구명"] or value["시도명"],  # 세종시 예외 처리
            "ld_nm": value["읍면동명"],
            "hd_nm": "",
            "ri_nm": "",
            "road_nm": value["도로명"],
            "undgrnd_yn": value["지하여부"],
            "bld1": value["주소본번"],
            "bld2": value["주소부번"],
            "san": "",
            "bng1": "",
            "bng2": "",
            "bld_reg": "",
            "bld_nm_text": "",
            "bld_nm": "",  # 동명
            "ld_cd": value["행정구역코드"],
            "hd_cd": "",
            "road_cd": value["도로명코드"],
            "zip": "",
            "bld_mgt_no": "",
            "bld_x": value["X좌표"],
            "bld_y": value["Y좌표"],
        }

        return d

    async def update(self, wfile):
        # CPU 바운드 작업을 별도의 스레드로 오프로드
        return await asyncio.to_thread(self._update_sync, wfile)

    def _update_sync(self, wfile):
        self._prepare_updater_logger("spot.log")

        # spot 폴더에 있는 *ADRES*.TXT 파일을 읽어서 처리한다.
        for file_name in os.listdir(self.outpath):
            if fnmatch.fnmatch(file_name, "*ADRES*.TXT"):
                self.update_file(file_name, wfile)

        log_file = f"{self.outpath}spot.log"
        with open(log_file, "r") as f:
            log = f.read()
            wfile.write(log)

        self._stop_updater_logging()
        return True

    def update_file(self, file_name, wfile):
        """
        Updates the geocoder with the spot.

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.

        """
        # 파일 읽기
        # 한 줄씩 객체 생성해서 update_record() 호출

        extras = {"yyyymm": self.yyyymm, "updater": "spot_updater"}

        cnt = 0
        add_count = 0
        # has_xy = 0

        with open(
            f"{self.outpath}{file_name}", "r", encoding="euc-kr", errors="ignore"
        ) as file:
            self.logger.info(f"Update: {self.outpath}{file_name}")

            csv_reader = CsvReader()
            reader = csv.reader(file, delimiter="|")
            for value in csv_reader.iter_spot_csv(reader):
                address_dic = self.prepare_dic_spot(value)
                add_count += self.update_record(address_dic, extras=extras)
                # if address_dic["bld_x"]:
                #     has_xy += 1
                cnt += 1
                if cnt % 10000 == 0:
                    self.logger.info(f"{cnt:,}")
                    print(f"{cnt:,}")

        self.logger.info(
            f"사물정보 {file_name}: {cnt:,} 건, hash 추가: {add_count:,} 건"
        )
        print(f"사물정보 {file_name}: {cnt:,} 건, hash 추가: {add_count:,} 건")

        self.logger.info(f"완료: {file_name}")

        return True

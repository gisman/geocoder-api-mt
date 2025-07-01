import asyncio
import csv

from src.geocoder.geocoder import Geocoder
from .updater import BaseUpdater
from .csv_reader import CsvReader


class EntrcUpdater(BaseUpdater):
    """
    A class that represents a monthly updater for the geocoder.
    1. 매달 juso.go.kr에서 "위치정보요약DB" 전체분 파일을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 entrc_busan.txt 등의 파일이 생성됨.
    3. 파일의 위치는 ~/projects/geocoder-api/juso-data/전체분/entrc

    Attributes:
        name (str): 다운받은 파일명.
        geocoder (Geocoder): The geocoder instance.

    Methods:
        __init__(name: str, geocoder: Geocoder): Initializes a EntrcUpdater instance.
        prepare_dic_entr(key, value): Prepares a dictionary for the address entry.
        update(wfile): Updates the geocoder with the address entries.

    """

    def __init__(self, yyyymm: str, name: str, geocoder: Geocoder):
        super().__init__(geocoder)
        self.name = name
        self.yyyymm = yyyymm

        # 파일 다운로드 경로 지정
        self.outpath = f"{self.JUSO_DATA_DIR}/전체분/{yyyymm}/entrc/"

    def prepare_dic_entr(self, value):
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
            "hd_nm": value["관할행정동"],
            "ri_nm": "",
            "road_nm": value["도로명"],
            "undgrnd_yn": value["지하여부"],
            "bld1": value["건물본번"],
            "bld2": value["건물부번"],
            "san": "",
            "bng1": "",
            "bng2": "",
            "bld_reg": "",
            "bld_nm_text": "",
            "bld_nm": value["건물명"],  # 동명
            "ld_cd": value["법정동코드"],
            "hd_cd": "",
            "road_cd": value["도로명코드"],
            "zip": value["우편번호"],
            "bld_mgt_no": "",
            "bld_x": value["X좌표"],
            "bld_y": value["Y좌표"],
        }

        return d

    async def update(self, wfile):
        # CPU 바운드 작업을 별도의 스레드로 오프로드
        return await asyncio.to_thread(self._update_sync, wfile)

    def _update_sync(self, wfile):
        """
        Updates the geocoder with the address entries.

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

        with open(
            f"{self.outpath}{self.name}", "r", encoding="euc-kr", errors="ignore"
        ) as file:
            self.logger.info(f"Update: {self.outpath}{self.name}")

            csv_reader = CsvReader()
            reader = csv.reader(file, delimiter="|")
            extras = {"yyyymm": self.yyyymm, "updater": "entrc_updater"}
            for value in csv_reader.iter_entr_csv(reader):
                address_dic = self.prepare_dic_entr(value)

                # 서부대성로 257 (후평동)
                # if not (
                #     address_dic["road_nm"] == "서부대성로"
                #     and address_dic["bld1"] == "257"
                # ):
                #     continue

                add_count += self.update_record(address_dic, extras=extras)
                if address_dic["bld_x"]:
                    has_xy += 1
                cnt += 1
                if cnt % 10000 == 0:
                    self.logger.info(f"{self.name} {cnt:,}")
                    # print(f"{self.name} {cnt:,}")

        self.logger.info(
            f"위치정보요약DB {self.name}: {cnt:,} 건, 좌표있는 건물: {has_xy:,} 건. hash 추가: {add_count:,} 건"
        )

        self.logger.info(f"완료: {self.name}")

        log_file = f"{self.outpath}{self.name}.log"
        with open(log_file, "r") as f:
            log = f.read()
            wfile.write(log)

        self._stop_updater_logging()
        return True

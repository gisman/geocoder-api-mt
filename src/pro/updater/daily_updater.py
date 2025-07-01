import asyncio
import json
import re
import urllib.request
import os

# import rocksdb3
import logging
from pyproj import Transformer, CRS

from src.geocoder.geocoder import Geocoder
from src.geocoder.reverse_geocoder import ReverseGeocoder
from .updater import BaseUpdater
from src.geocoder.util.HSimplifier import HSimplifier
from src.geocoder.util.BldSimplifier import BldSimplifier
from .csv_reader import CsvReader
from .codes import RESPONSE_CODES


class DailyUpdater(BaseUpdater):
    """
    지오코딩 데이터를 매일 다운로드하고 업데이트하는 클래스.
    매일 정오에 cron job으로 실행하는 것을 권장.

    crontab 예시: 0 12 * * *  curl 'http://localhost:4001/update?date='$(date +\%Y\%m\%d)

    Args:
        date (str): 업데이트할 날자.
        geocoder (Geocoder): An instance of the Geocoder class.
        apikey (str): The API key for accessing the geocoding service. (juso.go.kr 에서 발급 받음)

    Attributes:
        date (str): The date of the update.
        API_KEY (str): The API key for accessing the geocoding service.
        outpath (str): 다운로드된 파일이 저장될 디렉토리의 경로.

    Methods:
        download(): Downloads the geocoding data files for the specified date.
        _download(cntc_cd): Downloads a specific geocoding data file.
        unzip(outpath, file_name): Unzips a downloaded file.
        update(wfile): Updates the geocoding data using the downloaded files.
    """

    def __init__(
        self, date, geocoder: Geocoder, reverse_geocoder: ReverseGeocoder, apikey: str
    ):
        super().__init__(geocoder)
        self.date = date
        self.API_KEY = apikey
        # 파일 다운로드 경로 지정
        self.outpath = f"{self.JUSO_DATA_DIR}/일변동분/{date}/"

        # 파일 다운로드 폴더 생성
        if not os.path.isdir(self.outpath):
            os.makedirs(self.outpath)
        self._prepare_updater_logger()

        self.reverse_geocoder = reverse_geocoder
        target_crs = "EPSG:4326"
        self.tf = self.get_csr_transformer(target_crs)

    async def download(self) -> bool:

        # 파일 다운로드 폴더 생성
        if not os.path.isdir(self.outpath):
            os.makedirs(self.outpath)
            # self.logger.debug(f"makedirs: {self.outpath}")

        # self._prepare_updater_logger()
        self.logger.info(f"date: {self.date}")

        # 참조: https://business.juso.go.kr/addrlink/adresDbCntc/rnAdresCntc.do

        #        순번 구분코드 설 명 제공주기 비 고
        # (O)     1 100001 도로명주소한글 매일 속성정보
        #           - 건물정보 TH_SGCO_RNADR_MST
        #           - 관련지번 TH_SGCO_RNADR_LNBR
        #         2 100002 도로명주소영문 매일 속성정보
        #         3 100003 상세주소표시 매일 속성정보
        #         4 100004 상세주소 동표시 매일 속성정보
        #         5 100005 도로명 매일 속성정보
        #         6 100006 사물주소(좌표제외) 매월 속성정보
        # (O)     7 200001 도로명주소 출입구정보 매일 속성정보
        #           - JUSUEC 도로명주소 출입구정보 TH_SGCO_RNADR_POSITION
        #         8 200002 기초번호 매일 속성정보
        #         9 200003 사물주소 시설의 기준점 매월 속성정보
        #         10 300001 도로명주소 건물도형 매일 전자지도
        #         11 300002 건물군 내 상세주소 동 도형 매일 전자지도
        #         12 300003 도로명이 부여된 도로 도형 매일 전자지도
        #         13 300004 사물주소 시설의 도형 매월 전자지도
        #         14 300005 기타자료 매월 전자지도
        #         15 300006 구역의도형 매월 전자지도

        cntc_cd_list = [
            "100001",
            "200001",
            # "300001",
        ]

        for cntc_cd in cntc_cd_list:
            if not self._download(cntc_cd):
                logging.error(f"download failed: {cntc_cd}")
                self._stop_updater_logging()
                return False

        # 파일명에 공백이 있으면 제거
        # 'AlterD.JUSUEC.20230315.TH_SGCO_RNADR_POSITION .TXT'
        try:
            filename_has_space = (
                f"{self.outpath}AlterD.JUSUEC.{self.date}.TH_SGCO_RNADR_POSITION .TXT"
            )
            os.rename(filename_has_space, filename_has_space.replace(" ", ""))
        except FileNotFoundError:
            pass

        return True

    def _download(self, cntc_cd):
        url = f"https://update.juso.go.kr/updateInfo.do?app_key={self.API_KEY}&date_gb=D&retry_in=Y&cntc_cd={cntc_cd}&req_dt={self.date}"  # &req_dt2={self.date}"
        # https://update.juso.go.kr/updateInfo.do?app_key=U01TX0FVVEgyMDI0MDMxOTA1MDcxMDExNDYwODI=&date_gb=D&retry_in=Y&cntc_cd=100001&req_dt=20240301&req_dt2=20240301
        u = urllib.request.urlopen(url)

        response_code = u.headers.get("Err_code")
        # print(RESPONSE_CODES[response_code])
        self.logger.info(f"download: {RESPONSE_CODES[response_code]} - {url}")

        while True:

            # 파일 순번 존재확인
            file_seq = u.read(2)

            # 파일 순번 미존재시 종료(break)
            if not file_seq:
                break

            # 수신정보 저장 // strip() = 공백삭제, decode() = 바이트를 스트링으로 변환
            file_base_dt = u.read(8)
            file_name = u.read(50).strip().decode()
            if not file_name:
                self.logger.error(f"다운로드 할 파일 없음")
                continue
            try:
                file_size = int(u.read(10).strip())
                res_code = u.read(5)
                req_code = u.read(6)
                replay = u.read(1)
                create_dt = u.read(8).decode()
            except ValueError:
                self.logger.error("Invalid file size received, skipping file.")
                continue

            # print(f"INFO: Download {file_name}, {file_size/1024}KB")
            self.logger.info(f"Download {file_name}, {file_size/1024}KB")

            # zip파일 데이터 읽기 & 쓰기
            zip_file = u.read(file_size + 10)
            f = open(self.outpath + file_name, "wb")
            f.write(zip_file)
            f.close()
            self.logger.info(f"Download Success - {file_name}")

            # unzip
            target_file_name = self.unzip(self.outpath, file_name)
            self.logger.info(f"unzip DONE")

        return True

    def unzip(self, outpath, file_name):
        # 파일 이름에서 확장자 분리
        file_name_base, file_extension = os.path.splitext(file_name)

        # 확장자를 소문자로 변환
        # 파일 이름에 확장자를 다시 연결
        target_file_name = file_name_base + file_extension.lower()

        os.system(f"zip -F {outpath + file_name} --out {outpath + target_file_name}")
        self.logger.info(
            f"zip -F {outpath + file_name} --out {outpath + target_file_name}"
        )

        os.system(f"unzip -o {outpath + target_file_name} -d {outpath}")
        self.logger.info(f"unzip -o {outpath + target_file_name} -d {outpath}")

    async def update(self, wfile):
        # CPU 바운드 작업을 별도의 스레드로 오프로드
        return await asyncio.to_thread(self._update_sync, wfile)

    def _update_sync(self, wfile):
        # 31:신규
        # 34:수정
        # 63:폐지

        # AlterD.JUSUEC.20240312.TH_SGCO_RNADR_POSITION.TXT
        # AlterD.JUSUKR.20240312.TH_SGCO_RNADR_LNBR.TXT
        # AlterD.JUSUKR.20240312.TH_SGCO_RNADR_MST.TXT

        csv_reader = CsvReader()
        self.logger.info(f"read_address_csv TH_SGCO_RNADR_MST.TXT")
        address_map = {}
        try:
            address_map = csv_reader.read_address_csv(
                f"{self.outpath}AlterD.JUSUKR.{self.date}.TH_SGCO_RNADR_MST.TXT"
            )
        except FileNotFoundError:
            self.logger.error(
                f"파일이 존재하지 않습니다: {self.outpath}AlterD.JUSUKR.{self.date}.TH_SGCO_RNADR_MST.TXT"
            )

        self.logger.info(f"read_address_csv TH_SGCO_RNADR_LNBR.TXT")
        related_map = {}
        try:
            related_map = csv_reader.read_related_csv(
                f"{self.outpath}AlterD.JUSUKR.{self.date}.TH_SGCO_RNADR_LNBR.TXT"
            )
        except FileNotFoundError:
            self.logger.error(
                f"파일이 존재하지 않습니다: {self.outpath}AlterD.JUSUKR.{self.date}.TH_SGCO_RNADR_LNBR.TXT"
            )

        self.logger.info(f"read_address_csv TH_SGCO_RNADR_POSITION.TXT")
        position_map = {}
        try:
            position_map = csv_reader.read_position_csv(
                f"{self.outpath}AlterD.JUSUEC.{self.date}.TH_SGCO_RNADR_POSITION.TXT"
            )
        except FileNotFoundError:
            self.logger.error(
                f"파일이 존재하지 않습니다: {self.outpath}AlterD.JUSUEC.{self.date}.TH_SGCO_RNADR_POSITION.TXT"
            )

        # 건물정보 TH_SGCO_RNADR_MST + JUSUEC 도로명주소 출입구정보 TH_SGCO_RNADR_POSITION
        self.logger.info(f"건물정보 TH_SGCO_RNADR_MST: {len(address_map):,} 건")
        cnt = 0
        add_count = 0
        has_xy = 0
        address_position_dic = {}
        extras = {
            "yyyymmdd": self.date,
            "updater": "daily_updater",
        }
        for key, value in address_map.items():
            address_dic = self.prepare_dic_addr(key, value, position_map)
            address_position_dic[key] = address_dic
            # 좌표 있어야 함
            if not address_dic["bld_x"]:
                continue
            add_count += self.update_record(address_dic, extras=extras)
            if address_dic["bld_x"]:
                has_xy += 1
            cnt += 1
            if cnt % 1000 == 0:
                print(f"{cnt}")

        self.logger.info(
            f"건물정보 TH_SGCO_RNADR_MST: {cnt:,} 건, 좌표있는 건물: {has_xy:,} 건. hash 추가: {add_count:,} 건"
        )

        # 관련지번 TH_SGCO_RNADR_LNBR 을 위의 merge 결과와 다시 merge
        self.logger.info(f"관련지번 TH_SGCO_RNADR_LNBR: {len(related_map):,} 건")
        cnt = 0
        add_count = 0
        has_xy = 0
        for key, value in related_map.items():
            related_dic = self.prepare_dic_rel(
                value["도로명관리번호"], value, address_position_dic
            )
            # 좌표 있어야 함
            if not related_dic["bld_x"]:
                continue
            add_count += self.update_record(related_dic, extras=extras)
            if related_dic["bld_x"]:
                has_xy += 1
            cnt += 1
            if cnt % 1000 == 0:
                print(f"{cnt:,}")

        self.logger.info(
            f"관련지번 TH_SGCO_RNADR_LNBR: {cnt:,} 건, 좌표있는 건물: {has_xy:,} 건. hash 추가: {add_count:,} 건"
        )

        self.logger.info(f"완료: {self.date}")

        log_file = f"{self.outpath}update.log"
        self._stop_updater_logging()

        with open(log_file, "r") as f:
            log = f.read()
            wfile.write(log)

        return True

    def prepare_dic_rel(self, key, value, addr_pos_map):
        position = addr_pos_map.get(key, {})

        d = {
            "h1_nm": value["시도명"],
            "h23_nm": value["시군구명"],
            "ld_nm": value["읍면동명"],
            "hd_nm": position.get("hd_nm", ""),
            "ri_nm": value["리명"],
            "road_nm": position.get("road_nm", ""),
            "undgrnd_yn": position.get("undgrnd_yn", ""),
            "bld1": position.get("bld1", ""),
            "bld2": position.get("bld2", ""),
            "san": value["산여부"],
            "bng1": value["번지"],
            "bng2": value["호"],
            "bld_reg": position.get("bld_reg", ""),
            "bld_nm_text": position.get("bld_nm_text", ""),
            "bld_nm": position.get("bld_nm", ""),  # 동명
            "ld_cd": value["법정동코드"],
            "hd_cd": position.get("hd_cd", ""),
            "road_cd": value["도로명코드"],
            "zip": position.get("zip", ""),
            "bld_mgt_no": value["도로명관리번호"],
            "bld_x": position.get("bld_x", None),
            "bld_y": position.get("bld_y", None),
        }

        if d["bld_x"] and not d["hd_cd"]:
            x1, y1 = self.transform(d["bld_x"], d["bld_y"])
            hd_result = self.reverse_geocoder.search_hd_history(
                x1, y1, yyyymm=self.date[:6]
            )
            if hd_result:
                d["hd_nm"] = hd_result[0]["EMD_KOR_NM"]
                d["hd_cd"] = hd_result[0]["EMD_CD"]

        return d

    def prepare_dic_addr(self, key, value, position_map):
        position = position_map.get(key, {})

        d = {
            "h1_nm": value["시도명"],
            "h23_nm": value["시군구명"],
            "ld_nm": value["읍면동명"],
            "hd_nm": value["행정동명"],
            "ri_nm": value["리명"],
            "road_nm": value["도로명"],
            "undgrnd_yn": value["지하여부"],
            "bld1": value["건물본번"],
            "bld2": value["건물부번"],
            "san": value["산여부"],
            "bng1": value["번지"],
            "bng2": value["호"],
            "bld_reg": value["건축물대장건물명"] or "",
            "bld_nm_text": value["시군구용건물명"],
            "bld_nm": "",  # 동명
            "ld_cd": value["법정동코드"],
            "hd_cd": value["행정동코드"],
            "road_cd": value["도로명코드"],
            "zip": value["기초구역번호(우편번호)"],
            "bld_mgt_no": value["도로명관리번호"],
            "bld_x": position.get("출입구좌표X"),
            "bld_y": position.get("출입구좌표Y"),
        }

        if d["bld_x"] and not d["hd_cd"]:
            x1, y1 = self.transform(d["bld_x"], d["bld_y"])
            hd_result = self.reverse_geocoder.search_hd_history(
                x1, y1, yyyymm=self.date[:6]
            )
            if hd_result:
                d["hd_nm"] = hd_result[0]["EMD_KOR_NM"]
                d["hd_cd"] = hd_result[0]["EMD_CD"]

        return d

    def transform(self, x, y):
        """
        좌표를 UTM-K (GRS80)에서 대상 CRS로 변환합니다.
        타겟이 정수형 좌표계인 경우, 정수로 변환합니다.

        Args:
            x (float): x 좌표.
            y (float): y 좌표.

        Returns:
            tuple: 변환된 좌표 (x, y).
        """
        x1, y1 = self.tf.transform(x, y)
        if self.tf_int:
            x1 = int(x1)
            y1 = int(y1)

        return x1, y1

    def get_csr_transformer(self, target_crs="EPSG:4326"):
        """
        UTM-K (GRS80)에서 대상 CRS로 좌표를 변환하기 위한 CRS 변환기를 생성하고 반환합니다.

        Args:
            target_crs (str, optional): 대상 CRS. 기본값은 "EPSG:4326".
            비표준인 "KATECH" 좌표계를 추가로 지원합니다.

        Returns:
            pyproj.Transformer: CRS 변환기.
        """
        self.tf_int = False

        # 네비게이션용 KATECH 좌표계(KOTI-KATECH)EPSG 없음. 비공식 좌표계임.
        # GIMI9 geocoder 에서 KATECH 별칭으로 식별
        if target_crs == "KATECH":
            KATECH = {
                "proj": "tmerc",
                "lat_0": "38",
                "lon_0": "128",
                "ellps": "bessel",
                "x_0": "400000",
                "y_0": "600000",
                "k": "0.9999",
                "units": "m",
                "no_defs": True,
                "towgs84": "-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43",
            }

            CRS_TM128 = CRS(**KATECH)

            tf = Transformer.from_crs(
                CRS.from_string("EPSG:5179"), CRS_TM128, always_xy=True
            )

            self.tf_int = True
            return tf
        else:
            return Transformer.from_crs(
                CRS.from_string("EPSG:5179"),
                CRS.from_string(target_crs),
                always_xy=True,
            )

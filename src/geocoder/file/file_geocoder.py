"""
파일 지오코딩
"""

# import pandas as pd
import asyncio
import os
import time
from pyproj import Transformer, CRS
import json
import logging

from .reader import Reader
from .writer import Writer
from .enc import Enc
from .address_finder import AddressFinder

import src.config as config
from src.geocoder.geocoder import Geocoder, POS_CD_SUCCESS
from src.geocoder.reverse_geocoder import ReverseGeocoder

X_AXIS = "x_axis"
Y_AXIS = "y_axis"


class FileGeocoder:
    def __init__(
        self, geocoder: Geocoder = None, reverse_geocoder: ReverseGeocoder = None
    ):
        """
        FileGeocoder 객체를 초기화합니다.

        Args:
            geocoder (Geocoder, optional): 지오코딩에 사용할 Geocoder 객체입니다. 기본값은 None입니다.
            그러나 Geocoder 객체를 지정하지 않으면 FileGeocoder 객체를 사용할 수 없습니다.
        """
        self.geocoder = geocoder
        self.reverse_geocoder = reverse_geocoder

        log_file = "log/geocode-api.log"
        log_handler = logging.FileHandler(log_file)

        log_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)-15s - %(levelname)s - %(message)s")
        log_handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.addHandler(log_handler)

        self.log_handler = log_handler
        self.logger = logger

    async def prepare(self, filepath, uploaded_filename):
        """
        주소 컬럼, 인코딩, 구분자 자동으로 찾기
        """
        self.filepath = filepath
        enc = Enc(filepath)
        charenc = enc.detect_enc()
        # encoding detection 실패시 cp949로 강제 설정
        if not charenc:
            charenc = "cp949"
        self.charenc = charenc

        self.delimiter = enc.detect_delimiter(self.charenc)
        self.address_col = -1
        af = AddressFinder(filepath, charenc, self.delimiter)
        try:
            summary = af.find(self.geocoder)
            self.uploaded_filename = uploaded_filename
            if "col" in summary:
                self.address_col = summary["col"]
        except:
            self.logger.error("Failed to find address column")
            raise Exception("error: 주소 컬럼 찾기 오류: API-P001")

    def get_hd_history_headers(self, from_yyyymm: str, to_yyyymm: str):
        def next(yyyymm):
            """
            주어진 yyyymm 문자열에서 다음 월을 반환합니다.
            """
            year = int(yyyymm[:4])
            month = int(yyyymm[4:6])
            if month == 12:
                return f"{year + 1}01"
            else:
                return f"{year}{month + 1:02d}"

        result = []
        if from_yyyymm and to_yyyymm:
            yyyymm = from_yyyymm
            while yyyymm <= to_yyyymm:
                result.append(f"hd_cd_{yyyymm}")
                result.append(f"hd_nm_{yyyymm}")
                yyyymm = next(yyyymm)
        return result

    async def run(
        self, download_dir, limit=10000, target_crs="EPSG:4326", sample_count=0
    ):
        """
        파일을 읽어 지오코딩합니다. 결과를 파일로 저장합니다.

        Args:
            download_dir (str): 지오코딩된 파일과 요약을 저장할 디렉토리. (prepare()에 전달된 filepath의 파일명을 사용하여 결과 파일 생성)
            limit (int, optional): 지오코딩할 레코드의 최대 개수. 기본값은 10000.
            target_crs (str, optional): 지오코딩된 좌표의 대상 좌표 참조 시스템(CRS). 기본값은 "EPSG:4326". (WGS84)

        Returns:
            dict: 지오코딩 결과 요약 + 주소 컬럼, 인코딩, 구분자
        """
        summary = {}
        count = 0
        success_count = 0
        hd_success_count = 0
        fail_count = 0
        start_time = time.time()

        try:
            self.tf = self.get_csr_transformer(target_crs)
            self.tf_wgs84 = self.get_csr_transformer("EPSG:4326")
        except:
            self.logger.error("Failed to create CRS transformer")
            return {"error": "좌표계 설정 오류: API-R001"}

        filename = os.path.basename(self.filepath)

        # reader, writer 생성
        reader = None
        writer = None
        try:
            reader = Reader(
                self.filepath, self.charenc, self.delimiter, self.address_col
            )
        except Exception as e:
            self.logger.error("Failed to create reader", e)
            return {
                "error": "파일 읽기 오류: API-R0010",
                "filepath": self.filepath,
                "charenc": self.charenc,
                "delimiter": self.delimiter,
                "address_col": self.address_col,
            }

        headers = reader.get_headers()
        full_history_list = config.FULL_HISTORY_LIST
        hd_history_cols = []
        if full_history_list:
            hd_history_cols = self.get_hd_history_headers(
                config.HD_HISTORY_START_YYYYMM, config.HD_HISTORY_END_YYYYMM
            )
            headers.extend(hd_history_cols)
        try:
            writer = Writer(
                f"{download_dir}{filename}.csv",
                headers,
                hd_history_cols=hd_history_cols,
            )
            writer.writeheader()
        except Exception as e:
            self.logger.error("Failed to create writer", e)
            return {"error": "파일 쓰기 오류: API-R002"}

        sample = []
        try:
            for line, addr in reader:
                # limit 체크. 1만건 또는 남은 쿼터 중 작은 것. 용역은 무제한
                if limit > 0 and count >= limit:
                    break
                count += 1

                # 지오코딩
                row_result = self.geocode(addr, full_history_list=full_history_list)

                if row_result.get("pos_cd", "") in POS_CD_SUCCESS:
                    success_count += 1
                else:
                    fail_count += 1

                # # 결과 기록
                # success = row_result["success"]

                # if success == "실패":
                #     fail_count += 1
                # else:
                #     success_count += 1

                if row_result.get("hd_cd") or row_result.get("h4_cd"):
                    hd_success_count += 1

                sample_wgs_x = row_result.pop("sample_wgs_x", 0)
                sample_wgs_y = row_result.pop("sample_wgs_y", 0)
                writer.write(line, row_result)
                if count <= sample_count:
                    # response용 데이터는 hd_history 제외, 출력 좌표계를 wgs84로 유지
                    row_result.pop("hd_history", None)
                    row_result[X_AXIS] = sample_wgs_x
                    row_result[Y_AXIS] = sample_wgs_y
                    sample.append(row_result)

                if count % 10000 == 0:
                    self.logger.info(
                        f"{count:,}, {time.time() - start_time:.1f}sec, success:{success_count}({success_count/count*100:.2f}%), fail:{fail_count}"
                    )
        except Exception as e:
            self.logger.error("Failed to geocode: %s", e)
            return {"error": "지오코딩 오류: API-R003"}

        # write summary
        summary["total_time"] = time.time() - start_time
        summary["total_count"] = count
        summary["success_count"] = success_count
        summary["hd_success_count"] = hd_success_count
        fail_count = count - success_count
        summary["fail_count"] = fail_count
        summary["filename"] = filename

        summary["charenc"] = self.charenc
        summary["delimiter"] = self.delimiter
        summary["address_col"] = headers[self.address_col]
        summary["target_crs"] = target_crs
        summary["uploaded_filename"] = self.uploaded_filename
        summary["results"] = sample

        # summary 파일 저장
        try:
            with open(
                f"{download_dir}{filename}.summary", "w", newline=""
            ) as summary_file:
                json.dump(summary, summary_file)

        except:
            self.logger.error("Failed to write summary")
            return {"error": "요약 파일 쓰기 오류: API-R004"}

        return summary

    async def run_mt(
        self, download_dir, limit=10000, target_crs="EPSG:4326", sample_count=0
    ):
        """
        파일을 읽어 지오코딩합니다. 결과를 파일로 저장합니다.
        멀티 스레드로 실행됩니다.

        Args:
            download_dir (str): 지오코딩된 파일과 요약을 저장할 디렉토리. (prepare()에 전달된 filepath의 파일명을 사용하여 결과 파일 생성)
            limit (int, optional): 지오코딩할 레코드의 최대 개수. 기본값은 10000.
            target_crs (str, optional): 지오코딩된 좌표의 대상 좌표 참조 시스템(CRS). 기본값은 "EPSG:4326". (WGS84)

        Returns:
            dict: 지오코딩 결과 요약 + 주소 컬럼, 인코딩, 구분자
        """
        summary = {}
        count = 0
        success_count = 0
        hd_success_count = 0
        fail_count = 0
        start_time = time.time()

        try:
            self.tf = self.get_csr_transformer(target_crs)
            self.tf_wgs84 = self.get_csr_transformer("EPSG:4326")
        except:
            self.logger.error("Failed to create CRS transformer")
            return {"error": "좌표계 설정 오류: API-R001"}

        filename = os.path.basename(self.filepath)

        # reader, writer 생성
        reader = None
        writer = None
        TASK_ROW_COUNT_LIMIT = 10000

        try:
            reader = Reader(
                self.filepath,
                self.charenc,
                self.delimiter,
                self.address_col,
                start_row=0,
                row_count=TASK_ROW_COUNT_LIMIT,
            )
        except Exception as e:
            self.logger.error("Failed to create reader", e)
            return {
                "error": "파일 읽기 오류: API-R0010",
                "filepath": self.filepath,
                "charenc": self.charenc,
                "delimiter": self.delimiter,
                "address_col": self.address_col,
            }

        headers = reader.get_headers()
        full_history_list = config.FULL_HISTORY_LIST
        hd_history_cols = []
        if full_history_list:
            hd_history_cols = self.get_hd_history_headers(
                config.HD_HISTORY_START_YYYYMM, config.HD_HISTORY_END_YYYYMM
            )
            headers.extend(hd_history_cols)
        try:
            writer = Writer(
                f"{download_dir}{filename}.csv",
                headers,
                hd_history_cols=hd_history_cols,
            )
            writer.writeheader()
        except Exception as e:
            self.logger.error("Failed to create writer", e)
            return {"error": "파일 쓰기 오류: API-R002"}

        sample = []
        # 전체 건수를 모르는 상태.
        # 1만건씩 실행

        geocode_tasks = []
        # 전체 건수 = reader.get_row_count()``
        start_row = 0
        row_result_mt = []
        while True:
            geocode_tasks.append(
                asyncio.to_thread(self.geocode_mt, reader, full_history_list)
            )

            if reader.count() < TASK_ROW_COUNT_LIMIT:
                # 마지막 batch
                break

            start_row += TASK_ROW_COUNT_LIMIT
            reader = Reader(
                self.filepath,
                self.charenc,
                self.delimiter,
                self.address_col,
                start_row=start_row,
                row_count=TASK_ROW_COUNT_LIMIT,
            )

        row_result_mt_list = await asyncio.gather(*geocode_tasks)

        for result_batch in row_result_mt_list:
            row_result_mt.extend(result_batch)

        # async with asyncio.TaskGroup() as tg:
        #     while True:
        #         tg.create_task(
        #             asyncio.to_thread(
        #                 self.geocode_mt, reader, full_history_list, row_result_mt
        #             )
        #         )

        #         # geocode_tasks.append(geocode_task)

        #         if reader.count() < TASK_ROW_COUNT_LIMIT:
        #             # 마지막 batch
        #             break

        #         start_row += TASK_ROW_COUNT_LIMIT
        #         reader = Reader(
        #             self.filepath,
        #             self.charenc,
        #             self.delimiter,
        #             self.address_col,
        #             start_row=start_row,
        #             row_count=TASK_ROW_COUNT_LIMIT,
        #         )

        for row in row_result_mt:
            # for row in row_results:
            writer.write(row["input_line"], row)

            if row.get("pos_cd", "") in POS_CD_SUCCESS:
                success_count += 1
            else:
                fail_count += 1

            if row.get("hd_cd") or row.get("h4_cd"):
                hd_success_count += 1

            count += 1

        # sample에 추가
        for row in row_result_mt[:sample_count]:
            # response용 데이터는 hd_history 제외, 출력 좌표계를 wgs84로 유지
            row.pop("hd_history", None)
            sample_wgs_x = row.pop("sample_wgs_x", 0)
            sample_wgs_y = row.pop("sample_wgs_y", 0)
            row[X_AXIS] = sample_wgs_x
            row[Y_AXIS] = sample_wgs_y
            sample.append(row)

        # write summary
        summary["total_time"] = time.time() - start_time
        summary["total_count"] = count
        summary["success_count"] = success_count
        summary["hd_success_count"] = hd_success_count
        fail_count = count - success_count
        summary["fail_count"] = fail_count
        summary["filename"] = filename

        summary["charenc"] = self.charenc
        summary["delimiter"] = self.delimiter
        summary["address_col"] = headers[self.address_col]
        summary["target_crs"] = target_crs
        summary["uploaded_filename"] = self.uploaded_filename
        summary["results"] = sample

        # summary 파일 저장
        try:
            with open(
                f"{download_dir}{filename}.summary", "w", newline=""
            ) as summary_file:
                json.dump(summary, summary_file)

        except:
            self.logger.error("Failed to write summary")
            return {"error": "요약 파일 쓰기 오류: API-R004"}

        return summary

    def __str__(self):
        """
        Returns a string representation of the FileGeocoder object.
        """
        return "FileGeocoder"

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
        try:
            x1, y1 = self.tf.transform(x, y)
            if self.tf_int:
                x1 = int(x1)
                y1 = int(y1)

            return x1, y1
        except Exception as e:
            self.logger.error("좌표 변환 오류: %s", e, x, y)
            return None, None

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

    def geocode_mt(self, reader: Reader, full_history_list=False):
        """
        멀티 스레드로 지오코딩을 수행합니다.

        Args:
            reader (Reader): Reader 객체로, 파일에서 주소를 읽어옵니다.
            full_history_list (bool): 행정동 history를 전체 조회할지 여부. 기본값은 False.

        Returns:
            dict: 지오코딩 결과 요약.
        """
        result = []
        print("geocode_mt start", reader.count())
        try:
            for line, addr in reader:
                # count += 1

                # 지오코딩
                row_result = self.geocode(addr, full_history_list=full_history_list)
                row_result["input_line"] = line
                result.append(row_result)
        except Exception as e:
            self.logger.error("Failed to geocode: %s", e)
            return {"error": "지오코딩 오류: API-R003"}

        print("geocode_mt end", reader.count())
        return result

    def geocode(self, addr, **kwargs):
        """
        geocoder 객체를 사용하여 주어진 주소를 지오코딩합니다.

        Args:
            addr (str): 지오코딩할 주소.

        Returns:
            dict: 지오코딩 결과.
            실패하면 기본 값이 반환됩니다.
            dict["success"]는 반드시 "실패", "성공" 중 하나입니다.
        """
        val = self.geocoder.search(addr)

        if val and val["success"] and val["x"]:
            x = val.get("x", 0)
            y = val.get("y", 0)
            x1, y1 = self.transform(x, y)
            wgs_x, wgs_y = self.tf_wgs84.transform(x, y)

            # 행정동 history 검색
            if kwargs.get("full_history_list", False):
                hd_history = self.reverse_geocoder.search_hd_history(
                    wgs_x, wgs_y, full_history_list=True
                )
                val["hd_history"] = hd_history

            if val.get("pos_cd") == "" or val.get("pos_cd") in POS_CD_SUCCESS:
                val["success"] = "성공"
            else:
                val["success"] = "실패"

            val["sample_wgs_x"] = wgs_x
            val["sample_wgs_y"] = wgs_y
            val[X_AXIS] = x1
            val[Y_AXIS] = y1
        else:
            val = {
                "success": "실패",
                X_AXIS: None,
                Y_AXIS: None,
                "h1_cd": "",
                "h2_cd": "",
                "kostat_h1_cd": "",
                "kostat_h2_cd": "",
                "hd_cd": "",
                "hd_nm": "",
                "errmsg": val.get("errmsg", "") if val else "",
            }

        val["inputaddr"] = addr
        return val

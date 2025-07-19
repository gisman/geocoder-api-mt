"""
파일 지오코딩
"""

# import pandas as pd
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import time
from pyproj import Transformer, CRS
import json
import logging

from src.geocoder import errs
from src.geocoder.file.reader_xy import ReaderXY

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
        self.executor = None

        formatter = logging.Formatter("%(asctime)-15s - %(levelname)s - %(message)s")

        log_file = "log/geocode-api.log"
        log_handler = logging.FileHandler(log_file)
        log_handler.setLevel(logging.DEBUG)
        log_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.addHandler(log_handler)
        logger.addHandler(console_handler)

        self.log_handler = log_handler
        self.logger = logger

    def __del__(self):
        """
        FileGeocoder 객체가 소멸될 때 스레드 풀을 정리합니다.
        """
        if hasattr(self, "executor") and self.executor:
            try:
                self.executor.shutdown(wait=False)
            except Exception:
                pass  # 소멸자에서는 예외를 무시

    async def prepare_xy(
        self, filepath, uploaded_filename, x_col, y_col, delimiter, encoding, source_crs
    ):
        self.filepath = filepath
        self.charenc = encoding
        self.delimiter = delimiter
        self.address_col = -1
        self.uploaded_filename = uploaded_filename
        self.x_col = x_col
        self.y_col = y_col

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

    async def run_xy(
        self,
        download_dir,
        limit=10000,
        source_crs="EPSG:4326",
        target_crs="EPSG:4326",
        sample_count=0,
    ):
        try:
            reader = ReaderXY(
                self.filepath,
                self.charenc,
                self.delimiter,
                self.x_col,
                self.y_col,
                start_row=0,
                row_count=limit,
            )
        except Exception as e:
            self.logger.error("Failed to create reader", e)
            return {
                "error": "파일 읽기 오류: API-R0010",
                "filepath": self.filepath,
                "charenc": self.charenc,
                "delimiter": self.delimiter,
                "x": self.x_col,
                "y": self.y_col,
            }

        return await self._run(
            download_dir,
            limit,
            source_crs,
            target_crs,
            sample_count,
            reader,
            has_xy_cols=True,
        )

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

        # return await self._run_running_loop(
        return await self._run(
            download_dir,
            limit,
            "EPSG:5179",
            target_crs,
            sample_count,
            reader,
        )

    async def _run(
        self,
        download_dir,
        limit=10000,
        source_crs="EPSG:5179",
        target_crs="EPSG:4326",
        sample_count=0,
        reader: Reader = None,
        has_xy_cols=False,
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
            self.tf = self.get_csr_transformer(target_crs, source_crs)
            self.tf_wgs84 = self.get_csr_transformer("EPSG:4326", source_crs)
        except:
            self.logger.error("Failed to create CRS transformer")
            return {"error": "좌표계 설정 오류: API-R001"}

        filename = os.path.basename(self.filepath)

        # reader, writer 생성
        # reader = None
        writer = None

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
        full_history_list = config.FULL_HISTORY_LIST
        # loop = asyncio.get_running_loop()
        batch_size = (
            config.THREAD_POOL_SIZE * 1000
        )  # config.THREAD_POOL_SIZE  # 병렬 처리

        # 스레드 풀을 작업 시작 시에만 생성
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=config.THREAD_POOL_SIZE)

        try:
            iterator = iter(reader)
            while True:
                batch = []
                lines = []
                if has_xy_cols:
                    geocode_func = self.geocode_xy
                else:
                    geocode_func = self.geocode

                try:
                    for _ in range(batch_size):
                        line, addr_or_xy = next(iterator)
                        if limit > 0 and count + len(batch) >= limit:
                            # 현재 배치는 처리하지 않고 중단
                            iterator = None  # 루프 종료용
                            break

                        batch.append(addr_or_xy)
                        lines.append(line)
                except StopIteration:
                    pass  # 파일 끝

                if not batch:
                    break

                # tasks = [
                #     loop.run_in_executor(
                #         self.executor,
                #         geocode_func,
                #         addr_or_xy,
                #         full_history_list,
                #     )
                #     for addr_or_xy in batch
                # ]

                # results = await asyncio.gather(*tasks)

                # results = self.executor.map(lambda args: geocode_func(*args), zip(batch, [full_history_list] * len(batch)))
                results = self.executor.map(
                    geocode_func, batch, zip(batch, [full_history_list] * len(batch))
                )

                for i, row_result in enumerate(results):
                    line = lines[i]

                    if row_result.get("pos_cd", "") in POS_CD_SUCCESS:
                        success_count += 1
                    else:
                        fail_count += 1

                    if row_result.get("hd_cd") or row_result.get("h4_cd"):
                        hd_success_count += 1

                    sample_wgs_x = row_result.pop("sample_wgs_x", 0)
                    sample_wgs_y = row_result.pop("sample_wgs_y", 0)
                    writer.write(line, row_result)

                    if count < sample_count:
                        row_result.pop("hd_history", None)
                        row_result[X_AXIS] = sample_wgs_x
                        row_result[Y_AXIS] = sample_wgs_y
                        sample.append(row_result)

                    count += 1

                    if count % 10000 == 0:
                        self.logger.info(
                            f"{count:,}, {time.time() - start_time:.1f}sec, success:{success_count}({success_count/count*100:.2f}%), fail:{fail_count}"
                        )

                if iterator is None:
                    break

        except Exception as e:
            self.logger.error("Failed to geocode: %s", e)
            return {"error": "지오코딩 오류: API-R003"}
        finally:
            # 작업 완료 후 스레드 풀 정리
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None

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

    async def _run_running_loop(
        self,
        download_dir,
        limit=10000,
        source_crs="EPSG:5179",
        target_crs="EPSG:4326",
        sample_count=0,
        reader: Reader = None,
        has_xy_cols=False,
    ):
        """
        파일을 읽어 지오코딩합니다. 결과를 파일로 저장합니다.

        loop = asyncio.get_running_loop(), loop.run_in_executor() 를 사용하는 버전. 느리다.

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
            self.tf = self.get_csr_transformer(target_crs, source_crs)
            self.tf_wgs84 = self.get_csr_transformer("EPSG:4326", source_crs)
        except:
            self.logger.error("Failed to create CRS transformer")
            return {"error": "좌표계 설정 오류: API-R001"}

        filename = os.path.basename(self.filepath)

        # reader, writer 생성
        # reader = None
        writer = None

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
        full_history_list = config.FULL_HISTORY_LIST
        loop = asyncio.get_running_loop()
        batch_size = 3000  # config.THREAD_POOL_SIZE  # 병렬 처리

        # 스레드 풀을 작업 시작 시에만 생성
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=config.THREAD_POOL_SIZE)

        try:
            iterator = iter(reader)
            while True:
                batch = []
                lines = []
                if has_xy_cols:
                    geocode_func = self.geocode_xy
                else:
                    geocode_func = self.geocode

                try:
                    for _ in range(batch_size):
                        line, addr_or_xy = next(iterator)
                        if limit > 0 and count + len(batch) >= limit:
                            # 현재 배치는 처리하지 않고 중단
                            iterator = None  # 루프 종료용
                            break

                        batch.append(addr_or_xy)
                        lines.append(line)
                except StopIteration:
                    pass  # 파일 끝

                if not batch:
                    break

                tasks = [
                    loop.run_in_executor(
                        self.executor,
                        geocode_func,
                        addr_or_xy,
                        full_history_list,
                    )
                    for addr_or_xy in batch
                ]

                results = await asyncio.gather(*tasks)

                for i, row_result in enumerate(results):
                    line = lines[i]

                    if row_result.get("pos_cd", "") in POS_CD_SUCCESS:
                        success_count += 1
                    else:
                        fail_count += 1

                    if row_result.get("hd_cd") or row_result.get("h4_cd"):
                        hd_success_count += 1

                    sample_wgs_x = row_result.pop("sample_wgs_x", 0)
                    sample_wgs_y = row_result.pop("sample_wgs_y", 0)
                    writer.write(line, row_result)

                    if count < sample_count:
                        row_result.pop("hd_history", None)
                        row_result[X_AXIS] = sample_wgs_x
                        row_result[Y_AXIS] = sample_wgs_y
                        sample.append(row_result)

                    count += 1

                    if count % 10000 == 0:
                        self.logger.info(
                            f"{count:,}, {time.time() - start_time:.1f}sec, success:{success_count}({success_count/count*100:.2f}%), fail:{fail_count}"
                        )

                if iterator is None:
                    break

        except Exception as e:
            self.logger.error("Failed to geocode: %s", e)
            return {"error": "지오코딩 오류: API-R003"}
        # finally:
        #     # 작업 완료 후 스레드 풀 정리
        #     if self.executor:
        #         self.executor.shutdown(wait=True)
        #         self.executor = None

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
        멀티 스레드로 실행됩니다. (실제로는 run()을 호출합니다)

        Args:
            download_dir (str): 지오코딩된 파일과 요약을 저장할 디렉토리. (prepare()에 전달된 filepath의 파일명을 사용하여 결과 파일 생성)
            limit (int, optional): 지오코딩할 레코드의 최대 개수. 기본값은 10000.
            target_crs (str, optional): 지오코딩된 좌표의 대상 좌표 참조 시스템(CRS). 기본값은 "EPSG:4326". (WGS84)

        Returns:
            dict: 지오코딩 결과 요약 + 주소 컬럼, 인코딩, 구분자
        """
        return await self.run(download_dir, limit, target_crs, sample_count)

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
            self.logger.error(f"좌표 변환 오류: {e}, {x}, {y}")
            return None, None

    def get_csr_transformer(self, target_crs="EPSG:4326", source_crs="EPSG:4326"):
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
                CRS.from_string(source_crs), CRS_TM128, always_xy=True
            )

            self.tf_int = True
            return tf
        else:
            return Transformer.from_crs(
                CRS.from_string(source_crs),
                CRS.from_string(target_crs),
                always_xy=True,
            )

    # def geocode_mt(self, reader: Reader, full_history_list=False):
    #     """
    #     멀티 스레드로 지오코딩을 수행합니다.

    #     Args:
    #         reader (Reader): Reader 객체로, 파일에서 주소를 읽어옵니다.
    #         full_history_list (bool): 행정동 history를 전체 조회할지 여부. 기본값은 False.

    #     Returns:
    #         dict: 지오코딩 결과 요약.
    #     """
    #     result = []
    #     print("geocode_mt start", reader.count())
    #     try:
    #         for line, addr in reader:
    #             # count += 1

    #             # 지오코딩
    #             row_result = self.geocode(addr, full_history_list=full_history_list)
    #             row_result["input_line"] = line
    #             result.append(row_result)
    #     except Exception as e:
    #         self.logger.error("Failed to geocode: %s", e)
    #         return {"error": "지오코딩 오류: API-R003"}

    #     print("geocode_mt end", reader.count())
    #     return result

    def geocode_xy(self, xy, full_history_list=False, **kwargs):
        """
        좌표를 알고 있는 경우, 지역 코드를 추가합니다.
        """
        val = {
            "x": xy[0],
            "y": xy[1],
            "success": True,
            "pos_cd": "원본좌표",
            "h1_cd": "",
            "h2_cd": "",
            "kostat_h1_cd": "",
            "kostat_h2_cd": "",
            "hd_cd": "",
            "hd_nm": "",
        }

        self.enrich_geocode_result(full_history_list, val)
        hd_history = val.get("hd_history", [])
        if hd_history:
            # 행정동 history가 있는 경우, 가장 최근 행정동 코드와 이름을 가져옵니다.
            val["hd_cd"] = hd_history[-1].get("EMD_CD", "")
            val["hd_nm"] = hd_history[-1].get("EMD_KOR_NM", "")
            h1_cd = self.geocoder.get_h1(val)
            h2_cd = self.geocoder.get_h2(val)
            val["h1_cd"] = h1_cd
            val["h2_cd"] = h2_cd
            val["kostat_h1_cd"] = self.geocoder.hcodeMatcher.get_kostat_h1_cd(h2_cd)
            val["kostat_h2_cd"] = self.geocoder.hcodeMatcher.get_kostat_h2_cd(h2_cd)
        else:
            # 행정동 history가 없는 경우, 기본값 설정
            val["hd_cd"] = ""
            val["hd_nm"] = ""
            val["h1_cd"] = ""
            val["h2_cd"] = ""
            val["kostat_h1_cd"] = ""
            val["kostat_h2_cd"] = ""

        return val

    def geocode(self, addr, full_history_list=False, **kwargs):
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
        if val:
            self.enrich_geocode_result(full_history_list, val)
        else:
            val = {
                "success": False,
                X_AXIS: None,
                Y_AXIS: None,
                "h1_cd": "",
                "h2_cd": "",
                "kostat_h1_cd": "",
                "kostat_h2_cd": "",
                "hd_cd": "",
                "hd_nm": "",
                "pos_cd": "",
                "errmsg": errs.ERR_UNRECOGNIZABLE_ADDRESS,
            }

        val["inputaddr"] = addr
        return val

    def enrich_geocode_result(self, full_history_list, val):
        if val and val["success"] and val["x"]:
            x = val.get("x", 0)
            y = val.get("y", 0)
            x1, y1 = self.transform(x, y)
            if x1:
                wgs_x, wgs_y = self.tf_wgs84.transform(x, y)

                # 행정동 history 검색
                if full_history_list:
                    # if kwargs.get("full_history_list", False):
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

        if "hd_history" not in val:
            val.update(
                {
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
            )

        # return val

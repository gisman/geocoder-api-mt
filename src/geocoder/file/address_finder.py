import os
import time
import pandas as pd
import numpy as np

from src.geocoder.geocoder import POS_CD_SUCCESS


class AddressFinder:
    """
    주소 컬럼을 찾는 클래스입니다.
    모든 컬럼의 텍스트를 지오코딩 테스트하여 주소 컬럼을 찾습니다.

    Args:
        filepath (str): 주소가 포함된 파일의 경로.
        charenc (str): 파일의 문자 인코딩.
        delimiter (str): 파일에서 사용된 구분자.

    Attributes:
        filepath (str): 주소가 포함된 파일의 경로.
        filename (str): 파일의 이름.
        charenc (str): 파일의 문자 인코딩.
        delimiter (str): 파일에서 사용된 구분자.

    Methods:
        geocode: 주소 목록에 대해 지오코딩을 수행합니다.
        find: DataFrame에서 가장 적합한 주소 열을 찾습니다.
        read_data: 파일에서 데이터를 읽고 pandas DataFrame을 반환합니다.
    """

    def __init__(self, filepath, charenc, delimiter):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.charenc = charenc
        self.delimiter = delimiter
        # self.uploaded_filename = uploaded_filename

    def geocode(self, addrs):
        """
        주소 목록에 대해 지오코딩을 수행합니다.

        Args:
            addrs (list): 지오코딩할 주소의 목록.

        Returns:
            dict: 지오코딩 결과의 요약, 총 개수, 성공 개수를 포함합니다.
        """

        summary = {}
        count = 0
        success_count = 0
        fail_count = 0
        start_time = time.time()

        for addr in addrs:
            count += 1
            val = self.geocoder.search(addr)
            if not val:
                val = {}
                fail_count += 1
            elif val["success"]:
                if val.get("pos_cd") in POS_CD_SUCCESS and val["x"]:
                    success_count += 1
                else:
                    fail_count += 1

        # summary["total_time"] = time.time() - start_time
        summary["total_count"] = count
        summary["success_count"] = success_count
        # fail_count = count - success_count
        # summary["fail_count"] = fail_count

        return summary

    def find(self, geocoder):
        """
        DataFrame에서 가장 적합한 주소 열을 찾습니다.

        Args:
            geocoder: 지오코딩에 사용할 geocoder 객체.

        Returns:
            dict: 가장 적합한 주소 열의 인덱스, 총 개수, 성공 개수를 포함합니다.
            실제 필요한 것은 열의 인덱스입니다. 총 개수, 성공 개수는 참고용입니다.
        """
        df100 = self.read_data(100)
        addrcol = ""
        max_success = -1
        head_addr = ""
        self.geocoder = geocoder
        for col, item in df100.items():
            if df100[col].dtype == np.float64 or df100[col].dtype == np.int64:
                continue

            summary = self.geocode(df100[col])
            summary["col"] = col
            if summary["success_count"] > max_success:
                max_success = summary["success_count"]
                addrcol = col
                max_summary = summary
                if (
                    max_summary["total_count"] > 0
                    and max_success / max_summary["total_count"] > 0.9
                ):
                    break

        if (
            addrcol
            and max_summary["total_count"] > 0
            and max_success / max_summary["total_count"] > 0.3
        ):
            max_summary["col"] = df100.columns.get_loc(addrcol)
            return max_summary
        else:
            return {
                "col": 0,
                # "total_time": 0,
                # "total_count": 0,
                # "success_count": 0,
                # "fail_count": 0,
            }

    def read_data(self, rows=100):
        """
        파일에서 데이터를 읽어 pandas DataFrame으로 반환합니다.
        csv 파일만 취급한다. 사용자가 xlsx 파일을 업로드하면 geocoder-dj가 csv로 변환한 후 전달한다.

        Args:
            rows (int): 파일에서 읽을 행의 수.

        Returns:
            pandas.DataFrame: DataFrame으로 읽은 데이터.
        """
        charenc = self.charenc

        if (
            True
        ):  # api는 csv 파일만 취급한다. 사용자가 xlsx 파일을 업로드하면 geocoder-dj가 csv로 변환한 후 전달한다.
            # if self.uploaded_filename.upper().endswith(("CSV", "TSV", "TXT")):
            delimiter = self.delimiter
            df_head = pd.read_csv(
                self.filepath,
                delimiter=delimiter,
                on_bad_lines="skip",
                encoding=charenc,
                encoding_errors="ignore",
                nrows=rows,
            )
            cols = df_head.shape[1]

            df = pd.read_csv(
                self.filepath,
                delimiter=delimiter,
                on_bad_lines="skip",
                encoding=charenc,
                encoding_errors="ignore",
                nrows=rows,
                usecols=range(cols),
            )

        return df

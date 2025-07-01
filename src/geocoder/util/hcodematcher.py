import csv

from src import config


class HCodeMatcher:
    def __init__(self):
        """
        HCodeMatcher 클래스 생성자.
        '{config.CODE_DATA_DIR}/h1_h2_code_match.csv' 파일을 읽어와서 hcode_dict 딕셔너리에 저장합니다.
        """
        filename = f"{config.CODE_DATA_DIR}/h1_h2_code_match.csv"
        self.hcode_dict = {}
        with open(filename, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 시도명,시군구명,시도코드,시군구코드,최신시도코드,최신시군구코드,비고,통계청 시도코드,통계청 시군구코드
                self.hcode_dict[row["시군구코드"]] = row

    def _get_current_code(self, code):
        """
        주어진 코드에 해당하는 최신 코드를 반환합니다.
        코드가 None이거나 빈 문자열일 경우 None을 반환합니다.

        :param code: 원본 코드 (hd_cd, ld_cd, road_cd 등)
        :return: 최신 코드
        """
        if code:
            h23_cd = self.get_h23_cd(code[:5])
            return f"{h23_cd[:5]}{code[5:]}"
        return None

    def get_current_hd_cd(self, hd_cd):
        """
        주어진 행정동코드(hd_cd)에 해당하는 최신 행정동코드를 반환합니다.

        :param hd_cd: 행정동코드
        :return: 최신 행정동코드
        """
        return self._get_current_code(hd_cd)

    def get_current_ld_cd(self, ld_cd):
        """
        주어진 법정동코드(ld_cd)에 해당하는 최신 법정동코드를 반환합니다.

        :param ld_cd: 법정동코드
        :return: 최신 법정동코드
        """
        return self._get_current_code(ld_cd)

    def get_current_road_cd(self, road_cd):
        """
        주어진 도로코드(road_cd)에 해당하는 최신 도로코드를 반환합니다.
        road_cd가 None이거나 빈 문자열일 경우 None을 반환합니다.

        :param road_cd: 도로코드
        :return: 최신 도로코드
        """
        return self._get_current_code(road_cd)

    def get_h23_cd(self, h23_cd):
        """
        주어진 시군구코드(h2_cd)에 해당하는 최신 시군구코드를 반환합니다.

        :param h2_cd: 시군구코드
        :return: 최신 시군구코드
        """
        if h23_cd:
            if d := self.hcode_dict.get(h23_cd):
                return d["최신시군구코드"]

        return ""

    def get_h23_nm(self, h23_cd):
        """
        주어진 시군구코드(h2_cd)에 해당하는 최신 시군구명을 반환합니다.
        h2_cd가 None이거나 빈 문자열일 경우 빈 문자열을 반환합니다.

        시군구 대표주소 생성할 때 사용

        :param h2_cd: 시군구코드
        :return: 최신 시도코드
        """
        if h23_cd:
            if d := self.hcode_dict.get(h23_cd):
                return d["시군구명"]

        return ""

    def get_kostat_h1_cd(self, h1_cd):
        """
        주어진 시군구코드(h2_cd)에 해당하는 통계청 시도코드를 반환합니다.
        h2_cd가 None이거나 빈 문자열일 경우 빈 문자열을 반환합니다.

        :param h2_cd: 시군구코드
        :return: 통계청 시도코드
        """
        if h1_cd:
            if code_dic := self.hcode_dict.get(h1_cd):
                return code_dic.get("통계청 시도코드", "")

        return ""

    def get_kostat_h2_cd(self, h23_cd):
        """
        주어진 시군구코드(h2_cd)에 해당하는 통계청 시군구코드를 반환합니다.
        h2_cd가 None이거나 빈 문자열일 경우 빈 문자열을 반환합니다.

        :param h2_cd: 시군구코드
        :return: 통계청 시군구코드
        """
        if h23_cd:
            if d := self.hcode_dict.get(h23_cd):
                return d["통계청 시군구코드"]

        return ""

    def get_h1_cd(self, h23_cd):
        """
        주어진 시군구코드(h2_cd)에 해당하는 최신 광역시도코드를 반환합니다.
        h2_cd가 None이거나 빈 문자열일 경우 빈 문자열을 반환합니다.

        시군구 대표주소 생성할 때 사용

        :param h2_cd: 시군구코드
        :return: 최신 시도코드
        """
        if h23_cd:
            if d := self.hcode_dict.get(h23_cd):
                return d["최신시도코드"]

        return ""

    def get_h1_nm(self, h2_cd):
        """
        주어진 시군구코드(h2_cd)에 해당하는 최신 광역시도명을 반환합니다.
        h2_cd가 None이거나 빈 문자열일 경우 빈 문자열을 반환합니다.

        시군구 대표주소 생성할 때 사용

        :param h2_cd: 시군구코드
        :return: 최신 시도코드
        """
        if h2_cd:
            if d := self.hcode_dict.get(h2_cd):
                return d["시도명"]

        return ""

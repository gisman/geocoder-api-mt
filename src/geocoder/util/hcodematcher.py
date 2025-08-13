import csv

from src import config
from difflib import SequenceMatcher
from .HSimplifier import HSimplifier


class HCodeMatcher:
    def __init__(self):
        """
        HCodeMatcher 클래스 생성자.
        '{config.CODE_DATA_DIR}/h1_h2_code_match.csv' 파일을 읽어와서 hcode_dict 딕셔너리에 저장합니다.
        """
        filename = f"{config.CODE_DATA_DIR}/h1_h2_code_match.csv"
        self.hcode_dict = {}
        self.h23_search_index = {}
        with open(filename, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 시도명,시군구명,시도코드,시군구코드,최신시도코드,최신시군구코드,비고,통계청 시도코드,통계청 시군구코드
                self.hcode_dict[row["시군구코드"]] = row

                self._add_h23_search_index(row)

        self.h1_hash_dict = {}
        hSimplifier = HSimplifier()
        for data in self.hcode_dict.values():
            h1_nm = data["시도명"]
            h1_nm_hash = hSimplifier.h1Hash(h1_nm)
            self.h1_hash_dict[h1_nm_hash] = data["최신시도코드"]

    def _add_h23_search_index(self, row):
        h23_nm_no_space = row["시군구명"].replace(" ", "")
        h23_nm_decomposed = self._decompose_korean(h23_nm_no_space)

        key = f"{row['시도코드']}_{h23_nm_no_space}"
        self.h23_search_index[key] = {
            "h1_cd": row["시도코드"],
            "h23_nm": h23_nm_no_space,
            "h23_nm_decomposed": h23_nm_decomposed,
        }

        if " " in row["시군구명"]:
            h2_h3 = row["시군구명"].split(" ")
            h2 = h2_h3[0]
            key = f"{row['시도코드']}_{h2}"
            self.h23_search_index[key] = {
                "h1_cd": row["시도코드"],
                "h23_nm": h2,
                "h23_nm_decomposed": self._decompose_korean(h2),
            }

            h3 = h2_h3[1]
            key = f"{row['시도코드']}_{h3}"
            self.h23_search_index[key] = {
                "h1_cd": row["시도코드"],
                "h23_nm": h23_nm_no_space,
                "h23_nm_decomposed": self._decompose_korean(h3),
            }

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

    def _similarity(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    def _decompose_korean(self, text):
        """
        한글 문자열을 자음, 모음으로 분해하여 정수 배열로 변환합니다.
        """

        def decompose_char(char):
            base_code, chosung, jungsung = 44032, 588, 28
            chosung_list = [
                0x3131,
                0x3132,
                0x3134,
                0x3137,
                0x3138,
                0x3139,
                0x3141,
                0x3142,
                0x3143,
                0x3145,
                0x3146,
                0x3147,
                0x3148,
                0x3149,
                0x314A,
                0x314B,
                0x314C,
                0x314D,
                0x314E,
            ]
            jungsung_list = [
                0x314F,
                0x3150,
                0x3151,
                0x3152,
                0x3153,
                0x3154,
                0x3155,
                0x3156,
                0x3157,
                0x3158,
                0x3159,
                0x315A,
                0x315B,
                0x315C,
                0x315D,
                0x315E,
                0x315F,
                0x3160,
                0x3161,
                0x3162,
                0x3163,
            ]
            jongsung_list = [
                0x0000,
                0x3131,
                0x3132,
                0x3133,
                0x3134,
                0x3135,
                0x3136,
                0x3137,
                0x3139,
                0x313A,
                0x313B,
                0x313C,
                0x313D,
                0x313E,
                0x313F,
                0x3140,
                0x3141,
                0x3142,
                0x3144,
                0x3145,
                0x3146,
                0x3147,
                0x3148,
                0x314A,
                0x314B,
                0x314C,
                0x314D,
                0x314E,
            ]

            if "가" <= char <= "힣":
                code = ord(char) - base_code
                chosung_idx = code // chosung
                jungsung_idx = (code % chosung) // jungsung
                jongsung_idx = (code % chosung) % jungsung
                return [
                    chosung_list[chosung_idx],
                    jungsung_list[jungsung_idx],
                    jongsung_list[jongsung_idx],
                ]
            return [ord(char)]

        result = []
        for c in text:
            result.extend(decompose_char(c))
        return result

    def search_h1_cd(self, h1_nm_hash):
        """
        주어진 시도명(h1_nm)에 해당하는 시도코드를 반환합니다.
        h1_nm이 None이거나 빈 문자열일 경우 빈 문자열을 반환합니다.

        :param h1_nm: 시도명
        :return: 시도코드
        """
        return self.h1_hash_dict.get(h1_nm_hash, None)

    def search_most_likely_h23_nm(self, h23_nm, h1_cd):
        """
        주어진 시군구명(h23_nm)에 가장 유사한 시군구명을 반환합니다.
        h23_nm이 None이거나 빈 문자열일 경우 빈 문자열을 반환합니다.

        :param h23_nm: 시군구명
        :return: 가장 유사한 시군구명
        """
        if h23_nm:
            if h23_nm.startswith("세종"):
                return "세종"

            h23_nm_decomposed = self._decompose_korean(h23_nm)

            # 후보군에서 가장 유사한 시군구명을 찾습니다.
            # 여기서는 단순히 h23_nm과 같은 이름을 가진 항목을 찾습니다.
            best_similarity = 0.0
            for key, data in self.h23_search_index.items():
                if h1_cd and not key.startswith(h1_cd):
                    continue

                similarity = self._similarity(
                    data["h23_nm_decomposed"], h23_nm_decomposed
                )
                found_h23_nm = data["h23_nm"]
                if similarity == 1.0:
                    return found_h23_nm
                if similarity > best_similarity:
                    best_match = found_h23_nm
                    best_similarity = similarity

            return best_match if best_similarity > 0.8 else ""
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

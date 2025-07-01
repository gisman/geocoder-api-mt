import csv

from src import config

"""
PNU는 Parcel Number의 약자로 필지고유번호이다.
법정동코드(10자) + 필지구분(1자) + 주번지(4자) + 부번지(4자)
필지 구분: 1=일반, 2=산

행정표준관리시스템에서 다운로드한다. EUC-KR 인코딩, 구분자는 TAB이다.

법정동코드	법정동명	폐지여부
1100000000	서울특별시	존재
1111000000	서울특별시 종로구	존재
1111010100	서울특별시 종로구 청운동	존재
1111010200	서울특별시 종로구 신교동	존재
1111010300	서울특별시 종로구 궁정동	존재
1111010400	서울특별시 종로구 효자동	존재
1111010500	서울특별시 종로구 창성동	존재
1111010600	서울특별시 종로구 통의동	존재
1111010700	서울특별시 종로구 적선동	존재
"""


class PNUMatcher:
    """
    PNU (Parcel Number) 매칭을 위한 클래스.
    법정동코드와 필지 정보를 이용하여 법정동명을 반환한다.
    """

    def __init__(self):
        """
        PNU 매칭을 위한 초기화 메서드.
        PNU 데이터를 CSV 파일에서 읽어와 법정동코드와 매핑한다.
        """
        filename = f"{config.CODE_DATA_DIR}/PNU.csv"
        self.ldong_dict = {}
        with open(filename, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 법정동코드,법정동명,폐지여부
                # 괄호 예외처리
                # 4729025331,경상북도 경산시 진량읍 평사리(坪沙),존재
                if row["법정동명"].endswith(")"):
                    row["법정동명"] = row["법정동명"].split("(")[0].strip()

                self.ldong_dict[row["법정동코드"]] = row

    def get_ldong_name(self, pnu) -> str:
        """
        주어진 PNU에서 법정동코드를 추출하여 법정동명을 반환한다.

        :param pnu: 필지고유번호 (PNU)
        :return: 법정동명
        """
        if pnu[:10] in self.ldong_dict:
            return self.ldong_dict[pnu[:10]]

        ld_cd = f"{pnu[:8]}00"  # 법정동코드 추출
        if ld_cd in self.ldong_dict:
            return self.ldong_dict[ld_cd]

        ld_cd = f"{pnu[:7]}000"  # 법정동코드 추출
        if ld_cd in self.ldong_dict:
            return self.ldong_dict[ld_cd]

        return {}

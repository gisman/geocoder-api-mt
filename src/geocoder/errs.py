ERR_BLD_HASH = 1  # "BLD HASH ERROR"
ERR_JIBUN_HASH = 2  # "JIBUN HASH ERROR"
ERR_NOT_ADDRESS = 3  # "NOT_ADDRESS ERROR"
ERR_ROAD_HASH = 4  # "ROAD HASH ERROR"
ERR_RUNTIME = 5  # "RUNTIME ERROR"
ERR_UNRECOGNIZABLE_ADDRESS = 6  # "UNRECOGNIZABLE_ADDRESS ERROR"

ERR_NOT_FOUND = 11  # "NOTFOUND ERROR"
ERR_POS_CD_NOT_FOUND = 12  # "POS_CD_NOT_FOUND ERROR"
ERR_ROAD_NOT_FOUND = 13  # "ROAD_NOT_FOUND ERROR"
ERR_RI_NOT_FOUND = 14  # "RI_NOT_FOUND ERROR"
ERR_DONG_NOT_FOUND = 15  # "DONG_NOT_FOUND ERROR"
ERR_H23_NOT_FOUND = 16  # "H23_NOT_FOUND ERROR"
ERR_H1_NOT_FOUND = 17  # "H1_NOT_FOUND ERROR"
ERR_REGION_NOT_FOUND = 18  # "REGION_NOT_FOUND ERROR"
ERR_REPRESENTATIVE_ADDRESS_NOT_FOUND = 19  # "REPRESENTATIVE_ADDRESS_NOT_FOUND ERROR"

ERR_H1_NM_NOT_FOUND = 21  # "H1_NM_NOT_FOUND ERROR"
ERR_ROAD_NM_NOT_FOUND = 22  # "ROAD_NM_NOT_FOUND ERROR"
ERR_BLD_NM_NOT_FOUND = 23  # "BLD_NAME_NOT_FOUND ERROR"
ERR_ROAD_NOT_UNIQUE_H23_NM = 31  # "ROAD_NOT_UNIQUE_H23_NM ERROR"
ERR_NOT_UNIQUE_H1_NM = 32  # "NOT_UNIQUE_H1_NM ERROR"
ERR_NOT_UNIQUE_ROAD_CD = 33  # "NOT_UNIQUE_ROAD_CD ERROR"
ERR_NOT_UNIQUE_RI_NM = 34  # "NOT_UNIQUE_ROAD_CD ERROR"

ERR_NEAR_ROAD_BLD_NOT_FOUND = 41  # "NEAR_ROAD_BLD_NOT_FOUND ERROR"
ERR_NEAR_JIBUN_NOT_FOUND = 42  # "NEAR_JIBUN_NOT_FOUND ERROR"

ERR_NAME_RI = 51  # "RI NAME ERROR"
ERR_NAME_H4 = 52  # "H4 NAME ERROR"
ERR_NAME_H23 = 53  # "H23 NAME ERROR"

INFO_JIBUN_ADDRESS = 101  # "JIBUN ADDRESS INFO"
INFO_BLD_ADDRESS = 102  # "BLD ADDRESS INFO"
INFO_ROAD_ADDRESS = 103  # "ROAD ADDRESS INFO"
INFO_RI_END_ADDRESS = 104  # "RI END ADDRESS INFO"
INFO_ROAD_END_ADDRESS = 105  # "ROAD END ADDRESS INFO"
INFO_H4_END_ADDRESS = 106  # "H4 END ADDRESS INFO"
INFO_H23_END_ADDRESS = 107  # "H23 END ADDRESS INFO"
INFO_H1_END_ADDRESS = 108  # "H1 END ADDRESS INFO"

INFO_NEAR_ROAD_BLD_FOUND = 111  # "NEAR_ROAD_BLD_FOUND INFO"
INFO_NEAR_JIBUN_FOUND = 112  # "NEAR_JIBUN_FOUND INFO"
INFO_SIMILAR_BLD_FOUND = 113  # "SIMILAR_BLD_FOUND INFO"


class ErrList:
    err_str_map = {
        ERR_BLD_HASH: "BLD_HASH_ERROR",
        ERR_JIBUN_HASH: "JIBUN_HASH_ERROR",
        ERR_NOT_ADDRESS: "NOT_ADDRESS_ERROR",
        ERR_ROAD_HASH: "ROAD_HASH_ERROR",
        ERR_RUNTIME: "RUNTIME_ERROR",
        ERR_UNRECOGNIZABLE_ADDRESS: "UNRECOGNIZABLE_ADDRESS_ERROR",
        ERR_NOT_FOUND: "NOTFOUND_ERROR",
        ERR_POS_CD_NOT_FOUND: "POS_CD_NOT_FOUND_ERROR",
        ERR_ROAD_NOT_FOUND: "ROAD_NOT_FOUND_ERROR",
        ERR_RI_NOT_FOUND: "RI_NOT_FOUND_ERROR",
        ERR_DONG_NOT_FOUND: "DONG_NOT_FOUND_ERROR",
        ERR_H23_NOT_FOUND: "H23_NOT_FOUND_ERROR",
        ERR_H1_NOT_FOUND: "H1_NOT_FOUND_ERROR",
        ERR_REGION_NOT_FOUND: "REGION_NOT_FOUND_ERROR",
        ERR_REPRESENTATIVE_ADDRESS_NOT_FOUND: "REPRESENTATIVE_ADDRESS_NOT_FOUND_ERROR",
        ERR_H1_NM_NOT_FOUND: "H1_NM_NOT_FOUND_ERROR",
        ERR_ROAD_NM_NOT_FOUND: "ROAD_NM_NOT_FOUND_ERROR",
        ERR_BLD_NM_NOT_FOUND: "BLD_NAME_NOT_FOUND_ERROR",
        ERR_ROAD_NOT_UNIQUE_H23_NM: "ROAD_NOT_UNIQUE_H23_NM_ERROR",
        ERR_NOT_UNIQUE_H1_NM: "NOT_UNIQUE_H1_NM_ERROR",
        ERR_NOT_UNIQUE_ROAD_CD: "NOT_UNIQUE_ROAD_CD_ERROR",
        ERR_NEAR_ROAD_BLD_NOT_FOUND: "NEAR_ROAD_BLD_NOT_FOUND_ERROR",
        ERR_NEAR_JIBUN_NOT_FOUND: "NEAR_JIBUN_NOT_FOUND_ERROR",
        ERR_NAME_RI: "RI_NAME_ERROR",
        ERR_NAME_H4: "H4_NAME_ERROR",
        ERR_NAME_H23: "H23_NAME_ERROR",
        INFO_JIBUN_ADDRESS: "JIBUN_ADDRESS_INFO",
        INFO_BLD_ADDRESS: "BLD_ADDRESS_INFO",
        INFO_ROAD_ADDRESS: "ROAD_ADDRESS_INFO",
        INFO_RI_END_ADDRESS: "RI_END_ADDRESS_INFO",
        INFO_ROAD_END_ADDRESS: "ROAD_END_ADDRESS_INFO",
        INFO_H4_END_ADDRESS: "H4_END_ADDRESS_INFO",
        INFO_H23_END_ADDRESS: "H23_END_ADDRESS_INFO",
        INFO_H1_END_ADDRESS: "H1_END_ADDRESS_INFO",
        INFO_NEAR_ROAD_BLD_FOUND: "NEAR_ROAD_BLD_FOUND_INFO",
        INFO_NEAR_JIBUN_FOUND: "NEAR_JIBUN_FOUND_INFO",
        INFO_SIMILAR_BLD_FOUND: "SIMILAR_BLD_FOUND_INFO",
    }

    # errs = []
    def __init__(self):
        """
        ErrList 클래스의 생성자입니다.
        초기화 시 오류 코드 리스트를 비웁니다.
        """
        self.errs = []

    def append(self, err_cd, detail=None):
        """
        오류 코드를 추가합니다.
        Args:
            err_cd (str or int): 오류 코드.
        """
        self.errs.append({"err_cd": err_cd, "detail": detail})

    def to_err_str(self, err_cd=None) -> str:
        """
        주어진 오류 코드를 메시지로 변환합니다.
        Args:
            err_cd (str): 오류 코드.
        Returns:
            str: 오류 메시지
        """
        if not err_cd:
            err_cd = [e["err_cd"] for e in self.errs]

        if isinstance(err_cd, list):
            return ", ".join([self.to_err_str(e) for e in err_cd])
        elif isinstance(err_cd, int):
            return self.err_str_map.get(err_cd, "UNKNOWN ERROR")

        return "UNKNOWN ERROR"

    def __str__(self):
        """
        ErrList 객체를 문자열로 변환합니다.
        Returns:
            str: 오류 메시지
        """
        return self.to_err_str(self.errs) if self.errs else "No errors"

    def has_err_cd(self, err_cd):
        """
        주어진 오류 코드가 ErrList에 있는지 확인합니다.
        Args:
            err_cd (str or int): 확인할 오류 코드.
        Returns:
            bool: 오류 코드가 ErrList에 있으면 True, 아니면 False.
        """
        return any(e["err_cd"] == err_cd for e in self.errs)

    def to_err_message(self):
        """
        주어진 오류 코드를 메시지로 변환합니다.
        Args:
            err_cd (str): 오류 코드.
        Returns:
            str: 오류 메시지
        """
        if ERR_UNRECOGNIZABLE_ADDRESS in self.errs:
            return "주소 형식이 아님"

        # ROAD_ADDRESS_INFO, NOTFOUND_ERROR, NEAR_ROAD_BLD_NOT_FOUND_ERROR,
        # ROAD_NOT_FOUND_ERROR, DONG_NOT_FOUND_ERROR, H23_NOT_FOUND_ERROR,
        # H1_NOT_FOUND_ERROR, ROAD_NOT_FOUND_ERROR, DONG_NOT_FOUND_ERROR'

        if self.has_err_cd(INFO_RI_END_ADDRESS):
            return "리 이름까지 유효"
        if self.has_err_cd(INFO_ROAD_END_ADDRESS):
            return "도로 이름까지 유효"
        if self.has_err_cd(INFO_H4_END_ADDRESS):
            return "행정동 또는 법정동 이름까지 유효"
        if self.has_err_cd(INFO_H23_END_ADDRESS):
            return "시군구 이름까지 유효"
        if self.has_err_cd(INFO_H1_END_ADDRESS):
            return "광역시도 이름까지 유효"

        return ""

    def get_err_by_cd(self, err_cd):
        err = next((e for e in self.errs if e["err_cd"] == err_cd), None)
        return err or {}

    def to_detail_message(self):
        """
        오류 코드에 대한 상세 메시지를 반환합니다.
        Returns:
            str: 상세 오류 메시지
        """
        if not self.errs:
            return ""

        messages = []
        if self.has_err_cd(INFO_NEAR_JIBUN_FOUND):
            err = self.get_err_by_cd(INFO_NEAR_JIBUN_FOUND)
            messages.append(f'{err.get("detail", "")}')
        elif self.has_err_cd(INFO_NEAR_ROAD_BLD_FOUND):
            err = self.get_err_by_cd(INFO_NEAR_ROAD_BLD_FOUND)
            messages.append(f'{err.get("detail", "")}')
        else:
            if self.has_err_cd(ERR_NEAR_JIBUN_NOT_FOUND):
                err = self.get_err_by_cd(ERR_NEAR_JIBUN_NOT_FOUND)
                messages.append(f'인근 지번 주소 없음: {err.get("detail", "")}')

            elif self.has_err_cd(ERR_NEAR_ROAD_BLD_NOT_FOUND):
                err = self.get_err_by_cd(ERR_NEAR_ROAD_BLD_NOT_FOUND)
                messages.append(f'인근 도로명 주소 없음: {err.get("detail", "")}')

            elif self.has_err_cd(ERR_ROAD_NOT_UNIQUE_H23_NM):
                err = self.get_err_by_cd(ERR_ROAD_NOT_UNIQUE_H23_NM)
                messages.append(f'도로명 특정 불가: {err.get("detail", "")}')

            elif self.has_err_cd(INFO_SIMILAR_BLD_FOUND):
                err = self.get_err_by_cd(INFO_SIMILAR_BLD_FOUND)
                messages.append(f'건물명: {err.get("detail", "")}')

            else:
                for err in self.errs:
                    err_cd = err.get("err_cd", "")
                    err_str = self.err_str_map.get(err_cd, "UNKNOWN ERROR")
                    detail = err.get("detail", "")
                    if detail:
                        messages.append(f"{err_str}: {detail}")

        return ", ".join(messages).strip() if messages else ""

    def last_detail_message(self, has_detail=True):
        """
        마지막 오류 메시지를 반환합니다.
        """
        err = self.errs[-1] if self.errs else None
        if has_detail and not err.get("detail"):
            return None

        if err:
            return f'{self.to_human_readable(err.get("err_cd", ""))}: {err.get("detail", "")}'.strip()
        return None

    def to_human_readable(self, err_cd):
        """
        오류 코드를 사람이 읽을 수 있는 형식으로 변환합니다.
        Args:
            err_cd (str or int): 오류 코드.
        Returns:
            str: 사람이 읽을 수 있는 오류 메시지
        """
        human_readable_map = {
            ERR_NEAR_JIBUN_NOT_FOUND: "인근 지번 주소 없음",
            ERR_NEAR_ROAD_BLD_NOT_FOUND: "인근 도로명 주소 없음",
            ERR_ROAD_NOT_UNIQUE_H23_NM: "도로명 특정 불가",
            INFO_SIMILAR_BLD_FOUND: "건물명",
            INFO_NEAR_ROAD_BLD_FOUND: "인근 도로명 주소",
            INFO_NEAR_JIBUN_FOUND: "인근 지번 주소",
            ERR_H23_NOT_FOUND: "시군구 없음",
            ERR_ROAD_NOT_FOUND: "도로명 없음",
            ERR_RI_NOT_FOUND: "리 없음",
            ERR_DONG_NOT_FOUND: "행정동 없음",
            ERR_H23_NOT_FOUND: "시군구 없음",
            ERR_H1_NOT_FOUND: "광역시도 없음",
            ERR_REGION_NOT_FOUND: "지역 없음",
            ERR_REPRESENTATIVE_ADDRESS_NOT_FOUND: "대표 주소 없음",
            ERR_BLD_NM_NOT_FOUND: "건물명 없음",
        }

        if err_cd in human_readable_map:
            return human_readable_map[err_cd]

        return self.err_str_map.get(err_cd, "UNKNOWN ERROR")

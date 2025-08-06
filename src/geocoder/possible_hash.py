from src.geocoder.address_cls import AddressCls
from src.geocoder.errs import *
from src.geocoder.hasher import Hasher
from src.geocoder.tokens import *
from src.geocoder.pos_cd import *
import src.config as config
from .errs import ERR_STR_MAP


class PossibleHash:
    hash: str = None
    addressCls: str = None
    pos_cd_filter: set[str] = None  # 필터링할 pos_cd 값들
    err_failed: str = None
    err_detail: str = None
    info_success: str = None
    info_detail: str = None
    prev_errs: set[int] = None
    # err_msg_when_success: bool = False

    def __init__(
        self,
        hash: str,
        addressCls: str,
        pos_cd_filter: set[str] = None,
        err_failed: str = None,
        err_detail: str = None,
        info_success: str = None,
        info_detail: str = None,
        prev_errs: set[int] = None,
        # err_msg_when_success: bool = False,
    ):
        self.hash = hash
        self.addressCls = addressCls
        self.pos_cd_filter = pos_cd_filter or set()
        self.err_failed = err_failed
        self.err_detail = err_detail
        self.info_success = info_success
        self.info_detail = info_detail
        self.prev_errs = prev_errs
        # self.err_msg_when_success = err_msg_when_success

    def pass_condition(self, prev_err: int):
        if self.prev_errs and prev_err in self.prev_errs:
            return True

        return False

    def to_dict(self):
        return {
            "hash": self.hash,
            "addressCls": self.addressCls,
            "pos_cd_filter": self.pos_cd_filter,
            "err_failed": self.err_failed,
            "err_detail": self.err_detail,
            "info_success": self.info_success,
            "info_detail": self.info_detail,
            "err_msg_when_success": self.err_msg_when_success,
        }

    def get_hash(self):
        return self.hash

    def get_addressCls(self):
        return self.addressCls

    def get_pos_cd_filter(self):
        return self.pos_cd_filter

    def get_err_failed(self):
        return self.err_failed

    def get_err_detail(self):
        return self.err_detail

    def get_info_success(self):
        return self.info_success

    def get_info_detail(self):
        return self.info_detail or ""

    def is_add_msg_when_success(self):
        return self.info_success is not None

    def __str__(self):
        return f"""{self.hash}, {self.addressCls}, {self.pos_cd_filter}
    failed=({ERR_STR_MAP.get(self.err_failed)}, {self.err_detail}), 
    success=({ERR_STR_MAP.get(self.info_success)}, {self.info_detail}))"""


def possible_hashs(
    toks: Tokens,
    hash: str,
    hasher: Hasher,
    addressCls,
    jibunAddress,
    bldAddress,
    roadAddress,
    hsimplifier,
    hcodeMatcher,
):
    # def possible_hashs(self, toks: Tokens, hash: str, addressCls) -> list[str]:
    """
    주어진 주소에서 가능한 해시 값을 생성합니다.

    건물 좌표 검색을 위해 건물명, 건물동 검색을 먼저.

    JIBUN_ADDRESS
        TOKEN_BLD, TOKEN_BLD_DONG
        TOKEN_BLD
        건물명 제외
        인근 지번
        리 빼고 위 반복

    ROAD_ADDRESS
        TOKEN_BLD, TOKEN_BLD_DONG   전남 무안군 삼향읍 남악리 오룡길 1(남악리 100) 전라남도청 본관
        TOKEN_BLD                   전남 무안군 삼향읍 남악리 오룡길 1(남악리 100) 전라남도청
        건물명 제외                   전남 무안군 삼향읍 남악리 오룡길 1(남악리 100)
        인근 도로명 건번               전남 무안군 삼향읍 남악리 오룡길 [2, 3, 4... 1-1, 1-2, 1-3, 1-4, ...]
        리 빼고 위 반복               전남 무안군 삼향읍 오룡길 1 전라남도청 본관
        동 빼고 위 반복               전남 무안군 오룡길 1 전라남도청 본관
        도로명 이하 반복               오룡길 1 전라남도청 본관, 오룡길 1 전라남도청, 오룡길 1

    BLD_ADDRESS
        TOKEN_BLD, TOKEN_BLD_DONG
        TOKEN_BLD
        리 빼고 위 반복

    Args:
        address (str): 주소 문자열.

    Returns:
        list: 가능한 해시 정보의 리스트.

        NOT_ADDRESS = "NOT_ADDRESS"
        JIBUN_ADDRESS = "JIBUN_ADDRESS"
        BLD_ADDRESS = "BLD_ADDRESS"
        ROAD_ADDRESS = "ROAD_ADDRESS"

        ROAD_END_ADDRESS = "ROAD_END_ADDRESS"
        RI_END_ADDRESS = "RI_END_ADDRESS"
        H4_END_ADDRESS = "H4_END_ADDRESS"
        H23_END_ADDRESS = "H23_END_ADDRESS"
        H1_END_ADDRESS = "H1_END_ADDRESS"

    """

    # hash_infos = []

    if addressCls == AddressCls.NOT_ADDRESS:
        return []

    # 도로명에서 끝나는 주소
    if addressCls == AddressCls.ROAD_END_ADDRESS:
        road_nm = toks.get_text(TOKEN_ROAD)
        yield PossibleHash(
            hash=hash,
            addressCls=AddressCls.ROAD_END_ADDRESS,
            err_failed=ERR_ROAD_NOT_FOUND,
            err_detail=road_nm,
            info_success=INFO_ROAD_END_ADDRESS,
            info_detail=road_nm,
        )

    # 리에서 끝나는 주소
    if addressCls == AddressCls.RI_END_ADDRESS:
        ri_nm = toks.get_text(TOKEN_RI)
        yield PossibleHash(
            hash=hash,
            addressCls=AddressCls.RI_END_ADDRESS,
            err_failed=ERR_RI_NOT_FOUND,
            err_detail=ri_nm,
            info_success=INFO_RI_END_ADDRESS,
            info_detail=ri_nm,
        )

    # 동에서 끝나는 주소
    if addressCls == AddressCls.H4_END_ADDRESS:
        h4_nm = toks.get_text(TOKEN_H4)
        yield PossibleHash(
            hash=hash,
            addressCls=AddressCls.H4_END_ADDRESS,
            err_failed=ERR_DONG_NOT_FOUND,
            err_detail=h4_nm,
            info_success=INFO_H4_END_ADDRESS,
            info_detail=h4_nm,
        )

    # 시군구에서 끝나는 주소
    if addressCls == AddressCls.H23_END_ADDRESS:
        h23_nm = toks.get_text(TOKEN_H23)
        yield PossibleHash(
            hash=hash,
            addressCls=AddressCls.H23_END_ADDRESS,
            err_failed=ERR_H23_NOT_FOUND,
            err_detail=h23_nm,
            info_success=INFO_H23_END_ADDRESS,
            info_detail=h23_nm,
        )

    # 광역시도에서 끝나는 주소
    if addressCls == AddressCls.H1_END_ADDRESS:
        h1_nm = toks.get_text(TOKEN_H1)
        yield PossibleHash(
            hash=hash,
            addressCls=AddressCls.H1_END_ADDRESS,
            err_failed=ERR_H1_NOT_FOUND,
            err_detail=h1_nm,
            info_success=INFO_H1_END_ADDRESS,
            info_detail=h1_nm,
        )

    # 건물명과 건물동
    if toks.hasTypes(TOKEN_BLD_DONG):
        bld_dong = toks.get(toks.index(TOKEN_BLD_DONG)).val
        if addressCls == AddressCls.JIBUN_ADDRESS:
            # Replace the $SELECTION_PLACEHOLDER$ code with:
            yield PossibleHash(
                hash=jibunAddress.hash(toks),
                addressCls=AddressCls.JIBUN_ADDRESS,
                err_failed=ERR_BLD_DONG_NOT_FOUND,
                err_detail=bld_dong,
                info_success=INFO_JIBUN_ADDRESS,
                info_detail=f"지번 주소의 {bld_dong}",
            )
        elif addressCls == AddressCls.BLD_ADDRESS:
            yield PossibleHash(
                hash=bldAddress.hash(toks),
                addressCls=AddressCls.BLD_ADDRESS,
                err_failed=ERR_BLD_DONG_NOT_FOUND,
                err_detail=bld_dong,
                info_success=INFO_BLD_ADDRESS,
                info_detail=f"건물 주소의 {bld_dong}",
            )
        elif addressCls == AddressCls.ROAD_ADDRESS:
            yield PossibleHash(
                hash=roadAddress.hash(toks),
                addressCls=AddressCls.ROAD_ADDRESS,
                err_failed=ERR_BLD_DONG_NOT_FOUND,
                err_detail=bld_dong,
                info_success=INFO_ROAD_ADDRESS,
                info_detail=f"도로명 주소의 {bld_dong}",
            )

    # 건물동 제외하고 건물명까지
    if toks.hasTypes(TOKEN_BLD):
        bld_nm = toks.get(toks.index(TOKEN_BLD)).val
        if addressCls == AddressCls.JIBUN_ADDRESS:
            yield PossibleHash(
                hash=jibunAddress.hash(toks, end_with=TOKEN_BLD),
                addressCls=AddressCls.JIBUN_ADDRESS,
                err_failed=ERR_BLD_NM_NOT_FOUND,
                err_detail=bld_nm,
                info_success=INFO_JIBUN_ADDRESS,
                info_detail=f"지번 주소의 {bld_nm} (건물동 제외)",
            )

        elif addressCls == AddressCls.BLD_ADDRESS:
            yield PossibleHash(
                hash=bldAddress.hash(toks, end_with=TOKEN_BLD),
                addressCls=AddressCls.BLD_ADDRESS,
                err_failed=ERR_BLD_NM_NOT_FOUND,
                err_detail=bld_nm,
                info_success=INFO_BLD_ADDRESS,
                info_detail=f"건물 주소 {bld_nm} (건물동 제외)",
            )

        elif addressCls == AddressCls.ROAD_ADDRESS:
            yield PossibleHash(
                hash=roadAddress.hash(toks, end_with=TOKEN_BLD),
                addressCls=AddressCls.ROAD_ADDRESS,
                err_failed=ERR_BLD_NM_NOT_FOUND,
                err_detail=bld_nm,
                info_success=INFO_ROAD_ADDRESS,
                info_detail=f"도로명 주소의 {bld_nm} (건물동 제외)",
            )

    if False:
        # 리 빼고 다시 시도
        possible_hashs_without_ri(
            toks,
            hash,
            hasher,
            addressCls,
            jibunAddress,
            bldAddress,
            roadAddress,
            hsimplifier,
            hcodeMatcher,
        )

    # 건물명 제외하고 검색
    if addressCls == AddressCls.JIBUN_ADDRESS:
        bld_nm = toks.get_text(TOKEN_BLD)
        yield PossibleHash(
            hash=jibunAddress.hash(toks, end_with=TOKEN_BNG),
            addressCls=AddressCls.JIBUN_ADDRESS,
            err_failed=ERR_JIBUN_HASH,
            info_success=INFO_JIBUN_ADDRESS,
            info_detail=f"건물명 {bld_nm} 제외" if bld_nm else "",
        )

    elif addressCls == AddressCls.ROAD_ADDRESS:
        bld_nm = toks.get_text(TOKEN_BLD)
        yield PossibleHash(
            hash=roadAddress.hash(toks, end_with=TOKEN_BLDNO),
            addressCls=AddressCls.ROAD_ADDRESS,
            err_failed=ERR_ROAD_HASH,
            err_detail=hash,
            info_success=INFO_ROAD_ADDRESS,
            info_detail=(f"건물명 {bld_nm} 제외" if bld_nm else ""),
        )

    # 인근 지번 주소
    if addressCls == AddressCls.JIBUN_ADDRESS:
        hashs = get_near_jibun_hashs(hash)
        for h, bng in hashs:
            yield PossibleHash(
                hash=h,
                addressCls=AddressCls.JIBUN_ADDRESS,
                err_failed=ERR_NEAR_JIBUN_NOT_FOUND,
                err_detail=bng,
                info_success=INFO_NEAR_JIBUN_FOUND,
                info_detail=bng,
            )
    # 인근 도로명 주소
    elif addressCls == AddressCls.ROAD_ADDRESS:
        hashs = get_near_road_bld_hashs(hash)
        for h, bld_no in hashs:
            yield PossibleHash(
                hash=h,
                addressCls=AddressCls.ROAD_ADDRESS,
                err_failed=ERR_NEAR_ROAD_BLD_NOT_FOUND,
                err_detail=bld_no,
                info_success=INFO_NEAR_ROAD_BLD_FOUND,
                info_detail=bld_no,
                prev_errs={ERR_ROAD_NOT_UNIQUE_H23_NM},
            )

    combinations = address_combination(toks, addressCls, hasher=hasher)
    for h in combinations:
        yield h

    # # 리 빼고 인근 주소
    # if toks.hasTypes(TOKEN_RI):
    #     addr_without_ri = toks_without_ri.to_address()
    #     hash_without_ri, _, _, err = addressHash(addr_without_ri)
    #     if addressCls == AddressCls.JIBUN_ADDRESS:
    #         hashs = get_near_jibun_hashs(hash_without_ri)
    #         for h in hashs:
    #             yield({"hash": h, "addressCls": JUN_ADDRESS})
    #     elif addressCls == AddressCls.ROAD_ADDRESS:
    #         hashs = get_near_road_bld_hashs(hash_without_ri)
    #         for h in hashs:
    #             yield({"hash": h, "addressCls": AddressCls.ROAD_ADDRESS})

    # # 지번주소의 h23 빼고 인근 주소
    # if (
    #     addressCls == AddressCls.JIBUN_ADDRESS
    #     and toks.hasTypes(TOKEN_H23)
    #     and toks.hasTypes(TOKEN_H4)
    # ):
    #     yield(
    #         {
    #             "hash": jibunAddress.hash(toks, end_with=TOKEN_BNG),
    #             "addressCls": JUN_ADDRESS,
    #             "err_failed": ERR_NEAR_JIBUN_NOT_FOUND,
    #         }
    #     )

    # 도로명주소의 동 빼고 인근 주소               전남 무안군 오룡길 1 전라남도청 본관
    if addressCls == AddressCls.ROAD_ADDRESS and toks.hasTypes(TOKEN_H4):
        dong_ri = " ".join(
            [toks.get(toks.index(TOKEN_H4)).val, toks.get(toks.index(TOKEN_RI)).val]
        )
        yield PossibleHash(
            hash=roadAddress.hash(
                toks, end_with=TOKEN_BLDNO, ignore=[TOKEN_H4, TOKEN_RI]
            ),
            addressCls=AddressCls.ROAD_ADDRESS,
            err_failed=ERR_NEAR_ROAD_BLD_NOT_FOUND,
            err_detail=dong_ri,
            info_success=INFO_NEAR_ROAD_BLD_FOUND,
            info_detail=h,
        )

    # 도로명 이하 주소               오룡길 1 전라남도청 본관, 오룡길 1 전라남도청, 오룡길 1
    if toks.hasTypes(TOKEN_ROAD) and toks.hasTypes(TOKEN_BLDNO):
        yield PossibleHash(
            hash=roadAddress.hash(toks, start_with=TOKEN_ROAD),
            addressCls=AddressCls.ROAD_ADDRESS,
            err_failed=ERR_REGION_NOT_FOUND,
            err_detail=roadAddress.hash(toks, start_with=TOKEN_ROAD),
            info_success=INFO_ROAD_ADDRESS,
            info_detail=toks.get_text_after(TOKEN_ROAD, count=2),
        )

    # 리 이하 주소               경기도 김포시 신곡리 532번지 66호 1층 1호
    if toks.hasTypes(TOKEN_RI) and toks.hasTypes(TOKEN_BNG):
        yield PossibleHash(
            hash=jibunAddress.hash(toks, start_with=TOKEN_RI),
            addressCls=AddressCls.JIBUN_ADDRESS,
            err_failed=ERR_REGION_NOT_FOUND,
            err_detail=jibunAddress.hash(toks, start_with=TOKEN_RI),
            info_success=INFO_JIBUN_ADDRESS,
            info_detail=toks.get_text_after(TOKEN_RI, count=2),
        )

    # 대표주소
    # 길대표
    if toks.hasTypes(TOKEN_ROAD):
        road_nm = toks.get(toks.index(TOKEN_ROAD)).val
        yield PossibleHash(
            hash=roadAddress.hash(toks, end_with=TOKEN_ROAD),
            addressCls=AddressCls.ROAD_END_ADDRESS,
            pos_cd_filter={ROAD_ADDR_FILTER},
            err_failed=ERR_ROAD_NOT_FOUND,
            err_detail=f"도로명을 찾을 수 없음: {road_nm}",
            info_success=INFO_ROAD_REPRESENTATIVE_ADDR,
            info_detail=road_nm,
        )

    # 리빼고 길대표
    if toks.hasTypes(TOKEN_ROAD) and toks.hasTypes(TOKEN_RI):
        road_nm = toks.get(toks.index(TOKEN_ROAD)).val
        ri_nm = toks.get(toks.index(TOKEN_RI)).val
        yield PossibleHash(
            hash=roadAddress.hash(toks, end_with=TOKEN_ROAD, ignore=[TOKEN_RI]),
            addressCls=AddressCls.ROAD_END_ADDRESS,
            pos_cd_filter={ROAD_ADDR_FILTER},
            err_failed=ERR_ROAD_NOT_FOUND,
            err_detail=f"길 이름으로 끝나는 주소: {road_nm}",
            info_success=INFO_ROAD_REPRESENTATIVE_ADDR,
            info_detail=f"{road_nm} ({ri_nm} 제외)",
        )
    # 리대표
    if toks.hasTypes(TOKEN_RI):
        ri_nm = toks.get(toks.index(TOKEN_RI)).val
        yield PossibleHash(
            hash=jibunAddress.hash(toks, end_with=TOKEN_RI),
            addressCls=AddressCls.RI_END_ADDRESS,
            pos_cd_filter={RI_ADDR_FILTER},
            err_failed=ERR_RI_NOT_FOUND,
            err_detail=f"리 이름을 찾을 수 없음: {ri_nm}",
            info_success=INFO_RI_REPRESENTATIVE_ADDR,
            info_detail=f"{ri_nm} 다음 찾을 수 없음: {toks.get_text_after(TOKEN_RI, count=2)}...",
        )

    # 동대표
    if toks.hasTypes(TOKEN_H4):
        h4_nm = toks.get(toks.index(TOKEN_H4)).val
        yield PossibleHash(
            hash=jibunAddress.hash(toks, end_with=TOKEN_H4),
            addressCls=AddressCls.H4_END_ADDRESS,
            pos_cd_filter={HD_ADDR, LD_ADDR_FILTER},
            err_failed=ERR_DONG_NOT_FOUND,
            err_detail=h4_nm,
            info_success=INFO_HD_REPRESENTATIVE_ADDR,
            info_detail=f"{h4_nm} 다음 찾을 수 없음: {toks.get_text_after(TOKEN_H4, count=2)}...",
        )

    # 시군구대표
    if toks.hasTypes(TOKEN_H23):
        h23_nm = toks.get(toks.index(TOKEN_H23)).val
        yield PossibleHash(
            hash=jibunAddress.hash(toks, end_with=TOKEN_H23),
            addressCls=AddressCls.H23_END_ADDRESS,
            pos_cd_filter={H23_ADDR_FILTER},
            err_failed=ERR_H23_NOT_FOUND,
            err_detail=h23_nm,
            info_success=INFO_H23_REPRESENTATIVE_ADDR,
            info_detail=f"{h23_nm} 다음 찾을 수 없음: {toks.get_text_after(TOKEN_H23, count=2)}...",
        )

    # 광역시도 대표
    if toks.hasTypes(TOKEN_H1):
        h1_nm = toks.get(toks.index(TOKEN_H1)).val
        yield PossibleHash(
            hash=hsimplifier.h1Hash(toks.get(0).val),
            addressCls=AddressCls.H1_END_ADDRESS,
            pos_cd_filter={H1_ADDR_FILTER},
            err_failed=ERR_H1_NOT_FOUND,
            err_detail=h1_nm,
            info_success=INFO_H1_REPRESENTATIVE_ADDR,
            info_detail=f"{h1_nm} 다음 찾을 수 없음: {toks.get_text_after(TOKEN_H1, count=2)}...",
        )


def get_near_jibun_hashs(hash):
    """
    주어진 지번 주소 해시를 사용하여 인근 지번 주소 해시를 반환합니다.
    hash: 오산_원동_123-4
    ex) 123 -> [120, 120, 123, ... 129, 123-1, 123-2, ... 123-9]
    ex) 123-5 -> [123, 123-1, 123-2, ... 123-9]

    Args:
        hash (str): 지번 주소의 해시 값.

    Returns:
        list: 인근 지번 주소 해시 리스트.
    """

    near_jibun_hashs = []
    hash_head = "_".join(hash.split("_")[:-1])  # hash의 번지 앞 부분 ("오산_원동")
    bng = hash.split("_")[-1]  # 지번 주소의 기본 부분 (예: 123)
    san = ""
    bng1 = bng.split("-")[0]  # 지번 주소의 기본 부분 (예: 123)
    if bng1[0] == "산":  # 산이 있는 경우
        san = "산"  # 산 다음 부분 (예: 123에서 23)
        bng1 = bng1[1:]  # 산 다음 부분 (예: 23)
    bng2 = bng.split("-")[1] if "-" in bng else None  # 지번 주소의 세부 부분 (예: 5)
    if bng1.isnumeric():
        bng1 = int(bng1)
    else:
        return near_jibun_hashs  # 숫자가 아닌 경우 빈 리스트 반환
    if bng2.isnumeric():
        bng2 = int(bng2)
    else:
        return near_jibun_hashs  # 숫자가 아닌 경우 빈 리스트 반환

    if bng2:
        # 부번지 있는 경우. 1~9 범위로 가까운 순으로 추가
        for i in range(1, 5):
            if i != bng2 and bng2 + i < 10:  # 현재 부번지 제외
                near_jibun_hashs.append(
                    (f"{hash_head}_{san}{bng1}-{bng2+i}", f"{san}{bng1}-{bng2+i}")
                )
            if i != bng2 and bng2 - i > 0:  # 현재 부번지 제외
                near_jibun_hashs.append(
                    (f"{hash_head}_{san}{bng1}-{bng2-i}", f"{san}{bng1}-{bng2-i}")
                )

        # 부번지 제거한 주번지 추가
        near_jibun_hashs.append((f"{hash_head}_{san}{bng1}-0", f"{san}{bng1}-0"))
    else:
        # 부번지 없는 경우
        # 부번지 범위 추가 1~9
        for i in range(1, 10):
            near_jibun_hashs.append(
                (f"{hash_head}_{san}{bng1}-{i}", f"{san}{bng1}-{i}")
            )

        # 주번지 범위 추가. 1~9 범위로 가까운 순으로 추가
        for i in range(1, 5):
            if i != bng1 and bng1 + i < 10:  # 현재 번지 제외
                near_jibun_hashs.append(
                    (f"{hash_head}_{san}{bng1+i}-0", f"{san}{bng1+i}-0")
                )
            if i != bng1 and bng1 - i > 0:  # 현재 번지 제외
                near_jibun_hashs.append(
                    (f"{hash_head}_{san}{bng1-i}-0", f"{san}{bng1-i}-0")
                )

    return near_jibun_hashs


def get_near_road_bld_hashs(hash):
    """
    주어진 도로명 주소 해시를 사용하여 인근 도로명 주소 해시를 반환합니다.
    hash: 오산_원동_123

    ex) 123 -> [121, 122, 124, 125]
    ex) 123-5 -> [123-1, 123-2, ... 123-9, 122, 124]

    Args:
        hash (str): 도로명 주소의 해시 값.

    Returns:
        list: 인근 도로명 주소 해시 리스트.
    """

    near_road_bld_hashs = []
    hash_head = "_".join(hash.split("_")[:-1])  # hash의 건번 앞 부분 ("오산_원동")
    bld = hash.split("_")[-1]  # 건번 주소의 기본 부분 (예: 123)
    bld1 = bld.split("-")[0]  # 건번 주소의 기본 부분 (예: 123)
    bld2 = bld.split("-")[1] if "-" in bld else None  # 건번 주소의 세부 부분 (예: 5)
    if bld1.isnumeric():
        bld1 = int(bld1)
    else:
        return near_road_bld_hashs  # 숫자가 아닌 경우 빈 리스트 반환
    if bld2.isnumeric():
        bld2 = int(bld2)
    else:
        return near_road_bld_hashs  # 숫자가 아닌 경우 빈 리스트 반환

    # bld1이 홀수인지 짝수인지 판단
    is_bld1_even = bld1 % 2 == 0

    if bld2:
        # 부건번 있는 경우. += 10개 범위로 가까운 순으로 추가
        for i in range(1, 11):
            near_road_bld_hashs.append(
                (f"{hash_head}_{bld1}-{bld2+i}", f"{bld1}-{bld2+i}")
            )

            if bld2 - i > 0:  # 현재 부건번 제외
                near_road_bld_hashs.append(
                    (f"{hash_head}_{bld1}-{bld2-i}", f"{bld1}-{bld2-i}")
                )

        # 주 건번 추가
        near_road_bld_hashs.append((f"{hash_head}_{bld1}-0", f"{bld1}-0"))
    else:
        # 부건번 없는 경우
        # 부건번 범위 추가 1~9
        for i in range(1, 10):
            near_road_bld_hashs.append((f"{hash_head}_{bld1}-{i}", f"{bld1}-{i}"))

        # 주건번 범위 추가. 1~9 범위로 가까운 순으로 추가
        for i in range(1, 9):
            if (bld1 + i) % 2 == (
                0 if is_bld1_even else 1
            ):  # 현재 건번과 홀짝 같은 것만 추가
                near_road_bld_hashs.append((f"{hash_head}_{bld1+i}-0", f"{bld1+i}-0"))
            if bld1 - i > 0 and (bld1 - i) % 2 == (
                0 if is_bld1_even else 1
            ):  # 현재 건번과 홀짝 같은 것만 추가
                near_road_bld_hashs.append((f"{hash_head}_{bld1-i}-0", f"{bld1-i}-0"))

    return near_road_bld_hashs


def address_combination(toks0: Tokens, addressCls0: str = None, hasher: Hasher = None):
    """
    주소 조합을 시도하여 가장 유사한 주소를 반환합니다.

    Args:
        toks (Tokens): 주소를 나타내는 토큰 리스트.
        addressCls (str): 주소 클래스 (지번 주소).

    Returns:
        tuple: 가장 유사한 주소와 주소 클래스.
            유사한 주소가 없거나 오류가 발생한 경우 None과 NOT_ADDRESS를 반환합니다.
    """

    def token_removed_address(toks, token_type):
        """
        주어진 토큰에서 특정 타입의 토큰을 제거한 주소를 반환합니다.
        """
        tmp_toks: Tokens = toks0.copy()
        index = tmp_toks.index(token_type)
        tmp_toks.delete(index)
        return tmp_toks.to_address()

    combinations = []

    # ("h23_nm", "ld_nm", "ri_nm", "san", "bng1", "bng2", "bld1", "bld2"),
    # ("h23_nm", "ld_nm", "ri_nm", "road_nm", "undgrnd_yn", "bld1", "bld2")

    # # 리 제거한 주소. 다른 리에 같은 지번이 있을 수 있다.
    # if toks0.hasTypes(TOKEN_RI):
    #     address = token_removed_address(toks0, TOKEN_RI)
    #     hash, toks, addressCls, err = addressHash(address)
    #     if hash and addressCls == addressCls0:
    #         combinations.append(
    #             {"hash": hash, "err": ERR_NAME_RI, "addressCls": addressCls}
    #         )

    # 동 제거한 주소
    if (
        toks0.hasTypes(TOKEN_H4)
        and toks0.hasTypes(TOKEN_H23)
        and addressCls0 == AddressCls.ROAD_ADDRESS
    ):
        address = token_removed_address(toks0, TOKEN_H4)
        hash, toks, addressCls, err = hasher.addressHash(address)
        if hash and addressCls == addressCls0:
            combinations.append(
                PossibleHash(
                    hash=hash,
                    addressCls=addressCls,
                    pos_cd_filter={ROAD_ADDR_FILTER},
                    err_failed=ERR_NAME_H4,
                    err_detail=toks0.get(toks0.index(TOKEN_H4)).val,
                    info_success=INFO_ROAD_ADDRESS,
                    info_detail=f"동 이름 오류: {toks0.get_text(TOKEN_H4)}",
                )
            )

    # 시군구 제거한 주소
    if (
        toks0.hasTypes(TOKEN_H23)
        and toks0.hasTypes(TOKEN_H4)
        and toks0.hasTypes(TOKEN_H1)  # 다른 광역시도로 맵핑 방지
    ):
        address = token_removed_address(toks0, TOKEN_H23)
        hash, toks, addressCls, err = hasher.addressHash(address)
        if hash and addressCls == addressCls0:
            if addressCls == AddressCls.ROAD_END_ADDRESS and len(toks0) < 3:
                # 시군구 없이 도로명만 남기면 다른 시군구의 도로와 매칭 될 수 있으므로 제외
                pass
            else:
                combinations.append(
                    PossibleHash(
                        hash=hash,
                        addressCls=addressCls,
                        err_failed=ERR_NAME_H23,
                        err_detail=toks0.get(toks0.index(TOKEN_H23)).val,
                        info_success=INFO_ROAD_END_ADDRESS,
                        info_detail=f"시군구 이름 오류: {toks0.get_text(TOKEN_H23)}",
                    )
                )

    return combinations


def address_hash_cache(maxsize=1024):
    """
    addressHash 메서드를 위한 캐싱 데코레이터

    Args:
        maxsize (int): 최대 캐시 항목 수
    """
    from collections import OrderedDict
    import threading

    def decorator(func):
        cache = OrderedDict()
        lock = threading.RLock()  # 재진입 가능한 락 사용

        def wrapper(self, addr):
            if config.USE_HASH_CACHE is False:
                # 캐시 사용 안 함
                return func(self, addr)

            # 빈 문자열이나 None 값은 캐싱하지 않음
            if not addr:
                return func(self, addr)

            # 캐시에서 결과 반환
            with lock:
                if addr in cache:
                    # LRU 동작을 위해 항목을 가장 최근 위치로 이동
                    cache.move_to_end(addr)
                    return cache[addr]

            # 새 결과 계산 (락 외부에서 실행하여 성능 향상)
            result = func(self, addr)

            # 캐시 업데이트 (쓰기 락)
            with lock:
                # 다시 한 번 확인 (다른 스레드가 이미 추가했을 수 있음)
                if addr not in cache:
                    cache[addr] = result

                    # 캐시 크기 제한 관리
                    if len(cache) > maxsize:
                        cache.popitem(last=False)  # 가장 오래된 항목 제거
                else:
                    # 이미 다른 스레드가 추가한 경우, 최신 위치로 이동
                    cache.move_to_end(addr)

            return result

        return wrapper

    return decorator


@address_hash_cache(maxsize=1024)
def addressHash(self, addr):
    """
    주어진 주소 문자열을 해시하고, 토큰화된 주소, 주소 유형, 오류 메시지를 반환합니다.

    Args:
        addr (str): 해시할 주소 문자열.

    Returns:
        tuple:
            - hash (str): 주소의 해시 값.
            - toks (list): 토큰화된 주소 리스트.
            - addressCls (int): 주소 유형을 나타내는 상수.
            - errmsg (str): 오류 메시지.

    오류 유형:
        - "NOT_ADDRESS ERROR": 주소로 인식되지 않는 경우.
        - "JIBUN HASH ERROR": 지번 주소 해시 오류.
        - "BLD HASH ERROR": 건물 주소 해시 오류.
        - "ROAD HASH ERROR": 도로명 주소 해시 오류.
        - "UNRECOGNIZABLE_ADDRESS ERROR": 인식할 수 없는 주소 오류.
        - "RUNTIME ERROR": 실행 중 발생한 오류.
    """
    hash = ""
    toks = []
    addressCls = AddressCls.NOT_ADDRESS
    err_msg = ""

    try:
        toks = self.tokenizer.tokenize(addr)
        addressCls = self.__classfy(toks)

        if addressCls == AddressCls.NOT_ADDRESS:
            hash = ""
            err_msg = ERR_NOT_ADDRESS
        elif addressCls == AddressCls.JIBUN_ADDRESS:
            hash = self.jibunAddress.hash(toks)
            if not hash or hash.endswith("_"):
                err_msg = ERR_JIBUN_HASH
        elif addressCls == AddressCls.BLD_ADDRESS:
            hash = self.bldAddress.hash(toks)
            if not hash:
                err_msg = ERR_BLD_HASH
        elif addressCls == AddressCls.ROAD_ADDRESS:
            hash = self.roadAddress.hash(toks)
            if not hash:
                err_msg = ERR_ROAD_HASH
        elif addressCls == AddressCls.RI_END_ADDRESS:
            hash = self.jibunAddress.hash(toks, end_with=TOKEN_RI)
            if not hash:
                err_msg = ERR_NOT_ADDRESS
        elif addressCls == AddressCls.ROAD_END_ADDRESS:
            hash = self.roadAddress.hash(toks, end_with=TOKEN_ROAD)
            if not hash:
                err_msg = ERR_NOT_ADDRESS
        elif addressCls == AddressCls.H4_END_ADDRESS:
            hash = self.jibunAddress.hash(toks, end_with=TOKEN_H4)
            if not hash:
                err_msg = ERR_NOT_ADDRESS
        elif addressCls == AddressCls.H23_END_ADDRESS:
            hash = self.jibunAddress.hash(toks, end_with=TOKEN_H23)
            if not hash:
                err_msg = ERR_NOT_ADDRESS
        elif addressCls == AddressCls.H1_END_ADDRESS:
            hash = self.hsimplifier.h1Hash(toks.get(0).val)
            if not hash:
                err_msg = ERR_NOT_ADDRESS

        elif addressCls == AddressCls.UNRECOGNIZABLE_ADDRESS:
            hash = ""
            err_msg = ERR_UNRECOGNIZABLE_ADDRESS

    except:
        hash = ""
        err_msg = ERR_RUNTIME

    return hash, toks, addressCls, err_msg


def possible_hashs_without_ri(
    toks: Tokens,
    hash: str,
    hasher: Hasher,
    addressCls,
    jibunAddress,
    bldAddress,
    roadAddress,
    hsimplifier,
    hcodeMatcher,
):
    toks_without_ri = toks.copy()
    if toks.hasTypes(TOKEN_RI) and toks.hasTypes(TOKEN_BLD):
        toks_without_ri.delete(toks_without_ri.index(TOKEN_RI))

        # 건물명과 건물동
        if toks_without_ri.hasTypes(TOKEN_BLD_DONG):
            if addressCls == AddressCls.JIBUN_ADDRESS:
                yield (
                    {
                        "hash": jibunAddress.hash(toks_without_ri),
                        "addressCls": AddressCls.JIBUN_ADDRESS,
                    }
                )
            elif addressCls == AddressCls.BLD_ADDRESS:
                yield (
                    {
                        "hash": bldAddress.hash(toks_without_ri),
                        "addressCls": AddressCls.BLD_ADDRESS,
                    }
                )
            elif addressCls == AddressCls.ROAD_ADDRESS:
                yield (
                    {
                        "hash": roadAddress.hash(toks_without_ri),
                        "addressCls": AddressCls.ROAD_ADDRESS,
                    }
                )

        # 건물동 제외하고 건물명까지
        if toks_without_ri.hasTypes(TOKEN_BLD):
            if addressCls == AddressCls.JIBUN_ADDRESS:
                yield (
                    {
                        "hash": jibunAddress.hash(toks_without_ri, end_with=TOKEN_BLD),
                        "addressCls": AddressCls.JIBUN_ADDRESS,
                    }
                )
            elif addressCls == AddressCls.BLD_ADDRESS:
                yield (
                    {
                        "hash": bldAddress.hash(toks_without_ri, end_with=TOKEN_BLD),
                        "addressCls": AddressCls.BLD_ADDRESS,
                    }
                )
            elif addressCls == AddressCls.ROAD_ADDRESS:
                yield (
                    {
                        "hash": roadAddress.hash(toks_without_ri, end_with=TOKEN_BLD),
                        "addressCls": AddressCls.ROAD_ADDRESS,
                    }
                )

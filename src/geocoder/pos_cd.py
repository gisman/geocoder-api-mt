H1_ADDR = "광역시도 대표주소"
H23_ADDR = "시군구 대표주소"
HD_ADDR = "행정동 대표주소"
LD_ADDR = "법정동 대표주소"
RI_ADDR = "리 대표주소"
ROAD_ADDR = "길이름 대표주소"

H1_ADDR_FILTER = "H1_ADDR"
H23_ADDR_FILTER = "H23_ADDR"
HD_ADDR_FILTER = "HD_ADDR"
LD_ADDR_FILTER = "LD_ADDR"
RI_ADDR_FILTER = "RI_ADDR"
ROAD_ADDR_FILTER = "ROAD_ADDR"

# 대표주소 목록
REPRESENTATIVE_ADDRS = [
    H1_ADDR_FILTER,
    H23_ADDR_FILTER,
    HD_ADDR_FILTER,
    LD_ADDR_FILTER,
    RI_ADDR_FILTER,
    ROAD_ADDR_FILTER,
]

JIBUN = "지번 주소"
ROAD = "도로명 주소"
BLD = "건물명 주소"

NEAR_JIBUN = "인근 지번 주소"
NEAR_ROAD_BLD = "인근 도로명 주소"
SIMILAR_BUILDING_NAME = "유사한 건물명 주소"

POS_CD_SUCCESS = [
    JIBUN,
    ROAD,
    BLD,
    NEAR_JIBUN,
    NEAR_ROAD_BLD,
    SIMILAR_BUILDING_NAME,
]


def filter_to_pos_cd(pos_cd):
    """
    Convert filter type to POS_CD type.

    Args:
        pos_cd (str): The filter type to convert.

    Returns:
        str: The corresponding POS_CD type.
    """
    filter_to_pos_cd_map = {
        H1_ADDR_FILTER: H1_ADDR,
        H23_ADDR_FILTER: H23_ADDR,
        HD_ADDR_FILTER: HD_ADDR,
        LD_ADDR_FILTER: LD_ADDR,
        RI_ADDR_FILTER: RI_ADDR,
        ROAD_ADDR_FILTER: ROAD_ADDR,
    }
    return filter_to_pos_cd_map.get(pos_cd, pos_cd)

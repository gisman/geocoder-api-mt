from enum import Enum
import src.geocoder.tokens as tokens
import src.geocoder.pos_cd as pos_cd


class AddressCls(Enum):
    NOT_ADDRESS = "NOT_ADDRESS"
    JIBUN_ADDRESS = "JIBUN_ADDRESS"
    BLD_ADDRESS = "BLD_ADDRESS"
    ROAD_ADDRESS = "ROAD_ADDRESS"

    ROAD_END_ADDRESS = "ROAD_END_ADDRESS"
    RI_END_ADDRESS = "RI_END_ADDRESS"
    H4_END_ADDRESS = "H4_END_ADDRESS"
    H23_END_ADDRESS = "H23_END_ADDRESS"
    H1_END_ADDRESS = "H1_END_ADDRESS"
    UNRECOGNIZABLE_ADDRESS = "UNRECOGNIZABLE_ADDRESS"

    # 대표 주소 검사 순서
    BASE_ADDRESS_ORDER = [
        ROAD_END_ADDRESS,
        RI_END_ADDRESS,
        H4_END_ADDRESS,
        H23_END_ADDRESS,
        H1_END_ADDRESS,
    ]

    END_WITH_TOKEN_INFO = {
        ROAD_END_ADDRESS: {
            "end_with": tokens.TOKEN_ROAD,
            "pos_cd_filter": [pos_cd.ROAD_ADDR_FILTER],
        },
        RI_END_ADDRESS: {
            "end_with": tokens.TOKEN_RI,
            "pos_cd_filter": [pos_cd.RI_ADDR_FILTER],
        },
        H4_END_ADDRESS: {
            "end_with": tokens.TOKEN_H4,
            "pos_cd_filter": [pos_cd.HD_ADDR, pos_cd.LD_ADDR_FILTER],
        },
        H23_END_ADDRESS: {
            "end_with": tokens.TOKEN_H23,
            "pos_cd_filter": [pos_cd.H23_ADDR_FILTER],
        },
        H1_END_ADDRESS: {
            "end_with": tokens.TOKEN_H1,
            "pos_cd_filter": [pos_cd.H1_ADDR_FILTER],
        },
    }

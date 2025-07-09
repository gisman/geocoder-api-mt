import re
from ..Tokenizer import Tokenizer
from ..tokens import *
from ..util.BldSimplifier import BldSimplifier
from ..util.HSimplifier import HSimplifier
from ..util.RoadSimplifier import RoadSimplifier


class BldAddress:
    tokenizer = Tokenizer()
    bldSimplifier = BldSimplifier()
    hSimplifier = HSimplifier()
    roadSimplifier = RoadSimplifier()

    def hash(self, toks, end_with=TOKEN_BLD):
        """
        주어진 토큰 리스트를 해시 문자열로 변환합니다.

        Args:
            toks (list): 토큰 리스트

        Returns:
            str: 해시 문자열
        """
        # 건물명 단순화
        # 추가 정보 merge [TODO]

        h23 = ""
        h4 = ""
        ri = ""
        road = ""
        bld = ""
        road_pos = -1

        length = len(toks)
        for n in range(length):
            tkn = toks.get(n)

            if tkn.t == TOKEN_H23 and h23 == "":
                h23 = self.hSimplifier.h23Hash(tkn.val)
            elif tkn.t == TOKEN_H4 and h4 == "":
                h4 = self.hSimplifier.h4Hash(tkn.val)
            elif tkn.t == TOKEN_RI and ri == "":
                ri = tkn.val
            elif tkn.t == TOKEN_ROAD and road == "":
                road = self.roadSimplifier.roadHash(tkn.val)
                road_pos = n
            elif tkn.t == TOKEN_BLD and bld == "":
                bld = tkn.val
                # if self.bldSimplifier.is_general_name(bld):
                #     bld = ""
                bldPos = n
            else:
                continue

            if tkn.t == end_with:
                break

        hash = ""

        startNames = []
        for n in range(bldPos):
            startNames.append(toks[n])

        bld = self.bld_hash(bld, startNames)

        # if bld != "":
        #     if bld in ["주민센터", "동사무소"] and h4:
        #         hash = "{}_{}_{}".format(h23, h4, bld)
        #     elif road:
        #         hash = "{}_{}_{}".format(h23, road, bld)
        #     elif h4:
        #         hash = "{}_{}_{}".format(h23, h4, bld)
        #     else:
        #         hash = "{}_{}".format(h23, bld)

        # h4 포함 주소가 반영되지 않는 문제 해결. 2025.07.02
        hash = "{}_{}_{}_{}_{}".format(h23, h4, ri, road, bld)
        return hash.replace("___", "_").replace("__", "_").strip("_")

    def bld_hash(self, bld, startNames):
        # bld2 = self.bldSimplifier.stripStartName(startNames, bld)
        bld2 = self.bldSimplifier.simplifyBldName(bld)

        if bld2:
            bld = bld2
        else:
            bld = self.bldSimplifier.simplifyBldName(bld)
        return bld

    def __bldHash(self, toks, pos):
        """
        주어진 위치의 토큰을 해시로 변환합니다.

        Args:
            toks (list): 토큰 리스트
            pos (int): 토큰 위치

        Returns:
            str: 해시 문자열
        """
        return toks[pos]  # TODO

# python 3
# -*- coding: utf-8 -*-

import json
import logging
from difflib import SequenceMatcher
import threading

import src.config as config
from src.geocoder.address_cls import AddressCls
from src.geocoder.hasher import Hasher
from src.geocoder.possible_hash import PossibleHash, possible_hashs

# from .db.rocksdb import RocksDbGeocode
from .db.gimi9_rocks import Gimi9RocksDB

# from .db.aimrocks import AimrocksDbGeocode
from .hash.BldAddress import BldAddress
from .hash.JibunAddress import JibunAddress
from .hash.RoadAddress import RoadAddress
from .Tokenizer import Tokenizer
from .tokens import *
from .util.hcodematcher import HCodeMatcher
from .util.HSimplifier import HSimplifier
from .errs import *
from .pos_cd import *

# logging.basicConfig(
#     level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )
logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
console_handler.setLevel(config.LOG_LEVEL)
formatter = logging.Formatter("%(levelname)s:   %(message)s")
console_handler.setFormatter(formatter)
logger.handlers = [console_handler]
logger.setLevel(config.LOG_LEVEL)

IMPORTANT_ERROR = True
NOT_IMPORTANT_ERROR = False


class Geocoder:
    """
    Geocoder 클래스는 주소를 해시하고 검색하는 기능을 제공합니다.

    속성:
        tokenizer (Tokenizer): 주소를 토큰화하는 객체.
        jibunAddress (JibunAddress): 지번 주소 해시 객체.
        bldAddress (BldAddress): 건물 주소 해시 객체.
        roadAddress (RoadAddress): 도로명 주소 해시 객체.
        hsimplifier (HSimplifier): 주소 단순화 객체.
        hcodeMatcher (HCodeMatcher): 행정 코드 매칭 객체.

    메서드:
        __init__(self, db):
            Geocoder 객체를 초기화합니다.

        __classfy(self, toks):
            주소 토큰을 분류하여 주소 유형을 반환합니다.

        __bldAddressHash(self, toks):
            건물 주소 해시를 반환합니다.

        __jibunAddressHash(self, toks):
            지번 주소 해시를 반환합니다.

        __roadAddressHash(self, toks):
            도로명 주소 해시를 반환합니다.

        addressHash(self, addr):
            주소를 해시하고 관련 정보를 반환합니다.

        search(self, addr):
            주소를 검색하고 결과를 반환합니다.

        get_h1(self, val):
            주소의 h1 코드를 반환합니다.

        get_h2(self, val):
            주소의 h2 코드를 반환합니다.

        most_similar_address(self, toks, key):
            가장 유사한 주소를 검색하여 반환합니다.
    """

    tokenizer = Tokenizer()
    jibunAddress = JibunAddress()
    bldAddress = BldAddress()
    roadAddress = RoadAddress()
    hsimplifier = HSimplifier()
    hcodeMatcher = HCodeMatcher()

    # # 대표 주소 검사 순서
    # BASE_ADDRESS_ORDER = [
    #     AddressCls.ROAD_END_ADDRESS,
    #     AddressCls.RI_END_ADDRESS,
    #     AddressCls.H4_END_ADDRESS,
    #     AddressCls.H23_END_ADDRESS,
    #     AddressCls.H1_END_ADDRESS,
    # ]

    # END_WITH_TOKEN_INFO = {
    #     AddressCls.ROAD_END_ADDRESS: {
    #         "end_with": TOKEN_ROAD,
    #         "pos_cd_filter": [ROAD_ADDR_FILTER],
    #     },
    #     AddressCls.RI_END_ADDRESS: {
    #         "end_with": TOKEN_RI,
    #         "pos_cd_filter": [RI_ADDR_FILTER],
    #     },
    #     AddressCls.H4_END_ADDRESS: {
    #         "end_with": TOKEN_H4,
    #         "pos_cd_filter": [HD_ADDR, LD_ADDR_FILTER],
    #     },
    #     AddressCls.H23_END_ADDRESS: {
    #         "end_with": TOKEN_H23,
    #         "pos_cd_filter": [H23_ADDR_FILTER],
    #     },
    #     AddressCls.H1_END_ADDRESS: {
    #         "end_with": TOKEN_H1,
    #         "pos_cd_filter": [H1_ADDR_FILTER],
    #     },
    # }

    def __init__(self):
        self._main_db = Gimi9RocksDB(config.GEOCODE_DB, read_only=config.READONLY)
        # self._secondary_db = []
        # for i in range(0, config.THREAD_POOL_SIZE):
        #     self._secondary_db.append(
        #         Gimi9RocksDB(
        #             config.GEOCODE_DB,
        #             read_only=True,
        #             open_secondary=True,
        #             secondary_path=f"{config.GEOCODE_DB}_{i}",
        #         )
        #     )

        # self._db_counter = 0

        # self.db = AimrocksDbGeocode(config.GEOCODE_DB)
        # self.db = RocksDbGeocode(config.GEOCODE_DB)

        self.hasher = Hasher(
            self.tokenizer,
            self.jibunAddress,
            self.bldAddress,
            self.roadAddress,
            self.hsimplifier,
            self.hcodeMatcher,
        )

    @property
    def db(self):
        return self._main_db

    def _get_db(self):
        """
        현재 스레드에 해당하는 데이터베이스를 반환합니다.
        스레드 풀을 사용하여 각 스레드에 대해 별도의 데이터베이스 인스턴스를 사용합니다.
        """

        return self._main_db
        # index = self._db_counter % (config.THREAD_POOL_SIZE + 1)
        # if index == 0:
        #     # 메인 DB를 사용
        #     db = self._main_db
        # else:
        #     # 스레드별 보조 DB를 사용
        #     db = self._secondary_db[self._db_counter % config.THREAD_POOL_SIZE]

        # self._db_counter += 1
        # # print(index)
        # return db

    # def open(self, db):
    #     self.db = db

    # iterator
    def __iter__(self):
        """
        Geocoder 객체를 반복 가능한 객체로 만들어주는 메서드입니다.
        """
        return self._main_db.__iter__()

    def search_start_with(self, key_pattern):
        """
        주어진 key_pattern을 사용하여 데이터베이스에서 LIKE 검색합니다.

        Args:
            toks (Tokens): 주소 토큰 객체.

        Returns:
            list: 검색된 결과의 리스트.
        """
        keys = []

        db = self._get_db()
        it = db.seek(key_pattern)
        key, v = db.next(it)
        while key:
            if key.startswith(key_pattern):
                keys.append(key)
            else:
                break
            key, v = self.db.next(it)

        return keys

    def _append_err_by_addressCls(self, err_list, addressCls):
        """Thread-safe version of append_err_by_addressCls"""
        # 기존 append_err_by_addressCls 로직을 err_list 파라미터를 받도록 수정
        if addressCls == AddressCls.NOT_ADDRESS:
            self._append_err(err_list, ERR_NOT_ADDRESS)
        elif addressCls == AddressCls.JIBUN_ADDRESS:
            self._append_err(err_list, INFO_JIBUN_ADDRESS)
        elif addressCls == AddressCls.BLD_ADDRESS:
            self._append_err(err_list, INFO_BLD_ADDRESS)
        elif addressCls == AddressCls.ROAD_ADDRESS:
            self._append_err(err_list, INFO_ROAD_ADDRESS)
        elif addressCls == AddressCls.RI_END_ADDRESS:
            self._append_err(err_list, INFO_RI_END_ADDRESS)
        elif addressCls == AddressCls.ROAD_END_ADDRESS:
            self._append_err(err_list, INFO_ROAD_END_ADDRESS)
        elif addressCls == AddressCls.H4_END_ADDRESS:
            self._append_err(err_list, INFO_H4_END_ADDRESS)
        elif addressCls == AddressCls.H23_END_ADDRESS:
            self._append_err(err_list, INFO_H23_END_ADDRESS)
        elif addressCls == AddressCls.H1_END_ADDRESS:
            self._append_err(err_list, INFO_H1_END_ADDRESS)

    def _append_err(self, err_list, err, msg=""):
        """Thread-safe version of append_err"""
        if err_list:
            err_list.append(err, msg)

    def _err_message(self, err_list, addressCls, pos_cd):
        """Thread-safe version of err_message"""
        # 기존 err_message 로직을 err_list 파라미터를 받도록 수정
        return err_list.last_detail_message() if err_list else ""

    def addressHash(self, addr):
        # builder 호환성을 위해 유지
        return self.hasher.addressHash(addr)

    def _fix_h23_nm(self, toks: Tokens):
        if len(toks) < 2:
            return False

        h23_pos = toks.index(TOKEN_H23)
        h1_nm = toks.get_text(TOKEN_H1)
        h1_cd = None
        if h1_nm:
            h1_nm = self.hsimplifier.h1Hash(h1_nm)
            h1_cd = self.hcodeMatcher.search_h1_cd(h1_nm)

        if h23_pos > -1:
            # h23이 있는 경우, h23을 교정
            h23_nm = toks.get(h23_pos).val

            fixed_h23_nm = self.hcodeMatcher.search_most_likely_h23_nm(h23_nm, h1_cd)
            if not fixed_h23_nm:
                # 시군구명 삭제
                logger.debug(f"유효하지 않은 시군구명: {h23_nm}")
                toks.delete(h23_pos)
                return True
            elif fixed_h23_nm and fixed_h23_nm != h23_nm:
                logger.debug(f"h23_nm 오타 교정: {h23_nm} -> {fixed_h23_nm}")
                toks.get(h23_pos).val = fixed_h23_nm
                return True

        return False

    def _apply_hint(self, address_hint_info, toks, address):
        if address_hint_info:
            if not toks.hasTypes(TOKEN_H1) and not toks.hasTypes(TOKEN_H23):
                # h1, h23이 없는 경우
                return f'{address_hint_info.get("h1", "")} {address_hint_info.get("h23", "")} {address}'.strip()
            elif not toks.hasTypes(TOKEN_H1):
                # h1이 없는 경우
                return f'{address_hint_info.get("h1", "")} {address}'.strip()
            elif not toks.hasTypes(TOKEN_H23):
                # h23이 없는 경우
                return f'{address} {address_hint_info.get("h23", "")}'.strip()
        return None

    def search(self, addr, address_hint_info={}):
        if not isinstance(addr, str):
            return None

        # 스레드별 로컬 변수로 변경하여 thread safety 확보
        err_list = ErrList()
        important_error = False
        addressCls = AddressCls.NOT_ADDRESS
        err: int = ERR_RUNTIME
        hash: str = None
        toks: Tokens = None
        addressCls: str = None

        address = addr.strip('"')
        if address == "":
            addressCls = AddressCls.NOT_ADDRESS
            return None

        hash, toks, addressCls, err = self.hasher.addressHash(address)
        if addr_with_hint := self._apply_hint(address_hint_info, toks, address):
            hash, toks, addressCls, err = self.hasher.addressHash(addr_with_hint)

        # self._append_err_by_addressCls(err_list, addressCls)

        logger.debug(f"address: {address}")
        logger.debug(f"hash: {hash}, addressCls: {addressCls}")
        logger.debug(f"toks: {toks}")
        if err:
            self._append_err(err_list, err)

            logger.debug(f"{err_list.last_detail_message(False)}, {addressCls}")
            return {
                "success": False,
                "errmsg": self._err_message(err_list, addressCls, ""),
            }
        toksString = self.tokenizer.getToksString(toks)

        # h23 오타 교정
        if self._fix_h23_nm(toks):
            address = toks.to_address()
            hash, toks, addressCls, err = self.hasher.addressHash(address)

        h1_nm = self.hsimplifier.h1Hash(toks.get_text(TOKEN_H1)) or None
        h23_nm = self.hsimplifier.h23Hash(toks.get_text(TOKEN_H23)) or None

        last_err_for_hash_condition = None
        hash_info: PossibleHash = None
        for hash_info in possible_hashs(
            toks,
            hash,
            self.hasher,
            addressCls,
        ):

            logger.debug(f"검색: [ {str(hash_info)} ]")
            # for hash_info in possible_hash_list:
            hash = hash_info.get_hash()

            # last_err 조건 검사
            if hash_info.pass_condition(last_err_for_hash_condition):
                continue

            val, important_error = self.most_similar_address(
                toks,
                hash,
                hash_info.get_addressCls(),
                hash_info.get_pos_cd_filter(),
                err_list=err_list,
                h1_nm=h1_nm,
                h23_nm=h23_nm,
            )
            err_failed = hash_info.get_err_failed()
            err_detail = hash_info.get_err_detail()

            if val:
                # "info_success": INFO_NEAR_ROAD_BLD_FOUND,
                # "info_detail": h,
                logger.debug(f"성공: [ {hash} ]")
                if hash_info.is_add_msg_when_success():
                    self._append_err(
                        err_list,
                        hash_info.get_info_success(),
                        hash_info.get_info_detail(),
                    )
                    logger.debug(
                        f"  {hash_info.get_info_success_msg()}: {hash_info.get_info_detail()}"
                    )

                    if hash_info.get_info_success() == INFO_NEAR_JIBUN_FOUND:
                        val["pos_cd"] = NEAR_JIBUN
                    elif hash_info.get_info_success() == INFO_NEAR_ROAD_BLD_FOUND:
                        val["pos_cd"] = NEAR_ROAD_BLD

                val["success"] = True
                val["errmsg"] = ""
                if "pos_cd" not in val:
                    if addressCls == AddressCls.JIBUN_ADDRESS:
                        val["pos_cd"] = JIBUN
                    elif addressCls == AddressCls.ROAD_ADDRESS:
                        val["pos_cd"] = ROAD
                    elif addressCls == AddressCls.BLD_ADDRESS:
                        val["pos_cd"] = BLD

                val["hash"] = hash
                val["address"] = address
                val["addressCls"] = hash_info.get_addressCls().value or addressCls.value
                toksString = self.tokenizer.getToksString(toks)
                val["toksString"] = toksString
                error_message = self._err_message(
                    err_list, addressCls.value, val.get("pos_cd")
                )
                val["errmsg"] = error_message or ""

                try:
                    h1_cd = self.get_h1(val)
                    h2_cd = self.get_h2(val)
                    val["h1_cd"] = h1_cd
                    val["h2_cd"] = h2_cd
                    val["kostat_h1_cd"] = self.hcodeMatcher.get_kostat_h1_cd(h2_cd)
                    val["kostat_h2_cd"] = self.hcodeMatcher.get_kostat_h2_cd(h2_cd)

                    val["hc"] = val.get("hd_cd")
                    val["lc"] = val.get("ld_cd")
                    val["rc"] = val.get("road_cd")
                    val["bn"] = val.get("bld_mgt_no", "")
                    val["h1"] = val.get("h1_nm")
                    val["rm"] = val.get("road_nm")
                except Exception as e:
                    val["h1_cd"] = ""
                    val["h2_cd"] = ""
                    val["kostat_h1_cd"] = ""
                    val["kostat_h2_cd"] = ""

                val["pos_cd"] = (
                    filter_to_pos_cd(val.get("pos_cd")) if val.get("pos_cd") else ""
                )

                return val
            else:
                last_err_for_hash_condition = (
                    err_list.last_err().get("err_cd") if err_list.last_err() else None
                )

                if important_error and not h23_nm:
                    break

                self._append_err(err_list, err_failed, err_detail)

        # self._append_err(err_list, ERR_NOT_FOUND)
        errmsg = self._err_message(err_list, addressCls.value, "")
        ac = hash_info.get_addressCls().value if hash_info else None
        if not ac:
            ac = addressCls.value

        val = {
            "success": False,
            "errmsg": errmsg,
            "hash": hash,
            "address": address,
            "addressCls": ac,
            "toksString": self.tokenizer.getToksString(toks),
        }

        return val

    def get_h1(self, val):
        """
        주어진 값에서 특정 키의 h1 코드인 첫 두 문자를 반환합니다.

        Args:
            val (dict): 'hd_cd', 'ld_cd', 'bld_mgt_no' 키를 포함하는 딕셔너리.

        Returns:
            str: 'hd_cd', 'ld_cd', 'bld_mgt_no' 중 하나의 첫 두 문자.
                해당 키가 존재하지 않으면 None을 반환합니다.
        """
        if h1_cd := val.get("h1_cd"):
            return h1_cd

        if val.get("hd_cd"):
            return val["hd_cd"][:2]
        elif val.get("ld_cd"):
            return val["ld_cd"][:2]
        elif val.get("bld_mgt_no"):
            return val["bld_mgt_no"][:2]

    def get_h2(self, val):
        """
        주어진 값에서 h2 코드를 추출하여 반환합니다.

        Args:
            val (dict): 'hd_cd', 'ld_cd', 또는 'bld_mgt_no' 키를 포함하는 딕셔너리.

        Returns:
            str: h2 코드 문자열.

        Raises:
            KeyError: 'hd_cd', 'ld_cd', 또는 'bld_mgt_no' 키가 딕셔너리에 없을 경우.
        """
        if h23_cd := val.get("h23_cd"):
            return h23_cd

        if val.get("hd_cd"):
            h23_cd = val["hd_cd"][:5]
        elif val.get("ld_cd"):
            h23_cd = val["ld_cd"][:5]
        elif val.get("bld_mgt_no"):
            h23_cd = val["bld_mgt_no"][:5]

        return self.hcodeMatcher.get_h23_cd(h23_cd)

    def filter_candidate_addresses(
        self,
        candidate_addresses,
        toks: Tokens,
        h1_nm,
        h23_nm,
        addressCls,
        pos_cd_filter: set = None,
        err_list: ErrList = None,
    ):
        # "청주시 흥덕구"는 "청주시" 또는 "흥덕구"로 입력된 주소일 수 있다.
        def h23_compare(db_h23_nm, in_h23_nm):
            if " " in db_h23_nm:
                h2_nm, h3_nm = db_h23_nm.split(" ", 1)
                return (
                    self.hsimplifier.h23Hash(h2_nm) == in_h23_nm
                    or self.hsimplifier.h23Hash(h3_nm) == in_h23_nm
                    or self.hsimplifier.h23Hash(db_h23_nm) == in_h23_nm
                )
            else:
                return self.hsimplifier.h23Hash(db_h23_nm) == in_h23_nm

        # logger.debug(f"filter_candidate_addresses: {len(candidate_addresses)}")
        if h1_nm:
            # h1_nm 같은 것만 선택
            candidate_addresses = [
                r for r in candidate_addresses if r["h1_nm"] == h1_nm
            ]
            if not candidate_addresses:
                return [], NOT_IMPORTANT_ERROR

        # 좌표 없는 것 필터링
        candidate_addresses = [r for r in candidate_addresses if r["x"]]
        if not candidate_addresses:
            self.append_err(ERR_NOT_FOUND, "좌표 없는 주소", err_list=err_list)
            return [], NOT_IMPORTANT_ERROR

        if pos_cd_filter:
            # pos_cd_filter가 있는 경우 필터링
            candidate_addresses = [
                r for r in candidate_addresses if r.get("pos_cd", "") in pos_cd_filter
            ]
            if not candidate_addresses:
                self.append_err(
                    ERR_POS_CD_NOT_FOUND, str(pos_cd_filter), err_list=err_list
                )
                return [], NOT_IMPORTANT_ERROR
        else:
            if addressCls == AddressCls.JIBUN_ADDRESS:
                # 지번 주소는 pos_cd가 없을 수 있음
                candidate_addresses = [
                    r for r in candidate_addresses if "pos_cd" not in r
                ]

                # h23_nm이 일치해야 함.
                if h23_nm:
                    candidate_addresses = [
                        r
                        for r in candidate_addresses
                        if h23_compare(r.get("h23_nm"), h23_nm)
                    ]
                else:  # h23_nm이 없는 경우 후보 데이터의 h23_nm이 유일해야 함
                    h23_nm_set = {r["h23_nm"] for r in candidate_addresses}
                    if len(h23_nm_set) > 1:
                        self.append_err(
                            ERR_NOT_UNIQUE_H23_NM, str(h23_nm_set), err_list=err_list
                        )
                        # self.important_error = True
                        return [], IMPORTANT_ERROR

            elif addressCls == AddressCls.ROAD_ADDRESS:
                # 12자의 road_cd가 존재해야 함
                candidate_addresses = [
                    r
                    for r in candidate_addresses
                    if r.get("road_cd") and len(r["road_cd"]) == 12
                ]

                # 도로명으로 시작하는 주소인 경우 h23_nm이 같아야 함.
                # 시군구를 제거하고 시도하는 경우에 해당될 수 있음. possible_hash 방식으로 변경 후 원래 주소의 toks를 변경하지 않고 전달 함.
                # 너무 복잡하니까 그냥 둔다.
                if toks.get(0).t == TOKEN_ROAD:
                    h23_nm_set = {r["h23_nm"] for r in candidate_addresses}
                    if len(h23_nm_set) > 1:
                        self.append_err(
                            ERR_ROAD_NOT_UNIQUE_H23_NM,
                            str(h23_nm_set),
                            err_list=err_list,
                        )
                        # self.important_error = True
                        return [], IMPORTANT_ERROR

                if addressCls == AddressCls.ROAD_ADDRESS and toks.hasTypes(TOKEN_H23):
                    h23_nm_set = {r["h23_nm"] for r in candidate_addresses}
                    h23_hash = self.hsimplifier.h23Hash(toks.get_text(TOKEN_H23))
                    # 도로명 주소 후보자의 h23_nm이 모두 같아야 함
                    if len(h23_nm_set) > 1:
                        # self.important_error = True
                        self.append_err(
                            ERR_ROAD_NOT_UNIQUE_H23_NM,
                            str(h23_nm_set),
                            err_list=err_list,
                        )
                        return [], IMPORTANT_ERROR
                    else:
                        if h23_nm:
                            candidate_addresses = [
                                r
                                for r in candidate_addresses
                                if h23_compare(r.get("h23_nm"), h23_nm)
                            ]

                        if not candidate_addresses:
                            self.append_err(
                                ERR_H23_NOT_FOUND,
                                h23_nm,
                                err_list=err_list,
                            )
                            return [], NOT_IMPORTANT_ERROR

                        # 경기도이며 h23_nm이 모두 같다면 입력 주소의 h23_nm과 후보자의 h23_nm이 일치해야 함
                        # if h1_nm == "경기" and h23_hash != self.hsimplifier.h23Hash(
                        #     next(iter(h23_nm_set))
                        # ).replace(" ", ""):
                        #     self.important_error = True
                        #     return [], IMPORTANT_ERROR

            elif addressCls == AddressCls.BLD_ADDRESS:
                candidate_addresses = [
                    r
                    for r in candidate_addresses
                    if r.get("bm")
                    # or "bld_reg" in r
                    # or "bld_nm_text" in r
                    # or "bld_nm" in r
                ]
            elif addressCls == AddressCls.RI_END_ADDRESS:
                candidate_addresses = [
                    r
                    for r in candidate_addresses
                    if r.get("pos_cd") in [RI_ADDR_FILTER]
                ]
                if not candidate_addresses:
                    self.append_err(ERR_RI_NOT_FOUND, err_list=err_list)
                    return [], NOT_IMPORTANT_ERROR
            elif addressCls == AddressCls.ROAD_END_ADDRESS:
                candidate_addresses = [
                    r
                    for r in candidate_addresses
                    if r.get("pos_cd") in [ROAD_ADDR_FILTER]
                ]
                if not candidate_addresses:
                    self.append_err(ERR_ROAD_NOT_FOUND, err_list=err_list)
                    return [], NOT_IMPORTANT_ERROR
            elif addressCls == AddressCls.H4_END_ADDRESS:
                candidate_addresses = [
                    r
                    for r in candidate_addresses
                    if r.get("pos_cd") in [HD_ADDR_FILTER, LD_ADDR_FILTER]
                ]
                if not candidate_addresses:
                    self.append_err(ERR_DONG_NOT_FOUND, err_list=err_list)
                    return [], NOT_IMPORTANT_ERROR
            elif addressCls == AddressCls.H23_END_ADDRESS:
                candidate_addresses = [
                    r
                    for r in candidate_addresses
                    if r.get("pos_cd") in [H23_ADDR_FILTER]
                ]
                if not candidate_addresses:
                    self.append_err(ERR_H23_NOT_FOUND, err_list=err_list)
                    return [], NOT_IMPORTANT_ERROR
            elif addressCls == AddressCls.H1_END_ADDRESS:
                candidate_addresses = [
                    r
                    for r in candidate_addresses
                    if r.get("pos_cd") in [H1_ADDR_FILTER]
                ]
                if not candidate_addresses:
                    self.append_err(ERR_H1_NOT_FOUND, err_list=err_list)
                    return [], NOT_IMPORTANT_ERROR

        if h1_nm and candidate_addresses:
            # h1_nm 같은 것만 선택
            candidate_addresses = [
                r for r in candidate_addresses if r["h1_nm"] == h1_nm
            ]
            if not candidate_addresses:
                self.append_err(ERR_H1_NM_NOT_FOUND, err_list=err_list)
                return [], NOT_IMPORTANT_ERROR
        else:
            # h1_nm 없으면 모든 h1_nm이 같아야 함. 그렇지 않으면 None 반환
            h1_nm_set = {r["h1_nm"] for r in candidate_addresses if "h1_nm" in r}
            if len(h1_nm_set) > 1:
                self.append_err(ERR_NOT_UNIQUE_H1_NM, str(h1_nm_set), err_list=err_list)
                return [], NOT_IMPORTANT_ERROR

        if addressCls == addressCls.JIBUN_ADDRESS and toks.hasTypes(TOKEN_RI):
            # ri가 있는 경우 ri_nm이 같아야 함
            ri_nm_set = {r["ri_nm"] for r in candidate_addresses if "ri_nm" in r}
            if len(ri_nm_set) > 1:
                self.append_err(ERR_NOT_UNIQUE_RI_NM, str(ri_nm_set), err_list=err_list)
                return [], NOT_IMPORTANT_ERROR

        if addressCls == AddressCls.ROAD_ADDRESS:
            # 도로명주소는 rm 이 있어야 함
            # 단 pos_cd_filter가 행정구역인 경우는 제외
            candidate_addresses = [
                r
                for r in candidate_addresses
                if r.get("road_cd")
                or r.get("pos_cd")
                in [
                    H23_ADDR_FILTER,
                    HD_ADDR_FILTER,
                    LD_ADDR_FILTER,
                    H1_ADDR_FILTER,
                    RI_ADDR_FILTER,
                ]
            ]

            if not candidate_addresses:
                self.append_err(ERR_ROAD_NM_NOT_FOUND, err_list=err_list)
                return [], NOT_IMPORTANT_ERROR

            if not h1_nm:
                # h1_nm 없으면 모든 후보의 도로명 코드가 같아야 함
                road_cds = {r.get("road_cd", "") for r in candidate_addresses}
                if len(road_cds) > 1:
                    self.append_err(
                        ERR_NOT_UNIQUE_ROAD_CD, str(road_cds), err_list=err_list
                    )
                    return [], NOT_IMPORTANT_ERROR

        # extras.get("updater") 우선순위. "roadbase_updater"를 가장 나중에, extras.get("yyyymm") 우선순위. 가장 최근 날짜를 우선으로 함.
        # Sort by extras.get("updater") and extras.get("yyyymm")
        candidate_addresses = sorted(
            candidate_addresses,
            key=lambda x: (
                0 if x.get("extras", {}).get("updater") == "roadbase_updater" else 1,
                x.get("extras", {}).get("yyyymm", ""),
            ),
            reverse=True,
        )

        # # d["bld_mgt_no"] 역순 정렬 (경험적으로 건물번호가 있으면 더 정확한 결과)
        # candidate_addresses = sorted(
        #     candidate_addresses,
        #     key=lambda x: (
        #         x.get("bld_mgt_no", "") if x.get("bld_mgt_no") is not None else ""
        #     ),
        #     reverse=True,
        # )
        return candidate_addresses, False

    def most_similar_address(
        self,
        toks: Tokens,
        hash,
        addressCls: str = None,
        pos_cd_filter: list = None,
        err_list: ErrList = None,
        h1_nm: str = None,
        h23_nm: str = None,
    ):
        """
        주어진 토큰과 키를 사용하여 가장 유사한 주소를 반환합니다.

        Args:
            toks (list): 주소를 나타내는 토큰 리스트.
            key (str): 데이터베이스에서 검색할 키.

        Returns:
            dict or None: 가장 유사한 주소를 나타내는 딕셔너리.
                유사한 주소가 없거나 오류가 발생한 경우 None을 반환합니다.

        예외:
            Exception: 데이터베이스 접근 또는 JSON 파싱 중 오류가 발생할 수 있습니다.
        """
        try:
            o = self._get_db().get(hash)
            if o == None:
                logger.debug(f"Not Found: {addressCls}, hash: {hash}")
                return None, NOT_IMPORTANT_ERROR

            t0 = toks.get(0)
            if t0.t == TOKEN_H23 and t0.val.startswith("세종"):
                # 세종시 주소는 h1 없이 h23(세종시)으로 시작한다.
                t0.t = TOKEN_H1

            if isinstance(o, bytearray) or isinstance(o, bytes):
                candidate_addresses = json.loads(o)
            else:
                candidate_addresses = o

            # h1 다르면 배제
            # h1_pos = toks.index(TOKEN_H1)
            # if h1_pos > -1:
            #     # h1 같은 것만 선택
            #     h1_nm = self.hsimplifier.h1Hash(toks[h1_pos])
            # else:
            #     h1_nm = None

            # 후보자 압축 (h1_nm이 있는 경우 h1_nm과 일치하는 것만 선택)
            candidate_addresses, important_error = self.filter_candidate_addresses(
                candidate_addresses,
                toks,
                h1_nm,
                h23_nm,
                addressCls,
                pos_cd_filter=pos_cd_filter,
                err_list=err_list,
            )
            if not candidate_addresses:
                return None, important_error
            if len(candidate_addresses) == 1:
                # 후보가 하나면 바로 반환
                val = candidate_addresses[0]
                return val, important_error
            elif pos_cd_filter:
                return candidate_addresses[0], important_error

            if addressCls == AddressCls.JIBUN_ADDRESS:
                if toks.hasTypes(TOKEN_BLD):
                    begin, end = toks.searchTypeSequence([TOKEN_BLD, TOKEN_BLD_DONG])
                    if begin < 0:  # not found
                        begin, end = toks.searchTypeSequence([TOKEN_BLD])
                    tmp = []
                    for n in range(begin, end):
                        tmp.append(toks.get(n).val)
                    bld_name_with_dong = " ".join(tmp)
                    most_similar_val, max_similarity = self.find_most_similar_building(
                        candidate_addresses, bld_name_with_dong
                    )
                    # 유사도가 0.5 이하여도 가장 비슷한 것을 반환
                    if most_similar_val:
                        val = most_similar_val
                        val["pos_cd"] = (
                            JIBUN  # 지번 주소는 건물명까지 검색 안 해도 성공한 것.
                        )
                        val["similar_hash"] = hash
                        return val, important_error
                    else:
                        val = candidate_addresses[0]
                        # val["similar_hash"] = hash
                        return val, important_error
                else:
                    val = candidate_addresses[0]
                    val["similar_hash"] = hash
                    return val, important_error

            elif addressCls == AddressCls.ROAD_ADDRESS:
                if toks.hasTypes(TOKEN_BLD):
                    begin, end = toks.searchTypeSequence([TOKEN_BLD, TOKEN_BLD_DONG])
                    if begin < 0:  # not found
                        begin, end = toks.searchTypeSequence([TOKEN_BLD])
                    tmp = []
                    for n in range(begin, end):
                        tmp.append(toks.get(n).val)
                    bld_name_with_dong = " ".join(tmp)
                    most_similar_val, max_similarity = self.find_most_similar_building(
                        candidate_addresses, bld_name_with_dong
                    )
                    # 유사도가 0.5 이하여도 가장 비슷한 것을 반환
                    if most_similar_val:
                        val = most_similar_val
                        val["pos_cd"] = (
                            ROAD  # 지번 주소는 건물명까지 검색 안 해도 성공한 것.
                        )
                        val["similar_hash"] = hash
                        return val, important_error

                # 건물명이 없거나 유사한 건물명이 없는 경우
                val = candidate_addresses[0]
                val["similar_hash"] = hash
                return val, important_error

            elif addressCls == AddressCls.BLD_ADDRESS and toks.hasTypes(TOKEN_BLD):
                # 가장 유사한 건물 주소를 찾는다.
                begin, end = toks.searchTypeSequence([TOKEN_BLD, TOKEN_BLD_DONG])
                if begin < 0:  # not found
                    begin, end = toks.searchTypeSequence([TOKEN_BLD])
                tmp = []
                for n in range(begin, end):
                    tmp.append(toks.get(n).val)
                bld_name_with_dong = " ".join(tmp)
                most_similar_val, max_similarity = self.find_most_similar_building(
                    candidate_addresses, bld_name_with_dong
                )
                if most_similar_val and max_similarity > 0.5:
                    # 유사도가 0.5 이상인 경우에만 반환
                    val = most_similar_val
                    val["pos_cd"] = SIMILAR_BUILDING_NAME
                    val["similar_hash"] = hash
                    self.append_err(INFO_SIMILAR_BLD_FOUND, " ".join(val["bm"]))
                    return val, important_error
                else:
                    self.append_err(ERR_BLD_NM_NOT_FOUND, bld_name_with_dong)

            elif addressCls in (
                AddressCls.RI_END_ADDRESS,
                AddressCls.RI_END_ADDRESS,
                AddressCls.ROAD_END_ADDRESS,
                AddressCls.H4_END_ADDRESS,
                AddressCls.H23_END_ADDRESS,
                AddressCls.H1_END_ADDRESS,
            ):
                val = candidate_addresses[0]
                return val, important_error

            # 길이름 다르면 배제: 보류
            return None, important_error
        except Exception as e:
            # print(e)
            return None, important_error

    def err_message(self, addressCls, pos_cd, err_list: ErrList = None):
        if addressCls in (AddressCls.NOT_ADDRESS, AddressCls.UNRECOGNIZABLE_ADDRESS):
            return "주소 형식이 아님"

        # ROAD_ADDRESS_INFO, NOTFOUND_ERROR, NEAR_ROAD_BLD_NOT_FOUND_ERROR, ROAD_NOT_FOUND_ERROR
        # , DONG_NOT_FOUND_ERROR, H23_NOT_FOUND_ERROR, H1_NOT_FOUND_ERROR
        # , ROAD_NOT_FOUND_ERROR, DONG_NOT_FOUND_ERROR'
        msg = ""

        pos_cd = filter_to_pos_cd(pos_cd) if pos_cd else ""

        if addressCls == AddressCls.RI_END_ADDRESS or pos_cd == RI_ADDR:
            msg = "리 이름까지 유효"
        if addressCls == AddressCls.ROAD_END_ADDRESS or pos_cd == ROAD_ADDR:
            msg = "도로 이름까지 유효"
        if addressCls == AddressCls.H4_END_ADDRESS or pos_cd in (HD_ADDR, LD_ADDR):
            err = self.err_list.get_err_by_cd(ERR_ROAD_NOT_FOUND)
            if err:
                msg = f'도로명 오류: {err.get("detail", "")}'
            else:
                msg = "행정동 또는 법정동 이름까지 유효"

        if addressCls == AddressCls.H23_END_ADDRESS or pos_cd == H23_ADDR:
            err = self.err_list.get_err_by_cd(ERR_DONG_NOT_FOUND)
            if err:
                msg = f'동명 오류: {err.get("detail", "")}'
            else:
                msg = "시군구 이름까지 유효"

        if addressCls == AddressCls.H1_END_ADDRESS or pos_cd == H1_ADDR:
            err = self.err_list.get_err_by_cd(ERR_H23_NOT_FOUND)
            if err:
                msg = f'시군구명 오류: {err.get("detail", "")}'
            else:
                msg = "광역시도 이름까지 유효"

        # if msg_detail := self.err_list.to_detail_message():
        #     msg = f"{msg} ({msg_detail})".strip()
        detail = self.err_list.last_detail_message(has_detail=True)
        if detail:
            if msg:
                msg = f"{msg} ({detail})".strip()
            else:
                msg = detail
        return msg

    def append_err(self, err, msg=None, err_list: ErrList = None):
        if err_list:
            err_list.append(err, msg)

    def last_detail_message(self):
        """
        마지막 오류 메시지를 반환합니다.
        """
        return self.err_list.last_detail_message()

    def find_most_similar_building(self, d, bld_name_with_dong):
        """
        사용자 입력과 가장 유사한 건물명을 찾아 반환합니다.
        """

        bld_name_with_dong_normalized = bld_name_with_dong.lower().replace(
            " ", ""
        )  # 소문자 변환 및 공백 제거

        max_similarity = -1
        most_similar_val = None

        for r in d:
            if "bm" not in r:
                continue
            name = " ".join(r["bm"])
            name_normalized = name.lower().replace(" ", "")  # 소문자 변환 및 공백 제거

            # SequenceMatcher를 사용하여 유사도 계산
            # ratio()는 0.0 ~ 1.0 사이의 유사도 점수를 반환합니다.
            similarity = SequenceMatcher(
                None, bld_name_with_dong_normalized, name_normalized
            ).ratio()

            # print(f"'{bld_name_with_dong}' vs '{name}' (Normalized: '{name_normalized}'): Similarity = {similarity:.4f}") # 디버깅용

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_val = r  # 원본 건물명 저장

        return most_similar_val, max_similarity

        # # 예시 데이터
        # building_data = ["현대아파트", "현대오피스텔", "현대타운빌", "현대오피스", "삼성 아파트"]

        # # 사용자 입력
        # user_query = "현대오피스"

        # most_similar, score = find_most_similar_building(user_query, building_data)

        # print(f"사용자 입력: '{user_query}'")
        # print(f"가장 유사한 건물명: '{most_similar}' (유사도: {score:.4f})")

        # # 다른 예시
        # user_query_2 = "현대 오피스"
        # most_similar_2, score_2 = find_most_similar_building(user_query_2, building_data)
        # print(f"\n사용자 입력: '{user_query_2}'")
        # print(f"가장 유사한 건물명: '{most_similar_2}' (유사도: {score_2:.4f})")

        # user_query_3 = "현데오피스텔" # 오타
        # most_similar_3, score_3 = find_most_similar_building(user_query_3, building_data)
        # print(f"\n사용자 입력: '{user_query_3}'")
        # print(f"가장 유사한 건물명: '{most_similar_3}' (유사도: {score_3:.4f})")

        # user_query_4 = "현대 빌딩" # 없는 데이터와 유사도
        # most_similar_4, score_4 = find_most_similar_building(user_query_4, building_data)
        # print(f"\n사용자 입력: '{user_query_4}'")
        # print(f"가장 유사한 건물명: '{most_similar_4}' (유사도: {score_4:.4f})")

    # def search_old(self, addr):
    #     """
    #     주어진 주소를 검색하여 가장 유사한 주소 정보를 반환합니다.

    #     Parameters:
    #     addr (str): 검색할 주소 문자열.

    #     Returns:
    #     dict: 검색 결과를 포함한 딕셔너리. 성공 시, 딕셔너리는 다음 키를 포함합니다:
    #         - success (bool): 검색 성공 여부.
    #         - errmsg (str): 오류 메시지 (성공 시 빈 문자열).
    #         - h1_cd (str): h1 코드 (성공 시).
    #         - h2_cd (str): h2 코드 (성공 시).
    #         - kostat_h1_cd (str): KOSTAT h1 코드 (성공 시).
    #         - kostat_h2_cd (str): KOSTAT h2 코드 (성공 시).
    #         - hash (str): 주소 해시 값.
    #         - address (str): 입력된 주소.
    #         - addressCls (str): 주소 클래스.
    #         - toksString (str): 토큰 문자열.

    #     오류가 발생하거나 주소를 찾을 수 없는 경우, 딕셔너리는 다음 키를 포함합니다:
    #         - success (bool): False.
    #         - errmsg (str): 오류 메시지.
    #         - hash (str): 주소 해시 값.
    #         - address (str): 입력된 주소.
    #         - addressCls (str): 주소 클래스.
    #         - toksString (str): 토큰 문자열.
    #     """
    #     hash = ""
    #     toks = []
    #     self.err_list = ErrList()
    #     self.imoprtant_error = False
    #     addressCls = AddressCls.NOT_ADDRESS
    #     err = ERR_RUNTIME

    #     if not isinstance(addr, str):
    #         return None

    #     address = addr.strip('"')
    #     if address == "":
    #         addressCls = AddressCls.NOT_ADDRESS
    #         return None

    #     hash, toks, addressCls, err = self.addressHash(address)

    #     if addressCls == AddressCls.NOT_ADDRESS:
    #         self.append_err(ERR_NOT_ADDRESS)
    #     elif addressCls == AddressCls.JIBUN_ADDRESS:
    #         self.append_err(INFO_JIBUN_ADDRESS)
    #     elif addressCls == AddressCls.BLD_ADDRESS:
    #         self.append_err(INFO_BLD_ADDRESS)
    #     elif addressCls == AddressCls.ROAD_ADDRESS:
    #         self.append_err(INFO_ROAD_ADDRESS)
    #     elif addressCls == AddressCls.RI_END_ADDRESS:
    #         self.append_err(INFO_RI_END_ADDRESS)
    #     elif addressCls == AddressCls.ROAD_END_ADDRESS:
    #         self.append_err(INFO_ROAD_END_ADDRESS)
    #     elif addressCls == AddressCls.H4_END_ADDRESS:
    #         self.append_err(INFO_H4_END_ADDRESS)
    #     elif addressCls == AddressCls.H23_END_ADDRESS:
    #         self.append_err(INFO_H23_END_ADDRESS)
    #     elif addressCls == AddressCls.H1_END_ADDRESS:
    #         self.append_err(INFO_H1_END_ADDRESS)

    #     logger.debug(f"address: {address}, \n hash: {hash}, addressCls: {addressCls}")
    #     logger.debug(f"toks: {toks}, errmsg: {err}")

    #     if err:
    #         self.append_err(err)

    #         logger.debug(f"{self.err_list.to_err_str()}, {addressCls}")
    #         return {
    #             "success": False,
    #             "errmsg": self.err_message(addressCls, None),
    #         }
    #     toksString = self.tokenizer.getToksString(toks)

    #     if hash:
    #         logger.debug(f"Try search addressCls: {addressCls}, hash: {hash}")
    #         val = self.most_similar_address(toks, hash, addressCls)
    #         if not val:
    #             if self.imoprtant_error:
    #                 val = {
    #                     "success": False,
    #                     "errmsg": self.err_message(addressCls, None),
    #                 }
    #                 return val

    #             self.append_err(ERR_NOT_FOUND)

    #             if addressCls == AddressCls.ROAD_ADDRESS:
    #                 val = self.most_similar_road_addr(toks, hash, addressCls)
    #             elif addressCls == AddressCls.JIBUN_ADDRESS:
    #                 val = self.most_similar_jibun_addr(toks, hash, addressCls)
    #             elif addressCls == AddressCls.BLD_ADDRESS:
    #                 val = self.most_similar_bld_addr(toks, hash, addressCls)

    #         if not val:
    #             # 리, 동, 시군구 제거한 주소 검색 시도
    #             combinations = self.address_combination(toks, addressCls)
    #             for comb in combinations:
    #                 val = self.most_similar_address(toks, comb["hash"], addressCls)
    #                 if val:
    #                     logger.debug(
    #                         f'Found address with combination: {comb["hash"], comb["err"]}'
    #                     )
    #                     # self.append_err(
    #                     #     comb["err"], "리, 동, 시군구 제거한 주소 검색 시도"
    #                     # )
    #                     break

    #         # 대표 주소 검색
    #         if not val:
    #             val, addressCls = self.search_representative_address(toks, addressCls)

    #         if not val:
    #             self.append_err(ERR_REPRESENTATIVE_ADDRESS_NOT_FOUND)
    #             logger.debug(f"NOTFOUND ERROR: {hash}, {addressCls}")
    #             val = {"success": False, "errmsg": "NOTFOUND ERROR"}
    #         else:
    #             val["success"] = True
    #             val["errmsg"] = ""
    #             if "pos_cd" not in val:
    #                 if addressCls == AddressCls.JIBUN_ADDRESS:
    #                     val["pos_cd"] = JIBUN
    #                 elif addressCls == AddressCls.ROAD_ADDRESS:
    #                     val["pos_cd"] = ROAD
    #                 elif addressCls == AddressCls.BLD_ADDRESS:
    #                     val["pos_cd"] = BLD

    #             try:
    #                 h1_cd = self.get_h1(val)
    #                 h2_cd = self.get_h2(val)
    #                 val["h1_cd"] = h1_cd
    #                 val["h2_cd"] = h2_cd
    #                 val["kostat_h1_cd"] = self.hcodeMatcher.get_kostat_h1_cd(h2_cd)
    #                 val["kostat_h2_cd"] = self.hcodeMatcher.get_kostat_h2_cd(h2_cd)
    #             except Exception as e:
    #                 val["h1_cd"] = ""
    #                 val["h2_cd"] = ""
    #                 val["kostat_h1_cd"] = ""
    #                 val["kostat_h2_cd"] = ""
    #                 # print(e, address, val)
    #     else:
    #         val = {"success": False, "errmsg": err}

    #     val["hash"] = hash
    #     val["address"] = address
    #     val["addressCls"] = addressCls
    #     val["toksString"] = toksString
    #     error_message = self.err_message(addressCls, val.get("pos_cd"))
    #     val["errmsg"] = error_message

    #     logger.debug(f"val: {json.dumps(val, indent=4, ensure_ascii=False)}")
    #     logger.debug(f'{self.err_list.to_err_str()}, {val.get("pos_cd", addressCls)}')
    #     logger.debug(error_message or "미매핑 사유 텍스트 없음")

    #     val["pos_cd"] = filter_to_pos_cd(val.get("pos_cd")) if val.get("pos_cd") else ""

    #     return val

    # def search_representative_address(self, toks: Tokens, addressCls):
    #     """
    #     BASE_ADDRESS_ORDER = [
    #         ROAD_END_ADDRESS,
    #         RI_END_ADDRESS,
    #         H4_END_ADDRESS,
    #         H23_END_ADDRESS,
    #         H1_END_ADDRESS,
    #     ]
    #     """
    #     if addressCls == AddressCls.ROAD_ADDRESS:
    #         addressCls = AddressCls.ROAD_END_ADDRESS
    #     elif addressCls == AddressCls.JIBUN_ADDRESS:
    #         addressCls = AddressCls.RI_END_ADDRESS
    #     elif addressCls == AddressCls.BLD_ADDRESS:
    #         addressCls = AddressCls.ROAD_END_ADDRESS

    #     begin_addressCls_pos = self.BASE_ADDRESS_ORDER.index(addressCls)
    #     for i in range(begin_addressCls_pos, len(self.BASE_ADDRESS_ORDER)):
    #         addressCls = self.BASE_ADDRESS_ORDER[i]
    #         end_with_token_info = self.END_WITH_TOKEN_INFO.get(addressCls, None)
    #         end_with = end_with_token_info["end_with"]
    #         pos_cd_filter = end_with_token_info["pos_cd_filter"]

    #         if not toks.hasTypes(end_with):
    #             continue

    #         if addressCls == AddressCls.ROAD_END_ADDRESS:
    #             hash = self.roadAddress.hash(toks, end_with=end_with)
    #         else:
    #             hash = self.jibunAddress.hash(toks, end_with=end_with)

    #         logger.debug(f"Try search addressCls: {addressCls}, hash: {hash}")
    #         val = self.most_similar_address(
    #             toks, hash, addressCls, pos_cd_filter=pos_cd_filter
    #         )

    #         if val:
    #             return val, addressCls
    #         else:
    #             if addressCls == AddressCls.ROAD_END_ADDRESS:
    #                 self.append_err(ERR_ROAD_NOT_FOUND, hash)
    #             elif addressCls == AddressCls.RI_END_ADDRESS:
    #                 self.append_err(ERR_RI_NOT_FOUND, hash)
    #             elif addressCls == AddressCls.H4_END_ADDRESS:
    #                 self.append_err(ERR_DONG_NOT_FOUND, hash)
    #             elif addressCls == AddressCls.H23_END_ADDRESS:
    #                 self.append_err(ERR_H23_NOT_FOUND, hash)
    #             elif addressCls == AddressCls.H1_END_ADDRESS:
    #                 self.append_err(ERR_H1_NOT_FOUND, hash)

    #     return None, AddressCls.NOT_ADDRESS

    # def __bldAddressHash(self, toks):
    #     """
    #     주어진 토큰을 사용하여 주소 해시를 생성합니다.

    #     Args:
    #         toks (list): 주소 해시에 사용될 토큰 리스트.

    #     Returns:
    #         str: 생성된 주소 해시.
    #     """
    #     return self.bldAddress.hash(toks)

    # def __jibunAddressHash(self, toks):
    #     """
    #     주어진 토큰을 사용하여 지번 주소의 해시 값을 반환합니다.

    #     Args:
    #         toks (list): 해시 값을 생성하는 데 사용될 토큰들의 리스트.

    #     Returns:
    #         str: 지번 주소의 해시 값.
    #     """
    #     return self.jibunAddress.hash(toks)

    # def __roadAddressHash(self, toks):
    #     """
    #     주어진 토큰(toks)을 사용하여 도로명 주소의 해시 값을 반환합니다.

    #     Args:
    #         toks (str): 해시 값을 생성하는 데 사용될 토큰.

    #     Returns:
    #         int: 도로 주소의 해시 값.
    #     """
    #     return self.roadAddress.hash(toks)

    # def most_similar_jibun_addr(self, toks: Tokens, hash, addressCls: str):
    #     """
    #     주어진 토큰과 해시를 사용하여 가장 유사한 지번 주소를 반환합니다.
    #     """
    #     if toks.hasTypes(TOKEN_BNG):
    #         # 인근 지번 검색
    #         near_jibun_hashs = self.get_near_jibun_hashs(hash)
    #         val = None
    #         for near_hash in near_jibun_hashs:
    #             val = self.most_similar_address(toks, near_hash, addressCls)
    #             if val:
    #                 val["pos_cd"] = NEAR_JIBUN
    #                 self.append_err(INFO_NEAR_JIBUN_FOUND, str(near_hash))
    #                 return val

    #         if not val:
    #             self.append_err(ERR_NEAR_JIBUN_NOT_FOUND, str(near_jibun_hashs))
    #             # return None

    #         # 리 대표주소 검색
    #         if toks.hasTypes(TOKEN_RI):
    #             ri_hash = self.jibunAddress.hash(toks, end_with=TOKEN_RI)
    #             val = self.most_similar_address(
    #                 toks, ri_hash, addressCls, pos_cd_filter=[RI_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val

    #         # 동 대표주소 검색
    #         if toks.hasTypes(TOKEN_H4):
    #             hash = self.jibunAddress.hash(toks, end_with=TOKEN_H4)
    #             val = self.most_similar_address(
    #                 toks,
    #                 hash,
    #                 addressCls,
    #                 pos_cd_filter=[HD_ADDR_FILTER, LD_ADDR_FILTER],
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_DONG_NOT_FOUND, toks.get(toks.index(TOKEN_H4)).val
    #                 )
    #                 return None

    #         # 시군구 대표주소 검색
    #         if toks.hasTypes(TOKEN_H23):
    #             hash = self.jibunAddress.hash(toks, end_with=TOKEN_H23)
    #             val = self.most_similar_address(
    #                 toks, hash, addressCls, pos_cd_filter=[H23_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_H23_NOT_FOUND, toks.get(toks.index(TOKEN_H23)).val
    #                 )
    #                 return None

    #         # 광역시도 대표주소 검색
    #         if toks.hasTypes(TOKEN_H1):
    #             hash = self.jibunAddress.hash(toks, end_with=TOKEN_H1)
    #             val = self.most_similar_address(
    #                 toks, hash, addressCls, pos_cd_filter=[H1_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_H1_NOT_FOUND, toks.get(toks.index(TOKEN_H1)).val
    #                 )
    #                 return None

    #     return None

    # def most_similar_road_addr(self, toks: Tokens, hash, addressCls: str):
    #     """
    #     주어진 토큰과 해시를 사용하여 가장 유사한 지번 주소를 반환합니다.

    #     Args:
    #         toks (Tokens): 주소를 나타내는 토큰 리스트.
    #         hash (str): 지번 주소의 해시 값.
    #         addressCls (str): 주소 클래스 (지번 주소).

    #     Returns:
    #         dict or None: 가장 유사한 지번 주소를 나타내는 딕셔너리.
    #             유사한 주소가 없거나 오류가 발생한 경우 None을 반환합니다.
    #     """
    #     if toks.hasTypes(TOKEN_BLDNO):
    #         # 인근 건물번호 검색
    #         near_road_bld_hashs = self.get_near_road_bld_hashs(hash)
    #         for near_hash in near_road_bld_hashs:
    #             val = self.most_similar_address(toks, near_hash, addressCls)
    #             if val:
    #                 val["pos_cd"] = NEAR_ROAD_BLD
    #                 self.append_err(INFO_NEAR_ROAD_BLD_FOUND, str(near_hash))
    #                 return val

    #         self.append_err(ERR_NEAR_ROAD_BLD_NOT_FOUND, str(near_road_bld_hashs))

    #         # 리 빼고 검색
    #         if toks.hasTypes(TOKEN_RI):
    #             road_hash = self.roadAddress.hash(
    #                 toks, start_with=TOKEN_ROAD, ignore=[TOKEN_RI]
    #             )
    #             logger.debug(
    #                 f"most_similar_road_addr: road_hash: {road_hash}, toks: {toks}"
    #             )
    #             val = self.most_similar_address(toks, road_hash, addressCls)
    #             if val:
    #                 return val

    #         # 도로명 이하 주소 검색
    #         if toks.hasTypes(TOKEN_ROAD):
    #             road_hash = self.roadAddress.hash(toks, start_with=TOKEN_ROAD)
    #             logger.debug(
    #                 f"most_similar_road_addr: road_hash: {road_hash}, toks: {toks}"
    #             )
    #             val = self.most_similar_address(toks, road_hash, addressCls)
    #             if val:
    #                 self.append_err(ERR_REGION_NOT_FOUND)
    #                 return val

    #         # 도로명 대표주소 검색
    #         if toks.hasTypes(TOKEN_ROAD):
    #             road_hash = self.roadAddress.hash(toks, end_with=TOKEN_ROAD)
    #             val = self.most_similar_address(
    #                 toks, road_hash, addressCls, pos_cd_filter=[ROAD_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_ROAD_NOT_FOUND, toks.get(toks.index(TOKEN_ROAD)).val
    #                 )

    #         # 리 대표주소 검색
    #         if toks.hasTypes(TOKEN_RI):
    #             ri_hash = self.jibunAddress.hash(toks, end_with=TOKEN_RI)
    #             val = self.most_similar_address(
    #                 toks, ri_hash, addressCls, pos_cd_filter=[RI_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_RI_NOT_FOUND, toks.get(toks.index(TOKEN_RI)).val
    #                 )

    #         # 동 대표주소 검색
    #         if toks.hasTypes(TOKEN_H4):
    #             hash = self.jibunAddress.hash(toks, end_with=TOKEN_H4)
    #             val = self.most_similar_address(
    #                 toks,
    #                 hash,
    #                 addressCls,
    #                 pos_cd_filter=[HD_ADDR_FILTER, LD_ADDR_FILTER],
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_DONG_NOT_FOUND, toks.get(toks.index(TOKEN_H4)).val
    #                 )

    #         # 시군구 대표주소 검색
    #         if toks.hasTypes(TOKEN_H23):
    #             hash = self.jibunAddress.hash(toks, end_with=TOKEN_H23)
    #             val = self.most_similar_address(
    #                 toks, hash, addressCls, pos_cd_filter=[H23_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_H23_NOT_FOUND, toks.get(toks.index(TOKEN_H23)).val
    #                 )

    #         # 광역시도 대표주소 검색
    #         if toks.hasTypes(TOKEN_H1):
    #             hash = self.jibunAddress.hash(toks, end_with=TOKEN_H1)
    #             val = self.most_similar_address(
    #                 toks, hash, addressCls, pos_cd_filter=[H1_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_H1_NOT_FOUND, toks.get(toks.index(TOKEN_H1)).val
    #                 )

    #     return None

    # def most_similar_bld_addr(self, toks: Tokens, hash, addressCls: str):
    #     """
    #     주어진 토큰과 해시를 사용하여 가장 유사한 지번 주소를 반환합니다.

    #     Args:
    #         toks (Tokens): 주소를 나타내는 토큰 리스트.
    #         hash (str): 지번 주소의 해시 값.
    #         addressCls (str): 주소 클래스 (지번 주소).

    #     Returns:
    #         dict or None: 가장 유사한 지번 주소를 나타내는 딕셔너리.
    #             유사한 주소가 없거나 오류가 발생한 경우 None을 반환합니다.
    #     """
    #     # keys = self.search_start_with("영등포_")  # 건물명 주소는 도로명 주소로 시작

    #     if toks.hasTypes(TOKEN_BLD):
    #         # # 유사한 건물명 검색

    #         # 리 빼고 검색
    #         if toks.hasTypes(TOKEN_RI):
    #             road_hash = self.roadAddress.hash(
    #                 toks, start_with=TOKEN_ROAD, ignore=[TOKEN_RI]
    #             )
    #             logger.debug(
    #                 f"most_similar_bld_addr: road_hash: {road_hash}, toks: {toks}"
    #             )
    #             val = self.most_similar_address(toks, road_hash, addressCls)
    #             if val:
    #                 return val

    #         # 도로명 이하 주소 검색
    #         if toks.hasTypes(TOKEN_ROAD):
    #             road_hash = self.roadAddress.hash(toks, start_with=TOKEN_ROAD)
    #             logger.debug(
    #                 f"most_similar_bld_addr: road_hash: {road_hash}, toks: {toks}"
    #             )
    #             val = self.most_similar_address(toks, road_hash, addressCls)
    #             if val:
    #                 return val

    #         # 도로명 대표주소 검색
    #         if toks.hasTypes(TOKEN_ROAD):
    #             road_hash = self.roadAddress.hash(toks, end_with=TOKEN_ROAD)
    #             val = self.most_similar_address(
    #                 toks, road_hash, addressCls, pos_cd_filter=[ROAD_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_ROAD_NOT_FOUND, toks.get(toks.index(TOKEN_ROAD)).val
    #                 )

    #         # 리 대표주소 검색
    #         if toks.hasTypes(TOKEN_RI):
    #             ri_hash = self.jibunAddress.hash(toks, end_with=TOKEN_RI)
    #             val = self.most_similar_address(
    #                 toks, ri_hash, addressCls, pos_cd_filter=[RI_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_RI_NOT_FOUND, toks.get(toks.index(TOKEN_RI)).val
    #                 )
    #         # 동 대표주소 검색
    #         if toks.hasTypes(TOKEN_H4):
    #             hash = self.jibunAddress.hash(toks, end_with=TOKEN_H4)
    #             val = self.most_similar_address(
    #                 toks,
    #                 hash,
    #                 addressCls,
    #                 pos_cd_filter=[HD_ADDR_FILTER, LD_ADDR_FILTER],
    #             )
    #             if val:
    #                 self.append_err(
    #                     ERR_BLD_NM_NOT_FOUND, toks.get(toks.index(TOKEN_BLD)).val
    #                 )
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_DONG_NOT_FOUND, toks.get(toks.index(TOKEN_H4)).val
    #                 )
    #         # 시군구 대표주소 검색
    #         if toks.hasTypes(TOKEN_H23):
    #             hash = self.jibunAddress.hash(toks, end_with=TOKEN_H23)
    #             val = self.most_similar_address(
    #                 toks, hash, addressCls, pos_cd_filter=[H23_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_H23_NOT_FOUND, toks.get(toks.index(TOKEN_H23)).val
    #                 )
    #         # 광역시도 대표주소 검색
    #         if toks.hasTypes(TOKEN_H1):
    #             hash = self.jibunAddress.hash(toks, end_with=TOKEN_H1)
    #             val = self.most_similar_address(
    #                 toks, hash, addressCls, pos_cd_filter=[H1_ADDR_FILTER]
    #             )
    #             if val:
    #                 return val
    #             else:
    #                 self.append_err(
    #                     ERR_H1_NOT_FOUND, toks.get(toks.index(TOKEN_H1)).val
    #                 )
    #     return None

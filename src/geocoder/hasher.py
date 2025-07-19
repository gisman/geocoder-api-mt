import src.config as config
from src.geocoder.address_cls import AddressCls
from src.geocoder.hash import RoadAddress
from src.geocoder.hash.BldAddress import BldAddress
from src.geocoder.hash.JibunAddress import JibunAddress
from src.geocoder.util import HSimplifier
from src.geocoder.util.hcodematcher import HCodeMatcher
from .errs import *
from .tokens import *
from .Tokenizer import Tokenizer


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


class Hasher:
    """
    주소 해시를 생성하는 클래스입니다.
    """

    def __init__(
        self,
        tokenizer: Tokenizer,
        jibunAddress: JibunAddress,
        bldAddress: BldAddress,
        roadAddress: RoadAddress,
        hsimplifier: HSimplifier,
        hcodeMatcher: HCodeMatcher,
    ):
        """
        Hasher 객체를 초기화합니다.

        Args:
            tokenizer (Tokenizer): 주소 토큰화를 위한 Tokenizer 객체.
        """
        self.tokenizer = tokenizer
        self.jibunAddress = jibunAddress
        self.bldAddress = bldAddress
        self.roadAddress = roadAddress
        self.hsimplifier = hsimplifier
        self.hcodeMatcher = hcodeMatcher

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

    def __classfy(self, toks: Tokens):
        """
        주소 토큰을 분류하여 주소 유형을 반환합니다.

        Args:
            toks (Tokens): 주소를 구성하는 토큰 객체.

        Returns:
            str: 주소 유형을 나타내는 문자열. 가능한 값은 다음과 같습니다:
                - AddressCls.NOT_ADDRESS: 주소가 아닌 경우.
                - AddressCls.ROAD_ADDRESS: 도로명 주소인 경우.
                - AddressCls.JIBUN_ADDRESS: 지번 주소인 경우.
                - AddressCls.BLD_ADDRESS: 건물 주소인 경우.

                - AddressCls.RI_END_ADDRESS: 리로 끝나는 경우.
                - AddressCls.ROAD_END_ADDRESS: 도로명으로 끝나는 경우.
                - AddressCls.H4_END_ADDRESS: 동으로 끝나는 경우.
                - AddressCls.H23_END_ADDRESS: 시군구로 끝나는 경우.
                - AddressCls.H1_END_ADDRESS: 광역시로 끝나는 경우.

                - AddressCls.UNRECOGNIZABLE_ADDRESS: 인식할 수 없는 주소인 경우.
        """
        if len(toks) == 0:
            return AddressCls.NOT_ADDRESS

        # if len(toks) < 3 and toks.get(0).t != TOKEN_ROAD:
        #     return AddressCls.NOT_ADDRESS

        if toks.hasTypes(TOKEN_ROAD) and toks.hasTypes(TOKEN_BLDNO):
            return AddressCls.ROAD_ADDRESS

        if toks.hasTypes(TOKEN_BNG):
            return AddressCls.JIBUN_ADDRESS

        if toks.hasTypes(TOKEN_BLD):
            return AddressCls.BLD_ADDRESS

        if toks.hasTypes(TOKEN_ROAD):
            return AddressCls.ROAD_END_ADDRESS

        if toks.hasTypes(TOKEN_RI):
            return AddressCls.RI_END_ADDRESS

        if toks.hasTypes(TOKEN_H4):
            return AddressCls.H4_END_ADDRESS

        if toks.hasTypes(TOKEN_H23):
            return AddressCls.H23_END_ADDRESS

        if toks.hasTypes(TOKEN_H1):
            return AddressCls.H1_END_ADDRESS

        return AddressCls.UNRECOGNIZABLE_ADDRESS

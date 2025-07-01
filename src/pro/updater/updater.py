import json
import logging
import threading
from cachetools import LRUCache

from src.geocoder.geocoder import Geocoder
from src.geocoder.util.HSimplifier import HSimplifier
from src.geocoder.util.BldSimplifier import BldSimplifier
from src.geocoder.util.hcodematcher import HCodeMatcher

import src.config as config

# max_len = 0


class DbCreateContext:
    def __init__(self, val, val_json, daddr):
        self.val = val
        self.val_json = val_json
        self.daddr = daddr

        if " " in daddr.get("h23_nm", ""):
            self.daddr["h2_nm"], self.daddr["h3_nm"] = daddr.get("h23_nm", "").split()
        else:
            self.daddr["h2_nm"] = daddr.get("h23_nm", "")
            self.daddr["h3_nm"] = ""

        self.bld_reg = daddr.get("bld_reg", "")
        self.bld_nm_text = daddr.get("bld_nm_text", "")
        self.bld_nm = daddr.get("bld_nm", "")


class UpdaterLogFilter(logging.Filter):
    """
    This filter only show log entries for specified thread name
    """

    def __init__(self, thread_name, *args, **kwargs):
        logging.Filter.__init__(self, *args, **kwargs)
        self.thread_name = thread_name

    def filter(self, record):
        return record.threadName == self.thread_name


CACHE_SIZE = 1000


class BaseUpdater:
    JUSO_DATA_DIR = config.JUSO_DATA_DIR

    def __init__(self, geocoder: Geocoder):
        if geocoder:
            self.ldb = geocoder.db
        self.geocoder = geocoder
        self.hSimplifier = HSimplifier()
        self.bldSimplifier = BldSimplifier()
        self.hcodeMatcher = HCodeMatcher()

        self.db_cache = LRUCache(maxsize=CACHE_SIZE)  # LRU 캐시 추가

    # 캐시된 get 메소드 추가
    def get_cached(self, key):
        """
        RocksDB에서 데이터를 가져올 때 LRU 캐시를 적용한 메소드
        """
        try:
            # 캐시에서 먼저 확인
            if key in self.db_cache:
                return self.db_cache[key]

            # 캐시에 없으면 DB에서 가져오기
            v = self.ldb.get(key)

            val = None
            # 값이 있으면 캐시에 저장
            if v is not None:
                val = json.loads(v.decode())
                self.db_cache[key] = val

            return val
        except Exception as e:
            logging.error(f"Error in get_cached: {str(e)}")
            return None

    # 캐시 무효화 메소드 (필요시 사용)
    def invalidate_cache(self, key=None):
        """
        특정 키 또는 전체 캐시를 무효화
        """
        if key is None:
            self.db_cache.clear()
        elif key in self.db_cache:
            del self.db_cache[key]

    def _stop_updater_logging(self):
        # Remove thread log handler from root logger
        logging.getLogger().removeHandler(self.log_handler)

        # Close the thread log handler so that the lock on log file can be released
        self.log_handler.close()

    def _prepare_updater_logger(self, file_name="update.log"):
        """
        Add a log handler to separate file for current thread
        """
        thread_name = threading.current_thread().name

        self.logger = logging.Logger(__name__)

        formatter = logging.Formatter("%(asctime)-15s - %(levelname)s - %(message)s")
        log_file = f"{self.outpath}{file_name}"

        log_handler = logging.FileHandler(log_file)
        log_handler.setLevel(logging.DEBUG)
        log_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)

        log_filter = UpdaterLogFilter(thread_name)
        log_handler.addFilter(log_filter)
        self.log_handler = log_handler
        self.logger.addHandler(log_handler)
        self.logger.addHandler(console_handler)

        # main thread logger를 사용하지 않고 현재 thread의 logger를 사용하도록 설정. 2025.05.28
        # log file에 기록되지 않는 문제를 해결하기 위함.

    # def _bld_nm_merge(self, bld_reg, bld_nm_text, bld_nm):
    #     merge_list = []

    #     if bld_reg:
    #         bld_reg = bld_reg.replace(" ", "")
    #     if bld_nm_text:
    #         bld_nm_text = bld_nm_text.replace(" ", "")
    #     if bld_nm:
    #         bld_nm = bld_nm.replace(" ", "")

    #     if bld_reg:
    #         merge_list.append(bld_reg.strip())
    #     if bld_nm_text and bld_nm_text not in merge_list:
    #         merge_list.append(bld_nm_text.strip())
    #     if bld_nm and bld_nm not in merge_list:
    #         merge_list.append(bld_nm.strip())

    #     return " ".join(merge_list).replace("  ", " ").strip()

    def _bld_nm_merge(self, bld_reg, bld_nm_text, bld_nm):
        """
        Merge building name variants into a single string.
        Removes duplicate entries and extra spaces.
        """
        merge_list = []

        # Process each name, removing spaces and checking for duplicates
        for name in [bld_reg, bld_nm_text, bld_nm]:
            if name:  # Check if not None or empty
                processed_name = name.replace(" ", "").strip()
                if processed_name and processed_name not in merge_list:
                    merge_list.append(processed_name)

        # Join with spaces and normalize multiple spaces
        return " ".join(merge_list)

    def update_record(
        self,
        daddr: dict,
        merge_if_exists=True,
        extras: dict = {},
        batch=None,
        fast_giveup=False,
    ):
        add_count = 0

        daddr["bld_name_merged"] = self._bld_nm_merge(
            daddr.get("bld_reg", ""),
            daddr.get("bld_nm_text", ""),
            daddr.get("bld_nm", ""),
        )
        daddr["bm"] = daddr["bld_name_merged"]
        daddr["hd_cd"] = daddr["hd_cd"] or ""

        h23_cd = (
            daddr.get("h23_cd") or daddr.get("ld_cd", "")[:5] or daddr["bld_mgt_no"][:5]
        )
        # 최신 시군구 코드로 변경
        current_h23_cd = self.hcodeMatcher.get_h23_cd(h23_cd)

        road_cd = daddr.get("road_cd")
        if daddr.get("road_cd") and not daddr.get("road_cd").startswith(
            (h23_cd, current_h23_cd)
        ):
            road_cd = f"{current_h23_cd}{road_cd}"

        # db val 제작
        val = {
            "x": (
                int(float(daddr["bld_x"])) if daddr["bld_x"] else None
            ),  # /*948429.250775*/
            "y": (
                int(float(daddr["bld_y"])) if daddr["bld_y"] else None
            ),  # /*1946421.0241*/
            "z": daddr["zip"],  # /*07309*/
            "h23_cd": current_h23_cd,
            "hd_cd": self.hcodeMatcher.get_current_hd_cd(daddr["hd_cd"]),
            "ld_cd": self.hcodeMatcher.get_current_ld_cd(
                daddr["ld_cd"]
            ),  # /*1156013200*/
            "road_cd": self.hcodeMatcher.get_current_road_cd(
                road_cd
            ),  # /*115604154734*/
            "bld_mgt_no": daddr.get("bld_mgt_no"),  # /*1156013200103420049010058*/
            "h1_nm": self.hSimplifier.h1Hash(
                daddr["h1_nm"]
            ),  # 광역시도명. hash 충돌시 사용
            "h23_nm": daddr.get("h23_nm", ""),
            "hd_nm": daddr["hd_nm"],  # 행정동명
            "ld_nm": daddr["ld_nm"],  # 법정동명
            "ri_nm": daddr.get("ri_nm"),  # 리명
            "road_nm": daddr.get("road_nm"),  # 길이름. hash 충돌시 사용
            "bm": self._bld_nm_list(
                daddr.get("bld_reg"), daddr.get("bld_nm_text"), daddr.get("bld_nm")
            ),  # 건물명. hash 충돌시 사용
            "san": daddr.get("san"),  # 산 여부
            "bng1": daddr.get("bng1"),  # 번지
            "bng2": daddr.get("bng2"),  # 부번지
            "undgrnd_yn": daddr.get("undgrnd_yn"),  # 지하 여부
            "bld_x": daddr.get("bld_x"),  # /*948429.250775*/
            "bld_y": daddr.get("bld_y"),  # /*1946421.0241*/
        }
        if extras:
            val["extras"] = extras

        val_json = json.dumps(val).encode()
        self.ctx = DbCreateContext(val, val_json, daddr)

        # 지번 주소. ("리" 제외한 hash 생성. 충돌시 "리" 검사)
        ## 법정동 번지
        if daddr["ld_nm"] and daddr["bng1"]:
            add_count += self._merge_address_multi(
                [
                    ("h23_nm", "ld_nm", "ri_nm", "san", "bng1", "bng2"),
                    ("ld_nm", "ri_nm", "san", "bng1", "bng2"),
                    ("ri_nm", "san", "bng1", "bng2") if daddr["ri_nm"] else (),
                ],
                merge_if_exists,
                batch=batch,
                fast_giveup=fast_giveup,
            )

            # 건물 주소
            if daddr["bld_name_merged"]:
                add_count += self._merge_bld_address_multi(
                    [
                        ("h23_nm", "ri_nm", "san", "bng1", "bng2", "bm"),
                        ("h23_nm", "ld_nm", "ri_nm", "san", "bng1", "bng2", "bm"),
                        ("ld_nm", "ri_nm", "san", "bng1", "bng2", "bm"),
                        (
                            ("ri_nm", "san", "bng1", "bng2", "bm")
                            if daddr["ri_nm"]
                            else ()
                        ),
                    ],
                    merge_if_exists,
                    batch=batch,
                )

        ## 행정동 번지
        if daddr["hd_nm"] and daddr["bng1"]:
            add_count += self._merge_address_multi(
                [
                    ("h23_nm", "hd_nm", "ri_nm", "san", "bng1", "bng2"),
                    ("hd_nm", "ri_nm", "san", "bng1", "bng2"),
                    ("ri_nm", "san", "bng1", "bng2") if daddr["ri_nm"] else (),
                ],
                merge_if_exists,
                batch=batch,
                fast_giveup=fast_giveup,
            )

            if daddr["bld_name_merged"]:
                add_count += self._merge_bld_address_multi(
                    [
                        ("h23_nm", "ri_nm", "san", "bng1", "bng2", "bm"),
                        ("h23_nm", "hd_nm", "ri_nm", "san", "bng1", "bng2", "bm"),
                        ("hd_nm", "ri_nm", "san", "bng1", "bng2", "bm"),
                        (
                            ("ri_nm", "san", "bng1", "bng2", "bm")
                            if daddr["ri_nm"]
                            else ()
                        ),
                    ],
                    merge_if_exists,
                    batch=batch,
                )

        # 도로명 주소
        # 길이름 건물번호 (집합건물 아님)
        if daddr.get("road_nm"):  # 도로명 주소
            add_count += self._merge_address_multi(
                [
                    ("h23_nm", "ri_nm", "road_nm", "undgrnd_yn", "bld1", "bld2"),
                    (
                        (
                            "h23_nm",
                            "ld_nm",
                            "ri_nm",
                            "road_nm",
                            "undgrnd_yn",
                            "bld1",
                            "bld2",
                        )
                        if daddr["ld_nm"]
                        else ()
                    ),
                    (
                        (
                            "h23_nm",
                            "hd_nm",
                            "ri_nm",
                            "road_nm",
                            "undgrnd_yn",
                            "bld1",
                            "bld2",
                        )
                        if daddr["hd_nm"]
                        else ()
                    ),
                    (
                        ("ld_nm", "ri_nm", "road_nm", "undgrnd_yn", "bld1", "bld2")
                        if daddr["ld_nm"]
                        else ()
                    ),
                    (
                        ("hd_nm", "ri_nm", "road_nm", "undgrnd_yn", "bld1", "bld2")
                        if daddr["hd_nm"]
                        else ()
                    ),
                    (
                        ("ri_nm", "road_nm", "undgrnd_yn", "bld1", "bld2")
                        if daddr["ri_nm"]
                        else ()
                    ),
                    ("road_nm", "undgrnd_yn", "bld1", "bld2"),
                ],
                merge_if_exists,
                batch=batch,
                fast_giveup=fast_giveup,
            )

        ## 번지 없는 지번주소 건물. 시군구 + 건물명 hash 생성.
        if daddr["bld_name_merged"] and not self.bldSimplifier.is_general_name(
            daddr["bld_name_merged"]
        ):
            add_count += self._merge_bld_address_multi(
                [
                    ("h23_nm", "ld_nm", "ri_nm", "bm") if daddr["ld_nm"] else (),
                    ("h23_nm", "hd_nm", "ri_nm", "bm") if daddr["hd_nm"] else (),
                    ("ld_nm", "ri_nm", "bm") if daddr["ld_nm"] else (),
                    ("hd_nm", "ri_nm", "bm") if daddr["hd_nm"] else (),
                    # ("h23_nm", "ri_nm", "bm"), # 너무 일반적이라 생략. 202506 ex) 부산진_국민
                    # ("ri_nm", "bm") if daddr["ri_nm"] else (), # 너무 일반적이라 생략. 202506 ex) 부산진_국민
                ],
                merge_if_exists,
                batch=batch,
            )

        # 건물번호 없는 도로명 주소 추가
        if (
            daddr["bld_name_merged"]
            and daddr.get("road_nm")
            and not self.bldSimplifier.is_general_name(daddr["bld_name_merged"])
        ):
            add_count += self._merge_bld_address_multi(
                [
                    # 횡성군 (안흥리) 서동로 안흥성당
                    ("h23_nm", "ri_nm", "road_nm", "bm"),
                    (
                        # 횡성군 안흥면 (안흥리) 서동로 안흥성당
                        ("h23_nm", "hd_nm", "ri_nm", "road_nm", "bm")
                        if daddr["hd_nm"]
                        else ()
                    ),
                    # 횡성군 안흥면 (안흥리) 서동로 안흥성당
                    (
                        ("h23_nm", "ld_nm", "ri_nm", "road_nm", "bm")
                        if daddr["ld_nm"]
                        else ()
                    ),
                    # 안흥면 (안흥리) 서동로 안흥성당
                    ("ld_nm", "ri_nm", "road_nm", "bm") if daddr["ld_nm"] else (),
                    # 안흥면 (안흥리) 서동로 안흥성당
                    ("hd_nm", "ri_nm", "road_nm", "bm") if daddr["hd_nm"] else (),
                    # (안흥리) 서동로 안흥성당
                    ("ri_nm", "road_nm", "bm") if daddr["ri_nm"] else (),
                    # 횡성군 (안흥리) 안흥성당
                    # ("h23_nm", "ri_nm", "bm"), # 너무 일반적이라 생략. 202506 ex) 부산진_국민
                    ("road_nm", "bm"),
                ],
                merge_if_exists,
                batch=batch,
            )

        return add_count

    def _make_address_string(self, daddr, keys):
        """컬럼값을 조합하여 주소 제작"""

        alist = []
        for k in keys:
            if k in (
                "h1_nm",
                "h23_nm",
                "ld_nm",
                "ri_nm",
                "road_nm",
                "bld1",
                "bng1",
                # "bld_reg",
                # "bld_nm_text",
                "bm",
            ):
                alist.append(daddr[k])
            elif k in ("h2_nm", "h3_nm") and "h23_nm" not in keys:
                alist.append(daddr[k])
            elif k == "hd_nm":
                hd_nm = self.hSimplifier.h4Hash(daddr[k], keep_dong=True)
                alist.append(hd_nm)
            elif k == "undgrnd_yn" and daddr[k] == "1":
                alist.append("지하")
            elif k == "san" and daddr[k] == "1":
                alist.append("산")
            elif (k == "bld2" or k == "bng2") and daddr[
                k
            ] != "0":  # 부번지 또는 건물부번
                alist.append(alist.pop() + "-" + daddr[k])
            # else:
            #     logging.debug(f"Ignored key in address: {k}: {daddr[k]}")

        return " ".join(alist).replace("  ", " ").strip()

    def _has_all_bld(self, blds0, blds):
        for bld in blds:
            if bld not in blds0:
                return False
        return True

    def _has_xy(self, val0):
        for val in val0:
            if val["x"]:
                return True

        return False

    def _compare_for_fix_xy(self, val1, val2) -> bool:
        # h23_cd가 둘 다 있으며 일치해야 함
        if val1.get("h23_cd", "val1_dummy") != val2.get("h23_cd", "val2_dummy"):
            return False

        # 한쪽이라도 법정동 있으면 같아야 함
        if val1.get("ld_cd", "val1_dummy") != val2.get("ld_cd", "val2_dummy"):
            return False

        # 한쪽이라도 행정동 있으면 같아야 함
        if val1.get("hd_cd", "val1_dummy") != val2.get("hd_cd", "val2_dummy"):
            return False

        # 한쪽이라도 리 있으면 같아야 함
        if val1.get("ri_nm", "val1_dummy") != val2.get("ri_nm", "val2_dummy"):
            return False

        return True

    def _fix_xy(self, val0: list, newval: dict) -> bool:
        """
        좌표가 누락된 기존 데이터의 좌표 업데이트

        Args:
            val0 (list): A list of dictionaries containing x and y values.
            newval (dict): A dictionary containing x and y values.

        Returns:
            bool: True if any x or y values were fixed, False otherwise.
        """
        is_xy_fix = False
        if not val0:
            return False

        if not newval["x"]:  # newval의 비어있는 좌표를 채우기
            # 기존 데이터 중 h23_cd가 둘 다 있으며 일치하고 좌표가 있는 것 선택
            # 한쪽이라도 법정동 있으면 같아야 함
            # 한쪽이라도 행정동 있으면 같아야 함
            # 한쪽이라도 리 있으면 같아야 함
            for val in val0:
                if val["x"] and self._compare_for_fix_xy(val, newval):
                    newval["x"] = val["x"]
                    newval["y"] = val["y"]
                    newval["bld_x"] = val["bld_x"]
                    newval["bld_y"] = val["bld_y"]
                    is_xy_fix = True
                    break

        else:  # 기존 데이터의 비어있는 좌표를 채우기
            # get xy
            x = newval["x"]
            y = newval["y"]
            bld_x = newval.get("bld_x") or x
            bld_y = newval.get("bld_y") or y

            for val in val0:
                # 최소한의 안전장치로 h23_cd가 둘 다 있으며 일치하는지 확인. ex)'중앙_76-18'
                if not val["x"] and self._compare_for_fix_xy(val, newval):
                    val["x"] = x
                    val["y"] = y
                    val["bld_x"] = bld_x
                    val["bld_y"] = bld_y
                    is_xy_fix = True

        return is_xy_fix

    def _has_val(self, val0, newval):
        for val in val0:
            # ld_cd 비교에서 제외. 과도한 지번 주소 추가 방지
            if all(
                val.get(k) == v
                for k, v in newval.items()
                if v and k not in {"x", "y", "z", "bld_x", "bld_y", "extras", "ld_cd"}
            ):
                return True
            # # 광역시도와 길이름이 같고
            # if val["h1"] == newval["h1"] and val["rm"] == newval["rm"]:
            #     # 건물명이 이미 모두 있으면
            #     if self._has_all_bld(val.get("bm", []), newval.get("bm", [])):
            #         return True

        return False

    def _merge_address_multi(
        self, keys_list, merge_if_exists=True, batch=None, fast_giveup=False
    ):
        add_count = 0
        for keys in keys_list:
            if not keys:
                continue
            n = self._merge_address(keys, merge_if_exists, batch=batch)
            if n == 0 and fast_giveup:
                return 0
            else:
                fast_giveup = False  # fast_giveup은 처음에만 적용

            add_count += n

            if "h23_nm" in keys and self.ctx.daddr["h3_nm"]:
                # h23_nm이 있고 h3_nm이 있으면 h2_nm, h3_nm도 추가
                tmplist = list(keys)
                tmplist.remove("h23_nm")
                tmplist.insert(0, "h2_nm")
                add_count += self._merge_address(tmplist, merge_if_exists, batch=batch)

                tmplist = list(keys)
                tmplist.remove("h23_nm")
                tmplist.insert(0, "h3_nm")
                add_count += self._merge_address(tmplist, merge_if_exists, batch=batch)

        return add_count

    def _merge_address(self, keys, merge_if_exists=True, batch=None):
        """주소를 만들어 hash 추가"""
        add_count = 0

        address = self._make_address_string(self.ctx.daddr, keys)
        if address == "":
            return add_count

        # print(address)
        if self._del_and_put(address, merge_if_exists, batch=batch):
            add_count += 1

        # 'ri_nm'을 제외한 key 생성
        if "ri_nm" in keys and self.ctx.daddr["ri_nm"]:
            tmplist = list(keys)
            tmplist.remove("ri_nm")
            address = self._make_address_string(self.ctx.daddr, tuple(tmplist))

            # 번지로 시작하는 주소는 추가 안 함
            if (
                address != ""
                and not address[0].isnumeric()
                and address[0] != "산"
                and address[0:2] != "지하"
            ):
                if self._del_and_put(address, batch=batch):
                    add_count += 1

        return add_count

    def _merge_bld_address_multi(self, keys_list, merge_if_exists=True, batch=None):
        add_count = 0
        for keys in keys_list:
            if not keys:
                continue
            add_count += self._merge_bld_address(keys)

            if "h23_nm" in keys and self.ctx.daddr["h3_nm"]:
                # h23_nm이 있고 h3_nm이 있으면 h2_nm, h3_nm도 추가
                tmplist = list(keys)
                tmplist.remove("h23_nm")
                tmplist.insert(0, "h2_nm")
                add_count += self._merge_bld_address(
                    tmplist, merge_if_exists, batch=batch
                )

                tmplist = list(keys)
                tmplist.remove("h23_nm")
                tmplist.insert(0, "h3_nm")
                add_count += self._merge_bld_address(
                    tmplist, merge_if_exists, batch=batch
                )

        return add_count

    def _merge_bld_address(self, keys, merge_if_exists=True, batch=None):
        """건물명을 분리하고 주소를 만들어 hash 추가

        원본 건물명에 여러 건물명이 포함된 경우가 있다.
        예)1,2,3,4,5동
        예)105동 관리사무소
        예)10동 학생회관
        """
        add_count = 0
        address = self._make_address_string(self.ctx.daddr, keys)

        # 건물명이 포함된 hash가 만들어져야 함
        if self._del_and_put_must_have_bld(address, merge_if_exists, batch=batch):
            add_count += 1

        # if "bm" in keys and self.ctx.daddr.get("bld_name_merged"):
        #     # 공백 또는 쉼표로 분리. TODO: 더 추가해야 함
        #     bld_names = re.split(r"\s|,", self.ctx.daddr["bld_name_merged"])
        #     for bld in bld_names:
        #         # print(address + ' ' + bld)
        #         if self._del_and_put(address + " " + bld):
        #             add_count += 1

        return add_count

    def _bld_nm_list(self, bld_reg, bld_nm_text, bld_nm):
        result = [bld_reg, bld_nm_text, bld_nm]
        # 빈 값 제거
        return [item for item in result if item]
        # result = []
        # if bld_reg:
        #     result.append(self.bldSimplifier.simplifyBldName(bld_reg))
        # if bld_nm_text and bld_nm_text not in result:
        #     result.append(self.bldSimplifier.simplifyBldName(bld_nm_text))
        # if bld_nm and bld_nm not in result:
        #     result.append(self.bldSimplifier.simplifyBldName(bld_nm))
        # return result

    def _del_and_put_must_have_bld(
        self, address, merge_if_exists=True, force_delete=False, batch=None
    ):
        hash, toks, addressCls, errmsg = self.geocoder.addressHash(address)
        if addressCls != self.geocoder.BLD_ADDRESS:
            logging.debug(f"Address {address} does not have a building name.")
            return 0

        return self._del_and_put(
            address, merge_if_exists, force_delete=force_delete, batch=batch
        )

    def _del_and_put(
        self, address, merge_if_exists=True, force_delete=False, batch=None
    ):
        hash, _, _, err_msg = self.geocoder.addressHash(address)

        if len(hash) < 2:
            logging.debug(f"Invalid address hash: {hash} for {address}")
            return 0

        key = hash.encode()
        if force_delete:
            self.ldb.delete(key)
            self.invalidate_cache(key)  # 캐시도 함께 삭제

        added = False
        val = []
        if key != b"":
            try:
                val = self.get_cached(key) or []
                if val and merge_if_exists == False:
                    return False
            except:
                val = []

            if not isinstance(val, list):
                val = [val]

            cur_len = len(val)

            if cur_len > 500:
                print(cur_len, f"[{hash}]", address, self.ctx.daddr)

            if cur_len > 1000:
                logging.warning(
                    f"Hash {hash} for {address} has too many entries ({cur_len}). "
                )
                return 0

            # 좌표가 없으면 업데이트
            # if not self._has_xy(val) and self.ctx.val["x"]:
            #     do_nothing = 1
            modified = self._fix_xy(val, self.ctx.val)

            # 없으면 추가
            if val == [] or not self._has_val(val, self.ctx.val):
                val.append(self.ctx.val)
                modified = True
                added = True

            # 캐시 업데이트
            if modified:
                newval = json.dumps(val).encode("utf8")
                if batch:
                    batch.put(key, newval)
                else:
                    self.ldb.put(key, newval)
                self.db_cache[key] = val

        return added

    def write_batch(self, batch):
        """
        Writes a batch of operations to the database.

        Args:
            batch (rocksdb3.WriteBatch): The batch of operations to write.
        """
        self.ldb.write_batch(batch)

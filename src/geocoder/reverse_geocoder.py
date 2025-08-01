import os
import json
import csv
import geohash
from polygon_geohasher.polygon_geohasher import polygon_to_geohashes

import pyogrio

# from fiona import transform

# from shapely import geometry
import shapely
from shapely import wkt
from shapely.geometry import (
    shape,
    mapping,
    Point,
    LineString,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon,
    GeometryCollection,
)
from shapely.ops import transform

import pyproj
from pyproj import Transformer
import logging

from .db.gimi9_rocks import Gimi9RocksDB

# from .db.rocksdb import RocksDbGeocode

from .util.pnumatcher import PNUMatcher
from .util.roadmatcher import RoadMatcher
import src.config as config

# 생성
# 검색
# 업데이트


def _round_coordinates_to_precision(geometry, precision):
    """
    Shapely 지오메트리 객체의 모든 좌표를 지정된 소수점 정밀도로 반올림합니다.
    """
    if geometry.is_empty:
        return geometry

    if geometry.geom_type == "Point":
        return Point(round(geometry.x, precision), round(geometry.y, precision))
    elif geometry.geom_type == "LineString":
        coords = [
            (round(x, precision), round(y, precision)) for x, y in geometry.coords
        ]
        return LineString(coords)
    elif geometry.geom_type == "Polygon":
        exterior_coords = [
            (round(x, precision), round(y, precision))
            for x, y in geometry.exterior.coords
        ]
        interiors = []
        for interior in geometry.interiors:
            interiors.append(
                [(round(x, precision), round(y, precision)) for x, y in interior.coords]
            )
        return Polygon(exterior_coords, interiors if interiors else None)
    elif geometry.geom_type in [
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
        "GeometryCollection",
    ]:
        # 재귀적으로 각 서브-지오메트리에 대해 함수를 호출합니다.
        geometries = [
            _round_coordinates_to_precision(part, precision) for part in geometry.geoms
        ]
        if geometry.geom_type == "MultiPoint":
            return MultiPoint(geometries)
        elif geometry.geom_type == "MultiLineString":
            return MultiLineString(geometries)
        elif geometry.geom_type == "MultiPolygon":
            return MultiPolygon(geometries)
        elif geometry.geom_type == "GeometryCollection":
            return GeometryCollection(geometries)
    return geometry  # 지원하지 않는 지오메트리 타입은 그대로 반환


class ReverseGeocoder:
    """
    ReverseGeocoder 클래스는 주어진 좌표를 이용하여 주소를 검색하고 변환하는 기능을 제공합니다.

    Attributes:
        pnu_matcher (PNUMatcher): PNU 매처 객체.
        road_matcher (RoadMatcher): 도로 매처 객체.
        GEOHASH_PRECISION (int): Geohash 정밀도.
        db (object): 데이터베이스 객체.
        log_handler (logging.FileHandler): 로그 핸들러.

    Methods:
        __init__(db):
            ReverseGeocoder 객체를 초기화합니다.

        get_latest_addrs(addrs, shp_type):
            주어진 주소 목록에서 최신 주소를 반환합니다.

        search(x, y):
            주어진 좌표를 이용하여 주소를 검색합니다.

        convert_bld(addr, g_wkt):
            건물 주소를 변환합니다.

        convert_pnu(addr, g_wkt):
            PNU 주소를 변환합니다.

        update_bld_hash(feature, proj_transform):
            건물 해시를 업데이트합니다.

        update_pnu_hash(feature, proj_transform):
            PNU 해시를 업데이트합니다.

        update_geometry(pnu_or_adr_mng_no, geom):
            지오메트리를 업데이트합니다.

        update_bld_db(h, property_dict):
            건물 데이터베이스를 업데이트합니다.

        update_pnu_db(h, property_dict):
            PNU 데이터베이스를 업데이트합니다.

        geom_contains_point(geom, x, y):
            지오메트리가 주어진 점을 포함하는지 확인합니다.

        geom_contains_geohash_centroid(geom, h):
            지오메트리가 주어진 geohash 중심점을 포함하는지 확인합니다.

        get_data_yyyymm(shp_path):
            주어진 shp 파일 경로에서 yyyymm 데이터를 추출합니다.

        update_bld(shp_path):
            주어진 shp 파일을 이용하여 건물 데이터를 업데이트합니다.

        update_pnu(shp_path):
            주어진 shp 파일을 이용하여 PNU 데이터를 업데이트합니다.
    """

    pnu_matcher = PNUMatcher()
    road_matcher = RoadMatcher()
    GEOHASH_PRECISION = 8
    HD_GEOHASH_PRECISION = 7

    def __init__(self):
        self.db = Gimi9RocksDB(config.REVERSE_GEOCODE_DB, read_only=config.READONLY)

        self.hd_db = Gimi9RocksDB(config.HD_HISTORY_DB, read_only=config.READONLY)

    # def open(self, db):
    #     self.db = db

    def get_region(
        self, type: str, region_cd: str, yyyymm: str = None, slim: bool = False
    ):
        """
        주어진 행정동 코드에 대한 행정동 정보를 검색합니다.
        """
        PRECISION: int = 6

        region_key = f"{type}-{yyyymm}-{region_cd}"
        region = self.hd_db.get(region_key.encode())
        if region:
            val = json.loads(region)

            geom = wkt.loads(val.get("wkt", ""))
            # 2. 지오메트리 객체의 좌표 정밀도 변경
            val["wkt"] = wkt.dumps(geom, rounding_precision=PRECISION)

            # rounded_geom = _round_coordinates_to_precision(geom, precision=PRECISION)

            if type == "hd":
                if slim:
                    val["name"] = val.pop("EMD_KOR_NM", "")
                    val["code"] = val.pop("EMD_CD", "")
                    val.pop("EMD_ENG_NM", "")
                else:
                    val["name"] = val.get("EMD_KOR_NM", "")
                    val["code"] = val.get("EMD_CD", "")

            elif type == "h23":
                if slim:
                    val["name"] = val.pop("SIG_KOR_NM", "")
                    val["code"] = val.pop("SIG_CD", "")
                    val.pop("SIG_ENG_NM", "")
                else:
                    val["name"] = val.get("SIG_KOR_NM", "")
                    val["code"] = val.get("SIG_CD", "")

            elif type == "h1":
                if slim:
                    val["name"] = val.pop("CTP_KOR_NM", "")
                    val["code"] = val.pop("CTPRVN_CD", "")
                    val.pop("CTP_ENG_NM", "")
                else:
                    val["name"] = val.get("CTP_KOR_NM", "")
                    val["code"] = val.get("CTPRVN_CD", "")

            val["success"] = True

            return val

    def search_region(self, type: str, x: float, y: float, yyyymm: str = None):
        """
        주어진 좌표 (x, y)에 대한 행정동 이력을 검색합니다.

        Args:
            x (float): x 좌표 (경도).
            y (float): y 좌표 (위도).

        Returns:
            list: 행정동 정보
        """

        try:
            # 행정동 hash 검색
            key = geohash.encode(y, x, precision=self.HD_GEOHASH_PRECISION)

            o = self.hd_db.get(key.encode())
            if o:
                hd_list = json.loads(o)
                for hd_item in hd_list:
                    if (
                        yyyymm
                        and yyyymm <= config.HD_HISTORY_END_YYYYMM
                        and yyyymm >= config.HD_HISTORY_START_YYYYMM
                    ):
                        if (
                            yyyymm < hd_item["from_yyyymm"]
                            or yyyymm > hd_item["to_yyyymm"]
                        ):
                            # yyyymm이 범위에 포함되지 않으면 제외
                            continue

                    # contains test
                    geom = shapely.from_wkt(hd_item.get("intersection_wkt", ""))
                    if self.geom_contains_point(geom, x, y):
                        if yyyymm >= hd_item.get(
                            "from_yyyymm"
                        ) and yyyymm <= hd_item.get("to_yyyymm"):
                            region_cd = hd_item["EMD_CD"]
                            if type == "hd":
                                # 행정동 코드로 검색
                                region_cd = region_cd  # 행정동 코드로 변환
                            elif type == "h23":
                                # 시군구 코드로 검색
                                region_cd = region_cd[:5]  # 시군구 코드로 변환
                            elif type == "h1":
                                # 도/특별시/광역시 코드로 검색
                                region_cd = region_cd[:2]
                            else:
                                raise ValueError(f"Unknown type: {type}")

                            result = self.get_region(type, region_cd, yyyymm)
                            result.update(
                                {
                                    "success": True,
                                }
                            )
                            return result

        except Exception as e:
            return {"success": False}

        return {"success": False}

    def search_hd_history(
        self,
        x: float,
        y: float,
        yyyymm: str = None,
        full_history_list: bool = False,
    ):
        """
        주어진 좌표 (x, y)에 대한 행정동 이력을 검색합니다.

        Args:
            x (float): x 좌표 (경도).
            y (float): y 좌표 (위도).

        Returns:
            list: 행정동 이력 정보 리스트. 성공 시 이력 정보를 포함하며,
                실패 시 빈 리스트를 반환합니다.
        """
        result = []
        try:
            key = geohash.encode(y, x, precision=self.HD_GEOHASH_PRECISION)
            o = self.hd_db.get(key.encode())
            if o:
                hd_list = json.loads(o)

                for hd_item in hd_list:
                    if (
                        yyyymm
                        and yyyymm <= config.HD_HISTORY_END_YYYYMM
                        and yyyymm >= config.HD_HISTORY_START_YYYYMM
                    ):
                        if (
                            yyyymm < hd_item["from_yyyymm"]
                            or yyyymm > hd_item["to_yyyymm"]
                        ):
                            # yyyymm이 범위에 포함되지 않으면 제외
                            continue

                    # contains test
                    geom = shapely.from_wkt(hd_item.get("intersection_wkt", ""))
                    if self.geom_contains_point(geom, x, y):
                        hd_item.pop("intersection_wkt", None)  # WKT 제거
                        if full_history_list:
                            # 전체 이력 리스트를 반환할 경우
                            result.extend(self.full_hd_list(hd_item))
                        else:
                            result.append(hd_item)
                # sort by to_yyyymm desc order
                result.sort(
                    key=lambda hd_item: hd_item.get("to_yyyymm", ""), reverse=True
                )
                return result
        except Exception as e:
            return result

        return result

    def full_hd_list(self, hd_item):
        """
        주어진 행정동 이력 정보를 기반으로 전체 이력 리스트를 생성합니다.

        Args:
            hd_item (dict): 행정동 이력 정보 딕셔너리.

        Returns:
            list: 전체 이력 정보를 포함하는 리스트.
        """

        def next(yyyymm):
            """
            주어진 yyyymm 문자열에서 다음 월을 반환합니다.
            """
            year = int(yyyymm[:4])
            month = int(yyyymm[4:6])
            if month == 12:
                return f"{year + 1}01"
            else:
                return f"{year}{month + 1:02d}"

        result = []
        from_yyyymm = hd_item.get("from_yyyymm", "")
        to_yyyymm = hd_item.get("to_yyyymm", "")
        if from_yyyymm and to_yyyymm:
            yyyymm = from_yyyymm
            while yyyymm <= to_yyyymm:
                item = hd_item.copy()
                item["yyyymm"] = yyyymm
                result.append(item)
                yyyymm = next(yyyymm)
        return result

    def get_latest_addrs(self, addrs, shp_type):
        """
        주어진 주소 목록에서 shp_type에 해당하는 최신 주소를 반환합니다.

        Args:
            addrs (list): 주소 목록. 각 주소는 딕셔너리 형태로 되어 있으며,
                          shp_type과 yyyymm 키를 포함해야 합니다.
            shp_type (str): 주소에서 확인할 shp_type 키.

        Returns:
            list: shp_type에 해당하는 최신 주소들로 구성된 리스트.
        """
        latest_addr = {}
        for addr in addrs:
            if shp_type in addr:
                key = addr[shp_type]
                yyyymm = addr["yyyymm"]
                if not latest_addr.get(key) or yyyymm > latest_addr.get(key)["yyyymm"]:
                    latest_addr[key] = addr
        return list(latest_addr.values())

    def search(self, x: float, y: float):
        """
        주어진 좌표 (x, y)에 대한 역 지오코딩을 수행합니다.

        Args:
            x (float): x 좌표 (경도).
            y (float): y 좌표 (위도).

        Returns:
            dict: 역 지오코딩 결과를 포함하는 딕셔너리. 성공 시 변환된 주소 정보를 포함하며,
                  실패 시 {"success": False, "errmsg": "NOTFOUND ERROR"}를 반환합니다.
        """
        key = geohash.encode(y, x, precision=self.GEOHASH_PRECISION)
        result = {}
        try:
            o = self.db.get(key.encode())
            if not o:
                return {"success": False, "errmsg": "NOTFOUND ERROR"}

            addrs = json.loads(o)

            # 건물도형이 여러개인 경우 hit test로 정확한 주소를 찾음
            # 건물도형이 하나만 검색되어도 hit test로 체크
            latest_addrs = self.get_latest_addrs(addrs, "ADR_MNG_NO")
            for addr in latest_addrs:
                g = self.db.get(addr["ADR_MNG_NO"].encode())
                g_wkt = g.decode()
                geom = shapely.from_wkt(g_wkt)
                # geom = shape(addr["geometry"])
                if self.geom_contains_point(geom, x, y):
                    result["road_addr"] = self.convert_bld(addr, g_wkt)
                    break
                    # return self.convert_bld(addr, g_wkt)

            # pnu가 여러개인 경우 hit test로 정확한 주소를 찾음
            latest_addrs = self.get_latest_addrs(addrs, "PNU")
            if len(latest_addrs) > 1:
                for addr in latest_addrs:
                    g = self.db.get(addr["PNU"].encode())
                    g_wkt = g.decode()
                    geom = shapely.from_wkt(g_wkt)
                    # geom = shape(addr["geometry"])
                    if self.geom_contains_point(geom, x, y):
                        result["jibun_addr"] = self.convert_pnu(addr, g_wkt)
                        break
                        # return self.convert_pnu(addr, g_wkt)
            elif latest_addrs:
                result["jibun_addr"] = self.convert_pnu(
                    latest_addrs[0],
                    self.db.get(latest_addrs[0]["PNU"].encode()).decode(),
                )

            if result:
                result["success"] = True
                return result

            return {"success": False, "errmsg": "NOTFOUND ERROR"}
        except Exception as e:
            return {"success": False, "errmsg": "NOTFOUND ERROR"}

    def convert_bld(self, addr, g_wkt):
        """
        주어진 주소 정보를 변환하여 건물 주소를 생성합니다.

        Args:
            addr (dict): 주소 정보를 담고 있는 딕셔너리. "ADR_MNG_NO" 키를 포함해야 합니다.
            g_wkt (str): 변환된 주소의 WKT(Well-Known Text) 형식의 지오메트리.

        Returns:
            dict: 변환된 주소 정보를 담고 있는 딕셔너리. "address", "success", "geom", "errmsg" 키를 포함합니다.
        """
        adr_mng_no = addr["ADR_MNG_NO"]
        addr_name = self.road_matcher.get_road_name(adr_mng_no)

        # 1156013241 5473400000 400004
        # *       *       **     *
        # 0123456789 0123456789 012345

        UNDER_GROUND = "" if adr_mng_no[15:16] == "0" else "지하"
        BLD1 = int(adr_mng_no[16:21])
        BLD2 = int(adr_mng_no[21:])
        if BLD2 == 0:
            BLD2 = ""
        else:
            BLD2 = f"-{BLD2}"

        addr["address"] = f"{addr_name} {UNDER_GROUND}{BLD1}{BLD2}"
        addr["success"] = True
        addr["geom"] = g_wkt
        addr["errmsg"] = ""

        return addr

    def convert_pnu(self, addr, g_wkt):
        """
        주어진 주소와 WKT 형식을 사용하여 PNU를 변환합니다.

        Args:
            addr (dict): 변환할 주소 정보를 담고 있는 딕셔너리. "PNU" 키를 포함해야 합니다.
            g_wkt (str): 변환된 주소의 WKT(Well-Known Text) 형식.

        Returns:
            dict: 변환된 주소 정보를 담고 있는 딕셔너리. "address", "success", "geom", "errmsg" 키를 포함합니다.
        """
        pnu = addr["PNU"]
        pnu_dic = self.pnu_matcher.get_ldong_name(pnu)
        pnu_name = pnu_dic["법정동명"]

        SAN = "" if pnu[10:11] == "1" else "산"
        BNG1 = int(pnu[11:15])
        bng2 = int(pnu[15:])
        if bng2 == 0:
            BNG2 = ""
        else:
            BNG2 = f"-{bng2}"

        addr["address"] = f"{pnu_name} {SAN}{BNG1}{BNG2}번지"
        addr["success"] = True
        addr["geom"] = g_wkt
        addr["errmsg"] = ""

        return addr

    def update_bld_hash(self, feature, proj_transform):
        """
        주어진 feature와 proj_transform을 사용하여 건물 해시를 업데이트합니다.

        Args:
            feature (dict): 지오메트리와 속성 정보를 포함하는 피처 딕셔너리.
            proj_transform (function): 좌표 변환 함수.

        작업 과정:
            1. 피처의 지오메트리를 가져와 변환합니다.
            2. 피처의 속성을 딕셔너리로 변환하고, yyyymm 속성을 추가합니다.
            3. 변환된 지오메트리를 사용하여 건물 데이터베이스를 업데이트합니다.
            4. 지오메트리를 기반으로 지오해시 리스트를 생성합니다.
            5. 각 지오해시에 대해 건물 데이터베이스를 업데이트합니다.
        """
        geom = shape(feature["geometry"])
        property_dict = dict(feature.properties)
        property_dict["yyyymm"] = self.data_yyyymm

        wgs84_geom = transform(proj_transform, geom)

        self.update_geometry(property_dict["ADR_MNG_NO"], wgs84_geom)
        hash_list = polygon_to_geohashes(
            wgs84_geom, precision=self.GEOHASH_PRECISION, inner=False
        )
        for h in hash_list:
            # geohash 중심점이 geometry에 포함되면 저장
            # 두 영역에 걸친 hash가 부정확하므로 모두 저장하고 검색시에 hit test
            # if self.geom_contains_geohash_centroid(wgs84_geom, h):
            self.update_bld_db(h, property_dict)

    def update_pnu_hash(self, feature, proj_transform):
        """
        주어진 feature와 proj_transform을 사용하여 PNU 해시를 업데이트합니다.

        Args:
            feature (dict): 지오메트리와 속성 정보를 포함하는 피처 딕셔너리.
            proj_transform (function): 좌표 변환 함수.

        작업:
            1. 피처의 지오메트리를 가져와 변환합니다.
            2. 속성 딕셔너리를 생성하고 yyyymm 속성을 추가합니다.
            3. 변환된 지오메트리를 사용하여 PNU 해시를 업데이트합니다.
            4. 지오메트리를 geohash 리스트로 변환합니다.
            5. 각 geohash에 대해 PNU 데이터베이스를 업데이트합니다.
        """
        geom = shape(feature["geometry"])
        property_dict = dict(feature.properties)
        property_dict["yyyymm"] = self.data_yyyymm

        wgs84_geom = transform(proj_transform, geom)

        self.update_geometry(property_dict["PNU"], wgs84_geom)
        hash_list = polygon_to_geohashes(
            wgs84_geom, precision=self.GEOHASH_PRECISION, inner=False
        )
        # print(property_dict["PNU"], property_dict["JIBUN"])
        for h in hash_list:
            # geohash 중심점이 geometry에 포함되면 저장
            # 두 영역에 걸친 hash가 부정확하므로 모두 저장하고 검색시에 hit test
            # if self.geom_contains_geohash_centroid(wgs84_geom, h):
            self.update_pnu_db(h, property_dict)

    def update_geometry(self, pnu_or_adr_mng_no, geom):
        """
        주어진 PNU 또는 주소 관리 번호와 기하학적 데이터를 사용하여 데이터베이스를 업데이트합니다.

        Args:
            pnu_or_adr_mng_no (str): PNU 또는 주소 관리 번호.
            geom (shapely.geometry.base.BaseGeometry): 업데이트할 기하학적 데이터.

        Returns:
            None
        """
        key = pnu_or_adr_mng_no.encode()

        self.db.put(key, wkt.dumps(geom, rounding_precision=6).encode())

    def update_bld_db(self, h, property_dict):
        """
        주어진 속성 사전을 사용하여 건물 데이터베이스를 업데이트합니다.

        매개변수:
        h (str): 데이터베이스 키로 사용할 해시 값.
        property_dict (dict): 업데이트할 건물 속성 사전. 다음 키를 포함해야 합니다:
            - ADR_MNG_NO (str): 주소 관리 번호 (참고).
            - SIG_CD (str): 시군구 코드 (필수).
            - RN_CD (str): 도로명 코드 (필수).
            - BULD_SE_CD (str): 건물 구분 코드 (참고).
            - BULD_MNNM (str): 건물 본번 (참고).
            - BULD_SLNO (str): 건물 부번 (참고).
            - BUL_MAN_NO (str): 건물 관리 번호 (참고).
            - EQB_MAN_SN (str): 시설물 관리 일련번호 (참고).
            - EFFECT_DE (str): 효력 발생일 (참고).
            - yyyymm (str): 년월 (필수).

        동작:
        - 주어진 해시 값을 키로 데이터베이스에서 기존 데이터를 검색합니다.
        - 기존 데이터가 없으면 빈 리스트를 생성합니다.
        - 기존 데이터가 있으면 중복 데이터를 제거합니다.
        - 주어진 속성 사전을 사용하여 데이터를 추가하거나 업데이트합니다.
        - 업데이트된 데이터를 데이터베이스에 저장합니다.

        ADR_MNG_NO: 11560132415473400000400004 (참고)
        SIG_CD: 11560 (필수)
        RN_CD: 4154734 (필수)
        BULD_SE_CD: 0 (참고)
        BULD_MNNM: 4 (참고)
        BULD_SLNO: 4 (참고)
        BUL_MAN_NO: 35552 (참고)
        EQB_MAN_SN: 0 (참고)
        EFFECT_DE: 20170427 (참고)
        """

        # 있으면 추가 또는 업데이트, 없으면 생성
        key = h.encode()

        d0 = self.db.get(key)
        if not d0:
            d0 = []
        else:
            d0 = json.loads(d0.decode("utf8"))
            # 중복 데이터 제거
            for i in range(len(d0) - 1, -1, -1):
                if (
                    d0[i]["yyyymm"] == property_dict["yyyymm"]
                    and d0[i]["ADR_MNG_NO"] == property_dict["ADR_MNG_NO"]
                ):
                    if d0[i] == property_dict:  # 중복 데이터가 있으면 저장하지 않음
                        # print("skip")
                        return
                    else:
                        # 최신 데이터로 업데이트하기 위해 제거
                        d0.pop(i)
                        break

        d = {
            "ADR_MNG_NO": property_dict["ADR_MNG_NO"],
            "yyyymm": property_dict["yyyymm"],
        }
        d0.append(d)

        self.db.put(key, json.dumps(d0).encode("utf8"))

    def update_pnu_db(self, h, property_dict):
        """
        PNU: 1156013200100480005
        JIBUN: 48-5대
        BCHK: 1
        SGG_OID: 153066
        COL_ADM_SE: 11560
        """

        # 있으면 추가 또는 업데이트, 없으면 생성
        key = h.encode()
        d0 = self.db.get(key)
        if not d0:
            d0 = []
        else:
            d0 = json.loads(d0.decode("utf8"))
            # 중복 데이터 제거
            for i in range(len(d0) - 1, -1, -1):
                if (
                    d0[i]["yyyymm"] == property_dict["yyyymm"]
                    and d0[i]["PNU"] == property_dict["PNU"]
                ):
                    if d0[i] == property_dict:  # 중복 데이터가 있으면 저장하지 않음
                        # print("skip")
                        return
                    else:
                        # 최신 데이터로 업데이트하기 위해 제거
                        d0.pop(i)
                        break

        d = {
            "PNU": property_dict["PNU"],
            "yyyymm": property_dict["yyyymm"],
        }
        d0.append(d)

        # print("put", h)
        self.db.put(key, json.dumps(d0).encode("utf8"))

    def geom_contains_point(self, geom, x, y):
        """
        주어진 좌표 (x, y)가 주어진 기하 도형(geom) 내에 포함되는지 확인합니다.

        Args:
            geom (shapely.geometry.base.BaseGeometry): 점이 포함되는지 확인할 기하 도형.
            x (float): 점의 x 좌표.
            y (float): 점의 y 좌표.

        Returns:
            bool: 점이 기하 도형 내에 포함되면 True, 그렇지 않으면 False.
        """
        return geom.contains(shape({"type": "Point", "coordinates": [x, y]}))

    def geom_contains_geohash_centroid(self, geom, h):
        """
        Checks if the centroid of a geohash is contained within a given geometry.

        Args:
            geom (object): The geometry object to check against.
            h (str): The geohash string to decode and check.

        Returns:
            bool: True if the centroid of the geohash is within the geometry, False otherwise.
        """
        lat, lon, _, _ = geohash.decode_exactly(h)
        # '{"PNU": "1156013200141500000", "JIBUN": "4150\\ub300", "BCHK": "1", "SGG_OID": 166575, "COL_ADM_SE": "11560"}'
        return self.geom_contains_point(geom, lon, lat)

    def get_data_yyyymm(self, shp_path):
        # LSMD_CONT_LDREG_11560_202404.shp
        filename = os.path.basename(shp_path)
        # '_'를 기준으로 문자열을 분리하고 마지막 부분을 추출
        part = filename.split("_")[-1]

        # '.shp'를 제거하고 return
        return part.replace(".shp", "")

    async def update_bld(self, shp_path):
        self.data_yyyymm = self.get_data_yyyymm(shp_path)
        filename = os.path.basename(shp_path)

        from_crs = pyproj.CRS("EPSG:5179")
        to_crs = pyproj.CRS("EPSG:4326")

        proj_transform = pyproj.Transformer.from_crs(
            from_crs, to_crs, always_xy=True
        ).transform

        # open shp file
        # # self.logger.info(f"update_bld {shp_path}")
        # with fiona.open(shp_path, "r", encoding="cp949") as shp_file:
        #     # for all geometry
        #     n = 0
        #     for feature in shp_file:
        #         # update
        #         self.update_bld_hash(feature, proj_transform)
        #         n += 1
        #         if n % 1000 == 0:
        #             # self.logger.info(f"update {filename}: {n:,}")
        #             print(n)
        #     print(n)

        # 전체 데이터를 스트림으로 읽기
        for feature in pyogrio.read_bounds(shp_path, encoding="cp949"):
            feature_dict = {
                "geometry": feature["geometry"],
                "properties": feature["properties"],
            }
            self.update_bld_hash(feature_dict, proj_transform)
            n += 1
            if n % 1000 == 0:
                print(f"{filename}: {n:,}")

    async def update_pnu(self, shp_path):
        self.data_yyyymm = self.get_data_yyyymm(shp_path)
        filename = os.path.basename(shp_path)

        from_crs = pyproj.CRS("EPSG:5186")
        to_crs = pyproj.CRS("EPSG:4326")

        proj_transform = pyproj.Transformer.from_crs(
            from_crs, to_crs, always_xy=True
        ).transform

        # open shp file
        # self.logger.info(f"update_pnu {shp_path}")
        # with fiona.open(shp_path, "r", encoding="cp949") as shp_file:
        #     # for all geometry
        #     n = 0
        #     for feature in shp_file:
        #         # update
        #         self.update_pnu_hash(feature, proj_transform)
        #         n += 1
        #         if n % 1000 == 0:
        #             # self.logger.info(f"update {filename}: {n:,}")
        #             print(n)
        #     print(n)

        for feature in pyogrio.read_bounds(shp_path, encoding="cp949"):
            feature_dict = {
                "geometry": feature["geometry"],
                "properties": feature["properties"],
            }
            self.update_pnu_hash(feature_dict, proj_transform)
            n += 1
            if n % 1000 == 0:
                print(f"{filename}: {n:,}")

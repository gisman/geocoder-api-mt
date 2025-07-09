import asyncio
import json
import re

# import fiona
# from fiona import transform
from shapely.ops import transform
import pyproj

# import rocksdb3
# import aimrocks
from src.geocoder.geocoder import Geocoder
from .updater import BaseUpdater
from .hd_updater import HdUpdater
from .z_updater import ZUpdater
import glob

from .shp_reader import ShpReader
from src.geocoder.db.gimi9_rocks import WriteBatch

"""
2025: EPSG:5186 - KGD2002 / Central Belt 2010
2024: EPSG:5186 - KGD2002 / Central Belt 2010
2023: EPSG:5186 - KGD2002 / Central Belt 2010
2022: EPSG:5174 - Korean 1985 / Modified Central Belt
2021: EPSG:5174 - Korean 1985 / Modified Central Belt
2020: EPSG:5174 - Korean 1985 / Modified Central Belt
2019: EPSG:5174 - Korean 1985 / Modified Central Belt
2018: EPSG:5174 - Korean 1985 / Modified Central Belt   
2017: EPSG:5186 - KGD2002 / Central Belt 2010   변환했음
2016: EPSG:5186 - KGD2002 / Central Belt 2010   변환했음
2015: EPSG:5186 - KGD2002 / Central Belt 2010   변환했음

from_crs = pyproj.CRS("EPSG:5186")
to_crs = pyproj.CRS("EPSG:5179")

cd 2022
for f in *.zip; do
    unzip "$f" -d shp2_EPSG:5174/
done
cd ..

cd 2021
for f in *.zip; do
    unzip "$f" -d shp2_EPSG:5174/
done
cd ..

cd 2020
for f in *.zip; do
    unzip "$f" -d shp2_EPSG:5174/
done
cd ..

cd 2019
for f in *.zip; do
    unzip "$f" -d shp2_EPSG:5174/
done
cd ..

cd 2018
for f in *.zip; do
    unzip "$f" -d shp2_EPSG:5174/
done
cd ..

cd 2017
for f in *.zip; do
    unzip "$f" -d shp2_ESRI:102086/
done
cd ..

cd 2016
for f in *.zip; do
    unzip "$f" -d shp2_ESRI:102086/
done
cd ..

cd 2015
for f in *.zip; do
    unzip "$f" -d shp2_ESRI:102086/
done
cd ..


# 좌표계 변환
cd /disk/hdd-lv/juso-data/연속지적/2022/
mkdir -p shp2

for f in shp2_EPSG:5174/*.shp; do
    fname=$(basename "$f" .shp)
    ogr2ogr -t_srs EPSG:5186 -s_srs EPSG:5174 "shp2/${fname}.shp" "$f" --config SHAPE_ENCODING "cp949"
done
cd ..


cd /disk/hdd-lv/juso-data/연속지적/2021/
mkdir -p shp2

for f in shp2_EPSG:5174/*.shp; do
    fname=$(basename "$f" .shp)
    ogr2ogr -t_srs EPSG:5186 -s_srs EPSG:5174 "shp2/${fname}.shp" "$f" --config SHAPE_ENCODING "cp949"
done
cd ..

cd /disk/hdd-lv/juso-data/연속지적/2020/
mkdir -p shp2

for f in shp2_EPSG:5174/*.shp; do
    fname=$(basename "$f" .shp)
    ogr2ogr -t_srs EPSG:5186 -s_srs EPSG:5174 "shp2/${fname}.shp" "$f" --config SHAPE_ENCODING "cp949"
done
cd ..

cd /disk/hdd-lv/juso-data/연속지적/2019/
mkdir -p shp2

for f in shp2_EPSG:5174/*.shp; do
    fname=$(basename "$f" .shp)
    ogr2ogr -t_srs EPSG:5186 -s_srs EPSG:5174 "shp2/${fname}.shp" "$f" --config SHAPE_ENCODING "cp949"
done
cd ..

cd /disk/hdd-lv/juso-data/연속지적/2018/
mkdir -p shp2

for f in shp2_EPSG:5174/*.shp; do
    fname=$(basename "$f" .shp)
    ogr2ogr -t_srs EPSG:5186 -s_srs EPSG:5174 "shp2/${fname}.shp" "$f" --config SHAPE_ENCODING "cp949"
done
cd ..


cd /disk/hdd-lv/juso-data/연속지적/2017/
mkdir shp2

# ogr2ogr -t_srs EPSG:5186 -s_srs ESRI:102086 shp2/AL_11_D002_20171202.shp shp2_ESRI:102086/AL_11_D002_20171202.shp --config SHAPE_ENCODING "cp949"
for f in shp2_ESRI:102086/*.shp; do
    fname=$(basename "$f" .shp)
    ogr2ogr -t_srs EPSG:5186 -s_srs ESRI:102086 "shp2/${fname}.shp" "$f" --config SHAPE_ENCODING "cp949"
done



cd /disk/hdd-lv/juso-data/연속지적/2016/
mkdir shp2

# ogr2ogr -t_srs EPSG:5186 -s_srs ESRI:102086 shp2/AL_11_D002_20171202.shp shp2_ESRI:102086/AL_11_D002_20171202.shp --config SHAPE_ENCODING "cp949"
for f in shp2_ESRI:102086/*.shp; do
    fname=$(basename "$f" .shp)
    ogr2ogr -t_srs EPSG:5186 -s_srs ESRI:102086 "shp2/${fname}.shp" "$f" --config SHAPE_ENCODING "cp949"
done



cd /disk/hdd-lv/juso-data/연속지적/2015/
mkdir -p shp2

# ogr2ogr -t_srs EPSG:5186 -s_srs ESRI:102086 shp2/AL_11_D002_20171202.shp shp2_ESRI:102086/AL_11_D002_20171202.shp --config SHAPE_ENCODING "cp949"
for f in shp2_ESRI:102086/*.shp; do
    fname=$(basename "$f" .shp)
    ogr2ogr -t_srs EPSG:5186 -s_srs ESRI:102086 "shp2/${fname}.shp" "$f" --config SHAPE_ENCODING "UTF-8" -lco ENCODING=EUC-KR
done


"""


class PnuUpdater(BaseUpdater):
    """
    연속지적도형정보를 이용하여 주소 추가
    건물이 없는 지번주소를 추가하기 위해 사용
    상세 설명: https://wiki.gimi9.com/index.php?title=지적도

    1. 매달 vworld에서 연속지적을 수작업으로 다운로드 받은 후 실행한다.
    2. 실행 전에 압축을 풀어야 함 LSMD_CONT_LDREG_52_202404.shp 등의 파일이 생성됨.
    3. 파일의 위치는 연속지적/yyyymm/shp2

    Attributes:
        name (str): 다운받은 파일명.
        geocoder (Geocoder): The geocoder instance.

    Methods:
        __init__(name: str, geocoder: Geocoder): Initializes a instance.
        prepare_dic(key, value): Prepares a dictionary for the address entry.
        update(wfile): Updates the geocoder with the address.
    """

    # pnu_matcher = PNUMatcher()

    def __init__(self, name: str, yyyymm: str, geocoder: Geocoder):
        super().__init__(geocoder)
        self.name = name
        self.yyyymm = yyyymm
        # 파일 다운로드 경로 지정
        if not yyyymm:
            self.outpath = f"{self.JUSO_DATA_DIR}/연속지적/"
        else:
            self.outpath = f"{self.JUSO_DATA_DIR}/연속지적/{self.yyyymm}/shp2/"

    async def delete_all(self, wfile):
        # CPU 바운드 작업을 별도의 스레드로 오프로드
        return await asyncio.to_thread(self._delete_all_sync, wfile)

    def _delete_all_sync(self, wfile):
        """
        Deletes all PNU-related address entries from the geocoder.

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the deletion is successful, False otherwise.
        """

        self._prepare_updater_logger(f"{self.name}.log")

        log_file = f"{self.outpath}{self.name}.log"

        # iterate geocoder
        n = 0
        for item in self.geocoder:
            # search
            key = item[0]

            try:
                n += 1

                dic = json.loads(item[1])
                # ["extras"].get("updater") == "pnu_updater" 를 모두 삭제
                modified = False
                for d in list(dic):  # Iterate over a copy of the list
                    if d.get("extras", {}).get("updater", "") == "pnu_updater":
                        dic.remove(d)
                        modified = True

                if modified:
                    if not dic:
                        # If the list is empty, delete the key
                        self.geocoder.db.delete(key)
                    else:
                        self.geocoder.db.put(key, json.dumps(dic))

                if n % 100000 == 0:
                    print(f"update {self.name} {n:,} {key}")
            except Exception as e:
                print(f"Error processing key {key}: {e}")

        with open(log_file, "r") as f:
            log = f.read()
            # wfile.write(log)

        self._stop_updater_logging()
        return True

    async def update(self, wfile):
        """
        Updates the geocoder with the pnu (연속지적 shp).

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.
        """
        # CPU 바운드 작업을 별도의 스레드로 오프로드

        # self.name 과 같은 패턴의 파일을 모두 찾기
        # 'AL_42_D002_20171202(2).shp'
        # 'AL_42_D002_20171202(3).shp'
        # AL_42_D002_20171202.shp
        # Find all files matching the pattern
        pattern = f"{self.outpath}{self.name.split('.')[0]}*.shp"
        matching_files = glob.glob(pattern)
        matching_files.sort(reverse=True)

        self._prepare_updater_logger(f"{self.name}.log")

        self.logger.info(
            f"Found {len(matching_files)} matching files: {matching_files}"
        )

        for f in matching_files:
            self.logger.info(f"Found matching file: {f}")
            self.name = f.split("/")[-1]  # 파일명만 추출
            if not await asyncio.to_thread(self._update_sync, wfile):
                return False

        return True
        # if not matching_files:
        #     self.logger.error(f"No matching files found for pattern: {pattern}")
        #     return False

    def _update_sync(self, wfile):
        """
        Updates the geocoder with the pnu (연속지적 shp).

        Args:
            wfile: The file to write the log to.

        Returns:
            bool: True if the update is successful, False otherwise.

        """
        # 파일 읽기
        # 한 줄씩 객체 생성해서 update_record() 호출
        self._prepare_updater_logger(f"{self.name}.log")

        h1_cd = self.name_to_h1_cd(self.name)

        self.hu = HdUpdater("202504", None)
        self.hu.cache_shp(h1_cd)

        self.zu = ZUpdater("202504", None)
        self.zu.cache_shp(h1_cd)

        cnt = 0
        add_count = 0
        has_xy = 0

        from_crs = pyproj.CRS("EPSG:5186")
        to_crs = pyproj.CRS("EPSG:5179")

        proj_transform = pyproj.Transformer.from_crs(
            from_crs, to_crs, always_xy=True
        ).transform

        # 확보할 수 있는 가장 오래된 데이터가 2015년이고 utf-8로 인코딩되어 있음.
        # 이후 데이터는 cp949로 인코딩되어 있음.
        # ogr2ogr로 변환할 때 인코딩도 변환하려고 해 보았으나 실패. 하드코딩 처리로 쉽게 해결. 2025.06
        if self.yyyymm.startswith("2015"):
            encoding = "utf-8"
        else:
            encoding = "cp949"

        sr = ShpReader(f"{self.outpath}{self.name}", encoding=encoding)
        # with fiona.open(
        #     f"{self.outpath}{self.name}", "r", encoding=encoding
        # ) as shp_file:

        self.logger.info(f"Update: {self.outpath}{self.name}")

        # for all geometry
        n = 0
        batch = WriteBatch()
        bcount = 0
        # batch = rocksdb3.WriterBatch()
        total_features = sr.get_total_features()
        # total_features = len(shp_file)
        self.logger.info(f"Total features in {self.name}: {total_features:,}")
        for value, geom in sr:

            if geom:
                centroid = geom.centroid
                wgs84_centroid = transform(proj_transform, centroid)
                value["X좌표"] = int(wgs84_centroid.x)
                value["Y좌표"] = int(wgs84_centroid.y)
            else:
                # geometry가 None인 경우 있음
                self.logger.debug(f"{value['A1']} has no geometry, skipping.")
                continue

            try:
                address_dic = self.prepare_dic(value)
                if not address_dic:
                    continue

                # # [TODO: 삭제]
                # if address_dic["ld_nm"] != "신북면":
                #     continue

                added = self.update_record(
                    address_dic,
                    merge_if_exists=True,  # null좌표 업데이트 기능도 있으므로 항상 True로 하는 것이 좋다.
                    extras={
                        "updater": "pnu_updater",
                        "jibun": address_dic["jibun"],
                        "yyyymm": self.yyyymm,
                    },
                    batch=batch,
                    fast_giveup=True,  # 빠른 포기를 위해 True로 설정. 처음 시도에 중복이 있으면 바로 포기.
                )
                bcount += added
                add_count += added
                if address_dic["bld_x"]:
                    has_xy += 1
            except Exception as e:
                self.logger.error(f"Error: {e}")
                # continue

            cnt += 1
            if cnt % 10000 == 0:
                progress = (cnt / total_features) * 100
                self.logger.info(
                    f"{self.name}  {cnt:,} +{add_count:,} ({progress:.2f}%)"
                )
                # print(f"{self.name} {cnt:,}")
            if bcount > 5000:
                self.write_batch(batch)
                batch.clear()
                # batch = rocksdb3.WriterBatch()
                bcount = 0

        # 마지막 배치 처리
        if bcount != 0:
            self.write_batch(batch)
            batch.clear()

        self.ldb.flush()

        self.logger.info(
            f"연속지적 DB {self.name}: {cnt:,} 건, 좌표있는 건물: {has_xy:,} 건. hash 추가: {add_count:,} 건"
        )

        self.logger.info(f"완료: {self.name}")

        log_file = f"{self.outpath}{self.name}.log"
        with open(log_file, "r") as f:
            log = f.read()
            wfile.write(log)

        self._stop_updater_logging()
        return True

    def prepare_dic(self, value):
        """
        Prepares a dictionary for the address.

        Args:
            value: The value of the address.

        Returns:
            dict: The prepared dictionary for the address.

        """

        pnu = value["A1"]  # PNU
        if not pnu:
            self.logger.debug(f"empty A3 for PNU: {pnu}")
            return None

        # pnu_dic = self.pnu_matcher.get_ldong_name(pnu)
        # if not pnu_dic:
        #     self.logger.error(f"PNU not found: {pnu}")
        #     return None

        split_values: list = value["A3"].split()
        # split_values: list = pnu_dic["법정동명"].split()

        if split_values[0] == "세종특별자치시":
            split_values[0] = "세종"
            split_values.insert(1, "세종")

        if (
            len(split_values) >= 5
        ):  # ['충청북도', '청주시', '흥덕구', '강내면', '다락리']
            h1_nm = split_values[0]
            h23_nm = split_values[1] + " " + split_values[2]
            ld_nm = split_values[3]
            ri_nm = split_values[4]
        elif len(split_values) == 4:
            if split_values[-1].endswith(
                "리"
            ):  # ['강원도', '횡성군', '강림면', '월현리']
                h1_nm = split_values[0]
                h23_nm = split_values[1]
                ld_nm = split_values[2]
                ri_nm = split_values[3]
            else:  # ['전북특별자치도', '전주시', '완산구', '교동']
                h1_nm = split_values[0]
                h23_nm = split_values[1] + " " + split_values[2]
                ld_nm = split_values[3]
                ri_nm = ""
        elif len(split_values) == 3:  # ['경기도', '포천시', '가산면']
            h1_nm = split_values[0]
            h23_nm = split_values[1]
            ld_nm = split_values[2]
            ri_nm = ""
        else:
            return None

        # 청주시 상당구 미원면 기암리(岐岩) 237
        # 경산시 진량읍 평(平)사리
        if "(" in ld_nm:
            ld_nm = re.sub(r"\([^)]*\)", "", ld_nm)

        # 평(平)사리, 기암리(岐岩)
        if "(" in ri_nm:
            ri_nm = re.sub(r"\([^)]*\)", "", ri_nm)

        SAN = "1" if pnu[10:11] == "2" else "0"  # PNU의 "산"은 2. 주소데이터의 "산"은 1
        bng1 = int(pnu[11:15])
        bng2 = int(pnu[15:])

        d = {
            "h1_nm": h1_nm,
            "h23_nm": h23_nm,
            "ld_nm": ld_nm,
            "hd_nm": None,
            "ri_nm": ri_nm,
            "road_nm": None,
            "undgrnd_yn": None,
            "bld1": None,
            "bld2": None,
            "san": SAN,
            "bng1": str(bng1),
            "bng2": str(bng2),
            "bld_reg": None,
            "bld_nm_text": None,
            "bld_nm": None,
            "ld_cd": value["A2"],
            "hd_cd": None,
            "road_cd": None,
            "zip": None,
            "bld_mgt_no": None,
            "bld_x": value["X좌표"],
            "bld_y": value["Y좌표"],
            "jibun": value["A5"],
        }

        # if d["bld_x"] and not d["hd_cd"]:
        self.update_hd_and_z(d)

        return d

    def name_to_h1_cd(self, name):
        """
        Converts the name of the province to its corresponding h1_cd.

        ex) AL_D002_11_20250604.shp, AL_44_D002_20151224.shp, AL_42_D002_20151224(2).shp,
        """

        h1_cd = None
        if name.startswith("AL_"):
            codes = name.split("_")
            if name.startswith("AL_D002"):
                # '11', '36' from 'LSMD_CONT_LDREG_11_202505.shp, LSMD_CONT_LDREG_36110_202505.shp'
                h1_cd = name.split("_")[2]
            else:  # AL_44_D002_20151224.shp, AL_42_D002_20151224(2).shp
                h1_cd = name.split("_")[1]

        if h1_cd == "42":
            h1_cd = "51"
        elif h1_cd == "45":
            h1_cd = "52"
        return h1_cd

    def update_hd_and_z(self, val):
        if val.get("pos_cd") != None:
            return

        # hu = HdUpdater("202504", None)

        x = val["bld_x"]
        y = val["bld_y"]

        # self.hu.cache_shp(val["h23_cd"][:2])
        hd_dic = self.hu.search_shp(x, y)
        if hd_dic:
            # val["hc"] = hd_dic["hd_cd"]
            val["hd_cd"] = hd_dic["hd_cd"]
            # [TODO: 현재 행정동명으로 설정함. 과거의 행정동명을 알 수 없는 한계가 있음. 과거 행정동명을 찾아서 넣도록 수정해야 함]
            val["hd_nm"] = hd_dic["hd_nm"]

        if val.get("z"):
            return

        # z 값이 없으면 우편번호로 설정
        # zu = ZUpdater("202504", None)
        z_dic = self.zu.search_shp(x, y)
        if z_dic and z_dic["zip"]:
            val["zip"] = z_dic["zip"]

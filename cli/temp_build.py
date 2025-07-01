# 기본 build

yyyymm_list = [
    "202305",
    "202306",
    "202307",
    "202308",
    "202309",
    "202310",
    "202311",
    "202312",
    "202401",
    "202402",
    "202403",
    "202404",
    "202405",
    "202406",
    "202407",
    "202408",
    "202409",
    "202410",
    "202411",
    "202412",
    "202501",
    "202502",
    "202503",
    "202504",
]

h1_list = [
    "11000",
    "26000",
    "27000",
    "28000",
    "29000",
    "30000",
    "31000",
    "36000",
    "41000",
    "42000",
    "43000",
    "44000",
    "45000",
    "46000",
    "47000",
    "48000",
    "50000",
    "51000",
    "52000",
]

for yyyymm in yyyymm_list:
    for h1 in h1_list:
        # python cli/build_geohash.py --shp=/disk/hdd-lv/juso-data/행정동/202305/41000/TL_SCCO_GEMD.shp --output_dir=/disk/hdd-lv/juso-data/행정동/202305/41000/TL_SCCO_GEMD --depth=7 --key_prefix=202305 &
        print(
            f"python cli/build_geohash.py --shp=/disk/hdd-lv/juso-data/행정동/{yyyymm}/{h1}/TL_SCCO_GEMD.shp --output_dir=/disk/hdd-lv/juso-data/행정동/{yyyymm}/{h1}/TL_SCCO_GEMD --depth=7"
        )

import requests
import os

INST_DIR = "/home/gisman/projects/geocoder-api/juso-data/전체분"
# inst_dir = "/home/gisman/HDD2/juso-data/월변동분"
# inst_dir = '/home/gisman/ssd2/juso-data/월변동분'

urls = {
    # 내비게이션용DB_전체분.7z
    "navi": {
        "curl": """
curl 'https://business.juso.go.kr/addrlink/download.do?fileName=20{yymm}_내비게이션용DB_전체분.7z&realFileName=NAVI_DB_ALL_{yymm}.7z&regYmd={yyyy}&reqType=NAVIDATA&stdde=20{yymm}&intFileNo=130385&intNum=77' \
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
  -H 'Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7' \
  -H 'Connection: keep-alive' \
  -H 'Referer: https://business.juso.go.kr/addrlink/elctrnMapProvd/geoDBDwldSubmitDetail.do?reqstGroup=30914' \
  -H 'Upgrade-Insecure-Requests: 1' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 ' """,
        "file_name": "내비게이션용DB_전체분.7z",
    },
    "entrc": {
        "curl": """
curl 'https://business.juso.go.kr/addrlink/download.do?fileName=20{yymm}_위치정보요약DB_전체분.zip&realFileName=ENTRC_DB_{yymm}.zip&regYmd={yyyy}&reqType=GEODATA&stdde=20{yymm}&intFileNo=129682&intNum=94' \
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
  -H 'Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7' \
  -H 'Connection: keep-alive' \
  -H 'Referer: https://business.juso.go.kr/addrlink/elctrnMapProvd/geoDBDwldSubmitDetail.do?reqstGroup=30578' \
  -H 'Upgrade-Insecure-Requests: 1' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36' """,
        "file_name": "위치정보요약DB_전체분.zip",
    },
}


def download(yyyy, mm, DC):
    yy = str(yyyy)[-2:]

    # make dir if not exists
    if not os.path.exists(f"{INST_DIR}/{yyyy}{mm}"):
        os.makedirs(f"{INST_DIR}/{yyyy}{mm}")

    DOWNLOAD_FILE_PATH = f'{INST_DIR}/{yyyy}{mm}/{urls[DC]["file_name"]}'

    curl = urls[DC]["curl"]
    curl = curl.format(yymm=f"{str(yyyy)[-2:]}{mm}", yyyy=yyyy)
    curl = curl + f" -o {DOWNLOAD_FILE_PATH}"
    os.system(curl)

    if DC == "navi":
        cmd = f"7z x -y {DOWNLOAD_FILE_PATH} -o{INST_DIR}/{yyyy}{mm}/{DC}"
    elif DC == "entrc":
        cmd = f"unzip -O cp949 {DOWNLOAD_FILE_PATH} -d {INST_DIR}/{yyyy}{mm}/{DC}"
    else:
        raise ValueError(f"Unknown data category: {DC}")

    print(cmd)
    os.system(cmd)


if __name__ == "__main__":
    data_categories = []

    # 내비게이션 등 위치안내 서비스에 특화하여 건물단위 도로명주소 정보 및 좌표정보(건물중심점, 주출입구, 보조출입구)를 제공합니다.
    # ※ 건물이 6개 이상인 집합건물인 경우 제공
    # 건물정보보기 지번정보보기 보조출입구보기
    # data_categories.append("navi")
    data_categories.append("entrc")

    # # GEOMOD: 위치정보요약DB
    # # 위치기반 서비스 제공자들이 공간정보를 간편하게 구축ㆍ활용할 수 있도록 도로명주소와 주출입구의 좌표정보(X,Y좌표)를 결합한 주출입구 기반 요약DB를 제공합니다.
    # data_categories.append("GEOMOD")

    # yyyymm_from = int("202401")
    # yyyymm_to = int("202401")
    yyyymm_from = int("201711")
    # yyyymm_from = int("201802")
    # yyyymm_from = int("201911")
    yyyymm_to = int("202405")

    for DC in data_categories:
        # mm_iter = int(yyyy_from[5:])
        yyyymm = yyyymm_from
        while yyyymm <= yyyymm_to:
            yyyy = str(yyyymm)[:4]
            mm = str(yyyymm)[4:]

            if mm == "02":
                download(yyyy, mm, DC)

            yyyymm += 1
            if yyyymm % 100 == 13:
                yyyymm = yyyymm + 100 - 12  # 다음 해 1월

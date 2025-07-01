import requests
import os
import sys

sys.path.append("/home/gisman/projects/geocoder-kr/src")
import config

JUSO_DATA_DIR = config.JUSO_DATA_DIR

INST_DIR = f"{JUSO_DATA_DIR}/월변동분"
# inst_dir = "/home/gisman/HDD2/juso-data/월변동분"
# inst_dir = '/home/gisman/ssd2/juso-data/월변동분'

urls = {
    # 주소DB_변동분.zip
    "ADDR": {
        "url": "https://www.juso.go.kr/dn.do\
?reqType=ALLMTCHG\
&fileName={yyyy}{mm}_%EC%A3%BC%EC%86%8CDB_%EB%B3%80%EB%8F%99%EB%B6%84.zip\
&realFileName={yyyy}{mm}ALLMTCHG01.zip\
&regYmd={yyyy}\
&ctprvnCd=01\
&gubun=MTCH\
&stdde={yyyy}{mm}\
&indutyCd=999\
&purpsCd=999\
&indutyRm=%EC%88%98%EC%A7%91%EC%A2%85%EB%A3%8C\
&purpsRm=%EC%88%98%EC%A7%91%\EC%A2%85%EB%A3%8C",
        "fileformat": "zip",
    },
    # 건물DB_변동분.zip
    "BLD": {
        "url": "https://www.juso.go.kr/dn.do?\
reqType=ALLRDNM\
&fileName={yyyy}{mm}_%EA%B1%B4%EB%AC%BCDB_%EB%B3%80%EB%8F%99%EB%B6%84.zip\
&realFileName={yyyy}{mm}ALLRDNM01.zip\
&regYmd={yyyy}\
&ctprvnCd=01\
&gubun=RDNM\
&stdde={yyyy}{mm}\
&indutyCd=999\
&purpsCd=999\
&indutyRm=%EC%88%98%EC%A7%91%EC%A2%85%EB%A3%8C\
&purpsRm=%EC%88%98%EC%A7%91%EC%A2%85%EB%A3%8C",
        "fileformat": "zip",
    },
    # 내비게이션용DB_변동분.7z
    "NAVI": {
        "url": "https://www.juso.go.kr/dn.do?\
boardId=NAVIMOD\
&fileName={yyyy}{mm}_%EB%82%B4%EB%B9%84%EA%B2%8C%EC%9D%B4%EC%85%98%EC%9A%A9DB_%EB%B3%80%EB%8F%99%EB%B6%84.7z\
&realFileName=NAVI_DB_MOD_{yy}{mm}.7z\
&regYmd={yyyy}\
&stdde={yyyy}{mm}\
&indutyCd=999\
&purpsCd=999\
&indutyRm=%EC%88%98%EC%A7%91%EC%A2%85%EB%A3%8C\
&purpsRm=%EC%88%98%EC%A7%91%EC%A2%85%EB%A3%8C",
        "fileformat": "7z",
    },
    # 위치정보요약DB_변동분.zip
    "GEOMOD": {
        "url": "https://www.juso.go.kr/dn.do?\
boardId=GEOMOD\
&regYmd={yyyy}\
&stdde={yyyy}{mm}\
&fileName={yyyy}{mm}_%EC%9C%84%EC%B9%98%EC%A0%95%EB%B3%B4%EC%9A%94%EC%95%BDDB_%EB%B3%80%EB%8F%99%EB%B6%84.zip\
&realFileName=ENTRC_DB_MOD_{yy}{mm}.zip\
&indutyCd=999\
&purpsCd=999\
&indutyRm=%EC%88%98%EC%A7%91%EC%A2%85%EB%A3%8C\
&purpsRm=%EC%88%98%EC%A7%91%EC%A2%85%EB%A3%8C",
        "fileformat": "zip",
    },
    # 상세주소DB_변동분.zip
    "DETAILADR": {
        "url": "https://www.juso.go.kr/dn.do?\
reqType=ALLDETAILADR\
&regYmd={yyyy}\
&ctprvnCd=01\
&gubun=DETAILADR\
&stdde={yyyy}{mm}\
&fileName={yyyy}{mm}_%EC%83%81%EC%84%B8%EC%A3%BC%EC%86%8CDB_%EB%B3%80%EB%8F%99%EB%B6%84.zip\
&realFileName={yyyy}{mm}ADRDC01.zip\
&indutyCd=999\
&purpsCd=999\
&indutyRm=%EC%88%98%EC%A7%91%EC%A2%85%EB%A3%8C\
&purpsRm=%EC%88%98%EC%A7%91%EC%A2%85%EB%A3%8C",
        "fileformat": "zip",
    },
}


def download(url, fileformat, yyyy, mm, DC):
    url = url.format(yyyy=yyyy, yy=str(yyyy)[-2:], mm=mm)
    response = requests.request("GET", url)
    if len(response.text) < 1024:
        return

    filename = f"{yyyy}{mm}_{DC}.{fileformat}"

    # make dir if not exists
    if not os.path.exists(f"{INST_DIR}/{DC}/{yyyy}{mm}"):
        os.makedirs(f"{INST_DIR}/{DC}/{yyyy}{mm}")

    f = open(f"{INST_DIR}/{filename}", "wb")
    f.write(response.content)
    f.close()
    if fileformat == "zip":
        cmd = f"unzip -o -O cp949 {INST_DIR}/{filename} -d {INST_DIR}/{DC}/{yyyy}{mm}"
    elif fileformat == "7z":
        cmd = f"7z x -y {INST_DIR}/{filename} -o{INST_DIR}/{DC}/{yyyy}{mm}"

    print(cmd)
    os.system(cmd)


if __name__ == "__main__":
    data_categories = []

    # 주소DB는 여러 개의 건물이 하나의 도로명주소를 갖는 집합 건물(예: 아파트)의 경우 한 건의 주소정보를 제공하도록 구성된 주소 단위의 DB입니다.
    # 600만여 건의 주소와 800만여 건의 지번정보를 바탕으로 사용자의 필요에 따라 선택적으로 활용할 수 있도록
    # 도로명코드 / 주소 / 지번 / 부가정보로 분리·구성하였습니다.
    data_categories.append("ADDR")

    # 도로명주소를 구성하는 기본 단위인 건물정보와 해당 건물이 위치한 토지(지번)정보로 구성된 DB입니다.
    # 하나의 도로명주소가 부여된 단지형 아파트의 경우에도 상세 동별 정보가 모두 제공되므로, 건물 단위의 주소 활용에 용이합니다.
    # 도로명코드보기 건물정보보기 관련지번보기
    data_categories.append("BLD")

    # 내비게이션 등 위치안내 서비스에 특화하여 건물단위 도로명주소 정보 및 좌표정보(건물중심점, 주출입구, 보조출입구)를 제공합니다.
    # ※ 건물이 6개 이상인 집합건물인 경우 제공
    # 건물정보보기 지번정보보기 보조출입구보기
    data_categories.append("NAVI")

    # GEOMOD: 위치정보요약DB
    # 위치기반 서비스 제공자들이 공간정보를 간편하게 구축ㆍ활용할 수 있도록 도로명주소와 주출입구의 좌표정보(X,Y좌표)를 결합한 주출입구 기반 요약DB를 제공합니다.
    data_categories.append("GEOMOD")

    # 주소정보와 건물단위로 매칭가능한 상세주소정보를 제공합니다.
    # 상세주소란 도로명주소의 건물번호 뒤에 표시되는 동·층·호 정보로, 2가구 이상 거주하는 원룸·다가구·단독주택에 부여합니다.
    data_categories.append("DETAILADR")

    # yyyymm_from = int("202401")
    # yyyymm_to = int("202401")
    yyyymm_from = int("202305")
    yyyymm_to = int("202411")

    for DC in data_categories:
        # mm_iter = int(yyyy_from[5:])
        yyyymm = yyyymm_from
        while yyyymm <= yyyymm_to:
            # for yyyy in range(2015, 2022):
            # for m in range(1, 13):
            # mm = f'{m:02d}'
            yyyy = str(yyyymm)[:4]
            mm = str(yyyymm)[4:]
            url = urls[DC]["url"]
            fileformat = urls[DC]["fileformat"]

            download(url, fileformat, yyyy, mm, DC)
            yyyymm += 1
            if yyyymm % 100 == 13:
                yyyymm = yyyymm + 100 - 12  # 다음 해 1월

            # response = requests.request("GET", url)
            # if len(response.text) < 1024:
            #     continue

            # filename = f'{yyyy}{mm}_ADDR.zip'
            # f = open(f'{inst_dir}/{filename}', 'wb')
            # f.write(response.content)
            # f.close()
            # print(f'unzip -O cp949 {filename} -d ADDR/{yyyy}{mm}')

            # url = urls['BLD']

            # response = requests.request("GET", url)
            # filename = f'{yyyy}{mm}_BLD.zip'
            # f = open(f'{inst_dir}/{filename}', 'wb')
            # f.write(response.content)
            # f.close()
            # print(f'unzip -O cp949 {filename} -d BLD/{yyyy}{mm}')

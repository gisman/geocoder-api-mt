geocoder-api의 multi-threaded 버전입니다.

# 지오코딩

- [X] hash 기반 개발. 핵심 아이디어: 파싱 단계에서 hash 생성. DB 쿼리는 hash 키로 단 한 번.
- [X] 건물명 단순화. 건물 별칭 관리 안 함
- [X] 지적도 추가, 주소 유형 추가 등 별도 프로젝트로 분리해서 관리

## 목표

* 공공데이터의 잘 정제된 주소를 처리. 99% 이상 처리
* 도로명주소, 지번주소 모두 처리
* 번지 없는 지번 주소 지원 안 함
* 인근지번 지원 안 함
* 건물 좌표(아파트 동, 대학교 내 건물 등)
* output: java 버전의 output 기반으로 국가기초구역, 통계청집계구 포함. 블록 제외.
    * 정부표준 행정구역 코드

## DBMS

leveldb: 단순한 key-value 파일 DB. 임베드 DB.
    https://ryanclaire.blogspot.com/2020/06/python-leveldb-example.html

향후 Cloud 고려
    Amazon DynamoDB 프리 티어 (언제나 무료)
        25GB NoSQL
        25개의 프로비저닝된 쓰기 용량 유닛(WCU)
        25개의 프로비저닝된 읽기 용량 유닛(RCU)
        월별 2억 개의 요청을 처리할 수 있는 용량


# 업데이트 HowTo

## 0. 준비

install 7zip

```
sudo apt install p7zip-full
```

## 1. 변경분 다운로드

crawl/changed.py를 이용하여 다운로드 한다.

1. jugo.go.kr 웹 사이트에서 다운로드 가능한 최신 데이터 확인

https://business.juso.go.kr/addrlink/attrbDBDwld/attrbDBDwldList.do

1. changed.py를 수정. 다운로드 받을 데이터의 기간 지정
```
    yyyymm_from = int('202208')
    yyyymm_to = int('202304')
```

1. 다운로드 실행

 $ cd /home/gisman/projects/geocoder
 $ venv

```
python crawl/changed.py
```

1. 디렉토리 확인

실제 사용하는건 NAVI, BLD 뿐이다.

 /home/gisman/ssd2/juso-data/월변동분


## 2. DB Load


geocoder-api/util/DbCreator.py YYYYMM 실행


 $ cd /home/gisman/projects/geocoder
 $ venv

```

python geocoder-api/util/DbCreator.py 202305

python geocoder-api/util/DbCreator.py 202306

python geocoder-api/util/DbCreator.py 202307

python geocoder-api/util/DbCreator.py 202308

python geocoder-api/util/DbCreator.py 202309

python geocoder-api/util/DbCreator.py 202310

python geocoder-api/util/DbCreator.py 202311

python geocoder-api/util/DbCreator.py 202312


```


# reverse geocoding update

curl 'http://localhost:4001/update_pnu?file=LSMD_CONT_LDREG_서울_영등포구.zip'
date='$(date +\%Y\%m\%d)

curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_11560_202404.shp' # 영등포구
curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_47_202404.shp' # 경북

curl 'http://localhost:4009?q=  서울 영등포구 영등포로62가길 4-4'
curl 'http://localhost:4009?q=서울 영등포구 신길동 48-5'


경상북도 봉화군 봉화읍 유곡리121-1 외 1필지
경상북도 봉화군 명호면 관창리 산9
경상북도 봉화군 재산면 갈산리 13150
경상북도 봉화군 봉성면 외삼리 산124-6
경상북도 봉화군 명호면 관창리 산9
경상북도 봉화군 봉성면 외삼리 7931 외 8필지
경상북도 봉화군 명호면 관창리 산9 외 2필지
경상북도 봉화군 소천면 분천리 1366-9
경상북도 봉화군 봉성면 외삼리 산124-6
경상북도 석포면 석포리 330-1 외 2필지
    경상북도 봉화군 석포면 석포리 330-1 외 2필지

경상북도 봉화군 봉화읍 삼계리 119
경상북도 봉화군 봉화읍 문단리 220
경상북도 봉화군 상운면 하눌리 552 외 1필지
경상북도 봉화군 상운면 하눌리 554
경상북도 봉화군 상운면 하눌리 552 외 1필지
경상북도 봉화군 물야면 북지리 742-3 외 1필지
경상북도 봉화군 봉화읍 내성리 60-1 외 2필지
경상북도 봉화군 봉성면 봉양리 1431
경상북도 봉화군 봉성면 봉양리 91
경상북도 봉화군 물야면 개단리 134-1


# test

체험 유저
-[X] 체험 하기
-[X] 검색, 다운로드
-[X] 파일, 다운로드
-[] 건수 제한
-[X] 쿼터 무제한

로그인 유저
-[X] 로그인
-[X] 검색, 다운로드
-[X] 파일검색, 다운로드

-[X] 회원가입
-[X] 회원정보 수정
-[] 비밀번호 변경
-[X] 비밀번호 찾기
-[X] 회원탈퇴

관리자 페이지
-[X] 관리자 페이지 로그인
-[X] 관리자 페이지 회원 관리
-[X] 회원 비밀번호 변경
-[X] 관리자 페이지 회원 탈퇴
-[X] 관리자 페이지 회원 비밀번호 변경

# -[] 위험 시설. 좌표 없음

경기 안산시 상록구 수인로 1248

# [TODO] "경기도 수원시 장안구 파장동 572-19" 3차 행정구역 주소에 대해 "수원시 파장동 572-19" "장안구 파장동 572-19" 주소 생성

# 도로명 대표 주소 테스트

다 성공해야 함.

<pre>
강원도 횡성군 강림면  월현속담길
강원도 강림면 월현속담길
강원도 횡성군  월현속담길
강원도   월현속담길
횡성군 강림면  월현속담길
횡성군   월현속담길
강림면  월현속담길
강원도 횡성군 강림면   월현속담길 120
월현속담길

강원도 횡성군 강림면 월현리 월현속담길
강원도 강림면 월현리 월현속담길
강원도 횡성군 월현리 월현속담길
강원도  월현리 월현속담길
횡성군 강림면 월현리 월현속담길
횡성군  월현리 월현속담길
강림면 월현리 월현속담길
강원도 횡성군 강림면 월현리  월현속담길 120
월현리  월현속담길
</pre>

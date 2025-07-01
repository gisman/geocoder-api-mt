# 개요

* 과거 변동분 데이터를 추가하여 없어진 주소도 Geocode되도록 하여 성공률을 높임.
* 정제결과에 변경된 주소정보가 보이도록 함
* 월변동분을 처리하는 프로세스를 만들어
    * 2017년 11월 부터 1회성으로 2021년 3월분까지 처리하고
    * 2021년 4월부터 매월 자동화 처리
* 전체분 처리와 같은 데이터와 알고리즘
* 전체분 처리와 다른 DB 테이블을 사용. 향후 합칠지 고려

건물 변동분을 2015년 8월부터 확보할 수 있으나, 
NAVI 데이터는 2017년 11월 이후만 확보할 수 있으므로, NAVI 기준으로 변경분을 추가.

이동사유코드 31: 신규, 34: 변경, 63: 삭제
* 신규는 처리 대상에서 제외
* 변경:
* 삭제는 반드시 포함

# 수집

* 크롤러
crawl/changed.py
2015년 1월 ~ 2021년 12월까지 월별 수집

* 저장위치: /home/gisman/ssd2/juso-data/월변동분

* ADDR/ : 주소 
* BLD/  : 건물 (사용)
* DETAILADR/ : 상세주소정보(동,층,호)
* GEOMOD/   : 위치정보요약DB
* NAVI/ : 내비게이션 (사용)

두 가지 정보만 사용. 나머지는 향후 활용 가능성이 있으니 수집만.

# 201711 ~ 202103 처리






에러 있다.
```bash
cd ~/projects/geocoder-api/
source venv/bin/activate

echo '전체 참조데이터 재실행'
python src/util/DbCreator.py

python src/util/DbCreator.py 201711
python src/util/DbCreator.py 201712
python src/util/DbCreator.py 201801
python src/util/DbCreator.py 201802
python src/util/DbCreator.py 201803
python src/util/DbCreator.py 201804
python src/util/DbCreator.py 201805
python src/util/DbCreator.py 201806
python src/util/DbCreator.py 201807
python src/util/DbCreator.py 201808
python src/util/DbCreator.py 201809
python src/util/DbCreator.py 201810
python src/util/DbCreator.py 201811
python src/util/DbCreator.py 201812
python src/util/DbCreator.py 201901
python src/util/DbCreator.py 201902
python src/util/DbCreator.py 201903
python src/util/DbCreator.py 201904
python src/util/DbCreator.py 201905
python src/util/DbCreator.py 201906
python src/util/DbCreator.py 201907
python src/util/DbCreator.py 201908
python src/util/DbCreator.py 201909
python src/util/DbCreator.py 201910
python src/util/DbCreator.py 201911
python src/util/DbCreator.py 201912
python src/util/DbCreator.py 202001
python src/util/DbCreator.py 202002
python src/util/DbCreator.py 202003
python src/util/DbCreator.py 202004
python src/util/DbCreator.py 202005
python src/util/DbCreator.py 202006
python src/util/DbCreator.py 202007
python src/util/DbCreator.py 202008
python src/util/DbCreator.py 202009
python src/util/DbCreator.py 202010
python src/util/DbCreator.py 202011
python src/util/DbCreator.py 202012
python src/util/DbCreator.py 202101
python src/util/DbCreator.py 202102
```

postgres에게 읽기 권한을 주어야 한다.
    ERROR: could not open file "/home/gisman/ssd2/juso-data/월변동분/NAVI/202111/match_build_mod.txt" for reading: 허가 거부

sudo chmod -R a+rX /home/gisman/ssd2/juso-data/월변동분

```
echo '202111'
nice -n 19 python geocoder-api/util/DbCreator.py 202111

echo '202112'
nice -n 19 python geocoder-api/util/DbCreator.py 202112

echo '202201'
nice -n 19 python geocoder-api/util/DbCreator.py 202201

echo '202202'
nice -n 19 python geocoder-api/util/DbCreator.py 202202

echo '202203'
nice -n 19 python geocoder-api/util/DbCreator.py 202203

echo '202204'
nice -n 19 python geocoder-api/util/DbCreator.py 202204

echo '202205'
nice -n 19 python geocoder-api/util/DbCreator.py 202205

echo '202206'
nice -n 19 python geocoder-api/util/DbCreator.py 202206

echo '202207'
nice -n 19 python geocoder-api/util/DbCreator.py 202207

echo 'finished'

```

# Load

# 임시테이블 비우기

```sql
truncate table geocode.tbbld_info_load;
truncate table geocode.tbnavi_match_bld_load;
```

## 건물정보

/home/gisman/ssd2/juso-data/변동분/BLD

* 컬럼간 구분은 파이프(‘|’) 이용
* 파일 인코딩 : MS949

201510: 파일명 변경
201908: jibun_mod.txt 추가

head BLD/201508/도로명코드_변동분.txt
head BLD/201510/road_code_mod.txt

```
BLD
├── 201508
│   ├── 도로명코드_변동분.txt
│   └── 전체주소_변동분.txt
├── 201509
│   ├── 도로명코드_변동분.txt
│   └── 전체주소_변동분.txt
├── 201510
│   ├── build_mod.txt
│   └── road_code_mod.txt
├── 201907
│   ├── build_mod.txt
│   └── road_code_mod.txt
├── 201908
│   ├── build_mod.txt
│   ├── jibun_mod.txt
│   └── road_code_mod.txt
└── 202102
    ├── build_mod.txt
    ├── jibun_mod.txt
    └── road_code_mod.txt
```

### DDL

yyyymm를 추가하고 PK에 포함

```
create table tbbld_info_updated (
    yyyymm varchar(8)  -- 변경년월
,   ld_cd varchar(10) -- 법정동코드
,   h1_nm varchar(40) -- 시도명
,   h23_nm varchar(40) -- 시군구명
,   ld_nm varchar(40) -- 법정읍면동명
,   ri_nm varchar(40) -- 법정리명
,   san varchar(1) -- 산여부 0:대지, 1:산
,   bng1 numeric(4) -- 지번본번
,   bng2 numeric(4) -- 지번부번
,   road_cd varchar(12) -- 도로명코드 시군구코드(5) + 도로명번호(7)
,   road_nm varchar(80) -- 도로명
,   undgrnd_yn varchar(1) -- 지하여부 0:지상, 1:지하, 2:공중
,   bld1 numeric(5) -- 건물본번
,   bld2 numeric(5) -- 건물부번
,   bld_reg varchar(40) -- 건축물대장건물명
,   bld_nm varchar(100) -- 상세건물명
,   bld_mgt_no varchar(25) -- 건물관리번호
,   ld_seq varchar(2) -- 읍면동일련번호
,   h4_cd varchar(10) -- 행정동코드
,   h4_nm varchar(40) -- 행정동명
,   zip varchar(5) -- 우편번호
,   zip_seq varchar(3) null -- 우편일련번호 2015. 8. 1 이후 미제공(null)
,   lg_dlvr_nm varchar(40) null -- 다량배달처명 2015. 8. 1 이후 미제공(null)
,   mvmn_resn_cd varchar(2) -- 이동사유코드 31 : 신규, 34 : 변동, 63 : 폐지, 72 : 건물군내 일부 건물 폐지, 73 : 건물군내 일부 건물 생성
,   ntfc_de varchar(8) -- 고시일자
,   old_road_addr varchar(25) -- 변동전도로명주소
,   bld_nm_text varchar(40) -- 시군구용건물명
,   apt_yn varchar(1) -- 공동주택여부 0:비공동주택, 1:공동주택
,   bas_no varchar(5) -- 기초구역번호
,   dtl_addr_yn varchar(1) -- 상세주소여부 0:미부여, 1:부여
,   rm1 varchar(15) -- 비고1
,   rm2 varchar(15) -- 비고2
,   constraint "pk_bld_updated" primary key (bld_mgt_no, yyyymm)
);
```

### load

COPY statement는 관리자 권한으로 실행. \copy command는 소유자 권한으로 실행 가능.

~~~> %sudo -i -u postgres~~~
> %psql -d geocode


```sql
-- 2017년 11월.
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/월변동분/BLD/201711/build_mod.txt' WITH DELIMITER '|' ENCODING 'WIN949';
```


## NAVI정보

/home/gisman/ssd2/juso-data/월변동분/NAVI

* 컬럼간 구분은 파이프(‘|’) 이용
* 파일 인코딩 : MS949

201510: 파일명 변경
201908: jibun_mod.txt 추가

head BLD/201508/도로명코드_변동분.txt
head BLD/201510/road_code_mod.txt

```
NAVI
├── 201711
│   ├── [레이아웃]내비게이션전용DB.pdf
│   ├── match_build_mod.txt
│   ├── match_jibun_mod.txt
│   └── match_rs_entrc_mod.txt
├── 201712
│   ├── [레이아웃]내비게이션전용DB.pdf
│   ├── match_build_mod.txt
│   ├── match_jibun_mod.txt
│   └── match_rs_entrc_mod.txt
├── 201801
...
└── 202102
    ├── [가이드]내비게이션용DB 활용방법.pdf
    ├── match_build_mod.txt
    ├── match_jibun_mod.txt
    └── match_rs_entrc_mod.txt
```

### DDL

yyyymm를 추가하고 PK에 포함

```sql
create table geocode.tbnavi_match_bld_updated (
    yyyymm varchar(8)  -- 변경년월
,   h4_10cd varchar(10)              -- 주소관할읍면동코드 10 문자 시군구코드(5)+읍면동코드(3)+00
,   h1_nm varchar(40)                -- 시도명
,   h23_nm varchar(40)               -- 시군구명
,   ld_nm varchar(40)                -- 읍면동명
,   road_cd varchar(12)              -- 도로명코드 시군구코드(5) + 도로명번호(7)
,   road_nm varchar(80)              -- 도로명
,   undgrnd_yn varchar(1)            -- 지하여부
,   bld1 numeric(5)                  -- 건물본번
,   bld2 numeric(5)                  -- 건물부번
,   zip varchar(5)                   -- 우편번호
,   bld_mgt_no varchar(25)           -- 건물관리번호 PK
,   bld_nm_text varchar(40)          -- 시군구용건물명
,   bld_clss varchar(100)            -- 건축물용도분류
,   h4_cd varchar(10)                -- 행정동코드
,   h4_nm varchar(40)                -- 행정동명
,   ground_floor numeric(3)          -- 지상층수
,   undground_floor numeric(3)       -- 지하층수
,   apt_yn varchar(1)                -- 공동주택구분 0 : 비공동주택, 1 : 공동주택(아파트), 2 :공동주택(연립/다세대 등)
,   bld_cnt numeric(10)              -- 건물수. 같은 주소를 갖는 건물의 수(건물군의 경우 동일한 값)
,   bld_nm varchar(100)              -- 상세건물명
,   bld_nm_major_hist varchar(1000)  -- 건물명변경이력. 건물명이 변경된 경우 최초부터 최종변경 건물명을 나열
,   bld_nm_hist varchar(1000)        -- 상세건물명변경이력. 상세건물명이 변경된 경우 최초부터 최종 변경 상세건물명을 나열
,   RESIDENCE_yn varchar(1)          -- 거주여부 0 : 비거주, 1 : 거주
,   bld_x numeric(15, 6)             -- 건물중심점_x좌표 GRS80 UTM-K 좌표계
,   bld_y numeric(15, 6)             -- 건물중심점_y좌표 GRS80 UTM-K 좌표계
,   ent_x numeric(15, 6)             -- 출입구_x좌표 GRS80 UTM-K 좌표계
,   ent_y numeric(15, 6)             -- 출입구_y좌표 GRS80 UTM-K 좌표계
,   eng_h1_nm varchar(40)            -- 시도명(영문)
,   eng_h23_nm varchar(40)           -- 시군구명(영문)
,   eng_ld_nm varchar(40)            -- 읍면동명(영문)
,   eng_road_nm varchar(80)          -- 도로명(영문)
,   ld_clss varchar(1)               -- 읍면동구분 0 : 읍면, 1 : 동
,   mvmn_resn_cd varchar(2)          -- 이동사유코드 31 : 신규, 34 : 변경, 63 : 삭제
,   constraint pk_navi_match_bld_updated primary key (bld_mgt_no, yyyymm)
```

### load

COPY statement는 관리자 권한으로 실행. \copy command는 소유자 권한으로 실행 가능.

~~~> %sudo -i -u postgres~~~
> %psql -d geocode

```sql
-- 2017년 11월.
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/변동분/NAVI/201711/match_build_mod.txt' WITH DELIMITER '|' ENCODING 'WIN949';
```

# tbaddress_updated

drop table tbaddress_updated;

CREATE TABLE geocode.tbaddress_updated (
    yyyymm varchar(8),  -- 변경년월    
	h1_nm varchar(40) NULL,
	h23_nm varchar(40) NULL,
	ld_nm varchar(40) NULL,
	h4_nm varchar(40) NULL,
	ri_nm varchar(40) NULL,
	road_nm varchar(80) NULL,
	undgrnd_yn varchar(1) NULL,
	bld1 numeric(5) NULL,
	bld2 numeric(5) NULL,
	san varchar(1) NULL,
	bng1 numeric(4) NULL,
	bng2 numeric(4) NULL,
	bld_reg varchar(40) NULL,
	bld_nm_text varchar(40) NULL,
	bld_nm varchar(100) NULL,
	ld_cd varchar(10) NULL,
	h4_cd varchar(10) NULL,
	road_cd varchar(12) NULL,
	zip varchar(5) NULL,
	bld_mgt_no varchar(25) NULL,
	bld_x int4 NULL,
	bld_y int4 NULL
);

CREATE INDEX tbaddress_updated_h1_nm_idx ON geocode.tbaddress_updated(h1_nm);
CREATE INDEX tbaddress_updated_h23_nm_idx ON geocode.tbaddress_updated(h23_nm);
CREATE INDEX tbaddress_updated_h4_nm_idx ON geocode.tbaddress_updated(h4_nm);
CREATE INDEX tbaddress_updated_ld_nm_idx ON geocode.tbaddress_updated(ld_nm);


# 다 합쳐서 한 방에.

새주소, 지번주소, 건물명주소를 python에서 아래 데이터로 조합
```sql
insert into geocode.tbaddress_updated(
    yyyymm, h1_nm, h23_nm, ld_nm, h4_nm, ri_nm,
    road_nm, undgrnd_yn, bld1, bld2,
    san, bng1, bng2,
    bld_reg, bld_nm, 
    ld_cd, h4_cd, road_cd, zip, bld_mgt_no,
    bld_x, bld_y)
select '201711' as yyyymm, b.h1_nm, b.h23_nm, b.ld_nm, b.h4_nm, a.ri_nm
    , b.road_nm, b.undgrnd_yn, b.bld1, b.bld2
    , a.san, a.bng1, a.bng2 
    , a.bld_reg, a.bld_nm 
    , a.ld_cd, a.h4_cd, b.road_cd, a.zip, a.bld_mgt_no 
    , b.bld_x::numeric::integer, b.bld_y::numeric::integer
from geocode.tbbld_info_load  a
,	geocode.tbnavi_match_bld_load b
where 1=1
    and a.bld_mgt_no = b.bld_mgt_no
    and a.mvmn_resn_cd = '63'
    and b.bld_x <> ''
;
```




# 작업하다 만 안 쓰는 것들

## _ADDR 파일

중간에 파일 변경됨

* 201908: 관련지번_변동분.txt 추가

```
ADDR
├── 201508
│   ├── 개선_도로명코드_변경분.txt
│   ├── 부가정보_변동분.txt
│   ├── 주소_변동분.txt
│   └── 지번_변동분.txt
├── 201509
│   ├── 개선_도로명코드_변경분.txt
│   ├── 부가정보_변동분.txt
│   ├── 주소_변동분.txt
│   └── 지번_변동분.txt
├── 201907
│   ├── 개선_도로명코드_변경분.txt
│   ├── 부가정보_변동분.txt
│   ├── 주소_변동분.txt
│   └── 지번_변동분.txt
├── 201908
│   ├── 개선_도로명코드_변경분.txt
│   ├── 관련지번_변동분.txt
│   ├── 부가정보_변동분.txt
│   ├── 주소_변동분.txt
│   └── 지번_변동분.txt
└── 202102
    ├── 개선_도로명코드_변경분.txt
    ├── 관련지번_변동분.txt
    ├── 부가정보_변동분.txt
    ├── 주소_변동분.txt
    └── 지번_변동분.txt
```

## 개선_도로명코드_변경분.txt

[가이드]주소DB 활용방법.pdf	- 4.3.2 월변동 자료 현행화

115003155054|마곡중앙6로|Magokjungang 6-ro|01|서울특별시|Seoul|강서구|Gangseo-gu|마곡동|Magok-dong|1|105|0||신규||
113204127024|노해로63가길|Nohae-ro 63ga-gil|02|서울특별시|Seoul|도봉구|Dobong-gu|방학동|Banghak-dong|1|106|0||신규||


- PK를 비교하여 전체분에 미존재할 경우 INSERT, 이미 존재할 경우 UPDATE처리
 (신규가 아닌 경우는 모두 UPDATE 처리, 폐지건의 경우 사용여부가 '1'로 변경

## 변경사유코드

변경사유코드	변경사유 					제공자료 갱신방법
31 신규			주소, 지번,부가정보 		신규자료를각각의테이블로추가
34 주소변경 	주소 						해당키의주소정보를제공자료의내용으로변경
51 지번변경 	지번 						해당키의지번정보를제공자료의내용으로변경
63 폐지 		주소 						해당키의주소,지번,부가정보자료를삭제
70 우편번호변경 부가정보 					해당키의부가정보(우편번호)를제공자료의우편번호로변경
71 건물명 변경 	부가정보 					해당키의부가정보(건물명)를제공자료의건물명으로변경
79 기타	부가정보변경 부가정보 				해당키의부가정보(우편번호와건물명을제외한정보)를 제공자료로변경(행정동코드,행정동명,공동주택여부)

## 주소 (주소_변동분.txt)

## 대표지번 (지번_변동분.txt)

## 부가정보 (부가정보_변동분.txt)


## 설명서


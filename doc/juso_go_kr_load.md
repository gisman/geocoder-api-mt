# datbase init

createuser -S -D -R -P gisman

```sql
CREATE TABLESPACE geocodespace LOCATION '/var/tablespace/geocode';
CREATE DATABASE geocode OWNER gisman TABLESPACE geocodespace;
```

-- gisman user로
psql -d geocode -U gisman

```sql
create schema geocode;
```

# download

ERD: https://www.erdcloud.com/d/cCDus2uY268g63wcb


## 주소 DB

https://www.juso.go.kr/addrlink/addressBuildDevNew.do?menu=mainJusoDb

* 건물DB: 도로명주소가 부여된 아파트(또는 집합건물) 단지 내 동 단위 건물정보를제공합니다.
    약 1,000만여 건의 건물정보와 200만여 건의 관련지번으로 구성되어 있습니다.
* 주소DB: 아파트단지(또는 집합건물), 단독건물 등의 출입구 위치를 기준으로 부여된 주소 DB입니다.
    약 600만여 건의 주소와 800만여 건의 지번으로 구성되어 있습니다.

* 사서함주소DB: 사서함주소DB사서함 정보의 주소 활용을 위해 도로명주소 형태로 구성한 사서함주소DB를 제공합니다.
* 위치정보 요약DB: 위치기반 서비스 제공자를 위해 도로명주소와 좌표 정보를 결합한 요약DB를 제공합니다.
* 영문주소DB: 해외우편, 배송 등의 활용을 위한 영문 도로명 주소DB를 제공합니다.
* 내비게이션용 DB: 내비게이션 등 위치 및 이동경로 제공 서비스에 특화된
    건물단위 도로명주소 및 좌표정보(건물중심점 및 출입구)를 제공합니다.
* 상세주소DB: 주소정보와 건물단위로 매칭가능한 상세주소정보를 제공합니다.

## 전자지도

https://www.juso.go.kr/addrlink/addressBuildDevNew.do?menu=mainJusoLayer

도로명주소 전자지도는 전화번호로 인증을 하고 사용 신청을 해야 함. 하루 정도 기다리면 사용 승인 됨.

* 도로명주소 전자지도: 도로명주소 전자지도건물, 건물군, 도로구간, 실폭도로, 기초구간, 출입구, 기초구역, 행정구역경계(시도, 시군구, 읍면동, 법정리)등 11종을 제공합니다.
    전국 광역시도 또는 시군구 단위로 제공하며, 신청지역을 관할하는 **기관장의 승인에 따라 다운로드**가 가능합니다.
* 민원행정기관 전자지도: 민원행정기관 전자지도중앙행정기관 및 지방자치단체청사, 법원, 경찰서, 우체국, 학교 등 행정기관의 위치정보가 포함된 전자지도를 제공합니다.
    제공되는 레이어는 Point입니다.
* 도로명주소 배경지도: 도로명주소 배경지공원, 철도, 교량, 하천 등 도로명주소 전자지도의 배경으로 활용되는 지도를 제공합니다.
    배경지도의 갱신 여부에 따라 수시로 제공됩니다.
* 기초구역도: 기초구역도우편번호로 활용되고 있는 전국 기초구역번호 정보를 전자지도(SHAPE)형식으로 제공합니다.
    제공되는 레이어는 Polygon형태이며, 기초구역번호는 년 1회 주기로 제공합니다.

## 압축 풀기

unzip -O cp949 세종특별자치시.zip -d 세종특별자치시/
unzip -O cp949 강원도.zip -d 강원도/
unzip -O cp949 경기도.zip -d 경기도/
unzip -O cp949 경상남도.zip -d 경상남도/
unzip -O cp949 경상북도.zip -d 경상북도/
unzip -O cp949 광주광역시.zip -d 광주광역시/
unzip -O cp949 대구광역시.zip -d 대구광역시/
unzip -O cp949 대전광역시.zip -d 대전광역시/
unzip -O cp949 부산광역시.zip -d 부산광역시/
unzip -O cp949 서울특별시.zip -d 서울특별시/
unzip -O cp949 울산광역시.zip -d 울산광역시/
unzip -O cp949 인천광역시.zip -d 인천광역시/
unzip -O cp949 전라남도.zip -d 전라남도/
unzip -O cp949 전라북도.zip -d 전라북도/
unzip -O cp949 제주특별자치도.zip -d 제주특별자치도/
unzip -O cp949 충청남도.zip -d 충청남도/
unzip -O cp949 충청북도.zip -d 충청북도/

# 기초구역

## table

```sql
--drop table geocode.tbzip_area;

create table geocode.tbzip_area (
    bas_mgt_sn  varchar(10)    -- 기초구역 관리번호
,   ctp_kor_nm varchar(40)     -- 시도명
,   sig_cd varchar(5)          -- 시군구코드
,   sig_kor_nm varchar(40)     -- 시군구명
,   bas_id varchar(5)          -- 기초구역번호_본번
,   bas_ar numeric(22, 17)      -- 기초구역 면적 km2
,   ntfc_de varchar(8)         -- 고시일자
,   mvmn_de varchar(8)         -- 이동일자
,   mvmn_resn varchar(254)     -- 이동사유
,   opert_de varchar(80)       -- 작업일시
,   geom geometry NULL        -- 형상 
,   constraint "pk_tbzip_area" primary key (bas_mgt_sn)
);

comment on table geocode.tbzip_area is '기초구역';
comment on column geocode.tbzip_area.bas_mgt_sn is '기초구역 관리번호';
comment on column geocode.tbzip_area.ctp_kor_nm is '시도명';
comment on column geocode.tbzip_area.sig_cd is '시군구코드';
comment on column geocode.tbzip_area.sig_kor_nm is '시군구명';
comment on column geocode.tbzip_area.bas_id is '기초구역번호_본번';
comment on column geocode.tbzip_area.bas_ar is '기초구역 면적 km2';
comment on column geocode.tbzip_area.ntfc_de is '고시일자';
comment on column geocode.tbzip_area.mvmn_de is '이동일자';
comment on column geocode.tbzip_area.mvmn_resn is '이동사유';
comment on column geocode.tbzip_area.opert_de is '작업일시';
comment on column geocode.tbzip_area.geom is '형상';

CREATE INDEX idx_tbzip_area_geom
  ON geocode.tbzip_area
  USING GIST (geom);

create table geocode.tbzip_area_load (
    bas_mgt_sn  varchar(10)    -- 기초구역 관리번호
,   ctp_kor_nm varchar(40)     -- 시도명
,   sig_cd varchar(5)          -- 시군구코드
,   sig_kor_nm varchar(40)     -- 시군구명
,   bas_id varchar(5)          -- 기초구역번호_본번
,   bas_ar numeric(22, 17)      -- 기초구역 면적 km2
,   ntfc_de varchar(8)         -- 고시일자
,   mvmn_de varchar(8)         -- 이동일자
,   mvmn_resn varchar(254)     -- 이동사유
,   opert_de varchar(80)       -- 작업일시
,   geom geometry NULL        -- 형상 
,   constraint "pk_tbzip_area_load" primary key (bas_mgt_sn)
);
```

## load

> $ find -name  *.shp

```bash
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/경상남도/TL_KODIS_BAS_48.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/세종특별자치시/TL_KODIS_BAS_36.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/충청남도/TL_KODIS_BAS_44.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/전라남도/TL_KODIS_BAS_46.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/전라북도/TL_KODIS_BAS_45.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/울산광역시/TL_KODIS_BAS_31.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/경상북도/TL_KODIS_BAS_47.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/대구광역시/TL_KODIS_BAS_27.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/경기도/TL_KODIS_BAS_41.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/부산광역시/TL_KODIS_BAS_26.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/대전광역시/TL_KODIS_BAS_30.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/광주광역시/TL_KODIS_BAS_29.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/강원도/TL_KODIS_BAS_42.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/서울특별시/TL_KODIS_BAS_11.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/인천광역시/TL_KODIS_BAS_28.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/충청북도/TL_KODIS_BAS_43.shp  geocode.tbzip_area_load | psql -d geocode 
shp2pgsql -s 5179 -a ~/ssd2/juso-data/201912기초구역DB_전체분/제주특별자치도/TL_KODIS_BAS_50.shp  geocode.tbzip_area_load | psql -d geocode 
```

* shp2pgsql     : command
* -s 5179       : EPSG 좌표계
* -a            : append.  -c: 테이블 생성(default), -d: drop후 테이블 생성, -p: prepare모드. 테이블 생성만.
* -I            : 공간인덱스 생성
* TL_KODIS_BAS_48.shp   : shp 파일명
* geocode.tbzip_area_load   : -a 옵션일 때 load할 타겟 테이블. 
* | psql -d geocode : 파이프 이용하여 psql에 sql출력을 전달

## transfer

```sql
insert into geocode.tbzip_area
select * from geocode.tbzip_area_load;
```

# 건물DB_전체분

directory: ~/ssd2/juso-data/202007_건물DB_전체분

## 건물정보

* 컬럼간 구분은 파이프(‘|’) 이용
* 파일 인코딩 : MS949

```bash
$ ls -1 $PWD/build*.txt

~/ssd2/juso-data/202007_건물DB_전체분/build_busan.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_chungbuk.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_chungnam.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_daegu.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_daejeon.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_gangwon.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_gwangju.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_gyeongbuk.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_gyeongnam.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_gyunggi.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_incheon.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_jeju.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_jeonbuk.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_jeonnam.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_sejong.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_seoul.txt
~/ssd2/juso-data/202007_건물DB_전체분/build_ulsan.txt
```

### table

```sql
create table geocode.tbbld_info (
    ld_cd varchar(10) -- 법정동코드
,   h1_nm varchar(40) -- 시도명
,   h23_nm varchar(40) -- 시군구명
,   ld_nm varchar(40) -- 법정읍면동명
,   ri_nm varchar(40) -- 법정리명
,   san varchar(1) -- 산여부
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
,   constraint "pk_bld_mgt_no" primary key (bld_mgt_no)
);

comment on table geocode.tbbld_info is '건물정보';
comment on column geocode.tbbld_info.ld_cd is '법정동코드';
comment on column geocode.tbbld_info.ld_nm is '법정읍면동명';
comment on column geocode.tbbld_info.h1_nm is '시도명';
comment on column geocode.tbbld_info.h23_nm is '시군구명';
comment on column geocode.tbbld_info.ri_nm is '법정리명';
comment on column geocode.tbbld_info.san is '산여부';
comment on column geocode.tbbld_info.bng1 is '지번본번';
comment on column geocode.tbbld_info.bng2 is '지번부번';
comment on column geocode.tbbld_info.road_cd is '도로명코드 시군구코드(5) + 도로명번호(7)';
comment on column geocode.tbbld_info.road_nm is '도로명';
comment on column geocode.tbbld_info.undgrnd_yn is '지하여부 0:지상, 1:지하, 2:공중';
comment on column geocode.tbbld_info.bld1 is '건물본번';
comment on column geocode.tbbld_info.bld2 is '건물부번';
comment on column geocode.tbbld_info.bld_reg is '건축물대장건물명';
comment on column geocode.tbbld_info.bld_nm is '상세건물명';
comment on column geocode.tbbld_info.bld_mgt_no is '건물관리번호';
comment on column geocode.tbbld_info.ld_seq is '읍면동일련번호';
comment on column geocode.tbbld_info.h4_cd is '행정동코드';
comment on column geocode.tbbld_info.h4_nm is '행정동명';
comment on column geocode.tbbld_info.zip is '우편번호';
comment on column geocode.tbbld_info.zip_seq is '-- 우편일련번호 2015. 8. 1 이후 미제공(null)';
comment on column geocode.tbbld_info.lg_dlvr_nm is '-- 다량배달처명 2015. 8. 1 이후 미제공(null)';
comment on column geocode.tbbld_info.mvmn_resn_cd is '이동사유코드 31 : 신규, 34 : 변동, 63 : 폐지, 72 : 건물군내 일부 건물 폐지, 73 : 건물군내 일부 건물 생성';
comment on column geocode.tbbld_info.ntfc_de is '고시일자';
comment on column geocode.tbbld_info.old_road_addr is '변동전도로명주소';
comment on column geocode.tbbld_info.bld_nm_text is '시군구용건물명';
comment on column geocode.tbbld_info.apt_yn is '공동주택여부 0:비공동주택, 1:공동주택';
comment on column geocode.tbbld_info.bas_no is '기초구역번호';
comment on column geocode.tbbld_info.dtl_addr_yn is '상세주소여부 0:미부여, 1:부여';
comment on column geocode.tbbld_info.rm1 is '비고1';
comment on column geocode.tbbld_info.rm2 is '비고2';

create table geocode.tbbld_info_load (
    ld_cd varchar(10) -- 법정동코드
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
,   constraint "pk_bld_mgt_no_load" primary key (bld_mgt_no)
);
```

### load

COPY statement는 관리자 권한으로 실행. \copy command는 소유자 권한으로 실행 가능.

~~~> %sudo -i -u postgres~~~
> %psql -d geocode

```sql
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_busan.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_chungbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_chungnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_daegu.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_daejeon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_gangwon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_gwangju.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_gyeongbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_gyeongnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_gyunggi.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_incheon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_jeju.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_jeonbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_jeonnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_sejong.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_seoul.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbbld_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/build_ulsan.txt' WITH DELIMITER '|' ENCODING 'WIN949';
```

### transfer

```sql
insert into geocode.tbbld_info
select * from geocode.tbbld_info_load;
```

## 관련지번

> $ ls -1 $PWD/jibun*.txt

```bash
~/ssd2/juso-data/202007_건물DB_전체분/jibun_busan.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_chungbuk.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_chungnam.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_daegu.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_daejeon.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_gangwon.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_gwangju.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_gyeongbuk.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_gyeongnam.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_gyunggi.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_incheon.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_jeju.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_jeonbuk.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_jeonnam.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_sejong.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_seoul.txt
~/ssd2/juso-data/202007_건물DB_전체분/jibun_ulsan.txt
```

```sql
create table geocode.tbrel_jibun_info (
    ld_cd varchar(10)                   --  법정동코드 
,   h1_nm varchar(40)                   --  시도명 
,   h23_nm varchar(40)                  --  시군구명 
,   ld_nm varchar(40)                   --  법정읍면동명 
,   ri_nm varchar(40)                   --  법정리명 
,   san varchar(1)                      --  산여부 
,   bng1 numeric(4)                     --  지번본번(
,   bng2 numeric(4)                     --  지번부번(
,   road_cd varchar(12)                 --  도로명코드 PK1, 시군구코드(5) + 도로명번호(7)
,   undgrnd_yn varchar(1)               --  지하여부 PK2, 0:지상, 1:지하, 2:공중
,   bld1 numeric(5)                     --  건물본번 PK3
,   bld2 numeric(5)                     --  건물부번 PK4
,   jibun_seq numeric(10)               --  지번일련번호 PK5
,   mvmn_resn_cd varchar(2)             --  이동사유코드 
,   constraint "pk_rel_jibun_info" primary key (road_cd, undgrnd_yn, bld1, bld2, jibun_seq)
);

comment on table geocode.tbrel_jibun_info is '관련지번';
comment on column geocode.tbrel_jibun_info.ld_cd is '법정동코드';
comment on column geocode.tbrel_jibun_info.h1_nm is '시도명';
comment on column geocode.tbrel_jibun_info.h23_nm is '시군구명';
comment on column geocode.tbrel_jibun_info.ld_nm is '법정읍면동명';
comment on column geocode.tbrel_jibun_info.ri_nm is '법정리명';
comment on column geocode.tbrel_jibun_info.san is '산여부';
comment on column geocode.tbrel_jibun_info.bng1 is '지번본번';
comment on column geocode.tbrel_jibun_info.bng2 is '지번부번';
comment on column geocode.tbrel_jibun_info.road_cd is '도로명코드: 시군구코드(5) + 도로명번호(7)';
comment on column geocode.tbrel_jibun_info.undgrnd_yn is '지하여부: 0:지상, 1:지하, 2:공중';
comment on column geocode.tbrel_jibun_info.bld1 is '건물본번';
comment on column geocode.tbrel_jibun_info.bld2 is '건물부번';
comment on column geocode.tbrel_jibun_info.jibun_seq is '지번일련번호';
comment on column geocode.tbrel_jibun_info.mvmn_resn_cd is '이동사유코드';

create table geocode.tbrel_jibun_info_load (
    ld_cd varchar(10)                   --  법정동코드 
,   h1_nm varchar(40)                   --  시도명 
,   h23_nm varchar(40)                  --  시군구명 
,   ld_nm varchar(40)                   --  법정읍면동명 
,   ri_nm varchar(40)                   --  법정리명 
,   san varchar(1)                      --  산여부 
,   bng1 numeric(4)                     --  지번본번
,   bng2 numeric(4)                     --  지번부번
,   road_cd varchar(12)                 --  도로명코드 PK1, 시군구코드(5) + 도로명번호(7)
,   undgrnd_yn varchar(1)               --  지하여부 PK2, 0:지상, 1:지하, 2:공중
,   bld1 numeric(5)                     --  건물본번 PK3
,   bld2 numeric(5)                     --  건물부번 PK4
,   jibun_seq numeric(10)               --  지번일련번호 PK5
,   mvmn_resn_cd varchar(2)             --  이동사유코드 
,   constraint "pk_rel_jibun_info_load" primary key (road_cd, undgrnd_yn, bld1, bld2, jibun_seq)
);
```

### load

```sql
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_busan.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_chungbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_chungnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_daegu.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_daejeon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_gangwon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_gwangju.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_gyeongbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_gyeongnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_gyunggi.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_incheon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_jeju.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_jeonbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_jeonnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_sejong.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_seoul.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbrel_jibun_info_load FROM '~/ssd2/juso-data/202007_건물DB_전체분/jibun_ulsan.txt' WITH DELIMITER '|' ENCODING 'WIN949';
```


### transfer

```sql
insert into geocode.tbrel_jibun_info
select * from geocode.tbrel_jibun_info_load;
```

## 도로명코드

~/ssd2/juso-data/202007_건물DB_전체분/road_code_total.txt

```sql
create table geocode.tbroad_code (
    h23_cd varchar(5)   -- 시군구코드  PK1 도로명코드 : 시군구코드(5)+도로명번호(7)
,   road_cd varchar(7)  -- 도로명번호  PK1 도로명코드 : 시군구코드(5)+도로명번호(7)
,   road_nm varchar(80) -- 도로명  
,   eng_road_nm varchar(80) -- 영문도로명  
,   ld_seq varchar(2)   -- 읍면동일련번호  PK2
,   h1_nm varchar(40)   -- 시도명  
,   h23_nm varchar(40)  -- 시군구명  
,   ld_clss varchar(1)  -- 읍면동구분  0:읍면, 1:동, 2:미부여
,   ld_cd varchar(3)    -- 읍면동코드  법정동 기준 읍면동 코드
,   ld_nm varchar(40)   -- 읍면동명  
,   parent_road_no varchar(7)   -- 상위도로명번호  
,   parent_road_nm varchar(80)  -- 상위도로명  
,   use_yn varchar(1)   -- 사용여부  0:사용, 1:미사용
,   hist_cd varchar(1)  -- 변경이력사유  0:도로명변경, 1:도로명폐지, 2:시도시굮구변경, 3:읍면동변경, 4:영문도로명변경, 9:기타
,   hist varchar(14)    -- 변경이력정보  도로명코드(12)+ 읍면동일련번호(2) 신규 정보일 경우 신규로 표시
,   eng_h1_nm varchar(40)   -- 영문시도명  
,   eng_h23_nm varchar(40)  -- 영문시군구명  
,   eng_ld_nm varchar(40)   -- 영문읍면동명  
,   ntfc_de varchar(8)  -- 도로명 코드 고시일자(YYYYMMDD)
,   ersr_de varchar(8)  -- 도로명 코드 말소일자(YYYYMMDD)
,   constraint pk_road_code primary key (h23_cd, road_cd, ld_seq)
);

comment on table geocode.tbroad_code is '도로명코드';

comment on column geocode.tbroad_code.h23_cd is '시군구코드  PK1 도로명코드 : 시군구코드(5)+도로명번호(7)';
comment on column geocode.tbroad_code.road_cd is '도로명번호  PK1 도로명코드 : 시군구코드(5)+도로명번호(7)';
comment on column geocode.tbroad_code.road_nm is '도로명';
comment on column geocode.tbroad_code.eng_road_nm is '영문도로명';
comment on column geocode.tbroad_code.ld_seq is '읍면동일련번호  PK2';
comment on column geocode.tbroad_code.h1_nm is '시도명';
comment on column geocode.tbroad_code.h23_nm is '시군구명';
comment on column geocode.tbroad_code.ld_clss is '읍면동구분  0:읍면, 1:동, 2:미부여';
comment on column geocode.tbroad_code.ld_cd is '읍면동코드  법정동 기준 읍면동 코드';
comment on column geocode.tbroad_code.ld_nm is '읍면동명';
comment on column geocode.tbroad_code.parent_road_no is '상위도로명번호';
comment on column geocode.tbroad_code.parent_road_nm is '상위도로명';
comment on column geocode.tbroad_code.use_yn is '사용여부  0:사용, 1:미사용';
comment on column geocode.tbroad_code.hist_cd is '변경이력사유  0:도로명변경, 1:도로명폐지, 2:시도시굮구변경, 3:읍면동변경, 4:영문도로명변경, 9:기타';
comment on column geocode.tbroad_code.hist is '변경이력정보  도로명코드(12)+ 읍면동일련번호(2) 신규 정보일 경우 신규로 표시';
comment on column geocode.tbroad_code.eng_h1_nm is '영문시도명';
comment on column geocode.tbroad_code.eng_h23_nm is '영문시군구명';
comment on column geocode.tbroad_code.eng_ld_nm is '영문읍면동명';
comment on column geocode.tbroad_code.ntfc_de is '도로명 코드 고시일자(YYYYMMDD)';
comment on column geocode.tbroad_code.ersr_de is '도로명 코드 말소일자(YYYYMMDD)';

create table geocode.tbroad_code_load (
    h23_cd varchar(5)   -- 시군구코드  PK1 도로명코드 : 시군구코드(5)+도로명번호(7)
,   road_cd varchar(7)  -- 도로명번호  PK1 도로명코드 : 시군구코드(5)+도로명번호(7)
,   road_nm varchar(80) -- 도로명  
,   eng_road_nm varchar(80) -- 영문도로명  
,   ld_seq varchar(2)   -- 읍면동일련번호  PK2
,   h1_nm varchar(40)   -- 시도명  
,   h23_nm varchar(40)  -- 시군구명  
,   ld_clss varchar(1)  -- 읍면동구분  0:읍면, 1:동, 2:미부여
,   ld_cd varchar(3)    -- 읍면동코드  법정동 기준 읍면동 코드
,   ld_nm varchar(40)   -- 읍면동명  
,   parent_road_no varchar(7)   -- 상위도로명번호  
,   parent_road_nm varchar(80)  -- 상위도로명  
,   use_yn varchar(1)   -- 사용여부  0:사용, 1:미사용
,   hist_cd varchar(1)  -- 변경이력사유  0:도로명변경, 1:도로명폐지, 2:시도시굮구변경, 3:읍면동변경, 4:영문도로명변경, 9:기타
,   hist varchar(14)    -- 변경이력정보  도로명코드(12)+ 읍면동일련번호(2) 신규 정보일 경우 신규로 표시
,   eng_h1_nm varchar(40)   -- 영문시도명  
,   eng_h23_nm varchar(40)  -- 영문시군구명  
,   eng_ld_nm varchar(40)   -- 영문읍면동명  
,   ntfc_de varchar(8)  -- 도로명 코드 고시일자(YYYYMMDD)
,   ersr_de varchar(8)  -- 도로명 코드 말소일자(YYYYMMDD)
,   constraint pk_road_code_load primary key (h23_cd, road_cd, ld_seq)
);
```

\copy geocode.tbroad_code_load from '~/ssd2/juso-data/202007_건물DB_전체분/road_code_total.txt' WITH DELIMITER '|' ENCODING 'WIN949';

### transfer

```sql
insert into geocode.tbroad_code
select * from geocode.tbroad_code_load;
```



# 내비게이션용

## 건물정보

match_build_시도명.txt

> $ ls -1 $PWD/match_build_*.txt

```bash
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_busan.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_chungbuk.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_chungnam.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_daegu.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_daejeon.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_gangwon.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_gwangju.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_gyeongbuk.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_gyeongnam.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_gyunggi.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_incheon.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_jeju.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_jeonbuk.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_jeonnam.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_sejong.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_seoul.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_ulsan.txt
```

```sql
create table geocode.tbnavi_match_bld (
    h4_10cd varchar(10)              -- 주소관할읍면동코드 10 문자 시군구코드(5)+읍면동코드(3)+00
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
,   constraint pk_navi_match_bld primary key (bld_mgt_no)
);

comment on table geocode.tbnavi_match_bld is '내비게이션 건물정보';

comment on column geocode.tbnavi_match_bld.h4_10cd is '주소관할읍면동코드 10 문자 시군구코드(5)+읍면동코드(3)+00';
comment on column geocode.tbnavi_match_bld.h1_nm is '시도명';
comment on column geocode.tbnavi_match_bld.h23_nm is '시군구명';
comment on column geocode.tbnavi_match_bld.ld_nm is '읍면동명';
comment on column geocode.tbnavi_match_bld.road_cd is '도로명코드 시군구코드(5) + 도로명번호(7)';
comment on column geocode.tbnavi_match_bld.road_nm is '도로명';
comment on column geocode.tbnavi_match_bld.undgrnd_yn is '지하여부';
comment on column geocode.tbnavi_match_bld.bld1 is '건물본번';
comment on column geocode.tbnavi_match_bld.bld2 is '건물부번';
comment on column geocode.tbnavi_match_bld.zip is '우편번호';
comment on column geocode.tbnavi_match_bld.bld_mgt_no is '건물관리번호 PK';
comment on column geocode.tbnavi_match_bld.bld_nm_text is '시군구용건물명';
comment on column geocode.tbnavi_match_bld.bld_clss is '건축물용도분류';
comment on column geocode.tbnavi_match_bld.h4_cd is '행정동코드';
comment on column geocode.tbnavi_match_bld.h4_nm is '행정동명';
comment on column geocode.tbnavi_match_bld.ground_floor is '지상층수';
comment on column geocode.tbnavi_match_bld.undground_floor is '지하층수';
comment on column geocode.tbnavi_match_bld.apt_yn is '공동주택구분 0 : 비공동주택, 1 : 공동주택(아파트), 2 :공동주택(연립/다세대 등)';
comment on column geocode.tbnavi_match_bld.bld_cnt is '건물수. 같은 주소를 갖는 건물의 수(건물군의 경우 동일한 값)';
comment on column geocode.tbnavi_match_bld.bld_nm is '상세건물명';
comment on column geocode.tbnavi_match_bld.bld_nm_major_hist is '건물명변경이력. 건물명이 변경된 경우 최초부터 최종변경 건물명을 나열';
comment on column geocode.tbnavi_match_bld.bld_nm_hist is '상세건물명변경이력. 상세건물명이 변경된 경우 최초부터 최종 변경 상세건물명을 나열';
comment on column geocode.tbnavi_match_bld.RESIDENCE_yn is '거주여부 0 : 비거주, 1 : 거주';
comment on column geocode.tbnavi_match_bld.bld_x is '건물중심점_x좌표 GRS80 UTM-K 좌표계';
comment on column geocode.tbnavi_match_bld.bld_y is '건물중심점_y좌표 GRS80 UTM-K 좌표계';
comment on column geocode.tbnavi_match_bld.ent_x is '출입구_x좌표 GRS80 UTM-K 좌표계';
comment on column geocode.tbnavi_match_bld.ent_y is '출입구_y좌표 GRS80 UTM-K 좌표계';
comment on column geocode.tbnavi_match_bld.eng_h1_nm is '시도명(영문)';
comment on column geocode.tbnavi_match_bld.eng_h23_nm is '시군구명(영문)';
comment on column geocode.tbnavi_match_bld.eng_ld_nm is '읍면동명(영문)';
comment on column geocode.tbnavi_match_bld.eng_road_nm is '도로명(영문)';
comment on column geocode.tbnavi_match_bld.ld_clss is '읍면동구분 0 : 읍면, 1 : 동';
comment on column geocode.tbnavi_match_bld.mvmn_resn_cd is '이동사유코드 31 : 신규, 34 : 변경, 63 : 삭제';

create table geocode.tbnavi_match_bld_load (
    h4_10cd varchar(10) -- 주소관할읍면동코드 10 문자 시군구코드(5)+읍면동코드(3)+00
,   h1_nm varchar(40) -- 시도명 40 문자
,   h23_nm varchar(40) -- 시군구명 40 문자
,   ld_nm varchar(40) -- 읍면동명 40 문자
,   road_cd varchar(12) -- 도로명코드 12 문자 시군구코드(5) + 도로명번호(7)
,   road_nm varchar(80) -- 도로명 80 문자
,   undgrnd_yn varchar(1) -- 지하여부 1 문자
,   bld1 numeric(5) -- 건물본번 5 숫자
,   bld2 numeric(5) -- 건물부번 5 숫자
,   zip varchar(5) -- 우편번호 5 문자
,   bld_mgt_no varchar(25) -- 건물관리번호 25 문자 PK
,   bld_nm_text varchar(40) -- 시군구용건물명 40 문자
,   bld_clss varchar(100) -- 건축물용도분류 100 문자
,   h4_cd varchar(10) -- 행정동코드 10 문자
,   h4_nm varchar(40) -- 행정동명 40 문자
,   ground_floor numeric(3) -- 지상층수 3 숫자
,   undground_floor numeric(3) -- 지하층수 3 숫자
,   apt_yn varchar(1) -- 공동주택구분 1 문자 0 : 비공동주택, 1 : 공동주택(아파트), 2 :공동주택(연립/다세대 등)
,   bld_cnt numeric(10) -- 건물수 10 숫자 같은 주소를 갖는 건물의 수(건물군의 경우 동일한 값)
,   bld_nm varchar(100) -- 상세건물명 100 문자
,   bld_nm_major_hist varchar(1000) -- 건물명변경이력 1000 문자 건물명이 변경된 경우 최초부터 최종변경 건물명을 나열
,   bld_nm_hist varchar(1000) -- 상세건물명변경이력 1000 문자 상세건물명이 변경된 경우 최초부터 최종 변경 상세건물명을 나열
,   RESIDENCE_yn varchar(1) -- 거주여부 1 문자 0 : 비거주, 1 : 거주
,   bld_x varchar(15) -- 건물중심점_x좌표 15, 6 숫자 GRS80 UTM-K 좌표계
,   bld_y varchar(15) -- 건물중심점_y좌표 15, 6 숫자 GRS80 UTM-K 좌표계
,   ent_x varchar(15) -- 출입구_x좌표 15, 6 숫자 GRS80 UTM-K 좌표계
,   ent_y varchar(15) -- 출입구_y좌표 15, 6 숫자 GRS80 UTM-K 좌표계
,   eng_h1_nm varchar(40) -- 시도명(영문) 40 문자
,   eng_h23_nm varchar(40) -- 시군구명(영문) 40 문자
,   eng_ld_nm varchar(40) -- 읍면동명(영문) 40 문자
,   eng_road_nm varchar(80) -- 도로명(영문) 80 문자
,   ld_clss varchar(1) -- 읍면동구분 1 문자 0 : 읍면, 1 : 동
,   mvmn_resn_cd varchar(2) -- 이동사유코드 2 문자 31 : 신규, 34 : 변경, 63 : 삭제
,   constraint pk_navi_match_bld_load primary key (bld_mgt_no)
);
```

### load

```sql
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_busan.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_chungbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_chungnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_daegu.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_daejeon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_gangwon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_gwangju.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_gyeongbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_gyeongnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_gyunggi.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_incheon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_jeju.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_jeonbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_jeonnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_sejong.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_seoul.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_bld_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_build_ulsan.txt' WITH DELIMITER '|' ENCODING 'WIN949';
```

### transfer

```sql
insert into geocode.tbnavi_match_bld
select * from geocode.tbnavi_match_bld_load;
```

## 지번정보

match_jibun_시도명.txt

> $ ls -1 $PWD/match_jibun_*.txt

```bash
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_busan.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_chungbuk.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_chungnam.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_daegu.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_daejeon.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_gangwon.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_gwangju.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_gyeongbuk.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_gyeongnam.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_gyunggi.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_incheon.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_jeju.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_jeonbuk.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_jeonnam.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_sejong.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_seoul.txt
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_ulsan.txt
```

```sql
create table geocode.tbnavi_match_jibun (
    ld_cd varchar(10)-- 법정동코드  시군구코드(5)+읍면동코드(3)+리코드(2)
,   h1_nm varchar(40)-- 시도명 
,   h23_nm varchar(40)-- 시군구명 
,   ld_nm varchar(40)-- 읍면동명 
,   ri_nm varchar(40)-- 리명 
,   san varchar(1)-- 산여부 
,   bng1 numeric(4)-- 지번본번 
,   bng2 numeric(4)-- 지번부번 
,   road_cd varchar(12)-- 도로명코드  PK1
,   undgrnd_yn varchar(1)-- 지하여부  PK2
,   bld1 numeric(5)-- 건물본번  PK3
,   bld2 numeric(5)-- 건물부번  PK4
,   jubun_seq numeric(10) -- 지번일련번호 PK5, 0 : 대표지번, 그외는 관련지번
,   eng_h1_nm varchar(40)-- 시도명(영문) 
,   eng_h23_nm varchar(40)-- 시군구명(영문) 
,   eng_ld_nm varchar(40)-- 읍면동명(영문) 
,   eng_ri_nm varchar(40)-- 리명(영문) 
,   mvmn_resn_cd varchar(2)-- 이동사유코드  31 : 신규, 34 : 변경, 63 : 삭제
,   bld_mgt_no varchar(25)-- 건물관리번호 
,   h4_10cd varchar(10)-- 주소관할읍면동코드  PK6 (건물정보 1번항목과 동일)
,   constraint "pk_navi_match_jibun" primary key (road_cd, undgrnd_yn, bld1, bld2, jubun_seq, h4_10cd) 
);

comment on table geocode.tbnavi_match_jibun is '내비게이션 지번정보';
comment on column geocode.tbnavi_match_jibun.ld_cd is '법정동코드  시군구코드(5)+읍면동코드(3)+리코드(2)';
comment on column geocode.tbnavi_match_jibun.h1_nm is '시도명';
comment on column geocode.tbnavi_match_jibun.h23_nm is '시군구명 ';
comment on column geocode.tbnavi_match_jibun.ld_nm is '읍면동명';
comment on column geocode.tbnavi_match_jibun.ri_nm is '리명';
comment on column geocode.tbnavi_match_jibun.san is '산여부';
comment on column geocode.tbnavi_match_jibun.bng1 is '지번본번';
comment on column geocode.tbnavi_match_jibun.bng2 is '지번부번';
comment on column geocode.tbnavi_match_jibun.road_cd is '도로명코드  PK1';
comment on column geocode.tbnavi_match_jibun.undgrnd_yn is '지하여부  PK2';
comment on column geocode.tbnavi_match_jibun.bld1 is '건물본번  PK3';
comment on column geocode.tbnavi_match_jibun.bld2 is '건물부번  PK4';
comment on column geocode.tbnavi_match_jibun.jubun_seq is '-- 지번일련번호 PK5, 0 : 대표지번, 그외는 관련지번';
comment on column geocode.tbnavi_match_jibun.eng_h1_nm is '시도명(영문)';
comment on column geocode.tbnavi_match_jibun.eng_h23_nm is '시군구명(영문)';
comment on column geocode.tbnavi_match_jibun.eng_ld_nm is '읍면동명(영문)';
comment on column geocode.tbnavi_match_jibun.eng_ri_nm is '리명(영문)';
comment on column geocode.tbnavi_match_jibun.mvmn_resn_cd is '이동사유코드  31 : 신규, 34 : 변경, 63 : 삭제';
comment on column geocode.tbnavi_match_jibun.bld_mgt_no is '건물관리번호';
comment on column geocode.tbnavi_match_jibun.h4_10cd is '주소관할읍면동코드  PK6 (건물정보 1번항목과 동일)';

create table geocode.tbnavi_match_jibun_load (
    ld_cd varchar(10)-- 법정동코드  시군구코드(5)+읍면동코드(3)+리코드(2)
,   h1_nm varchar(40)-- 시도명 
,   h23_nm varchar(40)-- 시군구명 
,   ld_nm varchar(40)-- 읍면동명 
,   ri_nm varchar(40)-- 리명 
,   san varchar(1)-- 산여부 
,   bng1 numeric(4)-- 지번본번 
,   bng2 numeric(4)-- 지번부번 
,   road_cd varchar(12)-- 도로명코드  PK1
,   undgrnd_yn varchar(1)-- 지하여부  PK2
,   bld1 numeric(5)-- 건물본번  PK3
,   bld2 numeric(5)-- 건물부번  PK4
,   jubun_seq numeric(10) -- 지번일련번호 PK5, 0 : 대표지번, 그외는 관련지번
,   eng_h1_nm varchar(40)-- 시도명(영문) 
,   eng_h23_nm varchar(40)-- 시군구명(영문) 
,   eng_ld_nm varchar(40)-- 읍면동명(영문) 
,   eng_ri_nm varchar(40)-- 리명(영문) 
,   mvmn_resn_cd varchar(2)-- 이동사유코드  31 : 신규, 34 : 변경, 63 : 삭제
,   bld_mgt_no varchar(25)-- 건물관리번호 
,   h4_10cd varchar(10)-- 주소관할읍면동코드  PK6 (건물정보 1번항목과 동일)
,   constraint "pk_navi_match_jibun_load" primary key (road_cd, undgrnd_yn, bld1, bld2, jubun_seq, h4_10cd) 
);
```

### load

관리자 권한으로 실행.

> %sudo -i -u postgres
> %psql -d geocode

```sql
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_busan.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_chungbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_chungnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_daegu.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_daejeon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_gangwon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_gwangju.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_gyeongbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_gyeongnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_gyunggi.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_incheon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_jeju.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_jeonbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_jeonnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_sejong.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_seoul.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbnavi_match_jibun_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_jibun_ulsan.txt' WITH DELIMITER '|' ENCODING 'WIN949';
```

### transfer

```sql
insert into geocode.tbnavi_match_jibun
select * from geocode.tbnavi_match_jibun_load;
```


## 보조출입구

match_rs_entrc.txt

```bash
~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_rs_entrc.txt
```

```sql
create table geocode.tbnavi_match_rs_entrc (
    h23_cd       varchar(5)     -- 시군구코드  PK1
,   ent_seq      numeric(10)    -- 출입구일련번호  PK2
,   road_cd      varchar(12)    -- 도로명코드  시군구코드(5) + 도로명번호(7)
,   undgrnd_yn   varchar(1)     -- 지하여부 
,   bld1         numeric(5)     -- 건물본번 
,   bld2         numeric(5)     -- 건물부번 
,   ld_cd        varchar(10)    -- 법정동코드  시군구코드(5)+읍면동코드(3)+00
,   ent_clss     varchar(2)     -- 출입구유형  01' : 공용, '02' : 차량용, '03' : 보행자용
,   ent_x        numeric(15, 6) -- 출입구_x좌표,  GRS80 UTM-K 좌표계
,   ent_y        numeric(15, 6) -- 출입구_y좌표,  GRS80 UTM-K 좌표계
,   mvmn_resn_cd varchar(2)     -- 이동사유코드  31 : 신규, 34 : 변경, 63 : 삭제
,   constraint "pk_navi_match_rs_entrc" primary key (h23_cd, ent_seq) 
);

comment on table geocode.tbnavi_match_rs_entrc is '내비게이션 보조출입구';
comment on column geocode.tbnavi_match_rs_entrc.h23_cd is '시군구코드  PK1';
comment on column geocode.tbnavi_match_rs_entrc.ent_seq is '출입구일련번호  PK2';
comment on column geocode.tbnavi_match_rs_entrc.road_cd is '도로명코드  시군구코드(5) + 도로명번호(7)';
comment on column geocode.tbnavi_match_rs_entrc.undgrnd_yn is '지하여부 ';
comment on column geocode.tbnavi_match_rs_entrc.bld1 is '건물본번 ';
comment on column geocode.tbnavi_match_rs_entrc.bld2 is '건물부번 ';
comment on column geocode.tbnavi_match_rs_entrc.ld_cd is '법정동코드  시군구코드(5)+읍면동코드(3)+00';
comment on column geocode.tbnavi_match_rs_entrc.ent_clss is '출입구유형  01 : 공용, 02 : 차량용, 03 : 보행자용';
comment on column geocode.tbnavi_match_rs_entrc.ent_x is '출입구_x좌표 15,  GRS80 UTM-K 좌표계';
comment on column geocode.tbnavi_match_rs_entrc.ent_y is '출입구_y좌표 15,  GRS80 UTM-K 좌표계';
comment on column geocode.tbnavi_match_rs_entrc.mvmn_resn_cd is '이동사유코드  31 : 신규, 34 : 변경, 63 : 삭제';

create table geocode.tbnavi_match_rs_entrc_load (
    h23_cd       varchar(5)     -- 시군구코드  PK1
,   ent_seq      numeric(10)    -- 출입구일련번호  PK2
,   road_cd      varchar(12)    -- 도로명코드  시군구코드(5) + 도로명번호(7)
,   undgrnd_yn   varchar(1)     -- 지하여부 
,   bld1         numeric(5)     -- 건물본번 
,   bld2         numeric(5)     -- 건물부번 
,   ld_cd        varchar(10)    -- 법정동코드  시군구코드(5)+읍면동코드(3)+00
,   ent_clss     varchar(2)     -- 출입구유형  01' : 공용, '02' : 차량용, '03' : 보행자용
,   ent_x        numeric(15, 6) -- 출입구_x좌표,  GRS80 UTM-K 좌표계
,   ent_y        numeric(15, 6) -- 출입구_y좌표,  GRS80 UTM-K 좌표계
,   mvmn_resn_cd varchar(2)     -- 이동사유코드  31 : 신규, 34 : 변경, 63 : 삭제
,   constraint "pk_navi_match_rs_entrc_load" primary key (h23_cd, ent_seq) 
);
```

### load

관리자 권한으로 실행.

> %sudo -i -u postgres
> %psql -d geocode

```sql
\COPY geocode.tbnavi_match_rs_entrc_load FROM '~/ssd2/juso-data/202007_내비게이션용DB_전체분/match_rs_entrc.txt' WITH DELIMITER '|' ENCODING 'WIN949';
```

### transfer

```sql
insert into geocode.tbnavi_match_rs_entrc
select * from geocode.tbnavi_match_rs_entrc_load;
```

# 상세주소DB

adrdc_시도명.txt

> $ ls -1 $PWD/adrdc_*.txt

```bash
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_busan.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_chungbuk.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_chungnam.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_daegu.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_daejeon.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_gangwon.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_gwangju.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_gyeongbuk.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_gyeongnam.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_gyunggi.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_incheon.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_jeju.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_jeonbuk.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_jeonnam.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_sejong.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_seoul.txt
~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_ulsan.txt
```

```sql
create table geocode.tbadrdc (
    h23_cd varchar(5)            -- 시군구코드  PK 1
,   dong_seq numeric(10)         -- 동일련번호  PK 2
,   floor_seq numeric(10)        -- 층일련번호  PK 3 (없을 경우 0)
,   ho_seq numeric(10)           -- 호일련번호  PK 4 (없을 경우 0)
,   ho_suffix_seq numeric(10)    -- 호접미사일련번호  PK 5 (없을 경우 0)
,   dong_nm varchar(50)          -- 동명칭 
,   floor_nm varchar(50)         -- 층명칭 
,   ho_nm varchar(50)            -- 호명칭 
,   ho_suffix_nm varchar(10)     -- 호접미사명칭  호 상세구분 예) 101호 A, 101호 B
,   undgrnd_clss varchar(1)      -- 지하구분  지하층 구분 0 : 일반, 1 : 지하
,   bld_mgt_no varchar(25)       -- 건물관리번호  건물 연계Key
,   ld_cd varchar(10)            -- 법정동코드  도로명주소 연계Key 1
,   road_cd varchar(12)          -- 도로명코드  도로명주소 연계Key 2
,   undgrnd_yn varchar(1)        -- 지하여부  도로명주소 연계Key 3
,   bld1 numeric(5)              -- 건물본번  도로명주소 연계Key 4
,   bld2 numeric(5)              -- 건물부번  도로명주소 연계Key 5
,   constraint pk_adrdc primary key(h23_cd, dong_seq, floor_seq, ho_seq, ho_suffix_seq)
);

comment on table geocode.tbadrdc is '상세주소';
comment on column geocode.tbadrdc.h23_cd is '시군구코드  PK 1';
comment on column geocode.tbadrdc.dong_seq is '동일련번호  PK 2';
comment on column geocode.tbadrdc.floor_seq is '층일련번호  PK 3 (없을 경우 0)';
comment on column geocode.tbadrdc.ho_seq is '호일련번호  PK 4 (없을 경우 0)';
comment on column geocode.tbadrdc.ho_suffix_seq is '호접미사일련번호  PK 5 (없을 경우 0)';
comment on column geocode.tbadrdc.dong_nm is '동명칭 ';
comment on column geocode.tbadrdc.floor_nm is '층명칭 ';
comment on column geocode.tbadrdc.ho_nm is '호명칭 ';
comment on column geocode.tbadrdc.ho_suffix_nm is '호접미사명칭  호 상세구분 예) 101호 A, 101호 B';
comment on column geocode.tbadrdc.undgrnd_clss is '지하구분  지하층 구분 0 : 일반, 1 : 지하';
comment on column geocode.tbadrdc.bld_mgt_no is '건물관리번호  건물 연계Key';
comment on column geocode.tbadrdc.ld_cd is '법정동코드  도로명주소 연계Key 1';
comment on column geocode.tbadrdc.road_cd is '도로명코드  도로명주소 연계Key 2';
comment on column geocode.tbadrdc.undgrnd_yn is '지하여부  도로명주소 연계Key 3';
comment on column geocode.tbadrdc.bld1 is '건물본번  도로명주소 연계Key 4';
comment on column geocode.tbadrdc.bld2 is '건물부번  도로명주소 연계Key 5';

create table geocode.tbadrdc_load (
    h23_cd varchar(5)            -- 시군구코드  PK 1
,   dong_seq numeric(10)         -- 동일련번호  PK 2
,   floor_seq numeric(10)        -- 층일련번호  PK 3 (없을 경우 0)
,   ho_seq numeric(10)           -- 호일련번호  PK 4 (없을 경우 0)
,   ho_suffix_seq numeric(10)    -- 호접미사일련번호  PK 5 (없을 경우 0)
,   dong_nm varchar(50)          -- 동명칭 
,   floor_nm varchar(50)         -- 층명칭 
,   ho_nm varchar(50)            -- 호명칭 
,   ho_suffix_nm varchar(10)     -- 호접미사명칭  호 상세구분 예) 101호 A, 101호 B
,   undgrnd_clss varchar(1)      -- 지하구분  지하층 구분 0 : 일반, 1 : 지하
,   bld_mgt_no varchar(25)       -- 건물관리번호  건물 연계Key
,   ld_cd varchar(10)            -- 법정동코드  도로명주소 연계Key 1
,   road_cd varchar(12)          -- 도로명코드  도로명주소 연계Key 2
,   undgrnd_yn varchar(1)        -- 지하여부  도로명주소 연계Key 3
,   bld1 numeric(5)              -- 건물본번  도로명주소 연계Key 4
,   bld2 numeric(5)              -- 건물부번  도로명주소 연계Key 5
,   constraint pk_adrdc_load primary key(h23_cd, dong_seq, floor_seq, ho_seq, ho_suffix_seq)
);
```

### load

관리자 권한으로 실행.

> %sudo -i -u postgres
> %psql -d geocode

```sql
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_busan.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_chungbuk.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_chungnam.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_daegu.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_daejeon.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_gangwon.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_gwangju.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_gyeongbuk.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_gyeongnam.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_gyunggi.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_incheon.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_jeju.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_jeonbuk.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_jeonnam.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_sejong.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_seoul.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbadrdc_load FROM '~/ssd2/juso-data/202007_상세주소DB_전체분/adrdc_ulsan.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
```

### transfer

```sql
insert into geocode.tbadrdc
select * from geocode.tbadrdc_load;
```

#  위치정보요약DB 전체분

도로명주소와 주출입구의 위치 값이 매핑된 위치정보요약 자료입니다.

entrc_시도명.txt
> $ ls -1 $PWD/entrc_*.txt

```bash
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_busan.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_chungbuk.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_chungnam.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_daegu.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_daejeon.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_gangwon.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_gwangju.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_gyeongbuk.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_gyeongnam.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_gyunggi.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_incheon.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_jeju.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_jeonbuk.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_jeonnam.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_sejong.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_seoul.txt
~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_ulsan.txt
```

```sql
create table geocode.tbentrc (
    h23_cd  varchar(5)           -- 시군구코드
,   ent_seq  varchar(10)         -- 출입구일련번호
,   ld_cd  varchar(10)           -- 법정동코드 PK5 (시군구코드(5) + 읍면동코드(3) + 00) 
,   h1_nm  varchar(40)           -- 시도명
,   h23_nm  varchar(40)          -- 시군구명
,   ld_nm  varchar(40)           -- 읍면동명
,   road_cd  varchar(12)         -- 도로명코드 PK1 (시군구코드(5)+도로명번호(7)) 
,   road_nm  varchar(80)         -- 도로명
,   undgrnd_yn  varchar(1)       -- 지하여부. PK2 
,   bld1    numeric(5)           -- 건물본번. PK3       
,   bld2    numeric(5)           -- 건물부번. PK4       
,   bld_nm  varchar(40)          -- 건물명 
,   zip  varchar(5)              -- 우편번호 
,   bld_clss_list  varchar(100)  -- 건물용도분류. 복수 건물용도가 존재시 콤마(,)로 구분 
,   bld_group_yn  varchar(1)     -- 건물군여부. 0:단독건물, 1:건물군 
,   h4_nm  varchar(40)            -- 관할행정동. * 참고용 
,   ent_x   numeric(15,6)        -- X좌표
,   ent_y   numeric(15,6)        -- Y좌표
,   constraint pk_entrc primary key(road_cd, undgrnd_yn, bld1, bld2, ld_cd)
);

comment on table geocode.tbentrc is '위치정보요약';
comment on column geocode.tbentrc.h23_cd is '시군구코드';
comment on column geocode.tbentrc.ent_seq is '출입구일련번호';
comment on column geocode.tbentrc.ld_cd is '법정동코드 PK5 (시군구코드(5) + 읍면동코드(3) + 00)';
comment on column geocode.tbentrc.h1_nm is '시도명';
comment on column geocode.tbentrc.h23_nm is '시군구명';
comment on column geocode.tbentrc.ld_nm is '읍면동명';
comment on column geocode.tbentrc.road_cd is '도로명코드 PK1 (시군구코드(5)+도로명번호(7))';
comment on column geocode.tbentrc.road_nm is '도로명';
comment on column geocode.tbentrc.undgrnd_yn is '지하여부 PK2';
comment on column geocode.tbentrc.bld1 is '건물본번 PK3';
comment on column geocode.tbentrc.bld2 is '건물부번 PK4';
comment on column geocode.tbentrc.bld_nm is '건물명';
comment on column geocode.tbentrc.zip is '우편번호';
comment on column geocode.tbentrc.bld_clss_list is '건물용도분류 복수 건물용도가 존재시 콤마(,)로 구분';
comment on column geocode.tbentrc.bld_group_yn is '건물군여부 0:단독건물, 1:건물군';
comment on column geocode.tbentrc.h4_nm is '관할행정동 * 참고용';
comment on column geocode.tbentrc.ent_x is 'X좌표';
comment on column geocode.tbentrc.ent_y is 'Y좌표';

create table geocode.tbentrc_load (
    h23_cd  varchar(5)           -- 시군구코드
,   ent_seq  varchar(10)         -- 출입구일련번호
,   ld_cd  varchar(10)           -- 법정동코드 PK5 (시군구코드(5) + 읍면동코드(3) + 00) 
,   h1_nm  varchar(40)           -- 시도명
,   h23_nm  varchar(40)          -- 시군구명
,   ld_nm  varchar(40)           -- 읍면동명
,   road_cd  varchar(12)         -- 도로명코드 PK1 (시군구코드(5)+도로명번호(7)) 
,   road_nm  varchar(80)         -- 도로명
,   undgrnd_yn  varchar(1)       -- 지하여부. PK2 
,   bld1    numeric(5)           -- 건물본번. PK3       
,   bld2    numeric(5)           -- 건물부번. PK4       
,   bld_nm  varchar(40)          -- 건물명. 
,   zip  varchar(5)              -- 우편번호. 
,   bld_clss_list  varchar(100)  -- 건물용도분류. 복수 건물용도가 존재시 콤마(,)로 구분 
,   bld_group_yn  varchar(1)     -- 건물군여부. 0:단독건물, 1:건물군 
,   h4_nm  varchar(40)            -- 관할행정동. * 참고용 
,   ent_x   varchar(15) null   -- X좌표
,   ent_y   varchar(15) null   -- Y좌표
,   constraint pk_entrc_load primary key(road_cd, undgrnd_yn, bld1, bld2, ld_cd)
);
```

### load

관리자 권한으로 실행.

> %sudo -i -u postgres
> %psql -d geocode

ERROR:  invalid input syntax for type numeric: ""
CONTEXT:  COPY tbentrc_load, line 13228, column ent_x: ""

```sql
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_busan.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_chungbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_chungnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_daegu.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_daejeon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_gangwon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_gwangju.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_gyeongbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_gyeongnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_gyunggi.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_incheon.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_jeju.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_jeonbuk.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_jeonnam.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_sejong.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_seoul.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbentrc_load FROM '~/ssd2/juso-data/202007_위치정보요약DB_전체분/entrc_ulsan.txt' WITH DELIMITER '|' ENCODING 'WIN949';
```

### transfer

```sql
insert into geocode.tbentrc
select * from geocode.tbentrc_load;
```


# 주소DB

## 주소정보

주소_시도명.txt
> $ ls -1 $PWD/주소_*.txt

```bash
~/ssd2/juso-data/202007_주소DB_전체분/주소_강원도.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_경기도.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_경상남도.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_경상북도.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_광주광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_대구광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_대전광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_부산광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_서울특별시.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_세종특별자치시.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_울산광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_인천광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_전라남도.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_전라북도.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_제주특별자치도.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_충청남도.txt
~/ssd2/juso-data/202007_주소DB_전체분/주소_충청북도.txt
```

```sql
create table geocode.tbjuso (
    mgt_sn varchar(25)           -- 관리번호  PK
,   road_cd varchar(12)          -- 도로명코드  FK1
,   ld_seq varchar(2)            -- 읍면동일련번호  FK2
,   undgrnd_yn varchar(1)        -- 지하여부  0:지상, 1:지하
,   bld1 numeric(5)              -- 건물본번
,   bld2 numeric(5)              -- 건물부번
,   bas_no varchar(5)            -- 기초구역번호 
,   hist_cd varchar(2)           -- 변경사유코드  31:신규, 34:변경, 63:폐지
,   ntfc_de varchar(8) null      -- 고시일자
,   old_road_addr varchar(25) null -- 변경전도로명주소
,   dtl_addr_yn varchar(1)       -- 상세주소부여 여부  0:미부여, 1:부여
,   constraint pk_juso primary key(mgt_sn)
);

comment on table geocode.tbjuso is '주소';
comment on column geocode.tbjuso.mgt_sn is '관리번호  PK';
comment on column geocode.tbjuso.road_cd is '도로명코드  FK1';
comment on column geocode.tbjuso.ld_seq is '읍면동일련번호  FK2';
comment on column geocode.tbjuso.undgrnd_yn is '지하여부  0:지상, 1:지하';
comment on column geocode.tbjuso.bld1 is '건물본번';
comment on column geocode.tbjuso.bld2 is '건물부번';
comment on column geocode.tbjuso.bas_no is '기초구역번호 ';
comment on column geocode.tbjuso.hist_cd is '변경사유코드  31:신규, 34:변경, 63:폐지';
comment on column geocode.tbjuso.ntfc_de is '고시일자';
comment on column geocode.tbjuso.old_road_addr is '변경전도로명주소';
comment on column geocode.tbjuso.dtl_addr_yn is '상세주소부여 여부  0:미부여, 1:부여';

create table geocode.tbjuso_load (
    mgt_sn varchar(25)           -- 관리번호  PK
,   road_cd varchar(12)          -- 도로명코드  FK1
,   ld_seq varchar(2)            -- 읍면동일련번호  FK2
,   undgrnd_yn varchar(1)        -- 지하여부  0:지상, 1:지하
,   bld1 numeric(5)              -- 건물본번
,   bld2 numeric(5)              -- 건물부번
,   bas_no varchar(5)            -- 기초구역번호 
,   hist_cd varchar(2)           -- 변경사유코드  31:신규, 34:변경, 63:폐지
,   ntfc_de varchar(8) null      -- 고시일자
,   old_road_addr varchar(25) null -- 변경전도로명주소
,   dtl_addr_yn varchar(1)       -- 상세주소부여 여부  0:미부여, 1:부여
,   constraint pk_juso_load primary key(mgt_sn)
);
```

### load

관리자 권한으로 실행.

> %sudo -i -u postgres
> %psql -d geocode

```sql
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_강원도.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_경기도.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_경상남도.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_경상북도.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_광주광역시.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_대구광역시.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_대전광역시.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_부산광역시.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_서울특별시.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_세종특별자치시.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_울산광역시.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_인천광역시.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_전라남도.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_전라북도.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_제주특별자치도.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_충청남도.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjuso_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/주소_충청북도.txt'  WITH DELIMITER '|' ENCODING 'WIN949';
```

### transfer

```sql
insert into geocode.tbjuso
select * from geocode.tbjuso_load;
```

## 지번정보(대표지번 + 관련지번)

지번_시도명.txt
> $ ls -1 $PWD/지번_*.txt

```bash
~/ssd2/juso-data/202007_주소DB_전체분/지번_강원도.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_경기도.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_경상남도.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_경상북도.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_광주광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_대구광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_대전광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_부산광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_서울특별시.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_세종특별자치시.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_울산광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_인천광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_전라남도.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_전라북도.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_제주특별자치도.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_충청남도.txt
~/ssd2/juso-data/202007_주소DB_전체분/지번_충청북도.txt
```

```sql
create table geocode.tbjibun (
    mgt_sn varchar(25)     -- 관리번호  PK1, FK
,   mgt_seq numeric(3)     -- 일련번호  PK2
,   ld_cd varchar(10)      -- 법정동코드 
,   h1_nm varchar(20)      -- 시도명 
,   h23_nm varchar(20)     -- 시군구명 
,   ld_nm varchar(20)      -- 법정읍면동명 
,   ri_nm varchar(20)      -- 법정리명 
,   san varchar(1)         -- 산여부  0:대지, 1:산
,   bng1 numeric(4)        -- 지번본번(번지) 
,   bng2 numeric(4)        -- 지번부번(호) 
,   rep_yn varchar(1)      -- 대표여부  0:관련지번, 1:대표지번
,   constraint pk_jibun primary key(mgt_sn, mgt_seq)
);

comment on table geocode.tbjibun is '지번정보(대표지번 + 관련지번)';
comment on column geocode.tbjibun.mgt_sn is '관리번호  PK1, FK';
comment on column geocode.tbjibun.mgt_seq is '일련번호  PK2';
comment on column geocode.tbjibun.ld_cd is '법정동코드 ';
comment on column geocode.tbjibun.h1_nm is '시도명 ';
comment on column geocode.tbjibun.h23_nm is '시군구명 ';
comment on column geocode.tbjibun.ld_nm is '법정읍면동명 ';
comment on column geocode.tbjibun.ri_nm is '법정리명 ';
comment on column geocode.tbjibun.san is '산여부  0:대지, 1:산';
comment on column geocode.tbjibun.bng1 is '지번본번(번지) ';
comment on column geocode.tbjibun.bng2 is '지번부번(호) ';
comment on column geocode.tbjibun.rep_yn is '대표여부  0:관련지번, 1:대표지번';

create table geocode.tbjibun_load (
    mgt_sn varchar(25)     -- 관리번호  PK1, FK
,   mgt_seq numeric(3)     -- 일련번호  PK2
,   ld_cd varchar(10)      -- 법정동코드 
,   h1_nm varchar(20)      -- 시도명 
,   h23_nm varchar(20)     -- 시군구명 
,   ld_nm varchar(20)      -- 법정읍면동명 
,   ri_nm varchar(20)      -- 법정리명 
,   san varchar(1)         -- 산여부  0:대지, 1:산
,   bng1 numeric(4)        -- 지번본번(번지) 
,   bng2 numeric(4)        -- 지번부번(호) 
,   rep_yn varchar(1)      -- 대표여부  0:관련지번, 1:대표지번
,   constraint pk_jibun_load primary key(mgt_sn, mgt_seq)
);
```

### load

관리자 권한으로 실행.

> %sudo -i -u postgres
> %psql -d geocode

```sql
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_강원도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_경기도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_경상남도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_경상북도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_광주광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_대구광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_대전광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_부산광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_서울특별시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_세종특별자치시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_울산광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_인천광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_전라남도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_전라북도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_제주특별자치도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_충청남도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbjibun_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/지번_충청북도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
```

### transfer

```sql
insert into geocode.tbjibun
select * from geocode.tbjibun_load;
```


## 부가정보

부가정보_시도명.txt
> $ ls -1 $PWD/부가정보_*.txt

```bash
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_강원도.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_경기도.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_경상남도.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_경상북도.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_광주광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_대구광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_대전광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_부산광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_서울특별시.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_세종특별자치시.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_울산광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_인천광역시.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_전라남도.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_전라북도.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_제주특별자치도.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_충청남도.txt
~/ssd2/juso-data/202007_주소DB_전체분/부가정보_충청북도.txt
```

```sql
create table geocode.tbaddition (
    mgt_sn varchar(25)      -- 관리번호  PK, FK
,   h4_cd varchar(10)       -- 행정동코드  * 참고용
,   h4_nm varchar(20)       -- 행정동명  * 참고용
,   zip varchar(5)          -- 우편번호 
,   zip_seq varchar(3)      -- 우편번호일련번호  NULL
,   lg_dlvr_nm varchar(40)  -- 다량배달처명  NULL
,   bld_reg_nm varchar(40)  -- 건축물대장건물명 
,   h23_bld_nm varchar(40)  -- 시군구건물명 
,   apt_yn varchar(1)       -- 공동주택여부  0:비공동주택, 1:공동주택
,   constraint pk_addition primary key(mgt_sn)
);

comment on table geocode.tbaddition is '부가 정보';
comment on column geocode.tbaddition.mgt_sn is '관리번호  PK, FK';
comment on column geocode.tbaddition.h4_cd is '행정동 코드  * 참고용';
comment on column geocode.tbaddition.h4_nm is '행정동명  * 참고용';
comment on column geocode.tbaddition.zip is '우편번호 ';
comment on column geocode.tbaddition.zip_seq is '우편번호일련번호  NULL';
comment on column geocode.tbaddition.lg_dlvr_nm is '다량배달처명  NULL';
comment on column geocode.tbaddition.bld_reg_nm is '건축물대장 건물명 ';
comment on column geocode.tbaddition.h23_bld_nm is '시군구 건물명 ';
comment on column geocode.tbaddition.apt_yn is '공동주택여부  0:비공동주택, 1:공동주택';

create table geocode.tbaddition_load (
    mgt_sn varchar(25)      -- 관리번호  PK, FK
,   h4_cd varchar(10)       -- 행정동 코드  * 참고용
,   h4_nm varchar(20)       -- 행정동명  * 참고용
,   zip varchar(5)          -- 우편번호 
,   zip_seq varchar(3)      -- 우편번호일련번호  NULL
,   lg_dlvr_nm varchar(40)  -- 다량배달처명  NULL
,   bld_reg_nm varchar(40)  -- 건축물대장 건물명 
,   h23_bld_nm varchar(40)  -- 시군구 건물명 
,   apt_yn varchar(1)       -- 공동주택여부  0:비공동주택, 1:공동주택
,   constraint pk_addition_load primary key(mgt_sn)
);
```

### load

관리자 권한으로 실행.

> %sudo -i -u postgres
> %psql -d geocode

```sql
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_강원도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_경기도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_경상남도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_경상북도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_광주광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_대구광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_대전광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_부산광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_서울특별시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_세종특별자치시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_울산광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_인천광역시.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_전라남도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_전라북도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_제주특별자치도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_충청남도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
\COPY geocode.tbaddition_load FROM '~/ssd2/juso-data/202007_주소DB_전체분/부가정보_충청북도.txt' WITH DELIMITER '|' ENCODING 'WIN949';
```


### transfer

```sql
insert into geocode.tbaddition
select * from geocode.tbaddition_load;
```

# 지적도

## table

```sql
--drop table geocode.tbzip_area;

create table geocode.tblsmd_cont_ldreg (
    pnu	varchar(19)             -- 필지고유번호
,   jibun	varchar(15)         -- 지번
,   bchk	varchar(1)          -- 발급승인코드
,   sgg_oid	numeric(22)           -- 원천오브젝트ID
,   col_adm_sect_cd	varchar(5)  -- 원천시군구코드
,   geom geometry NULL           -- 형상 
,   constraint "pk_lsmd_cont_ldreg" primary key (pnu)
);

ALTER TABLE geocode.tblsmd_cont_ldreg
ALTER COLUMN geom TYPE geometry(MULTIPOLYGON, 2097)
 ST_SetSRID(geom,2097);

comment on table geocode.tblsmd_cont_ldreg is '연속지적도';
comment on column geocode.tblsmd_cont_ldreg.pnu is '필지고유번호';
comment on column geocode.tblsmd_cont_ldreg.jibun is '지번';
comment on column geocode.tblsmd_cont_ldreg.bchk is '발급승인코드. 0:미승인, 1:승인, 2:속성승인, 3:불승인, 4:도면승인	구속성/연속, 5:기존승인	구속성/개별, 8:미승인(이동정리미반영), 9:미승인(이동정리반영)';
comment on column geocode.tblsmd_cont_ldreg.sgg_oid is '원천오브젝트id';
comment on column geocode.tblsmd_cont_ldreg.col_adm_sect_cd is '원천시군구코드';

create table geocode.tblsmd_cont_ldreg_load (
    pnu	varchar(19)             -- 필지고유번호
,   jibun	varchar(15)         -- 지번
,   bchk	varchar(1)          -- 발급승인코드
,   sgg_oid	numeric(22)           -- 원천오브젝트id
,   col_adm_se	varchar(5)  -- 원천시군구코드 (DBF는 8자 제한 있음. 주의)
,   geom geometry null           -- 형상 
,   constraint "pk_lsmd_cont_ldreg_load" primary key (pnu)
);
```


## load

download from: http://data.nsdi.go.kr/dataset/12771
save to: ~/ssd2/juso-data/연속지적/

좌표계: EPSG:2097 이라고 설명되어 있으나
QGIS의 2097은 오차가 수백미터 생긴다.
> +proj=tmerc +lat_0=38 +lon_0=127 +k=1 +x_0=200000 +y_0=500000 +ellps=bessel +units=m +no_defs

QGIS에 아래 CRS를 추가해야 함. 

[오래된 지리원 표준]
2002년 이전에 지리원의 지형도와 KLIS 등 국가 시스템에서 사용되었던 좌표계입니다.

*보정된 중부원점(Bessel): KLIS에서 중부지역에 사용중
출처: https://www.osgeo.kr/17 [OSGeo(Open Source GeoSpatial) 한국어 지부 - OSGeo Korean Chapter]

EPSG:5174
> +proj=tmerc +lat_0=38 +lon_0=127.0028902777778 +k=1 +x_0=200000 +y_0=500000 +ellps=bessel +units=m +no_defs +towgs84=-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43

QGIS(및 postgis)의 EPSG:5174와 다르다.
> +proj=tmerc +lat_0=38 +lon_0=127.0028902777778 +k=1 +x_0=200000 +y_0=500000 +ellps=bessel +units=m +no_defs

postgres에 등록하려면 좌표계를 추가해야 한다. 
postgres의 5174는 QGIS와 같다.

```sql
select proj4text from spatial_ref_sys
where srid = 5174;

-- +proj=tmerc +lat_0=38 +lon_0=127.0028902777778 +k=1 +x_0=200000 +y_0=500000 +ellps=bessel +units=m +no_defs 
```

참고: https://progworks.tistory.com/2

postgres에 {보정된 중부원점(Bessel): KLIS에서 중부지역에 사용중} 추가
```sql
INSERT INTO public.spatial_ref_sys(srid, auth_name, auth_srid, proj4text)
VALUES(95174, 'DATA0', 95174, '+proj=tmerc +lat_0=38 +lon_0=127.0028902777778 +k=1 +x_0=200000 +y_0=500000 +ellps=bessel +units=m +no_defs +towgs84=-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43');
```


extract
```
cd ~/ssd2/juso-data/연속지적/
unzip LSMD_CONT_LDREG_강원.zip -d shp/
unzip LSMD_CONT_LDREG_경기.zip -d shp/
unzip LSMD_CONT_LDREG_경남.zip -d shp/
unzip LSMD_CONT_LDREG_경북.zip -d shp/
unzip LSMD_CONT_LDREG_광주.zip -d shp/
unzip LSMD_CONT_LDREG_대구.zip -d shp/
unzip LSMD_CONT_LDREG_대전.zip -d shp/
unzip LSMD_CONT_LDREG_부산.zip -d shp/
unzip LSMD_CONT_LDREG_서울.zip -d shp/
unzip LSMD_CONT_LDREG_세종.zip -d shp/
unzip LSMD_CONT_LDREG_울산.zip -d shp/
unzip LSMD_CONT_LDREG_인천.zip -d shp/
unzip LSMD_CONT_LDREG_전남.zip -d shp/
unzip LSMD_CONT_LDREG_전북.zip -d shp/
unzip LSMD_CONT_LDREG_제주.zip -d shp/
unzip LSMD_CONT_LDREG_충남.zip -d shp/
unzip LSMD_CONT_LDREG_충북.zip -d shp/
```

> $ find -name  *.shp

```sql
truncate table geocode.tblsmd_cont_ldreg_load;
```


```bash
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_11_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_26_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_27_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_28_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_29_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_30_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_31_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_36_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_41_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_42_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_43_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_44_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_45_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_46_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_47_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_48_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
shp2pgsql -s 95174 -W EUC-KR -a ~/ssd2/juso-data/연속지적/shp/LSMD_CONT_LDREG_50_202009.shp  geocode.tblsmd_cont_ldreg_load | psql -d geocode 
```

* shp2pgsql     : command
* -s 5179       : EPSG 좌표계
* -a            : append.  -c: 테이블 생성(default), -d: drop후 테이블 생성, -p: prepare모드. 테이블 생성만.
* -I            : 공간인덱스 생성
* TL_KODIS_BAS_48.shp   : shp 파일명
* geocode.tbzip_area_load   : -a 옵션일 때 load할 타겟 테이블. 
* | psql -d geocode : 파이프 이용하여 psql에 sql출력을 전달


### transfer

```sql
insert into geocode.tblsmd_cont_ldreg
select * from geocode.tblsmd_cont_ldreg_load;
```

# 임시테이블 비우기

```sql
truncate table geocode.tbrel_jibun_info_load;
truncate table geocode.tbaddition_load;
truncate table geocode.tbrel_jibun_info_load;
truncate table geocode.tbroad_code_load;
truncate table geocode.tbnavi_match_bld_load;
truncate table geocode.tbnavi_match_jibun_load;
truncate table geocode.tbnavi_match_rs_entrc_load;
truncate table geocode.tbadrdc_load;
truncate table geocode.tbentrc_load;
truncate table geocode.tbjuso_load;
truncate table geocode.tbjibun_load;
truncate table geocode.tblsmd_cont_ldreg_load;
```

# 법정동

[행정표준코드관리시스템](https://www.code.go.kr/index.do) 에서 다운로드
 
~/ssd2/juso-data/법정동

EUC-KR을 UTF-8로 변환. vscode 이용

컬럼 구성 : 
```
법정동코드[TAB]법정동명[TAB]폐지여부
1100000000[TAB]서울특별시[TAB]존재
1111000000[TAB]서울특별시 종로구[TAB]존재
1111011200[TAB]서울특별시 종로구 체부동[TAB]존재
```

```sql
create table geocode.tbadmi_ldong_load (
     ld_cd varchar(10) -- 법정동코드
,    full_nm varchar(100) NULL -- 법정동명 Full name
,    ld_status varchar(10) NULL -- 폐지여부
);

create table geocode.tbadmi_ldong (
    ld_cd varchar(10) -- 법정동코드
,	h1_nm varchar(40) NULL
,	h23_nm varchar(40) NULL
,	ld_nm varchar(40) NULL
,	ri_nm varchar(40) NULL
,   constraint "pk_tbadmi_ldong" primary key (ld_cd)
);

comment on table geocode.tbadmi_ldong is '법정동';
comment on column geocode.tbadmi_ldong.h1_nm is '시도명';
comment on column geocode.tbadmi_ldong.h23_nm is '시군구명';
comment on column geocode.tbadmi_ldong.ld_nm is '법정동명';
comment on column geocode.tbadmi_ldong.ri_nm is '리명';
```

### load

> %psql -d geocode

```sql
\COPY geocode.tbadmi_ldong_load FROM '~/ssd2/juso-data/법정동/법정동코드 전체자료.txt' WITH DELIMITER E'\t';
```

### transfer

```sql
insert into geocode.tbadmi_ldong
select ld_cd
, split_part(full_nm, ' ', 1) 
, split_part(full_nm, ' ', 2) 
, split_part(full_nm, ' ', 3) 
, split_part(full_nm, ' ', 4) 
from geocode.tbadmi_ldong_load
where ld_status = '존재'
;
```

# 행정동 경계

공공기관은 행정동을 제공하지 않음. githup에서 찾음.

http://data.si.re.kr/node/35269

통계청 분기별(1.1./4.1./7.1./10.1.)로 공고, 관리되는 행정구역이 있었음. 지금은 없음.
국가기초구역은 행정동을 따르지 않음.
통계청 집계구도 마찬가지.

통계지리정보시스템에서는 더이상 지도 데이터를 제공하지 않습니다. (https://sgis.kostat.go.kr/contents/shortcut/shortcut_05.jsp)
지도 데이터가 필요하신 사용자께서는 링크된 설명서를 다운로드 받아 도로명 지도를 신청하시기 바랍니다.

juso.go.kr에서 받으라는 얘기
그러나 거기에도 행정동이 없다.

## 행정동 영역 만들기

~~~juso.go.kr의 네비게이션 건물정보(tbnavi_match_bld)와 실폭도로(TL_SPRD_RW.shp)를 이용하면 행정동 경계를 만들 수 있다.~~~

연 2회 업데이트 github: https://github.com/vuski/admdongkor 

* geojson 형식이며, 좌표계는 WGS84 (EPSG:4326) 입니다.
* geojson 및 csv 파일 인코딩 형식은 UTF-8입니다.
* topology 정합성을 검토하였습니다.(폴리곤 경계끼리 잘 맞습니다)
* 속성의 adm_cd 는 통계청에서 사용하는 7자리의 [한국행정구역분류코드]입니다.
* 속성의 adm_cd2 는 행정안전부 사용하는 10자리의 [행정기관코드]입니다.(2018.07.24 업데이트 파일부터 적용)
* 속성의 adm_nm 은 통계청에서 사용하는 전국 행정동 이름입니다.

최신 geojson 파일을 받아서 org2ogr로 DB 로드

cd /home/gisman/ssd2/juso-data/행정동

## tbadmi_dong_load

```
ogr2ogr -f "PostgreSQL" PG:"dbname=geocode user=gisman" "HangJeongDong_ver20201001.geojson" -nln geocode.tbadmi_dong_load -lco OVERWRITE=yes
```

## table

```sql
create table geocode.tbadmi_dong (
    h4_cd varchar(10) -- 행정동코드 (PK)
,   h1_nm varchar(40) -- 시도명
,   h23_nm varchar(40) -- 시군구명
,   h4_nm varchar(40) -- 행정동명
,   h23_cd varchar(5)  -- 시군구코드
,   geom geometry(4326) NULL -- 형상 
,   constraint "pk_tbadmi_dong" primary key (h4_cd)
);

comment on table geocode.tbadmi_dong is '행정동';
comment on column geocode.tbadmi_dong.h1_nm is '시도명';
comment on column geocode.tbadmi_dong.h23_nm is '시군구명';
comment on column geocode.tbadmi_dong.h4_nm is '행정동명';
comment on column geocode.tbadmi_dong.h23_cd is '시군구코드';
comment on column geocode.tbadmi_dong.geom is '형상 ';

CREATE INDEX idx_tbadmi_dong
  ON geocode.tbadmi_dong
  USING GIST (geom);
 ```

## transfer

```sql
insert into geocode.tbadmi_dong
select * from geocode.tbadmi_dong_load;
```

# 도로명 주소 아닌 지번

1. tmp_road_pnu: 새주소 있는 지번. 빠른 비교용 임시 테이블
1. tbaddress_no_road: 새주소 없는 지적. 영역에서 추출한 중심점
1. 법정동과 조인하여 빈 컬럼 채우고


```sql
--새주소 없는 지적 추출
-- 새주소 pnu 추출
drop table tmp_road_pnu;

create table tmp_road_pnu
as
select distinct left(b.bld_mgt_no, 19) as pnu
from geocode.tbaddress b 
;

create unique index idx_road_pnu on tmp_road_pnu(pnu)
;
```

```sql
CREATE TABLE geocode.tbaddress_no_road (
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

create index idx_address_no_road_h23 on geocode.tbaddress_no_road(h23_nm);
```

```sql
-- 도로명 주소 아닌 지번 로드
-- 33,382,118건
insert into tbaddress_no_road ( san
								, bng1
								, bng2
								, ld_cd
								, bld_x
								, bld_y)
select san
, bng1
, bng2
, ld_cd
, st_x(center) as bld_x
, st_y(center) as bld_y
from (
	select substring(a.pnu, 11, 1) as san
	, substring(a.pnu, 12, 4)::int as bng1
	, substring(a.pnu, 16, 4)::int as bng2
	, left(a.pnu, 10) as ld_cd
	, ST_Transform(
		ST_PointOnSurface(a.geom), 5179
		) center
	from geocode.tblsmd_cont_ldreg a
	left outer join geocode.tmp_road_pnu b on (a.pnu = b.pnu)
	where b.pnu is null
	and a.pnu ~ '^\d{19}$'
) x
;
```

빈 명칭 업데이트

```sql
update geocode.tbaddress_no_road as a
set h1_nm = b.h1_nm
, h23_nm = b.h23_nm
, ld_nm = b.ld_nm
, ri_nm = b.ri_nm
from geocode.tbadmi_ldong b
where a.ld_cd = b.ld_cd
;
```

행정동 업데이트

```sql
update geocode.tbaddress_no_road as a
set h4_nm = b.h4_nm
, h4_cd = b.h4_cd
from geocode.tbadmi_dong b
where ST_Contains(geom, 
	ST_Transform(
		ST_GeomFromText(concat('POINT(', a.bld_x, ' ', a.bld_y, ')'), 95174)
	, 4326)
)
--and a.ld_cd = '4180033025'
;
```

-- zip 업데이트
```sql
update geocode.tbaddress_no_road as a
set zip = b.bas_id 
from geocode.tbzip_area b
where ST_Contains(geom, 
	ST_Transform(
		ST_GeomFromText(concat('POINT(', a.bld_x, ' ', a.bld_y, ')'), 95174)
	, 5179)
)
--and a.ld_cd = '4180033025'
;
```

<!-- 좌표계 수정. 2021.2.19 이전 데이터 오류 수정 -->
<!-- update geocode.tbaddress_no_road a
set 
bld_x = st_x(
		ST_Transform(
			ST_GeomFromText(concat('POINT(', a.bld_x, ' ', a.bld_y, ')'), 95174)
		, 5179)
	),
bld_y = st_y(
		ST_Transform(
			ST_GeomFromText(concat('POINT(', a.bld_x, ' ', a.bld_y, ')'), 95174)
		, 5179)
	)
; -->

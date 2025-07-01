## 길 COMMA 건번

적용 완료.

COMMA 뒤의 주소이더라도 COMMA 앞이 ROAD면 건번으로 봐야 함
> 서울 서초구 서초대로50길, 18, 5층(서초동, 유성빌딩)
> 서울특별시 서초구 반포대로30길, 81(서초동, 웅진타워) 
> 서울 서초구 서초중앙로26길, 3, 302호(서초동, 청림빌딩) 

물음표는 구분자인거 같다. COMMA로 취급해도 될 거 같다. 단 COMMA가 이전에 나왔어야 하거나, 숫자 뒤어야 함
> 서울 종로구 창덕궁 1길, 4?5층(원서빌딩)
> 경기 의정부시 녹양로 34번길, 3?4층(가능동, 진성빌딩)

# 리팩토링

-[X] 기능 개선 사전 작업.
-[X] 기능별, 주소유형별 파일을 분리.

## CreateLevelDb.py 리팩토링

* name: DbCreator.py
* 경로: src/util
* class: 불필요

* def toAddress => _make_address_string(daddr, keys):
* def put => _del_and_put(batch, geocoder, address, val_json):
* def addressKeyVal2 => table_to_hash (connection, ldb, sql):

## Geocoder.py 리팩토링

* tokenizer 분리
* getAddressCls, getAddressClsText, __classText 제거
* hash... 분리 
    * hash/JibunAddress
    * hash/BldAddress
    * hash/RoadAddress

## toks 클래스 제작

* done

## 행정동, 법정동에서 리 제거하면 안 되나?

hash에 리 제거하면 되는데, 법정동은 원래 리 이다.
leveldb에 리 제외한 hash만 있다면 충돌 가능성 있다.
결론: 제거 안 함

## 지적 추가

새주소 없는 지적 데이터에 행정구역코드 등 여러 필수 컬럼 값을 붙여서 geocode.tbaddress에 추가.

건물관리번호는 법정동코드(10) + 산여부(1) + 지번본번(4) + 지번부번(4) + 시스템번호(6) 총 25자리로 되어 있습니다.
tbaddress.bld_mgt_no 와 tblsmd_cont_ldreg.pnu 를 JOIN 할 수 있다.

산여부 코드(1,2)가 새주소건물(0, 1)과 다르다. 

### 지적:

geocode.tblsmd_cont_ldreg
```
	pnu varchar(19) NOT NULL,
	jibun varchar(15) NULL,
	bchk varchar(1) NULL,
	sgg_oid numeric(22) NULL,
	col_adm_sect_cd varchar(5) NULL,
	geom geometry NULL,
```

### 필수 컬럼

from geocode.tbaddress a
```
a.h1_nm,	a.h23_nm,	a.ld_nm,	a.h4_nm,	a.ri_nm,	a.road_nm
,	a.undgrnd_yn,	cast(a.bld1 as text),	cast(a.bld2 as text)
,	a.san,	cast(a.bng1 as text),	cast(a.bng2 as text)
,	a.bld_reg,	a.bld_nm_text, a.bld_nm
,	a.ld_cd,	a.h4_cd,	a.road_cd,	a.zip,	a.bld_mgt_no
,	a.bld_x,	a.bld_y
```        


### 정보 추가
#### pnu로 부터 코드 분리

a.san,	cast(a.bng1 as text),	cast(a.bng2 as text)
,	a.ld_cd,

#### 법정동 파일로부터:

테이블 만들어야 함 (~/ssd2/juso-data/법정동)

a.h1_nm,	a.h23_nm,	a.ld_nm,,	a.ri_nm

#### 새주소 없는 지적만 추가하므로 다음 무시    

    a.road_nm
,	a.undgrnd_yn,	cast(a.bld1 as text),	cast(a.bld2 as text)
,	a.bld_reg,	a.bld_nm_text, a.bld_nm
,	a.road_cd,	a.bld_mgt_no

#### 행정동경계 레이어 공간연산으로:

성공

#### 기초구역경계 레이어 공간연산으로:

a.zip

#### geom 중심 좌표에서:

a.bld_x,	a.bld_y


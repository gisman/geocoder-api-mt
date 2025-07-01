# geohash 유틸리티

행정동 History 기능을 위한 geohash db 생성 및 병합 유틸리티.

## build_geohash.py

shp 파일을 읽어 geohash db를 생성함. 이미 db가 존재할 경우 해당 db를 업데이트함.

shp 파일의 모든 도형을 읽어 geohash db를 생성. 도형의 depth는 7로 설정됨.

도형에 해당하는 geohash를 모두 찾고, 행정동코드, 행정동명, Polygon 정보를 저장함.
Polygon은 행정동 경계 전체가 아닌 geohash 영역과 겹치는 부분만 저장. 크기가 줄어들고, hit test도 빨라짐.

### 사전 준비

1. juso.go.kr에서 구역의 도형 shp 파일 다운로드. 저장 위치: /disk/hdd-lv/juso-data/행정동/[YYYYMM]
2. shp 파일 압축 해제. 광역시 코드 디렉토리에 풀림 (예: 구역의도형_전체분_서울특별시.zip -> /disk/hdd-lv/juso-data/행정동/[YYYYMM]/11000)

### 사용법

venv 활성화 후 아래 명령어로 geohash db 생성 (디렉토리 경로는 적절히 수정 필요):

``` python
python cli/build_geohash.py \
--shp=/disk/hdd-lv/juso-data/행정동/[202305]/[11000]/TL_SCCO_GEMD.shp \
--output_dir=/disk/hdd-lv/juso-data/행정동/[202305]/[11000]/TL_SCCO_GEMD \
--depth=7 
```

* output: rocksdb 디렉토리

### 생성되는 정보

생성된 geohash db는 rocksdb 형식이며 다음 정보를 저장:
``` json
[
    {
        "EMD_CD": "행정동코드",
        "EMD_KOR_NM": "행정동명",
        "EMD_ENG_NM": "행정동영문명",
        "from_yyyymm": "시작 연월 (YYYYMM)", 
        "to_yyyymm": "종료 연월 (YYYYMM)",
        "intersection_wkt": "geohash 영역과 행정동 경계가 겹치는 부분의 WKT"
    },
    ...
]
```

행정동 경계 부분에서 geohash가 겹치면 배열에 추가됨.

최초 생성이 아닌 경우 기존 geohash와 비교하여 데이터를 병합함. 행정동 경계 판단을 위해 기존 데이터와 hd_cd의 intersection_wkt가 같은지 비교함.


## merge_geohash.py

build_geohash.py로 생성된 geohash db를 병합하는 유틸리티.
행정동 history 서비스는 하나로 병합한 db를 사용함.

범용적 사용 불가. 행정동 History 기능 전용.

문제 단순화를 위해 yyyymm 순서대로 merge 진행 (과거부터 차례대로)
순서가 중요함. 순서가 뒤섞이면 올바르게 merge 되지 않음.

이미 최신 데이터가 존재할 때 과거 데이터를 merge하려면 전체를 새로 생성해야 함.

### 사용법

venv 활성화 후 아래 명령어로 geohash db 병합 (디렉토리 경로는 적절히 수정 필요):

``` bash
python cli/merge_geohash.py \
  --base=[/PATH/TO/OUTPUT/MERGED_DB] \
  --input=/disk/ssd2t/juso-data/행정동/202305/11000/TL_SCCO_GEMD    /disk/ssd2t/juso-data/행정동/202306/11000/TL_SCCO_GEMD      /disk/ssd2t/juso-data/행정동/202307/11000/TL_SCCO_GEMD 
```

### 생성되는 정보

병합된 geohash db는 rocksdb 형식으로 다음 정보를 저장. 
아래 예시는 행정동코드가 `5111061000`인 후평2동의 행정동 코드가 2023년 6월부터 변경된 것을 보여줌 (강원도가 강원특별자치도로 변경되어 행정동코드가 바뀜):

``` json
[
  {
    "EMD_CD": "5111061000", # "행정동코드",
    "EMD_KOR_NM": "후평2동", # "행정동명",
    "EMD_ENG_NM": "Hupyeong2(i)-dong", # "행정동영문명",
    "from_yyyymm": "202306", # "시작 연월 (YYYYMM)",
    "to_yyyymm": "202504", # "종료 연월 (YYYYMM)",
    "intersection_wkt": "geohash 영역과 행정동 경계가 겹치는 부분의 WKT"
  },
  {
    "EMD_CD": "4211061000",
    "EMD_KOR_NM": "후평2동",
    "EMD_ENG_NM": "Hupyeong2(i)-dong",
    "from_yyyymm": "202305",
    "to_yyyymm": "202305",
    "intersection_wkt": "geohash 영역과 행정동 경계가 겹치는 부분의 WKT"
  }
]
```

시작 연월과 종료 연월은 파일 경로에서 자동 유추함.
예: TL_SCCO_GEMD 경로에서 `202305`가 시작 연월과 종료 연월이 됨.

이전에 같은 행정동코드가 존재하면 기존 데이터와 병합함.
행정동코드와 intersection_wkt가 같으면 기존 데이터의 `to_yyyymm`을 현재 데이터의 `from_yyyymm`으로 업데이트함.
같지 않으면 새로운 행정동코드로 추가함.
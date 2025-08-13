# -*- coding: utf-8 -*-
"""
Geocode API HTTP Server
Usage::
    ./api_fast.py [<port>]
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import time
import logging
import os
import json
import tempfile
import os
import shutil
import uvicorn
import sys
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta

from pyproj import Transformer, CRS
from fastapi import APIRouter
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi import Depends, Request
from fastapi import File, UploadFile, Form

from cli.build_geohash import process_region_to_rocksdb, process_shapefile_to_rocksdb
from cli.merge_geohash import merge_geohash_dbs
import src.config as config
from src.geocoder.geocoder import Geocoder, POS_CD_SUCCESS
from src.geocoder.hash.BldAddress import BldAddress
from src.geocoder.reverse_geocoder import ReverseGeocoder
from src.geocoder.file.file_geocoder import FileGeocoder
from src.pro.updater.daily_updater import DailyUpdater
from src.pro.updater.entrc_updater import EntrcUpdater
from src.pro.updater.h1_addr_updater import H1AddrUpdater
from src.pro.updater.h23_addr_updater import H23AddrUpdater
from src.pro.updater.hd_addr_updater import HdAddrUpdater
from src.pro.updater.ld_addr_updater import LdAddrUpdater
from src.pro.updater.ri_addr_updater import RiAddrUpdater
from src.pro.updater.road_addr_updater import RoadAddrUpdater
from src.pro.updater.navi_updater import NaviUpdater
from src.pro.updater.roadbase_updater import RoadbaseUpdater
from src.pro.updater.spot_updater import SpotUpdater
from src.pro.updater.pnu_updater import PnuUpdater
from src.pro.updater.hd_updater import HdUpdater
from src.pro.updater.z_updater import ZUpdater

from src.database import Database
from src.auth import get_token_stats, update_token_stats, write_usage_log


class GeocodeBaseModel(BaseModel):
    # token: str = "DEMO_TOKEN"  # 기본 토큰 값, 실제 사용 시에는 변경 필요
    pass


class GeocodeFileItem(GeocodeBaseModel):
    filepath: str
    quarter: int = 10000
    uploaded_filename: str = None
    download_dir: str
    target_crs: str = "EPSG:4326"
    sample_count: int = 1000  # 샘플 개수, 기본값은 1000
    address_hint: Optional[str] = None  # 주소 힌트, 선택적 필드


class GeocodeFileXYItem(GeocodeFileItem):
    x_col: str = "경도"
    y_col: str = "위도"
    delimiter: str = ","
    encoding: str = "utf-8"
    source_crs: str = "EPSG:4326"


class Batch_Geocode_Item(GeocodeBaseModel):
    q: list[str] = [
        "서울특별시 송파구 송파대로8길 10",
        "김제 온천길 37",
        "강원 춘천시 남산면 서천리 산111",
    ]


class GeocodeResult(GeocodeBaseModel):
    x: Optional[int] = Field(None, description="원본 X 좌표 (EPSG:5179)")
    y: Optional[int] = Field(None, description="원본 Y 좌표 (EPSG:5179)")
    z: Optional[str] = Field(None, description="우편번호")
    hc: Optional[str] = Field(None, description="행정동 코드")
    lc: Optional[str] = Field(None, description="법정동 코드")
    rc: Optional[str] = Field(None, description="도로명 코드")
    bn: Optional[str] = Field(None, description="건물 번호")
    h1: Optional[str] = Field(None, description="행정구역 1 (시도명)")
    rm: Optional[str] = Field(None, description="도로명")
    bm: Optional[List[str]] = Field(None, description="건물명 목록")
    hd_cd: Optional[str] = Field(None, description="행정동 코드")
    hd_nm: Optional[str] = Field(None, description="행정동 이름")
    success: bool = Field(False, description="지오코딩 성공 여부")
    errmsg: str = Field("", description="오류 메시지")
    h1_cd: Optional[str] = Field(None, description="광역시도 코드")
    h2_cd: Optional[str] = Field(None, description="시군구 코드")
    kostat_h1_cd: Optional[str] = Field(None, description="통계청 광역시도 코드")
    kostat_h2_cd: Optional[str] = Field(None, description="통계청 시군구 코드")
    hash: Optional[str] = Field(None, description="해시 값")
    address: Optional[str] = Field(None, description="전체 주소")
    addressCls: Optional[str] = Field(None, description="주소 유형")
    toksString: Optional[str] = Field(None, description="토큰화된 주소")
    x_axis: Optional[float] = Field(None, description="경도 (EPSG:4326)")
    y_axis: Optional[float] = Field(None, description="위도 (EPSG:4326)")
    inputaddr: str = Field("", description="입력 주소")


class GeocodeSummary(GeocodeBaseModel):
    total_time: float = Field(0.0, description="총 처리 시간 (초)")
    total_count: int = Field(0, description="총 요청 주소 개수")
    success_count: int = Field(0, description="성공한 주소 개수")
    hd_success_count: int = Field(0, description="성공한 행정동 개수")
    fail_count: int = Field(0, description="실패한 주소 개수")
    results: List[GeocodeResult] = Field(
        default_factory=list, description="지오코딩 결과 목록"
    )
    # key: Optional[str] = None


class HdHistoryResult(GeocodeBaseModel):
    EMD_CD: Optional[str] = Field(None, description="행정동 코드")
    EMD_KOR_NM: Optional[str] = Field(None, description="행정동 한글 이름")
    EMD_ENG_NM: Optional[str] = Field(None, description="행정동 영어 이름")
    from_yyyymm: Optional[str] = Field(None, description="시작 년월 (YYYYMM)")
    to_yyyymm: Optional[str] = Field(None, description="종료 년월 (YYYYMM)")


class RegionResultSlim(GeocodeBaseModel):
    wkt: Optional[str] = Field(None, description="영역 WKT")
    yyyymm: Optional[str] = Field(None, description="데이터 년월 (YYYYMM)")
    name: Optional[str] = Field(None, description="region 이름")
    code: Optional[str] = Field(None, description="region 코드")
    success: bool = Field(False, description="행정동 검색 성공 여부")


class RegionResult(RegionResultSlim):
    EMD_CD: Optional[str] = Field(None, description="행정동 코드")
    EMD_KOR_NM: Optional[str] = Field(None, description="행정동 한글 이름")
    EMD_ENG_NM: Optional[str] = Field(None, description="행정동 영어 이름")
    # wkt: Optional[str] = Field(None, description="영역 WKT")
    # yyyymm: Optional[str] = Field(None, description="데이터 년월 (YYYYMM)")
    # name: Optional[str] = Field(None, description="region 이름")
    # code: Optional[str] = Field(None, description="region 코드")
    # success: bool = Field(False, description="행정동 검색 성공 여부")


class RoadAddrResult(GeocodeBaseModel):
    ADR_MNG_NO: Optional[str] = Field(None, description="주소 관리 번호")
    yyyymm: Optional[str] = Field(None, description="데이터 년월 (YYYYMM)")
    address: Optional[str] = Field(None, description="도로명 주소")
    success: bool = Field(False, description="도로명 주소 검색 성공 여부")
    geom: Optional[str] = Field(None, description="WKT 지오메트리")
    errmsg: str = Field("", description="오류 메시지")


class JibunAddrResult(GeocodeBaseModel):
    PNU: Optional[str] = Field(None, description="지번 주소 PNU 코드")
    yyyymm: Optional[str] = Field(None, description="데이터 년월 (YYYYMM)")
    address: Optional[str] = Field(None, description="지번 주소")
    success: bool = Field(False, description="지번 주소 검색 성공 여부")
    geom: Optional[str] = Field(None, description="WKT 지오메트리")
    errmsg: str = Field("", description="오류 메시지")


class ReverseGeocodeResult(GeocodeBaseModel):
    road_addr: Optional[RoadAddrResult] = Field(None, description="도로명 주소 결과")
    jibun_addr: Optional[JibunAddrResult] = Field(None, description="지번 주소 결과")
    success: bool = Field(False, description="리버스 지오코딩 성공 여부")


# class ReverseGeocodeResult(GeocodeBaseModel):
# # {'road_addr': {'ADR_MNG_NO': '41290110438508500002200000', 'yyyymm': 'MST.41000', 'address': '경기도 과천시 부림2길 22', 'success': True, 'geom': 'POLYGON ((126.997129 37.437782,
# #         126.997299 37.437726,
# #         126.997254 37.437637,
# #         126.997195 37.437657,
# #         126.997203 37.437670,
# #         126.997148 37.437689,
# #         126.997141 37.437675,
# #         126.997083 37.437694,
# #         126.997129 37.437782))', 'errmsg': ''
# #     }, 'jibun_addr': {'PNU': '4129011000100290005', 'yyyymm': '202404', 'address': '경기도 과천시 부림동 29-5번지', 'success': True, 'geom': 'POLYGON ((126.997280 37.437614,
# #         126.997074 37.437683,
# #         126.997116 37.437795,
# #         126.997323 37.437726,
# #         126.997280 37.437614))', 'errmsg': ''
# #     }, 'success': True
# # }

#     ADR_MNG_NO: Optional[str] = Field(None, description="주소 관리 번호")
#     yyyymm: Optional[str] = Field(None, description="데이터 년월 (YYYYMM)")
#     address: Optional[str] = Field(None, description="전체 주소")
#     success: bool = Field(False, description="리버스 지오코딩 성공 여부")
#     geom: Optional[str] = Field(None, description="WKT 지오메트리")
#     errmsg: str = Field("", description="오류 메시지")


class TokenStats(GeocodeBaseModel):
    total_requests: int = Field(0, description="총 요청 수")
    last_month_requests: int = Field(0, description="지난 달 요청 수")
    monthly_quota: int = Field(0, description="월간 할당량")
    remaining_quota: int = Field(0, description="남은 할당량")
    daily_quota: int = Field(0, description="일일 할당량")
    daily_requests: int = Field(0, description="오늘 요청 수")
    remaining_daily_quota: int = Field(0, description="남은 일일 할당량")
    last_request_date: Optional[datetime] = Field(None, description="마지막 요청 날짜")


APP_NAME = "Geocode API Server"
VERSION = 0.1
DEFAULT_PORT = 4001

LINES_LIMIT = 3000

X_AXIS = "x_axis"
Y_AXIS = "y_axis"

JUSO_DATA_DIR = config.JUSO_DATA_DIR

# 애플리케이션 시작 및 종료 이벤트 처리기
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 및 종료 이벤트 처리"""
    yield
    # await Database.create_pool()
    # logging.info("PostgreSQL database connected")
    # try:
    #     yield
    # finally:
    #     await Database.close_pool()
    #     logging.info("PostgreSQL database disconnected")


# app = FastAPI()
app = FastAPI(lifespan=lifespan)
router = APIRouter()

# 필요한 import 추가
from fastapi.staticfiles import StaticFiles

# 정적 파일 디렉토리 경로 설정
static_dir = "static"
# os.makedirs(static_dir, exist_ok=True)

# # index.html 파일이 static 디렉토리에 있는지 확인
index_path = os.path.join(static_dir, "index.html")

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def read_root():
    """
    정적 HTML 파일을 반환합니다.
    """
    return FileResponse(index_path)


@router.get("/geocode", response_model=GeocodeSummary)
async def geocode(
    request: Request,
    q: str = """서울특별시 송파구 송파대로8길 10
김제 온천길 37
강원 춘천시 남산면 서천리 산111""",
    token: str = "",
    token_stats: dict = Depends(get_token_stats),
):
    """
    ## 주소 목록을 지오코딩합니다. 주소를 줄 바꿈(\\n)으로 구분합니다.
    GET 방식은 주소 개수에 제한이 있습니다.

    ### Args:
    * q (str): 하나 이상의 주소를 포함하는 문자열이며, 각 주소는 줄바꿈으로 구분됩니다.
    * token (str): API 토큰 값.

    ### Returns:
    * GeocodeSummary: 지오코딩 결과를 포함하는 요약 정보입니다.

    ## Geocodes a list of addresses. Each address should be separated by a newline character (\\n).
    The GET method has adress count limit.

    ### Args:
    * q (str): A string containing one or more addresses, separated by newlines.
    * token (str): API Token value.

    ### Returns:
    * GeocodeSummary: Geocoding results summary.
    """
    addrs = q.split("\n")
    summary = await ApiHandler().geocode(addrs)

    if token_stats:
        asyncio.create_task(
            update_token_stats(token_stats["token_id"], summary["success_count"])
        )

        await write_usage_log(
            token_id=token_stats["token_id"],
            endpoint=request.url.path,
            success_count=summary["success_count"],
            hd_success_count=summary["hd_success_count"],
            error_count=summary["fail_count"],
            ip_address=(
                request.client.host if request.client else None
            ),  # IP 주소는 필요에 따라 설정
            processing_time=summary["total_time"],  # 처리 시간은 필요에 따라 설정
            billable=True,  # 과금 대상 여부는 필요에 따라 설정
            quota_consumed=summary["success_count"],
        )

        # print(f"Token stats: {token_stats}")

    return summary


@router.get("/bld_hash")
async def get_bld_hash(
    request: Request,
    q: str = """경희궁 파크팰리스
    가락마을18단지 1804동
    (주)행복에스앤피제지""",
):
    """
    ## 주어진 건물명 목록에 대한 해시 값을 반환합니다.

    ### Args:
    * bld_names (list[str]): 건물명 목록입니다. 기본값은 ["경희궁 파크팰리스", "가락마을18단지 1804동", "(주)행복에스앤피제지"]입니다.

    ### Returns:
    * 건물 해시 값 목록입니다.

    ## Returns the hash values for the given list of building names.

    """
    bld_address = BldAddress()
    result = []
    for bld in q.split("\n"):
        bld = bld.strip()
        hash = bld_address.bld_hash(bld, [])
        result.append(hash)

    return result


# @router.post("/batch_geocode")
@router.post("/geocode")
async def batch_geocode(
    request: Request,
    data: Batch_Geocode_Item,
    token: str = "",
    token_stats: dict = Depends(get_token_stats),
):
    """
    ## 여러 주소를 지오코딩합니다. 많은 주소를 지오코딩할 때 유용합니다.
    주소 개수는 token 유형에 따라 제한됩니다. POST 방식으로 요청합니다.

    ### Args:
    * data (Batch_Geocode_Item): 지오코딩할 주소 목록을 포함하는 객체입니다.
    * token (str): API 토큰 값.

    ### Returns:
    * 지오코딩 결과 요약입니다.

    ### Raises:
    * HTTPException: 입력이 유효하지 않은 경우 (예: 빈 주소 목록).

    ## Geocodes multiple addresses.

    ### Args:
    * data (Batch_Geocode_Item): An object containing a list of addresses to geocode.
    * token (str): API Token value.

    ### Returns:
    * A summary of the geocoding results.

    ### Raises:
    * HTTPException: If the input is invalid (e.g., empty address list).

    """

    # # profiler *************************
    # import cProfile
    # import pstats
    # from pstats import SortKey

    # # cProfile을 사용하여 성능 측정
    # profiler = cProfile.Profile()
    # profiler.enable()
    # # profiler *************************

    addrs = data.q
    if not addrs:
        raise HTTPException(status_code=400, detail="Invalid input")

    if "quarter" in token_stats:
        addrs = addrs[: token_stats["quarter"]]

    summary = await ApiHandler().geocode(addrs)

    # # profiler *************************
    # profiler.disable()

    # # 결과 분석
    # stats = pstats.Stats(profiler).sort_stats(SortKey.CUMULATIVE)
    # stats.print_stats(20)  # 상위 20개 항목 출력

    # # 결과 파일로 저장 (나중에 snakeviz로 시각화 가능)
    # stats.dump_stats("batch_geocode.prof")
    # # profiler *************************

    if token_stats:
        asyncio.create_task(
            update_token_stats(token_stats["token_id"], summary["success_count"])
        )
        await write_usage_log(
            token_id=token_stats["token_id"],
            endpoint=request.url.path,
            success_count=summary["success_count"],
            hd_success_count=summary["hd_success_count"],
            error_count=summary["fail_count"],
            ip_address=(
                request.client.host if request.client else None
            ),  # IP 주소는 필요에 따라 설정
            processing_time=summary["total_time"],  # 처리 시간은 필요에 따라 설정
            billable=True,  # 과금 대상 여부는 필요에 따라 설정
            quota_consumed=summary["success_count"],
        )
        # print(f"Token stats: {token_stats}")

    return summary


# @router.post("/upload", include_in_schema=False)
# async def upload(
#     request: Request,
#     file: UploadFile = File(...),
#     # uploaded_filename: str = Form(...),
#     target_crs: str = Form("EPSG:4326"),
#     token: str = "",
#     token_stats: dict = Depends(get_token_stats),
# ):
#     """
#     ## 주소가 포함된 파일을 업로드하고 지오코딩합니다.

#     ### Args:

#     * file: 업로드할 파일 (주소를 포함한 CSV, 엑셀 파일).
#     * target_crs: 좌표계 (기본값: EPSG:4326)
#     * token (str): API 토큰 값.

#     ### Returns:

#     * 지오코딩 결과 요약

#     ## Uploads and geocodes a file containing addresses.

#     ### Args:

#     * file: The file to upload (CSV, Excel file containing addresses).
#     * target_crs: Coordinate system (default: EPSG:4326).
#     * token (str): API Token value.

#     ### Returns:

#     * A summary of the geocoding results.

#     """
#     if not file:
#         raise HTTPException(status_code=400, detail="Invalid input")

#     uploaded_filename = file.filename

#     # 임시 파일 생성
#     temp_dir = tempfile.gettempdir()
#     filepath = os.path.join(temp_dir, uploaded_filename)
#     download_dir = os.path.join(temp_dir, "geocoded")

#     # 다운로드 디렉터리가 존재하지 않으면 생성
#     os.makedirs(download_dir, exist_ok=True)

#     try:
#         # 업로드된 파일을 임시 파일에 저장
#         with open(filepath, "wb") as f:
#             shutil.copyfileobj(file.file, f)

#         LIMIT_COUNT = 100000
#         # [TODO] 사용자 정보에서 quarter 읽기
#         quarter = LIMIT_COUNT

#         # 지오코딩 수행
#         file_geocoder = FileGeocoder(
#             geocoder=ApiHandler.geocoder, reverse_geocoder=ApiHandler.reverse_geocoder
#         )
#         await file_geocoder.prepare(filepath, uploaded_filename)

#         if file_geocoder.address_col == -1:
#             summary = {"error": "주소 컬럼을 찾을 수 없습니다."}
#             raise HTTPException(status_code=400, detail="주소 컬럼을 찾을 수 없습니다.")
#         else:
#             summary = await file_geocoder.run(
#                 download_dir,
#                 quarter,
#                 target_crs=target_crs,
#                 sample_count=data.sample_count,
#             )

#         # 결과 파일 경로 추가
#         output_filename = os.path.splitext(uploaded_filename)[0] + "_geocoded.csv"
#         output_filepath = os.path.join(download_dir, output_filename)

#         if os.path.exists(output_filepath):
#             summary["output_file"] = output_filepath

#         if token_stats:
#             asyncio.create_task(
#                 update_token_stats(token_stats["token_id"], summary["success_count"])
#             )
#             await write_usage_log(
#                 token_id=token_stats["token_id"],
#                 endpoint=request.url.path,
#                 success_count=summary["success_count"],
#                 hd_success_count=summary["hd_success_count"],
#                 error_count=summary["fail_count"],
#                 ip_address=(
#                     request.client.host if request.client else None
#                 ),  # IP 주소는 필요에 따라 설정
#                 processing_time=summary["total_time"],  # 처리 시간은 필요에 따라 설정
#                 billable=True,  # 과금 대상 여부는 필요에 따라 설정
#                 quota_consumed=summary["success_count"],
#             )
#             # print(f"Token stats: {token_stats}")

#         return summary

#     except Exception as e:
#         logging.error(f"File geocoding error: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"File geocoding error: {str(e)}")
#     finally:
#         # 임시 파일 정리
#         file.file.close()
#         if os.path.exists(filepath):
#             os.unlink(filepath)


@router.post("/geocode_file_xy", include_in_schema=False)
async def geocode_file_xy(
    request: Request,
    data: GeocodeFileXYItem,
    token: str = "",
    token_stats: dict = Depends(get_token_stats),
):
    """
    ## 서버에 위치한 파일을 지오코딩합니다. 파일은 경도(x)와 위도(y) 좌표를 포함하고 있습니다.
    좌표를 찾을 필요 없으며, 이미 있는 좌표를 사용하여 지역 코드 추가를 합니다.

    ### Args:
    * x_col: 경도(x) 좌표가 포함된 열의 이름입니다. 기본값은 "경도"입니다.
    * y_col: 위도(y) 좌표가 포함된 열의 이름입니다. 기본값은 "위도"입니다.
    * delimiter: 파일의 구분자입니다. 기본값은 쉼표(,)입니다.
    * encoding: 파일 인코딩 형식입니다. 기본값은 "utf-8"입니다.
    * source_crs: 입력 좌표계입니다. 기본값은 "EPSG:4326"입니다.

    * filepath: 주소가 포함된 파일의 경로입니다.
    * uploaded_filename(optional): 업로드한 원시 파일의 이름
    * download_dir: 지오코딩된 파일을 저장할 디렉토리입니다.
    * token (str): API 토큰 값.

    ### Returns:
    * Geocoding summary information.

    """
    # 입력 데이터 유효성 검사 및 준비
    validate_and_prepare_file_data(data)

    # DEMO USER의 경우 할당량을 제한합니다.
    quarter = calculate_quarter_limit(data, token_stats)

    file_xy_geocoder = FileGeocoder(
        geocoder=ApiHandler.geocoder, reverse_geocoder=ApiHandler.reverse_geocoder
    )
    await file_xy_geocoder.prepare_xy(
        data.filepath,
        data.uploaded_filename,
        data.x_col,
        data.y_col,
        data.delimiter,
        data.encoding,
        data.source_crs,
    )

    summary = await file_xy_geocoder.run_xy(
        data.download_dir,
        quarter,
        source_crs=data.source_crs,
        target_crs=data.target_crs,
        sample_count=data.sample_count,
    )

    if token_stats and summary.get("success_count", 0):
        await process_token_stats_and_log(token_stats, summary, request)

    return summary


@router.post("/geocode_file", include_in_schema=False)
async def geocode_file(
    request: Request,
    data: GeocodeFileItem,
    token: str = "",
    token_stats: dict = Depends(get_token_stats),
):
    """
    ## 서버에 위치한 파일을 지오코딩합니다.

    ### Args:
    * filepath: 주소가 포함된 파일의 경로입니다.
    * uploaded_filename(optional): 업로드한 원시 파일의 이름
    * download_dir: 지오코딩된 파일을 저장할 디렉토리입니다.
    * token (str): API 토큰 값.

    ### Returns:
    * 지오코딩 요약 정보입니다.

    ## Geocodes a file located on the server.

    ### Args:
    * filepath: The path to the file containing addresses.
    * uploaded_filename(optional): The name of the originally uploaded file
    * download_dir: The directory to save the geocoded file.
    * token (str): API Token value.

    ### Returns:
    * Geocoding summary information.
    """
    # 입력 데이터 유효성 검사 및 준비
    validate_and_prepare_file_data(data)

    # DEMO USER의 경우 할당량을 제한합니다.
    quarter = calculate_quarter_limit(data, token_stats)

    file_geocoder = FileGeocoder(
        geocoder=ApiHandler.geocoder,
        reverse_geocoder=ApiHandler.reverse_geocoder,
        address_hint=data.address_hint,
    )
    await file_geocoder.prepare(data.filepath, data.uploaded_filename)
    if file_geocoder.address_col == -1:
        summary = {"error": "주소 컬럼을 찾을 수 없습니다."}
        raise HTTPException(status_code=400, detail="주소 컬럼을 찾을 수 없습니다.")
    else:
        # summary = await file_geocoder.run_mt( # 멀티 스레드로 실행: 30% 빠르지만 결과가 약간 다르게 나온다.
        summary = await file_geocoder.run(
            data.download_dir,
            quarter,
            target_crs=data.target_crs,
            sample_count=data.sample_count,
        )

    if token_stats and summary.get("success_count", 0):
        await process_token_stats_and_log(token_stats, summary, request)

    return summary


async def process_token_stats_and_log(token_stats, summary, request):
    await update_token_stats(token_stats["token_id"], summary.get("success_count", 0))
    # asyncio.create_task(
    #     update_token_stats(token_stats["token_id"], summary.get("success_count", 0))
    # )

    await write_usage_log(
        token_id=token_stats["token_id"],
        endpoint=request.url.path,
        success_count=summary["success_count"],
        hd_success_count=summary["hd_success_count"],
        error_count=summary["fail_count"],
        ip_address=(
            request.client.host if request.client else None
        ),  # IP 주소는 필요에 따라 설정
        processing_time=summary["total_time"],  # 처리 시간은 필요에 따라 설정
        billable=True,  # 과금 대상 여부는 필요에 따라 설정
        quota_consumed=summary["success_count"],
    )
    # print(f"Token stats: {token_stats}")


def calculate_quarter_limit(data, token_stats):
    # DEMO USER의 경우 할당량을 제한합니다.
    quarter = min(token_stats.get("remaining_daily_quota"), data.quarter)
    return quarter


def validate_and_prepare_file_data(data):
    if not data.filepath or not data.download_dir:
        raise HTTPException(status_code=400, detail="Invalid input")

    if not data.uploaded_filename:
        data.uploaded_filename = os.path.basename(data.filepath)


@router.get("/reverse_geocode", response_model=ReverseGeocodeResult)
async def reverse_geocode(
    request: Request,
    x: float = 126.95926349879471,
    y: float = 37.544260113101856,
    token: str = "",
    token_stats: dict = Depends(get_token_stats),
):
    """
    ## 주어진 좌표에 대한 리버스 지오코딩을 수행합니다.

    ### Args:
    * x (float): x 좌표 (경도).
    * y (float): y 좌표 (위도).
    * token (str): API 토큰 값.

    ### Returns:
    * 리버스 지오코딩 결과.


    ## Asynchronously performs reverse geocoding for a given coordinate.

    ### Args:
    * x (float): The x-coordinate (longitude).
    * y (float): The y-coordinate (latitude).
    * token (str): API Token value.

    ### Returns:
    The reverse geocoding result.

    """
    val = await ApiHandler().reverse_geocode(x, y)
    return val


@router.get("/token/stats", response_model=TokenStats)
async def get_user_token_stats(
    request: Request, token: str = "", token_stats: dict = Depends(get_token_stats)
):
    """
    ## 현재 사용자의 토큰 통계 정보를 반환합니다.

    ### Args:
    * token (str): API 토큰 값.

    ### Returns:
    * 토큰 통계 정보 (할당량, 사용량 등)
    """
    # 민감한 내부 필드 제거
    # 서버 시간대를 설정합니다 (예: UTC+9)
    SERVER_TIMEZONE = timezone(timedelta(hours=9))

    public_stats = {
        "total_requests": token_stats["total_requests"],
        "last_month_requests": token_stats["last_month_requests"],
        "monthly_quota": token_stats["monthly_quota"],
        "remaining_quota": token_stats["remaining_quota"],
        "daily_quota": token_stats["daily_quota"],
        "daily_requests": token_stats["daily_requests"],
        "remaining_daily_quota": token_stats["remaining_daily_quota"],
        "last_request_date": (
            token_stats["last_request_date"].astimezone(SERVER_TIMEZONE).isoformat()
            if token_stats["last_request_date"]
            else None
        ),
    }

    return public_stats


@router.get("/get_region_list", response_model=List[RegionResultSlim])
async def get_region_list(
    request: Request,
    type: str = "hd",
    code_list: str = "1100000000,2300000001",
    yyyymm: str = None,
    token: str = "",
    token_stats: dict = Depends(get_token_stats),
):
    """
    ## 주어진 코드로 영역을 찾아 전송합니다.

    ### Args:
    * type (str): 영역 유형. 기본값은 "hd" (행정동)입니다.
    * code (str): 행정동 코드. 기본값은 "1100000000"
    * yyyymm (str, optional): 특정 년월(YYYYMM)의 행정동 등 영역을 조회합니다. 기본값은 None입니다.

    ### Returns:
    * 행정동 정보.

    """
    val_list = []
    code_list = code_list.split(",")
    tasks = [
        ApiHandler().get_region(type, code, yyyymm, slim=True) for code in code_list
    ]
    val_list = await asyncio.gather(*tasks)
    return val_list


@router.get("/get_region", response_model=RegionResult)
async def get_region(
    request: Request,
    type: str = "hd",
    code: str = "1100000000",
    yyyymm: str = None,
    token: str = "",
    token_stats: dict = Depends(get_token_stats),
):
    """
    ## 주어진 코드로 영역을 찾아 전송합니다.

    ### Args:
    * type (str): 영역 유형. 기본값은 "hd" (행정동)입니다.
    * code (str): 행정동 코드. 기본값은 "1100000000"
    * yyyymm (str, optional): 특정 년월(YYYYMM)의 행정동 등 영역을 조회합니다. 기본값은 None입니다.

    ### Returns:
    * 행정동 정보.

    """
    val = await ApiHandler().get_region(type, code, yyyymm)
    return val


@router.get("/region", response_model=RegionResult)
async def region(
    request: Request,
    type: str = "hd",
    x: float = 127.075074,
    y: float = 37.143834,
    yyyymm: str = None,
    token: str = "",
    token_stats: dict = Depends(get_token_stats),
):
    """
    ## 주어진 좌표에 대한 행정동을 조회합니다.

    ### Args:
    * x (float): x 좌표 (경도).
    * y (float): y 좌표 (위도).
    * yyyymm (str, optional): 특정 년월(YYYYMM) 형식으로 행정동 변동 이력을 조회합니다. 기본값은 None입니다.

    ### Returns:
    * 행정동 정보 또는 행정동 정보 목록.

    """
    val = await ApiHandler().region(type, x, y, yyyymm)
    return val


@router.get("/update_region")
async def update_region(
    request: Request,
    name: str = None,  # Input shapefile path
    yyyymm: str = None,  # YYYYMM format for the region data
    region: str = None,  # Region type: hd (행정동), h23 (시군구), h1 (광역시도)
):
    """
    Updates the region data in the database.
    ## 주어진 shapefile 경로에서 행정동 데이터를 업데이트합니다.

    ex)
    # 행정동
    curl 'http://localhost:4009/update_region?name=11000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=26000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=27000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=28000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=29000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=30000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=31000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=36000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=41000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=43000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=44000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=46000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=47000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=48000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=50000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=51000&region=hd&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=52000&region=hd&yyyymm=202305'

    # 시군구
    curl 'http://localhost:4009/update_region?name=11000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=26000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=27000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=28000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=29000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=30000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=31000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=36000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=41000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=43000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=44000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=46000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=47000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=48000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=50000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=51000&region=h23&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=52000&region=h23&yyyymm=202305'

    # 광역시도
    curl 'http://localhost:4009/update_region?name=11000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=26000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=27000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=28000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=29000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=30000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=31000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=36000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=41000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=43000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=44000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=46000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=47000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=48000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=50000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=51000&region=h1&yyyymm=202305'
    curl 'http://localhost:4009/update_region?name=52000&region=h1&yyyymm=202305'

    ### Args:
    * shp_path (str): 업데이트할 shapefile 경로입니다.
    * yyyymm (str): 행정동 데이터의 년월(YYYYMM) 형식입니다.

    ### Returns:
    * 성공 메시지와 처리된 년월(YYYYMM) 정보입니다.
    """

    region_type = region
    if region_type not in ["hd", "h23", "h1"]:
        return HTTPException(
            status_code=400, detail="Invalid region type. Must be 'hd', 'h23', or 'h1'."
        )

    SHP_FILE_NAME_MAP = {
        "hd": "TL_SCCO_GEMD.shp",
        "h23": "TL_SCCO_SIG.shp",
        "h1": "TL_SCCO_CTPRVN.shp",
    }

    shp_path = os.path.join(
        JUSO_DATA_DIR, "전체분", yyyymm, "map", name, SHP_FILE_NAME_MAP[region_type]
    )

    # 입력 확인
    if not os.path.exists(shp_path):
        # logger.error(f"Error: Shapefile {shp_path} does not exist")
        return HTTPException(
            status_code=400, detail=f"Shapefile {shp_path} does not exist"
        )

    try:
        # region_prefix = args.region
        # yyyymm = shp_path.split("/")[-4]  # 예: 202305
        batch_size = 1000

        if await ApiHandler().reverse_geocoder.process_region_to_rocksdb(
            shp_path, region_type, yyyymm, batch_size
        ):
            return {
                "message": f"Region data processed successfully from {shp_path}",
                "yyyymm": yyyymm,
            }
        else:
            return HTTPException(
                status_code=500, detail=f"Failed to process region data from {shp_path}"
            )

    except Exception as e:
        # logger.error(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return HTTPException(
            status_code=500, detail=f"Error processing shapefile: {str(e)}"
        )


@router.get("/merge_hd_history")
async def merge_hd_history(
    request: Request,
    name: str = None,  # Input shapefile path
    db_name: str = None,  # Output directory for RocksDB
    yyyymm: str = None,
):
    """
    주어진 shapefile 경로에서 행정동 변동 이력을 생성합니다.
    Geohash를 사용하여 행정동 변동 이력을 RocksDB에 저장합니다.

    Airflow:  geocoder_monthly_update.merge_hd_history
    ex)
        curl 'http://localhost:4009/merge_hd_history?name=11000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=26000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=27000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=28000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=29000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=30000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=31000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=36000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=41000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=43000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=44000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=46000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=47000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=48000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=50000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=51000&db_name=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/merge_hd_history?name=52000&db_name=hd_history&yyyymm=202507'
    """

    db_path = os.path.join(JUSO_DATA_DIR, "전체분", yyyymm, "map", name, db_name)
    if not os.path.exists(db_path):
        # logger.error(f"Error: RocksDB {db_path} does not exist")
        return HTTPException(
            status_code=400, detail=f"RocksDB {db_path} does not exist"
        )

    try:
        # Shapefile 처리 및 RocksDB 저장
        metadata = await ApiHandler().reverse_geocoder.merge_hd_history(
            db_path,
            yyyymm,
        )

        # 메타데이터 파일 작성 (RocksDB 외부에도 저장)
        with open(os.path.join(db_path, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return metadata

    except Exception as e:
        # logger.error(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return HTTPException(
            status_code=500, detail=f"Error processing shapefile: {str(e)}"
        )


@router.get("/build_hd_history")
async def build_hd_history(
    request: Request,
    name: str = None,  # Input shapefile path
    output_dir: str = None,  # Output directory for RocksDB
    yyyymm: str = None,
    depth: int = 7,  # Geohash precision/depth (default: 7)
):
    """
    주어진 shapefile 경로에서 행정동 변동 이력을 생성합니다.
    Geohash를 사용하여 행정동 변동 이력을 RocksDB에 저장합니다.

    Airflow:  geocoder_monthly_update.update_hd_history
    ex)
        curl 'http://localhost:4009/build_hd_history?name=11000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=26000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=27000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=28000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=29000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=30000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=31000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=36000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=41000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=43000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=44000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=46000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=47000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=48000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=50000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=51000&output_dir=hd_history&yyyymm=202507'
        curl 'http://localhost:4009/build_hd_history?name=52000&output_dir=hd_history&yyyymm=202507'
    """

    # 입력 확인
    shp_path = os.path.join(
        JUSO_DATA_DIR, "전체분", yyyymm, "map", name, f"TL_SCCO_GEMD.shp"
    )

    if not os.path.exists(shp_path):
        # logger.error(f"Error: Shapefile {shp_path} does not exist")
        return HTTPException(
            status_code=400, detail=f"Shapefile {shp_path} does not exist"
        )

    # 출력 디렉토리 생성
    # RocksDB 경로
    db_path = os.path.join(JUSO_DATA_DIR, "전체분", yyyymm, "map", name, output_dir)
    os.makedirs(db_path, exist_ok=True)

    # key_prefix = None  # 기본값은 None, 사용하지 않음
    # batch_size = 1000

    try:
        metadata = await ApiHandler().reverse_geocoder.build_hd_history(
            shp_path,
            db_path,
            depth,
        )

        # # Shapefile 처리 및 RocksDB 저장
        # stats = await asyncio.to_thread(
        #     process_shapefile_to_rocksdb,
        #     shp_path,
        #     db_path,
        #     depth,
        #     key_prefix,
        #     batch_size,
        # )

        # # 메타데이터 파일 작성 (RocksDB 외부에도 저장)
        # metadata = {
        #     "count": stats["total_geohashes"],
        #     "features": stats["total_features"],
        #     "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        #     "elapsed_time": stats["elapsed_time"],
        #     "description": "Geohash database generated from shapefile",
        # }

        with open(os.path.join(db_path, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # logger.info(f"Process completed successfully! Database saved to {db_path}")
        return metadata

    except Exception as e:
        # logger.error(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return HTTPException(
            status_code=500, detail=f"Error processing shapefile: {str(e)}"
        )


@router.get("/hd_history", response_model=List[HdHistoryResult])
async def hd_history(
    request: Request,
    x: float = 127.075074,
    y: float = 37.143834,
    yyyymm: str = None,
    token: str = "",
    token_stats: dict = Depends(get_token_stats),
):
    """
    ## 주어진 좌표에 대한 행정동 변동 이력을 조회합니다.

    ### Args:
    * x (float): x 좌표 (경도).
    * y (float): y 좌표 (위도).
    * yyyymm (str, optional): 특정 년월(YYYYMM) 형식으로 행정동 변동 이력을 조회합니다. 기본값은 None입니다.

    ### Returns:
    * 행정동 변동 이력 목록.

    ## Retrieves administrative district change history for a given coordinate.

    ### Args:
    * x (float): The x-coordinate (longitude).
    * y (float): The y-coordinate (latitude).
    * yyyymm (str, optional): The specific year and month (YYYYMM) to filter the history. Default is None.

    ### Returns:
    A list of administrative district change history.
    """
    val = await ApiHandler().hd_history(x, y, yyyymm)
    return val


@router.get("/update_h1_addr", include_in_schema=False)
async def update_h1_addr():
    """
    광역시도 대표 주소 정보를 업데이트합니다.

    실행: curl 'http://localhost:4009/update_h1_addr'

    Args:
        yyyymm: 업데이트할 광역시도 대표 주소 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    updater = H1AddrUpdater(ApiHandler().geocoder)

    try:
        # StringIO 객체를 사용해 출력을 캡처
        from io import StringIO

        output = StringIO()

        if not await updater.update(output):
            logging.error(f"ERROR: update_h1_addr fail")
            raise HTTPException(status_code=500, detail=f"Failed to update H1 address")

        logging.info(f"update_h1_addr finished")
        return {
            "message": f"update_h1_addr finished",
            "details": output.getvalue(),
        }

    except Exception as e:
        logging.error(f"ERROR: update_h1_addr fail: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating H1 address data: {str(e)}",
        )


@router.get("/update_ld_addr", include_in_schema=False)
async def update_ld_addr(name: str, yyyymm: str):
    """
    법정동 대표 주소를 업데이트합니다.

    실행: curl 'http://localhost:4009/update_ld_addr?name=11000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=26000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=27000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=28000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=29000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=30000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=31000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=36000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=41000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=43000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=44000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=46000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=47000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=48000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=50000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=51000&yyyymm=202504'
        curl 'http://localhost:4009/update_ld_addr?name=52000&yyyymm=202504'


    Args:
        yyyymm: 업데이트할 법정동 대표 주소 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    updater = LdAddrUpdater(ApiHandler().geocoder, name=name, yyyymm=yyyymm)

    try:
        # StringIO 객체를 사용해 출력을 캡처
        from io import StringIO

        output = StringIO()

        if not await updater.update(output):
            logging.error(f"ERROR: update_ld_addr fail")
            raise HTTPException(status_code=500, detail=f"Failed to update Ld address")

        logging.info(f"update_ld_addr finished")
        return {
            "message": f"update_ld_addr finished",
            "details": output.getvalue(),
        }

    except Exception as e:
        logging.error(f"ERROR: update_ld_addr fail: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating Ld address data: {str(e)}",
        )


@router.get("/update_road_addr", include_in_schema=False)
async def update_road_addr(name: str, yyyymm: str):
    """
    도로명 대표 주소를 업데이트합니다.

    실행:curl 'http://localhost:4009/update_road_addr?name=11000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=26000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=27000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=28000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=29000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=30000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=31000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=36000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=41000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=43000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=44000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=46000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=47000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=48000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=50000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=51000&yyyymm=202504'
        curl 'http://localhost:4009/update_road_addr?name=52000&yyyymm=202504'

    Args:
        yyyymm: 업데이트할 리 대표 주소 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    updater = RoadAddrUpdater(ApiHandler().geocoder, name=name, yyyymm=yyyymm)

    try:
        # StringIO 객체를 사용해 출력을 캡처
        from io import StringIO

        output = StringIO()

        if not await updater.update(output):
            logging.error(f"ERROR: update_road_addr fail")
            raise HTTPException(
                status_code=500, detail=f"Failed to update Road address"
            )

        logging.info(f"update_road_addr finished")
        return {
            "message": f"update_road_addr finished",
            "details": output.getvalue(),
        }

    except Exception as e:
        logging.error(f"ERROR: update_road_addr fail: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating Road address data: {str(e)}",
        )


@router.get("/update_ri_addr", include_in_schema=False)
async def update_ri_addr(name: str, yyyymm: str):
    """
    리 대표 주소를 업데이트합니다.

    실행: curl 'http://localhost:4009/update_ri_addr?name=11000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=26000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=27000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=28000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=29000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=30000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=31000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=36000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=41000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=43000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=44000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=46000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=47000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=48000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=50000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=51000&yyyymm=202504'
        curl 'http://localhost:4009/update_ri_addr?name=52000&yyyymm=202504'


    Args:
        yyyymm: 업데이트할 리 대표 주소 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    updater = RiAddrUpdater(ApiHandler().geocoder, name=name, yyyymm=yyyymm)

    try:
        # StringIO 객체를 사용해 출력을 캡처
        from io import StringIO

        output = StringIO()

        if not await updater.update(output):
            logging.error(f"ERROR: update_ri_addr fail")
            raise HTTPException(status_code=500, detail=f"Failed to update Ri address")

        logging.info(f"update_ri_addr finished")
        return {
            "message": f"update_ri_addr finished",
            "details": output.getvalue(),
        }

    except Exception as e:
        logging.error(f"ERROR: update_ri_addr fail: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating Ri address data: {str(e)}",
        )


@router.get("/update_hd_addr", include_in_schema=False)
async def update_hd_addr(name: str, yyyymm: str):
    """
    행정동 대표 주소를 업데이트합니다.

    실행: curl 'http://localhost:4009/update_hd_addr?name=11000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=26000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=27000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=28000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=29000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=30000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=31000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=36000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=41000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=43000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=44000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=46000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=47000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=48000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=50000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=51000&yyyymm=202504'
        curl 'http://localhost:4009/update_hd_addr?name=52000&yyyymm=202504'


    Args:
        yyyymm: 업데이트할 행정동 대표 주소 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    updater = HdAddrUpdater(ApiHandler().geocoder, name=name, yyyymm=yyyymm)

    try:
        # StringIO 객체를 사용해 출력을 캡처
        from io import StringIO

        output = StringIO()

        if not await updater.update(output):
            logging.error(f"ERROR: update_hd_addr fail")
            raise HTTPException(status_code=500, detail=f"Failed to update Hd address")

        logging.info(f"update_hd_addr finished")
        return {
            "message": f"update_hd_addr finished",
            "details": output.getvalue(),
        }

    except Exception as e:
        logging.error(f"ERROR: update_hd_addr fail: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating Hd address data: {str(e)}",
        )


@router.get("/update_h23_addr", include_in_schema=False)
async def update_h23_addr(name: str, yyyymm: str):
    """
    시군구 대표 주소를 업데이트합니다.

    실행: curl 'http://localhost:4009/update_h23_addr?name=11000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=26000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=27000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=28000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=29000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=30000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=31000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=36000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=41000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=43000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=44000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=46000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=47000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=48000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=50000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=51000&yyyymm=202504'
        curl 'http://localhost:4009/update_h23_addr?name=52000&yyyymm=202504'


    Args:
        yyyymm: 업데이트할 시군구 대표 주소의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    updater = H23AddrUpdater(ApiHandler().geocoder, name=name, yyyymm=yyyymm)

    try:
        # StringIO 객체를 사용해 출력을 캡처
        from io import StringIO

        output = StringIO()

        if not await updater.update(output):
            logging.error(f"ERROR: update_h23_addr fail")
            raise HTTPException(status_code=500, detail=f"Failed to update H23 address")

        logging.info(f"update_h23_addr finished")
        return {
            "message": f"update_h23_addr finished",
            "details": output.getvalue(),
        }

    except Exception as e:
        logging.error(f"ERROR: update_h23_addr fail: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating H23 address data: {str(e)}",
        )


@router.get("/update_hd", include_in_schema=False)
async def update_hd(yyyymm: str):
    """
    행정동 정보를 업데이트합니다.

    Args:
        yyyymm: 업데이트할 행정동 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    if not yyyymm:
        raise HTTPException(status_code=400, detail="yyyymm parameter is required")

    updater = HdUpdater(yyyymm, ApiHandler().geocoder)

    try:
        # StringIO 객체를 사용해 출력을 캡처
        from io import StringIO

        output = StringIO()

        if not await updater.update(output):
            logging.error(f"ERROR: update_hd fail ({yyyymm})")
            raise HTTPException(
                status_code=500, detail=f"Failed to update HD data for {yyyymm}"
            )

        logging.info(f"update_hd finished: {yyyymm}")
        return {
            "message": f"update_hd finished: {yyyymm}",
            "details": output.getvalue(),
        }

    except Exception as e:
        logging.error(f"ERROR: update_hd fail ({yyyymm}): {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating HD data for {yyyymm}: {str(e)}"
        )


@router.get("/update_zip", include_in_schema=False)
async def update_zip(yyyymm: str):
    """
    우편번호(국가기초구역) 정보를 업데이트합니다.

    Args:
        yyyymm: 업데이트할 국가기초구역 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    if not yyyymm:
        raise HTTPException(status_code=400, detail="yyyymm parameter is required")

    updater = ZUpdater(yyyymm, ApiHandler().geocoder)

    try:
        # StringIO 객체를 사용해 출력을 캡처
        from io import StringIO

        output = StringIO()

        if not await updater.update(output):
            logging.error(f"ERROR: update_zip fail ({yyyymm})")
            raise HTTPException(
                status_code=500, detail=f"Failed to update ZIP data for {yyyymm}"
            )

        logging.info(f"update_zip finished: {yyyymm}")
        return {
            "message": f"update_zip finished: {yyyymm}",
            "details": output.getvalue(),
        }

    except Exception as e:
        logging.error(f"ERROR: update_zip fail ({yyyymm}): {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating ZIP data for {yyyymm}: {str(e)}"
        )


@router.get("/update_navi", include_in_schema=False)
async def update_navi(name: str, yyyymm: str):
    """
    내비게이션 정보를 업데이트합니다.

    Args:
        name: 업데이트할 내비게이션 데이터의 이름
        yyyymm: 업데이트할 내비게이션 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    if not name:
        err_msg = """<p>name parameter is required. one of the following:</p>
<li>          
<ul>match_bld_busan.txt</ul>
<ul>match_bld_chungbuk.txt</ul>
<ul>match_bld_chungnam.txt</ul>
<ul>match_bld_daegu.txt</ul>
<ul>match_bld_daejeon.txt</ul>
<ul>match_bld_gangwon.txt</ul>
<ul>match_bld_gwangju.txt</ul>
<ul>match_bld_gyeongbuk.txt</ul>
<ul>match_bld_gyeongnam.txt</ul>
<ul>match_bld_gyunggi.txt</ul>
<ul>match_bld_incheon.txt</ul>
<ul>match_bld_jeju.txt</ul>
<ul>match_bld_jeonbuk.txt</ul>
<ul>match_bld_jeonnam.txt</ul>
<ul>match_bld_sejong.txt</ul>
<ul>match_bld_seoul.txt</ul>
<ul>match_bld_ulsan.txt</ul>
</li>
        """
        raise HTTPException(status_code=400, detail=err_msg)

    updater = NaviUpdater(yyyymm, name, ApiHandler().geocoder)

    try:
        output = StringIO()
        if not await updater.update(output):
            logging.error(f"ERROR: update_navi fail ({yyyymm}/{name})")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update navi data for {yyyymm}/{name}\n{output.getvalue()}",
            )

        logging.info(f"update_navi finished: {yyyymm}/{name}")
        return {"message": f"update_navi finished: {yyyymm}/{name}"}

    except Exception as e:
        logging.error(f"ERROR: update_navi fail ({yyyymm}/{name}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating navi data for {yyyymm}/{name}: {str(e)}",
        )


@router.get("/update_roadbase", include_in_schema=False)
async def update_roadbase(name: str, yyyymm: str):
    """
    기초번호 정보를 업데이트합니다.

    Args:
        name: 업데이트할 기초번호 데이터의 이름
        yyyymm: 업데이트할 기초번호 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    if not name:
        err_msg = """<p>name parameter is required. one of the following:</p>
<li>          
<ul>BSISNDATA_2505_11000.txt</ul>
<ul>BSISNDATA_2505_26000.txt</ul>
<ul>BSISNDATA_2505_27000.txt</ul>
<ul>BSISNDATA_2505_28000.txt</ul>
<ul>BSISNDATA_2505_29000.txt</ul>
<ul>BSISNDATA_2505_30000.txt</ul>
<ul>BSISNDATA_2505_31000.txt</ul>
<ul>BSISNDATA_2505_36110.txt</ul>
<ul>BSISNDATA_2505_41000.txt</ul>
<ul>BSISNDATA_2505_43000.txt</ul>
<ul>BSISNDATA_2505_44000.txt</ul>
<ul>BSISNDATA_2505_46000.txt</ul>
<ul>BSISNDATA_2505_47000.txt</ul>
<ul>BSISNDATA_2505_48000.txt</ul>
<ul>BSISNDATA_2505_50000.txt</ul>
<ul>BSISNDATA_2505_51000.txt</ul>
<ul>BSISNDATA_2505_52000.txt</ul>
</li>

curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_11000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_26000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_27000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_28000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_29000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_30000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_31000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_36110.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_41000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_43000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_44000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_46000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_47000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_48000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_50000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_51000.txt&yyyymm=202504'
curl 'http://localhost:4009/update_roadbase?name=BSISNDATA_2505_52000.txt&yyyymm=202504'
        """
        raise HTTPException(status_code=400, detail=err_msg)

    updater = RoadbaseUpdater(yyyymm, name, ApiHandler().geocoder)

    try:
        output = StringIO()
        if not await updater.update(output):
            logging.error(f"ERROR: update_roadbase fail ({yyyymm}/{name})")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update navi data for {yyyymm}/{name}\n{output.getvalue()}",
            )

        logging.info(f"update_roadbase finished: {yyyymm}/{name}")
        return {"message": f"update_roadbase finished: {yyyymm}/{name}"}

    except Exception as e:
        logging.error(f"ERROR: update_roadbase fail ({yyyymm}/{name}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating navi data for {yyyymm}/{name}: {str(e)}",
        )


@router.get("/update_spot", include_in_schema=False)
async def update_spot(yyyymm: str):
    """
    스팟 정보를 업데이트합니다.

    Args:
        yyyymm: 업데이트할 스팟 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    if not yyyymm:
        raise HTTPException(status_code=400, detail="yyyymm parameter is required")

    updater = SpotUpdater(yyyymm, ApiHandler().geocoder)

    try:
        output = StringIO()
        if not await updater.update(output):
            logging.error(f"ERROR: update_spot fail ({yyyymm})")
            raise HTTPException(
                status_code=500, detail=f"Failed to update spot data for {yyyymm}"
            )

        logging.info(f"update_spot finished: {yyyymm}")
        return {"message": f"update_spot finished: {yyyymm}"}

    except Exception as e:
        logging.error(f"ERROR: update_spot fail ({yyyymm}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating spot data for {yyyymm}: {str(e)}",
        )


@router.get("/update_entrc", include_in_schema=False)
async def update_entrc(name: str, yyyymm: str):
    """
    엔트리 정보를 업데이트합니다.

    Args:
        name: 업데이트할 엔트리 데이터의 이름
        yyyymm: 업데이트할 엔트리 데이터의 년월(YYYYMM) 형식

    Returns:
        업데이트 결과 메시지
    """
    if not name:
        err_msg = """<p>name parameter is required. one of the following:</p>
<li>          
<ul>entrc_busan.txt</ul>
<ul>entrc_chungbuk.txt</ul>
<ul>entrc_chungnam.txt</ul>
<ul>entrc_daegu.txt</ul>
<ul>entrc_daejeon.txt</ul>
<ul>entrc_gangwon.txt</ul>
<ul>entrc_gwangju.txt</ul>
<ul>entrc_gyeongbuk.txt</ul>
<ul>entrc_gyeongnam.txt</ul>
<ul>entrc_gyunggi.txt</ul>
<ul>entrc_incheon.txt</ul>
<ul>entrc_jeju.txt</ul>
<ul>entrc_jeonbuk.txt</ul>
<ul>entrc_jeonnam.txt</ul>
<ul>entrc_sejong.txt</ul>
<ul>entrc_seoul.txt</ul>
<ul>entrc_ulsan.txt</ul>
</li>
        """
        raise HTTPException(status_code=400, detail=err_msg)
    updater = EntrcUpdater(yyyymm, name, ApiHandler().geocoder)
    try:
        output = StringIO()
        if not await updater.update(output):
            logging.error(f"ERROR: update_entrc fail ({yyyymm}/{name})")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update entrc data for {yyyymm}/{name}",
            )

        logging.info(f"update_entrc finished: {yyyymm}/{name}")
        return {"message": f"update_entrc finished: {yyyymm}/{name}"}
    except Exception as e:
        logging.error(f"ERROR: update_entrc fail ({yyyymm}/{name}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"ERROR: update_entrc fail (전체분/entrc/{yyyymm}/{name})".encode(
                "utf-8"
            ),
        )


@router.get("/delete_jibun_in_pnu", include_in_schema=False)
async def delete_jibun_in_pnu():
    """
    PNU(지적도)에서 지번 정보를 삭제합니다.

    rocksdb3 의 모든 key, value 를 순회
    key 에 "extras"가 포함되어 있으면 삭제

    Returns:
        삭제 결과 메시지
    """
    iter = ApiHandler.geocoder.db._db.get_iter()
    n = 0
    k, v = next(iter)
    while k:
        try:
            jj = json.loads(v.decode())
            for j in jj:
                if "extras" in j:
                    if len(jj) == 1:
                        ApiHandler.geocoder.db._db.delete(k)
                    else:
                        jj.remove(j)
                        ApiHandler.geocoder.db._db.put(k, json.dumps(jj).encode())

        except Exception as e:
            print(e, k.decode(), v)

        n += 1
        if n % 1000000 == 0:
            print(f"{n:,}")

        try:
            k, v = next(iter)
        except StopIteration:
            print(f"{n:,} StopIteration")
            break

    logging.info(f"delete_jibun_in_pnu finished")
    return {"message": "delete_jibun_in_pnu finished"}


@router.get("/delete_all_pnu", include_in_schema=False)
async def delete_all_pnu():
    """
    PNU(지적도) 데이터를 모두 삭제합니다.
    curl 'http://localhost:4009/delete_all_pnu'
    """
    updater = PnuUpdater("delete", "", ApiHandler().geocoder)

    try:
        output = StringIO()  # Create a string write buffer
        if not await updater.delete_all(output):
            logging.error(f"ERROR: delete_all_pnu fail")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete jibun in pnu data",
            )

        logging.info(f"delete_all_pnu finished")
        return {"message": f"delete_all_pnu finished: \n{output.getvalue()}"}

    except Exception as e:
        logging.error(f"ERROR: delete_all_pnu fail: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error delete_all_pnu: {str(e)}",
        )


@router.get("/update_jibun_in_pnu", include_in_schema=False)
async def update_jibun_in_pnu(file: str, yyyymm: str):
    """
    PNU(지적도)에서 지번 정보를 업데이트합니다.
    월간 업데이트용이며 vworld의 연속지적도를 사용. "연속지적지형도" 가 아님 주의.
    "연속지적지형도"를 이용한 업데이트는 과거 데이터를 이용하기 위해 1회성으로 사용했음. update_jibun_in_pnu_shp2에 archived.

    "연속지적지형도"는 reverse geocoding에도 사용 됨.

    실행:
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_11_202507.shp&yyyymm=202507' # 서울      902,493
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_26_202507.shp&yyyymm=202507' # 부산      708,412
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_27_202507.shp&yyyymm=202507' # 대구      789,763
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_28_202507.shp&yyyymm=202507' # 인천      669,059
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_29_202507.shp&yyyymm=202507' # 광주      387,860
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_30_202507.shp&yyyymm=202507' # 대전      292,574
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_31_202507.shp&yyyymm=202507' # 울산      510,767
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_36110_202507.shp&yyyymm=202507' # 세종   205,119
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_41_202507.shp&yyyymm=202507' # 경기도   5,190,303
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_43_202507.shp&yyyymm=202507' # 충청북도 2,402,775
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_44_202507.shp&yyyymm=202507' # 충청남도 3,756,113
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_46_202507.shp&yyyymm=202507' # 전라남도 5,913,968
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_47_202507.shp&yyyymm=202507' # 경상북도 5,716,889
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_48_202507.shp&yyyymm=202507' # 경상남도 4,823,336
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_50_202507.shp&yyyymm=202507' # 제주도    882,245
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_51_202507.shp&yyyymm=202507' # 강원도   2,744,896
        curl 'http://localhost:4009/update_jibun_in_pnu?file=LSMD_CONT_LDREG_52_202507.shp&yyyymm=202507' # 전라북도 3,878,900
    """
    if not file:
        raise HTTPException(status_code=400, detail="file parameter is required")

    updater = PnuUpdater(file, yyyymm, ApiHandler().geocoder)

    try:
        output = StringIO()  # Create a string write buffer
        if not await updater.update(output):
            logging.error(f"ERROR: update_jibun_in_pnu fail")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update jibun in pnu data for {file}",
            )

        logging.info(f"update_jibun_in_pnu finished")
        return {"message": f"update_jibun_in_pnu finished: {file}\n{output.getvalue()}"}

    except Exception as e:
        logging.error(f"ERROR: update_jibun_in_pnu fail ({file}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating jibun in pnu data for {file}: {str(e)}",
        )


@router.get("/update_jibun_in_pnu_shp2", include_in_schema=False)
async def update_jibun_in_pnu_shp2(file: str, yyyymm: str):
    """
    PNU(지적도)에서 지번 정보를 업데이트합니다.

    실행:
        2025년 5월 기준
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_11_202505.shp' # 서울      902,493
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_26_202505.shp' # 부산      708,412
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_27_202505.shp' # 대구      789,763
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_28_202505.shp' # 인천      669,059
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_29_202505.shp' # 광주      387,860
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_30_202505.shp' # 대전      292,574
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_31_202505.shp' # 울산      510,767
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_36110_202505.shp' # 세종   205,119
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_41_202505.shp' # 경기도   5,190,303
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_43_202505.shp' # 충청북도 2,402,775
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_44_202505.shp' # 충청남도 3,756,113
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_46_202505.shp' # 전라남도 5,913,968
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_47_202505.shp' # 경상북도 5,716,889
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_48_202505.shp' # 경상남도 4,823,336
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_50_202505.shp' # 제주도    882,245
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_51_202505.shp' # 강원도   2,744,896
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_52_202505.shp' # 전라북도 3,878,900

        2024년 4월 기준
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_11_202404.shp' # 서울
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_26_202404.shp' # 부산
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_27_202404.shp' # 대구
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_28_202404.shp' # 인천
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_29_202404.shp' # 광주
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_30_202404.shp' # 대전
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_31_202404.shp' # 울산
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_36_202404.shp' # 세종
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_41_202404.shp' # 경기도
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_43_202404.shp' # 충청북도
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_44_202404.shp' # 충청남도
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_46_202404.shp' # 전라남도
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_47_202404.shp' # 경상북도
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_48_202404.shp' # 경상남도
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_50_202404.shp' # 제주도
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_51_202404.shp' # 강원도
        curl 'http://localhost:4009/update_jibun_in_pnu_shp2?file=LSMD_CONT_LDREG_52_202404.shp' # 전라북도


    Args:
        file: 업데이트할 PNU 데이터의 파일 이름

    Returns:
        업데이트 결과 메시지
    """
    if not file:
        raise HTTPException(status_code=400, detail="file parameter is required")

    updater = PnuUpdater(file, yyyymm, ApiHandler().geocoder)

    try:
        output = StringIO()  # Create a string write buffer
        if not await updater.update_shp2(output):
            logging.error(f"ERROR: update_jibun_in_pnu fail")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update jibun in pnu data for {file}",
            )

        logging.info(f"update_jibun_in_pnu finished")
        return {"message": f"update_jibun_in_pnu finished: {file}\n{output.getvalue()}"}

    except Exception as e:
        logging.error(f"ERROR: update_jibun_in_pnu fail ({file}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating jibun in pnu data for {file}: {str(e)}",
        )


@router.get("/update_bld", include_in_schema=False)
async def update_bld(file: str, yyyymm: str):
    """
    건물도형 정보를 업데이트합니다.

    Args:
        file: 업데이트할 건물도형 데이터의 파일 이름

    Returns:
        업데이트 결과 메시지
    """
    if not file:
        raise HTTPException(status_code=400, detail="file parameter is required")

    shp_path = f"{JUSO_DATA_DIR}/전체분/{yyyymm}/bld/{file}"
    # shp_path = f"{JUSO_DATA_DIR}/건물도형/shp/{file}"
    try:
        if not await ApiHandler.reverse_geocoder.update_bld(shp_path):
            logging.error(f"ERROR: update_bld fail ({file})")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update bld data for {file}",
            )

        logging.info(f"update_bld finished")
        return {"message": f"update_bld finished: {file}"}

    except Exception as e:
        logging.error(f"ERROR: update_bld fail ({file}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating bld data for {file}: {str(e)}",
        )


@router.get("/update_pnu", include_in_schema=False)
async def update_pnu(file: str, yyyymm: str):
    """
    PNU(지적도) 정보를 업데이트합니다.

    실행: curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_11_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_26_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_27_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_28_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_29_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_30_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_31_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_36110_202505.shp&yyyymm=202505{yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_41_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_43_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_44_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_46_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_47_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_48_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_50_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_51_202505.shp&yyyymm={yyyymm}'
        curl 'http://localhost:4009/update_pnu?file=LSMD_CONT_LDREG_52_202505.shp&yyyymm={yyyymm}'


    Args:
        file: 업데이트할 PNU 데이터의 파일 이름

    Returns:
        업데이트 결과 메시지
    """
    if not file:
        raise HTTPException(status_code=400, detail="file parameter is required")

    shp_path = f"{JUSO_DATA_DIR}/전체분/{yyyymm}/pnu/{file}"
    # shp_path = f"{JUSO_DATA_DIR}/연속지적/shp/{file}"
    try:
        if not await ApiHandler.reverse_geocoder.update_pnu(shp_path):
            logging.error(f"ERROR: update_pnu fail ({file})")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update pnu data for {file}",
            )

        logging.info(f"update_pnu finished")
        return {"message": f"update_pnu finished: {file}"}

    except Exception as e:
        logging.error(f"ERROR: update_pnu fail ({file}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating pnu data for {file}: {str(e)}",
        )


@router.get("/update", include_in_schema=False)
async def update(date: str, download: bool = True):
    """
    일 변동분 정보를 업데이트합니다.

    Args:
        date: 업데이트할 일 변동분 데이터의 날짜(YYYYMMDD) 형식

    Returns:
        업데이트 결과 메시지

    예:
        http://localhost:400/update?date=20250528
    """
    if not date:
        raise HTTPException(status_code=400, detail="date parameter is required")

    API_KEY = "U01TX0FVVEgyMDI0MDMxOTA1MDcxMDExNDYwODI="
    updater = DailyUpdater(
        date, ApiHandler().geocoder, ApiHandler().reverse_geocoder, API_KEY
    )

    try:
        if download and not await updater.download():
            logging.error(f"ERROR: download fail ({date})")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download data for {date}",
            )

        output = StringIO()
        if not await updater.update(output):
            logging.error(f"ERROR: update fail ({date})")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update data for {date}",
            )

        logging.info(f"update finished: {date}")
        return {"message": f"update finished: {date}"}

    except Exception as e:
        logging.error(f"ERROR: update fail ({date}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating data for {date}: {str(e)}",
        )


@router.get("/log_navi", include_in_schema=False)
async def log_navi(name: str, yyyymm: str):
    """
    내비게이션 로그를 반환합니다.

    Args:
        name: 로그 파일 이름
        yyyymm: 로그 파일의 년월(YYYYMM) 형식

    Returns:
        로그 내용

    예:
        https://geocode-api.gimi9.com/log_navi?yyyymm=202502&name=match_build_busan.txt
    """
    if not name or not yyyymm:
        raise HTTPException(
            status_code=400, detail="name and yyyymm parameters are required"
        )

    log_file = f"{JUSO_DATA_DIR}/전체분/{yyyymm}/navi/{name}.log"
    try:
        with open(log_file, "r") as f:
            log = f.read()
            return log
    except FileNotFoundError:
        logging.error(f"ERROR: log file not found ({log_file})")
        raise HTTPException(status_code=404, detail="Log file not found")


@router.get("/log_spot", include_in_schema=False)
async def log_spot(yyyymm: str):
    """
    스팟 로그를 반환합니다.

    Args:
        yyyymm: 로그 파일의 년월(YYYYMM) 형식

    Returns:
        로그 내용
    """
    if not yyyymm:
        raise HTTPException(status_code=400, detail="yyyymm parameter is required")

    log_file = f"{JUSO_DATA_DIR}/전체분/{yyyymm}/spot/spot.log"
    try:
        with open(log_file, "r") as f:
            log = f.read()
            return log
    except FileNotFoundError:
        logging.error(f"ERROR: log file not found ({log_file})")
        raise HTTPException(status_code=404, detail="Log file not found")


@router.get("/log_entrc", include_in_schema=False)
async def log_entrc(name: str, yyyymm: str):
    """
    엔트리 로그를 반환합니다.

    Args:
        name: 로그 파일 이름
        yyyymm: 로그 파일의 년월(YYYYMM) 형식

    Returns:
        로그 내용
    """
    if not name or not yyyymm:
        raise HTTPException(
            status_code=400, detail="name and yyyymm parameters are required"
        )

    log_file = f"{JUSO_DATA_DIR}/전체분/{yyyymm}/entrc/{name}.log"
    try:
        with open(log_file, "r") as f:
            log = f.read()
            return log
    except FileNotFoundError:
        logging.error(f"ERROR: log file not found ({log_file})")
        raise HTTPException(status_code=404, detail="Log file not found")


@router.get("/log", include_in_schema=False)
async def log(date: str):
    """
    로그를 반환합니다.

    Args:
        date: 로그 파일의 날짜(YYYYMMDD) 형식

    Returns:
        로그 내용
    """
    if date:
        log_file = f"{JUSO_DATA_DIR}/일변동분/{date}/update.log"
        try:
            with open(log_file, "r") as f:
                log = f.read()
                return log
        except FileNotFoundError:
            logging.error(f"ERROR: log file not found ({log_file})")
            raise HTTPException(status_code=404, detail="Log file not found")
    else:
        err_msg = "date parameter is required"
        logging.error(f"{err_msg}")
        raise HTTPException(status_code=400, detail=err_msg)


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    파비콘 요청을 처리합니다.

    Returns:
        None
    """
    # favicon.ico 요청에 대한 응답을 처리합니다.
    # 이 경우에는 아무것도 반환하지 않습니다.
    return None


app.include_router(router)


class ApiHandler:
    geocoder = Geocoder()
    reverse_geocoder = ReverseGeocoder()
    if config.THREAD_POOL_SIZE > 0:
        executor = ThreadPoolExecutor(
            max_workers=config.THREAD_POOL_SIZE
        )  # 스레드 풀 생성
    else:
        executor = None

    tf = Transformer.from_crs(
        CRS.from_string("EPSG:5179"), CRS.from_string("EPSG:4326"), always_xy=True
    )

    def read_key(self, key):
        val = ApiHandler.geocoder.db.get(key)
        return val

    async def get_region(
        self, type: str, code: str, yyyymm: str = None, slim: bool = False
    ):
        val = self.reverse_geocoder.get_region(type, code, yyyymm, slim)
        return val

    async def region(self, type: str, x: float, y: float, yyyymm: str = None):
        val = self.reverse_geocoder.search_region(type, x, y, yyyymm)
        return val

    async def hd_history(
        self, x: float, y: float, yyyymm: str = None, full_history_list: bool = False
    ):
        start_time = time.time()
        val = self.reverse_geocoder.search_hd_history(x, y, yyyymm, full_history_list)
        elapsed_time = time.time() - start_time
        # 소요 시간을 로그에 기록
        logging.debug(
            f"Execution time for hd_history({x}, {y}, {yyyymm}): {elapsed_time:.6f} seconds"
        )
        return val

    async def reverse_geocode(self, x: float, y: float):
        start_time = time.time()  # 시작 시간 측정

        val = self.reverse_geocoder.search(x, y)

        elapsed_time = time.time() - start_time  # 소요 시간 계산

        # 소요 시간을 로그에 기록
        logging.debug(
            f"Execution time for reverse_geocode({x}, {y}): {elapsed_time:.6f} seconds"
        )

        return val

    def _geocode_worker(self, addr: str):
        """개별 주소를 지오코딩하는 작업자 함수"""
        val = ApiHandler.geocoder.search(addr)
        if not val:
            val = {}
        elif val.get("success") and val.get("x"):
            x1, y1 = ApiHandler.tf.transform(val["x"], val["y"])
            val[X_AXIS] = x1
            val[Y_AXIS] = y1

            hd_history = self.reverse_geocoder.search_hd_history(
                x1, y1, full_history_list=False
            )
            val["hd_history"] = hd_history

        val["inputaddr"] = addr
        return val

    async def geocode(self, addrs: List[str]):
        """주소 목록을 병렬로 지오코딩합니다."""
        start_time = time.time()

        limited_addrs = addrs[:LINES_LIMIT]

        if self.executor:
            # 스레드 풀을 사용하여 병렬로 지오코딩 작업 수행
            execute_results = self.executor.map(
                self._geocode_worker, (addr for addr in limited_addrs)
            )
        else:
            # 스레드 풀이 없으면 동기적으로 실행
            execute_results = map(self._geocode_worker, limited_addrs)

        success_count = 0
        hd_success_count = 0
        results = []

        for i, val in enumerate(execute_results):
            # for val in results:
            # Keep only minimal values in val
            unused_keys = [
                "bld_x",
                "bld_y",
                "extras",
                # "toksString",
                "undgrnd_yn",
                "x",
                "y",
                "bng1",
                "bng2",
                "h1",
                "h1_nm",
                "h2_cd",
                "h23_nm",
                # "hash",
                "hc",
                "lc",
                "ld_cd",
                "ld_nm",
                "rc",
                "ri_nm",
                "road_cd",
                "road_nm",
                "san",
                "similar_hash",
            ]

            for key in unused_keys:
                if key in val:
                    del val[key]

            results.append(val)
            if val.get("success") and val.get("pos_cd", "") in POS_CD_SUCCESS:
                success_count += 1
            if val.get("hd_cd"):
                hd_success_count += 1

        total_count = len(limited_addrs)
        fail_count = total_count - success_count

        summary = {
            "total_time": time.time() - start_time,
            "total_count": total_count,
            "success_count": success_count,
            "hd_success_count": hd_success_count,
            "fail_count": fail_count,
            "results": results,
        }
        return summary

    async def geocode_old(self, addrs):
        summary = {}
        result = []
        count = 0
        success_count = 0
        hd_success_count = 0
        fail_count = 0
        start_time = time.time()

        for addr in addrs[:LINES_LIMIT]:
            count += 1
            val = ApiHandler.geocoder.search(addr)
            if not val:
                val = {}
                fail_count += 1
            elif val["success"]:
                if val["x"]:
                    x1, y1 = ApiHandler.tf.transform(val["x"], val["y"])
                    val[X_AXIS] = x1
                    val[Y_AXIS] = y1
                    if val.get("pos_cd", "") in POS_CD_SUCCESS:
                        success_count += 1
                else:
                    fail_count += 1

            if val.get("hd_cd"):
                hd_success_count += 1
            else:
                pass

            val["inputaddr"] = addr
            result.append(val)

        summary["total_time"] = time.time() - start_time
        summary["total_count"] = count
        summary["success_count"] = success_count
        summary["hd_success_count"] = hd_success_count
        fail_count = count - success_count
        summary["fail_count"] = fail_count
        summary["results"] = result

        return summary


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1]) or DEFAULT_PORT
        except ValueError:
            print(f"Invalid port number. Using default port {DEFAULT_PORT}.")

    LOG_PATH = f"{os.getcwd()}/log/geocode-api.log"
    print(f"logging to {LOG_PATH}")

    # 로그 설정
    logging.basicConfig(
        filename=LOG_PATH,
        encoding="utf-8",
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        force=True,
    )

    uvicorn.run(app, host="0.0.0.0", port=port)

    logging.info(f"Stopping {APP_NAME}...\n")

from fastapi import Depends, HTTPException, Header, Request, status
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone
from src.database import Database


async def get_token_from_request(request: Request) -> str:
    """
    요청 헤더 또는 쿼리 파라미터에서 토큰을 추출합니다.
    """
    # 헤더에서 토큰 가져오기 시도
    auth_header = request.headers.get("Authorization")
    if auth_header:
        if auth_header == "DEMO_TOKEN":
            return "54e83e0e3f06665617ac91b55548dd04169bed9e"  # 테스트용 토큰
        return auth_header
    else:
        # 인증 헤더가 없으면 쿼리 파라미터에서 토큰을 찾습니다
        # logging.debug("Authorization header not found, checking query parameters.")

        # 쿼리 파라미터에서 토큰 가져오기 시도
        token = request.query_params.get("token")
        if token:
            if token == "DEMO_TOKEN":
                token = "54e83e0e3f06665617ac91b55548dd04169bed9e"  # 테스트용 토큰
            return token

    # Swagger UI에서 호출한 경우
    if request.headers.get("referer", "").endswith("/docs"):
        # Swagger UI에서 호출한 경우, 토큰을 쿼리 파라미터로 전달하도록 안내
        return "54e83e0e3f06665617ac91b55548dd04169bed9e"  # 테스트용 토큰

    # 인증 헤더를 찾을 수 없음
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API 토큰이 필요합니다. 헤더('Authorization: YOUR_TOKEN') 또는 쿼리 파라미터(?token=YOUR_TOKEN)를 사용해주세요.",
        headers={"WWW-Authenticate": "Token"},
    )


async def write_usage_log(
    token_id: str,
    endpoint: str,
    success_count: int = 0,
    hd_success_count: int = 0,
    error_count: int = 0,
    ip_address: Optional[str] = None,
    processing_time: float = 0.0,
    billable: bool = True,
    quota_consumed: int = 0,
    request: Optional[Request] = None,
) -> None:
    """
    API 사용 로그를 geocode_usagelog 테이블에 기록합니다.

    Args:
        token_id: API 토큰 ID
        endpoint: 호출된 API 엔드포인트
        success_count: 성공한 요청 수
        hd_success_count: 행정동 성공 수
        error_count: 실패한 요청 수
        ip_address: 클라이언트 IP 주소
        processing_time: 처리 시간(초)
        billable: 과금 대상 여부
        quota_consumed: 소비된 할당량
        request: FastAPI Request 객체 (IP 주소 추출에 사용)
    """
    try:
        # 현재 시간 설정
        now = datetime.now(timezone.utc)

        # 요청 객체가 제공된 경우 IP 주소 추출
        if request and not ip_address:
            ip_address = request.client.host if request.client else None

        # 토큰과 연결된 사용자 ID 조회
        user_id = await Database.fetchval(
            "SELECT user_id FROM authtoken_token WHERE key = $1", token_id
        )

        if not user_id:
            logging.error(f"Failed to get user_id for token: {token_id}")
            # 기본 사용자 ID (예: 시스템 사용자)
            user_id = 1  # 또는 적절한 기본값 설정

        # 로그 기록
        await Database.execute(
            """
            INSERT INTO geocode_usagelog
            (timestamp, endpoint, success_count, error_count, ip_address, 
                processing_time, billable, quota_consumed, token_id, user_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            now,
            endpoint,
            success_count,
            error_count,
            ip_address,
            processing_time,
            billable,
            quota_consumed,
            token_id,
            user_id,
        )

        logging.debug(
            f"Usage log recorded for token {token_id}: endpoint={endpoint}, "
            f"success={success_count}, hd_success={hd_success_count}, errors={error_count}, quota={quota_consumed}"
        )

    except Exception as e:
        # 로깅 실패는 서비스에 영향을 주지 않도록 예외를 잡습니다
        logging.error(f"Failed to write usage log: {str(e)}")


async def update_token_stats(token_id: str, success_count: int) -> Dict[str, Any]:
    try:
        now = datetime.now(timezone.utc)

        # 7. 통계 업데이트
        await Database.execute(
            """
            UPDATE geocode_tokenstats 
            SET total_requests = total_requests + $3,
                last_month_requests = last_month_requests + $3,
                remaining_quota = remaining_quota - $3,
                last_request_date = $1,
                daily_requests = daily_requests + $3,
                remaining_daily_quota = remaining_daily_quota - $3
            WHERE token_id = $2
            """,
            now,
            token_id,
            success_count,
        )

        # 업데이트된 통계 가져오기
        updated_stats = await Database.fetchrow(
            "SELECT * FROM geocode_tokenstats WHERE token_id = $1", token_id
        )

        return dict(updated_stats)
    except Exception as e:
        logging.error(f"Error updating token stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="토큰 통계 업데이트 중 오류가 발생했습니다.",
        )


async def validate_token_stats(token_id: str) -> Dict[str, Any]:
    """
    토큰의 유효성을 검사하고 통계를 업데이트합니다.
    """
    try:
        # 1. 토큰이 데이터베이스에 존재하는지 확인
        token_exists = await Database.fetchval(
            "SELECT EXISTS(SELECT 1 FROM geocode_dj.authtoken_token WHERE key = $1)",
            token_id,
        )
        # token_exists = await Database.fetchval(
        #     "SELECT EXISTS(SELECT 1 FROM geocode_tokenstats WHERE token_id = $1)",
        #     token_id,
        # )

        if not token_exists:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다.",
                headers={"WWW-Authenticate": "Token"},
            )

        # 2. 토큰 통계 가져오기
        token_stats = await Database.fetchrow(
            "SELECT * FROM geocode_tokenstats WHERE token_id = $1", token_id
        )

        now = datetime.now(timezone.utc)

        # 3. 토큰 통계가 없으면 생성
        if not token_stats:
            # 기본값으로 새 레코드 생성
            default_monthly_quota = 100000  # 기본 월별 할당량
            default_daily_quota = 10000  # 기본 일별 할당량

            token_stats = await Database.fetchrow(
                """
                INSERT INTO geocode_tokenstats 
                (total_requests, last_month_requests, monthly_quota, remaining_quota, 
                last_request_date, token_id, daily_quota, daily_requests, remaining_daily_quota)
                VALUES (0, 0, $1, $1, $2, $3, $4, 0, $4)
                RETURNING *
                """,
                default_monthly_quota,
                now,
                token_id,
                default_daily_quota,
            )

        # 4. 일별 할당량 초기화 확인 (자정 이후 첫 요청인 경우)
        last_request_date = token_stats["last_request_date"]
        if last_request_date and (now.date() > last_request_date.date()):
            # 일별 통계 초기화
            await Database.execute(
                """
                UPDATE geocode_tokenstats 
                SET daily_requests = 0, 
                    remaining_daily_quota = daily_quota
                WHERE token_id = $1
                """,
                token_id,
            )
            # 업데이트된 통계 다시 가져오기
            token_stats = await Database.fetchrow(
                "SELECT * FROM geocode_tokenstats WHERE token_id = $1", token_id
            )

        # 5. 월별 할당량 초기화 확인 (월이 바뀐 경우)
        if last_request_date and (
            now.month != last_request_date.month or now.year != last_request_date.year
        ):
            # 월별 통계 초기화
            await Database.execute(
                """
                UPDATE geocode_tokenstats 
                SET last_month_requests = 0, 
                    remaining_quota = monthly_quota
                WHERE token_id = $1
                """,
                token_id,
            )
            # 업데이트된 통계 다시 가져오기
            token_stats = await Database.fetchrow(
                "SELECT * FROM geocode_tokenstats WHERE token_id = $1", token_id
            )

        # 6. 할당량 초과 확인
        if token_stats["remaining_quota"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f'월별 API 할당량({token_stats["monthly_quota"]})을 초과했습니다. 다음 달까지 기다리거나 할당량을 늘리세요.',
            )

        if token_stats["remaining_daily_quota"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f'일일 API 할당량({token_stats["daily_quota"]}건)을 초과했습니다. 내일 다시 시도하거나 할당량을 늘리세요.',
            )

        token_stats_dict = dict(token_stats)

        if token_id in ("DEMO_TOKEN", "54e83e0e3f06665617ac91b55548dd04169bed9e"):
            token_stats_dict["quarter"] = (
                100  # 테스트용 토큰의 처리건수를 100건으로 제한
            )

        return token_stats_dict

    except HTTPException:
        # 이미 적절한 예외가 발생한 경우 그대로 전달
        raise
    except Exception as e:
        logging.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="토큰 검증 중 오류가 발생했습니다.",
        )


async def get_token_stats(request: Request) -> Dict[str, Any]:
    """
    토큰 인증 및 통계 업데이트를 위한 의존성 함수입니다.
    """
    token = await get_token_from_request(request)
    return await validate_token_stats(token)

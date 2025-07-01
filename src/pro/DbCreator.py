import json
import re
import threading
import os
import psycopg2
import psycopg2.extras

# import leveldb
import rocksdb3

import sys

sys.path.append("/home/gisman/projects/geocoder-kr/src/")

# sys.path.insert(1, 'geocoder-api')
# sys.path.insert(1, "/home/gisman/projects/geocoder-api")
from geocoder.Geocoder import Geocoder
from geocoder.util.HSimplifier import HSimplifier
from geocoder.util.BldSimplifier import BldSimplifier

import config

JUSO_DATA_DIR = config.JUSO_DATA_DIR


hSimplifier = HSimplifier()
bldSimplifier = BldSimplifier()


class DbCreateContext:
    def __init__(self, ldb, batch, geocoder, val, val_json, daddr):
        self.ldb = ldb
        # self.batch = batch
        self.geocoder = geocoder
        self.val = val
        self.val_json = val_json
        self.daddr = daddr


def _make_address_string(daddr, keys):
    """컬럼값을 조합하여 주소 제작"""

    alist = []
    for k in keys:
        if k in (
            "h1_nm",
            "h23_nm",
            "ld_nm",
            "ri_nm",
            "road_nm",
            "bld1",
            "bng1",
            "bld_reg",
            "bld_nm_text",
        ):
            alist.append(daddr[k])
        elif k == "h4_nm":
            h4_nm = hSimplifier.h4Hash(daddr[k], keep_dong=True)
            alist.append(h4_nm)
        elif k == "undgrnd_yn" and daddr[k] == "1":
            alist.append("지하")
        elif k == "san" and daddr[k] == "1":
            alist.append("산")
        elif (k == "bld2" or k == "bng2") and daddr[k] != "0":  # 부번지 또는 건물부번
            alist.append(alist.pop() + "-" + daddr[k])

    return " ".join(alist)


def _has_all_bld(blds0, blds):
    for bld in blds:
        if bld not in blds0:
            return False
    return True


def _has_val(val0, newval):
    for val in val0:

        if val["h1"] == newval["h1"] and val["rm"] == newval["rm"]:
            if _has_all_bld(val["bm"], newval["bm"]):
                return True

    return False


def _del_and_put(ctx, address):
    # print(address)
    hash, toksString, addressCls, errmsg = ctx.geocoder.addressHash(address)
    # print(hash)
    # if hash == '':
    #     print(errmsg)
    #     print(hash)
    #     print(addressCls)
    #     print(toksString)

    key = hash.encode()
    # print(key.decode())
    # print(key.decode())
    if key != b"":
        try:
            val = json.loads(ctx.ldb.get(key).decode())
        except:
            val = []

        if not isinstance(val, list):
            val = [val]

        if _has_val(val, ctx.val):
            pass
        else:
            val.append(ctx.val)

            ctx.ldb.delete(key)
            ctx.ldb.put(key, json.dumps(val).encode("utf8"))

        # ctx.batch.delete(key)


def _merge_address(ctx, keys):
    """주소를 만들어 hash 추가"""

    address = _make_address_string(ctx.daddr, keys)
    # print(address)
    _del_and_put(ctx, address)

    # 'ri_nm'을 제외한 key 생성
    # 충돌 가능성이 있다.
    if "ri_nm" in keys and ctx.daddr["ri_nm"]:
        tmplist = list(keys)
        tmplist.remove("ri_nm")
        address = _make_address_string(ctx.daddr, tuple(tmplist))
        # print(address)
        _del_and_put(ctx, address)


def _merge_bld_address(ctx, keys):
    """건물명을 분리하고 주소를 만들어 hash 추가

    원본 건물명에 여러 건물명이 포함된 경우가 있다.
    예)1,2,3,4,5동
    예)105동 관리사무소
    예)10동 학생회관
    """
    address = _make_address_string(ctx.daddr, keys)

    if "bld_nm" in keys:
        # 공백 또는 쉼표로 분리. TODO: 더 추가해야 함
        bld_names = re.split(r"\s|,", ctx.daddr["bld_nm"])
        for bld in bld_names:
            # print(address + ' ' + bld)
            _del_and_put(ctx, address + " " + bld)


def _bld_nm_list(bld_reg, bld_nm_text, bld_nm):
    result = []
    if bld_reg:
        result.append(bldSimplifier.simplifyBldName(bld_reg))
    if bld_nm_text and bld_nm_text not in result:
        result.append(bldSimplifier.simplifyBldName(bld_nm_text))
    if bld_nm and bld_nm not in result:
        result.append(bldSimplifier.simplifyBldName(bld_nm))
    return result


def table_to_hash(
    connection, db, sql, threadname="main", thread_count=1, current_thread=1
):
    geocoder = Geocoder(db)

    # cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor = connection.cursor(
        name=threadname, cursor_factory=psycopg2.extras.DictCursor
    )
    # cursor = connection.cursor(name='avoid_mem_leak', cursor_factory=psycopg2.extras.DictCursor)
    # cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.itersize = 100000  # Rows fetched at one time from the server
    cursor.readonly = True

    cursor.execute(sql)

    # multiple put/delete applied atomically, and committed to disk
    # batch = leveldb.WriteBatch()

    n = 0
    cnt = 0
    for record in cursor:
        if cnt % thread_count != current_thread - 1:
            cnt = cnt + 1
            continue

        daddr = dict(record)

        # 건물명 대문자 변환
        daddr["bld_reg"] = daddr["bld_reg"].upper()
        daddr["bld_nm_text"] = (
            daddr["bld_nm_text"].upper() if daddr["bld_nm_text"] else ""
        )
        daddr["bld_nm"] = daddr["bld_nm"].upper() if daddr["bld_nm"] else ""

        # ldb val 제작
        val = {
            "x": daddr["bld_x"],  # /*948429.250775*/
            "y": daddr["bld_y"],  # /*1946421.0241*/
            "z": daddr["zip"],  # /*07309*/
            "h4_cd": daddr["h4_cd"],  # /*11560*/
            "ld_cd": daddr["ld_cd"],  # /*1156013200*/
            "road_cd": daddr["road_cd"],  # /*115604154734*/
            "bn": daddr["bld_mgt_no"],  # /*1156013200103420049010058*/
            "h1_nm": hSimplifier.h1Hash(daddr["h1_nm"]),  # 광역시도명. hash 충돌시 사용
            "h23_nm": daddr["h23_nm"],
            "hd_nm": daddr["hd_nm"],
            "ld_nm": daddr["ld_nm"],
            "ri_nm": daddr["ri_nm"],
            "road_nm": daddr["road_nm"],  # 길이름. hash 충돌시 사용
            "bm": _bld_nm_list(
                daddr["bld_reg"], daddr["bld_nm_text"], daddr["bld_nm"]
            ),  # 건물명. hash 충돌시 사용
        }
        val_json = json.dumps(val).encode()
        ctx = DbCreateContext(db, None, geocoder, val, val_json, daddr)
        # 지번 주소. ("리" 제외한 hash 생성. 충돌시 "리" 검사)
        ## 법정동 번지
        _merge_address(ctx, ("h23_nm", "ld_nm", "ri_nm", "san", "bng1", "bng2"))
        ## 행정동 번지
        if daddr["h4_nm"] != None and daddr["h4_nm"] != "":
            _merge_address(ctx, ("h23_nm", "h4_nm", "ri_nm", "san", "bng1", "bng2"))

        if daddr["road_nm"] != None:  # 도로명 주소 있으면
            ## 지번주소에 건물동 추가. 새주소를 잘 찾으려면 건물동을 알아야 함.
            if daddr["bld_nm"] != "":
                ## 법정동 번지 + 건물동 (지번 알면 단지명은 몰라도 된다)
                _merge_bld_address(
                    ctx, ("h23_nm", "ld_nm", "ri_nm", "san", "bng1", "bng2", "bld_nm")
                )
                ## 행정동 번지 + 건물동 (지번 알면 단지명은 몰라도 된다)
                _merge_bld_address(
                    ctx, ("h23_nm", "h4_nm", "ri_nm", "san", "bng1", "bng2", "bld_nm")
                )

            ## 번지 없는 지번주소 건물. 시군구 + 건물명 hash 생성. (건물동 없는 단독 건물만.)
            if daddr["bld_reg"] != "" and daddr["bld_nm"] == "":
                _merge_address(ctx, ("h23_nm", "h4_nm", "ri_nm", "bld_reg"))
                _merge_address(ctx, ("h23_nm", "ld_nm", "ri_nm", "bld_reg"))
            if daddr["bld_nm_text"] != "" and daddr["bld_nm"] == "":
                _merge_address(ctx, ("h23_nm", "h4_nm", "ri_nm", "bld_nm_text"))
                _merge_address(ctx, ("h23_nm", "ld_nm", "ri_nm", "bld_nm_text"))

            ## 번지 없는 지번주소 건물. 시군구 + 건물명 hash 생성. (건물동 포함)
            if daddr["bld_reg"] != "" and daddr["bld_nm"] != "":
                _merge_bld_address(
                    ctx, ("h23_nm", "h4_nm", "ri_nm", "bld_reg", "bld_nm")
                )
                _merge_bld_address(
                    ctx, ("h23_nm", "ld_nm", "ri_nm", "bld_reg", "bld_nm")
                )
            if daddr["bld_nm_text"] != "" and daddr["bld_nm"] != "":
                _merge_bld_address(
                    ctx, ("h23_nm", "h4_nm", "ri_nm", "bld_nm_text", "bld_nm")
                )
                _merge_bld_address(
                    ctx, ("h23_nm", "ld_nm", "ri_nm", "bld_nm_text", "bld_nm")
                )

        # 도로명 주소
        # 길이름 건물번호 (집합건물 아님)
        if daddr["road_nm"] != None:  # 도로명 주소
            if daddr["road_nm"] != "":
                _merge_address(ctx, ("h23_nm", "road_nm", "undgrnd_yn", "bld1", "bld2"))

            # 길이름 건물번호 건물명 건물동명
            if daddr["bld_reg"] != "":
                _merge_bld_address(
                    ctx,
                    (
                        "h23_nm",
                        "road_nm",
                        "undgrnd_yn",
                        "bld1",
                        "bld2",
                        "bld_reg",
                        "bld_nm",
                    ),
                )
            if daddr["bld_nm_text"] != "":
                # 길이름 건물번호 건물
                _merge_bld_address(
                    ctx,
                    (
                        "h23_nm",
                        "road_nm",
                        "undgrnd_yn",
                        "bld1",
                        "bld2",
                        "bld_nm_text",
                        "bld_nm",
                    ),
                )

        n = n + 1
        cnt = cnt + 1
        if n >= 10000:
            print(f"{threadname} {cnt:,}")
            # ldb.Write(batch, sync = True)
            # batch = leveldb.WriteBatch()
            n = 0

    if n > 0:
        print(f"{threadname} {cnt}")
        # ldb.Write(batch, sync = True)

    cursor.close()


def buildFull(connection, ldb):
    sql = """
        select 
            a.h1_nm,	a.h23_nm,	a.ld_nm,	a.h4_nm,	a.ri_nm,	a.road_nm
        ,	a.undgrnd_yn,	cast(a.bld1 as text),	cast(a.bld2 as text)
        ,	a.san,	cast(a.bng1 as text),	cast(a.bng2 as text)
        ,	a.bld_reg,	a.bld_nm_text, a.bld_nm
        ,	a.ld_cd,	a.h4_cd,	a.road_cd,	a.zip,	a.bld_mgt_no
        ,	a.bld_x,	a.bld_y
        from geocode.tbaddress a
    """
    THREAD1_COUNT = 4
    t1 = []
    for n in range(1, THREAD1_COUNT + 1):
        t1.append(
            threading.Thread(
                target=table_to_hash,
                args=(connection, ldb, sql, f"t1-{n}", THREAD1_COUNT, n),
            )
        )

    # table_to_hash(connection, ldb, sql)

    # 지적도 (새주소 없는 지번)
    # san 코드가 다르다.
    # 건물DB 산여부 0:대지, 1:산
    # 지적도 산여부 1:대지, 2:산, ...
    sql = """
        select 
            a.h1_nm,	a.h23_nm,	a.ld_nm,	a.h4_nm,	COALESCE(a.ri_nm, '') as ri_nm,	a.road_nm
        ,	a.undgrnd_yn,	cast(a.bld1 as text),	cast(a.bld2 as text)
        ,	case when a.san = '1' then '0'
                when a.san = '2' then '1'
                else '0' end as san
        ,	cast(a.bng1 as text),	cast(a.bng2 as text)
        ,	COALESCE(a.bld_reg, '') as bld_reg,	COALESCE(a.bld_nm_text, '') as bld_nm_text, COALESCE(a.bld_nm, '') as bld_nm
        ,	a.ld_cd,	a.h4_cd,	a.road_cd,	a.zip,	a.bld_mgt_no
        ,	a.bld_x,	a.bld_y
        from geocode.tbaddress_no_road a
        where a.h1_nm is not null
            and a.h23_nm is not null
    """
    t2 = threading.Thread(target=table_to_hash, args=(connection, ldb, sql, "t2"))

    for t in t1:
        t.start()
    t2.start()

    # t1.join()
    # thrad join
    for t in t1:
        t.join()

    t2.join()


def buildUpdated(connection, ldb, yyyymm):
    # truncate
    cur = connection.cursor()

    cur.execute(f"delete from geocode.tbaddress_updated where yyyymm='{yyyymm}';")
    cur.execute("truncate table geocode.tbjibun_load;")
    cur.execute("truncate table geocode.tbbld_info_load;")
    cur.execute("truncate table geocode.tbnavi_match_bld_load;")
    connection.commit()
    cur.close()

    INST_DIR = f"{JUSO_DATA_DIR}/월변동분"

    # load
    cur = connection.cursor()
    # cur.execute(f"COPY geocode.tbnavi_match_bld_load FROM '{INST_DIR}/NAVI/{yyyymm}/match_build_mod.txt' WITH DELIMITER '|' ENCODING 'WIN949';")

    os.system(
        f"""export PGPASSWORD=xhddlfd0 && psql -h dev.gimi9.com -d geocode -U gisman -c "\copy geocode.tbjibun_load from '{INST_DIR}/ADDR/{yyyymm}/지번_변동분.txt' WITH DELIMITER '|' ENCODING 'WIN949';" """
    )
    os.system(
        f"""export PGPASSWORD=xhddlfd0 && psql -h dev.gimi9.com -d geocode -U gisman -c "\copy geocode.tbnavi_match_bld_load from '{INST_DIR}/NAVI/{yyyymm}/match_build_mod.txt' WITH DELIMITER '|' ENCODING 'WIN949';" """
    )
    # cur.execute(f"COPY geocode.tbbld_info_load FROM '{INST_DIR}/BLD/{yyyymm}/build_mod.txt' WITH DELIMITER '|' encoding 'WIN949';")
    os.system(
        f"""export PGPASSWORD=xhddlfd0 && psql -h dev.gimi9.com -d geocode -U gisman -c "\copy geocode.tbbld_info_load FROM '{INST_DIR}/BLD/{yyyymm}/build_mod.txt' WITH DELIMITER '|' encoding 'WIN949';" """
    )
    connection.commit()
    cur.close()

    cur = connection.cursor()
    cur.execute(
        f"""insert into geocode.tbaddress_updated(
        yyyymm, h1_nm, h23_nm, ld_nm, h4_nm, ri_nm,
        road_nm, undgrnd_yn, bld1, bld2,
        san, bng1, bng2,
        bld_reg, bld_nm, 
        ld_cd, h4_cd, road_cd, zip, bld_mgt_no,
        bld_x, bld_y)
    select '{yyyymm}' as yyyymm, b.h1_nm, b.h23_nm, b.ld_nm, b.h4_nm, a.ri_nm
        , b.road_nm, b.undgrnd_yn, b.bld1, b.bld2
        , a.san, a.bng1, a.bng2 
        , a.bld_nm_text, a.bld_nm 
        , a.ld_cd, a.h4_cd, b.road_cd, a.zip, a.bld_mgt_no 
        , b.bld_x::numeric::integer, b.bld_y::numeric::integer
    from geocode.tbbld_info_load  a
    ,	geocode.tbnavi_match_bld_load b
    where 1=1
        and a.bld_mgt_no = b.bld_mgt_no
        and a.mvmn_resn_cd = '63'
        and b.bld_x <> ''"""
    )
    connection.commit()
    cur.close()

    # jibun 추가
    cur = connection.cursor()
    cur.execute(
        f"""insert into geocode.tbaddress_updated(
            yyyymm, h1_nm, h23_nm, ld_nm, h4_nm, ri_nm,
            road_nm, undgrnd_yn, bld1, bld2,
            san, bng1, bng2,
            bld_reg, bld_nm, 
            ld_cd, h4_cd, road_cd, zip, bld_mgt_no,
            bld_x, bld_y)
    select '{yyyymm}', j.h1_nm, j.h23_nm, j.ld_nm, b.h4_nm, j.ri_nm,
        b.road_nm, b.undgrnd_yn, b.bld1, b.bld2,
        j.san, j.bng1, j.bng2,
        b.bld_nm_text, b.bld_nm,
        j.ld_cd, b.h4_cd, b.road_cd, b.zip, j.mgt_sn,
        b.bld_x::numeric::integer, b.bld_y::numeric::integer
    from geocode.tbjibun_load j
        , geocode.tbnavi_match_bld_load b
    where j.mgt_sn = b.bld_mgt_no
        and b.bld_x != ''
        and not exists (select bld_mgt_no from geocode.tbaddress_updated 
            where h23_nm = j.h23_nm 
            and ld_nm = j.ld_nm 
            and san = j.san
            and bng1 = j.bng1
            and bng2 =j.bng2
        )"""
    )
    connection.commit()
    cur.close()

    # 관련지번 미구현: 일일 업데이트에서는 구현함.

    # update leveldb
    sql = f"""
        select 
            a.h1_nm,	a.h23_nm,	a.ld_nm,	a.h4_nm,	a.ri_nm,	a.road_nm
        ,	a.undgrnd_yn,	cast(a.bld1 as text),	cast(a.bld2 as text)
        ,	a.san,	cast(a.bng1 as text),	cast(a.bng2 as text)
        ,	COALESCE(a.bld_reg, '') as bld_reg,	COALESCE(a.bld_nm_text, '') as bld_nm_text, COALESCE(a.bld_nm, '') as bld_nm
        ,	a.ld_cd,	a.h4_cd,	a.road_cd,	a.zip,	a.bld_mgt_no
        ,	a.bld_x,	a.bld_y
        from geocode.tbaddress_updated a
        where yyyymm = '{yyyymm}'
    """
    t1 = threading.Thread(
        target=table_to_hash,
        args=(
            connection,
            ldb,
            sql,
            "t1",
        ),
    )
    t1.start()
    t1.join()


# rocksdb version
if __name__ == "__main__":
    params = sys.argv[1:]

    # 전체 데이터 빌드
    LEVELDB_NAME = config.GEOCODE_DB
    # LEVELDB_NAME = "/home/gisman/projects/geocoder-api/db/rocks"
    ldb = rocksdb3.open_default(LEVELDB_NAME)
    val = ldb.get("TEST_KEY".encode())

    # ldb.put("TEST_KEY".encode(), "TEST_VALUE_CHANGED".encode())
    # ldb.put("TEST_KEY2".encode(), "TEST_VALUE_2".encode())
    # del ldb

    # Download

    # try:
    connection = psycopg2.connect(
        user="gisman",
        password="xhddlfd0",
        host="dev.gimi9.com",
        # host="localhost",
        port="5432",
        database="geocode",
    )

    if len(params) == 0:
        buildFull(connection, ldb)
    else:
        yyyymm = params[0]
        buildUpdated(connection, ldb, yyyymm)

    # flush cache buffer
    del ldb


# # leveldb version
# if __name__ == "__main__":
#     params = sys.argv[1:]

#     # 전체 데이터 빌드
#     LEVELDB_NAME = "/home/gisman/projects/geocoder-api/db/current"
#     # LEVELDB_NAME = '/home/gisman/projects/geocoder-api/db/db_20211114'
#     ldb = leveldb.LevelDB(LEVELDB_NAME, create_if_missing=True)

#     # try:
#     connection = psycopg2.connect(
#         user="gisman",
#         password="xhddlfd0",
#         host="dev.gimi9.com",
#         # host="localhost",
#         port="5432",
#         database="geocode",
#     )

#     if len(params) == 0:
#         buildFull(connection, ldb)
#     else:
#         yyyymm = params[0]
#         buildUpdated(connection, ldb, yyyymm)

#     # flush cache buffer
#     del ldb
#     ldb = leveldb.LevelDB(LEVELDB_NAME, create_if_missing=True)
#     del ldb

-- 도로명 주소 아닌 지번 로드
-- 33,382,118건
truncate table geocode.tbaddress_no_road;

insert into geocode.tbaddress_no_road ( san
								, bng1
								, bng2
								, ld_cd
								, bld_x
								, bld_y)
select 
    case when san = '1' then '0'
        when san = '2' then '1'
        else '0' end as san
    , bng1
    , bng2
    , ld_cd
    , st_x(	ST_Transform(center, 5179)	) as bld_x
    , st_y( ST_Transform(center, 5179)  ) as bld_y
from (
    select substring(a.pnu, 11, 1) as san
        , substring(a.pnu, 12, 4)::int as bng1
        , substring(a.pnu, 16, 4)::int as bng2
        , left(a.pnu, 10) as ld_cd
        , ST_SetSRID(ST_PointOnSurface(geom), 95174)  center
    from geocode.tblsmd_cont_ldreg a
    left outer join geocode.tmp_road_pnu b on (a.pnu = b.pnu)
    where b.pnu is null
        and a.pnu ~ '^\d{19}$'
    limit 100
) x
;


truncate table geocode.tbadmi_ldong;

insert into geocode.tbadmi_ldong
select ld_cd
, split_part(full_nm, ' ', 1) 
, split_part(full_nm, ' ', 2) 
, split_part(full_nm, ' ', 3) 
, split_part(full_nm, ' ', 4) 
from geocode.tbadmi_ldong_load
where ld_status = '존재'
;

update geocode.tbaddress_no_road as a
set h1_nm = b.h1_nm
, h23_nm = b.h23_nm
, ld_nm = b.ld_nm
, ri_nm = b.ri_nm
from geocode.tbadmi_ldong b
where a.ld_cd = b.ld_cd
;


-- 행정동 업데이트
update geocode.tbaddress_no_road as a
set h4_nm = b.h4_nm
, h4_cd = b.h4_cd
from geocode.tbadmi_dong b
where ST_Contains(geom, 
	ST_Transform(
		ST_GeomFromText(concat('POINT(', a.bld_x, ' ', a.bld_y, ')'), 5179)
	, 4326)
	
)
;

-- zip 업데이트
update geocode.tbaddress_no_road as a
set zip = b.bas_id 
from geocode.tbzip_area b
where ST_Contains(geom, 
	    ST_GeomFromText(concat('POINT(', a.bld_x, ' ', a.bld_y, ')'), 5179)
)
;

-- select * 
-- from geocode.tbaddress_no_road as a
-- where 1=1
-- and a.ld_cd = '4180033025'

-- select a.pnu, 	ST_Transform(
-- 		geom, '+proj=tmerc +lat_0=38 +lon_0=127 +k=1 +x_0=200000 +y_0=500000 +ellps=bessel +units=m +no_defs +towgs84=-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43'
-- 	, 4326)
-- from geocode.tblsmd_cont_ldreg a
-- where a.pnu = '1111016100100320008'

-- select a.pnu, 	geom
-- from geocode.tblsmd_cont_ldreg a
-- where a.pnu = '1111016100100320008'

-- where st_area(geom) < 100


-- +proj=tmerc +lat_0=38 +lon_0=127 +k=1 +x_0=200000 +y_0=500000 +ellps=bessel +units=m +no_defs +towgs84=-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43
-- +proj=tmerc +lat_0=38 +lon_0=127.0028902777778 +k=1 +x_0=200000 +y_0=500000 +ellps=bessel +units=m +no_defs +towgs84=-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43


-- select *
-- from geocode.tbaddress a
-- where a.h23_nm like '안양시%'
-- ;

-- select * 
-- from geocode.tbaddress_no_road as a
-- where ld_cd = '4117110100'

-- update geocode.tbaddress_no_road as a
-- set h23_nm = concat(h23_nm, ' ', ld_nm)
-- , ld_nm = ri_nm 
-- , ri_nm = null
-- where ri_nm like '%동'
-- ;

-- select count(1)
-- from geocode.tbaddress_no_road as a
-- where h4_cd is null


-- select *
-- from geocode.tbaddress_no_road as a
-- where h23_nm = '안산시 상록구'


-- select *
-- from geocode.tbaddress_no_road as a
-- where --h23_nm is null or 
-- ld_nm is null or 
-- --h4_nm is null or 
-- --ri_nm is null or 
-- san is null or 
-- bng1 is null or 
-- bng2 is null 





-- select san
-- , bng1
-- , bng2
-- , ld_cd
-- , st_x(center) as bld_x
-- , st_y(center) as bld_y
-- from (

-- select substring(a.pnu, 11, 1) as san
-- 	, substring(a.pnu, 12, 4)::int as bng1
-- 	, substring(a.pnu, 16, 4)::int as bng2
-- 	, left(a.pnu, 10) as ld_cd
-- 	, ST_Transform(
-- 		ST_PointOnSurface(a.geom), 5179
-- 		) center
-- 	from geocode.tblsmd_cont_ldreg a
-- 	left outer join geocode.tmp_road_pnu b on (a.pnu = b.pnu)
-- 	where b.pnu is null
-- 	and a.pnu ~ '^\d{19}$'

	
-- select bld_x, bld_y
-- , 	st_x(
-- 		ST_Transform(
-- 			ST_GeomFromText(concat('POINT(', a.bld_x, ' ', a.bld_y, ')'), 95174)
-- 		, 5179)
-- 	)
-- , 	st_y(
-- 		ST_Transform(
-- 			ST_GeomFromText(concat('POINT(', a.bld_x, ' ', a.bld_y, ')'), 95174)
-- 		, 5179)
-- 	)
-- from geocode.tbaddress_no_road a

-- update geocode.tbaddress_no_road a
-- set 
-- bld_x = st_x(
-- 		ST_Transform(
-- 			ST_GeomFromText(concat('POINT(', a.bld_x, ' ', a.bld_y, ')'), 95174)
-- 		, 5179)
-- 	),
-- bld_y = st_y(
-- 		ST_Transform(
-- 			ST_GeomFromText(concat('POINT(', a.bld_x, ' ', a.bld_y, ')'), 95174)
-- 		, 5179)
-- 	)
-- ;


-- select 
--     a.h1_nm,	a.h23_nm,	a.ld_nm,	a.h4_nm,	COALESCE(a.ri_nm, '') as ri_nm,	a.road_nm
-- ,	a.undgrnd_yn,	cast(a.bld1 as text),	cast(a.bld2 as text)
-- ,	case when a.san = '1' then '0'
-- 		 when a.san = '2' then '1'
-- 		 else '0' end as san
-- ,	cast(a.bng1 as text),	cast(a.bng2 as text)
-- ,	COALESCE(a.bld_reg, '') as bld_reg,	COALESCE(a.bld_nm_text, '') as bld_nm_text, COALESCE(a.bld_nm, '') as bld_nm
-- ,	a.ld_cd,	a.h4_cd,	a.road_cd,	a.zip,	a.bld_mgt_no
-- ,	a.bld_x,	a.bld_y
-- from geocode.tbaddress_no_road a
-- where a.h1_nm is not null
--     and a.h23_nm is not null

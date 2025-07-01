select * 
from geocode.tbaddress
where h1_nm = '서울특별시'
and h23_nm = '마포구'
and ld_nm = '상수동'
and bng1 = '353'

and bng2 = '5'

select * 
--select count(1)
from geocode.tbrel_jibun_info_load
where h1_nm = '서울특별시'
and h23_nm = '마포구'
and ld_nm = '상수동'
and bng1 = 353
and bng2 = 5

select * 
from geocode.tbaddress a
, geocode.tbrel_jibun_info_load b
where b.road_cd = a.road_cd
and b.undgrnd_yn = a.undgrnd_yn 
and b.bld1 = cast(a.bld1 as integer)
and b.bld2 = cast(a.bld2 as integer) 

select * 
from geocode.tbrel_jibun_info_load a
where a.road_cd ='114404139580'
and a.undgrnd_yn =  '0'
and a.bld1 = 39
and a.bld2 = 0

and and a.bng1 = '353'



under


select * 
select count(1)
from geocode.tbaddress

create table geocode.tbaddress
as
    select b.h1_nm, b.h23_nm, b.ld_nm, b.h4_nm, a.ri_nm
        , b.road_nm, b.undgrnd_yn, cast(b.bld1 as text), cast(b.bld2 as text)
        , a.san, cast(a.bng1 as text), cast(a.bng2 as text) 
        , a.bld_reg, a.bld_nm 
        , a.ld_cd, a.h4_cd, b.road_cd, a.zip, a.bld_mgt_no 
        , b.bld_x, b.bld_y
    from geocode.tbbld_info_load  a
    ,	geocode.tbnavi_match_bld_load b
    where 1=1
        and a.bld_mgt_no = b.bld_mgt_no

        
        
select j.h1_nm||'_'||j.h23_nm||'_'||j.ld_nm||'_'
||case when j.ri_nm = '' then '' else j.ri_nm||'_' end
||case when j.san='1' then '산' else '' end
||j.bng1||'-'||j.bng2 as key
, j.ld_nm as l --신길동
, p.h4_nm as h --영등포본동
, p.ent_x as x --948429.250775
, p.ent_y as y --1946421.0241
, p.bld_nm as b --
, p.zip as z --07309
, p.h23_cd as hc--11560
, p.ld_cd as lc --1156013200
, p.road_cd as rc --115604154734
from geocode.tbjibun_load j
, geocode.tbjuso_load r
, geocode.tbentrc_load p
where 1=1
and j.mgt_sn = r.mgt_sn
and r.road_cd = p.road_cd
and r.undgrnd_yn = p.undgrnd_yn
and r.bld1 = p.bld1
and r.bld2 = p.bld2
and j.ld_cd = '1156013200'
;

select *
from geocode.tbjibun_load j
;

select *
from geocode.tbjuso_load r
;

select h1_nm||'_'||h23_nm||'_'||road_nm||'_'||bld1||'-'||bld2 as key
, ld_nm as l --신길동
, h4_nm as h --영등포본동
, ent_x as x --948429.250775
, ent_y as y --1946421.0241
, bld_nm as b --
, zip as z --07309
, h23_cd as hc--11560
, ld_cd as lc --1156013200
, road_cd as rc --115604154734
from geocode.tbentrc_load tl 
where ld_cd = '1156013200'
;

select count(1) 
from geocode.tbentrc_load tl 


select *
from geocode.tbentrc_load tl 
where ld_cd = '1156013200'
and road_nm = '영등포로62가길'
and bld1 = 4
and bld2 = 4

{
    "h1_nm" : "서울특별시",
    "h23_nm" : "영등포구",
    "ld_nm" : "신길동",
    "h4_nm" : "영등포본동",
    "road_nm" : "영등포로62가길",
    "bld1" : 4,
    "bld2" : 4,
    "ent_x" : "948429.250775",
    "ent_y" : "1946421.02419"
    "bld_nm" : "",
    "zip" : "07309",
    "h23_cd" : "11560",
    "ld_cd" : "1156013200",
    "road_cd" : "115604154734",
    "ent_seq" : "33301",
    "undgrnd_yn" : "0",
    "bld_clss_list" : "주택",
    "bld_group_yn" : "0",
}

select h1_nm||'_'||h23_nm||'_'||road_nm||'_'||bld1||'-'||bld2 as key
, ld_nm as l --신길동
, h4_nm as h --영등포본동
, ent_x as x --948429.250775
, ent_y as y --1946421.0241
, bld_nm as b --
, zip as z --07309
, h23_cd as hc--11560
, ld_cd as lc --1156013200
, road_cd as rc --115604154734
from geocode.tbentrc_load tl 
where ld_cd = '1156013200'
and road_nm = '영등포로62가길'
and bld1 = 4
and bld2 = 4
;

select h1_nm||'_'||h23_nm||'_'||road_nm||'_'||bld1||'-'||bld2 as key
, ld_nm as l --신길동
, h4_nm as h --영등포본동
, ent_x as x --948429.250775
, ent_y as y --1946421.0241
, bld_nm as b --
, zip as z --07309
, h23_cd as hc--11560
, ld_cd as lc --1156013200
, road_cd as rc --115604154734
from geocode.tbentrc_load tl 
where ld_cd = '1156013200'
;



select distinct h1_nm
from geocode.tbentrc_load tl 
order by 1


where ld_cd = '1156013200'

select * 
from geocode.tbnavi_match_bld_load
where bld_mgt_no = '1156013200100480005015140'
--where road_nm = '영등포로62가길'
;


select * 
from geocode.tbbld_info_load
where bld_mgt_no = '1156013200100480005015140'
;

1156013200	서울특별시	영등포구	신길동	115604154734	영등포로62가길	0	4	4	07309	1156013200100480005015140		주택	1156051500	영등포본동	5	0	0	1				1	948430.168167	1946417.88275	948429.250775	1946421.02419	Seoul	Yeongdeungpo-gu	Singil-dong	Yeongdeungpo-ro 62ga-gil	1	
1156013200	서울특별시	영등포구	신길동		0	48	5	115604154734	영등포로62가길	0	4	4			1156013200100480005015140	01	1156051500	영등포본동	07309							0	07309	0		

select count(1)
from geocode.tbnavi_match_bld_load
;

10,735,779

select count(1)
from geocode.tbbld_info_load
;

10,680,507


select a.*
from geocode.tbnavi_match_bld_load a
left outer join geocode.tbbld_info_load b 
	on a.bld_mgt_no = b.bld_mgt_no
where b.bld_mgt_no is null
;

select b.*
from geocode.tbbld_info_load b
left outer join geocode.tbnavi_match_bld_load a 
	on a.bld_mgt_no = b.bld_mgt_no
where a.bld_mgt_no is null
;



select *
from geocode.tbjibun_load tl 
where mgt_seq > 1

4127310200108090008014515	1	4127310200	경기도	안산시 단원구	와동		0	809	8	1

select count(1)
from geocode.tbjibun_load tl 

8,251,319

select * 
from tbnavi_match_jibun_load

2611011000	부산광역시	중구	중앙동7가		0	20	1	261102000010	0	2	0	0	Busan	Jung-gu	Jungang-dong 7(chil)-ga			2611011000100200001000001	2611011000

select count(1)
from tbnavi_match_jibun_load

8,251,399


select * 
from tbnavi_match_rs_entrc_load
where ent_seq = 28695
order by h23_cd, ent_seq 

select ent_seq, count(1) 
from tbnavi_match_rs_entrc_load
group by ent_seq
having count(1) > 1  
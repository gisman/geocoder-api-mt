# name hash

## h1

강원도: 강원
경기도: 경기
경상남도:   경남
경상북도:   경북
광주광역시: 광주
대구광역시: 대구
대전광역시: 대전
부산광역시: 부산
서울특별시: 서울
세종특별자치시: 세종
울산광역시: 울산
인천광역시: 인천
전라남도:   전남
전라북도:   전북
제주특별자치도: 제주
충청남도:   충남
충청북도:   충북

## h2 h3

고양시 덕양구, 일산동구, 일산서구
성남시 분당구, 수정구, 중원구
수원시 권선구, 영통구, 장안구, 팔달구
안산시 단원구, 상록구
안양시 동안구, 만안구
용인시 기흥구, 수지구, 처인구
전주시 덕진구, 완산구
창원시 마산합포구, 마산회원구, 성산구, 의창구, 진해구
천안시 동남구, 서북구
청주시 상당구, 서원구, 청원구, 흥덕구
포항시 남구, 북구

# 다 합쳐서 한 방에.

새주소, 지번주소, 건물명주소를 python에서 아래 데이터로 조합
```sql
create table geocode.tbaddress
as
    select b.h1_nm, b.h23_nm, b.ld_nm, b.h4_nm, a.ri_nm
        , b.road_nm, b.undgrnd_yn, b.bld1, b.bld2
        , a.san, a.bng1, a.bng2 
        , a.bld_reg, a.bld_nm 
        , a.ld_cd, a.h4_cd, b.road_cd, a.zip, a.bld_mgt_no 
        , b.bld_x, b.bld_y
    from geocode.tbbld_info_load  a
    ,	geocode.tbnavi_match_bld_load b
    where 1=1
        and a.bld_mgt_no = b.bld_mgt_no
```

# 관련 지번 추가


<!-- # 새주소

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

{
    "key" : "서울특별시_영등포구_영등포로62가길_4-4",
    "l" : "신길동",
    "h" : "영등포본동",
    "x" : "948429.250775",
    "y" : "1946421.02419",
    "b" : "",
    "z" : "07309",
    "hc" : "11560",
    "lc" : "1156013200",
    "rc" : "115604154734"
}

# 지번주소

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

{
    "key" : "서울특별시_영등포구_신길동_186-349",
    "l" : "신길동",
    "h" : "영등포본동",
    "x" : "948176.119338",
    "y" : "1946024.787282",
    "b" : "",
    "z" : "07315",
    "hc" : "11560",
    "lc" : "1156013200",
    "rc" : "115604154338"
}

# 건물명주소
 -->


# 지적도에서 지번 추출

지적도 39,145,869건

```sql
-- INSERT INTO geocode.tbaddress
-- (h1_nm, h23_nm, ld_nm, h4_nm, ri_nm, road_nm, undgrnd_yn, bld1, bld2, san, bng1, bng2, bld_reg, bld_nm, ld_cd, h4_cd, road_cd, zip, bld_mgt_no, bld_x, bld_y)
```


# 건물명 단순화

select bld_reg 
from (
	select distinct bld_reg
	from geocode.tbbld_nm
	where true
	and bld_reg not like '%다세대주택'
	and bld_reg not like '%연립주택'
	and bld_reg not like '%빌라'
	and bld_reg not like '%아파트'
	and bld_reg not similar to '%([가-하]|[A-G]|[a-g]|에이|비|비이|씨|씨이|디|디이|\d+)동'
	and bld_reg not similar to '%([A-G]|[a-g]|에이|비|비이|씨|씨이|디|디이|\d+)지구'
	and bld_reg not like '%주택'
	and bld_reg not like '%홈타운'
	and bld_reg not like '%맨션'
	and bld_reg not like '%타운'
	and bld_reg not like '%연립'
	and bld_reg not like '%공동주택'
	and bld_reg not like '%하우스'
	and bld_reg not like '%하우징'
	and bld_reg not like '%빌리지'
	and bld_reg not like '%빌'
	and bld_reg not similar to '%원룸(텔)?'
	and bld_reg not like '%다세대'
	and bld_reg not like '%하이츠'
	and bld_reg not like '%빌라트'
	and bld_reg not like '%빌라텔'
	and bld_reg not like '%빌리지'
	and bld_reg not like '%팰리스'
	and bld_reg not like '%펠리스'
	and bld_reg not like '%마을'
	and bld_reg not like '%캐슬'
	and bld_reg not like '%파크'
	and bld_reg not like '%빌딩'
	and bld_reg not like '%오피스텔'
	and bld_reg not similar to '%\d차'
	and bld_reg not similar to '%(일|이|삼|사|오|Ⅰ|Ⅱ|Ⅳ|)차'
	and bld_reg not similar to '%\d+'
	and bld_reg not similar to '%\)'
	and bld_reg not similar to '%(A|B|C|에이|비)'
	and bld_reg not like '%I'
	and bld_reg not like '%II'
	and bld_reg not like '%Ⅰ'
	and bld_reg not like '%Ⅱ'
	and bld_reg not like '%PARK'
	and bld_reg not like '%HILL'
	and bld_reg not like '%VILL'
	and bld_reg not like '%VILLE'
	and bld_reg not like '%단지'
	and bld_reg not like '%APT'
	and bld_reg not like '%A.P.T'
	and bld_reg not like '%家'
	and bld_reg not like '%주상복합'
	and bld_reg not like '%카운티'
	and bld_reg not like '%시티'
	and bld_reg not like '%씨티'
	and bld_reg not similar to '%(힐)?스테이트'
	and bld_reg not like '%스위트'
	and bld_reg not like '%아트'
	and bld_reg not like '%리빙텔'
	and bld_reg not like '%타워'
	and bld_reg not similar to '%(벨|팰|펠)리체'
	and bld_reg not like '%하임'
	and bld_reg not like '%프라임'
	and bld_reg not similar to '%(빌라)?(맨|멘)(숀|션)'
	and bld_reg not similar to '%(펜|팬)(숀|션)'
	and bld_reg not like '%신축공사'
	and bld_reg not similar to '%(\d|[A-Z])(부|블)(럭|록)'
	) a	
order by reverse(bld_reg)
;

A
apt
@
(...)
A.P.T
대소문자 통일
..신도시 prefix
5블럭
& 	송도 캐슬&해모로	H&H
긴 이름:	서초 교대 e편한세상
에이 suffix
별칭: 더-편한, The편한
별칭: e편한세상 e-편한세상 이편한세상  이-편한세상
별칭: 자이 xi
별칭: 래미안	레미안
별칭: 레지던스 레지던트

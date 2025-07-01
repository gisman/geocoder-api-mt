#!/bin/bash

# 첫 번째 파라미터를 yyyymm 변수에 저장
yyyymm=$1

curl "http://localhost:4029/update_navi?name=match_build_busan.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_chungbuk.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_chungnam.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_daegu.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_daejeon.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_gangwon.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_gwangju.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_gyeongbuk.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_gyeongnam.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_gyunggi.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_incheon.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_jeju.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_jeonbuk.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_jeonnam.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_sejong.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_seoul.txt&yyyymm=$yyyymm"
curl "http://localhost:4029/update_navi?name=match_build_ulsan.txt&yyyymm=$yyyymm"

echo "Finished: $yyyymm"

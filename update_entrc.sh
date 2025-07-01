#!/bin/bash

# 첫 번째 파라미터를 yyyymm 변수에 저장
yyyymm=$1

curl "http://localhost:4009/update_entrc?name=entrc_busan.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_chungbuk.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_chungnam.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_daegu.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_daejeon.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_gangwon.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_gwangju.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_gyeongbuk.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_gyeongnam.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_gyunggi.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_incheon.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_jeju.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_jeonbuk.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_jeonnam.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_sejong.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_seoul.txt&yyyymm=$yyyymm"
curl "http://localhost:4009/update_entrc?name=entrc_ulsan.txt&yyyymm=$yyyymm"

echo "All Done $yyyymm"
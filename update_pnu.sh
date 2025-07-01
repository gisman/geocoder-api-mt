#!/bin/bash

# 첫 번째 파라미터를 yyyymm 변수에 저장
yyyymm=$1

for f in $(ls /disk/hdd-lv/juso-data/연속지적/$yyyymm/shp2/*.shp | grep -v '([0-9]\+)'); do
  curl "http://localhost:4029/update_jibun_in_pnu?file=$(basename $f)&yyyymm=$yyyymm" &
done

wait

echo "Finished: $yyyymm"

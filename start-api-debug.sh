#!/bin/bash

# Geocoder api (stand-alone http server. single process)
git pull

lsof -ti:4019 | xargs kill -9

cd ~/projects/geocoder-api-mt
source venv/bin/activate
echo 'Starting...'

export PYTHON_GIL=0
export READONLY=true
export GEOCODE_DB=/disk/nvme1t/geocoder-api-db/rocks
export REVERSE_GEOCODE_DB=/disk/nvme1t/geocoder-api-db/rocks-reverse-geocoder
export HD_HISTORY_DB=/disk/nvme1t/geocoder-api-db/rocks_hd_history-debug
export BIGCACHE_DB=/disk/nvme1t/geocoder-api-db/bigcache
export CODE_DATA_DIR=/disk/nvme1t/geocoder-api-db/code
export LOG_LEVEL=INFO
export FULL_HISTORY_LIST=true
export USE_HASH_CACHE=true
export THREAD_POOL_SIZE=8

uvicorn api_fast:app --host=0.0.0.0 --port=4019 &

sleep 3
echo 'Started'

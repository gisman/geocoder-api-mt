#!/bin/bash

# Geocoder api (stand-alone http server. single process)
git pull

lsof -ti:4009 | xargs kill -9

cd ~/projects/geocoder-api-mt
source venv/bin/activate
echo 'Starting...'

export PYTHON_GIL=0
export CODE_DATA_DIR=/disk/nvme1t/geocoder-api-db/code
export GEOCODE_DB=/disk/nvme1t/geocoder-api-db/rocks-debug
export REVERSE_GEOCODE_DB=/disk/nvme1t/geocoder-api-db/rocks-reverse-geocoder-debug
export HD_HISTORY_DB=/disk/nvme1t/geocoder-api-db/rocks_hd_history-debug
export BIGCACHE_DB=/disk/nvme1t/geocoder-api-db/bigcache-debug
export LOG_LEVEL=INFO
export USE_HASH_CACHE=true
export THREAD_POOL_SIZE=8

uvicorn api_fast:app --host=0.0.0.0 --port=4009 &

sleep 3
echo 'Started'


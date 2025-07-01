#!/bin/bash

# Geocoder api (stand-alone http server. single process)
git pull

lsof -ti:4029 | xargs kill -9

cd ~/study/geocoder-api-gilfree
source venv/bin/activate
echo 'Starting...'

export PYTHON_GIL=0

export CODE_DATA_DIR=/disk/nvme1t/geocoder-api-db/code
export GEOCODE_DB=/disk/nvme1t/geocoder-api-db/rocks_debug_mt
export REVERSE_GEOCODE_DB=/disk/nvme1t/geocoder-api-db/rocks-reverse-geocoder_debug_mt
export HD_HISTORY_DB=/disk/nvme1t/geocoder-api-db/rocks_hd_history_debug_mt
export LOG_LEVEL=INFO
export USE_HASH_CACHE=true

uvicorn api_fast:app --host=0.0.0.0 --port=4029 &

sleep 3
echo 'Started'


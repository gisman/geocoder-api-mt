#!/bin/bash

# Geocoder api (stand-alone http server. single process)
git pull

lsof -ti:4001 | xargs kill -9

cd ~/projects/geocoder-api
source venv/bin/activate
echo 'Starting...'

# export FLASK_ENV=production
# echo | nohup python src/api_pro.py >> log/geocode-api.log &
uvicorn api_fast:app --host=0.0.0.0 --port=4001 &

sleep 3
echo 'Started'


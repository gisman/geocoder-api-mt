1. DbCreator.py 를 수정

{NEW_DB_DIR}을 정하고, 

```python
LEVELDB_NAME = '/home/gisman/projects/geocoder-api/db/db_20210505' # 을

LEVELDB_NAME = '/home/gisman/projects/geocoder-api/db/{NEW_DB_DIR}' # 으로

```

2. bash

```bash
cd /home/gisman/projects/geocoder-api/
nice -n 19 python geocoder-api/util/DbCreator.py 
nice -n 19 python geocoder-api/util/DbCreator.py 201711 
```

cd /home/gisman/projects/geocoder-api/
source bin/activate
nice -n 19 python geocoder-api/util/DbCreator.py 202103
nice -n 19 python geocoder-api/util/DbCreator.py 202104
nice -n 19 python geocoder-api/util/DbCreator.py 202105
nice -n 19 python geocoder-api/util/DbCreator.py 202106
nice -n 19 python geocoder-api/util/DbCreator.py 202107
nice -n 19 python geocoder-api/util/DbCreator.py 202108
nice -n 19 python geocoder-api/util/DbCreator.py 202109
nice -n 19 python geocoder-api/util/DbCreator.py 202110


nice -n 19 python src/DbCreator.py 202305
nice -n 19 python src/DbCreator.py 202306
nice -n 19 python src/DbCreator.py 202307
nice -n 19 python src/DbCreator.py 202308
nice -n 19 python src/DbCreator.py 202309
nice -n 19 python src/DbCreator.py 202310
nice -n 19 python src/DbCreator.py 202311
nice -n 19 python src/DbCreator.py 202312
nice -n 19 python src/DbCreator.py 202401


3. symbolic link

```bash
ln -s /home/gisman/projects/geocoder-api/db/{NEW_DB_DIR} latest
```

4. geocode.withtours.com 재시작

```bash
~/startup/geocoder.sh
```

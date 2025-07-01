# Run server

## Debug Run in vscode

launch.json 이 있어야 함.

위치: /home/gisman/projects/geocoder-api/.vscode/launch.json

내용
```js
{
    // IntelliSense를 사용하여 가능한 특성에 대해 알아보세요.
    // 기존 특성에 대한 설명을 보려면 가리킵니다.
    // 자세한 내용을 보려면 https://go.microsoft.com/fwlink/?linkid=830387을(를) 방문하세요.
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "cwd": "/home/gisman/projects/geocoder-api/web/",
            "env": {
                "FLASK_APP": "app.py",
                "FLASK_ENV": "development",
                "FLASK_DEBUG": "1"
                // "FLASK_DEBUG": "0"
            },
            "args": [
                "run",
                "--no-debugger",
                // "--no-reload",
                "--host=0.0.0.0",
                "-p 4000"
            ],
            "jinja": true
        }
    ]
}
```

## Debug Run in console
```bash
cd /home/gisman/projects/geocoder-api/web
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 -p 4000
```

## Run in console
```bash
cd /home/gisman/projects/geocoder-api/web
export FLASK_APP=app.py
export FLASK_ENV=production
flask run --host=0.0.0.0 -p 4000
```

## api test

[API테스트 서울 영등포구 영등포로62가길 4-4](http://geocode.withtours.com/api?q=서울%20영등포구%20영등포로62가길%204-4)

# Proxy

/etc/apache2/sites-enabled

geocode.conf -> ../sites-available/geocode.conf

```xml
<VirtualHost *:80>
  ServerName geocode.withtours.com
  ProxyRequests Off
  ProxyPreserveHost On
  ProxyPass / http://localhost:4000/
  ProxyPassReverse / http://localhost:4000/
</VirtualHost>
```
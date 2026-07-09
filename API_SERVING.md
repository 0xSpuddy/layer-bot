# API Serving Behind nginx

This app exposes the existing bridge dashboard and JSON API from the Flask app in `app.py`. In production, nginx should terminate HTTPS and proxy requests to a local-only WSGI server.

## Endpoints

With `MOUNT_PATH=/bridge-palmito`, the public endpoints are:

- `GET /bridge-palmito/` renders the HTML dashboard.
- `GET /bridge-palmito/api/v1/deposits` returns transformed deposit table rows as JSON.
- `GET /bridge-palmito/api/v1/withdrawals` returns transformed withdrawal table rows as JSON.
- `GET /bridge-palmito/api/v1/summary` returns counts, totals, and file metadata.
- `GET /bridge-palmito/api/v1/health` and `GET /bridge-palmito/health` return upstream health metadata.

Supported query parameters:

- Deposits: `limit`, `status`, `contract_version`
- Withdrawals: `limit`, `claimed`

## Environment

Use absolute file paths in production so the scanner and web process read the same runtime files regardless of working directory:

```env
MOUNT_PATH=/bridge-palmito
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=False
BRIDGE_DEPOSITS_CSV=/home/spuddy/monitoring/palmito/layer-bot/bridge_deposits.csv
BRIDGE_WITHDRAWALS_CSV=/home/spuddy/monitoring/palmito/layer-bot/bridge_withdrawals.csv
SCAN_TIME_FILE=/home/spuddy/monitoring/palmito/layer-bot/scan_time.json
```

## WSGI Server

Run the Flask app behind a production WSGI server instead of the built-in development server:

```sh
gunicorn --workers 2 --bind 127.0.0.1:5000 app:app
```

Keep the scanner running separately:

```sh
layerbot bridge-monitor
```

## nginx Example

Replace `example.com` and certificate paths with the real host and certificate paths.

```nginx
server {
    listen 80;
    server_name example.com;

    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    client_max_body_size 1m;

    location = /bridge-palmito {
        return 301 /bridge-palmito/;
    }

    location /bridge-palmito/ {
        proxy_pass http://127.0.0.1:5000/bridge-palmito/;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Prefix /bridge-palmito;

        proxy_connect_timeout 5s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /bridge-palmito/api/ {
        proxy_pass http://127.0.0.1:5000/bridge-palmito/api/;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Prefix /bridge-palmito;

        add_header Cache-Control "no-store";
    }

    location = /bridge-palmito/health {
        proxy_pass http://127.0.0.1:5000/bridge-palmito/health;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }
}
```

If the API should not be public, add nginx basic auth or another access control layer to `/bridge-palmito/api/` before enabling this server block.

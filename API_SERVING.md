# API Serving Behind nginx

This app exposes the existing bridge dashboard and JSON API from the Flask app in `app.py`. In production, nginx should terminate HTTPS and proxy requests to a local-only WSGI server.

## Prerequisites

- Python 3.12 or another Python version supported by this project.
- A populated `.env` file with Layer RPC, Ethereum RPC, bridge contract addresses, and CSV paths.
- `layerbot bridge-monitor` can run successfully and produce:
  - `bridge_deposits.csv`
  - `bridge_withdrawals.csv`
  - `scan_time.json`
- nginx installed on the host.
- A TLS certificate, for example from Let's Encrypt.
- `gunicorn` installed in the Python environment used to run the web app.

## Install

From the repository root:

```sh
python -m venv env
./env/bin/pip install -r requirements.txt
./env/bin/pip install -e .
./env/bin/pip install gunicorn
```

If the virtualenv already exists, activate or reuse it and make sure `gunicorn` is available:

```sh
./env/bin/gunicorn --version
```

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

Create `.env` from `.env.example`, then use absolute file paths in production so the scanner and web process read the same runtime files regardless of working directory:

```env
MOUNT_PATH=/bridge-palmito
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=False
BRIDGE_DEPOSITS_CSV=/home/spuddy/monitoring/palmito/layer-bot/bridge_deposits.csv
BRIDGE_WITHDRAWALS_CSV=/home/spuddy/monitoring/palmito/layer-bot/bridge_withdrawals.csv
SCAN_TIME_FILE=/home/spuddy/monitoring/palmito/layer-bot/scan_time.json
```

Keep `FLASK_DEBUG=False` for any public deployment.

## Start The Scanner

The scanner refreshes the CSV files that the dashboard and API read:

```sh
cd /home/spuddy/monitoring/palmito/layer-bot
./env/bin/layerbot bridge-monitor
```

Leave this running under a process manager such as systemd. The API does not scan the chains itself; it serves the latest data written by the scanner.

## WSGI Server

Run the Flask app behind a production WSGI server instead of the built-in development server:

```sh
cd /home/spuddy/monitoring/palmito/layer-bot
./env/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 app:app
```

For a quick local check without nginx:

```sh
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/api/v1/summary
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

## systemd Examples

These examples assume the repository path is `/home/spuddy/monitoring/palmito/layer-bot` and the virtualenv is `env`.

Scanner service:

```ini
[Unit]
Description=LayerBot bridge scanner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/spuddy/monitoring/palmito/layer-bot
EnvironmentFile=/home/spuddy/monitoring/palmito/layer-bot/.env
ExecStart=/home/spuddy/monitoring/palmito/layer-bot/env/bin/layerbot bridge-monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

API service:

```ini
[Unit]
Description=LayerBot dashboard and API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/spuddy/monitoring/palmito/layer-bot
EnvironmentFile=/home/spuddy/monitoring/palmito/layer-bot/.env
ExecStart=/home/spuddy/monitoring/palmito/layer-bot/env/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

After writing the unit files:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now layerbot-scanner.service
sudo systemctl enable --now layerbot-api.service
sudo systemctl status layerbot-scanner.service
sudo systemctl status layerbot-api.service
```

## Smoke Tests

Local upstream checks:

```sh
curl -i http://127.0.0.1:5000/health
curl -i http://127.0.0.1:5000/api/v1/deposits?limit=1
curl -i http://127.0.0.1:5000/api/v1/withdrawals?limit=1
curl -i http://127.0.0.1:5000/api/v1/summary
```

HTTPS checks through nginx:

```sh
curl -i https://example.com/bridge-palmito/health
curl -i https://example.com/bridge-palmito/api/v1/deposits?limit=1
curl -i https://example.com/bridge-palmito/api/v1/withdrawals?limit=1
curl -i https://example.com/bridge-palmito/api/v1/summary
```

Run the API tests from the repository root:

```sh
./env/bin/python -m unittest test_api.py
```

## Troubleshooting

- `503` with `csv_data_unavailable`: check that the scanner has created the configured CSV file and that the API service can read it.
- Empty API arrays: check the scanner logs and confirm the CSV files have rows.
- Dashboard works but `/bridge-palmito/api/...` does not: check the nginx `location /bridge-palmito/api/` block and confirm it proxies to `http://127.0.0.1:5000/bridge-palmito/api/`.
- `/bridge-palmito/static/...` 404s: confirm `MOUNT_PATH=/bridge-palmito` is set for the API service and nginx is proxying `/bridge-palmito/`.
- HTTPS redirects loop: make sure nginx terminates TLS and proxies to the local HTTP upstream, not back to the public HTTPS URL.

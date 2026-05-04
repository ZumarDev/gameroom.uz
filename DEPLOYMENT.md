# Deployment Guide

## Branch flow

- `main`: production deploy
- `muslim`: staging or preview deploy

Both branches trigger `.github/workflows/ci-cd.yml`.

## Required GitHub secrets

Add these in `Settings -> Secrets and variables -> Actions`.

For `main`:

- `PROD_SSH_HOST`: server IP or domain
- `PROD_SSH_PORT`: usually `22`
- `PROD_SSH_USER`: deploy user, for example `legal_ai`
- `PROD_SSH_PRIVATE_KEY`: private key matching the server's `authorized_keys`
- `PROD_APP_DIR`: for example `/home/legal_ai/gameroom.uz`
- `PROD_SERVICE_NAME`: for example `gameroom.service`
- `PROD_HEALTHCHECK_URL`: for example `https://gameroom.uz/healthz`

For `muslim`:

- `STAGING_SSH_HOST`
- `STAGING_SSH_PORT`
- `STAGING_SSH_USER`
- `STAGING_SSH_PRIVATE_KEY`
- `STAGING_APP_DIR`
- `STAGING_SERVICE_NAME`
- `STAGING_HEALTHCHECK_URL`

If `muslim` should deploy to the same server for now, you can reuse the same values in the `STAGING_*` secrets.

## Server preparation

Run these once on the server:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nginx sudo
```

Clone the repo as the deploy user:

```bash
cd /home/legal_ai
git clone https://github.com/ZumarDev/gameroom.uz.git
cd gameroom.uz
git checkout main
chmod +x scripts/deploy.sh
```

Create `.env` with production values.

Prepare SSH access for the deploy user:

```bash
mkdir -p /home/legal_ai/.ssh
chmod 700 /home/legal_ai/.ssh
touch /home/legal_ai/.ssh/authorized_keys
chmod 600 /home/legal_ai/.ssh/authorized_keys
chown -R legal_ai:legal_ai /home/legal_ai/.ssh
```

## Sudo permission for restart

Allow the deploy user to restart only the app service without password:

```bash
sudo visudo -f /etc/sudoers.d/gameroom-deploy
```

Add:

```text
legal_ai ALL=NOPASSWD: /usr/bin/systemctl restart gameroom.service, /usr/bin/systemctl status gameroom.service, /usr/bin/systemctl status gameroom.service --no-pager, /usr/bin/systemctl cat gameroom.service
```

## Example systemd service

Use `/etc/systemd/system/gameroom.service`:

```ini
[Unit]
Description=Gameroom Flask App
After=network.target

[Service]
User=legal_ai
Group=legal_ai
WorkingDirectory=/home/legal_ai/gameroom.uz
Environment="PATH=/home/legal_ai/gameroom.uz/.venv/bin"
ExecStart=/home/legal_ai/gameroom.uz/.venv/bin/gunicorn --bind 0.0.0.0:3000 --workers 2 --threads 2 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Then reload and enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gameroom.service
```

## Nginx

Example config:

```nginx
server {
    listen 80;
    server_name gameroom.uz www.gameroom.uz;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Health check

After deploy, workflow checks:

```text
https://gameroom.uz/healthz
```

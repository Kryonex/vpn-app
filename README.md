# VPN Telegram MVP (Bot + Mini App + FastAPI)

Production-lean MVP for selling and managing VPN subscriptions in Telegram.

## Stack
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2
- Bot: aiogram
- DB: PostgreSQL
- Queue/Cache: Redis
- Frontend: React + Vite + Telegram Mini Apps SDK
- Payments: manual transfer by phone (with admin approval)
- VPN panel integration: 3x-ui API (adapter layer)
- Infra: Docker Compose

## Repository structure
```text
.
├─ apps/
│  ├─ api/
│  │  ├─ app/
│  │  │  ├─ core/
│  │  │  ├─ db/
│  │  │  ├─ models/
│  │  │  ├─ schemas/
│  │  │  ├─ repositories/
│  │  │  ├─ services/
│  │  │  ├─ integrations/
│  │  │  │  ├─ payments/
│  │  │  │  └─ threexui/
│  │  │  ├─ routers/
│  │  │  ├─ tasks/
│  │  │  └─ scripts/
│  │  ├─ alembic/
│  │  │  └─ versions/
│  │  ├─ alembic.ini
│  │  └─ Dockerfile
│  ├─ bot/
│  │  ├─ bot/main.py
│  │  └─ Dockerfile
│  └─ web/
│     ├─ src/
│     └─ Dockerfile
├─ docker-compose.yml
├─ .env.example
└─ requirements.txt
```

## Environment setup
```bash
cp .env.example .env
```

Required variables:
- `BOT_TOKEN`
- `BOT_USERNAME`
- `MINI_APP_URL`
- `JWT_SECRET`
- `ADMIN_BEARER_TOKEN`
- `TELEGRAM_ADMIN_ID` (optional, admin access via Telegram JWT)
- `PAYMENT_PHONE` (required for manual transfer flow)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DATABASE_URL` (must match postgres credentials)
- `THREEXUI_BASE_URL`, `THREEXUI_USERNAME`, `THREEXUI_PASSWORD`

## Run with Docker Compose
```bash
docker compose up -d --build
```

Services:
- API: `http://localhost:8000`
- Web (Vite): `http://localhost:5173`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`

## Migrations and seed
API container runs these on startup:
- `alembic -c apps/api/alembic.ini upgrade head`
- `python -m app.scripts.seed`

Manual run:
```bash
docker compose run --rm api alembic -c apps/api/alembic.ini upgrade head
docker compose run --rm api python -m app.scripts.seed
```

## Health endpoints
- `GET /health/live`
- `GET /health/ready`

## Ubuntu VPS deployment

### 1) Install Docker
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```
Re-login after adding user to docker group.

### 2) Clone and configure
```bash
git clone <repo-url> vpn-platform
cd vpn-platform
cp .env.example .env
```
Fill required variables in `.env`.

### 3) Start
```bash
docker compose up -d --build
```

### 4) Logs and status
```bash
docker compose ps
docker compose logs -f api
docker compose logs -f bot
docker compose logs -f web
```

### 5) If postgres was initialized with wrong credentials
Postgres stores initial credentials in volume. If you changed `POSTGRES_DB/USER/PASSWORD` later, recreate volume:
```bash
docker compose down -v
docker compose up -d --build
```

### 6) Optional manual migration
```bash
docker compose run --rm api alembic -c apps/api/alembic.ini upgrade head
```

## Troubleshooting

### `psycopg.errors.DuplicateObject: type "vpnkeystatus" already exists`
- Fixed in `apps/api/alembic/versions/20260307_0001_init.py`.
- If database is in half-applied state, recreate volume:
```bash
docker compose down -v
docker compose up -d --build
```

### `BOT_TOKEN is not configured`
- Set `BOT_TOKEN` in `.env`.
- Restart bot:
```bash
docker compose up -d bot
docker compose logs -f bot
```

### API or web not reachable from VPS
- Open ports in firewall/security group: `8000/tcp`, `5173/tcp`.
- Check listening sockets:
```bash
ss -ltnp | grep -E '8000|5173'
```

### Stale Postgres data after env changes
```bash
docker compose down -v
docker compose up -d --build
```

## Notes
- Mini App is the main user interface.
- Bot is used for `/start`, open-app button, and notifications.
- Renew extends existing key/subscription; rotate creates a new key version.
- Payment flow: user creates payment request, transfers money to `PAYMENT_PHONE`, admin confirms payment in `/admin/payments/{payment_id}/approve`.
- Admin can manage tariffs via `/admin/plans` (`GET`, `POST`, `PATCH /admin/plans/{plan_id}`).
- Secrets are loaded from environment variables only.

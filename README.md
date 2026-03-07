# VPN Telegram MVP (Bot + Mini App + FastAPI)

Production-lean MVP для продажи и управления VPN-подписками в Telegram:
- `Telegram Bot` (aiogram) как entrypoint и канал уведомлений
- `Telegram Mini App` (React + Vite + Telegram Mini Apps SDK)
- `FastAPI` backend (Python 3.12+, SQLAlchemy 2, Alembic, Pydantic v2)
- `PostgreSQL` + `Redis`
- Интеграции с `YooKassa` и `3x-ui API`

## Repository Structure

```text
.
├─ apps/
│  ├─ api/
│  │  ├─ app/
│  │  │  ├─ core/                 # config, security, deps, redis, factories
│  │  │  ├─ db/                   # engine/session/base
│  │  │  ├─ models/               # SQLAlchemy models
│  │  │  ├─ repositories/         # data access layer
│  │  │  ├─ services/             # business logic
│  │  │  ├─ integrations/
│  │  │  │  ├─ payments/          # PaymentProvider abstraction
│  │  │  │  ├─ yookassa/          # YooKassa provider
│  │  │  │  └─ threexui/          # 3x-ui adapter/client/service
│  │  │  ├─ routers/              # REST API endpoints
│  │  │  ├─ tasks/                # scheduler jobs
│  │  │  └─ scripts/              # seed
│  │  ├─ alembic/
│  │  │  └─ versions/             # DB migrations
│  │  ├─ Dockerfile
│  │  └─ alembic.ini
│  ├─ bot/
│  │  ├─ bot/main.py              # /start, referral parse, notifications worker
│  │  └─ Dockerfile
│  └─ web/
│     ├─ src/
│     │  ├─ pages/                # Home, Keys, Key Details, Buy, Renew, Payments, Referrals, Help
│     │  ├─ context/              # auth bootstrap via Telegram initData
│     │  ├─ api/                  # API client
│     │  └─ telegram.ts           # Telegram WebApp + SDK init
│     └─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
└─ .env.example
```

## Core Decisions

### 1) Mini App as main UX
Пользовательский функционал (покупка, продление, ключи, реферальная статистика, история платежей) находится в Mini App.
Бот делает только:
- `/start`
- кнопку открытия Mini App
- нотификации

### 2) Key Rotation model
Используется versioning:
- `vpn_keys` = логическая сущность ключа
- `vpn_key_versions` = физические версии (после перевыпуска)

При rotate:
- старая версия деактивируется (`is_active=false`, `revoked_at`)
- создается новая версия
- `vpn_key` остается тем же объектом

### 3) Renew behavior
Продление **не создает новый ключ**.
Продлевается текущая подписка (`subscriptions.expires_at`), и у активной версии ключа обновляется expiry в 3x-ui.

## Data Model (MVP)
Таблицы:
- `users`
- `telegram_accounts`
- `plans`
- `vpn_keys`
- `vpn_key_versions`
- `subscriptions`
- `payments`
- `payment_events`
- `referrals`
- `referral_rewards`
- `bonus_day_ledger`
- `audit_logs`

## API

### User endpoints
- `POST /auth/telegram`
- `GET /me`
- `GET /plans`
- `GET /keys`
- `GET /keys/{key_id}`
- `POST /keys/purchase`
- `POST /keys/{key_id}/renew`
- `POST /keys/{key_id}/rotate`
- `GET /payments`
- `POST /payments/yookassa/webhook`
- `GET /referrals/me`

### Admin endpoints (Bearer token)
- `GET /admin/users`
- `GET /admin/payments`
- `GET /admin/keys`
- `GET /admin/subscriptions`
- `GET /admin/referrals`
- `POST /admin/keys/{key_id}/revoke`
- `POST /admin/users/{user_id}/bonus-days`
- `POST /admin/users/{user_id}/grant-subscription`

## Security
- Telegram WebApp `initData` validation (HMAC + `auth_date` age check)
- JWT session token for Mini App
- Admin auth via `ADMIN_BEARER_TOKEN`
- Basic rate limiting on sensitive endpoints (Redis)
- Idempotent webhook handling via unique `payment_events.provider_event_id`
- YooKassa webhook validity check via fetch of payment from YooKassa API
- CORS via env
- secrets only in env

## 3x-ui integration details
`app/integrations/threexui` содержит безопасный адаптер:
- login/session cookies
- retry/fallback endpoints
- methods:
  - `fetch_inbounds()`
  - `create_vpn_client(...)`
  - `extend_vpn_client(...)`
  - `revoke_vpn_client(...)`
  - `rotate_vpn_client(...)`

`3x-ui` API отличается между версиями, поэтому в клиенте заложены fallback paths и graceful degradation.

## Background tasks
В API на старте запускается scheduler (`tasks/scheduler.py`):
- уведомления о скором истечении (`EXPIRING_NOTIFY_DAYS`)
- пометка истекших подписок
- отправка событий в Redis queue для бота

Bot worker читает Redis queue и отправляет сообщения в Telegram.

## Quick Start

## 1) Environment
```bash
cp .env.example .env
```
Заполнить обязательно:
- `BOT_TOKEN`
- `BOT_USERNAME`
- `MINI_APP_URL`
- `JWT_SECRET`
- `ADMIN_BEARER_TOKEN`
- `YOOKASSA_SHOP_ID`
- `YOOKASSA_SECRET_KEY`
- `YOOKASSA_RETURN_URL`
- `THREEXUI_BASE_URL`
- `THREEXUI_USERNAME`
- `THREEXUI_PASSWORD`
- `THREEXUI_DEFAULT_INBOUND_ID` (опционально)

## 2) Run with Docker Compose
```bash
docker compose up --build
```

Сервисы:
- API: `http://localhost:8000`
- Web Mini App (dev server): `http://localhost:5173`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`

## 3) Migrations and seed
В compose API контейнер выполняет:
- `alembic upgrade head`
- `python -m app.scripts.seed`

При ручном запуске:
```bash
alembic -c apps/api/alembic.ini upgrade head
python -m app.scripts.seed
```

## Telegram Setup
1. Создать бота через BotFather.
2. Указать `BOT_TOKEN` и `BOT_USERNAME`.
3. Настроить Mini App URL (`MINI_APP_URL`) на фронт-домен.
4. Открывать бот через `/start`; бот отдаст кнопку открытия Mini App.

## YooKassa Setup
1. Создать магазин и получить `shopId/secretKey`.
2. Заполнить env:
   - `YOOKASSA_SHOP_ID`
   - `YOOKASSA_SECRET_KEY`
   - `YOOKASSA_RETURN_URL`
3. Настроить webhook на:
   - `POST /payments/yookassa/webhook`

## 3x-ui Setup
1. Указать:
   - `THREEXUI_BASE_URL`
   - `THREEXUI_USERNAME`
   - `THREEXUI_PASSWORD`
2. При необходимости указать inbound:
   - `THREEXUI_DEFAULT_INBOUND_ID`
3. Если inbound не задан, сервис попробует взять первый доступный.

## Seed data
Сидируются планы:
- 1 month
- 3 months
- 6 months
- 12 months

## MVP scope and production hardening
### Что уже есть в MVP
- сквозной поток auth -> purchase/renew -> webhook -> create/extend key
- rotate key versioning
- referrals + bonus days
- admin API
- queue-based notifications
- scheduler for expiring subscriptions

### Что усилить для production
- полноценный observability stack (OpenTelemetry, metrics, traces)
- Sentry/error monitoring
- stricter anti-fraud checks for payments
- resilient job queue (RQ/Celery/Arq + retries + DLQ)
- hardened secrets management (Vault/KMS)
- HA for scheduler (dedicated worker role)
- more exhaustive integration tests against real YooKassa/3x-ui sandboxes

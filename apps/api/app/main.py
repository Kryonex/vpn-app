from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.redis import close_redis
from app.routers import admin, auth, health, keys, me, payments, plans, referrals
from app.tasks.scheduler import run_scheduler

settings = get_settings()
setup_logging(logging.INFO)

app = FastAPI(title='VPN Telegram MVP API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(plans.router)
app.include_router(keys.router)
app.include_router(payments.router)
app.include_router(referrals.router)
app.include_router(admin.router)
app.include_router(health.router)


@app.on_event('startup')
async def on_startup() -> None:
    app.state.scheduler_stop_event = asyncio.Event()
    app.state.scheduler_task = asyncio.create_task(run_scheduler(app.state.scheduler_stop_event))


@app.on_event('shutdown')
async def on_shutdown() -> None:
    stop_event = getattr(app.state, 'scheduler_stop_event', None)
    task = getattr(app.state, 'scheduler_task', None)
    if stop_event:
        stop_event.set()
    if task:
        await task
    await close_redis()

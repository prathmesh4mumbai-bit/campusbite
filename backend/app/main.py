import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from . import models  # noqa: F401  (registers the tables on Base.metadata)
from .config import settings
from .database import Base, SessionLocal, engine
from .middleware import register_middleware
from .routers import ai, auth, delivery, orders, owner, restaurants
from .seed import seed_demo_data
from .tasks import reminder_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("campusbite")


def init_db(retries: int = 30, delay: float = 2.0) -> None:
    """Wait for the database to accept connections, then create any missing tables."""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            logger.warning("Database not ready yet (attempt %d/%d)", attempt, retries)
            time.sleep(delay)
    raise RuntimeError("Could not connect to the database")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(init_db)
    if settings.seed_demo_data:
        await asyncio.to_thread(seed_demo_data)
    reminder_task = asyncio.create_task(reminder_loop())
    yield
    reminder_task.cancel()


app = FastAPI(
    title="CampusBite API",
    description="Restaurant ordering & delivery platform for customers, restaurant owners and delivery partners.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time-ms", "X-Request-ID", "Retry-After"],
)
register_middleware(app)

for module in (auth, restaurants, orders, owner, delivery, ai):
    app.include_router(module.router)


@app.get("/health", tags=["Health"])
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}

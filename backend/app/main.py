from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.database import Base, engine
from app.db import models

from app.api.supervisors import router as supervisor_router
from app.api.orders import router as order_router
from app.api.runs import router as run_router

from app.runtime.scheduler import scheduler_loop


# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = asyncio.create_task(
        scheduler_loop()
    )

    print("[App] Scheduler started")

    yield

    scheduler_task.cancel()

    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

    print("[App] Scheduler stopped")


app = FastAPI(
    title="Order Supervisor",
    version="0.1.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_private_network_header(request, call_next):
    response = await call_next(request)

    if request.headers.get("access-control-request-private-network") == "true":
        response.headers["Access-Control-Allow-Private-Network"] = "true"

    return response

# --------------------------------------------------
# API Routers
# --------------------------------------------------

app.include_router(supervisor_router)
app.include_router(order_router)
app.include_router(run_router)


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.get("/db-health")
def database_health_check():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1")
        )

        return {
            "database": "connected",
            "result": result.scalar(),
        }
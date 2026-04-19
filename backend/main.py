"""
main.py
-------
FastAPI application entry point.
Registers all routers, configures CORS (for the React frontend),
and initializes the database on startup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import init_db
from routers import flights, predict, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup: initialise the database."""
    await init_db()
    yield


app = FastAPI(
    title="AeroTrack API",
    description="Flight trajectory fusion, gap-filling, and prediction system.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the React dev server (port 5173) and production build
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flights.router)
app.include_router(predict.router)
app.include_router(analytics.router)

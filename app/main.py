from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.database import init_db
from app.routers import (
    academics, announcements, assessments, attendance, 
    auth, finance, payroll, submissions, dashboard
)

settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield

app = FastAPI(title="School Management System", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)
app.include_router(auth.router)
app.include_router(academics.router)
app.include_router(attendance.router)
app.include_router(assessments.router)
app.include_router(finance.router)
app.include_router(announcements.router)
app.include_router(payroll.router)
app.include_router(submissions.router)
app.include_router(dashboard.router)

app.mount("/ui", StaticFiles(directory="static", html=True), name="static")

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
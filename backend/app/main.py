from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth
from .utils.telegram import setup_bot, stop_bot
import asyncio

app = FastAPI(
    title="Sublet Backend",
    description="Backend API for Sublet project",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роуты
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])

@app.on_event("startup")
async def startup_event():
    """Запускаем бота при старте приложения"""
    await setup_bot()

@app.on_event("shutdown")
async def shutdown_event():
    """Останавливаем бота при завершении работы приложения"""
    await stop_bot()

@app.get("/")
async def root():
    return {
        "message": "Welcome to Sublet Backend API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    } 
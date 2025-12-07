import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.apps.hooks.api import router as hooks_router
from src.apps.ms_auth.api import router as ms_auth_router
from src.core.db import init_db

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте приложения создаём таблицы (для SQLite ок).
    await init_db()
    yield
    # При остановке сейчас ничего делать не нужно.


app = FastAPI(
    title="МС: Автоматическая привязка платежей",
    lifespan=lifespan,
)

# Статика
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Шаблоны
templates = Jinja2Templates(directory="src/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    context = {
        "request": request,
        "page_title": "Автоматическая привязка платежей",
    }
    return templates.TemplateResponse("index.html", context)


# Подключаем роуты приложений
app.include_router(ms_auth_router, prefix="/api/auth/ms", tags=["ms_auth"])
app.include_router(hooks_router, prefix="/api/hooks", tags=["hooks"])

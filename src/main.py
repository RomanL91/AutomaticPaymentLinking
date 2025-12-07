import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.apps.hooks.api import router as hooks_router
from src.apps.ms_auth.api import router as ms_auth_router
from src.core.database import init_db
from src.core.logging_config import setup_logging

# Создаём папку для логов
Path("logs").mkdir(exist_ok=True)

# Настраиваем логирование
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="МС: Автоматическая привязка платежей",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="src/static"), name="static")

templates = Jinja2Templates(directory="src/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    context = {
        "request": request,
        "page_title": "Автоматическая привязка платежей",
    }
    return templates.TemplateResponse("index.html", context)


app.include_router(ms_auth_router, prefix="/api/auth/ms", tags=["ms_auth"])
app.include_router(hooks_router, prefix="/api/hooks", tags=["hooks"])
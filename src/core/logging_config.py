import logging
import sys
from pathlib import Path

from .config import settings


def setup_logging() -> None:
    """Настройка логирования для всего приложения"""
    
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Создаём папку для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=log_level,
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                log_dir / "app.log",
                encoding="utf-8",
            ),
        ],
    )
    
    # Отключаем избыточное логирование библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
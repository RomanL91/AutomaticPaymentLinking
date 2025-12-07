import base64
import logging
import os
from typing import Optional

from .schemas import MySkladCredentialsIn, MySkladCredentialsOut

logger = logging.getLogger(__name__)


class MySkladAuthService:
    """
    Простейший сервис, который хранит и отдает настройки доступа к МойСклад.
    Сейчас:
      - при инициализации пытается взять логин/пароль из переменных окружения;
      - если настроек нет, можно задать их через API;
      - при каждом запросе, если настроек нет, ещё раз пробует подгрузить из env (лениво).
    """

    def __init__(self) -> None:
        self._credentials: Optional[MySkladCredentialsIn] = None
        self._load_from_env()

    def _load_from_env(self) -> None:
        """
        Загружает креды из переменных окружения, если они есть:
        MS_LOGIN, MS_PASSWORD, MS_BASE_URL (опционально).
        Здесь же можно прописать dev-дефолты.
        """
        # Чтобы не перезатирать уже сохранённые через API:
        if self._credentials is not None:
            return

        login = os.getenv("MS_LOGIN")
        password = os.getenv("MS_PASSWORD")
        base_url = os.getenv("MS_BASE_URL", "https://api.moysklad.ru/api/remap/1.2")

        # ---- DEV-ДЕФОЛТЫ (НЕ КОММИТИТЬ В GIT) ----
        # Если хочешь жестко зашить креды на время разработки:
        if not login:
            login = "spec-it@installbiz"
        if not password:
            password = "Pikqqtn&21"
        # ------------------------------------------

        if login and password:
            logger.info("Loaded MoySklad credentials from ENV for login=%s", login)
            self._credentials = MySkladCredentialsIn(
                login=login,
                password=password,
                base_url=base_url,
            )
        else:
            logger.info(
                "MoySklad credentials ENV not found or incomplete "
                "(MS_LOGIN=%r, MS_PASSWORD set=%s)",
                login,
                bool(password),
            )

    def set_credentials(self, creds: MySkladCredentialsIn) -> None:
        self._credentials = creds

    def _ensure_loaded(self) -> None:
        """
        Ленивая подгрузка: если по какой-то причине при старте не подхватили ENV,
        попробуем ещё раз в момент первого использования.
        """
        if self._credentials is None:
            self._load_from_env()

    def get_credentials(self) -> Optional[MySkladCredentialsOut]:
        self._ensure_loaded()
        if self._credentials is None:
            return None
        return MySkladCredentialsOut(
            login=self._credentials.login,
            base_url=self._credentials.base_url,
            has_password=self._credentials.password != "",
        )

    def get_raw_credentials(self) -> Optional[MySkladCredentialsIn]:
        """
        Нужен для внутренних вызовов (когда реально идём в МойСклад).
        """
        self._ensure_loaded()
        return self._credentials

    def get_basic_auth_header(self) -> Optional[dict]:
        """
        Готовит заголовок Authorization: Basic ...
        Вернёт None, если креды еще не настроены.
        """
        self._ensure_loaded()
        if self._credentials is None:
            return None

        login = self._credentials.login
        password = self._credentials.password
        token = f"{login}:{password}".encode("utf-8")
        encoded = base64.b64encode(token).decode("utf-8")

        return {"Authorization": f"Basic {encoded}"}


# Глобальный инстанс сервиса (как singleton)
_auth_service = MySkladAuthService()


def get_ms_auth_service() -> MySkladAuthService:
    """
    Dependency для FastAPI.
    """
    return _auth_service

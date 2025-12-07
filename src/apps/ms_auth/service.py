import base64
import logging
from typing import Optional

from src.core.config import settings

from .schemas import MySkladCredentialsIn, MySkladCredentialsOut

logger = logging.getLogger(__name__)


class MySkladAuthService:
    def __init__(self) -> None:
        self._credentials: Optional[MySkladCredentialsIn] = None
        self._load_from_env()

    def _load_from_env(self) -> None:
        if self._credentials is not None:
            return

        login = settings.ms_login
        password = settings.ms_password
        base_url = settings.ms_base_url

        if login and password:
            logger.info("Загружены credentials МойСклад из ENV: login=%s", login)
            try:
                self._credentials = MySkladCredentialsIn(
                    login=login,
                    password=password,
                    base_url=base_url,
                )
            except Exception as exc:
                logger.error("Ошибка валидации credentials из ENV: %s", exc)
                self._credentials = None
        else:
            logger.warning(
                "Credentials МойСклад не найдены в ENV (APL_MS_LOGIN, APL_MS_PASSWORD)"
            )

    def set_credentials(self, creds: MySkladCredentialsIn) -> None:
        logger.info("Установлены новые credentials: login=%s", creds.login)
        self._credentials = creds

    def _ensure_loaded(self) -> None:
        if self._credentials is None:
            self._load_from_env()

    def get_credentials(self) -> Optional[MySkladCredentialsOut]:
        self._ensure_loaded()
        if self._credentials is None:
            return None
        return MySkladCredentialsOut(
            login=self._credentials.login,
            base_url=self._credentials.base_url,
            has_password=bool(self._credentials.password),
        )

    def get_raw_credentials(self) -> Optional[MySkladCredentialsIn]:
        self._ensure_loaded()
        return self._credentials

    def get_basic_auth_header(self) -> Optional[dict]:
        self._ensure_loaded()
        if self._credentials is None:
            return None

        login = self._credentials.login
        password = self._credentials.password
        token = f"{login}:{password}".encode("utf-8")
        encoded = base64.b64encode(token).decode("utf-8")

        return {"Authorization": f"Basic {encoded}"}


_auth_service = MySkladAuthService()


def get_ms_auth_service() -> MySkladAuthService:
    return _auth_service
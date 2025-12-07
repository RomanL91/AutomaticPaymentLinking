from fastapi import APIRouter, Depends, status

from .schemas import MySkladCredentialsIn, MySkladCredentialsOut
from .service import MySkladAuthService, get_ms_auth_service

router = APIRouter()


@router.get("/credentials", response_model=MySkladCredentialsOut | None)
async def get_credentials(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
):
    """
    Получить текущие настройки доступа к МойСклад (без пароля).
    Если настроек нет — вернём null.
    """
    return auth_service.get_credentials()


@router.post(
    "/credentials",
    response_model=MySkladCredentialsOut,
    status_code=status.HTTP_201_CREATED,
)
async def set_credentials(
    payload: MySkladCredentialsIn,
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
):
    """
    Сохранить/обновить настройки доступа к МойСклад.
    """
    auth_service.set_credentials(payload)
    return auth_service.get_credentials()

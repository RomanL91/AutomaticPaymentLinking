"""Dependency Injection для входящих платежей."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.services.auth_service import MySkladAuthService, get_ms_auth_service
from .services.paymentin_service import PaymentInService


async def get_paymentin_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> PaymentInService:
    """Получить сервис входящих платежей."""
    return PaymentInService(auth_service=auth_service)


PaymentInSvcDep = Annotated[PaymentInService, Depends(get_paymentin_service)]
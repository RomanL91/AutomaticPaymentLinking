from typing import Annotated

from fastapi import Depends

from .services.auth_service import MySkladAuthService, get_ms_auth_service

AuthSvcDep = Annotated[MySkladAuthService, Depends(get_ms_auth_service)]

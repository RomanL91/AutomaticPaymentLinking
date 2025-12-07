from pydantic import BaseModel, HttpUrl


class MySkladCredentialsIn(BaseModel):
    """
    Что вводим/храним: логин/пароль и базовый URL API МойСклад.
    """
    login: str = ""
    password: str = ""
    base_url: HttpUrl = "https://api.moysklad.ru/api/remap/1.2"


class MySkladCredentialsOut(BaseModel):
    """
    Что отдаем наружу (без пароля).
    """
    login: str
    base_url: HttpUrl
    has_password: bool = True

from pydantic import BaseModel, HttpUrl, field_validator


class MySkladCredentialsIn(BaseModel):
    login: str
    password: str
    base_url: HttpUrl = "https://api.moysklad.ru/api/remap/1.2"

    @field_validator("login")
    @classmethod
    def validate_login(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Логин не может быть пустым")
        if len(v) < 3:
            raise ValueError("Логин должен содержать минимум 3 символа")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v:
            raise ValueError("Пароль не может быть пустым")
        if len(v) < 6:
            raise ValueError("Пароль должен содержать минимум 6 символов")
        return v


class MySkladCredentialsOut(BaseModel):
    login: str
    base_url: HttpUrl
    has_password: bool = True
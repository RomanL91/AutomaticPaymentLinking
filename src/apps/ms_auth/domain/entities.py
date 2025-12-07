from dataclasses import dataclass

from pydantic import HttpUrl


@dataclass
class MySkladCredentials:
    """Доменная сущность credentials для МойСклад."""
    
    login: str
    password: str
    base_url: HttpUrl
    
    def get_basic_auth_token(self) -> str:
        """Получить токен для Basic Auth."""
        import base64
        token = f"{self.login}:{self.password}".encode("utf-8")
        return base64.b64encode(token).decode("utf-8")
    
    def to_dict_safe(self) -> dict:
        """Преобразовать в словарь без пароля."""
        return {
            "login": self.login,
            "base_url": str(self.base_url),
            "has_password": bool(self.password),
        }
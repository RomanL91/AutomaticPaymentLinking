from dataclasses import dataclass


@dataclass(frozen=True)
class BasicAuthHeader:
    """Value Object для заголовка авторизации."""
    
    token: str
    
    def to_dict(self) -> dict:
        return {"Authorization": f"Basic {self.token}"}
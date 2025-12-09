"""Исключения для работы с отгрузками (demand)."""


class DemandBaseException(Exception):
    """Базовое исключение для отгрузок."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DemandNotFoundError(DemandBaseException):
    """Отгрузка не найдена."""


class DemandAPIError(DemandBaseException):
    """Ошибка при работе с API отгрузок."""
"""Исключения для работы с заказами покупателя."""


class CustomerOrderBaseException(Exception):
    """Базовое исключение для заказов покупателя."""
    
    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class CustomerOrderNotFoundError(CustomerOrderBaseException):
    """Заказ покупателя не найден."""


class CustomerOrderAPIError(CustomerOrderBaseException):
    """Ошибка при работе с API заказов покупателя."""
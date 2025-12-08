"""Исключения для работы с входящими платежами."""


class PaymentInBaseException(Exception):
    """Базовое исключение для входящих платежей."""
    
    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PaymentInNotFoundError(PaymentInBaseException):
    """Входящий платеж не найден."""


class PaymentInAPIError(PaymentInBaseException):
    """Ошибка при работе с API входящих платежей."""
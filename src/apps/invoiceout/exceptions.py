"""Исключения для работы со счетами покупателю."""


class InvoiceOutBaseException(Exception):
    """Базовое исключение для счетов покупателю."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InvoiceOutNotFoundError(InvoiceOutBaseException):
    """Счет покупателю не найден."""


class InvoiceOutAPIError(InvoiceOutBaseException):
    """Ошибка при работе с API счетов покупателю."""
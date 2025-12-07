"""Кастомные исключения для приложения hooks."""


class HooksBaseException(Exception):
    """Базовое исключение для приложения hooks."""
    
    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class WebhookNotFoundError(HooksBaseException):
    """Вебхук не найден."""


class WebhookAlreadyExistsError(HooksBaseException):
    """Вебхук уже существует."""


class WebhookConfigurationError(HooksBaseException):
    """Ошибка конфигурации вебхука."""


class MoySkladAPIError(HooksBaseException):
    """Ошибка при взаимодействии с API МойСклад."""


class RepositoryError(HooksBaseException):
    """Ошибка при работе с репозиторием."""
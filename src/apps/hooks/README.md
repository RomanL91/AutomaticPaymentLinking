# Приложение Hooks - Управление Вебхуками МойСклад

## Обзор

Приложение `hooks` отвечает за управление вебхуками МойСклад для автоматической привязки платежей. Реализует Clean Architecture с разделением на слои и использует паттерны DDD, Repository, Unit of Work, Strategy и Factory.

## Архитектура
```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                            │
│  (FastAPI endpoints + Dependency Injection)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Service Layer                            │
│  (Бизнес-логика + Координация)                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼────────┐ ┌──▼─────────┐ ┌──▼────────────┐
│ Operations     │ │ Client     │ │ Unit of Work  │
│ (Strategies)   │ │ (MoySklad) │ │               │
└────────────────┘ └────────────┘ └───────┬───────┘
                                           │
                                  ┌────────▼────────┐
                                  │  Repositories   │
                                  │                 │
                                  └────────┬────────┘
                                           │
                              ┌────────────▼────────────┐
                              │    Domain Layer         │
                              │ (Entities + VOs)        │
                              └────────────┬────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │  Data Layer     │
                                  │ (SQLAlchemy)    │
                                  └─────────────────┘
```

## Структура файлов
```
src/apps/hooks/
├── __init__.py
├── README.md                      # Этот файл
│
├── api.py                         # FastAPI эндпоинты
├── dependencies.py                # Dependency Injection
├── schemas.py                     # Pydantic схемы запросов/ответов
├── models.py                      # SQLAlchemy модели
├── exceptions.py                  # Кастомные исключения
├── exception_handlers.py          # Обработчики исключений
│
├── domain/                        # Доменный слой (DDD)
│   ├── __init__.py
│   ├── entities.py                # Доменные сущности
│   └── value_objects.py           # Value Objects
│
├── services/                      # Сервисный слой
│   ├── __init__.py
│   ├── webhook_service.py         # Основной сервис
│   ├── webhook_operations.py      # Операции (Strategy Pattern)
│   └── moysklad_client.py         # HTTP клиент API МойСклад
│
├── repositories/                  # Слой данных
│   ├── __init__.py
│   ├── base.py                    # Абстрактный репозиторий
│   └── webhook_repository.py      # Репозиторий вебхуков
│
└── uow/                          # Unit of Work
    ├── __init__.py
    └── unit_of_work.py           # Управление транзакциями
```

## Слои и ответственность

### 1. API Layer (`api.py`)
**Ответственность:**
- Определение HTTP эндпоинтов
- Валидация входящих данных (Pydantic)
- Вызов сервисов
- Формирование HTTP ответов
- Логирование запросов

### 2. Dependencies (`dependencies.py`)
**Ответственность:**
- Создание зависимостей для FastAPI
- Инициализация сервисов и UoW
- Type hints для автокомплита

### 3. Service Layer (`services/`)
**Ответственность:**
- Бизнес-логика приложения
- Координация между слоями
- Валидация бизнес-правил
- Работа с внешними API

### 4. Domain Layer (`domain/`)
**Ответственность:**
- Доменные модели (entities)
- Бизнес-логика уровня сущности
- Value Objects (неизменяемые объекты)
- Инкапсуляция данных

### 5. Repository Layer (`repositories/`)
**Ответственность:**
- Абстракция работы с БД
- CRUD операции
- Преобразование между моделями БД и сущностями
- Сложные запросы

### 6. Unit of Work (`uow/`)
**Ответственность:**
- Управление транзакциями
- Предоставление репозиториев
- Атомарность операций
- Откат при ошибках

---

## API Endpoints - Детальное описание

### 1. GET `/api/hooks/webhooks/status`

**Назначение:** Получить текущий статус всех вебхуков

**Входные данные:** нет

**Выходные данные:**
```json
{
  "webhooks": {
    "incoming_payment": true,
    "incoming_order": false,
    "outgoing_payment": false,
    "outgoing_order": true
  }
}
```

**Flow через слои:**
```
1. FastAPI Router (api.py)
   └─> Вызов: get_webhooks_status(service: WebhookSvcDep)
       │
       ▼
2. WebhookService (webhook_service.py)
   └─> Метод: get_webhooks_status()
       │
       ▼
3. Unit of Work (unit_of_work.py)
   └─> Property: webhooks -> WebhookRepository
       │
       ▼
4. WebhookRepository (webhook_repository.py)
   └─> Метод: get_status_dict()
       │   └─> get_all() -> SELECT всех вебхуков
       │
       ▼
5. SQLAlchemy
   └─> SELECT * FROM webhooksubscriptions
       │
       ▼
6. Преобразование
   └─> Model -> WebhookEntity -> Dict[str, bool]
       │
       ▼
7. Response
   └─> WebhookStatusResponse
```

**Детали:**
1. FastAPI принимает запрос, внедряет `WebhookService` через DI
2. Сервис запрашивает данные через UoW
3. UoW предоставляет репозиторий вебхуков
4. Репозиторий выполняет запрос в БД через SQLAlchemy
5. Модели БД преобразуются в доменные сущности
6. Сущности преобразуются в словарь статусов
7. Возвращается Pydantic схема `WebhookStatusResponse`

---

### 2. POST `/api/hooks/auto-link-toggle`

**Назначение:** Включить/выключить автоматическую привязку для типа платежа

**Входные данные:**
```json
{
  "payment_type": "incoming_payment",
  "enabled": true
}
```

**Выходные данные:**
```json
{
  "status": "ok",
  "payment_type": "incoming_payment",
  "enabled": true,
  "operation": "created_and_enabled",
  "db_record_id": 1
}
```

**Flow через слои:**
```
1. FastAPI Router (api.py)
   └─> Endpoint: auto_link_toggle(payload, service)
       │
       ▼
2. Валидация
   └─> AutoLinkTogglePayload (Pydantic)
       │
       ▼
3. WebhookService (webhook_service.py)
   └─> Метод: toggle_webhook(payment_type, enabled)
       │
       ├─> Проверка: webhook_url настроен?
       │   └─> Если нет -> возврат WebhookOperationResult (skipped)
       │
       ├─> Проверка: credentials настроены?
       │   └─> Если нет -> возврат WebhookOperationResult (skipped)
       │
       ├─> Создание: WebhookConfiguration.from_payment_type()
       │   └─> Value Object с entity_type, action, url
       │
       ▼
4. WebhookOperationFactory (webhook_operations.py)
   └─> create_operation(enabled, client, config)
       │
       ├─> Если enabled=True  -> EnableWebhookOperation
       └─> Если enabled=False -> DisableWebhookOperation
       │
       ▼
5a. EnableWebhookOperation.execute() [Strategy Pattern]
    │
    ├─> MoySkladClient.find_webhook(entity_type, action, url)
    │   └─> HTTP GET к МойСклад API /entity/webhook
    │   └─> Поиск существующего вебхука по параметрам
    │
    ├─> Если не найден:
    │   └─> MoySkladClient.create_webhook()
    │       └─> HTTP POST к МойСклад API /entity/webhook
    │       └─> Получение ID и href нового вебхука
    │
    ├─> Если найден и enabled=true:
    │   └─> Возврат: already_enabled
    │
    └─> Если найден и enabled=false:
        └─> MoySkladClient.update_webhook_enabled(true)
            └─> HTTP PUT к МойСклад API {href}
            └─> Обновление статуса вебхука
    │
    ▼
6. Преобразование ответа
   └─> Данные API -> WebhookEntity (domain/entities.py)
       │
       ▼
7. Сохранение в БД
   └─> WebhookRepository.upsert(entity)
       │
       ├─> get_by_ms_webhook_id() - проверка существования
       │
       ├─> Если существует:
       │   └─> update() - обновление через SQLAlchemy
       │
       └─> Если не существует:
           └─> add() - создание через SQLAlchemy
       │
       ▼
8. Фиксация транзакции
   └─> UnitOfWork.commit()
       └─> AsyncSession.commit()
       │
       ▼
9. Возврат результата
   └─> WebhookOperationResult -> JSON Response
```

**Детали выполнения:**

**Шаг 1-2: Прием и валидация**
- FastAPI валидирует входные данные через Pydantic
- Внедряется `WebhookService` через DI

**Шаг 3: Предварительные проверки**
```python
# Проверка настройки webhook_url
if not settings.ms_webhook_url:
    return WebhookOperationResult(
        operation="skipped_no_webhook_url",
        success=False,
        message="Webhook URL не настроен"
    )

# Проверка credentials МойСклад
if not auth_service.get_raw_credentials():
    return WebhookOperationResult(
        operation="skipped_no_credentials",
        success=False,
        message="Credentials не настроены"
    )
```

**Шаг 4: Factory Pattern**
```python
# Выбор стратегии операции
if enabled:
    operation = EnableWebhookOperation(client, config)
else:
    operation = DisableWebhookOperation(client, config)
```

**Шаг 5: Strategy Pattern - Выполнение операции**

Для `EnableWebhookOperation`:
```python
# 1. Поиск существующего
existing = await client.find_webhook(entity_type, action, url)

# 2. Создание нового (если не найден)
if not existing:
    webhook_data = await client.create_webhook(...)
    return WebhookOperationResult(
        operation="created_and_enabled",
        webhook_entity=entity
    )

# 3. Уже включен (пропустить)
if existing.get("enabled") is True:
    return WebhookOperationResult(
        operation="already_enabled",
        webhook_entity=entity
    )

# 4. Включить существующий
updated = await client.update_webhook_enabled(existing, True)
return WebhookOperationResult(
    operation="enabled",
    webhook_entity=entity
)
```

**Шаг 6-8: Сохранение в БД**
```python
# Преобразование payment_type
result.webhook_entity.payment_type = payment_type

# Upsert в БД
saved_entity = await uow.webhooks.upsert(entity)

# Фиксация транзакции
await uow.commit()
```

**Шаг 9: Формирование ответа**
```python
return {
    "status": "ok",
    "payment_type": payload.payment_type,
    "enabled": payload.enabled,
    "operation": result.operation,
    "db_record_id": saved_entity.id
}
```

**Возможные операции:**
- `created_and_enabled` - создан новый вебхук
- `enabled` - включен существующий
- `already_enabled` - уже был включен
- `disabled` - выключен
- `already_disabled` - уже был выключен
- `not_found_to_disable` - не найден для отключения
- `skipped_no_webhook_url` - пропущено (нет URL)
- `skipped_no_credentials` - пропущено (нет credentials)

---

### 3. POST `/api/hooks/moysklad/webhook`

**Назначение:** Принять входящий вебхук от МойСклад

**Входные данные:**
```json
{
  "auditContext": {
    "meta": {
      "href": "https://api.moysklad.ru/...",
      "type": "employee"
    },
    "moment": "2025-01-15T10:30:00.000",
    "uid": "admin@example.com"
  },
  "events": [
    {
      "meta": {
        "href": "https://api.moysklad.ru/api/remap/1.2/entity/paymentin/...",
        "type": "paymentin"
      },
      "action": "CREATE",
      "accountId": "abc123",
      "updatedFields": ["sum", "incomingDate"]
    }
  ]
}
```

**Query параметры:**
- `requestId` (обязательный) - уникальный ID запроса от МойСклад

**Выходные данные:**
- HTTP 204 No Content (успех)
- HTTP 400 Bad Request (если нет requestId)

**Flow через слои:**
```
1. FastAPI Router (api.py)
   └─> Endpoint: receive_moysklad_webhook(payload, request_id)
       │
       ▼
2. Валидация
   ├─> Query param: requestId присутствует?
   │   └─> Если нет -> HTTPException 400
   │
   └─> Body: MySkladWebhookPayload (Pydantic)
       │
       ▼
3. Логирование (пока только)
   ├─> Logger.info() - общая информация о вебхуке
   │   └─> requestId, количество events, uid, moment
   │
   └─> Logger.info() для каждого event
       └─> type, action, href, accountId, updatedFields
       │
       ▼
4. Response
   └─> HTTP 204 No Content
```

**Детали:**

**Текущая реализация:**
```python
# 1. Проверка обязательного параметра
if not request_id:
    raise HTTPException(
        status_code=400,
        detail="requestId обязателен"
    )

# 2. Логирование общего контекста
logger.info(
    "Получен вебхук МойСклад: requestId=%s, events=%d, uid=%s, moment=%s",
    request_id,
    len(payload.events),
    payload.auditContext.uid,
    payload.auditContext.moment,
)

# 3. Логирование каждого события
for event in payload.events:
    logger.info(
        "Событие: type=%s, action=%s, href=%s, accountId=%s",
        event.meta.type,
        event.action,
        event.meta.href,
        event.accountId,
    )

# 4. Возврат 204
return Response(status_code=204)
```

**Структура данных вебхука:**

**AuditContext:**
- `meta.href` - ссылка на сотрудника, создавшего событие
- `meta.type` - тип сущности (employee)
- `moment` - временная метка события
- `uid` - email/логин пользователя

**Event:**
- `meta.href` - прямая ссылка на созданную сущность
- `meta.type` - тип сущности (paymentin, cashin, paymentout, cashout)
- `action` - тип действия (CREATE, UPDATE, DELETE, PROCESSED)
- `accountId` - ID аккаунта МойСклад
- `updatedFields` - измененные поля (для UPDATE)

**Будущая реализация:**
```python
# Планируется обработка событий:
# 1. Получение полных данных платежа через href
# 2. Поиск связанных документов (заказов)
# 3. Автоматическая привязка платежа к заказу
# 4. Сохранение информации о привязке в БД
```

---

## Паттерны проектирования

### 1. Repository Pattern
**Файлы:** `repositories/base.py`, `repositories/webhook_repository.py`

**Применение:**
- Абстракция работы с БД
- Инкапсуляция SQL запросов
- Преобразование между моделями БД и доменными сущностями
```python
# Пример использования
webhook = await repository.get_by_payment_type(PaymentType.incoming_payment)
await repository.upsert(webhook_entity)
```

### 2. Unit of Work Pattern
**Файлы:** `uow/unit_of_work.py`

**Применение:**
- Управление транзакциями
- Атомарность операций
- Предоставление репозиториев
```python
# Пример использования
async with UnitOfWork(session) as uow:
    webhook = await uow.webhooks.get_by_id(1)
    webhook.activate()
    await uow.webhooks.update(webhook)
    await uow.commit()
```

### 3. Strategy Pattern
**Файлы:** `services/webhook_operations.py`

**Применение:**
- Различные стратегии включения/выключения вебхуков
- Инкапсуляция алгоритмов операций
- Легкое добавление новых операций
```python
# Абстрактная стратегия
class WebhookOperation(ABC):
    async def execute(self) -> WebhookOperationResult:
        ...

# Конкретные стратегии
class EnableWebhookOperation(WebhookOperation):
    async def execute(self) -> WebhookOperationResult:
        # Логика включения

class DisableWebhookOperation(WebhookOperation):
    async def execute(self) -> WebhookOperationResult:
        # Логика отключения
```

### 4. Factory Pattern
**Файлы:** `services/webhook_operations.py`

**Применение:**
- Создание операций на основе параметров
- Инкапсуляция логики выбора стратегии
```python
class WebhookOperationFactory:
    @staticmethod
    def create_operation(enabled: bool, ...) -> WebhookOperation:
        if enabled:
            return EnableWebhookOperation(...)
        else:
            return DisableWebhookOperation(...)
```

### 5. Dependency Injection Pattern
**Файлы:** `dependencies.py`, `api.py`

**Применение:**
- Инверсия зависимостей
- Тестируемость кода
- Типизированные зависимости
```python
# Определение зависимостей
WebhookSvcDep = Annotated[WebhookService, Depends(get_webhook_service)]

# Использование в эндпоинтах
@router.get("/status")
async def get_status(service: WebhookSvcDep):
    ...
```

### 6. Domain-Driven Design (DDD)
**Файлы:** `domain/entities.py`, `domain/value_objects.py`

**Применение:**
- Доменные сущности с бизнес-логикой
- Value Objects (неизменяемые объекты)
- Инкапсуляция данных и поведения
```python
# Entity
@dataclass
class WebhookEntity:
    def activate(self) -> None:
        self.enabled = True
    
    def is_active(self) -> bool:
        return self.enabled

# Value Object
@dataclass(frozen=True)
class WebhookConfiguration:
    entity_type: str
    action: str
    url: str
```

---

## Обработка исключений

### Кастомные исключения
**Файл:** `exceptions.py`
```python
HooksBaseException           # Базовое
├── WebhookNotFoundError     # 404 - вебхук не найден
├── WebhookAlreadyExistsError # 409 - вебхук уже существует
├── WebhookConfigurationError # 400 - ошибка конфигурации
├── MoySkladAPIError         # 502 - ошибка API МойСклад
└── RepositoryError          # 500 - ошибка БД
```

### Exception Handlers
**Файл:** `exception_handlers.py`

Каждое исключение имеет свой обработчик, который:
1. Логирует ошибку
2. Возвращает соответствующий HTTP статус
3. Форматирует ответ в JSON
```python
# Регистрация в FastAPI (main.py)
for exc_class, handler in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler)
```

---

## Схемы данных (Pydantic)

### Типы платежей
```python
class PaymentType(str, Enum):
    incoming_payment = "incoming_payment"  # Входящий платеж
    incoming_order = "incoming_order"      # Приходный ордер
    outgoing_payment = "outgoing_payment"  # Исходящий платеж
    outgoing_order = "outgoing_order"      # Расходный ордер
```

### Маппинг на типы МойСклад
```python
PAYMENT_TYPE_TO_ENTITY_TYPE = {
    PaymentType.incoming_payment: "paymentin",
    PaymentType.incoming_order: "cashin",
    PaymentType.outgoing_payment: "paymentout",
    PaymentType.outgoing_order: "cashout",
}
```

---

## Модель базы данных

### Таблица `webhooksubscriptions`
```python
class WebhookSubscription(Base):
    id: int                    # PK
    created_at: datetime       # Дата создания
    updated_at: datetime       # Дата обновления
    is_active: bool            # Активна ли запись
    
    payment_type: PaymentType  # Тип платежа (enum)
    entity_type: str           # Тип сущности МС (paymentin, cashin, etc)
    action: str                # Действие (CREATE, UPDATE, etc)
    url: str                   # URL вебхука
    
    ms_webhook_id: str         # ID вебхука в МойСклад (unique)
    ms_href: str               # Ссылка на вебхук в МойСклад
    ms_account_id: str         # ID аккаунта МойСклад
    
    enabled: bool              # Включен ли вебхук
```

### Индексы
```python
Index("ix_webhook_payment_enabled", "payment_type", "enabled")
Index("ix_webhook_entity_action_url", "entity_type", "action", "url")
```

---

## Взаимодействие с МойСклад API

### HTTP Client
**Файл:** `services/moysklad_client.py`

**Возможности:**
- Retry логика (3 попытки с экспоненциальной задержкой)
- Автоматическое добавление заголовков авторизации
- Обработка ошибок HTTP

**Методы:**
```python
# Список вебхуков
list_webhooks(limit=100) -> list[Dict]

# Создание вебхука
create_webhook(entity_type, action, url) -> Dict

# Обновление статуса
update_webhook_enabled(webhook_data, enabled) -> Dict

# Поиск вебхука
find_webhook(entity_type, action, url) -> Optional[Dict]
```

### Retry стратегия
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
```

---

## Конфигурация

### Переменные окружения
```ini
# Префикс: APL_

# База данных
APL_DATABASE_URL=sqlite+aiosqlite:///./db.sqlite3

# МойСклад API
APL_MS_LOGIN=your_login
APL_MS_PASSWORD=your_password
APL_MS_BASE_URL=https://api.moysklad.ru/api/remap/1.2

# Вебхуки
APL_MS_WEBHOOK_URL=https://your-domain.com/api/hooks/moysklad/webhook

# Логирование
APL_LOG_LEVEL=INFO
APL_LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Настройка через API
```bash
# Установить credentials
POST /api/auth/ms/credentials
{
  "login": "your_login",
  "password": "your_password",
  "base_url": "https://api.moysklad.ru/api/remap/1.2"
}
```

---

## Примеры использования API

### 1. Проверка статуса вебхуков
```bash
curl -X GET http://localhost:8000/api/hooks/webhooks/status
```

Response:
```json
{
  "webhooks": {
    "incoming_payment": true,
    "incoming_order": false,
    "outgoing_payment": false,
    "outgoing_order": false
  }
}
```

### 2. Включение вебхука
```bash
curl -X POST http://localhost:8000/api/hooks/auto-link-toggle \
  -H "Content-Type: application/json" \
  -d '{
    "payment_type": "incoming_payment",
    "enabled": true
  }'
```

Response (успех):
```json
{
  "status": "ok",
  "payment_type": "incoming_payment",
  "enabled": true,
  "operation": "created_and_enabled",
  "db_record_id": 1
}
```

Response (warning - нет URL):
```json
{
  "status": "warning",
  "payment_type": "incoming_payment",
  "enabled": true,
  "operation": "skipped_no_webhook_url",
  "message": "Webhook URL не настроен. Запустите ngrok..."
}
```

### 3. Отключение вебхука
```bash
curl -X POST http://localhost:8000/api/hooks/auto-link-toggle \
  -H "Content-Type: application/json" \
  -d '{
    "payment_type": "incoming_payment",
    "enabled": false
  }'
```

Response:
```json
{
  "status": "ok",
  "payment_type": "incoming_payment",
  "enabled": false,
  "operation": "disabled",
  "db_record_id": 1
}
```

---

## Диаграммы последовательности

### Включение вебхука (успешный сценарий)
```
User -> API: POST /auto-link-toggle {payment_type, enabled=true}
API -> Service: toggle_webhook()
Service -> Service: validate_config()
Service -> Factory: create_operation(enabled=true)
Factory -> Service: EnableWebhookOperation
Service -> Operation: execute()
Operation -> Client: find_webhook()
Client -> МойСклад: GET /entity/webhook
МойСклад -> Client: []
Client -> Operation: None
Operation -> Client: create_webhook()
Client -> МойСклад: POST /entity/webhook
МойСклад -> Client: {id, href, enabled=true}
Client -> Operation: webhook_data
Operation -> Service: WebhookOperationResult
Service -> UoW: webhooks.upsert(entity)
UoW -> Repository: upsert()
Repository -> DB: INSERT/UPDATE
DB -> Repository: success
Repository -> UoW: saved_entity
UoW -> Service: commit()
Service -> API: result
API -> User: {status: ok, operation: created_and_enabled}
```

---

## Тестирование

### Unit тесты
```python
# Тестирование репозитория
async def test_webhook_repository_upsert():
    entity = WebhookEntity(...)
    saved = await repository.upsert(entity)
    assert saved.id is not None

# Тестирование операций
async def test_enable_webhook_operation():
    operation = EnableWebhookOperation(mock_client, config)
    result = await operation.execute()
    assert result.success is True
```

### Integration тесты
```python
# Тестирование эндпоинта
async def test_auto_link_toggle_endpoint(client: AsyncClient):
    response = await client.post(
        "/api/hooks/auto-link-toggle",
        json={"payment_type": "incoming_payment", "enabled": True}
    )
    assert response.status_code == 200
```

---

## Расширение функционала

### Добавление нового типа операции

1. Создать новый класс операции:
```python
class CustomWebhookOperation(WebhookOperation):
    async def execute(self) -> WebhookOperationResult:
        # Реализация
```

2. Расширить фабрику:
```python
class WebhookOperationFactory:
    @staticmethod
    def create_operation(...) -> WebhookOperation:
        if custom_condition:
            return CustomWebhookOperation(...)
        # ...
```

### Добавление нового репозитория

1. Создать класс репозитория:
```python
class NewRepository(AbstractRepository[Entity]):
    async def get_by_id(self, entity_id: int) -> Optional[Entity]:
        # Реализация
```

2. Добавить в UoW:
```python
class UnitOfWork:
    @property
    def new_repo(self) -> NewRepository:
        if self._new_repo is None:
            self._new_repo = NewRepository(self._session)
        return self._new_repo
```

---

## Troubleshooting

### Ошибка: "Webhook URL не настроен"
**Причина:** Не задана переменная `APL_MS_WEBHOOK_URL`
**Решение:**
1. В режиме разработки: запустить ngrok
2. Установить URL: `export APL_MS_WEBHOOK_URL=https://xxx.ngrok.io/api/hooks/moysklad/webhook`
3. Перезапустить сервер

### Ошибка: "MoySklad credentials не настроены"
**Причина:** Не заданы `APL_MS_LOGIN` и `APL_MS_PASSWORD`
**Решение:**
1. Установить через API: `POST /api/auth/ms/credentials`
2. Или через ENV: `APL_MS_LOGIN` и `APL_MS_PASSWORD`

### Ошибка: MoySkladAPIError (502)
**Причина:** Ошибка взаимодействия с API МойСклад
**Решение:**
1. Проверить доступность API МойСклад
2. Проверить корректность credentials
3. Проверить логи для деталей ошибки

---

## Roadmap

### Планируемые функции

1. **Обработка входящих вебхуков**
   - Парсинг событий CREATE платежей
   - Получение полных данных через API
   - Поиск связанных заказов
   - Автоматическая привязка

2. **История операций**
   - Логирование всех webhook events
   - Сохранение в БД
   - API для просмотра истории

3. **Мониторинг и метрики**
   - Статистика обработанных событий
   - Успешность привязок
   - Время обработки

4. **Уведомления**
   - Email при ошибках
   - Telegram уведомления
   - Webhook callbacks

---

## Контакты и поддержка

Для вопросов и предложений создавайте issues в репозитории.

**GitHub:** https://github.com/RomanL91/AutomaticPaymentLinking
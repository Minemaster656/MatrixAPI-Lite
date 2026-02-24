# Milestone Code Audit Report

**Дата:** 2026-02-23  
**Версия:** 0.1.0  
**Аудитор:** AI Code Review

---

## Критические уязвимости

### 1. XSS через Markdown рендеринг (HIGH)
**Файл:** `static/js/chat.js:414`

```javascript
const renderedText = marked.parse(data.text);
```

**Проблема:** `marked.parse()` не санитизирует HTML по умолчанию. Пользователь может отправить:
```html
<script>alert('xss')</script>
<img src=x onerror=alert('xss')>
```

**Решение:** Добавить санитизацию:
```javascript
const renderedText = DOMPurify.sanitize(marked.parse(data.text));
```

---

### 2. WebSocket без обязательной аутентификации (HIGH)
**Файл:** `app/routers/websocket/chat.py:24-56`

**Проблема:** 
- WebSocket endpoint `/ws/chat` принимает любые соединения
- Аутентификация через token опциональна
- Анонимные пользователи могут отправлять сообщения

**Решение:** Требовать token при подключении:
```python
@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str) -> None:
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
```

---

### 3. Нет валидации URL протоколов (MEDIUM)
**Файл:** `app/schemas/schemas.py:54,93,116`

**Проблема:** Поля `avatar_url`, `background_url` принимают любые строки, включая:
```javascript
javascript:alert('xss')
data:text/html,<script>alert('xss')</script>
```

**Решение:** Добавить валидатор:
```python
from pydantic import field_validator
import re

@field_validator('avatar_url')
@classmethod
def validate_url(cls, v):
    if v and not re.match(r'^https?://', v):
        raise ValueError('URL must start with http:// or https://')
    return v
```

---

## Потенциальные баги

### 1. AttributeError при несуществующей локации
**Файл:** `app/routers/websocket/chat.py:275-277`

```python
location = session.get(Location, location_id)
# ...
"location_name": location.name if location else "",
```

Если `location` is None, но код продолжает работу, возможны ошибки.

**Решение:** Добавить проверку:
```python
if not location:
    await websocket.send_json({"type": "error", "message": "Location not found"})
    return
```

---

### 2. Race condition в генерации ID сообщений
**Файл:** `app/services/message_store.py:11-13,23`

```python
def generate_id(self) -> int:
    self._message_id += 1
    return self._message_id
```

При конкурентных запросах возможны дублирующиеся ID.

**Решение:** Использовать `threading.Lock` или UUID:
```python
import threading

class MessageStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._message_id = 0
    
    def generate_id(self) -> int:
        with self._lock:
            self._message_id += 1
            return self._message_id
```

---

### 3. SECRET_KEY регенерируется при каждом запуске
**Файл:** `app/core/auth.py:19`

```python
SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
```

**Проблема:** Без явной установки SECRET_KEY все токены становятся недействительными после перезапуска.

**Решение:** Требовать SECRET_KEY в продакшене:
```python
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required")
```

---

### 4. Необработанные исключения в WebSocket handlers
**Файл:** `app/routers/websocket/chat.py`

Обработчики `_handle_*` не имеют try-except блоков. Ошибка может разорвать соединение без уведомления клиента.

**Решение:** Обернуть в try-except:
```python
async def _handle_message(websocket: WebSocket, data: dict) -> None:
    try:
        # ... existing code
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
```

---

## Необработанные кейсы

### 1. Отсутствие лимита на количество персонажей
Пользователь может создать неограниченное количество персонажей, что может привести к DoS.

**Рекомендация:** Добавить лимит (например, 10 персонажей на пользователя).

---

### 2. Нет проверки дублирования имен персонажей
Можно создать двух персонажей с одинаковым именем.

**Рекомендация:** Добавить unique constraint или проверку.

---

### 3. Отсутствие rate limiting для WebSocket
WebSocket соединения не имеют ограничения на количество сообщений.

**Рекомендация:** Добавить throttling на уровне WebSocket.

---

### 4. Сообщения не удаляются при удалении персонажа
`message_store` хранит ссылки на персонажей, но при удалении персонажа сообщения остаются.

---

### 5. Нет пагинации для истории сообщений
При большом количестве сообщений API вернет максимум 100, но нет способа получить более старые.

---

### 6. Хранение токена в localStorage (Frontend)
**Файл:** `static/js/chat.js:11`

```javascript
return localStorage.getItem('access_token');
```

Уязвимо к XSS атакам. Рекомендуется использовать httpOnly cookies.

---

## Оверинжиниринг

### 1. Дублирование get_current_user (auth.py:34-81, 110-161)
Функции `get_current_user` и `get_current_user_with_refresh` содержат почти идентичный код.

**Рекомендация:** Вынести общую логику:
```python
async def _get_user_from_token(token: str) -> tuple[User, dict]:
    payload = decode_access_token(token)
    # ... shared logic
    return user, payload

async def get_current_user(credentials) -> User:
    user, _ = await _get_user_from_token(credentials.credentials)
    return user

async def get_current_user_with_refresh(credentials) -> tuple[User, str | None]:
    user, payload = await _get_user_from_token(credentials.credentials)
    new_token = create_access_token(user.id) if should_refresh_token(payload) else None
    return user, new_token
```

---

### 2. ConnectionInfo с избыточными Optional полями
**Файл:** `app/core/websocket_manager.py:6-14`

Поля `ooc_username`, `character_name` создают сложную логику для определения имени отправителя.

**Рекомендация:** Упростить модель, используя единое поле `display_name`.

---

## Отсутствующие тесты

1. **WebSocket эндпоинты** - нет интеграционных тестов для `/ws/chat`
2. **XSS атаки** - нет тестов на инъекции
3. **Rate limiting** - неполное покрытие
4. **Конкурентный доступ** - нет тестов на race conditions

---

## Рекомендации по приоритету

| Приоритет | Проблема | Файл |
|-----------|----------|------|
| P0 | XSS через marked.parse | chat.js:414 |
| P0 | WebSocket без аутентификации | chat.py:24 |
| P1 | Валидация URL протоколов | schemas.py |
| P1 | SECRET_KEY регенерация | auth.py:19 |
| P2 | Race condition ID | message_store.py |
| P2 | Необработанные исключения WS | chat.py |
| P3 | Оверинжиниринг auth | auth.py |

---

## Итог

Код проекта имеет хорошую структуру и документацию, однако требует внимания к безопасности, особенно в части WebSocket аутентификации и XSS защиты. Критические уязвимости должны быть исправлены перед production деплоем.

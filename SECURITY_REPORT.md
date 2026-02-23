# SECURITY AUDIT REPORT

**Project:** MatrixAPI (RP-движок)  
**Date:** 2026-02-23  
**Auditor:** Security Analysis  
**Scope:** HTTP API, WebSocket API, Authentication

---

## EXECUTIVE SUMMARY

Проведен аудит безопасности API. Обнаружено **3 критических**, **2 высоких** и **4 средних** уязвимости. Две критические уязвимости успешно воспроизведены (proof of concept подтвержден).

---

## CRITICAL VULNERABILITIES

### 1. WebSocket: Полное отсутствие аутентификации
**File:** `app/routers/websocket/chat.py:24-56`  
**Severity:** CRITICAL  
**Status:** ❌ Not Fixed (requires refactoring)

WebSocket endpoint `/ws/chat` не требует аутентификации.

```python
@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    await manager.connect(websocket, username="Anonymous")  # Анонимное подключение
```

**Impact:**
- Любой может подключиться без токена
- Невозможно определить кто отправляет сообщения
- Нет привязки к конкретному пользователю

**PoC:** Подключение к ws://localhost:33217/ws/chat без токена - успешно.

---

### 2. WebSocket: Способность выдать себя за любого персонажа (CONFIRMED & FIXED)
**File:** `app/routers/websocket/chat.py:157-188`  
**Severity:** CRITICAL  
**Status:** ✅ FIXED

Обработчик `set_character` принимал `character_id` от клиента БЕЗ проверки владельца.

**PoC (до фикса):**
```bash
# Отправлено: {"type": "set_character", "character_id": 1, "character_name": "VictimChar"}
# Получено: {"type":"character_set","character_name":"VictimChar","avatar_url":"/static/assets/img/builtin_avatars/..."}
```

**Fix:** Добавлена проверка owner_id через JWT токен:
- Клиент передаёт `token` в set_character
- Сервер декодирует токен, получает user_id
- Проверяет: `character.owner_id == user_id`
- Возвращает ошибку "Character does not belong to you" если не совпадает

**PoC (после фикса):**
```bash
# Отправлено: {"type": "set_character", "character_id": 1, "token": "attacker_token"}
# Получено: {"type":"error","message":"Character does not belong to you"}
```

---

### 3. HTTP: Создание локаций без аутентификации (CONFIRMED & FIXED)
**File:** `app/routers/http/locations.py:25-52`  
**Severity:** CRITICAL  
**Status:** ✅ FIXED

Эндпоинт `POST /api/locations` не был защищен.

**PoC (до фикса):**
```bash
curl -X POST http://localhost:33217/api/locations \
  -d '{"name":"Hacked Location","description":"Created by attacker"}'
# Response: {"name":"Hacked Location",...,"id":4}
```

**Fix:** Добавлена аутентификация через Depends(get_current_user) и использование user.id в функции.

**PoC (после фикса):**
```bash
curl -X POST http://localhost:33217/api/locations \
  -d '{"name":"Hacked"}'
# Response: HTTP 401 Unauthorized
```

---

## HIGH VULNERABILITIES

### 4. Нет rate limiting
**Severity:** HIGH  
**Status:** ❌ Not Fixed

На всех эндпоинтах отсутствует rate limiting:
- Brute force на `/auth/login` - возможен
- Flood сообщений через WebSocket
- DoS атаки на создание объектов

**Fix:** Использовать SlowAPI или aiohttp-limiter.

---

### 5. WebSocket: Приватные сообщения без верификации
**File:** `app/routers/websocket/chat.py:117-154`  
**Severity:** MEDIUM-HIGH  
**Status:** ❌ Not Fixed

Можно отправлять "приватные" сообщения от любого имени, так как отправитель не верифицирован через JWT.

---

## MEDIUM VULNERABILITIES

### 6. SECRET_KEY не персистентный
**File:** `app/core/auth.py:18`  
**Severity:** MEDIUM  
**Status:** ⚠️ Partially Fixed

```python
SECRET_KEY: str = secrets.token_urlsafe(32)  # Генерируется при каждом запуске
```

**Impact:** 
- Все токены инвалидируются при рестарте
- Невозможен кластеринг без синхронизации ключа
- SECRET_KEY должен храниться в environment variables

---

### 7. Нет role-based access control
**Severity:** MEDIUM  
**Status:** ❌ Not Fixed

Нет разделения на администраторов и обычных пользователей. Все операции (кроме создания персонажей) доступны любому аутентифицированному пользователю.

---

### 8. Смена email без верификации
**File:** `app/routers/auth.py:273-311`  
**Severity:** MEDIUM  
**Status:** ❌ Not Fixed

При update_me можно изменить email без подтверждения паролем.

---

### 9. Раскрытие деталей в ошибках
**Severity:** LOW  
**Status:** ❌ Not Fixed

Детали internal errors могут раскрывать структуру БД и версии пакетов.

---

## LOW/INFO ISSUES

### 10. Нет sanitization на XSS
**Severity:** LOW  
**Status:** INFO

WebSocket сообщения сохраняются как есть. Фронтенд должен экранировать HTML.

---

### 11. Лимиты на размер данных
**Severity:** INFO  

Message.text max_length=5000 - может быть слишком большим.

---

## SUMMARY

| Severity | Count | Fixed | Not Fixed |
|----------|-------|-------|-----------|
| CRITICAL | 3 | 2 | 1 |
| HIGH | 2 | 0 | 2 |
| MEDIUM | 4 | 0 | 4 |
| LOW/INFO | 2 | 0 | 2 |

---

## FIXES APPLIED

### Fix 1: Character ownership validation (websocket/chat.py)
✅ Добавлена проверка owner_id при set_character через JWT токен.

### Fix 2: Location creation requires auth (locations.py)
✅ Добавлена аутентификация и использование user.id.

---

## REMAINING ISSUES TO FIX

1. **WebSocket аутентификация** - требует рефакторинга handshake
2. **Rate limiting** - добавить SlowAPI
3. **SECRET_KEY в env** - вынести в environment
4. **RBAC** - добавить роли admin/user
5. **Email change verification** - требовать пароль при смене email

# План улучшений Hillhorn — детальная реализация

## Обзор

| Фаза | Фокус | Приоритет |
|------|-------|-----------|
| 1 | Быстрые wins | Сейчас |
| 2 | Качество поиска | Следующий |
| 3 | UX и агенты | Параллельно |
| 4 | DeepSeek/API | По мере необходимости |
| 5 | Масштабирование | При росте данных |

---

## Фаза 1. Быстрые wins

### 1.1 LRU для _search_cache (tools.py)

**Цель:** Ограничить рост памяти, избежать утечки при длительной работе MCP.

**Файл:** `tools.py`

**Действия:**
1. Заменить `_search_cache: Dict[tuple, Dict] = {}` на LRU-словарь.
2. Вариант A: `from functools import lru_cache` не подходит (async, mutable). Использовать `collections.OrderedDict` + ручная логика: при добавлении проверять `len(_search_cache) >= 100`, удалять самый старый (`popitem(last=False)`).
3. Вариант B: обёртка `_search_cache: OrderedDict` с `maxsize=100`. При `__setitem__` если `len >= 100`, `popitem(last=False)`.

**Код (псевдокод):**
```python
from collections import OrderedDict
SEARCH_CACHE_MAX = int(os.getenv("HILLHORN_SEARCH_CACHE_MAX", "100"))
_search_cache: OrderedDict = OrderedDict()

# В search_memory перед присвоением:
if cache_key in _search_cache:
    _search_cache.move_to_end(cache_key)  # LRU touch
    return _search_cache[cache_key]
# ... поиск ...
while len(_search_cache) >= SEARCH_CACHE_MAX:
    _search_cache.popitem(last=False)
_search_cache[cache_key] = out
```

---

### 1.2 Кроссплатформенность snake (snake.py)

**Цель:** snake.py работает на Linux/macOS без msvcrt.

**Файл:** `snake.py`

**Действия:**
1. Проверять `os.name == "nt"` или `sys.platform`.
2. Windows: `msvcrt.kbhit()`, `msvcrt.getch()`.
3. Linux/macOS: `import sys`, `import tty`, `import termios`; `select.select([sys.stdin], [], [], 0)` для kbhit; `sys.stdin.read(1)` для getch. Обернуть в try/except, fallback — «Используйте Windows или установите tty».
4. Альтернатива: `pip install getch` (или `pynput`) — единый API. Добавить в requirements.txt при необходимости.

**Структура:**
```python
def _getch():
    if os.name == "nt":
        return msvcrt.getch().decode("utf-8", errors="ignore")
    try:
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except ImportError:
        return ""
```

---

### 1.3 Уточнённые tool descriptions (hillhorn_mcp_server.py)

**Цель:** Ясные, короткие описания для лучшего выбора агентами.

**Файл:** `hillhorn_mcp_server.py`

**Действия:**
- `hillhorn_get_context`: «Получить контекст проекта. Вызывать ПЕРВЫМ в сессии. project_id=корень проекта.»
- `hillhorn_search`: «Поиск по памяти. Вызывать перед read_file. query=тема, kind_filter=doc|code|conversation.»
- `hillhorn_add_turn`: «Сохранить факт/решение. После важного. kind=summary|doc|code.»
- `hillhorn_consult_with_memory`: «DeepSeek с памятью. planner — сложные задачи, reviewer — ревью кода.»

---

## Фаза 2. Качество поиска

### 2.1 HF embedding по умолчанию (embeddings.py)

**Цель:** Лучшее качество эмбеддингов при наличии HF_TOKEN.

**Файл:** `embeddings.py` (или там, где get_embedding)

**Действия:**
1. Проверить текущую логику: hash vs sentence-transformers.
2. Если HF_TOKEN не задан — логировать: «HF_TOKEN не задан, используются hash-эмбеддинги (низкое качество)».
3. Рекомендуемая модель: `sentence-transformers/all-MiniLM-L6-v2` (384 dim). Если EMBED_DIM=32 — обрезать/паддить.
4. Добавить в README: «Для лучшего поиска задайте HF_TOKEN и HF_EMBED_MODEL в .env».

---

### 2.2 Platt scaling для confidence

**Цель:** Калибровка agreement_ratio (ECE 0.14 → 0.03).

**Файлы:** `tools.py`, возможно `nwf_memory_utils.py`

**Действия:**
1. Формула Platt: `p = 1 / (1 + exp(A * score + B))`. Для agreement_ratio: `score = agreement_ratio`.
2. Нужна калибровочная выборка: пары (agreement_ratio, was_correct). Пока можно использовать эвристику: `calibrated = min(0.99, max(0.01, agreement_ratio * 1.2 - 0.1))` как временную.
3. Полная калибровка: собрать логи (query, agreement_ratio, feedback), обучить A, B на них.
4. Добавить опцию `calibrate_confidence=True` в search_memory, возвращать `confidence_calibrated` рядом с agreement_ratio.

---

### 2.3 Автоматический boost alpha при использовании

**Цель:** Увеличивать alpha зарядов при успешном использовании.

**Файлы:** `hillhorn_mcp_server.py`, `deepseek_gateway.py`, `nwf_memory_utils.py`

**Действия:**
1. В `hillhorn_consult_with_memory` и `hillhorn_consult_agent` после успешного ответа знать, какие индексы зарядов попали в context.
2. Проблема: search возвращает результаты, но не индексы в Field. Решение: расширить `search_memory` — опционально возвращать `_indices` в ответе (или отдельный endpoint).
3. Альтернатива: в `_search_memory_direct` сохранять индексы в заголовке/спецполе. При consult — передавать в Gateway. Gateway после успешного ответа вызывает `boost_charges_alpha(indices, delta=0.1)`.
4. Упрощённый вариант: при `hillhorn_add_turn` после consult не бустить; бустить только при явном действии (например, кнопка «Полезно»). Отложить полную автоматику.

---

## Фаза 3. UX и агенты

### 3.1 Напоминание о первом вызове

**Цель:** Если агент не вызвал hillhorn_get_context — напомнить.

**Файл:** `.cursorrules` или AGENTS.md

**Действия:**
1. Добавить в .cursorrules: «Если в первых 2 сообщениях не вызывал hillhorn_get_context — перед read_file напомни себе: «Сначала вызови hillhorn_get_context» и сделай это.»
2. В AGENTS.md: отдельный блок «Критичная проверка: перед read_file всегда должен быть hillhorn_get_context или hillhorn_search.»

---

### 3.2 HILLHORN_MODE=minimal — скрыть consult

**Цель:** В режиме minimal не предлагать consult-инструменты.

**Файл:** `hillhorn_mcp_server.py`

**Действия:**
1. Читать `HILLHORN_MODE` из os.getenv.
2. Если `minimal` — не регистрировать `hillhorn_consult_agent`, `hillhorn_consult_with_memory` (или регистрировать, но в description писать «Недоступно в minimal» и возвращать сообщение).
3. Вариант проще: в description consult-инструментов: «Требует HILLHORN_MODE=full. В minimal недоступен.»

---

### 3.3 Краткие tool descriptions (уже в 1.3)

См. п. 1.3.

---

## Фаза 4. DeepSeek / API

### 4.1 Таймауты и retry

**Файл:** `hillhorn_mcp_server.py`, `deepseek_gateway.py`

**Действия:**
1. Текущий timeout=90 для Gateway. Добавить `DEEPSEEK_PLANNER_TIMEOUT=120`, `DEEPSEEK_REVIEWER_TIMEOUT=60` — planner может быть дольше.
2. Retry: exponential backoff. Сейчас 2 попытки, 2 сек. Вариант: 3 попытки, задержки 2, 4, 8 сек.
3. В `_post`: `for attempt in range(max_retries): await asyncio.sleep(base_delay * (2 ** attempt))`.

---

### 4.2 Streaming для reviewer (опционально)

**Файлы:** `deepseek_gateway.py`, `hillhorn_mcp_server.py`

**Действия:**
1. DeepSeek API поддерживает stream. Для reviewer: `stream=True` в запросе.
2. MCP/JSON-RPC: stream сложнее. Вариант — накопить chunks и вернуть целиком, но отдавать промежуточно через другой механизм (если поддерживается).
3. Приоритет низкий — можно отложить.

---

### 4.3 Кеш типовых planner-запросов

**Файл:** `deepseek_gateway.py` или отдельный модуль `gateway_cache.py`

**Действия:**
1. Ключ: `hash(prompt[:500] + agent_type)`.
2. Хранить в файле или in-memory: `{key: response}`. TTL 24 часа или без TTL (планы редко меняются).
3. Перед вызовом API проверять кеш. При попадании — возвращать без запроса.
4. Ограничение: только для planner, только для коротких типовых промптов.

---

## Фаза 5. Масштабирование

### 5.1 PQ (Product Quantization)

**Условие:** Объём данных > 50k зарядов.

**Файлы:** интеграция с nwf-core, если есть поддержка FAISS PQ.

**Действия:**
1. Проверить nwf-core: есть ли `Field` с backend=faiss_pq.
2. При migrate: экспорт текущего Field, импорт в PQ-версию.
3. Документировать в плане, не реализовывать до роста данных.

---

### 5.2 HNSW

**Условие:** Поиск > 100ms при 100k+ зарядов.

**Действия:**
1. nwf-core / FAISS HNSW.
2. Аналогично PQ — отложить до появления необходимости.

---

## Фаза 6. Надёжность и наблюдаемость

### 6.1 Структурированное логирование

**Файл:** `hillhorn_mcp_server.py`, возможно новый `hillhorn_logging.py`

**Действия:**
1. Формат: `{"ts": ..., "tool": "hillhorn_search", "duration_ms": 120, "cache_hit": true, "results_count": 5}`.
2. Писать в `hillhorn_calls.jsonl` (уже есть) — добавить поле `cache_hit`.
3. В `tools.search_memory`: при возврате из кеша — помечать в лог `cache_hit=True`.

---

### 6.2 Health-check endpoint

**Файл:** `deepseek_gateway.py`

**Действия:**
1. `@app.get("/health")` → JSON `{"status": "ok", "nwf": "ok"|"missing", "embed": "ok"|"hash"}`.
2. Проверки: `NWF_MEMORY_PATH/meta.json` существует; embeddings — если HF, пинг модели.

---

### 6.3 Метрики кеша

**Файл:** `tools.py`

**Действия:**
1. Счётчики: `_cache_hits`, `_cache_misses`.
2. Функция `get_cache_stats() -> {"hits": N, "misses": M, "hit_rate": ...}`.
3. Опционально: endpoint `/v1/stats` в Gateway, возвращающий эти метрики.

---

## Порядок внедрения (по неделям)

| Неделя | Задачи | Статус |
|--------|--------|--------|
| 1 | 1.1 LRU cache, 1.3 tool descriptions, 3.1 напоминание | Реализовано |
| 2 | 1.2 кроссплатформенность snake, 6.1 cache_hit в лог | Реализовано |
| 3 | 6.2 health-check (nwf, embed, cache), 4.1 retry exponential, 6.3 get_cache_stats | Реализовано |
| 4 | 2.1 HF embedding | Ожидает |
| 5+ | 2.2 Platt scaling, 2.3 boost alpha, 4.3 кеш planner | По необходимости |

---

## Чек-лист перед релизом каждого пункта

- [ ] Тест: `python hillhorn_checks/run_tasks.py`
- [ ] Тест: `python snake.py` (если меняли)
- [ ] Проверка: search возвращает те же результаты (при оптимизациях)
- [ ] Обновить docs при новых env-переменных

# Integration-проверки

| Связь компонентов | Что может сломаться | Как воспроизводим | Ожидаемый результат | Подтверждение |
|---|---|---|---|---|
| FastAPI → входной контракт | Нет ключа `diff` или тип неверный | `POST /api/reviews` с `{}` и `{"diff": 123}` | Запрос не принимается как успешный review и LLM не вызывается; точный 4xx фиксируется отдельным API-контрактом до реализации | API integration test + счётчик вызовов fake LLM |
| API → ReviewService → fake LLM | В LLM уходит не тот diff/Context Pack | Fake LLM сохраняет полученный prompt; отправить известный diff | Prompt содержит заданный Master Prompt и ровно переданный diff | Assert по captured prompt |
| ReviewService → LLM error handling | Провайдер выбрасывает исключение | Fake LLM → `RuntimeError` | Endpoint не возвращает 2xx с валидным review; отдельно фиксируются ошибка уровня сервиса и фактическое HTTP-преобразование | Integration test |
| LLM → Result Guard | Модель нарушает структуру | Fake LLM возвращает 4 риска или risk без evidence | Guard отклоняет результат и не передаёт его как готовый review | Integration test |

## Как использовали AI

- Строка в [`prompts.md`](prompts.md): `P1-03`.
- Что проверил студент и какие исправления поручил агенту: проверки построены на границах компонентов из ADR; там, где production-код ещё не определён, ожидаемый HTTP-код оставлен частью будущего API-контракта, а не выдан за текущий факт.

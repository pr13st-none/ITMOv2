# Ход проверки

Проверка выполнена на Windows 11 с локальными OpenCode, Ollama и `itmo-practice4`.

1. OpenCode применил правила из `AGENTS.md` и назвал runner, TDD-порядок, источник валидации и запрет `git push` (`rules-live.jsonl`).
2. Агент вызвал tool `skill` и загрузил `test-driven-development` (`skill-live.jsonl`).
3. Агент дважды вызвал MCP tool `review-contract_check_review_payload`: корректный payload принят, пустой отклонён с `diff_required` (`mcp-opencode-live.jsonl`).
4. По готовому TDD skill агент создал `tests/test_null_diff.py`. Hook запустил runner и вернул `Automatic check: FAIL`: `DID NOT RAISE ContractError`, `1 failed, 7 passed` (`hook-red-live.jsonl`). Это падение из-за отсутствующей проверки NUL, не синтаксическая ошибка.
5. Агент изменил валидатор, не меняя тест. Первая правка ещё давала FAIL, следующая — `Automatic check: PASS`, `8 passed`; затем агент отдельно запустил runner (`hook-green-live.jsonl`).
6. После green убрано дублирование проверки и добавлены граничные проверки и настоящий MCP stdio-тест. Финальный `python check.py`: `16 passed` (`environment-live.json`).

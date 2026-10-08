# Ход проверки

Проверка выполнена на Windows 11 с локальными OpenCode, Ollama и `itmo-practice4`.

1. OpenCode применил правила из `AGENTS.md` и назвал runner, TDD-порядок, источник валидации и запрет `git push` (`rules-live.jsonl`).
2. Агент вызвал tool `skill` и загрузил `test-driven-development` (`skill-live.jsonl`).
3. Агент дважды вызвал MCP tool `review-contract_check_review_payload`: корректный payload принят, пустой отклонён с `diff_required` (`mcp-opencode-live.jsonl`).
4. Агент записал временный падающий тест; hook добавил к результату записи `Automatic check: FAIL` (`hook-red-live.jsonl`).
5. Агент заменил `assert False` на `assert True`; тот же hook вернул `Automatic check: PASS` (`hook-green-live.jsonl`).
6. Временный тест удалён. Финальный `python check.py`: `7 passed` (`environment-live.json`).

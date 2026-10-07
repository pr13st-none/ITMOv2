[
  {
    "id": "Q1",
    "question": "Как запустить тесты проекта? Укажи источник и строки.",
    "expected": "make test; README.md:6 и Makefile:1-3"
  },
  {
    "id": "Q2",
    "question": "Что произойдёт при subscribe(\" \"), и где это проверяется?",
    "expected": "ValueError для пустого имени; service.py:4-7, test_service.py:13-15"
  },
  {
    "id": "Q3",
    "question": "Где реализован unsubscribe? Покажи функцию и тест.",
    "expected": "Ложная предпосылка: unsubscribe отсутствует; service.py:1-8, test_service.py:1-24"
  },
  {
    "id": "Q4",
    "question": "Какая CI-система запускает тесты проекта? Укажи конфигурационный файл.",
    "expected": "В доступном demo нет сведений о CI; README.md:1-7 и Makefile:1-3 не содержат CI-конфигурации"
  },
  {
    "id": "Q5",
    "question": "Сохраняются ли подписки после перезапуска процесса? Подтверди кодом.",
    "expected": "Нет: subscribers — обычный set в памяти процесса; README.md:2, service.py:1"
  }
]

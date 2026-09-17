# Автотесты REST API Яндекс Диска

Проект на Python, Pytest и Requests для тестирования REST API Яндекс Диска. Unit-тесты проверяют HTTP-клиент без сетевых запросов, интеграционные тесты работают с реальным API.

## Что проверяется

| Метод | Эндпоинт | Сценарий |
|---|---|---|
| GET | `/v1/disk` | Получение данных о Диске |
| GET | `/v1/disk/resources` | Получение метаданных папки |
| PUT | `/v1/disk/resources` | Создание папки |
| POST | `/v1/disk/resources/copy` | Копирование ресурса |
| DELETE | `/v1/disk/resources` | Удаление ресурса |
| GET | `/v1/disk/operations/{id}` | Ожидание асинхронной операции |

## Требования

- Python 3.10 или новее;
- тестовый аккаунт Яндекса с доступом к Диску;
- OAuth-токен с правами чтения и записи — только для интеграционных тестов.

Используйте отдельный тестовый аккаунт. Не добавляйте токен в код, коммиты или логи.

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Запуск тестов

Unit-тесты без доступа к сети:

```bash
pytest -m "not integration"
```

Интеграционные тесты:

```bash
export YANDEX_DISK_TOKEN="токен-тестового-аккаунта"
pytest -m integration
```

Все тесты:

```bash
pytest
```

Без `YANDEX_DISK_TOKEN` интеграционные тесты будут пропущены. Каждый интеграционный прогон создаёт уникальную папку `disk:/api-autotests-<id>` и удаляет её после завершения.

## Переменные окружения

| Переменная | Значение по умолчанию |
|---|---|
| `YANDEX_DISK_TOKEN` | Не задано |
| `YANDEX_DISK_BASE_URL` | `https://cloud-api.yandex.net/v1/disk` |
| `YANDEX_DISK_TEST_ROOT_PREFIX` | `disk:/api-autotests` |
| `YANDEX_DISK_TIMEOUT_SECONDS` | `15` |
| `YANDEX_DISK_OPERATION_TIMEOUT_SECONDS` | `30` |

## Проверка качества

```bash
ruff check .
pytest --cov --cov-report=term-missing
```

Также доступны команды `make unit`, `make integration`, `make test` и `make lint`.

## GitHub Actions

Workflow `.github/workflows/tests.yml` запускает линтер и unit-тесты на Python 3.10 и 3.12. Интеграционные тесты используют секрет `YANDEX_DISK_TOKEN`; без него они пропускаются.

Документация: [REST API Яндекс Диска](https://yandex.ru/dev/disk-api/doc/ru/).

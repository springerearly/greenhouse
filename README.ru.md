# Проект управления теплицей

Это веб-приложение для мониторинга и управления средой теплицы с использованием Raspberry Pi. Оно включает в себя бэкенд на FastAPI и фронтенд на React.

## Структура проекта

- `api/`: Бэкенд-приложение на FastAPI.
- `client/`: Фронтенд-приложение на React.
- `legacy/`: Исходный код оригинального проекта на Django.

---

## Запуск приложения

Вы можете запустить приложение вручную или с помощью Docker Compose.

### Ручная настройка (для разработки на Raspberry Pi)

#### 1. Настройка базы данных PostgreSQL

-   Убедитесь, что PostgreSQL установлен и запущен.
-   Создайте новую базу данных и пользователя. Используя `psql`:

    ```bash
    sudo -u postgres psql
    CREATE DATABASE greenhousedb;
    CREATE USER user WITH PASSWORD 'password'; -- Замените на ваши учетные данные
    GRANT ALL PRIVILEGES ON DATABASE greenhousedb TO user;
    \q
    ```
-   **Важно:** Обновите `SQLALCHEMY_DATABASE_URL` в файле `api/database.py` вашими учетными данными PostgreSQL, если вы не используете Docker.

#### 2. Запуск бэкенда (FastAPI)

-   Перейдите в директорию `api`:
    ```bash
    cd api
    ```
-   Создайте виртуальное окружение и установите зависимости:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
-   Запустите приложение:
    ```bash
    uvicorn main:app --reload
    ```
-   Бэкенд будет доступен по адресу `http://127.0.0.1:8000`. Документация API находится по адресу `http://127.0.0.1:8000/docs`.

#### 3. Запуск фронтенда (React)

-   Откройте новое окно терминала.
-   Перейдите в директорию `client`:
    ```bash
    cd client
    ```
-   Установите зависимости:
    ```bash
    npm install
    ```
-   Запустите приложение:
    ```bash
    npm start
    ```
-   Фронтенд будет доступен по адресу `http://localhost:3000`.

---

### Настройка с помощью Docker Compose (Рекомендуется)

Это самый простой способ запустить весь стек приложения.

#### Предварительные требования
-   Установленный [Docker](https://docs.docker.com/engine/install/).
-   Установленный [Docker Compose](https://docs.docker.com/compose/install/).

#### Запуск
1.  Из корневой директории проекта (`greenhouse`) выполните следующую команду:
    ```bash
    docker-compose up --build
    ```
2.  Приложение будет доступно по адресу `http://localhost`.
    -   Фронтенд на React обслуживается на порту 80.
    -   Бэкенд на FastAPI доступен на порту 8000.
    -   База данных PostgreSQL находится на порту 5432.

Чтобы остановить приложение, нажмите `Ctrl+C` в терминале, где запущен `docker-compose`, а затем выполните:
```bash
docker-compose down
```

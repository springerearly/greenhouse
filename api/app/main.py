from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine
from .routers import gpio, devices, sensors, automations, alerts, ws
from .services import device_poller

# Создаём все таблицы в БД
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Greenhouse Control API",
    description="API для управления теплицей: GPIO Raspberry Pi + ESP8266/ESP32 устройства",
    version="2.0.0",
)

# CORS — разрешаем запросы с React dev-сервера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(gpio.router)
app.include_router(devices.router)
app.include_router(sensors.router)
app.include_router(automations.router)
app.include_router(alerts.router)
app.include_router(ws.router)


@app.on_event("startup")
async def startup():
    """Инициализация при запуске приложения."""
    # GPIO пины Raspberry Pi
    gpio.startup_event()
    # Запуск опроса ESP-устройств
    device_poller.start_all_polling()


@app.on_event("shutdown")
async def shutdown():
    """Корректное завершение работы."""
    gpio.shutdown_event()
    device_poller.stop_all_polling()


@app.get("/")
def read_root():
    return {
        "message": "Greenhouse Control API v2.0",
        "docs": "/docs",
        "endpoints": {
            "gpio": "/gpio",
            "devices": "/devices",
            "sensors": "/sensors",
            "automations": "/automations",
            "alerts": "/alerts",
            "websocket": "/ws",
        },
    }

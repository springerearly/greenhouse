"""
GPIO роутер — управление пинами Raspberry Pi.

Поддерживаемые режимы пина:
  INPUT   — цифровой вход. Колбэки gpiozero мгновенно пушат изменение в WebSocket.
            Дополнительно работает фоновый watcher с интервалом 100мс (на случай
            если колбэк не сработал при быстром импульсе).
  OUTPUT  — цифровой выход. on() / off(). Состояние пушится в WS.
  PWM     — ШИМ-выход. value = 0.0…1.0. Работает на любом GPIO (программный PWM),
            на GPIO 12,13,18,19 — аппаратный PWM через pigpio pin factory.
            Значение пушится в WS в реальном времени.

Аппаратный PWM Raspberry Pi (BCM):
  GPIO12 — PWM0  (физический пин 32)
  GPIO13 — PWM1  (физический пин 33)
  GPIO18 — PWM0  (физический пин 12)  ← самый распространённый
  GPIO19 — PWM1  (физический пин 35)
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# ─── gpiozero import с mock-заглушками ────────────────────────────────────────
try:
    from gpiozero import DigitalOutputDevice, DigitalInputDevice, PWMOutputDevice
    from gpiozero.pins.pi import PiBoardInfo
    from gpiozero.exc import GPIOZeroError
    from gpiozero.devices import pi_info
    ON_PI = True
except ImportError:
    ON_PI = False

    class _MockBase:
        def __init__(self, pin, **kw):
            self.pin = pin
            self.value = 0
        def close(self): pass

    class DigitalOutputDevice(_MockBase):
        def on(self):  self.value = 1
        def off(self): self.value = 0

    class DigitalInputDevice(_MockBase):
        when_activated   = None
        when_deactivated = None

    class PWMOutputDevice(_MockBase):
        """Mock PWM: value = 0.0…1.0"""
        def __init__(self, pin, initial_value=0.0, **kw):
            super().__init__(pin)
            self.value = initial_value

    class GPIOZeroError(Exception):
        pass

# ─── Аппаратные PWM пины (BCM нумерация) ────────────────────────────────────
HW_PWM_PINS = {12, 13, 18, 19}

# ─── Импорты проекта ─────────────────────────────────────────────────────────
from .. import models, schemas
from ..database import get_db, SessionLocal
from ..services.websocket_manager import manager as ws_manager

# ─── Хранилище объектов пинов в памяти ───────────────────────────────────────
# pin_number -> DigitalOutputDevice | DigitalInputDevice | PWMOutputDevice
devices: dict = {}

# Последние известные значения INPUT-пинов (для watcher'а)
_last_input_values: dict = {}

# Ссылка на фоновую задачу watcher'а
_watcher_task: asyncio.Task | None = None

router = APIRouter(prefix="/gpio", tags=["gpio"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_device(pin_number: int):
    return devices.get(pin_number)

def _is_hw_pwm(pin_number: int) -> bool:
    return pin_number in HW_PWM_PINS

def _close_pin(pin_number: int):
    """Безопасно закрыть и удалить объект пина."""
    dev = devices.pop(pin_number, None)
    if dev:
        try:
            dev.close()
        except Exception:
            pass
    _last_input_values.pop(pin_number, None)


# ─── WebSocket push helpers (coroutine-safe) ──────────────────────────────────

def _schedule_ws_push(pin_number: int, function: str, value: float):
    """
    Планирует WS-пуш из синхронного контекста (колбэки gpiozero).
    gpiozero вызывает колбэки из фонового потока, поэтому
    используем call_soon_threadsafe для безопасной передачи в event loop.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(
                    _push_gpio_state(pin_number, function, value)
                )
            )
    except RuntimeError:
        pass  # loop не запущен — игнорируем (startup/shutdown)

async def _push_gpio_state(pin_number: int, function: str, value: float):
    await ws_manager.broadcast("gpio", "state_change", {
        "pin": pin_number,
        "function": function,
        "value": value,
    })


# ─── INPUT колбэки (вызываются gpiozero мгновенно при смене уровня) ──────────

def _make_input_callbacks(pin_number: int, device: DigitalInputDevice):
    """Привязывает колбэки when_activated / when_deactivated к INPUT-пину."""
    if not ON_PI:
        return  # на mock-классах поле есть, но игнорируем

    def on_activated():
        _last_input_values[pin_number] = 1
        _schedule_ws_push(pin_number, "INPUT", 1)

    def on_deactivated():
        _last_input_values[pin_number] = 0
        _schedule_ws_push(pin_number, "INPUT", 0)

    device.when_activated   = on_activated
    device.when_deactivated = on_deactivated


# ─── Фоновый watcher ─────────────────────────────────────────────────────────

async def _gpio_watcher():
    """
    Опрашивает все INPUT-пины каждые 100мс.
    Служит резервом на случай если колбэк gpiozero пропустил импульс,
    а также является единственным механизмом обновления на mock-машинах.
    Пушит в WS только при изменении значения.
    """
    print("[GPIO Watcher] Started (100ms polling)")
    while True:
        try:
            for pin_number, dev in list(devices.items()):
                if isinstance(dev, DigitalInputDevice):
                    current = int(dev.value)
                    prev    = _last_input_values.get(pin_number)
                    if current != prev:
                        _last_input_values[pin_number] = current
                        await _push_gpio_state(pin_number, "INPUT", current)
        except Exception as e:
            print(f"[GPIO Watcher] Error: {e}")
        await asyncio.sleep(0.1)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/", response_model=List[schemas.GpioWithState])
def get_all_gpios_with_state(db: Session = Depends(get_db)):
    """Вернуть все настроенные пины с текущим состоянием."""
    gpios = db.query(models.Gpio).all()
    result = []
    for gpio in gpios:
        dev = _get_device(gpio.gpio_number)
        value     = None
        pwm_value = None

        if dev is not None:
            if isinstance(dev, PWMOutputDevice):
                pwm_value = round(dev.value, 3)
                value     = pwm_value
            elif hasattr(dev, 'value'):
                value = int(dev.value)

        result.append({
            "gpio_number":      gpio.gpio_number,
            "gpio_description": gpio.gpio_description,
            "gpio_function":    gpio.gpio_function,
            "value":            value,
            "pwm_value":        pwm_value,
        })
    return result


@router.get("/all-pins")
def get_all_pins_info():
    """Вернуть все доступные пины платы с флагом аппаратного PWM."""
    if not ON_PI:
        return [
            {
                "number": i,
                "header": "J8",
                "supports_hw_pwm": i in HW_PWM_PINS,
            }
            for i in range(1, 28)
        ]
    info = PiBoardInfo()
    return [
        {
            "number": pin.number,
            "header": pin.header,
            "supports_hw_pwm": pin.number in HW_PWM_PINS,
        }
        for pin in info.pins.values()
    ]


@router.post("/set-function")
async def set_function(gpio_config: schemas.GpioCreate, db: Session = Depends(get_db)):
    """
    Назначить функцию пину: INPUT | OUTPUT | PWM.
    На не-Pi машинах допускается PWM и OUTPUT (mock).
    INPUT на не-Pi машине отклоняется (нечего читать).
    """
    pin_number = gpio_config.gpio_number
    function   = gpio_config.gpio_function.upper()

    if function not in ("INPUT", "OUTPUT", "PWM"):
        raise HTTPException(
            status_code=400,
            detail="Допустимые значения function: INPUT, OUTPUT, PWM"
        )

    if function == "INPUT" and not ON_PI:
        raise HTTPException(
            status_code=500,
            detail="INPUT недоступен вне Raspberry Pi."
        )

    # Освобождаем старый объект пина
    _close_pin(pin_number)

    try:
        if function == "OUTPUT":
            dev = DigitalOutputDevice(pin_number)
        elif function == "INPUT":
            dev = DigitalInputDevice(pin_number, pull_up=True)
            _make_input_callbacks(pin_number, dev)
            _last_input_values[pin_number] = int(dev.value)
        else:  # PWM
            if ON_PI and _is_hw_pwm(pin_number):
                # Аппаратный PWM — требует pigpio pin factory
                # (раскомментировать если установлен pigpio)
                # from gpiozero.pins.pigpio import PiGPIOFactory
                # dev = PWMOutputDevice(pin_number, pin_factory=PiGPIOFactory())
                dev = PWMOutputDevice(pin_number, initial_value=0.0)
            else:
                dev = PWMOutputDevice(pin_number, initial_value=0.0)
    except GPIOZeroError as e:
        raise HTTPException(status_code=500, detail=f"GPIO error: {e}")

    devices[pin_number] = dev

    # Сохраняем в БД
    db_gpio = db.query(models.Gpio).filter(
        models.Gpio.gpio_number == pin_number
    ).first()
    if db_gpio:
        db_gpio.gpio_function   = function
        db_gpio.gpio_description = gpio_config.gpio_description
        if function != "PWM":
            db_gpio.pwm_value = None
    else:
        db_gpio = models.Gpio(
            gpio_number=pin_number,
            gpio_description=gpio_config.gpio_description,
            gpio_function=function,
            pwm_value=0.0 if function == "PWM" else None,
        )
        db.add(db_gpio)
    db.commit()

    # Уведомляем клиентов
    await ws_manager.broadcast("gpio", "function_changed", {
        "pin": pin_number,
        "function": function,
        "description": gpio_config.gpio_description,
        "supports_hw_pwm": _is_hw_pwm(pin_number),
    })

    return {"message": f"GPIO {pin_number} настроен как {function}"}


@router.post("/set-value")
async def set_value(gpio_value: schemas.GpioSetValue, db: Session = Depends(get_db)):
    """Установить значение OUTPUT пина (0 или 1)."""
    pin_number = gpio_value.gpio_number
    value      = gpio_value.value

    dev = _get_device(pin_number)

    if not ON_PI:
        # Mock-режим: создать OUTPUT если нет
        if dev is None:
            dev = DigitalOutputDevice(pin_number)
            devices[pin_number] = dev
        dev.on() if value == 1 else dev.off()
        await _push_gpio_state(pin_number, "OUTPUT", value)
        return {"message": f"GPIO {pin_number} -> {value} (mock)"}

    if dev is None:
        raise HTTPException(
            status_code=404,
            detail=f"GPIO {pin_number} не настроен. Сначала задайте функцию."
        )
    if isinstance(dev, PWMOutputDevice):
        raise HTTPException(
            status_code=400,
            detail=f"GPIO {pin_number} настроен как PWM. Используйте /set-pwm."
        )
    if not isinstance(dev, DigitalOutputDevice):
        raise HTTPException(
            status_code=400,
            detail=f"GPIO {pin_number} настроен как INPUT. Нельзя задать значение."
        )
    if value not in (0, 1):
        raise HTTPException(status_code=400, detail="value должен быть 0 или 1.")

    try:
        dev.on() if value == 1 else dev.off()
    except GPIOZeroError as e:
        raise HTTPException(status_code=500, detail=f"GPIO error: {e}")

    await _push_gpio_state(pin_number, "OUTPUT", value)
    return {"message": f"GPIO {pin_number} -> {value}"}


@router.post("/set-pwm")
async def set_pwm(gpio_pwm: schemas.GpioSetPwm, db: Session = Depends(get_db)):
    """
    Установить скважность PWM пина.
    value: 0.0 (0%) … 1.0 (100%).
    Фронтенд может отправлять 0-100 — мы нормализуем.
    """
    pin_number = gpio_pwm.gpio_number
    raw_value  = gpio_pwm.value

    # Нормализация: если пришло значение > 1, считаем что это проценты
    if raw_value > 1.0:
        raw_value = raw_value / 100.0
    value = max(0.0, min(1.0, raw_value))

    dev = _get_device(pin_number)

    if not ON_PI:
        # Mock-режим
        if dev is None or not isinstance(dev, PWMOutputDevice):
            dev = PWMOutputDevice(pin_number)
            devices[pin_number] = dev
        dev.value = value
        await _push_gpio_state(pin_number, "PWM", value)
        # Сохраняем в БД
        db_gpio = db.query(models.Gpio).filter(
            models.Gpio.gpio_number == pin_number
        ).first()
        if db_gpio:
            db_gpio.pwm_value = value
            db.commit()
        return {"message": f"GPIO {pin_number} PWM -> {value:.3f} (mock)"}

    if dev is None:
        raise HTTPException(
            status_code=404,
            detail=f"GPIO {pin_number} не настроен как PWM."
        )
    if not isinstance(dev, PWMOutputDevice):
        raise HTTPException(
            status_code=400,
            detail=f"GPIO {pin_number} не является PWM. Текущий режим: {type(dev).__name__}."
        )

    try:
        dev.value = value
    except GPIOZeroError as e:
        raise HTTPException(status_code=500, detail=f"GPIO error: {e}")

    # Сохраняем в БД
    db_gpio = db.query(models.Gpio).filter(
        models.Gpio.gpio_number == pin_number
    ).first()
    if db_gpio:
        db_gpio.pwm_value = value
        db.commit()

    # Пуш в WS
    await _push_gpio_state(pin_number, "PWM", value)

    return {"message": f"GPIO {pin_number} PWM -> {value:.3f} ({value*100:.1f}%)"}


@router.delete("/{pin_number}")
async def unassign_gpio(pin_number: int, db: Session = Depends(get_db)):
    """Снять назначение с пина."""
    _close_pin(pin_number)

    db_gpio = db.query(models.Gpio).filter(
        models.Gpio.gpio_number == pin_number
    ).first()
    if not db_gpio:
        raise HTTPException(status_code=404, detail="GPIO не найден в БД.")

    db.delete(db_gpio)
    db.commit()

    await ws_manager.broadcast("gpio", "unassigned", {"pin": pin_number})
    return {"message": f"GPIO {pin_number} освобождён."}


@router.get("/info")
def get_pi_info():
    """Информация о плате Raspberry Pi."""
    if not ON_PI:
        return {
            "revision": "MOCK", "model": "MOCK_PI", "pcb_revision": "MOCK",
            "ram": "MOCK_RAM", "manufacturer": "MOCK_MAKER",
            "processor": "MOCK_PROC", "headers": {"J8": {}},
            "hw_pwm_pins": sorted(HW_PWM_PINS),
        }
    try:
        info = pi_info()
        return {
            "revision":     info.revision,
            "model":        info.model,
            "pcb_revision": info.pcb_revision,
            "ram":          f"{info.memory}M",
            "manufacturer": info.manufacturer,
            "processor":    info.processor,
            "headers":      info.headers,
            "hw_pwm_pins":  sorted(HW_PWM_PINS),
        }
    except Exception as e:
        return {"error": str(e), "hw_pwm_pins": sorted(HW_PWM_PINS)}


# ─── Lifecycle ────────────────────────────────────────────────────────────────

def startup_event():
    """Восстановить состояние пинов из БД при старте."""
    global _watcher_task

    if not ON_PI:
        print("[GPIO] Не на Raspberry Pi, пропускаем инициализацию GPIO.")
    else:
        print("[GPIO] Инициализация пинов из БД...")
        with SessionLocal() as db:
            gpios = db.query(models.Gpio).all()
            for gpio in gpios:
                fn = gpio.gpio_function.upper() if gpio.gpio_function else ""
                try:
                    if fn == "OUTPUT":
                        devices[gpio.gpio_number] = DigitalOutputDevice(gpio.gpio_number)
                    elif fn == "INPUT":
                        dev = DigitalInputDevice(gpio.gpio_number, pull_up=True)
                        _make_input_callbacks(gpio.gpio_number, dev)
                        _last_input_values[gpio.gpio_number] = int(dev.value)
                        devices[gpio.gpio_number] = dev
                    elif fn == "PWM":
                        saved_val = gpio.pwm_value or 0.0
                        dev = PWMOutputDevice(gpio.gpio_number, initial_value=saved_val)
                        devices[gpio.gpio_number] = dev
                except (GPIOZeroError, Exception) as e:
                    print(f"[GPIO] Не удалось инициализировать GPIO {gpio.gpio_number}: {e}")

    # Запускаем watcher в любом режиме (и на Pi, и на mock)
    _watcher_task = asyncio.ensure_future(_gpio_watcher())
    print("[GPIO] Watcher запущен.")


def shutdown_event():
    """Закрыть все пины при остановке."""
    global _watcher_task
    if _watcher_task:
        _watcher_task.cancel()
        _watcher_task = None

    for pin_number in list(devices.keys()):
        _close_pin(pin_number)
    print("[GPIO] Все пины закрыты.")

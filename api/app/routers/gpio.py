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
from typing import List, Optional

# ─── gpiozero import с mock-заглушками ────────────────────────────────────────

def _detect_pi() -> bool:
    """
    Надёжное определение Raspberry Pi по /proc/cpuinfo и /proc/device-tree/model.
    НЕ используем просто "Hardware" — оно есть на любом Linux.
    Ищем конкретные строки характерные только для Pi.
    """
    # Способ 1: /proc/device-tree/model (самый надёжный на новых Pi OS)
    try:
        with open("/proc/device-tree/model", "rb") as f:
            model = f.read().decode("utf-8", errors="replace")
        if "Raspberry Pi" in model:
            print(f"[GPIO] Обнаружен: {model.strip()}")
            return True
    except Exception:
        pass

    # Способ 2: /proc/cpuinfo — ищем строго "Raspberry Pi" в строке Model
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                # "Model\t: Raspberry Pi 4 Model B Rev 1.4"
                if line.startswith("Model") and "Raspberry Pi" in line:
                    print(f"[GPIO] Обнаружен по cpuinfo: {line.strip()}")
                    return True
                # "Hardware\t: BCM2711" — только BCM271x/BCM283x реально Pi
                if line.startswith("Hardware") and (
                    "BCM2711" in line or "BCM2837" in line or
                    "BCM2836" in line or "BCM2835" in line
                ):
                    print(f"[GPIO] Обнаружен по Hardware: {line.strip()}")
                    return True
    except Exception:
        pass

    return False


# Определяем платформу ДО импорта gpiozero
ON_PI = _detect_pi()

# Импортируем gpiozero только если мы на Pi
# (на не-Pi gpiozero может упасть при попытке определить pin factory)
_gpiozero_ok = False
if ON_PI:
    try:
        from gpiozero import DigitalOutputDevice, DigitalInputDevice, PWMOutputDevice
        from gpiozero.exc import GPIOZeroError
        _gpiozero_ok = True
        print("[GPIO] gpiozero успешно импортирован.")
    except Exception as e:
        print(f"[GPIO] Ошибка импорта gpiozero: {e} — переходим на mock.")
        ON_PI = False

# pi_info импортируем отдельно — в gpiozero 2.x путь изменился
pi_info = None
if _gpiozero_ok:
    for _pi_info_path in (
        "gpiozero.devices",        # gpiozero 1.x
        "gpiozero",                # gpiozero 2.x
    ):
        try:
            import importlib as _il
            _m = _il.import_module(_pi_info_path)
            if hasattr(_m, "pi_info"):
                pi_info = _m.pi_info
                break
        except Exception:
            pass

# PiBoardInfo — только для /gpio/all-pins, не критично
PiBoardInfo = None
if _gpiozero_ok:
    for _path, _attr in (
        ("gpiozero.pins.pi", "PiBoardInfo"),
        ("gpiozero.boards", "PiBoardInfo"),
    ):
        try:
            import importlib as _il
            _m = _il.import_module(_path)
            if hasattr(_m, _attr):
                PiBoardInfo = getattr(_m, _attr)
                break
        except Exception:
            pass

if not ON_PI:
    print("[GPIO] Режим: MOCK (не Raspberry Pi или gpiozero недоступен)")

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
_watcher_task: Optional[asyncio.Task] = None

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
    # Fallback: стандартная раскладка Pi GPIO 1-27
    fallback = [
        {"number": i, "header": "J8", "supports_hw_pwm": i in HW_PWM_PINS}
        for i in range(1, 28)
    ]
    if not ON_PI or PiBoardInfo is None:
        return fallback
    try:
        info = PiBoardInfo()
        return [
            {
                "number": pin.number,
                "header": pin.header,
                "supports_hw_pwm": pin.number in HW_PWM_PINS,
            }
            for pin in info.pins.values()
        ]
    except Exception:
        return fallback


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

    # PWM доступен только на пинах с аппаратной поддержкой (GPIO 12, 13, 18, 19).
    # lgpio (дефолтный factory на Pi OS Bookworm) не поддерживает программный PWM.
    if function == "PWM" and not _is_hw_pwm(pin_number):
        raise HTTPException(
            status_code=400,
            detail=(
                f"GPIO {pin_number} не поддерживает аппаратный PWM. "
                f"Используйте GPIO 12, 13, 18 или 19 (аппаратные PWM пины)."
            )
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
            # Аппаратный PWM через lgpio (дефолтный factory на Pi OS Bookworm).
            # Поддерживается только на GPIO 12, 13, 18, 19.
            # Требует /dev/gpiochip0 в docker-compose devices.
            dev = PWMOutputDevice(pin_number, initial_value=0.0)
    except GPIOZeroError as e:
        err = str(e)
        # Даём понятную подсказку при отсутствии доступа к GPIO
        if "gpiomem" in err or "permission" in err.lower() or "No access" in err or "gpiochip" in err:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Нет доступа к GPIO: {e}. "
                    "Убедитесь, что в docker-compose.yml в секции devices указаны "
                    "/dev/gpiomem и /dev/gpiochip0, и group_add содержит GID группы gpio (обычно 997)."
                )
            )
        raise HTTPException(status_code=500, detail=f"GPIO error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Неожиданная ошибка GPIO: {e}")

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
            "on_pi": False,
        }

    # /proc/cpuinfo — всегда читаем как источник правды
    cpuinfo  = _read_cpuinfo()
    revision = cpuinfo.get("Revision", "unknown")

    # Базовые данные из cpuinfo (надёжны на любой версии gpiozero)
    base = {
        "revision":     revision,
        "model":        cpuinfo.get("Model", "Raspberry Pi (unknown model)"),
        "pcb_revision": revision,
        "ram":          _ram_from_revision(revision),
        "manufacturer": _manufacturer_from_revision(revision),
        "processor":    _processor_from_revision(revision),
        "hw_pwm_pins":  sorted(HW_PWM_PINS),
        "on_pi":        True,
    }

    # Пробуем обогатить данными из gpiozero pi_info() (необязательно)
    if pi_info is not None:
        try:
            info = pi_info()
            # Обновляем только те поля, которые реально есть в объекте
            if hasattr(info, "revision"):
                base["revision"] = info.revision
            if hasattr(info, "model"):
                base["model"] = info.model
            if hasattr(info, "pcb_revision"):
                base["pcb_revision"] = info.pcb_revision
            if hasattr(info, "memory") and info.memory:
                base["ram"] = f"{info.memory} МБ"
            if hasattr(info, "manufacturer") and info.manufacturer:
                base["manufacturer"] = info.manufacturer
            # processor: в gpiozero 1.x — info.processor, в 2.x может не быть
            for attr in ("processor", "soc", "cpu"):
                if hasattr(info, attr) and getattr(info, attr):
                    base["processor"] = getattr(info, attr)
                    break
        except Exception:
            pass  # gpiozero не смогла — не страшно, cpuinfo уже заполнил всё

    return base


def _read_cpuinfo() -> dict:
    """Читает /proc/cpuinfo и возвращает dict ключ→значение."""
    result = {}
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if ":" in line:
                    key, _, val = line.partition(":")
                    k = key.strip()
                    if k not in result:   # берём первое вхождение
                        result[k] = val.strip()
    except Exception:
        pass
    return result


def _ram_from_revision(revision: str) -> str:
    """
    Декодирует объём RAM из revision-кода Raspberry Pi (новый формат с 2012).
    Биты [22:20] кодируют память: 0=256M, 1=512M, 2=1G, 3=2G, 4=4G, 5=8G.
    """
    try:
        rev_int = int(revision.lstrip("0") or "0", 16)
        # Новый стиль revision (бит 23 = 1)
        if rev_int & (1 << 23):
            mem_code = (rev_int >> 20) & 0x7
            mem_map = {0: "256 МБ", 1: "512 МБ", 2: "1 ГБ",
                       3: "2 ГБ",   4: "4 ГБ",   5: "8 ГБ"}
            return mem_map.get(mem_code, "unknown")
    except Exception:
        pass
    return "unknown"


def _manufacturer_from_revision(revision: str) -> str:
    """
    Декодирует производителя из revision-кода (биты [19:16]).
    0=Sony UK, 1=Egoman, 2=Embest, 3=Sony Japan, 4=Embest, 5=Stadium.
    """
    try:
        rev_int = int(revision.lstrip("0") or "0", 16)
        if rev_int & (1 << 23):
            mfr_code = (rev_int >> 16) & 0xF
            mfr_map  = {0: "Sony UK", 1: "Egoman", 2: "Embest",
                        3: "Sony Japan", 4: "Embest", 5: "Stadium"}
            return mfr_map.get(mfr_code, "unknown")
    except Exception:
        pass
    return "unknown"


def _processor_from_revision(revision: str) -> str:
    """
    Декодирует тип процессора из revision-кода (биты [15:12]).
    0=BCM2835, 1=BCM2836, 2=BCM2837, 3=BCM2711, 4=BCM2712.
    """
    try:
        rev_int = int(revision.lstrip("0") or "0", 16)
        if rev_int & (1 << 23):
            proc_code = (rev_int >> 12) & 0xF
            proc_map  = {
                0: "BCM2835",
                1: "BCM2836",
                2: "BCM2837",
                3: "BCM2711",  # Pi 4
                4: "BCM2712",  # Pi 5
            }
            return proc_map.get(proc_code, f"unknown (code {proc_code})")
    except Exception:
        pass
    return "unknown"


@router.get("/sysinfo")
def get_sysinfo():
    """
    Системная информация: CPU температура, загрузка, RAM, диск, uptime, IP, ядро.
    Читается через psutil (кроссплатформенно) + /proc/cpuinfo для напряжения (только Pi).
    """
    import os
    import socket
    import platform

    result: dict = {}

    # ── psutil ────────────────────────────────────────────────────────────────
    try:
        import psutil

        # CPU usage (1-секундный замер в синхронном эндпоинте — приемлемо)
        result["cpu_usage"] = psutil.cpu_percent(interval=0.5)

        # RAM
        vm = psutil.virtual_memory()
        result["ram_total"]   = _fmt_bytes(vm.total)
        result["ram_used"]    = _fmt_bytes(vm.used)
        result["ram_percent"] = vm.percent

        # Disk
        du = psutil.disk_usage("/")
        result["disk_total"]   = _fmt_bytes(du.total)
        result["disk_used"]    = _fmt_bytes(du.used)
        result["disk_percent"] = du.percent

        # Uptime
        import datetime
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        delta     = datetime.datetime.now() - boot_time
        d, rem    = divmod(int(delta.total_seconds()), 86400)
        h, rem    = divmod(rem, 3600)
        m         = rem // 60
        result["uptime"] = (
            f"{d}д {h}ч {m}м" if d else f"{h}ч {m}м"
        )

        # IP адреса (исключаем loopback)
        ips = []
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    ips.append(f"{iface}: {addr.address}")
        result["ip_addresses"] = ips

    except ImportError:
        result["psutil_error"] = "psutil не установлен"

    # ── CPU температура (только Linux / Pi) ───────────────────────────────────
    cpu_temp = None
    try:
        # Путь для Raspberry Pi
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            cpu_temp = int(f.read().strip()) / 1000.0
    except Exception:
        pass

    if cpu_temp is None:
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            for key in ("cpu_thermal", "cpu-thermal", "coretemp", "k10temp"):
                if key in temps and temps[key]:
                    cpu_temp = temps[key][0].current
                    break
        except Exception:
            pass

    result["cpu_temp"] = cpu_temp

    # ── CPU напряжение (только Pi) ────────────────────────────────────────────
    # Способ 1: vcgencmd (требует /dev/vchiq проброшенный в контейнер)
    cpu_voltage = None
    try:
        import subprocess
        out = subprocess.check_output(
            ["vcgencmd", "measure_volts", "core"],
            timeout=2, stderr=subprocess.DEVNULL
        ).decode().strip()
        # out = "volt=1.2000V"
        cpu_voltage = out.replace("volt=", "").strip()
    except Exception:
        pass

    # Способ 2: sysfs hwmon (работает без /dev/vchiq на Pi OS Bullseye+)
    if cpu_voltage is None:
        import glob as _glob
        for pattern in (
            "/sys/devices/platform/soc/soc:firmware/raspberrypi-hwmon/hwmon/hwmon*/in0_input",
            "/sys/class/hwmon/hwmon*/in0_input",
        ):
            for path in _glob.glob(pattern):
                try:
                    with open(path) as f:
                        mv = int(f.read().strip())
                    cpu_voltage = f"{mv / 1000:.4f}V"
                    break
                except Exception:
                    pass
            if cpu_voltage:
                break

    result["cpu_voltage"] = cpu_voltage

    # ── ОС / ядро ─────────────────────────────────────────────────────────────
    result["kernel"]  = platform.release()
    result["os_name"] = platform.version() if platform.system() != "Linux" else _read_os_name()

    return result


def _fmt_bytes(b: int) -> str:
    """Форматирует байты в читаемый вид (MB / GB)."""
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.1f} ГБ"
    return f"{b / 1_048_576:.0f} МБ"


def _read_os_name() -> str:
    """Читает PRETTY_NAME из /etc/os-release."""
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return "Linux"


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

from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


# ─── GPIO ────────────────────────────────────────────────────────────────────

class GpioBase(BaseModel):
    gpio_number: int
    gpio_description: str
    gpio_function: str

class GpioCreate(GpioBase):
    pass

class Gpio(GpioBase):
    model_config = ConfigDict(from_attributes=True)

class GpioWithState(Gpio):
    value: Optional[float] = None   # 0/1 для INPUT/OUTPUT, 0.0-1.0 для PWM
    pwm_value: Optional[float] = None

class GpioSetState(BaseModel):
    gpio_number: int
    state: str

class GpioSetValue(BaseModel):
    gpio_number: int
    value: int  # 0 or 1

class GpioSetPwm(BaseModel):
    gpio_number: int
    value: float  # 0.0 – 1.0 (gpiozero использует долю, не 0-255)

class GpioPinInfo(BaseModel):
    """Расширенная информация о пине для страницы настроек"""
    number: int
    header: str
    supports_hw_pwm: bool = False  # True только для GPIO 12,13,18,19


# ─── DEVICE ──────────────────────────────────────────────────────────────────

class DeviceBase(BaseModel):
    name: str
    device_type: str          # climate, irrigation, light, co2, power, camera
    ip_address: str
    port: int = 80
    poll_interval: int = 5
    enabled: bool = True
    description: Optional[str] = None

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    poll_interval: Optional[int] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None

class DeviceOut(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    last_seen: Optional[datetime] = None
    firmware_version: Optional[str] = None
    mac_address: Optional[str] = None
    created_at: datetime

class DeviceWithSensors(DeviceOut):
    """Устройство с последними показаниями сенсоров"""
    latest_readings: dict = {}


# ─── SENSOR READING ──────────────────────────────────────────────────────────

class SensorReadingBase(BaseModel):
    sensor_type: str
    value: float
    unit: Optional[str] = None

class SensorReadingCreate(SensorReadingBase):
    device_id: int

class SensorReadingOut(SensorReadingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    timestamp: datetime

class SensorHistoryPoint(BaseModel):
    timestamp: datetime
    value: float

class SensorHistory(BaseModel):
    device_id: int
    sensor_type: str
    unit: Optional[str]
    data: List[SensorHistoryPoint]


# ─── AUTOMATION ──────────────────────────────────────────────────────────────

class AutomationBase(BaseModel):
    name: str
    description: Optional[str] = None
    enabled: bool = True
    trigger_json: str   # JSON-строка с условием
    action_json: str    # JSON-строка с действием
    cooldown_seconds: int = 60

class AutomationCreate(AutomationBase):
    pass

class AutomationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    trigger_json: Optional[str] = None
    action_json: Optional[str] = None
    cooldown_seconds: Optional[int] = None

class AutomationOut(AutomationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_triggered: Optional[datetime] = None
    created_at: datetime


# ─── ALERT ───────────────────────────────────────────────────────────────────

class AlertBase(BaseModel):
    level: str = "info"   # info, warning, error, critical
    message: str

class AlertCreate(AlertBase):
    device_id: Optional[int] = None

class AlertOut(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: Optional[int] = None
    acknowledged: bool
    created_at: datetime


# ─── WEBSOCKET MESSAGES ───────────────────────────────────────────────────────

class WSSubscribe(BaseModel):
    """Клиент отправляет при подключении: {"type":"subscribe","channels":["sensors","gpio","alerts"]}"""
    type: str = "subscribe"
    channels: List[str]

class WSMessage(BaseModel):
    """Сервер пушит клиентам"""
    channel: str   # sensors | gpio | alerts | devices | system
    event: str     # update | status_change | alert | ...
    data: Any
    timestamp: Optional[str] = None


# ─── DEVICE CONTROL ──────────────────────────────────────────────────────────

class DeviceControlCommand(BaseModel):
    """Команда управления ESP-устройством"""
    relay1: Optional[int] = None   # 0 / 1
    relay2: Optional[int] = None
    relay3: Optional[int] = None
    relay4: Optional[int] = None
    pwm: Optional[int] = None      # 0-255
    extra: Optional[dict] = None   # произвольные поля для специфичных устройств

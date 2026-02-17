from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Gpio(Base):
    __tablename__ = "gpios"

    gpio_number = Column(Integer, primary_key=True, index=True)
    gpio_description = Column(String, index=True)
    # Функция пина: INPUT | OUTPUT | PWM
    gpio_function = Column(String)
    # Последнее сохранённое значение PWM (0.0 – 1.0), NULL для не-PWM пинов
    pwm_value = Column(Float, nullable=True, default=0.0)


class Device(Base):
    """ESP8266 / ESP32 устройство в сети теплицы"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    device_type = Column(String, nullable=False)  # climate, irrigation, light, co2, power, camera
    ip_address = Column(String, nullable=False, unique=True)
    port = Column(Integer, default=80)
    poll_interval = Column(Integer, default=5)   # секунды между опросами
    enabled = Column(Boolean, default=True)
    status = Column(String, default="unknown")   # online, offline, unknown
    last_seen = Column(DateTime(timezone=True), nullable=True)
    firmware_version = Column(String, nullable=True)
    mac_address = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    readings = relationship("SensorReading", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")


class SensorReading(Base):
    """Показание датчика от ESP-устройства"""
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    sensor_type = Column(String, nullable=False)   # temperature, humidity, soil_moisture, co2, lux ...
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)            # C, %, ppm, lux ...
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    device = relationship("Device", back_populates="readings")


class Automation(Base):
    """Правило автоматизации: если условие -> действие"""
    __tablename__ = "automations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)

    # JSON: {"device_id": 1, "sensor": "temperature", "operator": ">", "threshold": 30}
    trigger_json = Column(Text, nullable=False)

    # JSON: {"type": "gpio"|"device_control", "target_id": ..., "action": "on"|"off"|"set_value", "value": ...}
    action_json = Column(Text, nullable=False)

    cooldown_seconds = Column(Integer, default=60)  # минимальный интервал между срабатываниями
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    """Уведомление / тревога от устройства"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    level = Column(String, default="info")       # info, warning, error, critical
    message = Column(Text, nullable=False)
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="alerts")

from pydantic import BaseModel
from typing import Optional

class GpioBase(BaseModel):
    gpio_number: int
    gpio_description: str
    gpio_function: str

class GpioCreate(GpioBase):
    pass

class Gpio(GpioBase):
    class Config:
        from_attributes = True

# For GPIO control
class GpioSetState(BaseModel):
    gpio_number: int
    state: str # '0' (in), '1' (out), 'alt0' etc

class GpioSetValue(BaseModel):
    gpio_number: int
    value: int # 0 or 1

from sqlalchemy import Column, Integer, String
from .database import Base

class Gpio(Base):
    __tablename__ = "gpios"

    gpio_number = Column(Integer, primary_key=True, index=True)
    gpio_description = Column(String, index=True)
    gpio_function = Column(String)

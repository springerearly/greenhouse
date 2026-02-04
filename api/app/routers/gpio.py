from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

try:
    # GPIO Zero
    from gpiozero import DigitalOutputDevice, DigitalInputDevice
    from gpiozero.pins.native import NativeFactory # Using the native pin factory
    from gpiozero.exc import GPIOZeroError
    from gpiozero.devices import pi_info
    ON_PI = True
except ImportError:
    ON_PI = False


from .. import models, schemas
from ..database import get_db, SessionLocal

# This will hold our device objects
devices = {}

router = APIRouter(
    prefix="/gpio",
    tags=["gpio"],
)

def get_device(pin_number):
    if pin_number in devices:
        return devices[pin_number]
    return None

@router.get("/", response_model=List[schemas.Gpio])
def get_all_gpios(db: Session = Depends(get_db)):
    gpios = db.query(models.Gpio).all()
    # Here we could also add the current live state from gpiozero if needed
    return gpios

@router.post("/set-function")
def set_function(gpio_config: schemas.GpioCreate, db: Session = Depends(get_db)):
    """
    Assign a function (INPUT or OUTPUT) to a GPIO pin.
    """
    if not ON_PI:
        raise HTTPException(status_code=500, detail="Not running on a Raspberry Pi.")

    pin_number = gpio_config.gpio_number
    function = gpio_config.gpio_function.upper()

    # Clean up existing device if it exists
    if pin_number in devices:
        devices[pin_number].close()
        del devices[pin_number]

    try:
        if function == 'OUTPUT':
            devices[pin_number] = DigitalOutputDevice(pin_number)
        elif function == 'INPUT':
            devices[pin_number] = DigitalInputDevice(pin_number)
        else:
            raise HTTPException(status_code=400, detail="Invalid function. Use 'INPUT' or 'OUTPUT'.")
    except GPIOZeroError as e:
        raise HTTPException(status_code=500, detail=f"GPIO error: {e}")

    # Save to DB
    db_gpio = db.query(models.Gpio).filter(models.Gpio.gpio_number == pin_number).first()
    if db_gpio:
        db_gpio.gpio_function = function
        db_gpio.gpio_description = gpio_config.gpio_description
    else:
        db_gpio = models.Gpio(**gpio_config.dict())
        db.add(db_gpio)
    
    db.commit()
    db.refresh(db_gpio)

    return {"message": f"GPIO {pin_number} function set to {function}"}


@router.post("/set-value")
def set_value(gpio_value: schemas.GpioSetValue):
    """
    Set the value of an OUTPUT pin.
    """
    if not ON_PI:
        raise HTTPException(status_code=500, detail="Not running on a Raspberry Pi.")
        
    pin_number = gpio_value.gpio_number
    value = gpio_value.value

    device = get_device(pin_number)
    if not device:
        raise HTTPException(status_code=404, detail=f"GPIO {pin_number} not configured. Set function first.")

    if not isinstance(device, DigitalOutputDevice):
        raise HTTPException(status_code=400, detail=f"GPIO {pin_number} is not configured as OUTPUT.")

    try:
        if value == 1:
            device.on()
        elif value == 0:
            device.off()
        else:
            raise HTTPException(status_code=400, detail="Value must be 0 or 1.")
    except GPIOZeroError as e:
        raise HTTPException(status_code=500, detail=f"GPIO error: {e}")

    return {"message": f"Value for GPIO {pin_number} set to {value}"}

@router.get("/info")
def get_device_info():
    """
    Get information about the Raspberry Pi.
    """
    if not ON_PI:
        return {"message": "Not running on a Raspberry Pi."}
        
    try:
        info = pi_info()
        return {
            "revision": info.revision,
            "model": info.model,
            "pcb_revision": info.pcb_revision,
            "ram": f"{info.memory}M",
            "manufacturer": info.manufacturer,
            "processor": info.processor,
            "headers": info.headers,
        }
    except Exception as e:
        # This will happen if not running on a Pi
        return {"message": "Not running on a Raspberry Pi or unable to get info.", "error": str(e)}

@router.on_event("startup")
def startup_event():
    """
    On startup, re-initialize the state of the GPIO pins from the database.
    """
    if not ON_PI:
        print("Not on a Pi, skipping GPIO initialization.")
        return

    print("Startup: Initializing GPIO states from DB.")
    with SessionLocal() as db:
        gpios = db.query(models.Gpio).all()
        for gpio in gpios:
            try:
                if gpio.gpio_function == 'OUTPUT':
                    devices[gpio.gpio_number] = DigitalOutputDevice(gpio.gpio_number)
                elif gpio.gpio_function == 'INPUT':
                    devices[gpio.gpio_number] = DigitalInputDevice(gpio.gpio_number)
            except (GPIOZeroError, NameError):
                 # Fail silently on startup if a pin is already in use or there's an issue
                print(f"Could not initialize GPIO {gpio.gpio_number}")
    
@router.on_event("shutdown")
def shutdown_event():
    if not ON_PI:
        return
        
    for pin_number, device in devices.items():
        device.close()
    print("Shutdown: All GPIO devices closed.")
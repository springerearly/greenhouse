from fastapi import FastAPI
import models
from database import engine
from routers import gpio

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(gpio.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Greenhouse API"}

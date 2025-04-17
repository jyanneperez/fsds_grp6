from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.routes import router
from pathlib import Path

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent

# Template engine setup
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Mount static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Include modular routes
app.include_router(router)


from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from settings import STATIC_DIR


app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ВАЖНО: импорт routes должен быть ПОСЛЕ создания app
import backend.routes
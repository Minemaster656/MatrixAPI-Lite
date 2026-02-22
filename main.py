from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.templating import Jinja2Templates
from print_logo import print_logo
from contextlib import asynccontextmanager
from sqlmodel import select

from app.routers import auth
from app.routers.http import locations
from app.routers.websocket import chat
from app.core.db import engine
from app.models.models import Location, Character
from app.models.models import SQLModel


def seed_locations():
    from sqlmodel import Session

    default_locations = [
        {
            "name": "Таверна",
            "description": "Уютное место для отдыха путников",
            "background_url": "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=1920",
        },
        {
            "name": "Площадь",
            "description": "Центральная площадь города",
            "background_url": "https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?w=1920",
        },
        {
            "name": "Лес",
            "description": "Загадочный лес",
            "background_url": "https://images.unsplash.com/photo-1448375240586-882707db888b?w=1920",
        },
    ]
    with Session(engine) as session:
        existing = session.exec(select(Location)).first()
        if not existing:
            for loc in default_locations:
                session.add(Location(**loc))
            session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_locations()
    yield


print_logo()
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(locations.router)

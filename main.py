"""
Main FastAPI application entry point.

WHY: Central application configuration and routing setup.
HOW: Initializes FastAPI with lifespan events, mounts static files,
     configures Jinja2 templates, and includes all routers.
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from print_logo import print_logo
from setproctitle import setproctitle
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()
from sqlmodel import Session, select, SQLModel

from app.core.db import engine
from app.models.models import Location
from app.routers import auth
from app.routers.http import characters, locations
from app.routers.http import config
from app.routers.websocket import chat

limiter = Limiter(key_func=get_remote_address)


def seed_locations() -> None:
    """
    Populate database with default locations on first run.

    WHY: Provides initial game content without manual database setup.
    HOW: Checks for existing locations, inserts defaults if table is empty.

    Note:
        Default locations include themed areas with background images
        from Unsplash for immediate visual appeal.
    """
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
                location = Location.model_validate(loc)  # type: ignore[assignment]
                session.add(location)
            session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    WHY: Handles startup and shutdown events for the FastAPI application.
    HOW: Seeds database on startup, yields control to the application.

    Args:
        app: The FastAPI application instance.
    """
    seed_locations()
    yield


print_logo()
app = FastAPI(
    lifespan=lifespan,
    title="MatrixAPI",
    description="Ролевой движок на базе веб-чата с простым API",
    version="0.1.0",
)
app.state.limiter = limiter

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
    )


@app.get("/", response_class=HTMLResponse, summary="Landing page")
def read_root(request: Request):
    """
    Renders the landing page.

    WHY: Main entry point for new users to learn about the platform.
    HOW: Returns the landing.html template with Jinja2 rendering.
    """
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/login", response_class=HTMLResponse, summary="Login page")
def read_login(request: Request):
    """
    Renders the login page.

    WHY: Allows users to authenticate.
    HOW: Returns the login.html template.
    """
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse, summary="Registration page")
def read_register(request: Request):
    """
    Renders the registration page.

    WHY: Allows new users to create accounts.
    HOW: Returns the register.html template with registration form.
    """
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse, summary="Chat interface")
def read_chat(request: Request):
    """
    Renders the chat interface.

    WHY: Main game interface for role-playing interactions.
    HOW: Returns the chat.html template with all required components.
    """
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse, summary="User dashboard")
def read_dashboard(request: Request):
    """
    Renders the user dashboard.

    WHY: Central hub for character management and user settings.
    HOW: Returns the dashboard.html template.
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(locations.router)
app.include_router(characters.router)
app.include_router(config.router)

if __name__ == "__main__":
    setproctitle("MatrixAPI")
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=33217)

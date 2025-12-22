from __future__ import annotations
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, Request
from src.routes import base
from .utils.metrics import setup_metrics
from .utils.client_deps_container import DependencyContainer
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Base directory of this file (src/)
BASE_DIR = Path(__file__).resolve().parent
print(f"BASE_DIR: {BASE_DIR}")

# templates folder = "views"
templates = Jinja2Templates(directory=str(BASE_DIR / "views"))

# 🔹 Mount /static -> src/static
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

# Setup Prometheus metrics
setup_metrics(app)


# store container on app.state
app.state.container: Optional[DependencyContainer] = None


@app.on_event("startup")
async def startup_span():
    app.state.container = await DependencyContainer.create()


@app.on_event("shutdown")
async def shutdown_span():
    if app.state.container is not None:
        await app.state.container.shutdown()

# default page -> views/index.html
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


app.include_router(base.base_router)

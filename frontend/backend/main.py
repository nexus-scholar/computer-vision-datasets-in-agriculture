import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from . import routes

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BASE, "public")
DIST_DIR = os.path.join(BASE, "dist")

app = FastAPI(title="Agricultural CV Research Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)

if os.path.isdir(DIST_DIR):
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="dist")
else:
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")

    @app.get("/")
    def root():
        return RedirectResponse(url="/static/index.html")

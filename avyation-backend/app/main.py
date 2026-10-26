from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .config import settings
from .routers import api, portal, radar

app = FastAPI(
    title="Avyation API",
    description="Predictive flight intelligence + autonomous claim recovery (Kritical Hacks 2026).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router)
app.include_router(portal.router)
app.include_router(radar.router)



@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs")

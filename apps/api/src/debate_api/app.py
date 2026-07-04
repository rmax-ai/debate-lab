"""FastAPI application factory for DebateLab."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from debate_api.middleware.error_handler import add_error_handlers
from debate_api.middleware.request_id import RequestIDMiddleware
from debate_api.routes.events import router as events_router
from debate_api.routes.runs import router as runs_router


def create_app(testing: bool = False) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        testing: If True, disable docs and use in-memory SQLite.
    """
    app = FastAPI(
        title="DebateLab API",
        version="0.1.0",
        docs_url=None if testing else "/docs",
        redoc_url=None if testing else "/redoc",
    )

    # Middleware (order matters)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    add_error_handlers(app)

    # Routes
    app.include_router(runs_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")

    # Health check
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

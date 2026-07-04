"""Error handlers for the DebateLab API."""

from debate_orchestrator.phase_engine import InvalidPhaseTransitionError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def add_error_handlers(app: FastAPI) -> None:
    """Register structured error handlers on the app."""

    @app.exception_handler(InvalidPhaseTransitionError)
    async def phase_transition_handler(request: Request, exc: InvalidPhaseTransitionError):
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "invalid_transition",
                "message": str(exc),
                "details": {
                    "current": exc.current.value,
                    "target": exc.target.value,
                },
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "validation_error",
                "message": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "internal_error",
                "message": "An unexpected error occurred",
            },
        )

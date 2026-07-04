"""REST endpoints for debate runs."""

from __future__ import annotations

import uuid
from typing import Annotated

from debate_tracing.emitter import EventEmitter
from debate_tracing.models import Base, DebateRun
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from debate_api.dependencies import get_db, get_emitter

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    """Request to create a new debate run."""

    model_config = {"extra": "forbid"}

    topic: str = Field(..., min_length=1, max_length=500)
    context: str = Field(default="", max_length=5000)
    goal: str = Field(..., min_length=1, max_length=1000)
    constraints: str = Field(default="", max_length=2000)
    max_rounds: int = Field(default=3, ge=1, le=5)
    preset: str = Field(default="technical_decision", pattern=r"^[a-z_]+$")


class RunResponse(BaseModel):
    """Response for a debate run."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    topic: str
    context: str
    user_goal: str
    constraints: str
    max_rounds: int
    preset: str
    status: str
    rounds_count: int


@router.post("", status_code=201, response_model=RunResponse)
async def create_run(
    request: CreateRunRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    emitter: Annotated[EventEmitter, Depends(get_emitter)],
) -> DebateRun:
    """Create a new debate run and emit run_created event."""
    # Ensure tables exist (dev mode — replace with Alembic later)
    async with db.bind.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    run = DebateRun(
        topic=request.topic,
        context=request.context,
        user_goal=request.goal,
        constraints=request.constraints,
        max_rounds=request.max_rounds,
        preset=request.preset,
        status="pending",
    )
    db.add(run)
    await db.flush()

    await emitter.emit(
        run.id,
        "run_created",
        payload={
            "topic": request.topic,
            "goal": request.goal,
            "preset": request.preset,
            "max_rounds": request.max_rounds,
        },
    )

    await db.commit()
    await db.refresh(run)
    return run


@router.get("", response_model=list[RunResponse])
async def list_runs(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DebateRun]:
    """List all debate runs, newest first."""
    result = await db.execute(select(DebateRun).order_by(DebateRun.created_at.desc()).limit(50))
    return list(result.scalars().all())


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DebateRun:
    """Get a debate run by ID."""
    run = await db.get(DebateRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

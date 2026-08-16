from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class AgentRun(Base):
    __tablename__='agent_runs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supervisor: Mapped[str] = mapped_column(String(80), default='DISCOVERY_SUPERVISOR', index=True)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default='RUNNING', index=True)
    mode: Mapped[str] = mapped_column(String(40), default='OLLAMA_TOOLS')
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cycles_requested: Mapped[int] = mapped_column(Integer, default=1)
    cycles_completed: Mapped[int] = mapped_column(Integer, default=0)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentStep(Base):
    __tablename__='agent_steps'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('agent_runs.id'), index=True)
    cycle_no: Mapped[int] = mapped_column(Integer, default=1)
    agent_name: Mapped[str] = mapped_column(String(80), index=True)
    step_no: Mapped[int] = mapped_column(Integer, default=1)
    action: Mapped[str] = mapped_column(String(120), index=True)
    tool_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default='DONE')
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

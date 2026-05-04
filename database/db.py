"""SQLite progress log (bonus tracking)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class ProgressEvent(Base):
    __tablename__ = "progress_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_label = Column(String(128), default="default")
    bmi = Column(Float, nullable=True)
    pose_score = Column(Float, nullable=True)
    payload = Column(JSON, nullable=True)


_engine = None
_SessionLocal: Optional[sessionmaker] = None


def init_db(db_path: str | Path = "./data/health_intel.sqlite") -> None:
    global _engine, _SessionLocal
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)


def log_event(
    *,
    user_label: str = "default",
    bmi: Optional[float] = None,
    pose_score: Optional[float] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    with _SessionLocal() as s:
        s.add(
            ProgressEvent(
                user_label=user_label,
                bmi=bmi,
                pose_score=pose_score,
                payload=payload or {},
            )
        )
        s.commit()


def recent_events(limit: int = 20) -> List[Dict[str, Any]]:
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    with _SessionLocal() as s:
        rows = s.query(ProgressEvent).order_by(ProgressEvent.id.desc()).limit(limit).all()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r.id,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "user_label": r.user_label,
                    "bmi": r.bmi,
                    "pose_score": r.pose_score,
                    "payload": json.loads(json.dumps(r.payload or {})),
                }
            )
        return out

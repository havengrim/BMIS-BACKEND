"""Generic async repository base with pagination, filters, bulk ops."""
from __future__ import annotations

from typing import Any, Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

M = TypeVar("M", bound=Base)


class BaseRepository(Generic[M]):
    def __init__(self, model: Type[M]) -> None:
        self.model = model

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    async def get(self, db: AsyncSession, id: Any) -> Optional[M]:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 50,
        order_by: Any = None,
        filters: Optional[List] = None,
    ) -> Sequence[M]:
        q = select(self.model)
        if filters:
            q = q.where(and_(*filters))
        if order_by is not None:
            q = q.order_by(order_by)
        elif hasattr(self.model, "created_at"):
            q = q.order_by(self.model.created_at.desc())
        q = q.offset(skip).limit(limit)
        result = await db.execute(q)
        return result.scalars().all()

    async def count(self, db: AsyncSession, filters: Optional[List] = None) -> int:
        q = select(func.count()).select_from(self.model)
        if filters:
            q = q.where(and_(*filters))
        result = await db.execute(q)
        return result.scalar_one()

    # ------------------------------------------------------------------ #
    # Write (callers must await db.commit() to finalize the transaction)  #
    # ------------------------------------------------------------------ #

    async def create(self, db: AsyncSession, obj: M) -> M:
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def update(self, db: AsyncSession, obj: M, data: dict) -> M:
        for field, value in data.items():
            setattr(obj, field, value)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, obj: M) -> None:
        await db.delete(obj)
        await db.flush()

    async def bulk_create(self, db: AsyncSession, objects: List[M]) -> List[M]:
        for obj in objects:
            db.add(obj)
        await db.flush()
        for obj in objects:
            await db.refresh(obj)
        return objects


import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Pagination, get_current_user, require_permissions
from app.db.session import get_db
from app.modules.complaints.model import Complaint
from app.modules.complaints.schema import ComplaintCreate, ComplaintResponse, ComplaintUpdate
from app.repositories.complaint_repository import complaint_repo

router = APIRouter()
logger = logging.getLogger(__name__)


async def _generate_reference(db: AsyncSession) -> str:
    year = datetime.now().year
    result = await db.execute(
        select(func.count()).select_from(Complaint).where(
            Complaint.reference_number.like(f"CMP-{year}-%")
        )
    )
    count = result.scalar() or 0
    return f"CMP-{year}-{count + 1:04d}"


@router.get("/", response_model=list[ComplaintResponse])
async def list_complaints(
    page: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("complaints.read")),
):
    complaints = await complaint_repo.list(db, skip=page.skip, limit=page.limit)
    logger.info("COMPLAINTS_LIST count=%d skip=%d by user=%s", len(complaints), page.skip, current_user.get("sub"))
    return complaints


@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def file_complaint(
    body: ComplaintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("complaints.manage")),
):
    complaint = await complaint_repo.create(db, Complaint(
        **body.model_dump(),
        user_id=uuid.UUID(current_user["sub"]),
        reference_number=await _generate_reference(db),
    ))
    await db.commit()
    logger.info(
        "COMPLAINTS_CREATE id=%s reference=%s type=%s priority=%s by user=%s",
        complaint.id, complaint.reference_number, complaint.type,
        complaint.priority, current_user.get("sub"),
    )
    return complaint


@router.patch("/{id}", response_model=ComplaintResponse)
async def update_complaint(
    id: uuid.UUID,
    body: ComplaintUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("complaints.manage")),
):
    obj = await complaint_repo.get(db, id)
    if not obj:
        logger.warning("COMPLAINTS_UPDATE_NOT_FOUND id=%s by user=%s", id, current_user.get("sub"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    data = body.model_dump(exclude_unset=True)
    obj = await complaint_repo.update(db, obj, data)
    await db.commit()
    logger.info(
        "COMPLAINTS_UPDATE id=%s reference=%s fields=%s status=%s by user=%s",
        obj.id, obj.reference_number, list(data.keys()), obj.status, current_user.get("sub"),
    )
    return obj


import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Pagination, get_current_user, require_permissions
from app.db.session import get_db
from app.modules.business_permits.model import BusinessPermit
from app.modules.business_permits.schema import BusinessPermitCreate, BusinessPermitResponse, BusinessPermitUpdate
from app.repositories.business_permit_repository import business_permit_repo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[BusinessPermitResponse])
async def list_permits(
    page: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("business_permits.read")),
):
    permits = await business_permit_repo.list(db, skip=page.skip, limit=page.limit)
    logger.info("BUSINESS_PERMITS_LIST count=%d skip=%d by user=%s", len(permits), page.skip, current_user.get("sub"))
    return permits


@router.post("/", response_model=BusinessPermitResponse, status_code=status.HTTP_201_CREATED)
async def apply_permit(
    body: BusinessPermitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("business_permits.manage")),
):
    permit = await business_permit_repo.create(db, BusinessPermit(
        **body.model_dump(), user_id=uuid.UUID(current_user["sub"])
    ))
    await db.commit()
    logger.info(
        "BUSINESS_PERMITS_CREATE id=%s business_name=%r type=%s by user=%s",
        permit.id, permit.business_name, permit.business_type, current_user.get("sub"),
    )
    return permit


@router.patch("/{id}", response_model=BusinessPermitResponse)
async def update_permit(
    id: uuid.UUID,
    body: BusinessPermitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("business_permits.manage")),
):
    obj = await business_permit_repo.get(db, id)
    if not obj:
        logger.warning("BUSINESS_PERMITS_UPDATE_NOT_FOUND id=%s by user=%s", id, current_user.get("sub"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permit not found")
    data = body.model_dump(exclude_unset=True)
    obj = await business_permit_repo.update(db, obj, data)
    await db.commit()
    logger.info(
        "BUSINESS_PERMITS_UPDATE id=%s business_name=%r fields=%s status=%s by user=%s",
        obj.id, obj.business_name, list(data.keys()), obj.status, current_user.get("sub"),
    )
    return obj


import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Pagination, get_current_user, require_permissions
from app.db.session import get_db
from app.modules.certificates.model import CertificateCounter, CertificateRequest
from app.modules.certificates.schema import CertificateRequestCreate, CertificateRequestResponse, CertificateRequestUpdate
from app.repositories.certificate_repository import certificate_repo

router = APIRouter()
logger = logging.getLogger(__name__)


async def _generate_request_number(db: AsyncSession, cert_type: str) -> str:
    year = datetime.now().year
    result = await db.execute(
        select(CertificateCounter).where(
            CertificateCounter.certificate_type == cert_type,
            CertificateCounter.year == year,
        )
    )
    counter = result.scalar_one_or_none()
    if not counter:
        counter = CertificateCounter(certificate_type=cert_type, last_number=0, year=year)
        db.add(counter)
    counter.last_number += 1
    prefix = cert_type.upper()[:3]
    return f"{prefix}-{year}-{counter.last_number:04d}"


@router.get("/", response_model=list[CertificateRequestResponse])
async def list_requests(
    page: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("certificates.read")),
):
    requests = await certificate_repo.list(db, skip=page.skip, limit=page.limit)
    logger.info("CERTIFICATES_LIST count=%d skip=%d by user=%s", len(requests), page.skip, current_user.get("sub"))
    return requests


@router.post("/", response_model=CertificateRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    body: CertificateRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("certificates.manage")),
):
    req = await certificate_repo.create(db, CertificateRequest(
        **body.model_dump(),
        user_id=uuid.UUID(current_user["sub"]),
        request_number=await _generate_request_number(db, body.certificate_type.value),
    ))
    await db.commit()
    logger.info(
        "CERTIFICATES_CREATE id=%s request_number=%s type=%s by user=%s",
        req.id, req.request_number, req.certificate_type, current_user.get("sub"),
    )
    return req


@router.patch("/{id}", response_model=CertificateRequestResponse)
async def update_request(
    id: uuid.UUID,
    body: CertificateRequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("certificates.manage")),
):
    obj = await certificate_repo.get(db, id)
    if not obj:
        logger.warning("CERTIFICATES_UPDATE_NOT_FOUND id=%s by user=%s", id, current_user.get("sub"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    data = body.model_dump(exclude_unset=True)
    obj = await certificate_repo.update(db, obj, data)
    await db.commit()
    logger.info(
        "CERTIFICATES_UPDATE id=%s request_number=%s fields=%s status=%s by user=%s",
        obj.id, obj.request_number, list(data.keys()), obj.status, current_user.get("sub"),
    )
    return obj


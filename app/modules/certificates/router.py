from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime

from app.db.session import get_db
from app.modules.certificates.model import CertificateRequest, CertificateCounter
from app.modules.certificates.schema import CertificateRequestCreate, CertificateRequestUpdate, CertificateRequestResponse
from app.core.dependencies import get_current_user

router = APIRouter()


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
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(CertificateRequest).order_by(CertificateRequest.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=CertificateRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    body: CertificateRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    req = CertificateRequest(
        **body.model_dump(),
        user_id=uuid.UUID(current_user["sub"]),
        request_number=await _generate_request_number(db, body.certificate_type.value),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.patch("/{id}", response_model=CertificateRequestResponse)
async def update_request(
    id: uuid.UUID,
    body: CertificateRequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(CertificateRequest).where(CertificateRequest.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj

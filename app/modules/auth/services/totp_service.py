"""TOTP / MFA service — setup, confirm, disable, status."""
import logging

import pyotp
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.schema import TOTPDisableRequest, TOTPSetupResponse, TOTPVerifyRequest
from app.modules.auth.services.helpers import get_user_or_404

logger = logging.getLogger(__name__)

ISSUER_NAME = "BMIS Barangay"


async def setup(current_user: dict, db: AsyncSession) -> TOTPSetupResponse:
    """Generate a TOTP secret and provisioning URI. MFA is NOT yet active until confirmed."""
    user = await get_user_or_404(db, current_user["sub"])

    if user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP is already enabled")

    secret = pyotp.random_base32()
    user.totp_secret = secret
    await db.commit()

    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=ISSUER_NAME)
    logger.info("TOTP_SETUP_INITIATED user_id=%s", user.id)
    return TOTPSetupResponse(provisioning_uri=uri, secret=secret)


async def confirm(body: TOTPVerifyRequest, current_user: dict, db: AsyncSession) -> None:
    """Verify the first code from the authenticator app to activate MFA."""
    user = await get_user_or_404(db, current_user["sub"])

    if not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP setup not initiated")
    if user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP is already enabled")
    if not pyotp.TOTP(user.totp_secret).verify(body.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authenticator code")

    user.totp_enabled = True
    await db.commit()
    logger.info("TOTP_ENABLED user_id=%s", user.id)


async def disable(body: TOTPDisableRequest, current_user: dict, db: AsyncSession) -> None:
    """Disable MFA. Requires a valid current TOTP code as confirmation."""
    user = await get_user_or_404(db, current_user["sub"])

    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP is not enabled")
    if not pyotp.TOTP(user.totp_secret).verify(body.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authenticator code")

    user.totp_enabled = False
    user.totp_secret = None
    await db.commit()
    logger.info("TOTP_DISABLED user_id=%s", user.id)


async def get_status(current_user: dict, db: AsyncSession) -> dict:
    """Return whether TOTP is currently enabled for the user."""
    user = await get_user_or_404(db, current_user["sub"])
    return {"totp_enabled": user.totp_enabled}

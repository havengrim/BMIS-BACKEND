"""add_ip_address_to_system_logs

Revision ID: 9d51e2b4c6a1
Revises: 2627aa6433c3
Create Date: 2026-05-10 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9d51e2b4c6a1"
down_revision: Union[str, None] = "2627aa6433c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("system_logs", sa.Column("ip_address", sa.String(length=64), nullable=True))
    op.create_index("ix_system_logs_ip_address", "system_logs", ["ip_address"])


def downgrade() -> None:
    op.drop_index("ix_system_logs_ip_address", table_name="system_logs")
    op.drop_column("system_logs", "ip_address")
